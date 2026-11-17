"""Lambda handler for updating and observing document lifecycle statuses in DynamoDB.
Configured with SAM Policy Template: DynamoDBCrudPolicy.
"""

import os
from typing import Any, Dict

from src.common.models import DocumentStatus, VALID_STATUS_TRANSITIONS
from src.common.utils import (
    build_response,
    get_dynamodb_resource,
    logger,
    parse_body,
    utc_now_iso,
)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handles PATCH /documents/{id}/status for observability and state machine tracking."""
    table_name = os.getenv("TABLE_NAME")
    if not table_name:
        logger.error("Environment variable TABLE_NAME is not set.")
        return build_response(500, {"error": "Server configuration error: missing TABLE_NAME"})

    path_params = event.get("pathParameters") or {}
    document_id = path_params.get("id")
    if not document_id:
        return build_response(400, {"error": "Path parameter 'id' is required"})

    try:
        body = parse_body(event)
    except ValueError as err:
        return build_response(400, {"error": str(err)})

    target_status = body.get("status")
    reason = body.get("reason", "Manual observation update")

    # Validate status enum
    valid_statuses = [s.value for s in DocumentStatus]
    if not target_status or target_status not in valid_statuses:
        return build_response(
            400,
            {
                "error": f"Invalid status '{target_status}'. Must be one of: {valid_statuses}",
                "allowed_statuses": valid_statuses,
            },
        )

    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(table_name)

    # Fetch current document
    try:
        get_res = table.get_item(Key={"document_id": document_id})
        item = get_res.get("Item")
        if not item:
            return build_response(404, {"error": f"Document {document_id} not found"})
    except Exception as err:
        logger.error(f"Error fetching document {document_id}: {err}")
        return build_response(500, {"error": "Failed to fetch document"})

    current_status = item.get("status")
    now = utc_now_iso()

    # Log observable transition
    logger.info(
        f"[OBSERVABILITY] Document {document_id} transition: '{current_status}' -> '{target_status}'. Reason: {reason}"
    )

    history_entry = {
        "status": target_status,
        "previous_status": current_status,
        "changed_at": now,
        "reason": reason,
    }

    # Update item in DynamoDB using UpdateItem expression
    try:
        update_res = table.update_item(
            Key={"document_id": document_id},
            UpdateExpression="SET #s = :status, updated_at = :updated_at, history = list_append(if_not_exists(history, :empty_list), :new_entry)",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":status": target_status,
                ":updated_at": now,
                ":new_entry": [history_entry],
                ":empty_list": [],
            },
            ReturnValues="ALL_NEW",
        )
        updated_item = update_res.get("Attributes")
    except Exception as err:
        logger.error(f"Failed to update document status in DynamoDB: {err}")
        return build_response(500, {"error": "Failed to update document status"})

    return build_response(
        200,
        {
            "message": "Status updated successfully",
            "document": updated_item,
            "transition": {
                "from": current_status,
                "to": target_status,
                "timestamp": now,
            },
        },
    )

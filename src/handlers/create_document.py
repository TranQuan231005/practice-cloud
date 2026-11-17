"""Lambda handler for creating new document metadata in DynamoDB.
Configured with SAM Policy Template: DynamoDBCrudPolicy.
"""

import os
import uuid
from typing import Any, Dict

from src.common.models import DocumentStatus
from src.common.utils import (
    build_response,
    get_dynamodb_resource,
    logger,
    parse_body,
    utc_now_iso,
)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handles POST /documents."""
    table_name = os.getenv("TABLE_NAME")
    if not table_name:
        logger.error("Environment variable TABLE_NAME is not set.")
        return build_response(500, {"error": "Server configuration error: missing TABLE_NAME"})

    try:
        body = parse_body(event)
    except ValueError as err:
        return build_response(400, {"error": str(err)})

    title = body.get("title")
    owner = body.get("owner")
    description = body.get("description", "")

    # Validation
    if not title or not isinstance(title, str) or not title.strip():
        return build_response(400, {"error": "Field 'title' is required and must be a non-empty string"})
    if len(title) > 120:
        return build_response(400, {"error": "Field 'title' must not exceed 120 characters"})
    if not owner or not isinstance(owner, str) or not owner.strip():
        return build_response(400, {"error": "Field 'owner' is required and must be a non-empty string"})

    now = utc_now_iso()
    document_id = str(uuid.uuid4())
    initial_status = DocumentStatus.PENDING_UPLOAD.value

    item = {
        "document_id": document_id,
        "title": title.strip(),
        "owner": owner.strip(),
        "description": description.strip() if description else "",
        "status": initial_status,
        "file_key": None,
        "created_at": now,
        "updated_at": now,
        "history": [
            {
                "status": initial_status,
                "changed_at": now,
                "reason": "Initial document creation",
            }
        ],
    }

    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(table_name)

    try:
        table.put_item(Item=item)
        logger.info(
            f"Created document {document_id} with status {initial_status} for owner {owner}"
        )
    except Exception as err:
        logger.error(f"Failed to put item in DynamoDB table {table_name}: {err}")
        return build_response(500, {"error": "Failed to save document metadata"})

    return build_response(201, item)

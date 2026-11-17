"""Lambda handler for reading document metadata from DynamoDB.
Configured with SAM Policy Template: DynamoDBReadPolicy.
"""

import os
from typing import Any, Dict

from src.common.utils import (
    build_response,
    get_dynamodb_resource,
    logger,
)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handles GET /documents and GET /documents/{id}."""
    table_name = os.getenv("TABLE_NAME")
    if not table_name:
        logger.error("Environment variable TABLE_NAME is not set.")
        return build_response(500, {"error": "Server configuration error: missing TABLE_NAME"})

    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(table_name)

    path_params = event.get("pathParameters") or {}
    document_id = path_params.get("id")

    if document_id:
        try:
            response = table.get_item(Key={"document_id": document_id})
            item = response.get("Item")
            if not item:
                logger.info(f"Document {document_id} not found.")
                return build_response(404, {"error": f"Document with ID {document_id} not found"})
            return build_response(200, item)
        except Exception as err:
            logger.error(f"Error fetching document {document_id}: {err}")
            return build_response(500, {"error": "Failed to retrieve document"})

    # Listing all documents
    try:
        response = table.scan(Limit=50)
        items = response.get("Items", [])
        return build_response(200, {"documents": items, "count": len(items)})
    except Exception as err:
        logger.error(f"Error scanning documents: {err}")
        return build_response(500, {"error": "Failed to list documents"})

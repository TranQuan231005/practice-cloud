"""Common utilities, response builders, and AWS client initializers."""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import boto3

logger = logging.getLogger("document-vault")
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def build_response(status_code: int, body: Any) -> Dict[str, Any]:
    """Generate standardized API Gateway proxy integration response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PATCH,OPTIONS",
        },
        "body": json.dumps(body),
    }


def parse_body(event: Dict[str, Any]) -> Dict[str, Any]:
    """Safely parse JSON request body from API Gateway event."""
    body = event.get("body")
    if not body:
        return {}
    if isinstance(body, dict):
        return body
    try:
        return json.loads(body)
    except (TypeError, ValueError) as err:
        logger.warning(f"Failed to parse request JSON: {err}")
        raise ValueError("Invalid JSON in request body") from err


def get_dynamodb_resource():
    """Get DynamoDB resource, respecting local endpoint if set."""
    endpoint_url = os.getenv("DYNAMODB_ENDPOINT_URL")
    if endpoint_url:
        return boto3.resource("dynamodb", endpoint_url=endpoint_url)
    return boto3.resource("dynamodb")


def get_s3_client():
    """Get S3 client, respecting local endpoint if set."""
    endpoint_url = os.getenv("S3_ENDPOINT_URL")
    if endpoint_url:
        return boto3.client("s3", endpoint_url=endpoint_url)
    return boto3.client("s3")

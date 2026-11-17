"""Lambda handler for generating S3 Presigned Upload URLs.
Configured with SAM Policy Template: S3WritePolicy.
"""

import os
from typing import Any, Dict

try:
    from botocore.exceptions import ClientError
except ImportError:
    class ClientError(Exception):
        pass

from src.common.utils import (
    build_response,
    get_s3_client,
    logger,
    parse_body,
)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handles POST /documents/{id}/upload-url."""
    bucket_name = os.getenv("BUCKET_NAME")
    if not bucket_name:
        logger.error("Environment variable BUCKET_NAME is not set.")
        return build_response(500, {"error": "Server configuration error: missing BUCKET_NAME"})

    path_params = event.get("pathParameters") or {}
    document_id = path_params.get("id")
    if not document_id:
        return build_response(400, {"error": "Path parameter 'id' is required"})

    try:
        body = parse_body(event)
    except ValueError as err:
        return build_response(400, {"error": str(err)})

    file_name = body.get("file_name", "document.pdf")
    content_type = body.get("content_type", "application/octet-stream")
    file_key = f"documents/{document_id}/{file_name}"
    expires_in = int(os.getenv("URL_EXPIRY_SECONDS", "300"))

    s3 = get_s3_client()

    try:
        presigned_url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": bucket_name,
                "Key": file_key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_in,
        )
        logger.info(f"Generated upload URL for {file_key} in bucket {bucket_name}")
    except ClientError as err:
        logger.error(f"Failed to generate presigned URL: {err}")
        return build_response(500, {"error": "Failed to generate presigned upload URL"})

    return build_response(
        200,
        {
            "document_id": document_id,
            "file_key": file_key,
            "upload_url": presigned_url,
            "expires_in_seconds": expires_in,
            "instructions": f"Use HTTP PUT with Content-Type '{content_type}' to upload your file to the upload_url.",
        },
    )

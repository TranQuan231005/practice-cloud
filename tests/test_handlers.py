"""Comprehensive unit tests for Serverless Document Vault handlers using unittest.mock.
Self-contained, requires no external dependencies.
"""

import json
import os
import sys
from unittest.mock import MagicMock

# 1. Setup mock boto3 in sys.modules if not installed
mock_boto3 = MagicMock()
sys.modules["boto3"] = mock_boto3

# Set test environment variables
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["TABLE_NAME"] = "test-documents-table"
os.environ["BUCKET_NAME"] = "test-documents-bucket"

# In-memory storage for DynamoDB mock
_in_memory_dynamodb = {}


class MockTable:
    def __init__(self, table_name):
        self.table_name = table_name

    def put_item(self, Item):
        _in_memory_dynamodb[Item["document_id"]] = Item.copy()
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}

    def get_item(self, Key):
        doc_id = Key.get("document_id")
        item = _in_memory_dynamodb.get(doc_id)
        if item:
            return {"Item": item.copy()}
        return {}

    def scan(self, Limit=50):
        items = list(_in_memory_dynamodb.values())[:Limit]
        return {"Items": items}

    def update_item(self, Key, UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues, ReturnValues="ALL_NEW"):
        doc_id = Key.get("document_id")
        if doc_id not in _in_memory_dynamodb:
            raise Exception(f"Item {doc_id} not found")
        item = _in_memory_dynamodb[doc_id]
        new_status = ExpressionAttributeValues[":status"]
        updated_at = ExpressionAttributeValues[":updated_at"]
        new_history_entries = ExpressionAttributeValues[":new_entry"]

        item["status"] = new_status
        item["updated_at"] = updated_at
        if "history" not in item:
            item["history"] = []
        item["history"].extend(new_history_entries)
        return {"Attributes": item.copy()}


class MockDynamoDBResource:
    def Table(self, name):
        return MockTable(name)


class MockS3Client:
    def generate_presigned_url(self, ClientMethod, Params, ExpiresIn):
        bucket = Params.get("Bucket")
        key = Params.get("Key")
        return f"https://{bucket}.s3.amazonaws.com/{key}?Expires={ExpiresIn}&mock-signature=abc123xyz"


mock_boto3.resource.return_value = MockDynamoDBResource()
mock_boto3.client.return_value = MockS3Client()

from src.handlers import create_document, get_document, get_upload_url, update_status


def setup_function():
    """Clear in-memory storage before each test."""
    _in_memory_dynamodb.clear()


def test_create_document_success():
    """Test creating a document with valid title and owner."""
    event = {
        "body": json.dumps({
            "title": "Cloud Computing Lab 1",
            "owner": "alice@example.com",
            "description": "Practicing SAM and IAM",
        })
    }
    response = create_document.handler(event, None)
    assert response["statusCode"] == 201

    body = json.loads(response["body"])
    assert "document_id" in body
    assert body["title"] == "Cloud Computing Lab 1"
    assert body["owner"] == "alice@example.com"
    assert body["status"] == "PENDING_UPLOAD"
    assert len(body["history"]) == 1
    assert body["history"][0]["status"] == "PENDING_UPLOAD"


def test_create_document_validation_errors():
    """Test validation errors for empty title or owner."""
    # Missing title
    res1 = create_document.handler({"body": json.dumps({"owner": "alice"})}, None)
    assert res1["statusCode"] == 400
    assert "title" in json.loads(res1["body"])["error"]

    # Missing owner
    res2 = create_document.handler({"body": json.dumps({"title": "Test"})}, None)
    assert res2["statusCode"] == 400
    assert "owner" in json.loads(res2["body"])["error"]


def test_get_document_success_and_not_found():
    """Test retrieving an existing document and a non-existent document."""
    # 1. Create document first
    create_event = {
        "body": json.dumps({
            "title": "Test Document",
            "owner": "bob@example.com",
        })
    }
    create_res = create_document.handler(create_event, None)
    doc_id = json.loads(create_res["body"])["document_id"]

    # 2. Get existing document
    get_event = {"pathParameters": {"id": doc_id}}
    get_res = get_document.handler(get_event, None)
    assert get_res["statusCode"] == 200
    doc_body = json.loads(get_res["body"])
    assert doc_body["document_id"] == doc_id
    assert doc_body["title"] == "Test Document"

    # 3. Get non-existent document
    not_found_event = {"pathParameters": {"id": "non-existent-uuid"}}
    not_found_res = get_document.handler(not_found_event, None)
    assert not_found_res["statusCode"] == 404


def test_list_documents():
    """Test listing all documents."""
    # Create two documents
    create_document.handler({"body": json.dumps({"title": "Doc 1", "owner": "user1"})}, None)
    create_document.handler({"body": json.dumps({"title": "Doc 2", "owner": "user2"})}, None)

    list_res = get_document.handler({}, None)
    assert list_res["statusCode"] == 200
    body = json.loads(list_res["body"])
    assert body["count"] == 2
    assert len(body["documents"]) == 2


def test_update_status_for_observability():
    """Test observing and transitioning document lifecycle status."""
    # 1. Create initial document
    create_res = create_document.handler(
        {"body": json.dumps({"title": "Observable Doc", "owner": "carol@example.com"})},
        None,
    )
    doc_id = json.loads(create_res["body"])["document_id"]

    # 2. Transition to PROCESSING
    update_event = {
        "pathParameters": {"id": doc_id},
        "body": json.dumps({
            "status": "PROCESSING",
            "reason": "Document parsing pipeline started",
        }),
    }
    update_res = update_status.handler(update_event, None)
    assert update_res["statusCode"] == 200
    update_body = json.loads(update_res["body"])
    assert update_body["transition"]["from"] == "PENDING_UPLOAD"
    assert update_body["transition"]["to"] == "PROCESSING"

    # Verify document item reflects new status and appended history
    doc = update_body["document"]
    assert doc["status"] == "PROCESSING"
    assert len(doc["history"]) == 2
    assert doc["history"][1]["status"] == "PROCESSING"
    assert doc["history"][1]["reason"] == "Document parsing pipeline started"

    # 3. Transition to ACTIVE
    update_event2 = {
        "pathParameters": {"id": doc_id},
        "body": json.dumps({
            "status": "ACTIVE",
            "reason": "Document verified and published",
        }),
    }
    update_res2 = update_status.handler(update_event2, None)
    assert update_res2["statusCode"] == 200
    assert json.loads(update_res2["body"])["document"]["status"] == "ACTIVE"


def test_update_status_invalid():
    """Test passing an invalid status."""
    create_res = create_document.handler(
        {"body": json.dumps({"title": "Invalid Status Doc", "owner": "dave"})},
        None,
    )
    doc_id = json.loads(create_res["body"])["document_id"]

    bad_event = {
        "pathParameters": {"id": doc_id},
        "body": json.dumps({"status": "SOME_UNKNOWN_STATE"}),
    }
    bad_res = update_status.handler(bad_event, None)
    assert bad_res["statusCode"] == 400
    assert "Invalid status" in json.loads(bad_res["body"])["error"]


def test_get_upload_url_success():
    """Test generating presigned S3 upload URL."""
    event = {
        "pathParameters": {"id": "doc-uuid-456"},
        "body": json.dumps({
            "file_name": "contract.pdf",
            "content_type": "application/pdf",
        }),
    }
    response = get_upload_url.handler(event, None)
    assert response["statusCode"] == 200

    body = json.loads(response["body"])
    assert body["document_id"] == "doc-uuid-456"
    assert body["file_key"] == "documents/doc-uuid-456/contract.pdf"
    assert "upload_url" in body
    assert "https://" in body["upload_url"]
    assert body["expires_in_seconds"] == 300

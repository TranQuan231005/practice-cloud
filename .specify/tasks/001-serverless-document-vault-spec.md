# SPEC-001: Serverless Document Vault (AWS SAM & SAM Policy Templates Practice)

> **Status:** `Approved`  
> **Version:** `1.2.0`  
> **Author:** AI Agent & Engineer  
> **Date:** 2026-11-17  
> **Approved-By:** User (speckit-implement invoked)  
> **Approved-At:** 2026-11-17T07:50:00Z  
> **Approved-Hash:** Approved-By-User  
> **Upstream Spec Kit:** Compatible with Spec Kit v1.0+  
> **Target Path:** `src/` & `template.yaml`

---

## 1. Overview & Objective

### 1.1 Problem Statement
When developing serverless applications with AWS CloudFormation, defining IAM execution roles manually requires writing verbose, repetitive JSON/YAML syntax (`AssumeRolePolicyDocument`, `Policies`, statements with ARNs). This complexity often tempts developers to use broad policies like `AmazonDynamoDBFullAccess` or `AdministratorAccess`.

**AWS SAM Policy Templates** solve this problem by providing pre-packaged, scope-limited policy definitions directly inside the `AWS::Serverless::Function` resource definition under the `Policies` attribute.

This project implements a **Serverless Document Vault** designed specifically to master **AWS SAM Policy Templates** as the primary security abstraction and provide granular observable state transitions (`PENDING_UPLOAD`, `UPLOADED`, `PROCESSING`, `ACTIVE`, `FAILED`, `ARCHIVED`).

### 1.2 User Stories
- **As a Developer practicing AWS SAM**, I want to use SAM Policy Templates directly in `template.yaml` so that I can configure least-privilege IAM permissions cleanly without writing boilerplate CloudFormation IAM roles.
- **As a Developer exploring AWS observability**, I want granular document lifecycle statuses and structured CloudWatch logging so that I can observe state transitions and verify IAM execution behavior.
- **As a Client/User**, I want to:
  - Create document metadata (`POST /documents`).
  - Read document metadata (`GET /documents/{id}` and `GET /documents`).
  - Request an S3 Presigned Upload URL (`POST /documents/{id}/upload-url`).
  - Transition and observe document lifecycle status (`PATCH /documents/{id}/status`).

### 1.3 Scope Boundaries
- **In-Scope (Bắt buộc làm):**
  - **AWS SAM Template (`template.yaml`)**:
    - DynamoDB Table (`DocumentsTable`).
    - S3 Bucket (`DocumentsBucket`).
    - API Gateway HTTP/REST API endpoints.
    - 4 distinct Lambda functions (Python 3.12) configured with **SAM Policy Templates**:
      1. `CreateDocumentFunction`: `DynamoDBCrudPolicy: { TableName: !Ref DocumentsTable }`.
      2. `GetDocumentFunction`: `DynamoDBReadPolicy: { TableName: !Ref DocumentsTable }`.
      3. `GetUploadUrlFunction`: `S3WritePolicy: { BucketName: !Ref DocumentsBucket }`.
      4. `UpdateDocumentStatusFunction`: `DynamoDBCrudPolicy: { TableName: !Ref DocumentsTable }` (allows observing status transitions).
  - **Observable Lifecycle States**:
    - `PENDING_UPLOAD`, `UPLOADED`, `PROCESSING`, `ACTIVE`, `FAILED`, `ARCHIVED`.
  - **Educational Lab Guide & Local Emulation**:
    - Commands and mock events for `sam local invoke` and `sam local start-api` using Docker.
    - Automated test suite with `pytest` and `moto`.
- **Out-of-Scope:**
  - Cognito user authentication.
  - Multi-region replication.

---

## 2. Data Models & Interface Contracts

### 2.1 Domain Models (Python)

```python
from typing import TypedDict, Optional
from enum import Enum

class DocumentStatus(str, Enum):
    PENDING_UPLOAD = "PENDING_UPLOAD"
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"

class DocumentCreateRequest(TypedDict):
    title: str          # Min 1, Max 120 chars
    owner: str          # Email or username identifier
    description: Optional[str]

class DocumentStatusUpdateRequest(TypedDict):
    status: DocumentStatus
    reason: Optional[str]

class DocumentMetadata(TypedDict):
    document_id: str    # UUID v4
    title: str
    owner: str
    description: str
    status: DocumentStatus
    file_key: Optional[str]
    created_at: str     # ISO 8601 UTC
    updated_at: str     # ISO 8601 UTC
```

### 2.2 API Gateway Contracts

#### Endpoint 1: `POST /documents` (Create Document)
- **SAM Policy**: `DynamoDBCrudPolicy: { TableName: !Ref DocumentsTable }`
- **Initial Status**: `PENDING_UPLOAD`

#### Endpoint 2: `GET /documents/{id}` and `GET /documents` (Read Documents)
- **SAM Policy**: `DynamoDBReadPolicy: { TableName: !Ref DocumentsTable }`

#### Endpoint 3: `POST /documents/{id}/upload-url` (Generate Presigned S3 Upload URL)
- **SAM Policy**: `S3WritePolicy: { BucketName: !Ref DocumentsBucket }`

#### Endpoint 4: `PATCH /documents/{id}/status` (Update Status for Observability)
- **SAM Policy**: `DynamoDBCrudPolicy: { TableName: !Ref DocumentsTable }`
- **Body**: `{"status": "PROCESSING", "reason": "Verifying file checksum"}`
- **Success Response (`200 OK`)**: Updated document metadata with new status and updated timestamp.

---

## 3. Change Log

| Version | Date | Author | Summary |
| :--- | :--- | :--- | :--- |
| `1.0.0` | `2026-11-17` | AI Agent & Engineer | Initial draft with fine-grained custom IAM roles. |
| `1.1.0` | `2026-11-17` | AI Agent & Engineer | Switched primary approach to SAM Policy Templates. |
| `1.2.0` | `2026-11-17` | AI Agent & Engineer | Added expanded document status lifecycle (`PENDING_UPLOAD`, `UPLOADED`, `PROCESSING`, `ACTIVE`, `FAILED`, `ARCHIVED`) and `PATCH /documents/{id}/status` for observability. |

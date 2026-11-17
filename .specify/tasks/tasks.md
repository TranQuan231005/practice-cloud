# Implementation Tasks: Serverless Document Vault (AWS SAM & Policy Templates)

> Spec: [.specify/tasks/001-serverless-document-vault-spec.md](file:///home/tranquan/Project/practice-cloud-computuing/.specify/tasks/001-serverless-document-vault-spec.md)  
> Target: AWS SAM + Python 3.12 + Boto3 + Observability Statuses

---

## Task Progress Checklist

### Phase 1: Setup & Scaffold
- [x] **TASK-1.1**: Create project `.gitignore` and `.dockerignore` for Python & AWS SAM.
- [x] **TASK-1.2**: Define dependencies in `requirements.txt` (boto3) and `requirements-dev.txt` (pytest, moto).
- [x] **TASK-1.3**: Scaffold directory hierarchy (`src/common/`, `src/handlers/`, `events/`, `tests/`).

### Phase 2: Domain Models & Core Utilities
- [x] **TASK-2.1**: Implement `src/common/models.py` with expanded observable statuses (`PENDING_UPLOAD`, `UPLOADED`, `PROCESSING`, `ACTIVE`, `FAILED`, `ARCHIVED`).
- [x] **TASK-2.2**: Implement `src/common/utils.py` for structured API Gateway JSON responses, error formatting, and structured logging for observability.

### Phase 3: Lambda Handlers
- [x] **TASK-3.1**: Implement `src/handlers/create_document.py` (`POST /documents`).
- [x] **TASK-3.2**: Implement `src/handlers/get_document.py` (`GET /documents` and `GET /documents/{id}`).
- [x] **TASK-3.3**: Implement `src/handlers/get_upload_url.py` (`POST /documents/{id}/upload-url`).
- [x] **TASK-3.4**: Implement `src/handlers/update_status.py` (`PATCH /documents/{id}/status`) to observe and control lifecycle transitions.

### Phase 4: AWS SAM Infrastructure as Code
- [x] **TASK-4.1**: Author `template.yaml` defining DynamoDB table, S3 bucket, and 4 Lambda functions with SAM Policy Templates (`DynamoDBCrudPolicy`, `DynamoDBReadPolicy`, `S3WritePolicy`).
- [x] **TASK-4.2**: Generate mock event payloads in `events/` for `sam local invoke` testing.

### Phase 5: Automated Testing & Verification
- [x] **TASK-5.1**: Author comprehensive test suite in `tests/test_handlers.py` using `pytest` and `moto`.
- [x] **TASK-5.2**: Run pytest to verify all functional paths, status transitions, and error handling pass.

### Phase 6: Documentation & Observability Lab Guide
- [x] **TASK-6.1**: Author `README.md` with hands-on lab exercises: inspecting compiled IAM roles in `.aws-sam/build/template.yaml`, running `sam local invoke`, and observing state transitions.

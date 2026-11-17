"""Domain models and data definitions for Serverless Document Vault."""

from enum import Enum
from typing import TypedDict, Optional, List


class DocumentStatus(str, Enum):
    """Lifecycle statuses of a document for observability."""
    PENDING_UPLOAD = "PENDING_UPLOAD"  # Metadata created, awaiting S3 file upload
    UPLOADED = "UPLOADED"              # File uploaded to S3
    PROCESSING = "PROCESSING"          # Inspecting, indexing, or parsing file
    ACTIVE = "ACTIVE"                  # Verified and ready for consumption
    FAILED = "FAILED"                  # Validation or processing error occurred
    ARCHIVED = "ARCHIVED"              # Soft-deleted or archived document


VALID_STATUS_TRANSITIONS = {
    DocumentStatus.PENDING_UPLOAD: [DocumentStatus.UPLOADED, DocumentStatus.FAILED, DocumentStatus.ARCHIVED],
    DocumentStatus.UPLOADED: [DocumentStatus.PROCESSING, DocumentStatus.FAILED, DocumentStatus.ARCHIVED],
    DocumentStatus.PROCESSING: [DocumentStatus.ACTIVE, DocumentStatus.FAILED, DocumentStatus.ARCHIVED],
    DocumentStatus.ACTIVE: [DocumentStatus.PROCESSING, DocumentStatus.ARCHIVED],
    DocumentStatus.FAILED: [DocumentStatus.PROCESSING, DocumentStatus.ARCHIVED],
    DocumentStatus.ARCHIVED: [DocumentStatus.ACTIVE],
}


class DocumentCreateRequest(TypedDict, total=False):
    title: str
    owner: str
    description: Optional[str]


class DocumentStatusUpdateRequest(TypedDict, total=False):
    status: str
    reason: Optional[str]


class StatusHistoryEntry(TypedDict, total=False):
    status: str
    changed_at: str
    reason: Optional[str]


class DocumentMetadata(TypedDict, total=False):
    document_id: str
    title: str
    owner: str
    description: str
    status: str
    file_key: Optional[str]
    created_at: str
    updated_at: str
    history: List[StatusHistoryEntry]

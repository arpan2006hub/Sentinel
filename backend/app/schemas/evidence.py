"""Pydantic schemas for Evidence Management and Integrity Verification."""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class EvidenceResponse(BaseModel):
    """Metadata response for an ingested evidence item."""
    evidence_id: str
    case_id: str
    file_name: str
    file_hash: str = Field(description="SHA-256 integrity hash formatted as sha256:...")
    file_size_bytes: int
    source_type: str = Field(description="endpoint_log, cctv_video, auth_log, pdf_document, badge_log, etc.")
    processing_status: str = Field(default="pending", description="pending, processing, processed, error")
    ingested_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceListResponse(BaseModel):
    """List of evidence items associated with a case or repository."""
    evidence: list[EvidenceResponse]
    total: int


class EvidenceVerifyResponse(BaseModel):
    """Cryptographic integrity verification result."""
    evidence_id: str
    file_name: str
    stored_hash: str
    computed_hash: str
    integrity: str = Field(description="'verified' if hashes match, 'failed' otherwise")
    checked_at: str
    message: Optional[str] = None


class EvidenceAuditRecord(BaseModel):
    """Append-only audit trail entry for evidence chain of custody."""
    audit_id: str
    evidence_id: str
    case_id: str
    action: str = Field(description="ingested, verified, accessed, analysis_started, deleted")
    actor: str = Field(default="system")
    timestamp: str
    details: dict[str, Any] = Field(default_factory=dict)


"""Evidence Ingestion and Cryptographic Verification API Router."""

from __future__ import annotations

import json
from typing import Optional
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

from app.schemas.evidence import (
    EvidenceAuditRecord,
    EvidenceListResponse,
    EvidenceResponse,
    EvidenceVerifyResponse,
)
from app.services.case_service import CaseService
from app.services.evidence_service import EvidenceService

router = APIRouter(prefix="/evidence", tags=["Evidence"])


@router.post(
    "",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and register evidence",
    description=(
        "Uploads a binary evidence file (CCTV video, log file, PDF, etc.), computes its "
        "cryptographic SHA-256 fingerprint, stores it in the local evidence store, and "
        "appends an immutable chain-of-custody audit log."
    ),
)
async def upload_evidence(
    case_id: str = Form(..., description="Target investigation case ID"),
    source_type: str = Form("general", description="Evidence category (cctv_video, auth_log, pdf_document, etc.)"),
    file: UploadFile = File(..., description="Binary evidence file"),
    metadata: Optional[str] = Form(None, description="Optional JSON-encoded metadata string"),
) -> EvidenceResponse:
    # Verify case exists
    case_svc = CaseService.get_instance()
    case = case_svc.get_case(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target case with ID '{case_id}' does not exist.",
        )

    parsed_meta: dict = {}
    if metadata:
        try:
            parsed_meta = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provided metadata is not valid JSON.",
            )

    evidence_svc = EvidenceService.get_instance()
    try:
        return await evidence_svc.ingest_upload(
            case_id=case_id,
            file=file,
            source_type=source_type,
            metadata=parsed_meta,
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest evidence: {err}",
        )


@router.get(
    "",
    response_model=EvidenceListResponse,
    summary="List evidence items",
    description="Returns all registered evidence items, optionally filtered by case ID.",
)
async def list_evidence(
    case_id: Optional[str] = Query(None, description="Optional case ID filter"),
) -> EvidenceListResponse:
    service = EvidenceService.get_instance()
    return service.list_evidence(case_id=case_id)


@router.get(
    "/{evidence_id}",
    response_model=EvidenceResponse,
    summary="Get evidence metadata",
    description="Retrieves metadata, source category, and stored SHA-256 hash for an evidence record.",
)
async def get_evidence(evidence_id: str) -> EvidenceResponse:
    service = EvidenceService.get_instance()
    ev = service.get_evidence(evidence_id)
    if not ev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence with ID '{evidence_id}' was not found.",
        )
    return ev


@router.get(
    "/{evidence_id}/verify",
    response_model=EvidenceVerifyResponse,
    summary="Verify evidence integrity (SHA-256)",
    description=(
        "Performs a live cryptographic verification by re-computing the SHA-256 hash of the "
        "evidence file on disk and comparing it to the original hash recorded at ingestion. "
        "Records an immutable audit entry."
    ),
)
async def verify_evidence(evidence_id: str) -> EvidenceVerifyResponse:
    service = EvidenceService.get_instance()
    result = service.verify_evidence(evidence_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence with ID '{evidence_id}' was not found.",
        )
    return result


@router.get(
    "/{evidence_id}/audit",
    response_model=list[EvidenceAuditRecord],
    summary="Get chain-of-custody audit log",
    description="Retrieves the complete immutable audit trail of actions taken on this evidence item.",
)
async def get_evidence_audit(evidence_id: str) -> list[EvidenceAuditRecord]:
    service = EvidenceService.get_instance()
    ev = service.get_evidence(evidence_id)
    if not ev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence with ID '{evidence_id}' was not found.",
        )
    return service.get_audit_trail(evidence_id)


@router.delete(
    "/{evidence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete evidence",
    description="Deletes an evidence file and metadata while preserving audit logging.",
)
async def delete_evidence(evidence_id: str) -> None:
    service = EvidenceService.get_instance()
    deleted = service.delete_evidence(evidence_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence with ID '{evidence_id}' was not found.",
        )

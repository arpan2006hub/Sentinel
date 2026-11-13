"""Evidence Ingestion and Cryptographic Verification API Router."""

from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from ai.processing.router import SOURCE_TYPES
from app.api.cases import require_case
from app.schemas.evidence import (
    AuditChainVerifyResponse,
    EvidenceAuditRecord,
    EvidenceListResponse,
    EvidenceResponse,
    EvidenceVerifyResponse,
    SourceTypeInfo,
)
from app.services.evidence_service import EvidenceService, UploadTooLargeError

router = APIRouter(prefix="/evidence", tags=["Evidence"])


def _require_evidence(evidence_id: str) -> EvidenceResponse:
    ev = EvidenceService.get_instance().get_evidence(evidence_id)
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence with ID '{evidence_id}' was not found.")
    return ev


@router.get("/source-types", response_model=list[SourceTypeInfo],
            summary="Supported evidence source types (for the upload form)")
def list_source_types() -> list[SourceTypeInfo]:
    return [SourceTypeInfo(source_type=k, **v) for k, v in SOURCE_TYPES.items()]


@router.post(
    "",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and register evidence",
    description=(
        "Uploads an evidence file, computes its SHA-256 fingerprint, stores it in the local evidence store and "
        "appends a hash-chained audit record. Optional `metadata` (JSON string) keys used by the analysis: "
        "`recorded_at` (ISO time of the first video frame / document date) and `location_id` (camera zone, "
        "host location)."
    ),
)
async def upload_evidence(
    case_id: str = Form(..., description="Target investigation case ID"),
    source_type: str = Form("general", description="See GET /api/evidence/source-types"),
    file: UploadFile = File(..., description="Evidence file"),
    metadata: Optional[str] = Form(None, description='JSON object, e.g. {"recorded_at": "2026-01-16T21:58:00Z"}'),
) -> EvidenceResponse:
    require_case(case_id)
    if source_type not in SOURCE_TYPES:
        raise HTTPException(status_code=422,
                            detail=f"Unknown source_type '{source_type}'. Allowed: {sorted(SOURCE_TYPES)}")
    parsed_meta: dict = {}
    if metadata:
        try:
            parsed_meta = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provided metadata is not valid JSON.")
        if not isinstance(parsed_meta, dict):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="metadata must be a JSON object.")
    try:
        return await EvidenceService.get_instance().ingest_upload(
            case_id=case_id, file=file, source_type=source_type, metadata=parsed_meta,
        )
    except UploadTooLargeError as err:
        raise HTTPException(status_code=413, detail=str(err))


@router.get("", response_model=EvidenceListResponse, summary="List evidence items")
def list_evidence(case_id: Optional[str] = Query(None, description="Optional case ID filter")) -> EvidenceListResponse:
    return EvidenceService.get_instance().list_evidence(case_id=case_id)


@router.get("/{evidence_id}", response_model=EvidenceResponse, summary="Get evidence metadata")
def get_evidence(evidence_id: str) -> EvidenceResponse:
    return _require_evidence(evidence_id)


@router.get("/{evidence_id}/file", summary="Download the stored evidence file (audited)",
            response_class=FileResponse)
def download_evidence(evidence_id: str) -> FileResponse:
    ev = _require_evidence(evidence_id)
    service = EvidenceService.get_instance()
    path = service.get_evidence_file_path(evidence_id)
    if not path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file is missing from storage.")
    service.record_access(evidence_id, purpose="download")
    return FileResponse(path, filename=ev.file_name)


@router.get("/{evidence_id}/verify", response_model=EvidenceVerifyResponse,
            summary="Verify evidence integrity (SHA-256)")
def verify_evidence(evidence_id: str) -> EvidenceVerifyResponse:
    result = EvidenceService.get_instance().verify_evidence(evidence_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence with ID '{evidence_id}' was not found.")
    return result


@router.get("/{evidence_id}/audit", response_model=list[EvidenceAuditRecord],
            summary="Get chain-of-custody audit log (also available after deletion)")
def get_evidence_audit(evidence_id: str) -> list[EvidenceAuditRecord]:
    service = EvidenceService.get_instance()
    if not service.has_audit(evidence_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No audit records for evidence '{evidence_id}'.")
    return service.get_audit_trail(evidence_id)


@router.get("/{evidence_id}/audit/verify", response_model=AuditChainVerifyResponse,
            summary="Verify the audit hash chain (detects edited or removed audit records)")
def verify_evidence_audit(evidence_id: str) -> AuditChainVerifyResponse:
    service = EvidenceService.get_instance()
    if not service.has_audit(evidence_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No audit records for evidence '{evidence_id}'.")
    return service.verify_audit_chain(evidence_id)


@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete evidence (file + metadata; audit trail is preserved)")
def delete_evidence(evidence_id: str) -> None:
    if not EvidenceService.get_instance().delete_evidence(evidence_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence with ID '{evidence_id}' was not found.")

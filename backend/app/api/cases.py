"""Case Management API Router."""

from __future__ import annotations

from collections import Counter
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.cases import CaseCreate, CaseListResponse, CaseResponse, CaseSummaryResponse, CaseStatus, CaseUpdate
from app.services.analysis_service import AnalysisService
from app.services.case_service import CaseService
from app.services.evidence_service import EvidenceService

router = APIRouter(prefix="/cases", tags=["Cases"])


def require_case(case_id: str) -> CaseResponse:
    """Return the case or raise 404 (shared by other routers)."""
    case = CaseService.get_instance().get_case(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case with ID '{case_id}' was not found.")
    return case


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED,
             summary="Create a new investigation case")
async def create_case(case_in: CaseCreate) -> CaseResponse:
    return CaseService.get_instance().create_case(case_in)


@router.get("", response_model=CaseListResponse, summary="List investigation cases")
async def list_cases(
    status_filter: Optional[CaseStatus] = Query(None, alias="status", description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> CaseListResponse:
    return CaseService.get_instance().list_cases(status=status_filter, page=page, page_size=page_size)


@router.get("/{case_id}", response_model=CaseResponse, summary="Get case details")
async def get_case(case_id: str) -> CaseResponse:
    return require_case(case_id)


@router.get("/{case_id}/summary", response_model=CaseSummaryResponse,
            summary="Case dashboard overview (counts, latest run, top suspects)")
async def get_case_summary(case_id: str, top: int = Query(5, ge=1, le=50)) -> CaseSummaryResponse:
    case = require_case(case_id)
    analysis = AnalysisService.get_instance()
    runs = analysis.list_runs(case_id).runs
    summary: dict[str, Any] = analysis.read_output(case_id, "summary") or {}
    suspects = analysis.read_output(case_id, "suspects") or []
    contradictions = analysis.read_output(case_id, "contradictions") or []
    evidence = EvidenceService.get_instance().list_evidence(case_id).evidence
    return CaseSummaryResponse(
        case=case,
        analysis=runs[0].model_dump() if runs else None,
        summary=summary,
        top_suspects=suspects[:top],
        anomalies_by_severity=dict(Counter(c.get("severity", "unknown") for c in contradictions)),
        evidence_by_status=dict(Counter(e.processing_status for e in evidence)),
    )


@router.get("/{case_id}/suspects", summary="Ranked entities with reasons and evidence references")
async def get_suspects(case_id: str) -> dict[str, Any]:
    require_case(case_id)
    suspects = AnalysisService.get_instance().read_output(case_id, "suspects") or []
    return {"case_id": case_id, "suspects": suspects, "total": len(suspects)}


@router.patch("/{case_id}", response_model=CaseResponse, summary="Update case")
async def update_case(case_id: str, case_update: CaseUpdate) -> CaseResponse:
    updated = CaseService.get_instance().update_case(case_id, case_update)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case with ID '{case_id}' was not found.")
    return updated


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete case, its evidence files and analysis outputs (audit trail is kept)")
async def delete_case(case_id: str) -> None:
    if not CaseService.get_instance().delete_case(case_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case with ID '{case_id}' was not found.")

"""Anomalies and Contradictions API Router."""

from __future__ import annotations

from typing import Any, Literal, Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.api.cases import require_case
from app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/anomalies", tags=["Anomalies"])

Severity = Literal["low", "medium", "high", "critical"]


@router.get(
    "/{case_id}",
    summary="List anomalies / contradictions for a case",
    description="Types: impossible_travel, uncredentialed_presence, denied_access_then_activity, after_hours_activity.",
)
async def list_anomalies(
    case_id: str,
    severity: Optional[Severity] = Query(None),
    type: Optional[str] = Query(None, description="Filter by anomaly type"),
    entity: Optional[str] = Query(None, description="Filter by canonical entity"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    require_case(case_id)
    items: list[dict[str, Any]] = AnalysisService.get_instance().read_output(case_id, "contradictions") or []
    if severity:
        items = [c for c in items if c.get("severity") == severity]
    if type:
        items = [c for c in items if c.get("type") == type]
    if entity:
        items = [c for c in items if c.get("entity") == entity]
    offset = (page - 1) * page_size
    return {"case_id": case_id, "anomalies": items[offset: offset + page_size], "total": len(items),
            "page": page, "page_size": page_size}


@router.get("/{case_id}/{anomaly_id}", summary="Anomaly detail with the supporting events")
async def get_anomaly_detail(case_id: str, anomaly_id: str) -> dict[str, Any]:
    require_case(case_id)
    service = AnalysisService.get_instance()
    items: list[dict[str, Any]] = service.read_output(case_id, "contradictions") or []
    anomaly = next((c for c in items if c.get("anomaly_id") == anomaly_id), None)
    if not anomaly:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Anomaly '{anomaly_id}' was not found in case '{case_id}'.")
    timeline = service.read_output(case_id, "timeline") or {}
    wanted = set(anomaly.get("event_ids", []))
    events = [e for e in timeline.get("events", []) if e.get("event_id") in wanted]
    return {**anomaly, "case_id": case_id, "events": events,
            "evidence_ids": sorted({e["source_id"] for e in events if e.get("source_id")})}

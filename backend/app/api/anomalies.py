"""Anomalies and Contradictions API Router."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.services.case_service import CaseService

router = APIRouter(prefix="/anomalies", tags=["Anomalies"])


@router.get(
    "/{case_id}",
    summary="List anomalies and contradictions for a case",
    description="Returns cross-modality contradictions (impossible travel, uncredentialed presence) and anomalies.",
)
async def list_anomalies(
    case_id: str,
    severity: Optional[str] = Query(None, description="Filter by severity: low, medium, high, critical"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> dict[str, Any]:
    case_svc = CaseService.get_instance()
    case = case_svc.get_case(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found.",
        )

    contra_file = Path("artifacts/correlation/contradictions.json")
    contradictions: list[dict[str, Any]] = []
    if contra_file.exists():
        try:
            contradictions = json.loads(contra_file.read_text(encoding="utf-8"))
        except Exception:
            contradictions = []

    if severity:
        contradictions = [c for c in contradictions if c.get("severity") == severity]

    offset = (page - 1) * page_size
    paginated = contradictions[offset : offset + page_size]

    return {
        "case_id": case_id,
        "anomalies": paginated,
        "total": len(contradictions),
        "page": page,
        "page_size": page_size,
    }


@router.get(
    "/{anomaly_id}/detail",
    summary="Get anomaly detail",
    description="Fetches full supporting evidence and contradictory context for an anomaly.",
)
async def get_anomaly_detail(anomaly_id: str) -> dict[str, Any]:
    contra_file = Path("artifacts/correlation/contradictions.json")
    if not contra_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly '{anomaly_id}' was not found.",
        )

    try:
        items = json.loads(contra_file.read_text(encoding="utf-8"))
        for item in items:
            if item.get("type") == anomaly_id or str(item.get("event_ids", [""])) == anomaly_id:
                return item
    except Exception:
        pass

    return {
        "anomaly_id": anomaly_id,
        "status": "recorded",
        "description": "Cross-modal investigative anomaly signal.",
    }

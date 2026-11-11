"""Timeline API Router for Unified Multimodal Chronological Events."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.services.case_service import CaseService

router = APIRouter(prefix="/timeline", tags=["Timeline"])


@router.get(
    "/{case_id}",
    summary="Get unified event timeline",
    description="Retrieves chronological multimodal events for an investigation case with optional filtering.",
)
async def get_timeline(
    case_id: str,
    from_time: Optional[str] = Query(None, alias="from", description="Filter events on or after this ISO timestamp"),
    to_time: Optional[str] = Query(None, alias="to", description="Filter events on or before this ISO timestamp"),
    actor_id: Optional[str] = Query(None, description="Filter by canonical actor ID (e.g. user_007)"),
    source_type: Optional[str] = Query(None, description="Filter by modality (cyber, video, document, badge)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Page size"),
) -> dict[str, Any]:
    # Verify case exists
    case_svc = CaseService.get_instance()
    case = case_svc.get_case(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found.",
        )

    # Load correlation timeline
    timeline_file = Path("artifacts/correlation/timeline.json")
    if not timeline_file.exists():
        # Fallback to empty timeline if analysis hasn't run yet
        return {
            "case_id": case_id,
            "events": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "clusters": [],
            "contradictions": [],
        }

    try:
        timeline_data = json.loads(timeline_file.read_text(encoding="utf-8"))
        events: list[dict[str, Any]] = timeline_data.get("events", [])
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load timeline data: {err}",
        )

    # Filter events
    filtered = events
    if actor_id:
        filtered = [
            e for e in filtered
            if (e.get("canonical_entity") == actor_id or e.get("actor_id") == actor_id)
        ]
    if source_type:
        filtered = [
            e for e in filtered
            if (e.get("source") == source_type or e.get("source_type") == source_type)
        ]
    if from_time:
        filtered = [e for e in filtered if (e.get("timestamp") or "") >= from_time]
    if to_time:
        filtered = [e for e in filtered if (e.get("timestamp") or "") <= to_time]

    total = len(filtered)
    offset = (page - 1) * page_size
    paginated = filtered[offset : offset + page_size]

    return {
        "case_id": case_id,
        "events": paginated,
        "total": total,
        "page": page,
        "page_size": page_size,
        "contradictions": timeline_data.get("contradictions", []),
        "summary": timeline_data.get("summary", {}),
    }

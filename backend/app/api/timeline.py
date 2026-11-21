"""Timeline API Router — per-case chronological multimodal events and incident clusters."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

from ai.correlation.timeline.builder import IncidentTimelineBuilder
from app.api.cases import require_case
from app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/timeline", tags=["Timeline"])


def _parse_bound(value: Optional[str], name: str):
    if value is None:
        return None
    parsed = IncidentTimelineBuilder.parse_timestamp(value)
    if parsed is None:
        raise HTTPException(status_code=422, detail=f"'{name}' is not an ISO 8601 timestamp")
    return parsed


@router.get("/{case_id}", summary="Get the unified event timeline of a case")
async def get_timeline(
    case_id: str,
    from_time: Optional[str] = Query(None, alias="from", description="Events at or after this ISO timestamp"),
    to_time: Optional[str] = Query(None, alias="to", description="Events at or before this ISO timestamp"),
    actor_id: Optional[str] = Query(None, description="Canonical entity, e.g. user_007"),
    source: Optional[str] = Query(None, description="Modality: cyber, physical, video, document"),
    source_type: Optional[str] = Query(None, description="e.g. endpoint_log, badge_log, cctv_video, text_document"),
    flagged_only: bool = Query(False, description="Only events flagged by a model (prediction == 1)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
) -> dict[str, Any]:
    require_case(case_id)
    timeline = AnalysisService.get_instance().read_output(case_id, "timeline")
    if timeline is None:
        return {"case_id": case_id, "analyzed": False, "events": [], "total": 0, "page": page,
                "page_size": page_size, "summary": {}, "skipped_events": []}

    start, end = _parse_bound(from_time, "from"), _parse_bound(to_time, "to")
    events: list[dict[str, Any]] = timeline.get("events", [])

    def keep(e: dict[str, Any]) -> bool:
        if actor_id and actor_id not in (e.get("canonical_entity"), e.get("actor_id")):
            return False
        if source and e.get("source") != source:
            return False
        if source_type and e.get("source_type") != source_type:
            return False
        if flagged_only and e.get("prediction") != 1:
            return False
        if start or end:
            t = IncidentTimelineBuilder.parse_timestamp(e.get("timestamp"))
            if t is None or (start and t < start) or (end and t > end):
                return False
        return True

    filtered = [e for e in events if keep(e)]
    offset = (page - 1) * page_size
    return {
        "case_id": case_id,
        "analyzed": True,
        "events": filtered[offset: offset + page_size],
        "total": len(filtered),
        "page": page,
        "page_size": page_size,
        "summary": timeline.get("summary", {}),
        "skipped_events": timeline.get("skipped_events", []),
    }


@router.get("/{case_id}/clusters", summary="Incident clusters (temporal windows) of a case")
async def get_clusters(
    case_id: str,
    cross_modal_only: bool = Query(False, description="Only clusters spanning more than one modality"),
    include_events: bool = Query(False, description="Embed full events (otherwise only event_ids)"),
) -> dict[str, Any]:
    require_case(case_id)
    clusters = AnalysisService.get_instance().read_output(case_id, "events") or []
    if cross_modal_only:
        clusters = [c for c in clusters if c.get("is_cross_modal")]
    if not include_events:
        clusters = [{k: v for k, v in c.items() if k != "events"} for c in clusters]
    return {"case_id": case_id, "clusters": clusters, "total": len(clusters)}

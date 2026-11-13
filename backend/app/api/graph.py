"""Evidence Graph API Router."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Query

from app.api.cases import require_case
from app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/graph", tags=["Graph"])


@router.get(
    "/{case_id}",
    summary="Get the entity/evidence relationship graph of a case",
    description=(
        "`format=standard` returns {nodes, edges, metrics}; `format=cytoscape` returns "
        "{elements: {nodes, edges}} ready for Cytoscape.js. Node types: user, event, location, document, "
        "object, evidence, anomaly."
    ),
)
async def get_evidence_graph(
    case_id: str,
    format: Literal["standard", "cytoscape"] = Query("standard"),
) -> dict[str, Any]:
    require_case(case_id)
    service = AnalysisService.get_instance()
    data = service.read_output(case_id, "cytoscape" if format == "cytoscape" else "graph")
    if data is None:
        empty = ({"elements": {"nodes": [], "edges": []}} if format == "cytoscape"
                 else {"nodes": [], "edges": [], "metrics": {"total_nodes": 0, "total_edges": 0}})
        return {"case_id": case_id, "analyzed": False, **empty}
    return {"case_id": case_id, "analyzed": True, **data}

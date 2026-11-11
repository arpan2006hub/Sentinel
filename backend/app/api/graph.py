"""Evidence Graph API Router."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.services.case_service import CaseService

router = APIRouter(prefix="/graph", tags=["Graph"])


@router.get(
    "/{case_id}",
    summary="Get entity relationship graph",
    description="Retrieves the multi-modal evidence graph (nodes and directed edges) for visualization.",
)
async def get_evidence_graph(
    case_id: str,
    format: str = Query("standard", description="Graph representation format: 'standard' or 'cytoscape'"),
) -> dict[str, Any]:
    # Verify case exists
    case_svc = CaseService.get_instance()
    case = case_svc.get_case(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found.",
        )

    if format.lower() == "cytoscape":
        graph_file = Path("artifacts/correlation/cytoscape_graph.json")
    else:
        graph_file = Path("artifacts/correlation/evidence_graph.json")

    if not graph_file.exists():
        return {
            "case_id": case_id,
            "nodes": [],
            "edges": [],
            "metrics": {"total_nodes": 0, "total_edges": 0},
        }

    try:
        data = json.loads(graph_file.read_text(encoding="utf-8"))
        if format.lower() == "cytoscape":
            return {"case_id": case_id, **data}
        return {"case_id": case_id, **data}
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read graph data: {err}",
        )

"""
graph.py — Evidence Graph API Router (Placeholder)

Planned endpoints:
    GET    /graph/{case_id}

See docs/architecture/api-contract.md for the full API contract.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/graph", tags=["Graph"])

# TODO: Implement graph endpoints
# @router.get("/{case_id}")
# async def get_evidence_graph(...): ...


@router.get("/{case_id}", status_code=501)
async def get_evidence_graph(case_id: str):
    """NOT YET IMPLEMENTED — placeholder to show route exists."""
    return {"detail": "Not implemented", "planned_endpoint": f"GET /graph/{case_id}"}
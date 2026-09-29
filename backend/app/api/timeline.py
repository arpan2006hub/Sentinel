"""
timeline.py — Timeline API Router (Placeholder)

Planned endpoints:
    GET    /timeline/{case_id}

See docs/architecture/api-contract.md for the full API contract.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/timeline", tags=["Timeline"])

# TODO: Implement timeline endpoints
# @router.get("/{case_id}")
# async def get_timeline(...): ...


@router.get("/{case_id}", status_code=501)
async def get_timeline(case_id: str):
    """NOT YET IMPLEMENTED — placeholder to show route exists."""
    return {"detail": "Not implemented", "planned_endpoint": f"GET /timeline/{case_id}"}
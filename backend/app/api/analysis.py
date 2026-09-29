"""
analysis.py — Analysis API Router (Placeholder)

Planned endpoints:
    POST   /analysis/start
    GET    /analysis/{analysis_run_id}
    GET    /analysis/{analysis_run_id}/status

See docs/architecture/api-contract.md for the full API contract.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/analysis", tags=["Analysis"])

# TODO: Implement analysis endpoints
# @router.post("/start", status_code=202)
# async def start_analysis(...): ...
#
# @router.get("/{analysis_run_id}")
# async def get_analysis_run(...): ...


@router.post("/start", status_code=501)
async def start_analysis():
    """NOT YET IMPLEMENTED — placeholder to show route exists."""
    return {"detail": "Not implemented", "planned_endpoint": "POST /analysis/start"}


@router.get("/{analysis_run_id}", status_code=501)
async def get_analysis_run(analysis_run_id: str):
    """NOT YET IMPLEMENTED — placeholder to show route exists."""
    return {"detail": "Not implemented", "planned_endpoint": f"GET /analysis/{analysis_run_id}"}
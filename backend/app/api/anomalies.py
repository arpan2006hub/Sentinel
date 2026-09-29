"""
anomalies.py — Anomalies API Router (Placeholder)

Planned endpoints:
    GET    /anomalies/{case_id}
    GET    /anomalies/{anomaly_id}/detail

See docs/architecture/api-contract.md for the full API contract.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/anomalies", tags=["Anomalies"])

# TODO: Implement anomalies endpoints
# @router.get("/{case_id}")
# async def list_anomalies(...): ...
#
# @router.get("/{anomaly_id}/detail")
# async def get_anomaly_detail(...): ...


@router.get("/{case_id}", status_code=501)
async def list_anomalies(case_id: str):
    """NOT YET IMPLEMENTED — placeholder to show route exists."""
    return {"detail": "Not implemented", "planned_endpoint": f"GET /anomalies/{case_id}"}


@router.get("/{anomaly_id}/detail", status_code=501)
async def get_anomaly_detail(anomaly_id: str):
    """NOT YET IMPLEMENTED — placeholder to show route exists."""
    return {"detail": "Not implemented", "planned_endpoint": f"GET /anomalies/{anomaly_id}/detail"}
"""
evidence.py — Evidence API Router (Placeholder)

Planned endpoints:
    POST   /evidence
    GET    /evidence/{evidence_id}
    GET    /evidence/{evidence_id}/verify
    DELETE /evidence/{evidence_id}

See docs/architecture/api-contract.md for the full API contract.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/evidence", tags=["Evidence"])

# TODO: Implement evidence endpoints
# @router.post("", status_code=201)
# async def upload_evidence(...): ...
#
# @router.get("/{evidence_id}")
# async def get_evidence(...): ...
#
# @router.get("/{evidence_id}/verify")
# async def verify_evidence(...): ...
#
# @router.delete("/{evidence_id}")
# async def delete_evidence(...): ...


@router.post("", status_code=501)
async def upload_evidence():
    """NOT YET IMPLEMENTED — placeholder to show route exists."""
    return {"detail": "Not implemented", "planned_endpoint": "POST /evidence"}


@router.get("/{evidence_id}", status_code=501)
async def get_evidence(evidence_id: str):
    """NOT YET IMPLEMENTED — placeholder to show route exists."""
    return {"detail": "Not implemented", "planned_endpoint": f"GET /evidence/{evidence_id}"}


@router.get("/{evidence_id}/verify", status_code=501)
async def verify_evidence(evidence_id: str):
    """NOT YET IMPLEMENTED — placeholder to show route exists."""
    return {"detail": "Not implemented", "planned_endpoint": f"GET /evidence/{evidence_id}/verify"}
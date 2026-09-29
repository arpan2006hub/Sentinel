"""
cases.py — Cases API Router (Placeholder)

Planned endpoints:
    POST   /cases
    GET    /cases
    GET    /cases/{case_id}
    PATCH  /cases/{case_id}
    DELETE /cases/{case_id}

See docs/architecture/api-contract.md for the full API contract.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/cases", tags=["Cases"])

# TODO: Implement cases endpoints
# @router.post("", status_code=201)
# async def create_case(...): ...
#
# @router.get("")
# async def list_cases(...): ...
#
# @router.get("/{case_id}")
# async def get_case(...): ...
#
# @router.patch("/{case_id}")
# async def update_case(...): ...
#
# @router.delete("/{case_id}")
# async def delete_case(...): ...


@router.get("", status_code=501)
async def list_cases():
    """NOT YET IMPLEMENTED — placeholder to show route exists."""
    return {"detail": "Not implemented", "planned_endpoint": "GET /cases"}


@router.post("", status_code=501)
async def create_case():
    """NOT YET IMPLEMENTED — placeholder to show route exists."""
    return {"detail": "Not implemented", "planned_endpoint": "POST /cases"}


@router.get("/{case_id}", status_code=501)
async def get_case(case_id: str):
    """NOT YET IMPLEMENTED — placeholder to show route exists."""
    return {"detail": "Not implemented", "planned_endpoint": f"GET /cases/{case_id}"}
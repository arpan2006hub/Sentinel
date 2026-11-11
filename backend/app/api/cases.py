"""Case Management API Router."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.cases import CaseCreate, CaseListResponse, CaseResponse, CaseUpdate
from app.services.case_service import CaseService

router = APIRouter(prefix="/cases", tags=["Cases"])


@router.post(
    "",
    response_model=CaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new investigation case",
    description="Registers a new case record in the Sentinel platform.",
)
async def create_case(case_in: CaseCreate) -> CaseResponse:
    service = CaseService.get_instance()
    return service.create_case(case_in)


@router.get(
    "",
    response_model=CaseListResponse,
    summary="List investigation cases",
    description="Retrieves a paginated list of cases with optional status filtering.",
)
async def list_cases(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (open, closed, etc.)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
) -> CaseListResponse:
    service = CaseService.get_instance()
    return service.list_cases(status=status_filter, page=page, page_size=page_size)


@router.get(
    "/{case_id}",
    response_model=CaseResponse,
    summary="Get case details",
    description="Fetches complete metadata and evidence counts for a specific case.",
)
async def get_case(case_id: str) -> CaseResponse:
    service = CaseService.get_instance()
    case = service.get_case(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found.",
        )
    return case


@router.patch(
    "/{case_id}",
    response_model=CaseResponse,
    summary="Update case",
    description="Updates title, description, status, or metadata for an existing case.",
)
async def update_case(case_id: str, case_update: CaseUpdate) -> CaseResponse:
    service = CaseService.get_instance()
    updated = service.update_case(case_id, case_update)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found.",
        )
    return updated


@router.delete(
    "/{case_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete case",
    description="Deletes a case record and all associated evidence metadata.",
)
async def delete_case(case_id: str) -> None:
    service = CaseService.get_instance()
    deleted = service.delete_case(case_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found.",
        )

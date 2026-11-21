"""Analysis API Router — start and poll case analysis runs."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

from app.api.cases import require_case
from app.schemas.analysis import AnalysisRunListResponse, AnalysisRunResponse, AnalysisStartRequest
from app.services.analysis_service import AnalysisAlreadyRunningError, AnalysisService

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.post(
    "/start",
    response_model=AnalysisRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start analysing all evidence of a case",
    description=(
        "Queues a background run that processes every evidence item of the case into canonical events and "
        "correlates them (timeline, contradictions, evidence graph, suspect ranking). Poll "
        "`GET /api/analysis/{run_id}` until `status` is `completed` or `failed`. Returns 409 if a run is "
        "already active for the case. Video evidence is CPU-heavy; set `include_video=false` for a fast run."
    ),
)
async def start_analysis(request: AnalysisStartRequest, background_tasks: BackgroundTasks) -> AnalysisRunResponse:
    require_case(request.case_id)
    service = AnalysisService.get_instance()
    try:
        run = service.start_run(request)
    except AnalysisAlreadyRunningError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail={"message": str(err), "run_id": err.run_id})
    background_tasks.add_task(service.execute_run, run.run_id)
    return run


@router.get("", response_model=AnalysisRunListResponse, summary="List analysis runs")
async def list_runs(case_id: Optional[str] = Query(None)) -> AnalysisRunListResponse:
    return AnalysisService.get_instance().list_runs(case_id)


@router.get("/{run_id}", response_model=AnalysisRunResponse, summary="Get analysis run status and results")
async def get_run(run_id: str) -> AnalysisRunResponse:
    run = AnalysisService.get_instance().get_run(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Analysis run '{run_id}' was not found.")
    return run

"""FastAPI endpoints for Video Crime Analysis."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status  # type: ignore[import-untyped,import-not-found]

from app.schemas.video import (
    ModelInfoResponse,
    VideoAnalysisRequest,
    VideoAnalysisResponse,
)
from app.services.video_service import VideoAnalysisService

router = APIRouter(prefix="/video", tags=["Video AI"])


@router.get(
    "/model-info",
    response_model=ModelInfoResponse,
    summary="Get Video Crime Detector Model Info",
    description="Returns metadata and current status for the Nikeytas/timesformer-best-crime-detector model.",
)
async def get_model_info() -> ModelInfoResponse:
    service = VideoAnalysisService.get_instance()
    return service.get_model_info()


@router.post(
    "/analyze",
    response_model=VideoAnalysisResponse,
    summary="Analyze Video File Path",
    description="Runs TimeSformer crime detection on a video file located on disk.",
)
async def analyze_video(request: VideoAnalysisRequest) -> VideoAnalysisResponse:
    service = VideoAnalysisService.get_instance()
    try:
        result = service.analyze_video_path(request)
        return VideoAnalysisResponse(**result)
    except FileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Video analysis failed: {err}",
        )


@router.post(
    "/analyze-upload",
    response_model=VideoAnalysisResponse,
    summary="Analyze Uploaded Video",
    description="Uploads and analyzes a video file for criminal activities using TimeSformer.",
)
async def analyze_uploaded_video(
    file: UploadFile = File(..., description="Video file to analyze (.mp4, .avi, etc.)"),
    case_id: str = Form("CASE-DEFAULT", description="Associated case ID"),
    location_id: Optional[str] = Form(None, description="Camera zone / location ID"),
    threshold: float = Form(0.5, ge=0.0, le=1.0, description="Crime threshold"),
    window_seconds: float = Form(2.0, ge=0.5, le=30.0, description="Clip duration"),
    stride_seconds: float = Form(1.0, ge=0.2, le=30.0, description="Stride duration"),
) -> VideoAnalysisResponse:
    service = VideoAnalysisService.get_instance()
    try:
        result = await service.analyze_uploaded_file(
            file=file,
            case_id=case_id,
            location_id=location_id,
            threshold=threshold,
            window_seconds=window_seconds,
            stride_seconds=stride_seconds,
        )
        return VideoAnalysisResponse(**result)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze uploaded video: {err}",
        )


@router.post(
    "/download-weights",
    response_model=ModelInfoResponse,
    summary="Download Model Weights",
    description="Downloads Nikeytas/timesformer-best-crime-detector weights from Hugging Face.",
)
async def download_weights() -> ModelInfoResponse:
    service = VideoAnalysisService.get_instance()
    success = service.detector.download_and_load()
    if not success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to download weights from Hugging Face.",
        )
    return service.get_model_info()

"""Service layer for Video Crime Analysis using TimeSformer."""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Optional

from fastapi import UploadFile  # type: ignore[import-untyped,import-not-found]

from ai.video.timesformer_crime_detector import TimesformerCrimeDetector
from app.schemas.video import (
    ModelInfoResponse,
    VideoAnalysisRequest,
    VideoAnalysisResponse,
)

logger = logging.getLogger(__name__)


class VideoAnalysisService:
    """Singleton service managing TimeSformer model inference for video analysis."""

    _instance: Optional[VideoAnalysisService] = None

    def __init__(self, model_path: Optional[str] = None) -> None:
        self.detector = TimesformerCrimeDetector(
            model_path=model_path,
            auto_download=False,
        )

    @classmethod
    def get_instance(cls) -> VideoAnalysisService:
        if cls._instance is None:
            # Check environment variable for model path
            env_path = os.getenv("TIMESFORMER_MODEL_PATH")
            cls._instance = cls(model_path=env_path)
        return cls._instance

    def get_model_info(self) -> ModelInfoResponse:
        """Return information about the current TimeSformer model and runtime."""
        return ModelInfoResponse(
            model_id=self.detector.REPO_ID,
            architecture="TimeSformer (Time-Space Transformer)",
            dataset="UCF-Crime",
            f1_score=self.detector.MODEL_F1_SCORE,
            accuracy=self.detector.MODEL_ACCURACY,
            is_loaded=self.detector.is_loaded,
            is_fallback=self.detector.is_fallback,
            device=self.detector.device,
            model_path=str(self.detector.model_path) if self.detector.model_path else None,
        )

    def analyze_video_path(self, request: VideoAnalysisRequest) -> dict[str, Any]:
        """Analyze a video file specified by file path."""
        if request.auto_download and not self.detector.is_loaded and not self.detector.model_path:
            self.detector.download_and_load()

        return self.detector.analyze_video(
            video_path=request.video_path,
            window_seconds=request.window_seconds,
            stride_seconds=request.stride_seconds,
            threshold=request.threshold,
            case_id=request.case_id,
            location_id=request.location_id,
            evidence_id=request.evidence_id,
        )

    async def analyze_uploaded_file(
        self,
        file: UploadFile,
        case_id: str = "CASE-DEFAULT",
        location_id: Optional[str] = None,
        threshold: float = 0.5,
        window_seconds: float = 2.0,
        stride_seconds: float = 1.0,
    ) -> dict[str, Any]:
        """Analyze an uploaded video file."""
        suffix = Path(file.filename or "video.mp4").suffix or ".mp4"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = Path(tmp.name)

        try:
            return self.detector.analyze_video(
                video_path=tmp_path,
                window_seconds=window_seconds,
                stride_seconds=stride_seconds,
                threshold=threshold,
                case_id=case_id,
                location_id=location_id,
                evidence_id=f"EVID-{Path(file.filename or 'upload').stem[:8].upper()}",
            )
        finally:
            try:
                tmp_path.unlink()
            except Exception as err:
                logger.warning("Failed to clean up temp file %s: %s", tmp_path, err)

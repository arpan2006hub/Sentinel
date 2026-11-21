"""Service layer for Video Crime Analysis using TimeSformer.

The model (~485 MB) is loaded lazily on the first analysis so that API
start-up, health checks and tests stay fast on CPU-only machines.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Any, Optional

from fastapi import UploadFile  # type: ignore[import-untyped,import-not-found]

from ai.video.timesformer_crime_detector import TimesformerCrimeDetector
from app.config import PROJECT_ROOT, get_settings
from app.schemas.video import ModelInfoResponse, VideoAnalysisRequest

logger = logging.getLogger(__name__)


class VideoAnalysisService:
    """Singleton service managing TimeSformer inference."""

    _instance: Optional[VideoAnalysisService] = None

    def __init__(self, model_path: Optional[str | Path] = None, cache_dir: Optional[str | Path] = None) -> None:
        settings = get_settings()
        self.max_seconds_default = settings.video_max_seconds
        self.detector = TimesformerCrimeDetector(
            model_path=model_path or settings.timesformer_model_path,
            cache_dir=cache_dir or settings.timesformer_cache_dir,
            auto_download=settings.video_auto_download,
            load_on_init=False,
        )
        self._lock = threading.Lock()  # one CPU-heavy inference at a time

    @classmethod
    def get_instance(cls) -> VideoAnalysisService:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_model_info(self) -> ModelInfoResponse:
        return ModelInfoResponse(
            model_id=self.detector.REPO_ID,
            architecture="TimeSformer (Time-Space Transformer)",
            dataset="UCF-Crime",
            f1_score=self.detector.MODEL_F1_SCORE,
            accuracy=self.detector.MODEL_ACCURACY,
            is_loaded=self.detector.is_loaded,
            is_fallback=not self.detector.is_loaded and (self.detector.is_fallback or not self.detector.weights_available),
            weights_available=self.detector.weights_available,
            device=self.detector.device,
            model_path=str(self.detector.model_path) if self.detector.model_path else None,
        )

    def download_weights(self) -> bool:
        with self._lock:
            return self.detector.download_and_load()

    def analyze_file(
        self,
        video_path: Path,
        case_id: str = "CASE-DEFAULT",
        location_id: Optional[str] = None,
        evidence_id: Optional[str] = None,
        threshold: float = 0.5,
        window_seconds: float = 2.0,
        stride_seconds: float = 2.0,
        start_time: Optional[str] = None,
        max_seconds: Optional[float] = None,
    ) -> dict[str, Any]:
        with self._lock:
            self.detector.ensure_loaded()
            return self.detector.analyze_video(
                video_path=video_path,
                window_seconds=window_seconds,
                stride_seconds=stride_seconds,
                threshold=threshold,
                case_id=case_id,
                location_id=location_id,
                evidence_id=evidence_id,
                base_timestamp=start_time,
                max_seconds=max_seconds if max_seconds is not None else self.max_seconds_default,
            )

    def analyze_video_path(self, request: VideoAnalysisRequest) -> dict[str, Any]:
        """Analyse a video already on the server's disk (restricted to project/evidence folders)."""
        path = Path(request.video_path).expanduser()
        if not path.is_absolute():
            path = (PROJECT_ROOT / path).resolve()
        allowed_roots = [PROJECT_ROOT.resolve(), get_settings().storage_path.resolve()]
        if not any(path.resolve().is_relative_to(root) for root in allowed_roots):
            raise PermissionError("video_path must be inside the project directory or the evidence store")
        if not path.is_file():
            raise FileNotFoundError(f"Video file not found: {path}")
        if request.auto_download and not self.detector.weights_available:
            self.download_weights()
        return self.analyze_file(
            path, case_id=request.case_id, location_id=request.location_id, evidence_id=request.evidence_id,
            threshold=request.threshold, window_seconds=request.window_seconds,
            stride_seconds=request.stride_seconds, start_time=request.start_time, max_seconds=request.max_seconds,
        )

    def analyze_uploaded_file(
        self,
        file: UploadFile,
        case_id: str = "CASE-DEFAULT",
        location_id: Optional[str] = None,
        threshold: float = 0.5,
        window_seconds: float = 2.0,
        stride_seconds: float = 2.0,
        start_time: Optional[str] = None,
        max_seconds: Optional[float] = None,
    ) -> dict[str, Any]:
        """Analyse an uploaded video without storing it as evidence (quick look)."""
        suffix = Path(file.filename or "video.mp4").suffix or ".mp4"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = Path(tmp.name)
        try:
            return self.analyze_file(
                tmp_path, case_id=case_id, location_id=location_id,
                evidence_id=f"EVID-{Path(file.filename or 'upload').stem[:8].upper()}",
                threshold=threshold, window_seconds=window_seconds, stride_seconds=stride_seconds,
                start_time=start_time, max_seconds=max_seconds,
            )
        finally:
            try:
                tmp_path.unlink()
            except OSError as err:
                logger.warning("Failed to clean up temp file %s: %s", tmp_path, err)

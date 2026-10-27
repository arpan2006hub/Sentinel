"""Schemas for Video Analysis and Crime Detection."""

from __future__ import annotations

from typing import Any, List, Optional
from pydantic import BaseModel, Field  # type: ignore[import-untyped,import-not-found]


class VideoAnalysisRequest(BaseModel):
    """Request payload for analyzing a video for criminal activity."""
    video_path: str = Field(..., description="Absolute or relative path to the video file.")
    window_seconds: float = Field(2.0, ge=0.5, le=30.0, description="Duration in seconds for each temporal clip.")
    stride_seconds: float = Field(1.0, ge=0.2, le=30.0, description="Step in seconds between successive clips.")
    threshold: float = Field(0.5, ge=0.0, le=1.0, description="Confidence threshold for crime classification.")
    case_id: str = Field("CASE-DEFAULT", description="Associated investigation case ID.")
    location_id: Optional[str] = Field(None, description="Camera zone or location identifier.")
    evidence_id: Optional[str] = Field(None, description="Source evidence ID.")
    auto_download: bool = Field(False, description="Automatically download model weights from Hugging Face if not found.")


class CrimeSegment(BaseModel):
    """Crime detection results for a specific temporal window in a video."""
    start_seconds: float
    end_seconds: float
    prediction: str
    crime_probability: float
    confidence: float


class CanonicalEvent(BaseModel):
    """Sentinel Canonical Event representation for video anomaly/crime."""
    event_id: str
    case_id: str
    timestamp_start: str
    timestamp_end: Optional[str] = None
    actor_id: Optional[str] = "unknown"
    action: str = "crime_detected"
    object_id: Optional[str] = None
    location_id: Optional[str] = None
    source_type: str = "cctv_video"
    source_id: str
    confidence: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class VideoAnalysisResponse(BaseModel):
    """Response payload returned by the video crime detection engine."""
    video_file: str
    duration_seconds: float
    analyzed_segments_count: int
    crime_detected_count: int
    status: str
    max_crime_probability: float
    model_name: str
    model_f1_score: float
    segments: List[CrimeSegment]
    canonical_events: List[CanonicalEvent]


class ModelInfoResponse(BaseModel):
    """Information and current runtime status of the crime detection model."""
    model_id: str = "Nikeytas/timesformer-best-crime-detector"
    architecture: str = "TimeSformer (Time-Space Transformer)"
    dataset: str = "UCF-Crime"
    f1_score: float = 0.8868
    accuracy: float = 0.8425
    is_loaded: bool
    is_fallback: bool
    device: str
    model_path: Optional[str] = None
    supported_classes: List[str] = [
        "Normal",
        "Crime (Arson, Assault, Burglary, Robbery, Shooting, Stealing, Vandalism, etc.)",
    ]

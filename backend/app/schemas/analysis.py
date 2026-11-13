"""Schemas for case analysis runs (evidence processing + correlation)."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class AnalysisStartRequest(BaseModel):
    case_id: str = Field(..., description="Case to analyse")
    include_video: bool = Field(
        True,
        description="Run TimeSformer on cctv_video evidence. CPU-heavy (~7 s of CPU per video second).",
    )
    video_max_seconds: Optional[float] = Field(
        None, gt=0, description="Analyse at most N seconds per video (default: VIDEO_MAX_SECONDS env, 120)"
    )
    video_threshold: float = Field(0.5, ge=0.0, le=1.0)
    video_window_seconds: float = Field(2.0, ge=0.5, le=30.0)
    video_stride_seconds: float = Field(2.0, ge=0.2, le=30.0)
    window_minutes: int = Field(60, ge=1, le=1440, description="Correlation clustering window")


class EvidenceProcessingResult(BaseModel):
    evidence_id: str
    file_name: str
    source_type: str
    processor: str
    status: str = Field(description="processed, skipped, error")
    events: int = 0
    message: Optional[str] = None


class AnalysisRunResponse(BaseModel):
    run_id: str
    case_id: str
    status: str = Field(description="queued, running, completed, failed")
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    options: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)
    evidence_results: list[EvidenceProcessingResult] = Field(default_factory=list)
    error: Optional[str] = None


class AnalysisRunListResponse(BaseModel):
    runs: list[AnalysisRunResponse]
    total: int

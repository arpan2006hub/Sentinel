"""Pydantic schemas for Case Management."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

CaseStatus = Literal["open", "investigating", "closed", "archived"]


class CaseCreate(BaseModel):
    """Payload for creating a new case."""
    title: str = Field(..., min_length=1, max_length=255, description="Case title")
    description: Optional[str] = Field(default="", description="Case description")
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict, description="Custom metadata")


class CaseUpdate(BaseModel):
    """Payload for updating an existing case (all fields optional)."""
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None)
    status: Optional[CaseStatus] = Field(default=None, description="open, investigating, closed, archived")
    metadata: Optional[dict[str, Any]] = Field(default=None)


class CaseResponse(BaseModel):
    """Complete case representation returned by the API."""
    case_id: str
    title: str
    description: str
    status: str
    evidence_count: int = 0
    event_count: int = Field(0, description="Events in the latest completed analysis run")
    anomaly_count: int = Field(0, description="Contradictions/anomalies in the latest completed analysis run")
    last_analysis_run_id: Optional[str] = None
    last_analysis_status: Optional[str] = None
    created_at: str
    updated_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class CaseListResponse(BaseModel):
    """Paginated list of cases."""
    cases: list[CaseResponse]
    total: int
    page: int = 1
    page_size: int = 20


class CaseSummaryResponse(BaseModel):
    """Dashboard overview for one case."""
    case: CaseResponse
    analysis: Optional[dict[str, Any]] = Field(None, description="Latest analysis run (any status)")
    summary: dict[str, Any] = Field(default_factory=dict, description="Correlation summary of the latest completed run")
    top_suspects: list[dict[str, Any]] = Field(default_factory=list)
    anomalies_by_severity: dict[str, int] = Field(default_factory=dict)
    evidence_by_status: dict[str, int] = Field(default_factory=dict)

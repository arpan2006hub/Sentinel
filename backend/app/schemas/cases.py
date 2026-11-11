"""Pydantic schemas for Case Management."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field


class CaseBase(BaseModel):
    """Base fields for a case."""
    title: str = Field(..., min_length=1, max_length=255, description="Case title")
    description: str = Field(default="", description="Detailed description of the case")
    status: str = Field(default="open", description="Case status: open, closed, investigating, archived")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Custom metadata for the case")


class CaseCreate(BaseModel):
    """Payload for creating a new case."""
    title: str = Field(..., min_length=1, max_length=255, description="Case title")
    description: Optional[str] = Field(default="", description="Case description")
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict, description="Custom metadata")


class CaseUpdate(BaseModel):
    """Payload for updating an existing case."""
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None, description="open, investigating, closed, archived")
    metadata: Optional[dict[str, Any]] = Field(default=None)


class CaseResponse(BaseModel):
    """Complete case representation returned by API."""
    case_id: str
    title: str
    description: str
    status: str
    evidence_count: int = 0
    event_count: int = 0
    anomaly_count: int = 0
    created_at: str
    updated_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class CaseListResponse(BaseModel):
    """Paginated list of cases."""
    cases: list[CaseResponse]
    total: int
    page: int = 1
    page_size: int = 20


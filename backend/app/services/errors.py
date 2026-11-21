"""Shared service-layer exceptions."""

from __future__ import annotations


class ActiveAnalysisError(RuntimeError):
    """Raised when a destructive operation targets a case with an active run."""

    def __init__(self, case_id: str, run_id: str) -> None:
        super().__init__(f"Case '{case_id}' has an active analysis run and cannot be modified or deleted")
        self.case_id = case_id
        self.run_id = run_id

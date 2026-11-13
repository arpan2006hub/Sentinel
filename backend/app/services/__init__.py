"""Backend service layer (singletons wrapping SQLite + the AI layer)."""


def reset_services() -> None:
    """Drop all service singletons so they are rebuilt from current settings.

    Used by tests (after changing STORAGE_PATH / ARTIFACTS_DIR) and scripts.
    """
    from app.services.analysis_service import AnalysisService
    from app.services.case_service import CaseService
    from app.services.evidence_service import EvidenceService
    from app.services.video_service import VideoAnalysisService

    for cls in (CaseService, EvidenceService, AnalysisService, VideoAnalysisService):
        cls._instance = None  # type: ignore[attr-defined]

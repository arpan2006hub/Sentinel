"""Route an evidence file to the right processor based on its source type."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from ai.processing import processors

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".mpeg", ".mpg", ".webm"}

# source_type -> (processor kind, human description). Exposed to the frontend
# through GET /api/evidence/source-types.
SOURCE_TYPES: dict[str, dict[str, str]] = {
    "endpoint_log": {"processor": "cyber", "description": "Cyber activity feature CSV (timestamp,user_id,login_count,...)"},
    "auth_log": {"processor": "cyber", "description": "Authentication activity feature CSV"},
    "file_access_log": {"processor": "cyber", "description": "File access feature CSV"},
    "usb_log": {"processor": "cyber", "description": "Removable media feature CSV"},
    "network_log": {"processor": "cyber", "description": "Network activity feature CSV"},
    "email_log": {"processor": "cyber", "description": "Email activity feature CSV"},
    "badge_log": {"processor": "badge", "description": "Physical access CSV (timestamp,badge_id|user_id,location_id,result)"},
    "cctv_video": {"processor": "video", "description": "CCTV video file (.mp4/.avi/...) analysed with TimeSformer"},
    "video_features": {"processor": "video_features", "description": "Motion feature CSV (timestamp,camera_id,location_id,motion_score,...)"},
    "text_document": {"processor": "document", "description": "Statements/reports (.txt, .json, .jsonl with document_id,text,timestamp)"},
    "pdf_document": {"processor": "unsupported", "description": "PDF evidence (stored and hashed; text extraction/OCR not implemented yet)"},
    "canonical_events": {"processor": "canonical", "description": "Pre-computed canonical events JSONL (e.g. TimeSformer CLI output)"},
    "general": {"processor": "auto", "description": "Unknown type; processor is chosen from the file extension"},
}


def detect_processor(source_type: str, file_path: Path) -> str:
    """Return the processor kind for an evidence item."""
    kind = SOURCE_TYPES.get(source_type, {"processor": "auto"})["processor"]
    if kind != "auto":
        return kind
    suffix = file_path.suffix.lower()
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in {".txt", ".md", ".json", ".jsonl", ".ndjson", ".eml"}:
        return "document"
    return "unsupported"


def process_evidence_file(
    file_path: Path,
    source_type: str,
    source_id: str,
    case_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    cyber_model_path: Optional[Path] = None,
    document_model_path: Optional[Path] = None,
    video_features_model_path: Optional[Path] = None,
) -> list[dict[str, Any]]:
    """Process a non-video evidence file into canonical events.

    Video files must be handled by the caller (they need the TimeSformer
    detector); this function raises ``ValueError`` for them and for unsupported
    formats.
    """
    metadata = metadata or {}
    kind = detect_processor(source_type, file_path)
    if kind == "cyber":
        events = processors.process_cyber_csv(file_path, source_id, case_id, model_path=cyber_model_path)
    elif kind == "badge":
        events = processors.process_badge_csv(file_path, source_id, case_id)
    elif kind == "video_features":
        events = processors.process_video_features_csv(file_path, source_id, case_id, model_path=video_features_model_path)
    elif kind == "document":
        events = processors.process_documents(
            file_path, source_id, case_id,
            model_path=document_model_path,
            default_timestamp=metadata.get("recorded_at"),
        )
    elif kind == "canonical":
        events = processors.process_canonical_jsonl(file_path, source_id, case_id)
    elif kind == "video":
        raise ValueError("Video files must be analysed with the TimeSformer detector")
    else:
        raise ValueError(f"No processor available for source_type '{source_type}' ({file_path.suffix})")

    # Evidence-level location default (e.g. a camera's zone or a host's office).
    default_location = metadata.get("location_id")
    if default_location:
        for ev in events:
            ev.setdefault("location_id", default_location)
            if not ev.get("location_id"):
                ev["location_id"] = default_location
    return events

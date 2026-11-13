"""Central runtime configuration for the Sentinel backend.

All filesystem paths are resolved against the project root (not the current
working directory), so the API behaves identically whether uvicorn is started
from the repo root, from ``backend/``, or inside the Docker image.

Values are read from environment variables (optionally loaded from a ``.env``
file in the project root). Settings are re-read on every call to
``get_settings()`` so tests can override them with ``monkeypatch.setenv``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

try:  # optional dependency
    from dotenv import load_dotenv  # type: ignore[import-untyped,import-not-found]

    load_dotenv(PROJECT_ROOT / ".env", override=False)
except Exception:  # pragma: no cover - dotenv is optional
    pass


def resolve_path(value: str | os.PathLike[str]) -> Path:
    """Resolve a possibly-relative path against the project root."""
    path = Path(value).expanduser()
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    try:
        return float(raw) if raw not in (None, "") else default
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """Resolved Sentinel settings."""

    app_name: str = "Sentinel API"
    version: str = "0.2.0"
    storage_path: Path = field(default_factory=lambda: resolve_path("./local-evidence-store"))
    artifacts_dir: Path = field(default_factory=lambda: resolve_path("./artifacts"))
    max_upload_size_mb: float = 500.0
    cors_origins: tuple[str, ...] = ("http://localhost:5173", "http://localhost:3000")
    timesformer_model_path: Path | None = None
    timesformer_cache_dir: Path = field(default_factory=lambda: resolve_path("./artifacts/models/timesformer"))
    video_auto_download: bool = False
    video_max_seconds: float = 120.0
    cyber_model_path: Path | None = None
    document_model_path: Path | None = None
    video_features_model_path: Path | None = None

    @property
    def db_path(self) -> Path:
        return self.storage_path / "sentinel.db"

    @property
    def max_upload_bytes(self) -> int:
        return int(self.max_upload_size_mb * 1024 * 1024)

    def case_artifacts_dir(self, case_id: str) -> Path:
        """Per-case output directory for correlation results."""
        return self.artifacts_dir / "cases" / case_id


def _optional_path(name: str) -> Path | None:
    raw = os.getenv(name)
    return resolve_path(raw) if raw else None


def get_settings() -> Settings:
    """Build settings from the current environment."""
    artifacts_dir = resolve_path(os.getenv("ARTIFACTS_DIR", "./artifacts"))
    origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
    origins = tuple(o.strip() for o in origins_raw.split(",") if o.strip())

    def model_default(env: str, relative: str) -> Path | None:
        explicit = _optional_path(env)
        if explicit:
            return explicit
        candidate = artifacts_dir / relative
        return candidate if candidate.is_file() else None

    return Settings(
        storage_path=resolve_path(os.getenv("STORAGE_PATH", "./local-evidence-store")),
        artifacts_dir=artifacts_dir,
        max_upload_size_mb=_env_float("MAX_UPLOAD_SIZE_MB", 500.0),
        cors_origins=origins,
        timesformer_model_path=_optional_path("TIMESFORMER_MODEL_PATH"),
        timesformer_cache_dir=resolve_path(
            os.getenv("TIMESFORMER_CACHE_DIR", str(artifacts_dir / "models" / "timesformer"))
        ),
        video_auto_download=_env_bool("VIDEO_AUTO_DOWNLOAD", False),
        video_max_seconds=_env_float("VIDEO_MAX_SECONDS", 120.0),
        cyber_model_path=model_default("CYBER_MODEL_PATH", "cyber/model.joblib"),
        document_model_path=model_default("DOCUMENT_MODEL_PATH", "documents/model.joblib"),
        video_features_model_path=model_default("VIDEO_FEATURES_MODEL_PATH", "video/model.joblib"),
    )

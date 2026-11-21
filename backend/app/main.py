"""
Sentinel Backend — FastAPI Application Entry Point

Run (from the project root):
    uvicorn app.main:app --app-dir backend --reload --port 8000

All routes are served under ``/api`` (use this prefix from the frontend).
For backwards compatibility the case/evidence/timeline/graph/anomalies/analysis
routes are also reachable without the prefix (hidden from the OpenAPI schema).

API documentation:
    http://localhost:8000/docs     (Swagger UI)
    http://localhost:8000/redoc    (ReDoc)
    http://localhost:8000/openapi.json
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
for _path in (BACKEND_ROOT, PROJECT_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.api.analysis import router as analysis_router  # noqa: E402
from app.api.anomalies import router as anomalies_router  # noqa: E402
from app.api.cases import router as cases_router  # noqa: E402
from app.api.evidence import router as evidence_router  # noqa: E402
from app.api.graph import router as graph_router  # noqa: E402
from app.api.timeline import router as timeline_router  # noqa: E402
from app.api.video import router as video_router  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import connect  # noqa: E402

settings = get_settings()

app = FastAPI(
    title="Sentinel API",
    description=(
        "Local-first multimodal AI system for insider-threat investigation assistance. "
        "Outputs are investigative leads for human analysts, not automated verdicts."
    ),
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Status"])
async def root() -> dict:
    """Return a basic service identifier."""
    return {
        "service": "Sentinel API",
        "status": "running",
        "version": settings.version,
        "api_prefix": "/api",
        "docs": "/docs",
    }


@app.get("/health", tags=["Status"])
@app.get("/api/health", tags=["Status"], include_in_schema=False)
def health() -> dict:
    """Health probe: database, evidence storage, artifacts and video model status."""
    current = get_settings()
    checks: dict[str, str] = {}
    try:
        with connect(current.db_path) as conn:
            conn.execute("SELECT 1")
        checks["database"] = "ok (sqlite)"
    except Exception as err:  # pragma: no cover - environment dependent
        checks["database"] = f"error: {err}"
    try:
        current.storage_path.mkdir(parents=True, exist_ok=True)
        probe = current.storage_path / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        checks["storage"] = "ok"
    except Exception as err:  # pragma: no cover - environment dependent
        checks["storage"] = f"error: {err}"

    from app.services.video_service import VideoAnalysisService

    info = VideoAnalysisService.get_instance().get_model_info()
    checks["video_model"] = (
        "loaded" if info.is_loaded else ("weights_available (loads on first use)" if info.weights_available
                                         else "weights_missing (motion fallback)")
    )
    healthy = all(not v.startswith("error") for v in checks.values())
    return {
        "status": "healthy" if healthy else "degraded",
        "api": "running",
        **checks,
        "storage_path": str(current.storage_path),
        "artifacts_dir": str(current.artifacts_dir),
    }


for _router in (cases_router, evidence_router, analysis_router, timeline_router, graph_router, anomalies_router):
    app.include_router(_router, prefix="/api")
    app.include_router(_router, prefix="", include_in_schema=False)  # legacy un-prefixed paths
app.include_router(video_router, prefix="/api")

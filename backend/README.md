# Backend — Sentinel API (FastAPI)

## Run

```bash
# from the project root, inside the virtualenv
uvicorn app.main:app --app-dir backend --reload --port 8000
```

Paths in `.env` (`STORAGE_PATH`, `ARTIFACTS_DIR`, …) are resolved from the project root, so the working directory doesn't matter. Docs are at `/docs`, the schema at `/openapi.json`, and the health check at `/health`.

## Layout

```
backend/app/
├── main.py            app factory: CORS, /health, routers under /api (+ hidden legacy un-prefixed routes)
├── config.py          environment-driven settings (paths resolved from project root)
├── db.py              SQLite schema/migrations, connection helper, hash-chained audit log
├── api/               cases, evidence, analysis, timeline, graph, anomalies, video routers
├── schemas/           Pydantic request/response models
└── services/          CaseService, EvidenceService, AnalysisService, VideoAnalysisService (+ reset_services)
backend/Dockerfile     CPU-only image; build context = project root
```

## Key behaviours

- **Evidence integrity:**
  - Every file is streamed to `STORAGE_PATH/<case>/<evidence>/` and hashed with SHA-256.
  - Uploads larger than `MAX_UPLOAD_SIZE_MB` are rejected with 413 and nothing is kept.
  - Every action (`ingested`, `verified`, `accessed`, `analyzed`, `deleted`) appends an audit record chained to the previous one by hash.
  - `GET /api/evidence/{id}/audit/verify` detects edited or removed records.
  - Audit records outlive deleted evidence and deleted cases.
- **Analysis:**
  - `POST /api/analysis/start` queues an in-process background task (`AnalysisService.execute_run`).
  - The task routes each evidence item to its processor (`ai/processing`), runs the correlation engine, and writes `ARTIFACTS_DIR/cases/<case_id>/correlation/*.json`.
  - The timeline, graph, anomalies and suspects endpoints read those files, so results are strictly per case.
  - Results are written to a staging folder and swapped in only on success, so the previous results stay readable during a re-run and survive a failed run.
  - Only one active run per case is allowed (409 otherwise, checked atomically). Runs interrupted by a restart are marked failed at start-up.
  - CCTV video without `recorded_at` metadata is analysed, but its events are excluded from correlation (see the run's `evidence_results[].message`).
- **Video:**
  - TimeSformer loads lazily on first use, so start-up and tests stay fast.
  - Inference is serialised with a lock and bounded by `VIDEO_MAX_SECONDS`.
  - `POST /api/video/analyze` only accepts paths inside the project or the evidence store.

## Not implemented yet

- Authentication / roles (`AUTH_ENABLED` is ignored).
- PostgreSQL + Alembic.
- Redis/Celery workers: in-process background tasks don't survive restarts and run in the API process.
- PDF/OCR text extraction (PDFs are stored and hashed but skipped by analysis).

See `docs/STATUS.md`.

## Docker

Built and smoke-tested 2026-11-14. See the Docker section of the root `README.md`.

## Tests

```bash
python -m pytest tests -q
```

`tests/conftest.py` isolates storage and artifacts per test and never loads the video model.

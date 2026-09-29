# Backend — Sentinel

> **Status**: Foundation only. The FastAPI application runs but has minimal endpoints.

---

## Responsibility

The Sentinel backend is the central REST API and orchestration layer. It is responsible for:

- **Case management** — Create, list, update, and archive investigation cases
- **Evidence ingestion** — Accept file uploads, compute SHA-256 hashes, store metadata in PostgreSQL, write files to evidence store, create audit records
- **Analysis orchestration** — Queue AI analysis jobs via Celery, track analysis run status, collect results
- **Event storage** — Persist canonical events from all AI pipelines to PostgreSQL
- **Query APIs** — Serve timeline, evidence graph, and anomaly data to the frontend
- **Audit & integrity** — Maintain append-only audit logs; provide evidence hash verification
- **Security** — Authentication, authorization, input validation, CORS

---

## Technology

- **Python 3.11+**
- **FastAPI** — REST API framework with automatic OpenAPI docs
- **Pydantic v2** — Request/response validation and settings management
- **SQLAlchemy 2.x** — ORM for PostgreSQL (planned)
- **Alembic** — Database migrations (planned)
- **Redis + Celery** — Background task queue for AI jobs (planned)
- **PostgreSQL 16** — Primary database (planned)

---

## Directory Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI app entry point (IMPLEMENTED)
│   ├── api/                    # API routers (PLACEHOLDERS)
│   │   ├── cases.py
│   │   ├── evidence.py
│   │   ├── analysis.py
│   │   ├── anomalies.py
│   │   ├── timeline.py
│   │   └── graph.py
│   ├── models/                 # SQLAlchemy models (.gitkeep)
│   ├── schemas/                # Pydantic schemas (.gitkeep)
│   ├── services/               # Business logic (.gitkeep)
│   ├── repositories/           # Data access layer (.gitkeep)
│   ├── workers/                # Celery tasks (.gitkeep)
│   └── security/               # Auth, permissions (.gitkeep)
├── tests/                      # Backend tests (.gitkeep)
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

---

## API Endpoints

### Implemented

| Method | Path | Description |
|---|---|---|
| GET | `/` | Service identifier |
| GET | `/health` | Health probe |

### Planned (see `docs/architecture/api-contract.md`)

| Method | Path | Description |
|---|---|---|
| POST | `/cases` | Create a case |
| GET | `/cases` | List cases |
| GET | `/cases/{id}` | Get case details |
| POST | `/evidence` | Upload evidence |
| GET | `/evidence/{id}` | Get evidence metadata |
| GET | `/evidence/{id}/verify` | Verify evidence integrity |
| POST | `/analysis/start` | Start AI analysis job |
| GET | `/analysis/{id}` | Get analysis run status |
| GET | `/timeline/{case_id}` | Get unified event timeline |
| GET | `/graph/{case_id}` | Get entity relationship graph |
| GET | `/anomalies/{case_id}` | List anomalies for a case |
| GET | `/anomalies/{id}/detail` | Get anomaly detail |

---

## Running Locally

### Prerequisites

- Python 3.11+
- PostgreSQL 16 (for full implementation)
- Redis 7 (for background workers)

### Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp ../.env.example .env
# Edit .env with your configuration

# Run the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### API Documentation

Once running, auto-generated docs are available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Configuration

All configuration is via environment variables (see `.env.example`):

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `SECRET_KEY` | JWT signing secret |
| `STORAGE_PATH` | Local evidence store root path |
| `MLFLOW_TRACKING_URI` | MLflow server URL |

---

## Architecture Notes

### Service / Repository / Model Separation

```
API Router (app/api/)       →  HTTP layer, request/response
    │
    ▼
Service (app/services/)     →  Business logic, orchestration
    │
    ├── Repository (app/repositories/)  →  Data access, SQLAlchemy
    │       │
    │       ▼
    │   Model (app/models/)             →  SQLAlchemy ORM classes
    │
    ▼
Worker (app/workers/)       →  Background jobs (Celery)
```

### Evidence Integrity

Evidence files are stored in the local filesystem (`STORAGE_PATH`). PostgreSQL stores only metadata including the SHA-256 hash. The `/evidence/{id}/verify` endpoint re-computes the hash and compares it.

### Background Processing

Long-running AI analysis jobs are executed by Celery workers:
1. API receives `POST /analysis/start`
2. Creates `analysis_runs` record with status `queued`
3. Queues Celery task
4. Worker picks up task, updates status to `running`
5. Worker processes evidence, writes events to PostgreSQL
6. Worker updates `analysis_runs` with `completed` and summary

---

## Testing

```bash
# Run tests (once implemented)
cd backend
python -m pytest tests/ -v

# Lint
ruff check .

# Type check
mypy app/
```

---

## Development Workflow

1. Make changes
2. Test locally
3. Run lint: `ruff check .`
4. Push branch
5. Open PR
6. One teammate reviews
7. Merge

---

*Backend implementation begins with the case and evidence API endpoints, PostgreSQL models, and evidence ingestion pipeline.*
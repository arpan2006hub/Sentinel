# ADR-001: Technology Stack

**Status**: Accepted  
**Date**: 2026  
**Authors**: Sentinel Team  

---

## Context

Sentinel is a student research project with a 4-person team. The technology stack must:

- Be appropriate for the planned technical scope (multimodal AI, REST API, interactive dashboard)
- Be learnable by a small team
- Support rapid local development
- Be open-source and self-hostable
- Support the planned research evaluation workflows

---

## Decision

The following technology stack is adopted as the initial architectural plan.

---

## Frontend

| Technology | Version / Notes | Purpose |
|---|---|---|
| **React** | 18+ | UI component framework |
| **TypeScript** | 5+ | Type safety |
| **Vite** | Latest | Fast development build tool |
| **Tailwind CSS** | 3+ | Utility-first styling |
| **React Query** | v5 | Server state management and API caching |
| **React Flow** or **Cytoscape.js** | TBD | Evidence graph visualisation |
| **Recharts** | Latest | Timeline charts and analytics |
| **Axios** | Latest | HTTP client for API calls |

**Rationale**:
- React is the most widely adopted frontend framework, with extensive documentation and library ecosystem
- TypeScript reduces runtime errors and improves maintainability
- Vite provides fast hot-module replacement suitable for rapid UI development
- React Flow and Cytoscape.js are both suited to graph visualisation; final choice deferred until implementation
- React Query reduces complexity of loading/caching states

---

## Backend

| Technology | Version / Notes | Purpose |
|---|---|---|
| **Python** | 3.11+ | Primary backend language |
| **FastAPI** | Latest | REST API framework |
| **Pydantic** | v2 | Data validation and serialisation |
| **SQLAlchemy** | 2.x | ORM for PostgreSQL |
| **Alembic** | Latest | Database migration management |

**Rationale**:
- Python is used for both backend and AI components, reducing context switching for the team
- FastAPI provides automatic OpenAPI documentation, async support, and Pydantic integration
- SQLAlchemy with Alembic is the standard Python ORM stack for production PostgreSQL usage

---

## Database

| Technology | Purpose |
|---|---|
| **PostgreSQL 16** | Primary relational database for all structured data |

**Rationale**:
- PostgreSQL is robust, widely supported, and self-hostable
- JSONB support is useful for flexible event metadata storage
- Widely documented with SQLAlchemy

---

## AI / ML

| Technology | Purpose |
|---|---|
| **PyTorch** | Deep learning model training and inference |
| **scikit-learn** | Traditional ML (baselines, classical anomaly detection) |
| **OpenCV** | Video frame processing and computer vision utilities |
| **Hugging Face Transformers** | Pre-trained language models for document/text AI |
| **Sentence Transformers** | Semantic similarity for entity resolution and document matching |
| **spaCy** | Named entity recognition and NLP pipeline |
| **pandas** | Data manipulation and log processing |
| **NumPy** | Numerical computation |
| **Ultralytics YOLO** | Person / object detection in video frames |

**Rationale**:
- PyTorch is the leading research deep-learning framework
- Hugging Face provides access to pre-trained models that reduce training time
- spaCy and Sentence Transformers are well-suited to the entity extraction and resolution tasks
- OpenCV + YOLO is the standard approach for video object detection

---

## Background Processing

| Technology | Purpose |
|---|---|
| **Redis** | Message broker for background task queue |
| **Celery** | Distributed task queue for AI analysis jobs |

**Rationale**:
- AI processing jobs (video analysis, log ingestion) may be long-running
- Celery + Redis provides a lightweight, self-hostable background processing architecture
- Avoids blocking the API on heavy computation

---

## MLOps

| Technology | Purpose |
|---|---|
| **MLflow** | Experiment tracking, model registry, artefact logging |

**Rationale**:
- MLflow is open-source and self-hostable
- Provides experiment tracking needed for the ablation study
- Model registry supports tracking model versions

---

## Infrastructure / DevOps

| Technology | Purpose |
|---|---|
| **Docker** | Container runtime |
| **Docker Compose** | Local multi-service orchestration |
| **GitHub Actions** | CI/CD pipeline (future) |

**Rationale**:
- Docker enables reproducible local deployment
- Docker Compose is sufficient for local development with the planned service topology
- GitHub Actions integrates naturally with the GitHub repository

---

## What Was Not Chosen

| Alternative | Reason not selected |
|---|---|
| Django | FastAPI preferred for async, lightweight API-first design |
| GraphQL | REST is simpler for a student team; GraphQL overhead not justified |
| MongoDB | PostgreSQL's JSONB provides flexibility without sacrificing relational structure |
| Kubernetes | Docker Compose is sufficient for local-first deployment scope |
| TensorFlow | PyTorch preferred; better ecosystem for research |
| Kafka | Redis + Celery is sufficient; Kafka adds unnecessary complexity |

---

## Consequences

- The team must ensure Python 3.11+ is available across all development environments
- Node.js 20+ is required for frontend development
- Docker and Docker Compose must be installed for local service orchestration
- Some AI library versions may conflict; a pinned `requirements.txt` is essential

---

## Review Triggers

This ADR should be revisited if:
- A critical library is found to be incompatible with another
- A team member identifies a substantially better alternative for a specific component
- Deployment requirements change significantly

---

*Stack decisions can evolve as implementation progresses. Changes should be documented in a new ADR or as an amendment.*

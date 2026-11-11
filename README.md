# Sentinel

> A local-first multimodal AI system for insider-threat investigation assistance, evidence correlation, anomaly detection, and incident reconstruction.

---

## Overview

Sentinel is a **self-hosted, local-first investigation platform** designed to assist human investigators in analysing complex insider-threat scenarios involving multiple heterogeneous evidence sources.

Instead of siloing evidence into separate tools, Sentinel ingests data across multiple modalities (cyber logs, surveillance video, physical badge events, and narrative documents), normalises observations into a canonical schema, and uses cross-modal AI models to surface suspicious activity patterns, timeline anomalies, and investigative leads.

> **Investigative Signals — Not Automated Verdicts**: Sentinel is an investigative aid. All AI outputs represent prioritized leads, anomaly scores, and correlated timelines to guide human analysts. Human investigators remain responsible for all conclusions and decisions.

---

## Implementation Status & Roadmap

| Capability / Component | Status | Details |
|---|---|---|
| **Video AI (TimeSformer)** | 🟢 **Implemented** | Space-Time Transformer (`Nikeytas/timesformer-best-crime-detector`) fine-tuned on UCF-Crime (88.68% F1 score), frame extraction, temporal sliding window, CLI & REST endpoints |
| **Cyber AI (Log Anomaly Detection)** | 🟢 **Implemented** | CERT Insider Threat Dataset r4.2 pipeline; Isolation Forest baseline & supervised Random Forest with 97.65% ROC-AUC (see [`CYBER_MODEL_REPORT.md`](CYBER_MODEL_REPORT.md)) |
| **Document AI Baseline** | 🟢 **Implemented** | Narrative text parser, entity and keyword extraction, claim scoring ([`ai/documents/train.py`](ai/documents/train.py)) |
| **Cross-Modal Correlation Engine** | 🟢 **Implemented** | Entity resolution, temporal window clustering, automated contradiction detection (impossible travel, uncredentialed presence), and Cytoscape-compatible evidence graph generation ([`ai/correlation/`](ai/correlation/)) |
| **Case & Evidence Management API** | 🟢 **Implemented** | Local-first REST API and service layer for case CRUD, evidence ingestion, SHA-256 cryptographic verification, tamper detection, and chain-of-custody audit logging ([`backend/app/api/`](backend/app/api/)) |
| **End-to-End Demo Pipeline** | 🟢 **Implemented** | One-command generation of multimodal synthetic data, training, and correlation ([`scripts/run_all.py`](scripts/run_all.py)) |
| **FastAPI Backend Core & Endpoints** | 🟢 **Implemented** | REST API with health check, interactive OpenAPI docs (`/docs`), `/api/video/*`, `/cases`, and `/evidence` routes |
| **Test Suite** | 🟢 **Implemented** | 15+ automated pytest tests covering TimeSformer video inference, Case & Evidence API lifecycle, cryptographic tamper detection, entity resolution, and timeline correlation |
| **Investigator Dashboard (Frontend)** | 🟡 **In Progress** | React 18 + TypeScript + Vite project scaffolding with component architecture (see [`frontend/README.md`](frontend/README.md)) |
| **PostgreSQL & Redis Orchestration** | 📋 **Planned** | Docker Compose service topology ready for Celery background tasks and database persistence |

---

## Quickstart

### Prerequisites

- **Python**: 3.11 or higher
- **Node.js**: 18+ (for frontend dashboard development)
- **Docker & Docker Compose**: (Optional, for running PostgreSQL, Redis, and MLflow)
- **Hardware**:
  - **CPU**: Sufficient for all tabular cyber models, document AI, correlation pipelines, and TimeSformer fallback inference.
  - **GPU / CUDA**: Recommended for high-speed video inference with TimeSformer.

### 1. Installation

Clone the repository and set up a Python virtual environment:

```bash
git clone https://github.com/your-org/sentinel.git
cd sentinel

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate

# Install AI & ML dependencies
pip install -r requirements-ml.txt

# Install backend dependencies
pip install -r backend/requirements.txt
```

### 2. Run the Complete End-to-End Demo

Run the automated pipeline to generate synthetic multimodal data, train the baseline models, and perform cross-modal correlation:

```bash
python scripts/run_all.py
```

This single command will:
1. Generate synthetic cyber logs, video features, and document records under `data/generated/`.
2. Train the Cyber AI anomaly detector (`ai/cyber/train.py`).
3. Train the Video AI baseline model (`ai/video/train.py`).
4. Train the Document AI entity extractor (`ai/documents/train.py`).
5. Execute the Correlation Engine (`ai/correlation/run.py`), outputting correlated incident clusters to `artifacts/correlation/events.jsonl`.

### 3. Run the Video Crime Detector (TimeSformer)

Analyze surveillance footage using the integrated Time-Space Transformer:

```bash
# Analyze sample CCTV footage
python ai/video/detect_crime.py \
    --video data/sample/real_burglary.mp4 \
    --case-id CASE-2026-001 \
    --threshold 0.5 \
    --output artifacts/video/crime_analysis.json \
    --events-output artifacts/video/crime_events.jsonl
```

### 4. Launch the FastAPI Backend Server

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Once running, access the interactive API documentation:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

### 5. Run the Test Suite

```bash
pytest tests/ -v
```

---

## System Architecture

Sentinel follows a strict **self-hosted, local-first** design. No investigation data or evidence leaves your infrastructure.

```
React Frontend (Investigator Dashboard)
       │
       │  REST / HTTP (JSON)
       ▼
FastAPI Backend (app/main.py)
       │
       ├── Case & Evidence Management
       ├── Video Crime Detection API (/api/video/*)
       ├── Analysis Orchestration
       └── Cryptographic Audit Trail (SHA-256)
               │
       ┌───────┴────────┐
       ▼                ▼
 PostgreSQL        Local Evidence Store
 (metadata,         (raw videos, logs,
  events, audit)     scanned PDFs)
       │
       ▼
Multimodal AI Layer
       ├── Cyber AI       (CERT r4.2 Random Forest & Isolation Forest)
       ├── Video AI       (TimeSformer Space-Time Transformer)
       └── Document AI    (Entity parsing & claim extraction)
               │
               ▼
Canonical Event Normalisation (JSON-Schema)
               │
               ▼
Cross-Modal Correlation Engine (ai/correlation/run.py)
       ├── Entity Resolution (usernames, badge IDs, actors)
       ├── Temporal Clustering (sliding incident windows)
       └── Incident Timeline Construction
               │
               ▼
Human Investigator Dashboard (Review, Triaging, Reporting)
```

---

## Core Capabilities & AI Modules

### 1. Video AI (`ai/video/`)
- **Model**: [`Nikeytas/timesformer-best-crime-detector`](https://huggingface.co/Nikeytas/timesformer-best-crime-detector) (Time-Space Transformer).
- **Benchmark**: Fine-tuned on the UCF-Crime dataset (~1,900 surveillance videos) achieving **88.68% F1 score** and **84.25% accuracy**.
- **Detection Scope**: Physical anomalies and crimes including burglary, fighting, assault, theft, arson, vandalism, explosion, and unauthorized presence.
- **Inference**: Uses a temporal sliding window (default: 2.0s duration, 1.0s stride) sampling 16 frames uniformly at 224×224 resolution.
- **Reference**: Detailed usage in [`ai/video/README.md`](ai/video/README.md).

### 2. Cyber AI (`ai/cyber/`)
- **Dataset**: CERT Insider Threat Test Dataset r4.2 (~32 million raw records preprocessed into 330,452 user-day observations).
- **Models**:
  - **Isolation Forest**: Unsupervised baseline for rare behavioural patterns.
  - **Random Forest**: Supervised classifier achieving **97.65% ROC-AUC**, **43.16% F1 score**, and **47.19% Average Precision** on a chronological 80/20 test split.
- **Features**: Daily counts of logon/logoff events, file access records, removable USB connections, web browsing activities, and email volumes.
- **Reference**: Full training and benchmark report in [`CYBER_MODEL_REPORT.md`](CYBER_MODEL_REPORT.md).

### 3. Document AI (`ai/documents/`)
- Ingests text documents, incident summaries, and employee statements.
- Extracts named entities, accounts, and suspicious claims.
- Maps narrative claims to canonical timestamps for contradiction detection against cyber and video logs.

### 4. Correlation Engine (`ai/correlation/`)
- Ingests canonical events emitted across all modalities.
- Applies entity resolution and sliding temporal window clustering (e.g., matching a physical badge swipe, CCTV corridor detection, and privileged file export occurring within a 60-minute window).
- Outputs structured incident narratives to `artifacts/correlation/events.jsonl`.

---

## REST API Overview

The FastAPI backend exposes endpoints for evidence processing, case management, model status, and cryptographic verification:

| Method | Endpoint | Description | Status |
|---|---|---|---|
| `GET` | `/` | Service identifier and status | 🟢 Active |
| `GET` | `/health` | Health probe (database, redis, storage check) | 🟢 Active |
| `GET` | `/cases` | List investigation cases with pagination and status filters | 🟢 Active |
| `POST` | `/cases` | Create a new investigation case | 🟢 Active |
| `GET` | `/cases/{id}` | Get case details, evidence count, and metadata | 🟢 Active |
| `PATCH` | `/cases/{id}` | Update case status, description, or title | 🟢 Active |
| `DELETE` | `/cases/{id}` | Delete case and associated evidence records | 🟢 Active |
| `POST` | `/evidence` | Ingest evidence file, compute SHA-256 hash, and log audit entry | 🟢 Active |
| `GET` | `/evidence` | List all evidence items, optionally filtered by `case_id` | 🟢 Active |
| `GET` | `/evidence/{id}` | Retrieve evidence metadata and original hash | 🟢 Active |
| `GET` | `/evidence/{id}/verify` | Cryptographically re-verify SHA-256 hash against stored fingerprint | 🟢 Active |
| `GET` | `/evidence/{id}/audit` | Retrieve complete chain-of-custody audit log | 🟢 Active |
| `DELETE` | `/evidence/{id}` | Delete evidence file and record deletion in audit log | 🟢 Active |
| `GET` | `/api/video/model-info` | Returns TimeSformer architecture, device (CPU/CUDA), and benchmark metrics | 🟢 Active |
| `POST` | `/api/video/analyze` | Analyzes a video path on local disk | 🟢 Active |
| `POST` | `/api/video/analyze-upload` | Multipart upload and analysis of surveillance video | 🟢 Active |
| `POST` | `/api/video/download-weights` | Triggers background download of TimeSformer Hugging Face weights | 🟢 Active |
| `GET` | `/timeline/{case_id}` | Retrieve correlated multimodal incident timeline | 🟡 In Progress |

See [`docs/architecture/api-contract.md`](docs/architecture/api-contract.md) for the complete API specifications.

---

## Configuration

Configuration is managed via environment variables. Copy the provided template to create your `.env` file:

```bash
cp .env.example .env
```

Key environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `BACKEND_PORT` | `8000` | Port for the FastAPI backend server |
| `FRONTEND_PORT` | `5173` | Port for the Vite frontend development server |
| `DATABASE_URL` | `postgresql://...` | Connection string for PostgreSQL metadata storage |
| `REDIS_HOST` | `localhost` | Redis host for Celery background tasks |
| `STORAGE_PATH` | `./local-evidence-store` | Local directory for storing raw evidence files |
| `MAX_UPLOAD_SIZE_MB` | `500` | Maximum upload size for video and document files |
| `MLFLOW_TRACKING_URI` | `http://localhost:5000` | MLflow experiment tracking server |

---

## Docker & Developer Tools

A [`docker-compose.yml`](docker-compose.yml) and [`Makefile`](Makefile) are provided for managing development services:

```bash
# Initial project setup (copies .env and verifies dependencies)
make setup

# Start PostgreSQL and Redis infrastructure containers
make up

# Start FastAPI backend in development mode
make backend-dev

# View service logs
make logs

# Stop all services
make down
```

---

## Repository Structure

```
sentinel/
├── README.md                           # Project overview, quickstart, and documentation hub
├── TRAINING.md                         # Detailed guide for model training and synthetic data
├── CYBER_MODEL_REPORT.md               # CERT r4.2 evaluation results, methodology, and viva Q&A
├── LICENSE                             # MIT License
├── Makefile                            # Developer convenience targets
├── docker-compose.yml                  # Docker Compose services (Postgres, Redis, MLflow)
├── requirements-ml.txt                 # AI/ML dependencies (PyTorch, Transformers, scikit-learn)
├── .env.example                        # Environment variable configuration template
│
├── ai/                                 # AI & Machine Learning pipelines
│   ├── cyber/                          # CERT dataset preprocessing, labeling, and training
│   ├── video/                          # TimeSformer crime detector, feature extraction, and CLI
│   ├── documents/                      # Document text parsing, entity extraction, and claim scoring
│   └── correlation/                    # Cross-modal correlation and incident timeline clustering
│
├── backend/                            # FastAPI REST API & orchestration service
│   ├── app/
│   │   ├── main.py                     # Application entry point and router registration
│   │   ├── api/                        # API route handlers (video, cases, evidence, etc.)
│   │   ├── schemas/                    # Pydantic request/response schemas
│   │   └── services/                   # Business logic and model service wrappers
│   └── requirements.txt                # Backend web dependencies
│
├── frontend/                           # React + TypeScript investigator dashboard
│   ├── src/                            # Components, pages, hooks, services
│   └── package.json                    # Frontend npm dependencies and scripts
│
├── data/                               # Data schemas, synthetic outputs, and sample files
│   ├── schemas/event.schema.json       # Canonical Event JSON Schema
│   └── sample/                         # Sample video clips for local verification
│
├── artifacts/                          # Saved model weights, metrics, and correlation outputs
│   ├── models/timesformer/             # Downloaded TimeSformer model weights
│   ├── cyber/                          # Cyber model artifacts and evaluation metrics
│   └── correlation/                    # Correlated event timelines (events.jsonl)
│
├── docs/                               # Architectural and research documentation
│   ├── architecture/                   # System design, API contract, database schema, event schema
│   ├── research/                       # Research methodology, datasets, and evaluation metrics
│   └── decisions/                      # Architecture Decision Records (ADRs)
│
├── scripts/                            # Utility and orchestration scripts
│   ├── run_all.py                      # One-command demo pipeline runner
│   ├── generate_demo_data.py           # Synthetic multimodal data generator
│   └── threshold_report.py             # Classification threshold analysis
│
└── tests/                              # Automated test suites
    └── test_timesformer_detector.py    # TimeSformer unit tests and FastAPI integration tests
```

---

## Documentation Hub

- **Training & Running Baselines**: [`TRAINING.md`](TRAINING.md)
- **Cyber Model Evaluation & Defense Q&A**: [`CYBER_MODEL_REPORT.md`](CYBER_MODEL_REPORT.md)
- **Video AI Documentation**: [`ai/video/README.md`](ai/video/README.md)
- **Backend Architecture**: [`backend/README.md`](backend/README.md)
- **Frontend Architecture**: [`frontend/README.md`](frontend/README.md)
- **System Design Blueprint**: [`docs/architecture/system-design.md`](docs/architecture/system-design.md)
- **API Contract**: [`docs/architecture/api-contract.md`](docs/architecture/api-contract.md)
- **Database Schema**: [`docs/architecture/database-schema.md`](docs/architecture/database-schema.md)
- **Canonical Event Schema**: [`docs/architecture/event-schema.md`](docs/architecture/event-schema.md)
- **Research Methodology**: [`docs/research/methodology.md`](docs/research/methodology.md)
- **Dataset Strategy**: [`docs/research/datasets.md`](docs/research/datasets.md)
- **Local-First Architecture Decision (ADR-002)**: [`docs/decisions/ADR-002-local-first.md`](docs/decisions/ADR-002-local-first.md)

---

## Privacy and Data Handling

- **Zero Cloud Leakage**: All evidence files, model inferences, and audit records remain within your self-hosted infrastructure.
- **No Telemetry**: Sentinel includes no telemetry, analytics beacons, or remote tracking.
- **Integrity Verification**: Evidence files are hashed with SHA-256 upon ingestion to establish a verifiable chain of custody.
- **Confidentiality**: Real investigation evidence, CCTV footage, and private employee records must never be committed to public repositories.

---

## Disclaimer

Sentinel is an **investigative decision-support system** designed to assist qualified human analysts.

AI outputs produced by Sentinel represent:
- Prioritized investigative leads
- Multi-source anomaly indicators
- Evidence timeline correlations

Sentinel does **not** make autonomous determinations of guilt, malice, or employment misconduct. All conclusions and investigative actions remain the sole responsibility of human investigators operating within applicable legal frameworks.

---

## License

This project is licensed under the MIT License — see the [`LICENSE`](LICENSE) file for details.

Copyright (c) 2026 Sentinel Contributors

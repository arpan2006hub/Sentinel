# Sentinel

> A local-first multimodal AI system for insider-threat investigation assistance, evidence correlation, anomaly detection, and incident reconstruction.

---

## Overview

Sentinel is a **self-hosted, local-first investigation platform** designed to assist human investigators in analysing complex insider-threat scenarios involving multiple heterogeneous evidence sources.

The system is currently in its **initial foundation stage**. This repository contains the architectural blueprint, directory structure, development conventions, and documentation scaffolding for future implementation.

---

## Problem

Insider-threat investigations are fundamentally cross-domain. An investigator examining a suspected insider-threat incident may need to simultaneously review:

- Authentication and system-access logs
- File-access records
- USB and peripheral-device events
- Network, DNS, and HTTP activity
- Physical badge and door-access records
- CCTV or video footage from relevant areas
- Scanned documents, incident reports, and employee statements

These evidence sources live in different formats, different systems, and different timelines. A human investigator working through them manually faces an enormous correlation burden. Evidence relationships that span multiple sources may not surface without systematic cross-referencing.

Sentinel is designed to reduce this burden by automatically normalising, correlating, and structuring evidence — and by surfacing investigative leads that a human investigator can then evaluate and act upon.

---

## Core Idea

Sentinel ingests evidence from multiple modalities, normalises all observations into a canonical event format, and then applies cross-source correlation to surface suspicious activity patterns, timeline anomalies, and evidence relationships.

All AI outputs are **investigative signals** — not verdicts.

Human investigators remain responsible for all investigative decisions.

---

## Key Capabilities *(planned)*

| Capability | Description |
|---|---|
| **Multimodal ingestion** | Accept CCTV video, auth logs, file-access logs, USB events, network logs, physical badge data, PDFs, and documents |
| **Event normalisation** | Map all evidence sources to a canonical event schema |
| **Anomaly detection** | Identify unusual activity patterns per evidence source |
| **Cross-source correlation** | Connect related events across different evidence types |
| **Timeline construction** | Build a unified, sortable incident timeline |
| **Evidence graph** | Represent entity relationships and evidence connections |
| **Contradiction detection** | Surface inconsistencies across evidence sources |
| **Audit trail** | Maintain a cryptographic integrity record of all evidence |
| **Investigator dashboard** | Present evidence-backed leads to a human investigator |

> **Status**: None of these capabilities are implemented yet. This repository is currently a project foundation.

---

## Local-First Architecture

Sentinel is designed as a **self-hosted, local-first application**.

```
GitHub Repository
       │
       │  clone
       ▼
Organisation / User System
       │
       ├── Sentinel Frontend    (React)
       ├── Sentinel Backend     (FastAPI)
       ├── PostgreSQL           (structured metadata & events)
       ├── Local Evidence Store (files, video, documents)
       ├── AI Processing        (cyber / video / document AI)
       └── Audit / Integrity    (SHA-256 hashes & audit records)
```

**There is no mandatory centralised Sentinel server.**
**There is no mandatory cloud database.**
**There is no hidden telemetry.**

Each organisation clones the repository and operates its own independent instance. Investigation data remains under the organisation's control at all times.

---

## Evidence Sources *(planned)*

- **Cyber logs** — authentication, file-access, USB/device, network, DNS, HTTP, process events
- **Video / CCTV** — recorded surveillance footage from relevant physical areas
- **Physical access** — badge reader and door-access events
- **Documents** — PDFs, scanned reports, incident summaries, employee statements

---

## Evidence Integrity

Sentinel plans to implement a cryptographic evidence-integrity mechanism inspired by chain-of-custody principles:

```
Evidence File
     │
     ├── Evidence ID          (unique identifier)
     ├── SHA-256 Hash         (integrity fingerprint at ingest)
     ├── Ingest Timestamp
     ├── Source Metadata
     └── Audit History
             │
             ▼
       Investigation Record
```

- Evidence files are hashed with SHA-256 at ingest time.
- Any unexpected modification to an evidence file can be detected by re-hashing and comparing.
- All processing operations should eventually produce an audit record.

> This mechanism is planned and not yet implemented.

---

## Planned System Architecture

```
React Frontend  (Investigator Dashboard)
       │
       │  REST / HTTP
       ▼
FastAPI Backend
       │
       ├── Case Management
       ├── Evidence Ingestion
       ├── Analysis Orchestration
       └── Audit / Integrity
               │
       ┌───────┴────────┐
       ▼                ▼
 PostgreSQL       Local / Object
 (metadata,       Evidence Storage
  events,         (files, video,
  audit)          documents)
       │
       ▼
AI Processing Layer
       ├── Cyber AI          (log analysis, anomaly detection)
       ├── Video AI          (object detection, activity recognition)
       └── Document AI       (OCR, entity extraction, contradiction)
               │
               ▼
       Event Normalisation
       (Canonical Event Schema)
               │
               ▼
       Correlation Engine
       ├── Anomaly Detection
       ├── Timeline Construction
       └── Evidence Graph
               │
               ▼
       Investigator Dashboard
       (Evidence-backed leads for human review)
```

---

## Technology Stack *(planned)*

### Frontend
- React + TypeScript
- Vite
- Tailwind CSS
- React Query
- React Flow / Cytoscape.js (evidence graph)
- Recharts (timeline, analytics)
- Axios

### Backend
- Python + FastAPI
- Pydantic
- SQLAlchemy + Alembic
- PostgreSQL
- Redis + Celery (background workers)

### AI / ML
- PyTorch
- scikit-learn
- OpenCV
- Hugging Face Transformers
- Sentence Transformers
- spaCy
- pandas / NumPy
- YOLO (computer-vision detection)

### MLOps
- MLflow (experiment tracking)

### Infrastructure
- Docker + Docker Compose
- GitHub Actions (CI)

---

## Repository Structure

```
sentinel/
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── docker-compose.yml
├── Makefile
│
├── docs/
│   ├── architecture/       System design, schema, API contract
│   ├── research/           Datasets, methodology, evaluation
│   └── decisions/          Architecture Decision Records (ADRs)
│
├── frontend/               React + TypeScript investigator dashboard
├── backend/                FastAPI backend + evidence/case APIs
├── ai/                     Cyber / Video / Document AI + Correlation
├── data/                   Schemas, sample data, dataset docs
├── mlops/                  MLflow, model registry, experiments
├── scripts/                Developer utilities
├── tests/                  Integration tests + fixtures
└── .github/                Workflows, issue templates, PR template
```

---

## Research Direction

Sentinel is being developed as a research-oriented student project exploring:

> **Can multimodal evidence correlation improve the detection and explanation of insider-threat activity compared with analysing individual evidence sources independently?**

Planned ablation study:

| Model | Evidence Sources |
|---|---|
| A | Cyber logs only |
| B | Cyber + temporal correlation |
| C | Cyber + physical evidence |
| D | Cyber + physical + document evidence |

See [`docs/research/methodology.md`](docs/research/methodology.md) for full research design.

---

## Dataset Strategy

Sentinel plans to use publicly available research datasets as the basis for development and evaluation:

- **CERT Insider Threat Test Dataset** — cyber log baseline
- **LANL Cybersecurity Dataset** — network authentication events
- **VAST 2009 Grand Challenge** — multimodal investigation scenario
- **UCF-Crime** — video anomaly detection
- **DocVQA** — document understanding
- **MITRE ATT&CK STIX** — threat-intelligence knowledge graph

> ⚠️ No real investigation data, real CCTV footage, or private employee information should ever be committed to this repository.

See [`docs/research/datasets.md`](docs/research/datasets.md) for full dataset documentation.

---

## Development Status

| Component | Status |
|---|---|
| Repository structure | ✅ Initialised |
| Architecture documentation | ✅ Draft |
| Event schema | ✅ Draft |
| Backend (FastAPI) | 🏗️ Foundation only |
| Frontend (React) | 🏗️ Foundation only |
| Cyber AI | ❌ Not started |
| Video AI | ❌ Not started |
| Document AI | ❌ Not started |
| Correlation engine | ❌ Not started |
| PostgreSQL models | ❌ Not started |
| Evidence integrity | ❌ Not started |
| Authentication | ❌ Not started |
| CI/CD | ❌ Not started |

---

## Team Responsibilities

| Member | Role | Ownership |
|---|---|---|
| **Member 1 — AI/ML** | Cyber AI, Video AI, Document AI, Correlation, Evaluation | `/ai/` |
| **Member 2 — Full Stack / Frontend** | Dashboard, Case UI, Timeline, Evidence Graph | `/frontend/` |
| **Member 3 — UI/UX + DevOps** | UX, Design System, Docker, CI/CD, Infrastructure | `/.github/`, Docker |
| **Member 4 — Backend + Security** | FastAPI, PostgreSQL, APIs, Audit/Integrity Architecture | `/backend/` |

---

## Privacy and Data Handling

- All investigation evidence remains on the self-hosted instance.
- No investigation data is transmitted to any Sentinel-operated service.
- No telemetry is collected.
- Evidence files are never uploaded to the public repository.
- Secrets and credentials must never be committed to Git.

See [`docs/decisions/ADR-002-local-first.md`](docs/decisions/ADR-002-local-first.md) for the full rationale.

---

## Disclaimer

Sentinel is designed to **assist human investigation** — not to replace human judgment.

AI outputs produced by Sentinel should be interpreted as:
- investigative leads
- anomaly signals
- evidence correlations
- activity requiring further investigation

Sentinel does **not** automatically determine that any person is guilty, malicious, or responsible for an incident. All investigative conclusions are the responsibility of human investigators acting within applicable legal and organisational frameworks.

---

## License

MIT License — see [`LICENSE`](LICENSE).

Copyright (c) 2026 Sentinel Contributors

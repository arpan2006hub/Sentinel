# System Design — Sentinel

> **Status**: Planned architecture. Not yet implemented.

---

## Overview

This document describes the planned system architecture for Sentinel, a local-first multimodal AI system for insider-threat investigation assistance.

---

## Guiding Principles

1. **Local-first** — investigation data remains under the organisation's control at all times.
2. **Human-in-the-loop** — AI outputs are investigative signals, not verdicts.
3. **Evidence integrity** — cryptographic hashes enable detection of unexpected evidence modification.
4. **Modular AI** — each evidence modality has its own AI processing path; all paths emit a canonical event format.
5. **Separation of concerns** — evidence files are stored separately from structured metadata.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Investigator Browser                         │
│                  React + TypeScript Frontend                    │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────────┐  │
│   │  Cases   │ │Evidence  │ │ Timeline │ │  Evidence Graph │  │
│   │Dashboard │ │Explorer  │ │  View    │ │   + Anomalies   │  │
│   └──────────┘ └──────────┘ └──────────┘ └─────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │  REST / HTTP (JSON)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                             │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │  Cases  │ │Evidence  │ │Analysis  │ │ Audit / Integrity │   │
│  │   API   │ │   API    │ │   API    │ │      Service      │   │
│  └─────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              Service / Repository Layer                │    │
│  └────────────────────────────────────────────────────────┘    │
└───────┬───────────────────────────────────┬─────────────────────┘
        │                                   │
        ▼                                   ▼
┌───────────────┐                 ┌──────────────────────────┐
│  PostgreSQL   │                 │   Local / Object Store   │
│               │                 │                          │
│  cases        │                 │  /evidence-store/        │
│  evidence     │                 │    ├── video/            │
│  events       │                 │    ├── documents/        │
│  entities     │                 │    ├── logs/             │
│  anomalies    │                 │    └── images/           │
│  audit_logs   │                 │                          │
│  ...          │                 │  Files referenced by     │
│               │                 │  file_hash in PostgreSQL │
└───────────────┘                 └──────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AI Processing Layer                          │
│  (Background workers via Redis + Celery)                       │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Cyber AI    │  │  Video AI    │  │    Document AI       │  │
│  │              │  │              │  │                      │  │
│  │ Preprocessing│  │ Preprocessing│  │  OCR                 │  │
│  │ Feature Ext. │  │ Detection    │  │  Entity Extraction   │  │
│  │ Anomaly Det. │  │ Anomaly Det. │  │  Contradiction Det.  │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                 │                      │              │
│         └─────────────────┴──────────────────────┘              │
│                           │                                     │
│                           ▼                                     │
│              ┌────────────────────────┐                         │
│              │  Event Normalisation   │                         │
│              │  (Canonical Schema)    │                         │
│              └────────────┬───────────┘                         │
│                           │                                     │
│                           ▼                                     │
│              ┌────────────────────────┐                         │
│              │   Correlation Engine   │                         │
│              │                        │                         │
│              │  Entity Resolution     │                         │
│              │  Temporal Correlation  │                         │
│              │  Evidence Graph        │                         │
│              │  Timeline Construction │                         │
│              │  Anomaly Scoring       │                         │
│              └────────────┬───────────┘                         │
└───────────────────────────┼─────────────────────────────────────┘
                            │
                            ▼
                 Structured results written
                 back to PostgreSQL for
                 presentation via the API
```

---

## Component Descriptions

### Frontend

The investigator-facing dashboard. Built with React + TypeScript.

Planned views:
- **Case Dashboard** — list and manage investigation cases
- **Evidence Explorer** — browse, upload, and inspect evidence
- **Timeline** — unified chronological event view
- **Evidence Graph** — entity/event relationship visualisation (React Flow / Cytoscape.js)
- **Anomaly Details** — individual anomaly drill-down with supporting evidence
- **Investigation Summary** — synthesised investigative leads for human review

### Backend (FastAPI)

The REST API layer. Handles:
- Case creation and management
- Evidence ingestion and hash verification
- Analysis job orchestration
- Query endpoints for events, anomalies, timelines, graphs
- Audit record management

### PostgreSQL

Stores all structured data:
- Case and evidence metadata
- Normalised events (from all modalities)
- Entity registry
- Anomaly records
- Analysis run history
- Audit log

Does **not** store raw evidence files.

### Local / Object Storage

Stores raw evidence files on the local filesystem (or eventually S3-compatible object storage).

Evidence files are referenced in PostgreSQL by their `file_hash` (SHA-256).

### AI Processing

Three modality-specific pipelines, each producing normalised events:

| Pipeline | Input | Output |
|---|---|---|
| Cyber AI | Auth logs, file logs, USB, network, DNS | Normalised events |
| Video AI | CCTV footage, video files | Normalised events |
| Document AI | PDFs, scanned documents, statements | Normalised events |

### Correlation Engine

Cross-source analysis that operates on the unified event store:
- **Entity resolution** — match actors, objects, locations across modalities
- **Temporal correlation** — identify events that cluster in time
- **Evidence graph** — build and maintain a relationship graph
- **Timeline construction** — produce a sorted, annotated investigation timeline
- **Anomaly scoring** — score suspicious patterns with confidence levels

---

## Evidence Integrity Architecture

```
Evidence File Uploaded
         │
         ├── Compute SHA-256 hash
         ├── Assign Evidence ID
         ├── Record: evidence_id, file_hash, timestamp, source_type, metadata
         │
         ▼
   PostgreSQL: evidence table
   { evidence_id, file_hash, created_at, ingested_at, ... }
         │
         ├── Store file at: /evidence-store/<case_id>/<evidence_id>/<filename>
         │
         ├── Audit record created: "evidence_ingested"
         │
         ▼
   On every access / analysis run:
         ├── Re-hash file
         ├── Compare with stored hash
         └── Flag if mismatch → integrity alert
```

This mechanism is **planned** and not yet implemented.

---

## Data Flow

```
1. Investigator uploads evidence file via UI
2. Backend receives file, computes SHA-256 hash
3. Evidence metadata + hash stored in PostgreSQL
4. File stored in local evidence store
5. Audit record created
6. Analysis job queued to Redis
7. AI worker picks up job
8. Modality AI pipeline processes evidence
9. Extracted events written to events table (normalised)
10. Correlation engine runs across all events for the case
11. Anomalies, timeline, graph updated
12. Investigator views results via dashboard
13. Investigator makes investigation decisions
```

---

## Security Considerations (Planned)

- Secrets managed via environment variables (`.env`)
- Authentication and authorisation to be implemented
- Evidence files should not be publicly accessible
- All important operations should produce audit records
- AI outputs should never be treated as definitive verdicts

---

## Deployment Model

Sentinel is designed for self-hosted, local-first deployment:

```
docker compose up
```

No external Sentinel service is required.
No evidence data is transmitted outside the local instance.

---

*This document will be updated as implementation progresses.*

# Database Schema — Sentinel

> **Status**: Planned conceptual schema. No database models are implemented yet.

---

## Overview

Sentinel uses **PostgreSQL** as its primary relational database for all structured metadata, normalised events, entity relationships, anomaly records, and audit logs.

**PostgreSQL does not store raw evidence files.** Evidence files (video, PDFs, images, raw logs) are stored in local filesystem or object storage. PostgreSQL holds the metadata, including a SHA-256 hash for integrity verification.

---

## Planned Entities

```
users
cases
evidence
events
entities
relationships
anomalies
investigations
analysis_runs
audit_logs
```

---

## Entity Definitions

### `users`

Internal user accounts for investigators accessing the Sentinel dashboard.

| Column | Type | Description |
|---|---|---|
| `user_id` | UUID (PK) | Unique user identifier |
| `username` | TEXT (unique) | Login username |
| `email` | TEXT (unique) | Email address |
| `role` | TEXT | Role: `investigator`, `admin`, etc. |
| `created_at` | TIMESTAMPTZ | Account creation time |
| `last_login` | TIMESTAMPTZ | Last successful login |
| `is_active` | BOOLEAN | Whether the account is active |

---

### `cases`

An investigation case groups all related evidence, events, and analysis.

| Column | Type | Description |
|---|---|---|
| `case_id` | UUID (PK) | Unique case identifier |
| `title` | TEXT | Human-readable case title |
| `description` | TEXT | Case summary |
| `status` | TEXT | `open`, `under_review`, `closed`, `archived` |
| `created_by` | UUID (FK → users) | Investigator who created the case |
| `created_at` | TIMESTAMPTZ | Case creation time |
| `updated_at` | TIMESTAMPTZ | Last modification time |
| `metadata` | JSONB | Flexible additional case metadata |

---

### `evidence`

An evidence record represents one uploaded piece of evidence (a file).

| Column | Type | Description |
|---|---|---|
| `evidence_id` | UUID (PK) | Unique evidence identifier |
| `case_id` | UUID (FK → cases) | Associated case |
| `source_type` | TEXT | Evidence category: `endpoint_log`, `cctv_video`, `pdf_document`, etc. |
| `file_name` | TEXT | Original filename |
| `file_path` | TEXT | Path within the local evidence store |
| `file_hash` | TEXT | SHA-256 hash of the evidence file at ingest time |
| `file_size_bytes` | BIGINT | File size |
| `created_at` | TIMESTAMPTZ | Time the evidence record was created |
| `ingested_at` | TIMESTAMPTZ | Time the file was processed/ingested |
| `uploaded_by` | UUID (FK → users) | Investigator who uploaded the evidence |
| `processing_status` | TEXT | `pending`, `processing`, `completed`, `failed` |
| `metadata` | JSONB | Flexible source-specific metadata (device ID, camera ID, date range, etc.) |

**Note**: `file_hash` is the primary integrity mechanism. Re-computing the hash of the stored file and comparing to this value detects unexpected modification.

---

### `events`

Normalised events extracted from evidence by the AI processing pipelines.

All events conform to the canonical event schema regardless of their source modality.

| Column | Type | Description |
|---|---|---|
| `event_id` | UUID (PK) | Unique event identifier |
| `case_id` | UUID (FK → cases) | Associated case |
| `evidence_id` | UUID (FK → evidence) | Source evidence record |
| `timestamp_start` | TIMESTAMPTZ | Event start time |
| `timestamp_end` | TIMESTAMPTZ | Event end time (nullable) |
| `actor_id` | TEXT | Actor identifier (nullable) |
| `action` | TEXT | Action type from controlled vocabulary |
| `object_id` | TEXT | Object acted upon (nullable) |
| `location_id` | TEXT | Location (nullable) |
| `source_type` | TEXT | Source modality |
| `confidence` | FLOAT | Extraction confidence [0.0 – 1.0] |
| `metadata` | JSONB | Modality-specific additional data |
| `created_at` | TIMESTAMPTZ | When this event record was created |
| `analysis_run_id` | UUID (FK → analysis_runs) | Which analysis run produced this event |

---

### `entities`

The entity registry: unique actors, objects, and locations resolved across all evidence sources.

Entity resolution maps ambiguous actor references (username, badge ID, face cluster, name in document) to a single canonical entity.

| Column | Type | Description |
|---|---|---|
| `entity_id` | UUID (PK) | Unique entity identifier |
| `case_id` | UUID (FK → cases) | Associated case |
| `entity_type` | TEXT | `person`, `device`, `file`, `location`, `network_host` |
| `display_name` | TEXT | Human-readable label |
| `aliases` | JSONB | List of identifiers mapped to this entity |
| `metadata` | JSONB | Additional entity attributes |
| `created_at` | TIMESTAMPTZ | Record creation time |

---

### `relationships`

Edges in the evidence graph: directed relationships between entities, grounded in specific events.

| Column | Type | Description |
|---|---|---|
| `relationship_id` | UUID (PK) | Unique relationship identifier |
| `case_id` | UUID (FK → cases) | Associated case |
| `source_entity_id` | UUID (FK → entities) | The entity that initiates the relationship |
| `target_entity_id` | UUID (FK → entities) | The entity that is the target |
| `relationship_type` | TEXT | e.g. `accessed`, `transferred_to`, `co-located_with`, `communicated_with` |
| `event_ids` | UUID[] | Events that support this relationship |
| `confidence` | FLOAT | Confidence in this relationship |
| `metadata` | JSONB | Additional relationship attributes |
| `created_at` | TIMESTAMPTZ | Record creation time |

---

### `anomalies`

Individual anomaly signals detected by the AI pipelines or correlation engine.

| Column | Type | Description |
|---|---|---|
| `anomaly_id` | UUID (PK) | Unique anomaly identifier |
| `case_id` | UUID (FK → cases) | Associated case |
| `anomaly_type` | TEXT | Category: `temporal`, `behavioral`, `access_pattern`, `cross_source`, etc. |
| `description` | TEXT | Human-readable description of the anomaly |
| `severity` | TEXT | `low`, `medium`, `high` |
| `confidence` | FLOAT | Confidence score [0.0 – 1.0] |
| `supporting_event_ids` | UUID[] | Events that contribute to this anomaly signal |
| `contradicting_event_ids` | UUID[] | Events that contradict or contextualise this anomaly |
| `analysis_run_id` | UUID (FK → analysis_runs) | Which analysis run produced this anomaly |
| `metadata` | JSONB | Additional anomaly attributes |
| `created_at` | TIMESTAMPTZ | Record creation time |

---

### `analysis_runs`

A record of each time an AI analysis job is executed for a case.

| Column | Type | Description |
|---|---|---|
| `analysis_run_id` | UUID (PK) | Unique run identifier |
| `case_id` | UUID (FK → cases) | Associated case |
| `evidence_ids` | UUID[] | Evidence records included in this run |
| `status` | TEXT | `queued`, `running`, `completed`, `failed` |
| `started_at` | TIMESTAMPTZ | Run start time |
| `completed_at` | TIMESTAMPTZ | Run completion time |
| `triggered_by` | UUID (FK → users) | User who triggered the analysis |
| `configuration` | JSONB | Analysis configuration / parameters |
| `summary` | JSONB | High-level run summary (event counts, anomaly counts, etc.) |

---

### `audit_logs`

An append-only audit trail of all significant operations.

This table should be treated as immutable: records should only ever be inserted, never updated or deleted.

| Column | Type | Description |
|---|---|---|
| `audit_id` | UUID (PK) | Unique audit record identifier |
| `timestamp` | TIMESTAMPTZ | Time of the operation |
| `actor_user_id` | UUID (FK → users) | Investigator who performed the action (nullable for system actions) |
| `action` | TEXT | Operation type: `evidence_ingested`, `case_created`, `analysis_started`, `integrity_check_passed`, `integrity_check_failed`, etc. |
| `entity_type` | TEXT | Type of object acted on: `evidence`, `case`, `analysis_run` |
| `entity_id` | UUID | ID of the object acted on |
| `metadata` | JSONB | Additional context (hashes, parameters, results) |

---

## Entity Relationship Diagram

```
users ──────────────────────────────────────────────────┐
  │                                                      │
  │ created_by                                           │ audit
  ▼                                                      ▼
cases ─────────────┬──────────────────────────── audit_logs
  │                │
  │                │
  ▼                ▼
evidence        events ──────────────── anomalies
  │                │
  │                │
  └───── FK ───────┘
                   │
                   ▼
               entities
                   │
                   │
               relationships
```

---

## Storage Separation

```
PostgreSQL                           Local / Object Storage
─────────────────────────────────    ──────────────────────────────
evidence.file_hash  ←──────────────→  SHA-256 of /evidence-store/...
evidence.file_path  ←──────────────→  Actual file location
```

The `file_hash` in PostgreSQL is the integrity anchor. If the file is re-hashed and the value differs, an integrity alert should be raised.

---

*Database models (SQLAlchemy) and migrations (Alembic) will be implemented in the `backend/app/models/` directory.*

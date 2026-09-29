# API Contract — Sentinel

> **Status**: Planned API. No endpoints are implemented beyond `/` and `/health`.

---

## Overview

The Sentinel backend exposes a REST API built with FastAPI. All endpoints return JSON. All timestamps are ISO 8601 UTC strings.

The API is consumed exclusively by the Sentinel frontend. There is no public API contract intended for third-party consumption at this stage.

---

## Base URL

```
http://localhost:8000
```

(Configurable via `BACKEND_HOST` and `BACKEND_PORT` environment variables.)

---

## Currently Implemented

### `GET /`

Health check — returns a basic service identifier.

**Response**
```json
{
  "service": "Sentinel API",
  "status": "running",
  "version": "0.1.0"
}
```

---

### `GET /health`

Detailed health probe — used by Docker Compose and monitoring.

**Response**
```json
{
  "status": "healthy",
  "database": "not_configured",
  "storage": "not_configured"
}
```

---

## Planned Endpoints

The following endpoints are **planned** and not yet implemented.

---

## Cases

### `POST /cases`

Create a new investigation case.

**Request body**
```json
{
  "title": "Case Q1-2026",
  "description": "Suspected data exfiltration — Q1 incident"
}
```

**Response** `201 Created`
```json
{
  "case_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "title": "Case Q1-2026",
  "description": "Suspected data exfiltration — Q1 incident",
  "status": "open",
  "created_at": "2026-01-15T10:00:00Z"
}
```

---

### `GET /cases`

List all investigation cases.

**Query parameters**

| Parameter | Type | Description |
|---|---|---|
| `status` | string | Filter by status (`open`, `closed`, etc.) |
| `page` | int | Page number (default: 1) |
| `page_size` | int | Results per page (default: 20) |

**Response** `200 OK`
```json
{
  "cases": [ /* array of case objects */ ],
  "total": 12,
  "page": 1,
  "page_size": 20
}
```

---

### `GET /cases/{case_id}`

Get a specific case.

**Response** `200 OK`
```json
{
  "case_id": "...",
  "title": "...",
  "status": "open",
  "evidence_count": 5,
  "event_count": 1847,
  "anomaly_count": 12,
  "created_at": "...",
  "updated_at": "..."
}
```

---

## Evidence

### `POST /evidence`

Upload an evidence file and register it against a case.

This endpoint will:
1. Accept a multipart file upload.
2. Compute the SHA-256 hash of the file.
3. Store the file in the local evidence store.
4. Record the evidence metadata and hash in PostgreSQL.
5. Create an audit record.
6. Return the evidence record.

**Request** — `multipart/form-data`

| Field | Type | Description |
|---|---|---|
| `case_id` | string (UUID) | Target case |
| `source_type` | string | Evidence type: `endpoint_log`, `cctv_video`, etc. |
| `file` | binary | The evidence file |
| `metadata` | JSON string | Optional additional metadata |

**Response** `201 Created`
```json
{
  "evidence_id": "...",
  "case_id": "...",
  "file_name": "auth-log-2026-01-15.csv",
  "file_hash": "sha256:abc123...",
  "file_size_bytes": 248012,
  "source_type": "auth_log",
  "processing_status": "pending",
  "ingested_at": "2026-01-15T10:05:00Z"
}
```

---

### `GET /evidence/{evidence_id}`

Get metadata for a specific evidence record.

**Response** `200 OK` — evidence object as above.

---

### `GET /evidence/{evidence_id}/verify`

Re-hash the evidence file and verify integrity against the stored hash.

**Response** `200 OK`
```json
{
  "evidence_id": "...",
  "stored_hash": "sha256:abc123...",
  "computed_hash": "sha256:abc123...",
  "integrity": "verified",
  "checked_at": "2026-01-15T12:00:00Z"
}
```

If hashes differ:
```json
{
  "integrity": "failed",
  "message": "File hash does not match stored value. Evidence may have been modified."
}
```

---

## Analysis

### `POST /analysis/start`

Start an AI analysis job for a case.

**Request body**
```json
{
  "case_id": "...",
  "evidence_ids": ["...", "..."],
  "configuration": {}
}
```

**Response** `202 Accepted`
```json
{
  "analysis_run_id": "...",
  "case_id": "...",
  "status": "queued",
  "started_at": "2026-01-15T10:10:00Z"
}
```

---

### `GET /analysis/{analysis_run_id}`

Get the status and summary of an analysis run.

**Response** `200 OK`
```json
{
  "analysis_run_id": "...",
  "case_id": "...",
  "status": "completed",
  "started_at": "...",
  "completed_at": "...",
  "summary": {
    "events_extracted": 1847,
    "anomalies_detected": 12,
    "entities_resolved": 34
  }
}
```

---

## Timeline

### `GET /timeline/{case_id}`

Get the unified event timeline for a case.

**Query parameters**

| Parameter | Type | Description |
|---|---|---|
| `from` | ISO 8601 string | Filter events after this time |
| `to` | ISO 8601 string | Filter events before this time |
| `actor_id` | string | Filter by actor |
| `source_type` | string | Filter by source modality |
| `page` | int | Page number |
| `page_size` | int | Results per page |

**Response** `200 OK`
```json
{
  "case_id": "...",
  "events": [
    {
      "event_id": "EVT-1024",
      "timestamp_start": "2026-01-15T10:20:00Z",
      "actor_id": "EMP-104",
      "action": "file_access",
      "source_type": "endpoint_log",
      "confidence": 0.94
    }
  ],
  "total": 1847
}
```

---

## Evidence Graph

### `GET /graph/{case_id}`

Get the entity relationship graph for a case.

**Response** `200 OK`
```json
{
  "case_id": "...",
  "nodes": [
    { "id": "EMP-104", "type": "person", "label": "Employee 104" },
    { "id": "FILE-883", "type": "file", "label": "Q4-projections.xlsx" }
  ],
  "edges": [
    {
      "source": "EMP-104",
      "target": "FILE-883",
      "relationship": "accessed",
      "event_count": 7,
      "confidence": 0.94
    }
  ]
}
```

---

## Anomalies

### `GET /anomalies/{case_id}`

List all anomalies detected for a case.

**Query parameters**

| Parameter | Type | Description |
|---|---|---|
| `severity` | string | Filter by `low`, `medium`, `high` |
| `anomaly_type` | string | Filter by anomaly category |
| `page` | int | Page number |
| `page_size` | int | Results per page |

**Response** `200 OK`
```json
{
  "case_id": "...",
  "anomalies": [
    {
      "anomaly_id": "...",
      "anomaly_type": "temporal",
      "description": "File access activity observed outside normal working hours.",
      "severity": "high",
      "confidence": 0.87,
      "supporting_event_count": 14
    }
  ],
  "total": 12
}
```

---

### `GET /anomalies/{anomaly_id}/detail`

Get full detail for a single anomaly, including all supporting and contradicting events.

**Response** `200 OK`
```json
{
  "anomaly_id": "...",
  "description": "...",
  "severity": "high",
  "confidence": 0.87,
  "supporting_events": [ /* event objects */ ],
  "contradicting_events": [ /* event objects */ ],
  "analysis_run_id": "..."
}
```

---

## Error Responses

All error responses follow this structure:

```json
{
  "error": "not_found",
  "message": "Case with ID '...' does not exist.",
  "detail": null
}
```

| HTTP Status | Meaning |
|---|---|
| `400 Bad Request` | Invalid request body or parameters |
| `404 Not Found` | Requested resource does not exist |
| `409 Conflict` | Resource already exists |
| `422 Unprocessable Entity` | Validation error (FastAPI default) |
| `500 Internal Server Error` | Unexpected server error |

---

*API implementation will begin in `backend/app/api/`. Endpoint implementations should be registered on the FastAPI router in `backend/app/main.py`.*

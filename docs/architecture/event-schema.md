# Canonical Event Schema — Sentinel

> **Status**: Planned schema. Not yet implemented in code.

---

## Purpose

The canonical event schema is the **common language** that unifies all evidence sources within Sentinel.

Every evidence modality — cyber logs, video footage, physical badge events, and documents — produces observations that are heterogeneous in format, timing granularity, and semantics. The canonical event schema normalises all of these into a single structure that the correlation engine, timeline builder, evidence graph, and investigator dashboard can operate on uniformly.

```
Cyber AI      ─┐
Video AI       ├──→  Canonical Events  ──→  Correlation Engine
Document AI    │                            Timeline
Physical Logs ─┘                            Evidence Graph
                                            Investigator Dashboard
```

---

## Example Event

```json
{
  "event_id": "EVT-1024",
  "case_id": "CASE-001",
  "timestamp_start": "2026-01-15T10:20:00Z",
  "timestamp_end": "2026-01-15T10:21:00Z",
  "actor_id": "EMP-104",
  "action": "file_access",
  "object_id": "FILE-883",
  "location_id": "LAB-03",
  "source_type": "endpoint_log",
  "source_id": "LOG-2291",
  "confidence": 0.94,
  "metadata": {}
}
```

---

## Field Definitions

| Field | Type | Required | Description |
|---|---|---|---|
| `event_id` | `string` | ✅ | Unique identifier for this event. Format: `EVT-<number>` or UUID. |
| `case_id` | `string` | ✅ | The investigation case this event belongs to. |
| `timestamp_start` | `string` (ISO 8601) | ✅ | When the event began (UTC). |
| `timestamp_end` | `string` (ISO 8601) | ❌ | When the event ended. Null for instantaneous events. |
| `actor_id` | `string` | ❌ | The entity that performed the action (e.g., employee ID, username, camera zone). Null if unknown. |
| `action` | `string` | ✅ | The type of activity observed (see Action Vocabulary below). |
| `object_id` | `string` | ❌ | The object acted upon (file ID, device ID, door ID, etc.). Null if not applicable. |
| `location_id` | `string` | ❌ | Physical or logical location (room, network segment, server). Null if unknown. |
| `source_type` | `string` | ✅ | The modality/source that produced this event (see Source Types below). |
| `source_id` | `string` | ✅ | The specific evidence record that this event was extracted from (links back to the `evidence` table). |
| `confidence` | `float` | ✅ | Confidence in the event extraction, from 0.0 (low) to 1.0 (high). |
| `metadata` | `object` | ✅ | Modality-specific additional fields (see Metadata Extensions below). |

---

## Action Vocabulary

The `action` field uses a controlled vocabulary. Planned values:

### Cyber / System Actions
| Value | Description |
|---|---|
| `authentication_success` | Successful login |
| `authentication_failure` | Failed login attempt |
| `file_access` | File read/open |
| `file_write` | File write/create/modify |
| `file_delete` | File deletion |
| `file_copy` | File copied (possibly to removable media) |
| `usb_connect` | USB device connected |
| `usb_disconnect` | USB device disconnected |
| `process_exec` | Process execution |
| `network_connection` | Outbound/inbound network connection |
| `dns_query` | DNS query |
| `email_send` | Email sent |
| `email_receive` | Email received |
| `privilege_escalation` | Privilege change event |

### Physical / Badge Actions
| Value | Description |
|---|---|
| `badge_entry` | Badge used to enter a zone |
| `badge_exit` | Badge used to exit a zone |
| `badge_denied` | Badge access denied |
| `tailgating_detected` | Multiple persons detected entering on one badge (future) |

### Video / CCTV Actions
| Value | Description |
|---|---|
| `person_detected` | Person identified in frame |
| `person_movement` | Movement trajectory event |
| `object_removed` | Object removal detected |
| `restricted_zone_entry` | Entry into a restricted area detected |
| `unusual_activity` | General video anomaly |

### Document / Statement Actions
| Value | Description |
|---|---|
| `document_claim` | A factual claim extracted from a document or statement |
| `document_event` | A timestamped event referenced in a document |
| `contradiction_detected` | A contradiction found between document claims and other evidence |

---

## Source Types

| `source_type` value | Description |
|---|---|
| `endpoint_log` | Endpoint/workstation system log |
| `auth_log` | Authentication or directory log (Active Directory, LDAP, etc.) |
| `file_access_log` | File server or DLP log |
| `usb_log` | USB/device event log |
| `network_log` | Network traffic or firewall log |
| `dns_log` | DNS query log |
| `email_log` | Email gateway or mail server log |
| `badge_log` | Physical access / badge reader log |
| `cctv_video` | CCTV or surveillance video footage |
| `pdf_document` | Scanned PDF (incident report, statement, etc.) |
| `text_document` | Plain-text document or statement |

---

## Metadata Extensions

The `metadata` field is a flexible JSON object for modality-specific details.

### Cyber log example
```json
{
  "username": "jdoe",
  "hostname": "WORKSTATION-42",
  "file_path": "/data/finance/Q4-projections.xlsx",
  "bytes_transferred": 14200,
  "process_name": "explorer.exe",
  "ip_address": "10.0.1.88"
}
```

### Video example
```json
{
  "camera_id": "CAM-07",
  "frame_start": 18430,
  "frame_end": 18512,
  "bounding_box": [120, 45, 380, 620],
  "person_count": 1,
  "detection_model": "yolov8-nano"
}
```

### Document extraction example
```json
{
  "document_page": 3,
  "extracted_text": "The employee was observed accessing the server room at 10:20 AM.",
  "entity_type": "event_claim",
  "extractor": "document-ai-v0.1"
}
```

---

## Schema Versioning

The schema should include a version marker in future implementations so that changes can be tracked:

```json
{
  "schema_version": "1.0",
  "event_id": "EVT-1024",
  ...
}
```

---

## Relationship to Other Components

| Component | How it uses this schema |
|---|---|
| **Cyber AI** | Outputs events with `source_type: endpoint_log`, `auth_log`, etc. |
| **Video AI** | Outputs events with `source_type: cctv_video` |
| **Document AI** | Outputs events with `source_type: pdf_document`, `text_document` |
| **Correlation Engine** | Reads all events; resolves actors/objects; links events across sources |
| **Timeline** | Sorts events by `timestamp_start`; displays actor/action/object |
| **Evidence Graph** | Extracts nodes (actors, objects, locations) and edges (actions) |
| **Backend API** | Stores events in PostgreSQL; exposes them via REST |
| **Frontend** | Displays and filters events in the investigator dashboard |

---

## JSON Schema Definition

The formal JSON Schema is located at:

```
data/schemas/event.schema.json
```

---

*This schema is planned and subject to revision as implementation begins.*

# Frontend Integration Guide

This guide is for the team member building the investigator dashboard (`frontend/`).
The backend is ready: every screen below has an endpoint. The machine-readable
contract is in [`openapi.json`](openapi.json), regenerated with `python scripts/export_openapi.py`.
The live Swagger UI is at <http://localhost:8000/docs>.

---

## 1. Running the backend locally

```bash
# from the project root (Windows: .venv\Scripts\activate)
python scripts/demo.py                                     # builds an analysed demo case (~15 s)
uvicorn app.main:app --app-dir backend --reload --port 8000
```

- Base URL: **`http://localhost:8000/api`**. Put it in `frontend/.env` as `VITE_API_BASE_URL=http://localhost:8000/api`.
- CORS allows `http://localhost:5173` and `http://localhost:3000` by default. Change this with `CORS_ORIGINS` in `.env`.
- There is **no authentication** yet (`AUTH_ENABLED=false`, local-first single user).
- All timestamps are ISO 8601 UTC strings. All IDs are strings (case, evidence and run IDs are UUIDs).
- Errors use the FastAPI shape `{"detail": "..."}` (422 validation errors return `detail` as a list).

Generate TypeScript types:

```bash
cd frontend
npx openapi-typescript ../docs/architecture/openapi.json -o src/types/api.d.ts
```

Graph, timeline, anomaly and suspect payloads are typed `object` in OpenAPI because they come from the correlation engine. Section 4 documents their shapes.

---

## 2. Suggested screens and the calls they need

| Screen | Calls |
|---|---|
| **Case list** | `GET /cases?status=&page=&page_size=` · `POST /cases` · `PATCH /cases/{id}` · `DELETE /cases/{id}` |
| **Case overview** | `GET /cases/{id}/summary` (counts, latest run, top suspects, anomalies by severity, evidence by status) |
| **Evidence** | `GET /evidence?case_id=` · `GET /evidence/source-types` (upload form dropdown) · `POST /evidence` (multipart) · `GET /evidence/{id}/verify` · `GET /evidence/{id}/audit` · `GET /evidence/{id}/audit/verify` · `GET /evidence/{id}/file` (download) · `DELETE /evidence/{id}` |
| **Run analysis** | `POST /analysis/start` → poll `GET /analysis/{run_id}` every 1–2 s until `completed`/`failed` · history: `GET /analysis?case_id=` |
| **Timeline** | `GET /timeline/{id}?from=&to=&actor_id=&source=&source_type=&flagged_only=&page=&page_size=` · incident groups: `GET /timeline/{id}/clusters?cross_modal_only=true` |
| **Evidence graph** | `GET /graph/{id}?format=cytoscape` (render directly with Cytoscape.js) |
| **Anomalies / contradictions** | `GET /anomalies/{id}?severity=&type=&entity=` · detail: `GET /anomalies/{id}/{anomaly_id}` (includes the supporting events and evidence IDs) |
| **Suspects / entities** | `GET /cases/{id}/suspects` (ranked; each item has `reasons`, `event_ids`, `evidence_ids`, `anomaly_ids` for drill-down) |
| **Video quick look** | `GET /video/model-info` · `POST /video/analyze-upload` (multipart; does not create evidence) |
| **Status bar** | `GET /health` (no `/api` prefix; `/api/health` also works) |

### Typical flow

1. `POST /cases` with `{"title": "...", "description": "..."}` returns a `CaseResponse`.
2. Call `POST /evidence` (multipart) once per file. Fields:
   - `case_id`
   - `source_type` (one of `GET /evidence/source-types`)
   - `file`
   - optional `metadata`, a JSON string. The analysis uses two keys from it:
     - `recorded_at`: the ISO time of the first video frame, or the document date
     - `location_id`: the camera zone or host location
3. `POST /analysis/start` with `{"case_id": "...", "include_video": true}` returns **202** and a run with `status: "queued"`.
   - It returns **409** if a run is already active for that case (`detail.run_id` holds the active run's ID).
   - Video is CPU-heavy (roughly 7 s of compute per video second on a laptop). Offer an "include video" toggle and show progress.
4. Poll `GET /analysis/{run_id}`. When it reaches `completed`, refresh the summary, timeline, graph, anomalies and suspects.
   - `evidence_results[]` reports, for each file: `processed`, `skipped` (with a message, e.g. PDF not supported) or `error`.
5. Each item's `processing_status` (`pending → processing → processed | skipped | error`) is shown in `GET /evidence?case_id=`.

Before the first analysis, the case-scoped endpoints return empty data with `"analyzed": false` instead of a 404. Use this to show an "Analysis not run yet" empty state.

---

## 3. Domain vocabulary (for labels, colours, filters)

| Field | Values |
|---|---|
| Case `status` | `open`, `investigating`, `closed`, `archived` |
| Event `source` (modality) | `cyber`, `physical`, `video`, `document` |
| Event `source_type` | `endpoint_log`, `badge_log`, `cctv_video`, `text_document`, … (see `/evidence/source-types`) |
| Event `kind` | `cyber_anomaly`, `badge_access`, `badge_denied`, `video_motion_anomaly`, `video_crime`, `document_claim` |
| Event `prediction` | `1` = flagged by a model, `0` = context-only event (e.g. a granted badge swipe) |
| Anomaly `type` | `impossible_travel`, `uncredentialed_presence`, `denied_access_then_activity`, `after_hours_activity` |
| Anomaly `severity` | `low`, `medium`, `high`, `critical` |
| Graph node `type` | `user`, `event`, `location`, `document`, `object`, `evidence`, `anomaly` |
| Graph edge `label` | `GENERATED`, `OCCURRED_AT`, `PRESENT_IN`, `REFERENCES`, `MENTIONS`, `TARGETS`, `EXTRACTED_FROM`, `FLAGS`, `CONTRADICTS` |

**UI wording requirement:** Sentinel output is a set of *investigative leads*, not verdicts. Label scores "risk score" or "lead strength", never "guilty" or "malicious". Show `reasons` and the linked evidence for every suspect.

**Video caveats:**
- If `is_fallback` is `true` on a video result, or `metadata.is_fallback` is `true` on an event, the TimeSformer weights were not loaded and a motion heuristic produced the result. Show a warning badge.
- If `timestamp_is_estimated` is `true`, the video had no `recorded_at`, so its times are not real wall-clock times. Such videos are left out of correlation; the run's `evidence_results[].message` says so. Prompt the investigator for `recorded_at` (and `location_id`) when uploading CCTV.
- While a re-run is in progress, the timeline/graph/anomalies endpoints keep serving the previous run's results. A second `POST /api/analysis/start` for the same case returns 409 with the active `run_id`.
- The 88.68% F1 shown by `/video/model-info` comes from a third-party model card (`metrics_source`). Show it with that caveat.

---

## 4. Response shapes (trimmed real examples from the demo case)

### `GET /cases/{id}/summary`
```json
{
  "case": {"case_id": "f5ed…", "title": "Night Copy — …", "status": "open", "evidence_count": 4,
           "event_count": 146, "anomaly_count": 12, "last_analysis_run_id": "8e33…",
           "last_analysis_status": "completed", "created_at": "…", "updated_at": "…", "metadata": {}},
  "analysis": { "run_id": "8e33…", "status": "completed", "summary": {"…": "…"}, "evidence_results": ["…"] },
  "summary": {"total_events": 146, "skipped_events": 0, "incident_clusters": 35, "cross_modal_clusters": 13,
              "contradictions_detected": 12, "graph_nodes": 195, "graph_edges": 592, "ranked_suspects": 7,
              "top_suspect": "user_007", "sources_represented": ["cyber", "document", "physical", "video"]},
  "top_suspects": [ { "rank": 1, "entity": "user_007", "aggregate_risk_score": 11.27, "event_count": 6,
                      "distinct_sources": 3, "sources": ["cyber", "document", "physical"], "max_score": 0.99,
                      "contradiction_count": 6, "event_ids": ["EVT-CYBER-…"], "evidence_ids": ["…"],
                      "anomaly_ids": ["ANOM-0001"], "reasons": ["6 flagged event(s) across 3 source(s): …",
                      "impossible_travel (high): Entity 'user_007' registered in 'ZONE-OFFICE-3F' …"] } ],
  "anomalies_by_severity": {"high": 2, "critical": 2, "medium": 8},
  "evidence_by_status": {"processed": 4}
}
```

### Timeline event (`GET /timeline/{id}` → `events[]`)
```json
{
  "event_id": "EVT-BADGE-B0200BA9-0004", "case_id": "f5ed…", "timestamp": "2026-01-14T08:14:00+00:00",
  "timestamp_end": null, "source": "physical", "source_type": "badge_log", "source_id": "<evidence_id>",
  "actor_id": "BADGE-007", "canonical_entity": "user_007", "entity_resolution_confidence": 0.85,
  "action": "badge_swipe", "kind": "badge_access", "location_id": "ZONE-LOBBY", "object_id": "DOOR-MAIN",
  "score": 0.1, "confidence": 1.0, "prediction": 0,
  "details": {"…": "modality specific (cyber feature counts, document entities)"},
  "metadata": {"result": "granted"}
}
```
Optional per modality: `document_id` and `text` (documents), `metadata.crime_probability`/`model`/`is_fallback` (video).
The page wrapper is `{case_id, analyzed, events, total, page, page_size, summary, skipped_events}`. `skipped_events` lists inputs that had no usable timestamp. Sentinel never invents timestamps.

### Cluster (`GET /timeline/{id}/clusters`)
```json
{"cluster_id": "INC-CLUSTER-031", "start_time": "…", "end_time": "…", "duration_minutes": 50.0,
 "entities": ["unknown", "user_007"], "known_entities": ["user_007"], "sources": ["cyber", "physical", "video"],
 "is_cross_modal": true, "max_score": 0.99, "event_count": 9, "event_ids": ["…"]}
```

### Anomaly (`GET /anomalies/{id}` → `anomalies[]`; the detail endpoint adds `events` and `evidence_ids`)
```json
{"anomaly_id": "ANOM-0001", "type": "impossible_travel", "severity": "high", "entity": "user_007",
 "description": "Entity 'user_007' registered in 'ZONE-OFFICE-3F' at … and in 'ZONE-DATA-CENTER-B' at … (1.0 mins apart) …",
 "event_ids": ["EVT-CYBER-…", "EVT-BADGE-…"], "time_window_seconds": 60.0}
```

### Graph (`GET /graph/{id}?format=cytoscape`)
```json
{"case_id": "f5ed…", "analyzed": true,
 "elements": {"nodes": [{"data": {"id": "user_007", "label": "user_007", "type": "user", "resolved_id": "user_007"}}],
              "edges": [{"data": {"id": "edge_0", "source": "user_007", "target": "EVT-…", "label": "GENERATED", "weight": 0.99}}]}}
```
`format=standard` returns `{nodes, edges, metrics: {total_nodes, total_edges, node_types, centrality}}`. Use `centrality` to size nodes.
The demo graph has about 200 nodes and 600 edges. Consider filtering out event nodes with `prediction: 0`, or using a cose/fcose layout.

### Analysis run (`GET /analysis/{run_id}`)
```json
{"run_id": "8e33…", "case_id": "f5ed…", "status": "completed", "created_at": "…", "started_at": "…", "finished_at": "…",
 "options": {"include_video": false, "video_max_seconds": 20.0, "window_minutes": 60, "…": "…"},
 "summary": {"total_events": 146, "contradictions_detected": 12, "top_suspect": "user_007", "evidence_processed": 4, "…": "…"},
 "evidence_results": [{"evidence_id": "…", "file_name": "badge.csv", "source_type": "badge_log", "processor": "badge",
                       "status": "processed", "events": 96, "message": null}],
 "error": null}
```

### Evidence audit (`GET /evidence/{id}/audit`)
Records are hash-chained: each `prev_hash` equals the previous record's `record_hash`. `GET /evidence/{id}/audit/verify` returns `{valid, records, broken_at_index, reason}`. Show a "chain of custody verified" badge from it.

---

## 5. Demo evidence files

`python scripts/generate_demo_data.py` writes the scenario to `data/generated/`. Upload these files through the UI to test the full flow:

| File | `source_type` |
|---|---|
| `cyber.csv` | `endpoint_log` |
| `badge.csv` | `badge_log` |
| `video.csv` | `video_features` |
| `documents.jsonl` | `text_document` |
| any short `.mp4` (optional) | `cctv_video`, with metadata `{"recorded_at": "2026-01-16T21:58:00Z", "location_id": "ZONE-RESTRICTED-SERVER-ROOM"}` |

The expected result is in `scenario_ground_truth.json`: top suspect `user_007`, plus impossible-travel, uncredentialed-presence, denied-access-then-activity and after-hours anomalies.

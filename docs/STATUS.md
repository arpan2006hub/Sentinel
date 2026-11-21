# Sentinel — Status & Remaining Work

_Last updated 2026-11-22. The scope is the agreed component set: React investigator dashboard, Video AI (TimeSformer), Cyber AI, Document AI baseline, Cross-Modal Correlation, Case & Evidence API, and end-to-end demo._



- **Setup:**
  - `pip install -r requirements.txt` works on Python 3.11–3.14. The old pins needed a Rust build on 3.14.
  - Paths resolve from the project root, so the API works from any directory.
- **Case & Evidence API:**
  - Upload size limit, `source_type` validation, audited download.
  - Hash-chained audit log with a verification endpoint; audit records survive deletion.
  - Deleting a case removes its files and outputs.
  - `event_count` and `anomaly_count` are populated.
- **Analysis runs:**
  - `POST /api/analysis/start` → poll `GET /api/analysis/{run_id}`.
  - Per-evidence processing status; results scoped to the case; 409 on concurrent runs.
- **Correlation fixes:**
  - Operator-precedence bug fixed.
  - The badge check now compares location.
  - Unparseable timestamps are reported as skipped instead of being replaced with "now".
  - Documents use real timestamps.
  - `events.jsonl` is real JSON Lines.
  - Anomalies have IDs.
  - Suspects come with `reasons`, `evidence_ids` and `anomaly_ids`.
  - New rule: `denied_access_then_activity`.
- **TimeSformer:**
  - Weights (485 MB, SHA-256 `26ef20fc…6826e`, matches Hugging Face) load strictly with `weights_only=True`.
  - CPU inference works through the CLI and the analysis API.
  - Lazy loading.
  - `--start-time` / `recorded_at` alignment.
  - `max_seconds` bound.
  - The fallback is clearly labelled and no longer reports the model's F1.
- **Demo:** `python scripts/demo.py` produces a case whose top suspect `user_007` matches the scenario ground truth. All 4 expected contradiction types are found, and the benign admin is not flagged.
- **Tests and lint:** The suite currently has 53 passing tests in the patch workspace. The developer's Windows environment has verified clean Ruff output after the preceding patches; rerun tests and Ruff after applying each new patch. The OpenAPI schema has been exported.
- **Docker:** the backend image is built and smoke-tested (2026-11-14): CPU-only torch `2.15.0+cpu`, runs as non-root `sentinel`, Docker health check `healthy`, `scripts/demo.py` inside the container gives top suspect `user_007`, and the summary, timeline, anomalies, suspects and graph endpoints all return data. CORS for `localhost:5173` works.
- **Code-review fixes (2026-11-14):**
  - Videos without `recorded_at` are still analysed, but their events are kept out of correlation (the evidence result says why), so no invented timestamps reach the timeline.
  - Video events without a location no longer raise `uncredentialed_presence`.
  - Suspect ranking tolerates non-numeric scores.
  - Re-running analysis keeps the previous results readable until the new run succeeds (staging folder swap); a failed run no longer wipes results.
  - Starting two runs at once is atomic (the second gets 409).
  - Concurrent audit writes can no longer fork the hash chain.
  - Evidence routes (except upload) run in the threadpool, so verifying a large file no longer blocks the API.
- **PDF processing (2026-11-15):**
  - Text-based PDFs are routed through Document AI using pypdf; extracted events retain the PDF source type, page number and extraction method.
  - Scanned pages without embedded text can be rendered with pypdfium2 and OCR'd with Tesseract when the optional OCR dependencies and executable are installed.
  - OCR is bounded by a 100-page-per-file limit, a 20-million-pixel page render cap, a per-page timeout, and the existing 5-million-character extraction cap.
  - OCR provenance (engine, language, DPI and page number) is retained on generated events. OCR can be disabled with `PDF_OCR_ENABLED=false`; mixed PDFs remain processable when OCR is unavailable if embedded-text pages exist.
- **Upload reliability (2026-11-15):**
  - Upload disk I/O, hashing and database registration run in a worker thread; writes are atomic and uploaded files are cleaned up if registration fails.
- **Code-review fixes (2026-11-15):**
  - Audit-chain verification rejects a missing hash once hash chaining has begun, while still permitting a contiguous prefix of pre-migration legacy rows.
  - Case and evidence deletion return HTTP 409 while an analysis run is queued or running. The guard is serialized with analysis-run creation using SQLite `BEGIN IMMEDIATE`.
  - TimeSformer checkpoint loading now refuses unrestricted pickle deserialization if `weights_only=True` fails; an incompatible or unsafe checkpoint falls back to the clearly labelled motion heuristic instead of being unpickled.

## Implemented: frontend

- [x] Investigator dashboard in `frontend/`, including case management, evidence workflows, analysis status, timeline, anomalies, evidence graph and ranked entity leads.
- [ ] `frontend/Dockerfile`, then enable the `frontend` compose profile. Local frontend development is supported with Vite.

## Remaining: heavy jobs to delegate (not run on the CPU-only dev laptop)

| # | Job | Why it's heavy | How |
|---|---|---|---|
| 1 | ~~Build and smoke-test the backend Docker image~~ **Done 2026-11-14** | — | Rebuild after code changes: `docker compose --profile app build backend`. Still untested in the container: TimeSformer weights download + real video inference. |
| 2 | **Retrain the CERT r4.2 Random Forest** | ~32 M raw rows; long CPU run, large disk | `preprocess_cert.py` → `label_cert.py` → `train_supervised.py`. **Pick the threshold on a separate validation period**: the 0.80 in `CYBER_MODEL_REPORT.md` was chosen on the test set. Save `{"model", "features", "threshold"}` and point `CYBER_MODEL_PATH` at it. |
| 3 | **Independently evaluate TimeSformer on the UCF-Crime test split** | ~290 test videos × 7 s CPU per video second ⇒ GPU strongly recommended | Run `detect_crime.py` per test video and compute F1/AUC at video level. Replace the third-party 88.68% claim with the measured number. |
| 4 | **Long-video demo runs** | Real CCTV clips > 30 s take minutes on CPU | Use a GPU machine, or keep `VIDEO_MAX_SECONDS` small for live demos |
| 5 | (Optional) UCF-Crime motion baseline | Decodes ~1,900 videos | `extract_ucf_features.py` → `train_ucf.py` |

## Remaining: engineering (not blocking the lab demo)

- [ ] Authentication / roles (`AUTH_ENABLED`), and an investigator identity in the audit `actor` (currently `investigator`/`analysis`).
- [ ] PostgreSQL + Alembic migrations (ADR-003), and Redis/Celery workers so analysis runs survive restarts and leave the API process.
- [x] Text extraction for text-based `pdf_document` evidence using pypdf, with per-page provenance on generated events.
- [x] Optional OCR for scanned/image-only PDF pages using pypdfium2 + Tesseract. Install `requirements-ocr.txt` and the Tesseract executable separately; no executable or language model is downloaded automatically.
- [x] `impossible_travel` no longer infers distance from zone labels: it requires a source-provided minimum transit duration for the immediately previous location. The synthetic scenario includes an explicit 8-minute route-map value for its planted transition.
- [x] Canonical events are validated against `data/schemas/event.schema.json` before correlation; invalid and duplicate event IDs are excluded with auditable validation errors.
- [ ] Attribute CCTV events to people (re-identification or badge proximity). Video events are `actor_id: unknown` today.
- [x] Upload reliability: async evidence upload runs disk I/O and hashing in a thread pool, writes atomically, sanitizes filenames, enforces size limits, and cleans up if registration fails.
- [ ] CI workflow (`.github/workflows/` is empty).
- [ ] Original-report items now out of scope: LANL, Enron, embeddings/RAG/LLM summaries, phishing-screenshot CV. Revisit after the demo if needed.

## Honest caveats for the evaluation

- The Cyber, Document and video-feature models in the demo are trained and scored on **synthetic** data. Their metrics prove the plumbing, not detection quality. The real-data result is the CERT report.
- The Document AI predictions in `artifacts/documents` are in-sample.
- The TimeSformer metrics come from a third-party model card. Present them as "reported by the model author".

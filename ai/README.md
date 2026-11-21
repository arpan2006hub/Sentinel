# AI / ML — Sentinel

The `ai/` package contains the implemented processing and correlation layer used by the FastAPI backend.

## Processing

`ai/processing/` routes evidence to a modality processor:

| Source | Implementation |
|---|---|
| Cyber CSV/log data | Isolation Forest anomaly scoring, with a saved-model bundle or synthetic-model fallback |
| Badge CSV | Granted/denied access events and location facts |
| Video feature CSV | Isolation Forest video-motion anomaly scoring |
| CCTV MP4 | TimeSformer crime detection or a clearly labelled motion fallback |
| Text and JSONL | Entity, timestamp and zone extraction with a TF-IDF/logistic-regression baseline or keyword heuristic |
| PDF | Text extraction with pypdf; optional Tesseract OCR through pypdfium2 |

All processors emit canonical runtime events defined by `data/schemas/event.schema.json`. Invalid events and duplicate event IDs are reported and excluded before correlation.

## Cyber AI

`ai/cyber/` contains:

- CERT preprocessing and feature normalisation
- Synthetic label generation
- Isolation Forest training
- Supervised Random Forest training and model bundles

The live demo uses the lightweight Isolation Forest path or a configured saved model. Retraining the CERT r4.2 Random Forest is a heavy offline job; see `CYBER_MODEL_REPORT.md` and `docs/STATUS.md`.

## Video AI

`ai/video/` contains TimeSformer inference, a motion-feature baseline, UCF-Crime training utilities and the standalone CLI.

- Default model: `Nikeytas/timesformer-best-crime-detector`
- CPU inference is supported and lazy-loaded
- `--start-time` / `recorded_at` aligns analysis with other evidence
- `--max-seconds` and `VIDEO_MAX_SECONDS` bound processing
- Missing weights or unsafe/incompatible checkpoints produce a labelled fallback rather than silent success
- The 88.68% F1 value is a third-party model-card claim, not an independent Sentinel evaluation

See `ai/video/README.md` for CLI usage.

## Document AI

`ai/documents/train.py` trains or rebuilds the document baseline. Text extraction supports `.txt`, `.json`, `.jsonl`, text PDFs and optional OCR for scanned PDF pages.

OCR requires `requirements-ocr.txt` and an external Tesseract executable. It is disabled or skipped without a usable runtime.

## Correlation

`ai/correlation/` contains the implemented cross-modal pipeline:

- entity resolution
- timestamped timeline construction
- temporal clustering
- evidence graph construction
- contradiction detection
- explainable entity/lead ranking

The correlator currently implements impossible-travel, uncredentialed-presence, denied-access-then-activity and after-hours contradiction rules.

The backend runs one in-process analysis task per case and writes case-scoped JSON/JSONL results under `artifacts/cases/<case_id>/correlation/`. Redis/Celery workers and a distributed queue are not used in the current build.

## Integration

Analysis is orchestrated by `backend/app/services/analysis_service.py`. The backend routes uploaded evidence through `ai/processing/router.py`, validates processor output and then invokes `ai/correlation/correlator.py`.

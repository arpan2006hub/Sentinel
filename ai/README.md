# AI / ML — Sentinel

> **Status**: Foundation only. No AI models are implemented yet.

---

## Planned Architecture

The AI layer is organised into four modality-specific pipelines and a cross-modal correlation layer. All pipelines output **canonical events** (see `docs/architecture/event-schema.md`) that feed the correlation engine.

```
Cyber AI      ──┐
Video AI       ├──→  Canonical Events  ──→  Correlation Engine
Document AI    │                            Entity Resolution
Physical AI   ─┘                            Timeline Construction
                                           Evidence Graph
```

---

## Cyber AI

**Directory**: `ai/cyber/`

### Responsibilities

- Log preprocessing and normalisation
- Feature extraction from authentication, file-access, USB, network, DNS, HTTP, process logs
- Anomaly detection on behavioural sequences
- User/entity behavioural baselines
- Output: canonical events with `source_type` in `endpoint_log`, `auth_log`, `file_access_log`, `usb_log`, `network_log`, `dns_log`, `email_log`

### Planned Modules

| Subdirectory | Purpose |
|---|---|
| `preprocessing/` | Parse raw logs (CSV, JSON, EVTX, Sysmon); normalise timestamps; map fields |
| `features/` | Extract behavioural features: session patterns, access frequencies, command sequences |
| `models/` | Train and serve anomaly detection models (isolation forests, LSTM autoencoders, transformers) |
| `inference/` | Batch and streaming inference pipelines; event emission |

---

## Video AI

**Directory**: `ai/video/`

### Responsibilities

- Frame extraction and preprocessing
- Person/vehicle/object detection (YOLO-based)
- Activity recognition and temporal event extraction
- Anomaly detection in video streams (unusual movement, restricted zone entry)
- Output: canonical events with `source_type: cctv_video`

### Planned Modules

| Subdirectory | Purpose |
|---|---|
| `preprocessing/` | Video decoding, frame sampling, resolution normalisation |
| `detection/` | Object/person detection, tracking, bounding-box extraction |
| `anomaly/` | Temporal anomaly detection on detection outputs; event emission |

---

## Document AI

**Directory**: `ai/documents/`

### Responsibilities

- OCR for scanned PDFs and images
- Entity extraction (names, dates, locations, IDs)
- Event/timeline extraction from narrative text
- Contradiction detection between document claims and other evidence
- Output: canonical events with `source_type` in `pdf_document`, `text_document`

### Planned Modules

| Subdirectory | Purpose |
|---|---|
| `ocr/` | Text extraction from PDFs and images (Tesseract, PaddleOCR, etc.) |
| `extraction/` | NER, relation extraction, date/time/location parsing, event claim extraction |
| `contradiction/` | Cross-reference document claims against canonical events; surface inconsistencies |

---

## Correlation

**Directory**: `ai/correlation/`

### Responsibilities

- **Entity resolution**: Map ambiguous actor references (usernames, badge IDs, face clusters, names in documents) to canonical entities
- **Temporal correlation**: Align events across modalities by time
- **Cross-source matching**: Link related events from different sources (e.g., badge entry + video detection + logon)
- **Evidence graph generation**: Build entity-relationship graph from correlated events
- **Incident reconstruction**: Synthesise a coherent narrative from multimodal evidence

### Planned Modules

| Subdirectory | Purpose |
|---|---|
| `entity_resolution/` | Blocking, matching, and clustering for entity deduplication |
| `timeline/` | Global timeline construction; gap analysis; event ordering |
| `evidence_graph/` | Graph construction; edge inference; graph algorithms for investigation |

---

## Evaluation

**Directory**: `ai/evaluation/`

### Responsibilities

- Metrics computation for anomaly detection (precision, recall, F1, PR-AUC)
- Ablation study orchestration
- False-positive analysis
- Error analysis tooling
- Reproducible experiment scripts

---

## Integration with Backend

The AI pipelines are invoked by the backend as **background jobs** (Celery workers):

1. Backend receives analysis request via `POST /analysis/start`
2. Backend creates an `analysis_runs` record and queues a Celery task
3. Worker loads the relevant evidence files from the evidence store
4. Worker executes the appropriate AI pipeline(s)
5. Worker writes canonical events to PostgreSQL
6. Worker updates `analysis_runs` with summary and status

AI code should be **importable as modules** from the worker. The backend does not embed AI logic directly.

---

## MLOps

Experiment tracking uses **MLflow** (see `mlops/`):

- Each training run logs parameters, metrics, and model artefacts
- Model registry tracks versions for deployment to workers
- Ablation studies are organised as MLflow experiments

---

## Development Notes

- AI code runs in the same Python environment as the backend (or a compatible one)
- GPU access is optional for development; CPU inference should work for testing
- Models should be serialisable (ONNX, TorchScript, or pickled) for deployment
- All AI outputs must conform to the canonical event schema
- Confidence scores must be calibrated where possible

---

*Implementation begins with the cyber log preprocessing pipeline and canonical event emission.*
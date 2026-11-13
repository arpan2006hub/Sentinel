# Sentinel

> A local-first multimodal AI system for insider-threat investigation assistance: evidence integrity, per-modality anomaly detection, cross-modal correlation and incident reconstruction.

Sentinel takes in heterogeneous evidence: endpoint/cyber activity, physical badge logs, CCTV video and its motion features, and written statements/reports. It turns every item into **canonical events**, then correlates them across modalities into one timeline, a set of contradictions (impossible travel, presence without a badge, denied badge followed by activity, after-hours activity), an evidence graph, and a ranked list of entities. Every ranked entity comes with its reasons and links back to the source evidence.

> **Investigative signals, not automated verdicts.** All outputs are prioritised leads for human analysts. Human investigators remain responsible for every conclusion.

---

## Implementation status (verified 2026-11-14)

| Component | Status | Notes |
|---|---|---|
| **Case & Evidence API** | 🟢 Ready | Case CRUD, multipart upload with size limit, SHA-256 fingerprint, tamper detection, **hash-chained audit log** (with chain verification), audited download. SQLite store. |
| **Analysis orchestration** | 🟢 Ready | `POST /api/analysis/start` processes every evidence item of a case in the background and correlates it. Results are stored **per case**. |
| **Cross-modal correlation engine** | 🟢 Ready | Entity resolution, temporal clustering, 4 contradiction rules, Cytoscape graph, explainable suspect ranking (`reasons`, `evidence_ids`). |
| **Video AI (TimeSformer)** | 🟢 Ready (inference only) | Pretrained `Nikeytas/timesformer-best-crime-detector` (no training). Weights load strictly; CPU inference verified. Supports a start time for aligning with other evidence, a bounded `max_seconds`, and a clearly-labelled fallback. The 88.68% F1 is a **third-party, unverified** claim. |
| **Cyber AI** | 🟢 Demo / 🟡 CERT | Isolation Forest scorer used live (saved model or fitted on the evidence file). CERT r4.2 Random Forest pipeline exists (`CYBER_MODEL_REPORT.md`), but its model file must be retrained offline (see *Remaining work*). |
| **Document AI baseline** | 🟢 Demo | TF-IDF + logistic regression (trained on the synthetic corpus in seconds) or a transparent keyword heuristic. Entity, time and zone extraction. Supports `.txt/.json/.jsonl`. PDF/OCR not implemented. |
| **Synthetic demo scenario** | 🟢 Ready | Deterministic "Night Copy" insider scenario across all 4 modalities, with ground truth and benign hard negatives. |
| **One-command demo** | 🟢 Ready | `python scripts/demo.py` builds an analysed demo case in about 15 s on a laptop CPU. |
| **Tests / lint** | 🟢 42 tests pass, ruff clean | No test loads the 485 MB video model. |
| **Docker (backend)** | 🟢 Built and smoke-tested | `backend/Dockerfile` (CPU torch, non-root, ~3 GB) plus a compose `app` profile. Verified 2026-11-14: `/health` healthy, `scripts/demo.py` runs inside the container, all case endpoints return data. Video weights are not baked in (download into the `/data` volume). |
| **Investigator dashboard (frontend)** | 🔴 Not started | Backend contract ready: [`docs/architecture/frontend-integration.md`](docs/architecture/frontend-integration.md), [`openapi.json`](docs/architecture/openapi.json). |
| PostgreSQL / Redis / Celery / auth | 📋 Planned | SQLite + in-process background tasks are used for the local-first build. |

Open tasks and the jobs to delegate are listed in [`docs/STATUS.md`](docs/STATUS.md).

---

## Quickstart (Windows / macOS / Linux, CPU only)

**Prerequisites:** Python **3.11–3.14**. Docker and Node.js 18+ are optional (Docker for the container, Node for frontend work).

```bash
python -m venv .venv
.venv\Scripts\activate                 # macOS/Linux: source .venv/bin/activate
# Linux only (avoids the 2 GB CUDA wheel):
#   pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt        # backend + ML + dev tools
```

### 1. Build the demo case (≈15 s, no model training needed)

```bash
python scripts/demo.py
```

This does four things:
1. Generates the synthetic scenario in `data/generated/`.
2. Fits the three lightweight baselines in seconds.
3. Creates a case, ingests the four evidence files (hashing + audit) and runs the full analysis.
4. Prints the case ID and the API URLs to open.

Expected result: top suspect `user_007`, with 4 contradiction types detected.

### 2. Start the API (always from the project root)

```bash
uvicorn app.main:app --app-dir backend --reload --port 8000
```

- Swagger UI: <http://localhost:8000/docs>
- Health: <http://localhost:8000/health>
- All routes are under **`/api`**. For example: `/api/cases`, `/api/analysis/start`, `/api/timeline/{case_id}`.

### 3. (Optional) Add CCTV video with TimeSformer

1. Download the pretrained weights once (~485 MB, network only):
   ```bash
   make weights
   # or: python ai/video/detect_crime.py --video <clip> --auto-download
   ```
2. Analyse a short clip, aligned to the scenario time (CPU: about 7 s of compute per second of video, so keep clips short):
   ```bash
   python scripts/demo.py --video path/to/clip.mp4 --video-max-seconds 20
   ```
3. Or run the CLI on its own:
   ```bash
   python ai/video/detect_crime.py --video clip.mp4 --start-time 2026-01-16T21:58:00Z \
       --location-id ZONE-RESTRICTED-SERVER-ROOM --max-seconds 20 --require-model
   ```

### 4. Tests and lint

```bash
python -m pytest tests -q      # 42 tests, ~20–45 s, never loads the video model
python -m ruff check ai backend scripts tests
```

`make <target>` wraps all of these (`make help`; needs GNU make / Git Bash on Windows).

---

## Architecture

```
React dashboard (frontend/, not started)  ──REST /api──►  FastAPI (backend/app)
                                                            │
     cases / evidence (SHA-256, hash-chained audit) ◄──── SQLite + local evidence store
                                                            │  POST /api/analysis/start
                                                            ▼
                         ai/processing  (per-evidence processors → canonical events)
                           ├─ cyber CSV      → Isolation Forest / saved model (CERT RF bundle supported)
                           ├─ badge CSV      → access facts (granted / denied)
                           ├─ video features → Isolation Forest
                           ├─ CCTV video     → TimeSformer (pretrained, CPU/GPU)
                           └─ documents      → TF-IDF classifier / keyword heuristic + entity extraction
                                                            ▼
                         ai/correlation  (entity resolution → timeline + clusters → contradictions
                                          → evidence graph → explainable suspect ranking)
                                                            ▼
                         artifacts/cases/<case_id>/correlation/*.json  → timeline / graph / anomalies APIs
```

## Configuration (`.env`, see `.env.example`)

| Variable | Default | Purpose |
|---|---|---|
| `STORAGE_PATH` | `./local-evidence-store` | Evidence files and `sentinel.db` (paths are resolved from the project root) |
| `ARTIFACTS_DIR` | `./artifacts` | Baseline models, per-case outputs, TimeSformer weights |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Frontend origins |
| `MAX_UPLOAD_SIZE_MB` | `500` | Upload limit (HTTP 413 above it) |
| `TIMESFORMER_MODEL_PATH` | `$ARTIFACTS_DIR/models/timesformer/model.pth` | Video weights |
| `VIDEO_AUTO_DOWNLOAD` | `false` | Download the weights on first use |
| `VIDEO_MAX_SECONDS` | `120` | CPU bound per video during analysis |
| `CYBER_MODEL_PATH` | `$ARTIFACTS_DIR/cyber/model.joblib` | Set to the CERT RF bundle to score CERT features |

## Docker (backend)

```bash
docker compose --profile app up --build backend     # http://localhost:8000
```

The image uses CPU-only torch and stores everything in the `sentinel-data` volume. Fetch the video weights inside the container with `POST /api/video/download-weights`. Build the demo case inside it with `docker compose exec backend python scripts/demo.py` (run it without `--skip-train` the first time, since a fresh volume has no generated data). Rebuild the image after code changes: `docker compose --profile app build backend`.

## Repository layout

```
ai/processing/      evidence → canonical events (router + per-modality processors)
ai/correlation/     entity resolution, timeline/contradictions, evidence graph, orchestrator
ai/cyber/           CERT r4.2 preprocessing, labelling, Isolation Forest / Random Forest trainers
ai/video/           TimeSformer detector + CLI, motion-feature baselines
ai/documents/       document baseline trainer
backend/app/        FastAPI app: api/ routers, services/, schemas/, config.py, db.py; Dockerfile
scripts/            demo.py, run_all.py, generate_demo_data.py, export_openapi.py, seed_database.py
tests/              pytest suite (isolated temp storage)
docs/               architecture (incl. frontend-integration.md, openapi.json), research, ADRs, STATUS.md
```

## Documentation

- [`docs/STATUS.md`](docs/STATUS.md): what's done, what's remaining, which jobs to delegate
- [`docs/architecture/frontend-integration.md`](docs/architecture/frontend-integration.md): API guide for the dashboard
- [`CYBER_MODEL_REPORT.md`](CYBER_MODEL_REPORT.md): CERT r4.2 results and methodology
- [`TRAINING.md`](TRAINING.md): baselines and synthetic data
- [`ai/video/README.md`](ai/video/README.md): TimeSformer usage
- [`docs/architecture/`](docs/architecture/), [`docs/research/`](docs/research/), [`docs/decisions/`](docs/decisions/)

## Privacy and data handling

- Everything runs locally. There is no telemetry, and evidence never leaves the machine. The only outbound call is the optional one-off Hugging Face weight download.
- Evidence is hashed with SHA-256 at ingestion. The audit log is append-only and hash-chained.
- Never commit real evidence. `local-evidence-store/`, `artifacts/` and `data/generated/` are git-ignored.

## License

MIT — see [`LICENSE`](LICENSE).

# Sentinel starter training guide

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-ml.txt
```

## Run a complete local test

```bash
python scripts/run_all.py
```

This generates synthetic cyber, video-feature, document, and physical data,
trains the three starter models, and writes outputs under `artifacts/`.

## Run each stage separately

```bash
python scripts/generate_demo_data.py --output data/generated
python ai/cyber/train.py --data data/generated/cyber.csv
python ai/video/train.py --data data/generated/video.csv
python ai/documents/train.py --data data/generated/documents.jsonl
python ai/correlation/run.py --data-dir data/generated
```

## Replace synthetic data

Keep the same input columns and pass your own files:

- Cyber CSV: `timestamp,user_id,login_count,file_reads,usb_events,bytes_out,label`
- Video-feature CSV: `timestamp,camera_id,motion_score,person_count,restricted_zone,label`
- Documents JSONL: `document_id,text,label`

`label` is optional for inference, but required for meaningful supervised
evaluation. Public datasets must be downloaded separately and must not be
committed to this repository.

## Important interpretation

These are CPU-friendly baselines for validating the architecture. They are not
production-ready insider-threat models. Before claiming research results, use
proper train/validation/test splits, tune thresholds only on validation data,
and evaluate on held-out real data.


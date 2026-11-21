# Sentinel: baselines, synthetic data and (re)training

**No training is needed to run the demo.** The lightweight baselines below are fitted in seconds as part of `scripts/run_all.py` / `scripts/demo.py`. TimeSformer is used pretrained.

## Install

```bash
python -m venv .venv && .venv\Scripts\activate      # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## Synthetic scenario + baselines (≈15 s on a laptop CPU)

```bash
python scripts/run_all.py --regenerate
```

1. `scripts/generate_demo_data.py --seed 42` writes the deterministic **"Night Copy"** scenario to `data/generated/`:

   | File | Contents |
   |---|---|
   | `cyber.csv` | 302 rows of user-hour endpoint features |
   | `badge.csv` | 96 physical access swipes |
   | `video.csv` | 614 CCTV motion-feature rows for 3 cameras |
   | `documents.jsonl` | 19 documents |
   | `scenario_ground_truth.json` | Ground truth |

   One insider (`user_007`) appears across all four modalities. There are benign hard negatives: an admin with valid daily server-room visits, and a busy engineer with an approved USB exception.
2. It then fits three models:
   - `ai/cyber/train.py`: Isolation Forest (chronological 80/20 split)
   - `ai/video/train.py`: Isolation Forest on the motion features
   - `ai/documents/train.py`: TF-IDF + logistic regression. Its predictions are **in-sample**, so this is a demo baseline only.
3. Finally `ai/correlation/run.py` correlates everything into `artifacts/correlation/`.

The backend scorers reuse `artifacts/{cyber,documents,video}/model.joblib` when present. Otherwise:
- cyber and video features use an Isolation Forest fitted on the uploaded evidence file (unsupervised);
- documents use a transparent keyword heuristic.

## Input formats (for your own evidence)

| `source_type` | Format |
|---|---|
| `endpoint_log` (and other `*_log` cyber types) | CSV: `timestamp,user_id[,host,location_id],login_count,file_reads,usb_events,bytes_out[,http_events,email_events,after_hours_events]` |
| `badge_log` | CSV: `timestamp,badge_id\|user_id,location_id\|door_id[,door_id,result]` (`result`: granted/denied) |
| `video_features` | CSV: `timestamp,camera_id,location_id,motion_score,person_count,restricted_zone` (per-frame motion: `ai/video/extract_features.py`) |
| `text_document` | `.jsonl/.json` rows `{document_id, text, timestamp?}`, or a `.txt` file. Set evidence metadata `recorded_at` if the text has no date. |
| `cctv_video` | `.mp4/.avi/...` plus evidence metadata `recorded_at` (time of frame 0) and `location_id` |

`label` columns are optional and used only for evaluation.

## Heavier jobs (run on a capable machine, not required for the demo)

| Job | Command | Cost |
|---|---|---|
| CERT r4.2 features + labels | `ai/cyber/preprocess_cert.py` → `ai/cyber/label_cert.py` | ~32 M rows; long CPU run + large disk |
| CERT Random Forest | `ai/cyber/train_supervised.py --threshold 0.8` | Minutes of CPU; pick the threshold on a separate validation period |
| UCF-Crime motion baseline | `ai/video/extract_ucf_features.py` → `ai/video/train_ucf.py` | Decodes ~1,900 videos; hours of CPU |
| TimeSformer evaluation on UCF-Crime | `ai/video/detect_crime.py` per test video | GPU strongly recommended |

To use the CERT model in the API, set `CYBER_MODEL_PATH` to its `model.joblib`. The scorer recognises supervised bundles (`predict_proba`) and an optional `threshold` key.

## Interpretation

These are CPU-friendly baselines that validate the architecture. They are not production insider-threat models. Before claiming research results:
- use proper train/validation/test splits;
- tune thresholds on validation data only;
- evaluate on held-out real data.

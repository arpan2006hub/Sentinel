# Video AI — Sentinel

The Video AI module handles surveillance and CCTV video evidence analysis, anomaly detection, and crime event extraction for Sentinel's multimodal investigation platform.

---

## Integrated Models

### TimeSformer Crime Detector (`Nikeytas/timesformer-best-crime-detector`)

- **Hugging Face Model**: [`Nikeytas/timesformer-best-crime-detector`](https://huggingface.co/Nikeytas/timesformer-best-crime-detector)
- **Architecture**: Space-Time Transformer (TimeSformer) with divided space-time self-attention
- **Training Benchmark**: Fine-tuned on the **UCF-Crime dataset** (~1,900+ surveillance videos)
- **Reported Performance**:
  - **F1 Score**: `0.8868` (World-record tier for UCF-Crime video classification)
  - **Accuracy**: `0.8425`
  - **Precision**: `0.8691` (estimated)
  - **Recall**: `0.8513` (estimated)
- **Target Event Categories**:
  - Arson, Assault, Burglary, Explosion, Fighting
  - Road Accidents, Robbery, Shooting, Shoplifting
  - Stealing, Vandalism, and general physical surveillance anomalies
- **Input Specifications**:
  - 16 uniformly sampled frames per temporal window
  - 224×224 resolution per frame
  - ImageNet normalization (`mean=[0.485, 0.456, 0.406]`, `std=[0.229, 0.224, 0.225]`)

---

## Directory Structure

```
ai/video/
├── timesformer_crime_detector.py   # Core TimeSformer detector & preprocessing engine
├── detect_crime.py                 # CLI executable for video evidence scanning
├── extract_ucf_features.py         # Motion feature extraction baseline
├── train_ucf.py                    # Supervised UCF baseline training
├── train.py                        # IsolationForest motion baseline
├── anomaly/                        # Spatial/temporal anomaly helpers
├── detection/                      # Object & entity detection modules
└── preprocessing/                  # Frame decoding & sampling utilities
```

---

## Usage

### 1. Python API

```python
from ai.video.timesformer_crime_detector import TimesformerCrimeDetector

# Initialize (auto-selects CUDA if available, else CPU)
detector = TimesformerCrimeDetector(auto_download=True)

# Analyze a full video with a 2-second sliding window
results = detector.analyze_video(
    video_path="evidence/corridor_cctv.mp4",
    window_seconds=2.0,
    stride_seconds=1.0,
    threshold=0.5,
    case_id="CASE-2026-001",
    location_id="ZONE-HALLWAY-B",
)

print(f"Status: {results['status']}")
print(f"Max crime probability: {results['max_crime_probability']}")
print(f"Canonical events: {len(results['canonical_events'])}")
```

### 2. Command Line Interface (CLI)

```bash
# Run analysis on a video file
python ai/video/detect_crime.py \
    --video evidence/cctv_feed.mp4 \
    --case-id CASE-001 \
    --location-id ZONE-CORRIDOR-01 \
    --threshold 0.5 \
    --output artifacts/video/crime_analysis.json \
    --events-output artifacts/video/crime_events.jsonl
```

### 3. REST API

The Sentinel FastAPI backend exposes endpoints for video AI:

- `GET /api/video/model-info` — Inspect model specifications, device, and status
- `POST /api/video/analyze` — Run analysis on a local video file path
- `POST /api/video/analyze-upload` — Upload and analyze a video file via multipart form
- `POST /api/video/download-weights` — Trigger Hugging Face weights download

---

## Canonical Event Output

Detected crime events are automatically emitted conforming to Sentinel's [Canonical Event Schema](../../docs/architecture/event-schema.md):

```json
{
  "event_id": "EVT-CRIME-7B1A2C3D",
  "case_id": "CASE-2026-001",
  "timestamp_start": "2026-01-15T14:32:10.000000+00:00",
  "timestamp_end": "2026-01-15T14:32:12.000000+00:00",
  "actor_id": "unknown",
  "action": "crime_detected",
  "object_id": "corridor_cctv.mp4",
  "location_id": "ZONE-HALLWAY-B",
  "source_type": "cctv_video",
  "source_id": "EVID-CORRIDOR",
  "confidence": 0.892,
  "metadata": {
    "model": "Nikeytas/timesformer-best-crime-detector",
    "architecture": "TimeSformer",
    "f1_score": 0.8868,
    "crime_probability": 0.892,
    "start_seconds": 10.0,
    "end_seconds": 12.0,
    "video_file": "evidence/corridor_cctv.mp4"
  }
}
```

These canonical events feed directly into the **Correlation Engine** (`ai/correlation/run.py`), which aligns CCTV anomalies with endpoint and document logs in the global investigation timeline.

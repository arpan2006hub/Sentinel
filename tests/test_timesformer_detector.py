"""Tests for the TimeSformer Crime Detector Integration."""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pytest
from PIL import Image

from ai.video.timesformer_crime_detector import TimesformerCrimeDetector


def create_dummy_frame(color: tuple[int, int, int] = (100, 150, 200)) -> Image.Image:
    """Create a synthetic PIL RGB image."""
    arr = np.full((120, 160, 3), color, dtype=np.uint8)
    return Image.fromarray(arr)


class TestTimesformerCrimeDetector:
    """Test suite for TimesformerCrimeDetector functionality."""

    def test_detector_initialization(self) -> None:
        """Verify detector initial properties and model metadata."""
        detector = TimesformerCrimeDetector(auto_download=False)
        assert detector.REPO_ID == "Nikeytas/timesformer-best-crime-detector"
        assert detector.MODEL_F1_SCORE == 0.8868
        assert detector.MODEL_ACCURACY == 0.8425
        assert detector.device in ("cuda", "cpu")

    def test_preprocessing_frames(self) -> None:
        """Verify preprocessing transforms sequence into standard (1, T, 3, 224, 224) tensor."""
        detector = TimesformerCrimeDetector(auto_download=False)
        frames = [create_dummy_frame((i * 10, i * 15, i * 20)) for i in range(16)]
        tensor = detector.preprocess_frames(frames)

        # Should have shape (1, 16, 3, 224, 224)
        assert tensor.shape == (1, 16, 3, 224, 224)

    def test_predict_clip_fallback(self) -> None:
        """Verify clip inference produces structured output even in fallback mode."""
        detector = TimesformerCrimeDetector(auto_download=False)
        frames = [create_dummy_frame((50, 50, 50)) for _ in range(16)]
        result = detector.predict_clip(frames, threshold=0.5)

        assert "prediction" in result
        assert result["prediction"] in ("crime", "normal")
        assert "crime_probability" in result
        assert 0.0 <= result["crime_probability"] <= 1.0
        assert "confidence" in result
        assert result["model_f1"] == 0.8868

    def test_canonical_event_structure(self) -> None:
        """Verify that canonical events comply with Sentinel event schema."""
        detector = TimesformerCrimeDetector(auto_download=False)
        segment = {
            "start_seconds": 2.0,
            "end_seconds": 4.0,
            "prediction": "crime",
            "crime_probability": 0.89,
            "confidence": 0.89,
        }
        event = detector._build_canonical_event(
            case_id="CASE-999",
            evidence_id="EVID-TEST",
            location_id="ZONE-VAULT",
            timestamp_start="2026-01-15T10:00:00+00:00",
            timestamp_end="2026-01-15T10:00:02+00:00",
            segment=segment,
            video_path=Path("vault_camera.mp4"),
        )

        assert event["event_id"].startswith("EVT-CRIME-")
        assert event["case_id"] == "CASE-999"
        assert event["action"] == "crime_detected"
        assert event["source_type"] == "cctv_video"
        assert event["location_id"] == "ZONE-VAULT"
        assert event["confidence"] == 0.89
        assert event["metadata"]["model"] == "Nikeytas/timesformer-best-crime-detector"
        assert event["metadata"]["architecture"] == "TimeSformer"
        assert event["metadata"]["f1_score"] == 0.8868
        assert event["metadata"]["crime_probability"] == 0.89


class TestFastAPIIntegration:
    """Test suite for FastAPI endpoints."""

    def test_model_info_endpoint(self) -> None:
        """Test GET /api/video/model-info."""
        from fastapi.testclient import TestClient
        from backend.app.main import app

        client = TestClient(app)
        response = client.get("/api/video/model-info")
        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] == "Nikeytas/timesformer-best-crime-detector"
        assert data["architecture"] == "TimeSformer (Time-Space Transformer)"
        assert data["f1_score"] == 0.8868
        assert data["dataset"] == "UCF-Crime"
        assert "device" in data

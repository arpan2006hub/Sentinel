"""Tests for the TimeSformer Crime Detector integration (no model weights are loaded)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from ai.video.timesformer_crime_detector import TimesformerCrimeDetector


def create_dummy_frame(color: tuple[int, int, int] = (100, 150, 200)) -> Image.Image:
    return Image.fromarray(np.full((120, 160, 3), color, dtype=np.uint8))


def make_detector(tmp_path: Path) -> TimesformerCrimeDetector:
    """Detector pointed at an empty cache dir -> never loads the 485 MB weights."""
    return TimesformerCrimeDetector(auto_download=False, cache_dir=tmp_path / "no-weights")


class TestTimesformerCrimeDetector:
    def test_detector_initialization(self, tmp_path) -> None:
        detector = make_detector(tmp_path)
        assert detector.REPO_ID == "Nikeytas/timesformer-best-crime-detector"
        assert detector.device in ("cuda", "cpu")
        assert detector.is_loaded is False and detector.is_fallback is True
        assert detector.weights_available is False

    def test_lazy_init_does_not_load(self, tmp_path) -> None:
        detector = TimesformerCrimeDetector(cache_dir=tmp_path, load_on_init=False)
        assert detector.is_loaded is False and detector.is_fallback is False
        assert detector.ensure_loaded() is False and detector.is_fallback is True

    def test_preprocessing_frames(self, tmp_path) -> None:
        detector = make_detector(tmp_path)
        frames = [create_dummy_frame((i * 10, i * 15, i * 20)) for i in range(16)]
        tensor = detector.preprocess_frames(frames)
        assert tuple(tensor.shape) == (1, 16, 3, 224, 224)

    def test_predict_clip_fallback_is_clearly_labelled(self, tmp_path) -> None:
        detector = make_detector(tmp_path)
        result = detector.predict_clip([create_dummy_frame((50, 50, 50)) for _ in range(16)], threshold=0.5)
        assert result["prediction"] in ("crime", "normal")
        assert 0.0 <= result["crime_probability"] <= 1.0
        assert result["is_fallback"] is True
        assert result["model_f1"] is None  # fallback must not borrow the model's F1 score
        assert "fallback" in result["model_name"]

    def test_canonical_event_structure(self, tmp_path) -> None:
        detector = make_detector(tmp_path)
        segment = {"start_seconds": 2.0, "end_seconds": 4.0, "prediction": "crime",
                   "crime_probability": 0.89, "confidence": 0.89}
        event = detector._build_canonical_event(
            case_id="CASE-999", evidence_id="EVID-TEST", location_id="ZONE-VAULT",
            timestamp_start="2026-01-15T10:00:00+00:00", timestamp_end="2026-01-15T10:00:02+00:00",
            segment=segment, video_path=Path("vault_camera.mp4"),
        )
        assert event["event_id"].startswith("EVT-CRIME-")
        assert event["action"] == "crime_detected"
        assert event["source_type"] == "cctv_video"
        assert event["metadata"]["model"] == "Nikeytas/timesformer-best-crime-detector"
        assert event["metadata"]["f1_score"] == 0.8868
        assert event["metadata"]["is_fallback"] is False

    def test_analyze_video_uses_start_time(self, tmp_path) -> None:
        cv2 = __import__("cv2")
        clip = tmp_path / "clip.avi"
        writer = cv2.VideoWriter(str(clip), cv2.VideoWriter_fourcc(*"MJPG"), 10, (64, 48))
        for i in range(30):  # 3 seconds
            frame = np.full((48, 64, 3), 40, np.uint8)
            frame[:, (i * 4) % 60:(i * 4) % 60 + 4] = 255
            writer.write(frame)
        writer.release()

        detector = make_detector(tmp_path)
        result = detector.analyze_video(clip, window_seconds=1.0, stride_seconds=1.0, threshold=0.0,
                                        base_timestamp="2026-01-16T21:58:00Z", max_seconds=2.0,
                                        location_id="ZONE-RESTRICTED-SERVER-ROOM")
        assert result["is_fallback"] is True and result["model_f1_score"] is None
        assert result["timestamp_is_estimated"] is False
        assert result["analyzed_seconds"] == 2.0
        assert result["canonical_events"][0]["timestamp_start"].startswith("2026-01-16T21:58:00")


class TestFastAPIIntegration:
    def test_model_info_endpoint(self, client) -> None:
        response = client.get("/api/video/model-info")
        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] == "Nikeytas/timesformer-best-crime-detector"
        assert data["is_loaded"] is False and data["weights_available"] is False
        assert "unverified" in data["metrics_source"] or "not verified" in data["metrics_source"]

    def test_analyze_path_outside_project_rejected(self, client, tmp_path) -> None:
        outside = Path(tmp_path).anchor + "definitely-not-allowed.mp4"
        response = client.post("/api/video/analyze", json={"video_path": outside})
        assert response.status_code == 403

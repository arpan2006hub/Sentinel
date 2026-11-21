"""Runtime canonical-event contract validation tests."""

from __future__ import annotations

from ai.processing.validation import validate_canonical_events


def _event(**overrides):
    event = {
        "event_id": "EVT-VALID-0001",
        "case_id": "case-001",
        "timestamp": "2026-01-15T10:00:00Z",
        "source": "cyber",
        "source_type": "endpoint_log",
        "source_id": "evidence-001",
        "actor_id": "user_001",
        "action": "anomalous_activity",
        "score": 0.85,
        "prediction": 1,
        "metadata": {},
    }
    event.update(overrides)
    return event


def test_accepts_valid_runtime_event_and_video_interval_timestamp():
    valid, invalid = validate_canonical_events([
        _event(),
        _event(event_id="EVT-VIDEO-0001", timestamp=None, timestamp_start="2026-01-15T10:00:00Z",
               source="video", source_type="cctv_video", action="motion_anomaly"),
    ])
    assert len(valid) == 2
    assert invalid == []


def test_rejects_missing_source_identifier():
    event = _event()
    del event["source_id"]
    valid, invalid = validate_canonical_events([event])
    assert valid == []
    assert invalid[0]["event_id"] == "EVT-VALID-0001"
    assert any("source_id" in error for error in invalid[0]["errors"])


def test_rejects_out_of_range_scores():
    valid, invalid = validate_canonical_events([_event(score=1.5)])
    assert valid == []
    assert any("score" in error for error in invalid[0]["errors"])


def test_rejects_duplicate_event_ids():
    valid, invalid = validate_canonical_events([_event(), _event(source_id="evidence-002")])
    assert len(valid) == 1
    assert len(invalid) == 1
    assert any("duplicate identifier" in error for error in invalid[0]["errors"])


def test_rejects_non_object_payloads_without_raising():
    valid, invalid = validate_canonical_events([None])  # type: ignore[list-item]
    assert valid == []
    assert invalid[0]["errors"] == ["event must be a JSON object"]

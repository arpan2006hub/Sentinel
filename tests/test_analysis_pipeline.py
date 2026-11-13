"""End-to-end tests: scenario evidence -> analysis run -> per-case API outputs."""

from __future__ import annotations

import json

import pytest

from ai.processing import processors
from ai.processing.router import detect_processor

EVIDENCE = [
    ("cyber.csv", "endpoint_log"),
    ("badge.csv", "badge_log"),
    ("video.csv", "video_features"),
    ("documents.jsonl", "text_document"),
]


def _create_case_with_scenario(client, scenario_dir) -> str:
    case_id = client.post("/api/cases", json={"title": "Night Copy"}).json()["case_id"]
    for name, source_type in EVIDENCE:
        with open(scenario_dir / name, "rb") as handle:
            res = client.post("/api/evidence", data={"case_id": case_id, "source_type": source_type},
                              files={"file": (name, handle, "application/octet-stream")})
        assert res.status_code == 201, res.text
    return case_id


@pytest.fixture
def analysed_case(client, scenario_dir):
    case_id = _create_case_with_scenario(client, scenario_dir)
    start = client.post("/api/analysis/start", json={"case_id": case_id, "include_video": False})
    assert start.status_code == 202, start.text
    # TestClient runs background tasks before returning, so the run is finished.
    run = client.get(f"/api/analysis/{start.json()['run_id']}").json()
    assert run["status"] == "completed", run
    return case_id, run


class TestAnalysisPipeline:
    def test_run_summary_and_ground_truth(self, analysed_case, scenario_dir) -> None:
        _, run = analysed_case
        truth = json.loads((scenario_dir / "scenario_ground_truth.json").read_text(encoding="utf-8"))
        assert run["summary"]["top_suspect"] == truth["malicious_entity"]
        assert run["summary"]["evidence_processed"] == 4
        assert set(run["summary"]["sources_represented"]) == {"cyber", "physical", "video", "document"}
        assert all(r["status"] == "processed" for r in run["evidence_results"])

    def test_expected_contradictions(self, client, analysed_case, scenario_dir) -> None:
        case_id, _ = analysed_case
        truth = json.loads((scenario_dir / "scenario_ground_truth.json").read_text(encoding="utf-8"))
        anomalies = client.get(f"/api/anomalies/{case_id}").json()["anomalies"]
        found = {a["type"] for a in anomalies}
        assert set(truth["expected_contradictions"]) <= found
        # Benign hard negative: the admin's authorised daily server-room visits are not flagged.
        assert not any(a["entity"] == "user_003" for a in anomalies)

        detail = client.get(f"/api/anomalies/{case_id}/{anomalies[0]['anomaly_id']}").json()
        assert detail["events"] and detail["evidence_ids"]

    def test_case_scoped_outputs(self, client, analysed_case) -> None:
        case_id, _ = analysed_case
        other = client.post("/api/cases", json={"title": "Empty case"}).json()["case_id"]

        timeline = client.get(f"/api/timeline/{case_id}").json()
        assert timeline["analyzed"] and timeline["total"] > 0
        assert client.get(f"/api/timeline/{other}").json()["total"] == 0

        filtered = client.get(f"/api/timeline/{case_id}", params={
            "actor_id": "user_007", "from": "2026-01-16T21:00:00Z", "to": "2026-01-16T23:00:00Z"}).json()
        assert filtered["total"] >= 5
        assert {e["source"] for e in filtered["events"]} >= {"cyber", "physical", "document"}

        clusters = client.get(f"/api/timeline/{case_id}/clusters", params={"cross_modal_only": True}).json()
        assert clusters["total"] >= 1 and "events" not in clusters["clusters"][0]

        graph = client.get(f"/api/graph/{case_id}", params={"format": "cytoscape"}).json()
        node_types = {n["data"]["type"] for n in graph["elements"]["nodes"]}
        assert {"user", "event", "location", "evidence", "anomaly"} <= node_types

        summary = client.get(f"/api/cases/{case_id}/summary").json()
        assert summary["case"]["event_count"] > 0 and summary["case"]["anomaly_count"] > 0
        assert summary["top_suspects"][0]["entity"] == "user_007"
        assert summary["top_suspects"][0]["reasons"] and summary["top_suspects"][0]["evidence_ids"]

        evidence = client.get("/api/evidence", params={"case_id": case_id}).json()["evidence"]
        assert {e["processing_status"] for e in evidence} == {"processed"}

    def test_concurrent_run_rejected_and_unknown_case(self, client) -> None:
        from app.schemas.analysis import AnalysisStartRequest
        from app.services.analysis_service import AnalysisAlreadyRunningError, AnalysisService

        assert client.post("/api/analysis/start", json={"case_id": "missing"}).status_code == 404
        case_id = client.post("/api/cases", json={"title": "Busy"}).json()["case_id"]
        AnalysisService.get_instance().start_run(AnalysisStartRequest(case_id=case_id))  # stays queued
        with pytest.raises(AnalysisAlreadyRunningError):
            AnalysisService.get_instance().start_run(AnalysisStartRequest(case_id=case_id))
        assert client.post("/api/analysis/start", json={"case_id": case_id}).status_code == 409

    def test_video_evidence_skipped_when_disabled(self, client, isolated_env) -> None:
        case_id = client.post("/api/cases", json={"title": "Video"}).json()["case_id"]
        client.post("/api/evidence", data={"case_id": case_id, "source_type": "cctv_video"},
                    files={"file": ("clip.mp4", b"not really a video", "video/mp4")})
        run_id = client.post("/api/analysis/start", json={"case_id": case_id, "include_video": False}).json()["run_id"]
        run = client.get(f"/api/analysis/{run_id}").json()
        assert run["status"] == "completed"
        assert run["evidence_results"][0]["status"] == "skipped"
        assert client.get(f"/api/timeline/{case_id}").json()["total"] == 0


class TestProcessors:
    def test_document_without_timestamp_is_not_given_a_fake_time(self, tmp_path) -> None:
        doc = tmp_path / "note.txt"
        doc.write_text("Guard saw user_009 copying confidential files to USB in the server room.", encoding="utf-8")
        events = processors.process_documents(doc, source_id="EV1")
        assert events and events[0]["timestamp"] is None

        events = processors.process_documents(doc, source_id="EV1", default_timestamp="2026-01-16T22:00:00Z")
        assert events[0]["timestamp"] == "2026-01-16T22:00:00Z"

    def test_document_aliases_deduplicated(self, tmp_path) -> None:
        doc = tmp_path / "d.jsonl"
        doc.write_text(json.dumps({"document_id": "D1", "timestamp": "2026-01-16T22:30:00Z",
                                   "text": "badge BADGE-007 denied; user_007 left with a USB drive, unauthorized"}),
                       encoding="utf-8")
        actors = [e["actor_id"] for e in processors.process_documents(doc, source_id="EV2")]
        assert len(actors) == 1

    def test_detect_processor(self, tmp_path) -> None:
        assert detect_processor("general", tmp_path / "x.mp4") == "video"
        assert detect_processor("general", tmp_path / "x.jsonl") == "document"
        assert detect_processor("badge_log", tmp_path / "x.csv") == "badge"
        assert detect_processor("pdf_document", tmp_path / "x.pdf") == "unsupported"

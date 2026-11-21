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
        assert detect_processor("pdf_document", tmp_path / "x.pdf") == "document"
        assert detect_processor("general", tmp_path / "x.pdf") == "document"


class TestPdfProcessing:
    @staticmethod
    def _write_text_pdf(path, pages: list[str]) -> None:
        from pypdf import PdfWriter
        from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

        writer = PdfWriter()
        for text in pages:
            page = writer.add_blank_page(width=612, height=792)
            font = DictionaryObject({
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            })
            resources = DictionaryObject({
                NameObject("/Font"): DictionaryObject({
                    NameObject("/F1"): writer._add_object(font),
                }),
            })
            page[NameObject("/Resources")] = resources
            stream = DecodedStreamObject()
            escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream.set_data(f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("utf-8"))
            page[NameObject("/Contents")] = writer._add_object(stream)
        with path.open("wb") as handle:
            writer.write(handle)

    def test_text_pdf_extracts_events_with_page_references(self, tmp_path) -> None:
        pdf = tmp_path / "incident-report.pdf"
        self._write_text_pdf(pdf, [
            "Guard report: user_007 unauthorized exfiltration of confidential source code to USB in ZONE-SERVER-ROOM at 2026-01-16T22:30:00Z.",
            "Follow-up: user_009 exfiltrated restricted source code to a competitor after hours using USB.",
        ])

        events = processors.process_documents(pdf, source_id="PDF-EVIDENCE")

        assert len(events) == 2
        assert {event["source_type"] for event in events} == {"pdf_document"}
        assert {event["page_number"] for event in events} == {1, 2}
        assert {event["actor_id"] for event in events} == {"user_007", "user_009"}
        assert events[0]["timestamp"] == "2026-01-16T22:30:00Z"
        assert all(event["document_id"] == "incident-report" for event in events)
        assert all(event["metadata"]["extraction_method"] == "pypdf_embedded_text" for event in events)
        assert all(event["metadata"]["pages_without_embedded_text"] == [] for event in events)

    def test_scanned_pdf_ocr_can_be_disabled_with_actionable_error(self, tmp_path, monkeypatch) -> None:
        from pypdf import PdfWriter

        pdf = tmp_path / "scanned.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        with pdf.open("wb") as handle:
            writer.write(handle)

        monkeypatch.setenv("PDF_OCR_ENABLED", "false")
        with pytest.raises(ValueError, match="OCR is disabled"):
            processors.process_documents(pdf, source_id="PDF-SCAN")

    def test_scanned_pdf_reports_missing_tesseract_runtime(self, tmp_path, monkeypatch) -> None:
        from pypdf import PdfWriter
        from ai.documents.ocr import pdf_ocr

        pdf = tmp_path / "scanned-no-runtime.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        with pdf.open("wb") as handle:
            writer.write(handle)

        def missing_runtime(_path, _page_index):
            raise RuntimeError(
                "Tesseract OCR executable was not found. Install Tesseract and add it to PATH."
            )

        monkeypatch.setattr(pdf_ocr, "extract_pdf_page_text", missing_runtime)
        with pytest.raises(ValueError, match="Tesseract OCR executable was not found"):
            processors.process_documents(pdf, source_id="PDF-NO-OCR")

    def test_scanned_pdf_uses_tesseract_ocr_and_preserves_provenance(self, tmp_path) -> None:
        import shutil

        pytest.importorskip("pypdfium2")
        pytest.importorskip("pytesseract")
        import os
        if not shutil.which("tesseract") and not os.getenv("TESSERACT_CMD"):
            pytest.skip("Tesseract executable is not installed")

        from PIL import Image, ImageDraw, ImageFont

        pdf = tmp_path / "scanned-incident.pdf"
        image = Image.new("RGB", (1654, 2339), "white")
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default(size=48)
        draw.multiline_text(
            (100, 180),
            "INCIDENT REPORT\nUser user_007 copied confidential source code to USB\n"
            "Unauthorized exfiltration after hours\n2026-01-16T22:30:00Z",
            fill="black",
            font=font,
            spacing=35,
        )
        image.save(pdf, "PDF", resolution=200)
        image.close()

        events = processors.process_documents(pdf, source_id="PDF-OCR")

        assert len(events) == 1
        event = events[0]
        assert event["actor_id"] == "user_007"
        assert event["timestamp"] == "2026-01-16T22:30:00Z"
        assert event["page_number"] == 1
        assert event["source_type"] == "pdf_document"
        assert event["metadata"]["extraction_method"] == "tesseract_ocr"
        assert event["metadata"]["ocr_engine"] == "tesseract"
        assert event["metadata"]["pages_without_embedded_text"] == [1]

    def test_pdf_upload_is_processed_by_case_analysis(self, client, tmp_path) -> None:
        pdf = tmp_path / "statement.pdf"
        self._write_text_pdf(pdf, [
            "Statement: user_007 exfiltrated confidential source code using USB after hours without authorization in ZONE-SECURE-ROOM."
        ])
        case_id = client.post("/api/cases", json={"title": "PDF report"}).json()["case_id"]
        with pdf.open("rb") as handle:
            uploaded = client.post(
                "/api/evidence",
                data={
                    "case_id": case_id,
                    "source_type": "pdf_document",
                    "metadata": json.dumps({"recorded_at": "2026-01-16T22:30:00Z"}),
                },
                files={"file": (pdf.name, handle, "application/pdf")},
            )
        assert uploaded.status_code == 201, uploaded.text

        started = client.post("/api/analysis/start", json={"case_id": case_id})
        assert started.status_code == 202, started.text
        run = client.get(f"/api/analysis/{started.json()['run_id']}").json()

        assert run["status"] == "completed"
        assert run["evidence_results"][0]["status"] == "processed"
        assert run["evidence_results"][0]["events"] == 1
        timeline = client.get(f"/api/timeline/{case_id}").json()
        assert timeline["total"] == 1
        assert timeline["events"][0]["source_type"] == "pdf_document"
        assert timeline["events"][0]["page_number"] == 1

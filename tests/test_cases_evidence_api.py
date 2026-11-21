"""Tests for Case and Evidence services and API."""

from __future__ import annotations

import io
import sqlite3

import pytest

from app.db import append_audit, connect
from app.schemas.cases import CaseCreate, CaseUpdate
from app.schemas.analysis import AnalysisStartRequest
from app.services.analysis_service import AnalysisService
from app.services.case_service import CaseService
from app.services.evidence_service import EvidenceService


class TestCaseService:
    def test_create_and_get_case(self) -> None:
        svc = CaseService.get_instance()
        case = svc.create_case(CaseCreate(title="Insider Threat Alpha", description="user_007", metadata={"priority": "high"}))
        assert case.status == "open"
        assert case.metadata["priority"] == "high"
        fetched = svc.get_case(case.case_id)
        assert fetched is not None and fetched.title == "Insider Threat Alpha"

    def test_list_and_update_case(self) -> None:
        svc = CaseService.get_instance()
        c1 = svc.create_case(CaseCreate(title="Case 1"))
        svc.create_case(CaseCreate(title="Case 2"))
        assert svc.list_cases().total == 2
        updated = svc.update_case(c1.case_id, CaseUpdate(status="investigating", description="Active review"))
        assert updated is not None and updated.status == "investigating"
        assert svc.list_cases(status="investigating").total == 1

    def test_delete_case_removes_files_but_keeps_audit(self, isolated_env) -> None:
        svc, ev_svc = CaseService.get_instance(), EvidenceService.get_instance()
        case = svc.create_case(CaseCreate(title="To Delete"))
        src = isolated_env["tmp"] / "a.txt"
        src.write_text("x", encoding="utf-8")
        ev = ev_svc.ingest_local_file(case.case_id, src)
        assert (isolated_env["storage"] / case.case_id).is_dir()
        assert svc.delete_case(case.case_id) is True
        assert svc.get_case(case.case_id) is None
        assert not (isolated_env["storage"] / case.case_id).exists()
        actions = [a.action for a in ev_svc.get_audit_trail(ev.evidence_id)]
        assert actions == ["ingested", "deleted"]


class TestEvidenceService:
    def test_ingest_and_verify_evidence(self, isolated_env) -> None:
        case = CaseService.get_instance().create_case(CaseCreate(title="Evidence Case"))
        ev_svc = EvidenceService.get_instance()
        sample = isolated_env["tmp"] / "auth_log.csv"
        sample.write_text("timestamp,user,action\n2026-01-01T00:00:00Z,user_001,login\n", encoding="utf-8")
        evidence = ev_svc.ingest_local_file(case.case_id, sample, source_type="auth_log")
        assert evidence.file_hash.startswith("sha256:")
        result = ev_svc.verify_evidence(evidence.evidence_id)
        assert result is not None and result.integrity == "verified"
        audit = ev_svc.get_audit_trail(evidence.evidence_id)
        assert [a.action for a in audit] == ["ingested", "verified"]
        assert audit[1].prev_hash == audit[0].record_hash

    def test_tamper_detection(self, isolated_env) -> None:
        case = CaseService.get_instance().create_case(CaseCreate(title="Tamper Test Case"))
        ev_svc = EvidenceService.get_instance()
        sample = isolated_env["tmp"] / "sensitive.txt"
        sample.write_text("Original confidential evidence", encoding="utf-8")
        evidence = ev_svc.ingest_local_file(case.case_id, sample, source_type="text_document")
        stored = ev_svc.get_evidence_file_path(evidence.evidence_id)
        assert stored is not None
        stored.write_text("Tampered content!", encoding="utf-8")
        result = ev_svc.verify_evidence(evidence.evidence_id)
        assert result is not None and result.integrity == "failed"
        assert "modified or corrupted" in (result.message or "")

    def test_audit_chain_detects_edited_record(self, isolated_env) -> None:
        case = CaseService.get_instance().create_case(CaseCreate(title="Audit chain"))
        ev_svc = EvidenceService.get_instance()
        sample = isolated_env["tmp"] / "log.txt"
        sample.write_text("data", encoding="utf-8")
        evidence = ev_svc.ingest_local_file(case.case_id, sample)
        ev_svc.verify_evidence(evidence.evidence_id)
        assert ev_svc.verify_audit_chain(evidence.evidence_id).valid is True

        conn = sqlite3.connect(str(ev_svc.db_path))
        conn.execute("UPDATE evidence_audit SET actor = 'mallory' WHERE evidence_id = ? AND action = 'ingested'",
                     (evidence.evidence_id,))
        conn.commit()
        conn.close()
        result = ev_svc.verify_audit_chain(evidence.evidence_id)
        assert result.valid is False and result.broken_at_index == 0

    def test_audit_chain_accepts_legacy_prefix_before_hashed_records(self, isolated_env) -> None:
        case = CaseService.get_instance().create_case(CaseCreate(title="Legacy audit compatibility"))
        ev_svc = EvidenceService.get_instance()
        evidence_id = "legacy-evidence-id"

        # Simulate a row created before prev_hash / record_hash were added.
        with connect(ev_svc.db_path) as conn:
            conn.execute(
                """INSERT INTO evidence_audit
                   (audit_id, evidence_id, case_id, action, actor, timestamp, details)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ("legacy-audit-id", evidence_id, case.case_id, "ingested", "system", "2026-01-01T00:00:00Z", "{}"),
            )
            append_audit(conn, evidence_id, case.case_id, "verified", "system", {})

        result = ev_svc.verify_audit_chain(evidence_id)
        assert result.valid is True
        assert result.legacy_unverifiable == 1

    def test_audit_chain_detects_removed_record_hash(self, isolated_env) -> None:
        case = CaseService.get_instance().create_case(CaseCreate(title="Missing audit hash"))
        ev_svc = EvidenceService.get_instance()
        sample = isolated_env["tmp"] / "log.txt"
        sample.write_text("data", encoding="utf-8")
        evidence = ev_svc.ingest_local_file(case.case_id, sample)
        ev_svc.verify_evidence(evidence.evidence_id)
        assert ev_svc.verify_audit_chain(evidence.evidence_id).valid is True

        conn = sqlite3.connect(str(ev_svc.db_path))
        conn.execute(
            "UPDATE evidence_audit SET record_hash = NULL WHERE evidence_id = ? AND action = 'verified'",
            (evidence.evidence_id,),
        )
        conn.commit()
        conn.close()

        result = ev_svc.verify_audit_chain(evidence.evidence_id)
        assert result.valid is False
        assert result.broken_at_index == 1
        assert "record hash is missing" in (result.reason or "")


class TestCaseEvidenceAPI:
    def test_case_and_evidence_api_lifecycle(self, client) -> None:
        create = client.post("/api/cases", json={"title": "API Case Test", "description": "Via TestClient"})
        assert create.status_code == 201
        case_id = create.json()["case_id"]
        assert client.get(f"/api/cases/{case_id}").status_code == 200
        assert client.get(f"/cases/{case_id}").status_code == 200  # legacy un-prefixed route

        upload = client.post(
            "/api/evidence",
            data={"case_id": case_id, "source_type": "endpoint_log", "metadata": '{"location_id": "ZONE-HQ"}'},
            files={"file": ("network.csv", io.BytesIO(b"h1,h2\nv1,v2\n"), "text/csv")},
        )
        assert upload.status_code == 201, upload.text
        evidence_id = upload.json()["evidence_id"]
        assert upload.json()["metadata"]["location_id"] == "ZONE-HQ"

        assert client.get(f"/api/evidence/{evidence_id}/verify").json()["integrity"] == "verified"
        download = client.get(f"/api/evidence/{evidence_id}/file")
        assert download.status_code == 200 and download.content == b"h1,h2\nv1,v2\n"
        audit = client.get(f"/api/evidence/{evidence_id}/audit").json()
        assert [a["action"] for a in audit] == ["ingested", "verified", "accessed"]
        assert client.get(f"/api/evidence/{evidence_id}/audit/verify").json()["valid"] is True

        assert client.delete(f"/api/evidence/{evidence_id}").status_code == 204
        assert client.get(f"/api/evidence/{evidence_id}").status_code == 404
        assert client.get(f"/api/evidence/{evidence_id}/audit").status_code == 200  # audit survives deletion

    def test_upload_sanitizes_windows_path_and_preserves_integrity(self, client, isolated_env) -> None:
        case_id = client.post("/api/cases", json={"title": "Portable filename"}).json()["case_id"]
        payload = b"timestamp,user,action\n2026-01-01T00:00:00Z,user_001,login\n"

        response = client.post(
            "/api/evidence",
            data={"case_id": case_id, "source_type": "endpoint_log"},
            files={"file": (r"..\..\private\auth.csv", io.BytesIO(payload), "text/csv")},
        )

        assert response.status_code == 201, response.text
        evidence = response.json()
        assert evidence["file_name"] == "auth.csv"
        stored_path = EvidenceService.get_instance().get_evidence_file_path(evidence["evidence_id"])
        assert stored_path is not None
        assert stored_path.read_bytes() == payload
        assert stored_path.resolve().is_relative_to(isolated_env["storage"].resolve())
        assert client.get(f"/api/evidence/{evidence['evidence_id']}/verify").json()["integrity"] == "verified"

    def test_upload_cleans_file_when_database_registration_fails(self, client, isolated_env, monkeypatch) -> None:
        case_id = client.post("/api/cases", json={"title": "Registration rollback"}).json()["case_id"]
        service = EvidenceService.get_instance()

        def fail_register(*args, **kwargs):
            raise RuntimeError("simulated database registration failure")

        monkeypatch.setattr(service, "_register", fail_register)
        with pytest.raises(RuntimeError, match="simulated database registration failure"):
            client.post(
                "/api/evidence",
                data={"case_id": case_id, "source_type": "general"},
                files={"file": ("orphan.txt", io.BytesIO(b"must not remain"), "text/plain")},
            )

        case_storage = isolated_env["storage"] / case_id
        assert not case_storage.exists() or list(case_storage.iterdir()) == []
        assert client.get("/api/evidence", params={"case_id": case_id}).json()["total"] == 0

    def test_upload_validation(self, client, isolated_env, monkeypatch) -> None:
        case_id = client.post("/api/cases", json={"title": "Validation"}).json()["case_id"]
        bad_type = client.post("/api/evidence", data={"case_id": case_id, "source_type": "nope"},
                               files={"file": ("a.txt", io.BytesIO(b"x"), "text/plain")})
        assert bad_type.status_code == 422
        missing_case = client.post("/api/evidence", data={"case_id": "missing", "source_type": "general"},
                                   files={"file": ("a.txt", io.BytesIO(b"x"), "text/plain")})
        assert missing_case.status_code == 404

        EvidenceService.get_instance().max_upload_bytes = 10
        too_big = client.post("/api/evidence", data={"case_id": case_id, "source_type": "general"},
                              files={"file": ("big.bin", io.BytesIO(b"x" * 50), "application/octet-stream")})
        assert too_big.status_code == 413
        assert client.get("/api/evidence", params={"case_id": case_id}).json()["total"] == 0
        case_storage = isolated_env["storage"] / case_id
        assert not case_storage.exists() or list(case_storage.iterdir()) == []

    def test_source_types_and_health(self, client) -> None:
        types = {t["source_type"] for t in client.get("/api/evidence/source-types").json()}
        assert {"endpoint_log", "badge_log", "cctv_video", "text_document", "pdf_document"} <= types
        health = client.get("/health").json()
        assert health["status"] == "healthy"
        assert health["video_model"].startswith("weights_missing")

    def test_invalid_case_status_rejected(self, client) -> None:
        case_id = client.post("/api/cases", json={"title": "Status"}).json()["case_id"]
        assert client.patch(f"/api/cases/{case_id}", json={"status": "bogus"}).status_code == 422

    def test_cannot_delete_case_or_evidence_during_active_analysis(self, client) -> None:
        case = client.post("/api/cases", json={"title": "Active analysis deletion guard"}).json()
        case_id = case["case_id"]
        upload = client.post(
            "/api/evidence",
            data={"case_id": case_id, "source_type": "general"},
            files={"file": ("evidence.txt", io.BytesIO(b"important evidence"), "text/plain")},
        )
        assert upload.status_code == 201, upload.text
        evidence_id = upload.json()["evidence_id"]

        run = AnalysisService.get_instance().start_run(AnalysisStartRequest(case_id=case_id))
        assert run.status == "queued"

        delete_evidence = client.delete(f"/api/evidence/{evidence_id}")
        assert delete_evidence.status_code == 409
        assert delete_evidence.json()["detail"]["run_id"] == run.run_id

        delete_case = client.delete(f"/api/cases/{case_id}")
        assert delete_case.status_code == 409
        assert delete_case.json()["detail"]["run_id"] == run.run_id

        assert client.get(f"/api/evidence/{evidence_id}").status_code == 200
        assert client.get(f"/api/cases/{case_id}").status_code == 200

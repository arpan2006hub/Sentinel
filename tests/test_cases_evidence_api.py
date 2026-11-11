"""Tests for Case and Evidence API and Services."""

from __future__ import annotations

import io
import sys
import tempfile
from pathlib import Path

# Add project root and backend to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.cases import CaseCreate, CaseUpdate
from backend.app.services.case_service import CaseService
from backend.app.services.evidence_service import EvidenceService


@pytest.fixture
def temp_storage():
    """Create an isolated temporary directory for sqlite db and evidence files."""
    import gc
    tmpdir_obj = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    tmpdir = Path(tmpdir_obj.name)
    db_path = tmpdir / "test_sentinel.db"
    storage_root = tmpdir / "evidence_store"
    storage_root.mkdir(parents=True, exist_ok=True)

    case_svc = CaseService(db_path=db_path)
    evidence_svc = EvidenceService(db_path=db_path, storage_root=storage_root)

    # Wire singletons
    CaseService._instance = case_svc
    EvidenceService._instance = evidence_svc

    yield {
        "tmpdir": tmpdir,
        "db_path": db_path,
        "storage_root": storage_root,
        "case_svc": case_svc,
        "evidence_svc": evidence_svc,
    }

    CaseService._instance = None
    EvidenceService._instance = None
    gc.collect()
    try:
        tmpdir_obj.cleanup()
    except Exception:
        pass


class TestCaseService:
    """Direct tests for CaseService."""

    def test_create_and_get_case(self, temp_storage) -> None:
        svc: CaseService = temp_storage["case_svc"]
        case = svc.create_case(
            # pyrefly: ignore[bad-argument-type]
            CaseCreate(title="Insider Threat Alpha", description="Investigation into user_007", metadata={"priority": "high"})
        )
        assert case.case_id is not None
        assert case.title == "Insider Threat Alpha"
        assert case.status == "open"
        assert case.metadata["priority"] == "high"

        fetched = svc.get_case(case.case_id)
        assert fetched is not None
        assert fetched.case_id == case.case_id
        assert fetched.title == "Insider Threat Alpha"

    def test_list_and_update_case(self, temp_storage) -> None:
        svc: CaseService = temp_storage["case_svc"]
        # pyrefly: ignore[bad-argument-type]
        c1 = svc.create_case(CaseCreate(title="Case 1"))
        # pyrefly: ignore[bad-argument-type]
        c2 = svc.create_case(CaseCreate(title="Case 2"))

        cases_list = svc.list_cases()
        assert cases_list.total >= 2

        # pyrefly: ignore[bad-argument-type]
        updated = svc.update_case(c1.case_id, CaseUpdate(status="investigating", description="Active review"))
        assert updated is not None
        assert updated.status == "investigating"
        assert updated.description == "Active review"

    def test_delete_case(self, temp_storage) -> None:
        svc: CaseService = temp_storage["case_svc"]
        # pyrefly: ignore[bad-argument-type]
        case = svc.create_case(CaseCreate(title="To Delete"))
        assert svc.delete_case(case.case_id) is True
        assert svc.get_case(case.case_id) is None


class TestEvidenceService:
    """Direct tests for EvidenceService and cryptographic verification."""

    def test_ingest_and_verify_evidence(self, temp_storage) -> None:
        case_svc: CaseService = temp_storage["case_svc"]
        ev_svc: EvidenceService = temp_storage["evidence_svc"]

        # pyrefly: ignore[bad-argument-type]
        case = case_svc.create_case(CaseCreate(title="Evidence Case"))

        # Create dummy file
        sample_file = temp_storage["tmpdir"] / "auth_log.csv"
        sample_file.write_text("timestamp,user,action\n2026-01-01T00:00:00Z,user_001,login\n", encoding="utf-8")

        evidence = ev_svc.ingest_local_file(
            case_id=case.case_id,
            source_path=sample_file,
            source_type="auth_log",
            metadata={"collector": "syslog"},
        )
        assert evidence.evidence_id is not None
        assert evidence.file_name == "auth_log.csv"
        assert evidence.file_hash.startswith("sha256:")

        # Verify integrity
        verify_result = ev_svc.verify_evidence(evidence.evidence_id)
        assert verify_result is not None
        assert verify_result.integrity == "verified"
        assert verify_result.computed_hash == evidence.file_hash

        # Audit trail check
        audit = ev_svc.get_audit_trail(evidence.evidence_id)
        assert len(audit) >= 2  # ingested + verified
        assert audit[0].action == "ingested"
        assert audit[1].action == "verified"

    def test_tamper_detection(self, temp_storage) -> None:
        case_svc: CaseService = temp_storage["case_svc"]
        ev_svc: EvidenceService = temp_storage["evidence_svc"]

        # pyrefly: ignore[bad-argument-type]
        case = case_svc.create_case(CaseCreate(title="Tamper Test Case"))
        sample_file = temp_storage["tmpdir"] / "sensitive.txt"
        sample_file.write_text("Original confidential evidence", encoding="utf-8")

        evidence = ev_svc.ingest_local_file(
            case_id=case.case_id,
            source_path=sample_file,
            source_type="document",
        )
        stored_path = ev_svc.get_evidence_file_path(evidence.evidence_id)
        assert stored_path is not None

        # Simulate tampering
        stored_path.write_text("Tampered confidential evidence - altered content!", encoding="utf-8")

        verify_result = ev_svc.verify_evidence(evidence.evidence_id)
        assert verify_result is not None
        assert verify_result.integrity == "failed"
        assert "modified or corrupted" in (verify_result.message or "")


class TestCaseEvidenceAPIEndpoints:
    """FastAPI TestClient integration tests for Cases and Evidence routes."""

    def test_case_and_evidence_api_lifecycle(self, temp_storage) -> None:
        client = TestClient(app)

        # 1. Create Case
        create_res = client.post("/cases", json={"title": "API Case Test", "description": "Via TestClient"})
        assert create_res.status_code == 201
        case_data = create_res.json()
        case_id = case_data["case_id"]
        assert case_data["title"] == "API Case Test"

        # 2. Get Case
        get_res = client.get(f"/cases/{case_id}")
        assert get_res.status_code == 200

        # 3. Upload Evidence
        file_content = b"header1,header2\nval1,val2\n"
        upload_res = client.post(
            "/evidence",
            data={"case_id": case_id, "source_type": "endpoint_log"},
            files={"file": ("network.csv", io.BytesIO(file_content), "text/csv")},
        )
        assert upload_res.status_code == 201
        ev_data = upload_res.json()
        evidence_id = ev_data["evidence_id"]
        assert ev_data["file_name"] == "network.csv"
        assert ev_data["file_hash"].startswith("sha256:")

        # 4. Verify Evidence via API
        verify_res = client.get(f"/evidence/{evidence_id}/verify")
        assert verify_res.status_code == 200
        verify_data = verify_res.json()
        assert verify_data["integrity"] == "verified"

        # 5. Get Evidence Audit Trail
        audit_res = client.get(f"/evidence/{evidence_id}/audit")
        assert audit_res.status_code == 200
        assert len(audit_res.json()) >= 2

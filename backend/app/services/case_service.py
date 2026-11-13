"""Service layer for Case Management with local-first SQLite storage."""

from __future__ import annotations

import json
import logging
import shutil
import sqlite3
from pathlib import Path
from typing import Any, Optional

from app.config import get_settings
from app.db import append_audit, connect, new_id, utcnow
from app.schemas.cases import CaseCreate, CaseListResponse, CaseResponse, CaseUpdate

logger = logging.getLogger(__name__)


class CaseService:
    """Singleton service managing investigation cases."""

    _instance: Optional[CaseService] = None

    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        settings = get_settings()
        self.db_path = Path(db_path) if db_path else settings.db_path
        self.storage_root = settings.storage_path
        self.artifacts_dir = settings.artifacts_dir
        with connect(self.db_path):
            pass

    @classmethod
    def get_instance(cls, db_path: Optional[str | Path] = None) -> CaseService:
        if cls._instance is None or db_path is not None:
            cls._instance = cls(db_path=db_path)
        return cls._instance

    # ------------------------------------------------------------------ CRUD
    def create_case(self, case_in: CaseCreate) -> CaseResponse:
        case_id = new_id()
        now = utcnow()
        with connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO cases (case_id, title, description, status, created_at, updated_at, metadata) "
                "VALUES (?, ?, ?, 'open', ?, ?, ?)",
                (case_id, case_in.title, case_in.description or "", now, now, json.dumps(case_in.metadata or {})),
            )
        created = self.get_case(case_id)
        assert created is not None
        return created

    def get_case(self, case_id: str) -> Optional[CaseResponse]:
        with connect(self.db_path) as conn:
            row = conn.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
            if not row:
                return None
            return self._row_to_case_response(conn, row)

    def list_cases(self, status: Optional[str] = None, page: int = 1, page_size: int = 20) -> CaseListResponse:
        page = max(1, page)
        page_size = max(1, min(100, page_size))
        offset = (page - 1) * page_size
        with connect(self.db_path) as conn:
            where, params = ("WHERE status = ?", [status]) if status else ("", [])
            total = conn.execute(f"SELECT COUNT(*) FROM cases {where}", params).fetchone()[0]
            rows = conn.execute(
                f"SELECT * FROM cases {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                [*params, page_size, offset],
            ).fetchall()
            cases = [self._row_to_case_response(conn, r) for r in rows]
        return CaseListResponse(cases=cases, total=total, page=page, page_size=page_size)

    def update_case(self, case_id: str, case_update: CaseUpdate) -> Optional[CaseResponse]:
        existing = self.get_case(case_id)
        if not existing:
            return None
        values = {
            "title": case_update.title if case_update.title is not None else existing.title,
            "description": case_update.description if case_update.description is not None else existing.description,
            "status": case_update.status if case_update.status is not None else existing.status,
            "metadata": json.dumps(case_update.metadata if case_update.metadata is not None else existing.metadata),
        }
        with connect(self.db_path) as conn:
            conn.execute(
                "UPDATE cases SET title = ?, description = ?, status = ?, updated_at = ?, metadata = ? WHERE case_id = ?",
                (values["title"], values["description"], values["status"], utcnow(), values["metadata"], case_id),
            )
        return self.get_case(case_id)

    def delete_case(self, case_id: str, actor: str = "investigator") -> bool:
        """Delete a case, its evidence files and analysis outputs.

        Audit records are intentionally kept (chain of custody); a final
        ``deleted`` record is appended for each evidence item.
        """
        with connect(self.db_path) as conn:
            if not conn.execute("SELECT 1 FROM cases WHERE case_id = ?", (case_id,)).fetchone():
                return False
            for ev in conn.execute("SELECT evidence_id, file_name FROM evidence WHERE case_id = ?", (case_id,)).fetchall():
                append_audit(conn, ev["evidence_id"], case_id, "deleted", actor,
                             {"file_name": ev["file_name"], "reason": "case_deleted"})
            conn.execute("DELETE FROM evidence WHERE case_id = ?", (case_id,))
            conn.execute("DELETE FROM analysis_runs WHERE case_id = ?", (case_id,))
            conn.execute("DELETE FROM cases WHERE case_id = ?", (case_id,))
        for directory in (self.storage_root / case_id, self.artifacts_dir / "cases" / case_id):
            if directory.is_dir():
                shutil.rmtree(directory, ignore_errors=True)
        return True

    # --------------------------------------------------------------- helpers
    @staticmethod
    def latest_run(conn: sqlite3.Connection, case_id: str, completed_only: bool = False) -> Optional[sqlite3.Row]:
        query = "SELECT * FROM analysis_runs WHERE case_id = ?"
        if completed_only:
            query += " AND status = 'completed'"
        return conn.execute(query + " ORDER BY created_at DESC LIMIT 1", (case_id,)).fetchone()

    def _row_to_case_response(self, conn: sqlite3.Connection, row: sqlite3.Row) -> CaseResponse:
        try:
            metadata: dict[str, Any] = json.loads(row["metadata"])
        except Exception:
            metadata = {}
        evidence_count = conn.execute(
            "SELECT COUNT(*) FROM evidence WHERE case_id = ?", (row["case_id"],)
        ).fetchone()[0]
        latest = self.latest_run(conn, row["case_id"])
        completed = self.latest_run(conn, row["case_id"], completed_only=True)
        summary = json.loads(completed["summary"]) if completed else {}
        return CaseResponse(
            case_id=row["case_id"],
            title=row["title"],
            description=row["description"],
            status=row["status"],
            evidence_count=evidence_count,
            event_count=int(summary.get("total_events", 0)),
            anomaly_count=int(summary.get("contradictions_detected", 0)),
            last_analysis_run_id=latest["run_id"] if latest else None,
            last_analysis_status=latest["status"] if latest else None,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            metadata=metadata,
        )

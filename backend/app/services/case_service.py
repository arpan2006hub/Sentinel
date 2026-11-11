"""Service layer for Case Management with local-first persistent storage."""

from __future__ import annotations

import datetime
import json
import logging
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Optional

from app.schemas.cases import CaseCreate, CaseListResponse, CaseResponse, CaseUpdate

logger = logging.getLogger(__name__)


class CaseService:
    """Singleton service managing investigation cases backed by SQLite."""

    _instance: Optional[CaseService] = None

    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        storage_root = Path(os.getenv("STORAGE_PATH", "./local-evidence-store"))
        storage_root.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(db_path) if db_path else (storage_root / "sentinel.db")
        self._init_db()

    @classmethod
    def get_instance(cls, db_path: Optional[str | Path] = None) -> CaseService:
        if cls._instance is None or db_path is not None:
            cls._instance = cls(db_path=db_path)
        return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize SQLite database tables if not existing."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cases (
                    case_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'open',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status)")
            conn.commit()

    def create_case(self, case_in: CaseCreate) -> CaseResponse:
        """Create a new investigation case."""
        case_id = str(uuid.uuid4())
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        metadata_str = json.dumps(case_in.metadata or {})

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO cases (case_id, title, description, status, created_at, updated_at, metadata)
                VALUES (?, ?, ?, 'open', ?, ?, ?)
                """,
                (case_id, case_in.title, case_in.description or "", now, now, metadata_str),
            )
            conn.commit()

        return CaseResponse(
            case_id=case_id,
            title=case_in.title,
            description=case_in.description or "",
            status="open",
            evidence_count=0,
            event_count=0,
            anomaly_count=0,
            created_at=now,
            updated_at=now,
            metadata=case_in.metadata or {},
        )

    def get_case(self, case_id: str) -> Optional[CaseResponse]:
        """Fetch a specific case by its ID."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
            if not row:
                return None

            # Get counts
            evidence_count = conn.execute(
                "SELECT COUNT(*) FROM evidence WHERE case_id = ?", (case_id,)
            ).fetchone()[0] if self._table_exists(conn, "evidence") else 0

        return self._row_to_case_response(row, evidence_count=evidence_count)

    def list_cases(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> CaseListResponse:
        """List cases with optional status filter and pagination."""
        page = max(1, page)
        page_size = max(1, min(100, page_size))
        offset = (page - 1) * page_size

        with self._get_connection() as conn:
            if status:
                total = conn.execute(
                    "SELECT COUNT(*) FROM cases WHERE status = ?", (status,)
                ).fetchone()[0]
                rows = conn.execute(
                    "SELECT * FROM cases WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (status, page_size, offset),
                ).fetchall()
            else:
                total = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
                rows = conn.execute(
                    "SELECT * FROM cases ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (page_size, offset),
                ).fetchall()

            cases: list[CaseResponse] = []
            has_evidence_tbl = self._table_exists(conn, "evidence")
            for r in rows:
                ev_count = conn.execute(
                    "SELECT COUNT(*) FROM evidence WHERE case_id = ?", (r["case_id"],)
                ).fetchone()[0] if has_evidence_tbl else 0
                cases.append(self._row_to_case_response(r, evidence_count=ev_count))

        return CaseListResponse(
            cases=cases,
            total=total,
            page=page,
            page_size=page_size,
        )

    def update_case(self, case_id: str, case_update: CaseUpdate) -> Optional[CaseResponse]:
        """Update fields on an existing case."""
        existing = self.get_case(case_id)
        if not existing:
            return None

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        new_title = case_update.title if case_update.title is not None else existing.title
        new_desc = case_update.description if case_update.description is not None else existing.description
        new_status = case_update.status if case_update.status is not None else existing.status
        new_meta = case_update.metadata if case_update.metadata is not None else existing.metadata

        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE cases
                SET title = ?, description = ?, status = ?, updated_at = ?, metadata = ?
                WHERE case_id = ?
                """,
                (new_title, new_desc, new_status, now, json.dumps(new_meta), case_id),
            )
            conn.commit()

        return self.get_case(case_id)

    def delete_case(self, case_id: str) -> bool:
        """Delete a case and associated metadata."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM cases WHERE case_id = ?", (case_id,))
            if cursor.rowcount == 0:
                return False
            if self._table_exists(conn, "evidence"):
                conn.execute("DELETE FROM evidence WHERE case_id = ?", (case_id,))
            conn.commit()
            return True

    def _table_exists(self, conn: sqlite3.Connection, table_name: str) -> bool:
        cur = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?", (table_name,)
        )
        return cur.fetchone() is not None

    def _row_to_case_response(self, row: sqlite3.Row, evidence_count: int = 0) -> CaseResponse:
        try:
            metadata = json.loads(row["metadata"])
        except Exception:
            metadata = {}

        return CaseResponse(
            case_id=row["case_id"],
            title=row["title"],
            description=row["description"],
            status=row["status"],
            evidence_count=evidence_count,
            event_count=0,
            anomaly_count=0,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            metadata=metadata,
        )


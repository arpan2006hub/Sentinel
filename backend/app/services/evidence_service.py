"""Service layer for Evidence Ingestion, Storage, and Cryptographic Integrity Verification."""

from __future__ import annotations

import datetime
import hashlib
import json
import logging
import os
import shutil
import sqlite3
import uuid
from pathlib import Path
from typing import Any, BinaryIO, Optional

from fastapi import UploadFile  # type: ignore[import-untyped,import-not-found]

from app.schemas.evidence import (
    EvidenceAuditRecord,
    EvidenceListResponse,
    EvidenceResponse,
    EvidenceVerifyResponse,
)

logger = logging.getLogger(__name__)


class EvidenceService:
    """Service managing evidence files, SHA-256 hashing, and chain-of-custody audit logs."""

    _instance: Optional[EvidenceService] = None

    def __init__(self, db_path: Optional[str | Path] = None, storage_root: Optional[str | Path] = None) -> None:
        self.storage_root = Path(storage_root or os.getenv("STORAGE_PATH", "./local-evidence-store"))
        self.storage_root.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(db_path) if db_path else (self.storage_root / "sentinel.db")
        self._init_db()

    @classmethod
    def get_instance(
        cls,
        db_path: Optional[str | Path] = None,
        storage_root: Optional[str | Path] = None,
    ) -> EvidenceService:
        if cls._instance is None or db_path is not None:
            cls._instance = cls(db_path=db_path, storage_root=storage_root)
        return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize SQLite database tables for evidence and audit trail."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS evidence (
                    evidence_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    file_size_bytes INTEGER NOT NULL,
                    source_type TEXT NOT NULL,
                    processing_status TEXT NOT NULL DEFAULT 'pending',
                    ingested_at TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS evidence_audit (
                    audit_id TEXT PRIMARY KEY,
                    evidence_id TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    details TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_evidence_case ON evidence(case_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_evidence ON evidence_audit(evidence_id)")
            conn.commit()

    @staticmethod
    def compute_sha256(file_obj: BinaryIO) -> tuple[str, int]:
        """Compute SHA-256 hash and byte size of an open binary stream."""
        hasher = hashlib.sha256()
        total_bytes = 0
        file_obj.seek(0)
        while chunk := file_obj.read(65536):
            hasher.update(chunk)
            total_bytes += len(chunk)
        file_obj.seek(0)
        return f"sha256:{hasher.hexdigest()}", total_bytes

    async def ingest_upload(
        self,
        case_id: str,
        file: UploadFile,
        source_type: str = "general",
        metadata: Optional[dict[str, Any]] = None,
        actor: str = "investigator",
    ) -> EvidenceResponse:
        """Ingest evidence from an uploaded multipart file."""
        evidence_id = str(uuid.uuid4())
        safe_filename = Path(file.filename or "evidence.bin").name

        dest_dir = self.storage_root / case_id / evidence_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / safe_filename

        # Stream copy to disk while hashing
        hasher = hashlib.sha256()
        file_size = 0
        with open(dest_path, "wb") as out_file:
            while chunk := await file.read(65536):
                hasher.update(chunk)
                out_file.write(chunk)
                file_size += len(chunk)

        file_hash = f"sha256:{hasher.hexdigest()}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        metadata_dict = metadata or {}

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO evidence (
                    evidence_id, case_id, file_name, file_path, file_hash,
                    file_size_bytes, source_type, processing_status, ingested_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    evidence_id,
                    case_id,
                    safe_filename,
                    str(dest_path),
                    file_hash,
                    file_size,
                    source_type,
                    now,
                    json.dumps(metadata_dict),
                ),
            )
            # Record audit log
            self._record_audit(
                conn,
                evidence_id=evidence_id,
                case_id=case_id,
                action="ingested",
                actor=actor,
                details={
                    "file_name": safe_filename,
                    "file_hash": file_hash,
                    "file_size_bytes": file_size,
                    "source_type": source_type,
                },
            )
            conn.commit()

        return EvidenceResponse(
            evidence_id=evidence_id,
            case_id=case_id,
            file_name=safe_filename,
            file_hash=file_hash,
            file_size_bytes=file_size,
            source_type=source_type,
            processing_status="pending",
            ingested_at=now,
            metadata=metadata_dict,
        )

    def ingest_local_file(
        self,
        case_id: str,
        source_path: Path | str,
        source_type: str = "general",
        metadata: Optional[dict[str, Any]] = None,
        actor: str = "system",
    ) -> EvidenceResponse:
        """Register a local file on disk as evidence without re-uploading."""
        src = Path(source_path)
        if not src.is_file():
            raise FileNotFoundError(f"Source evidence file not found: {src}")

        evidence_id = str(uuid.uuid4())
        dest_dir = self.storage_root / case_id / evidence_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / src.name

        shutil.copy2(src, dest_path)

        with open(dest_path, "rb") as f:
            file_hash, file_size = self.compute_sha256(f)

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        metadata_dict = metadata or {}

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO evidence (
                    evidence_id, case_id, file_name, file_path, file_hash,
                    file_size_bytes, source_type, processing_status, ingested_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    evidence_id,
                    case_id,
                    src.name,
                    str(dest_path),
                    file_hash,
                    file_size,
                    source_type,
                    now,
                    json.dumps(metadata_dict),
                ),
            )
            self._record_audit(
                conn,
                evidence_id=evidence_id,
                case_id=case_id,
                action="ingested",
                actor=actor,
                details={
                    "file_name": src.name,
                    "file_hash": file_hash,
                    "file_size_bytes": file_size,
                    "source_type": source_type,
                },
            )
            conn.commit()

        return EvidenceResponse(
            evidence_id=evidence_id,
            case_id=case_id,
            file_name=src.name,
            file_hash=file_hash,
            file_size_bytes=file_size,
            source_type=source_type,
            processing_status="pending",
            ingested_at=now,
            metadata=metadata_dict,
        )

    def get_evidence(self, evidence_id: str) -> Optional[EvidenceResponse]:
        """Retrieve evidence metadata by ID."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM evidence WHERE evidence_id = ?", (evidence_id,)).fetchone()
            if not row:
                return None
            return self._row_to_evidence(row)

    def get_evidence_file_path(self, evidence_id: str) -> Optional[Path]:
        """Get the filesystem path of the stored evidence binary."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT file_path FROM evidence WHERE evidence_id = ?", (evidence_id,)).fetchone()
            if not row:
                return None
            p = Path(row["file_path"])
            return p if p.is_file() else None

    def list_evidence(self, case_id: Optional[str] = None) -> EvidenceListResponse:
        """List all evidence, optionally filtered by case."""
        with self._get_connection() as conn:
            if case_id:
                rows = conn.execute(
                    "SELECT * FROM evidence WHERE case_id = ? ORDER BY ingested_at DESC", (case_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM evidence ORDER BY ingested_at DESC"
                ).fetchall()

            items = [self._row_to_evidence(r) for r in rows]
            return EvidenceListResponse(evidence=items, total=len(items))

    def verify_evidence(self, evidence_id: str, actor: str = "system") -> Optional[EvidenceVerifyResponse]:
        """Re-hash the physical evidence file and verify against stored cryptographic fingerprint."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM evidence WHERE evidence_id = ?", (evidence_id,)).fetchone()
            if not row:
                return None

            stored_hash = row["file_hash"]
            file_path = Path(row["file_path"])
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()

            if not file_path.is_file():
                result = EvidenceVerifyResponse(
                    evidence_id=evidence_id,
                    file_name=row["file_name"],
                    stored_hash=stored_hash,
                    computed_hash="file_not_found",
                    integrity="failed",
                    checked_at=now,
                    message="Evidence file is missing from local storage.",
                )
            else:
                with open(file_path, "rb") as f:
                    computed_hash, _ = self.compute_sha256(f)

                if computed_hash == stored_hash:
                    result = EvidenceVerifyResponse(
                        evidence_id=evidence_id,
                        file_name=row["file_name"],
                        stored_hash=stored_hash,
                        computed_hash=computed_hash,
                        integrity="verified",
                        checked_at=now,
                        message="Integrity check passed. SHA-256 fingerprint matches original ingest state.",
                    )
                else:
                    result = EvidenceVerifyResponse(
                        evidence_id=evidence_id,
                        file_name=row["file_name"],
                        stored_hash=stored_hash,
                        computed_hash=computed_hash,
                        integrity="failed",
                        checked_at=now,
                        message="File hash does not match stored value. Evidence has been modified or corrupted.",
                    )

            # Record audit verification attempt
            self._record_audit(
                conn,
                evidence_id=evidence_id,
                case_id=row["case_id"],
                action="verified",
                actor=actor,
                details={
                    "stored_hash": stored_hash,
                    "computed_hash": result.computed_hash,
                    "integrity": result.integrity,
                },
            )
            conn.commit()

            return result

    def delete_evidence(self, evidence_id: str, actor: str = "system") -> bool:
        """Delete evidence metadata, file, and log deletion audit record."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM evidence WHERE evidence_id = ?", (evidence_id,)).fetchone()
            if not row:
                return False

            file_path = Path(row["file_path"])
            if file_path.is_file():
                try:
                    file_path.unlink()
                    if file_path.parent.is_dir() and not any(file_path.parent.iterdir()):
                        file_path.parent.rmdir()
                except Exception as err:
                    logger.warning("Could not delete file %s: %s", file_path, err)

            conn.execute("DELETE FROM evidence WHERE evidence_id = ?", (evidence_id,))
            self._record_audit(
                conn,
                evidence_id=evidence_id,
                case_id=row["case_id"],
                action="deleted",
                actor=actor,
                details={"file_name": row["file_name"]},
            )
            conn.commit()
            return True

    def get_audit_trail(self, evidence_id: str) -> list[EvidenceAuditRecord]:
        """Retrieve complete immutable audit history for an evidence item."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM evidence_audit WHERE evidence_id = ? ORDER BY timestamp ASC",
                (evidence_id,),
            ).fetchall()
            return [
                EvidenceAuditRecord(
                    audit_id=r["audit_id"],
                    evidence_id=r["evidence_id"],
                    case_id=r["case_id"],
                    action=r["action"],
                    actor=r["actor"],
                    timestamp=r["timestamp"],
                    details=json.loads(r["details"]),
                )
                for r in rows
            ]

    def _record_audit(
        self,
        conn: sqlite3.Connection,
        evidence_id: str,
        case_id: str,
        action: str,
        actor: str,
        details: dict[str, Any],
    ) -> None:
        audit_id = str(uuid.uuid4())
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        conn.execute(
            """
            INSERT INTO evidence_audit (audit_id, evidence_id, case_id, action, actor, timestamp, details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (audit_id, evidence_id, case_id, action, actor, now, json.dumps(details)),
        )

    def _row_to_evidence(self, row: sqlite3.Row) -> EvidenceResponse:
        try:
            metadata = json.loads(row["metadata"])
        except Exception:
            metadata = {}

        return EvidenceResponse(
            evidence_id=row["evidence_id"],
            case_id=row["case_id"],
            file_name=row["file_name"],
            file_hash=row["file_hash"],
            file_size_bytes=row["file_size_bytes"],
            source_type=row["source_type"],
            processing_status=row["processing_status"],
            ingested_at=row["ingested_at"],
            metadata=metadata,
        )


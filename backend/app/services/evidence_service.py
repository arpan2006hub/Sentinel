"""Service layer for Evidence Ingestion, Storage, and Cryptographic Integrity Verification."""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import sqlite3
from pathlib import Path
from typing import Any, BinaryIO, Optional

from fastapi import UploadFile  # type: ignore[import-untyped,import-not-found]

from app.config import get_settings
from app.db import append_audit, connect, new_id, utcnow, verify_audit_chain
from app.schemas.evidence import (
    AuditChainVerifyResponse,
    EvidenceAuditRecord,
    EvidenceListResponse,
    EvidenceResponse,
    EvidenceVerifyResponse,
)

logger = logging.getLogger(__name__)


class UploadTooLargeError(ValueError):
    """Raised when an upload exceeds MAX_UPLOAD_SIZE_MB."""


class EvidenceService:
    """Evidence files, SHA-256 hashing, and hash-chained chain-of-custody audit logs."""

    _instance: Optional[EvidenceService] = None

    def __init__(
        self,
        db_path: Optional[str | Path] = None,
        storage_root: Optional[str | Path] = None,
        max_upload_bytes: Optional[int] = None,
    ) -> None:
        settings = get_settings()
        self.storage_root = Path(storage_root) if storage_root else settings.storage_path
        self.storage_root.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(db_path) if db_path else settings.db_path
        self.max_upload_bytes = max_upload_bytes or settings.max_upload_bytes
        with connect(self.db_path):
            pass

    @classmethod
    def get_instance(
        cls,
        db_path: Optional[str | Path] = None,
        storage_root: Optional[str | Path] = None,
    ) -> EvidenceService:
        if cls._instance is None or db_path is not None:
            cls._instance = cls(db_path=db_path, storage_root=storage_root)
        return cls._instance

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

    # ------------------------------------------------------------- ingestion
    def _register(
        self,
        conn: sqlite3.Connection,
        evidence_id: str,
        case_id: str,
        file_name: str,
        dest_path: Path,
        file_hash: str,
        file_size: int,
        source_type: str,
        metadata: dict[str, Any],
        actor: str,
    ) -> EvidenceResponse:
        now = utcnow()
        conn.execute(
            """
            INSERT INTO evidence (evidence_id, case_id, file_name, file_path, file_hash, file_size_bytes,
                                  source_type, processing_status, ingested_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
            (evidence_id, case_id, file_name, str(dest_path), file_hash, file_size, source_type, now,
             json.dumps(metadata)),
        )
        append_audit(conn, evidence_id, case_id, "ingested", actor, {
            "file_name": file_name, "file_hash": file_hash, "file_size_bytes": file_size, "source_type": source_type,
        })
        return EvidenceResponse(
            evidence_id=evidence_id, case_id=case_id, file_name=file_name, file_hash=file_hash,
            file_size_bytes=file_size, source_type=source_type, processing_status="pending",
            ingested_at=now, metadata=metadata,
        )

    async def ingest_upload(
        self,
        case_id: str,
        file: UploadFile,
        source_type: str = "general",
        metadata: Optional[dict[str, Any]] = None,
        actor: str = "investigator",
    ) -> EvidenceResponse:
        """Stream an uploaded file to disk while hashing it."""
        evidence_id = new_id()
        safe_filename = Path(file.filename or "evidence.bin").name or "evidence.bin"
        dest_dir = self.storage_root / case_id / evidence_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / safe_filename

        hasher = hashlib.sha256()
        file_size = 0
        try:
            with open(dest_path, "wb") as out_file:
                while chunk := await file.read(1024 * 1024):
                    file_size += len(chunk)
                    if file_size > self.max_upload_bytes:
                        raise UploadTooLargeError(
                            f"Upload exceeds the {self.max_upload_bytes // (1024 * 1024)} MB limit (MAX_UPLOAD_SIZE_MB)"
                        )
                    hasher.update(chunk)
                    out_file.write(chunk)
        except Exception:
            shutil.rmtree(dest_dir, ignore_errors=True)
            raise

        with connect(self.db_path) as conn:
            return self._register(conn, evidence_id, case_id, safe_filename, dest_path,
                                  f"sha256:{hasher.hexdigest()}", file_size, source_type, metadata or {}, actor)

    def ingest_local_file(
        self,
        case_id: str,
        source_path: Path | str,
        source_type: str = "general",
        metadata: Optional[dict[str, Any]] = None,
        actor: str = "system",
    ) -> EvidenceResponse:
        """Copy a local file into the evidence store and register it."""
        src = Path(source_path)
        if not src.is_file():
            raise FileNotFoundError(f"Source evidence file not found: {src}")
        evidence_id = new_id()
        dest_dir = self.storage_root / case_id / evidence_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / src.name
        shutil.copy2(src, dest_path)
        with open(dest_path, "rb") as f:
            file_hash, file_size = self.compute_sha256(f)
        with connect(self.db_path) as conn:
            return self._register(conn, evidence_id, case_id, src.name, dest_path, file_hash, file_size,
                                  source_type, metadata or {}, actor)

    # ---------------------------------------------------------------- reads
    def get_evidence(self, evidence_id: str) -> Optional[EvidenceResponse]:
        with connect(self.db_path) as conn:
            row = conn.execute("SELECT * FROM evidence WHERE evidence_id = ?", (evidence_id,)).fetchone()
            return self._row_to_evidence(row) if row else None

    def get_evidence_file_path(self, evidence_id: str) -> Optional[Path]:
        with connect(self.db_path) as conn:
            row = conn.execute("SELECT file_path FROM evidence WHERE evidence_id = ?", (evidence_id,)).fetchone()
        if not row:
            return None
        path = Path(row["file_path"])
        return path if path.is_file() else None

    def list_evidence(self, case_id: Optional[str] = None) -> EvidenceListResponse:
        with connect(self.db_path) as conn:
            if case_id:
                rows = conn.execute(
                    "SELECT * FROM evidence WHERE case_id = ? ORDER BY ingested_at DESC", (case_id,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM evidence ORDER BY ingested_at DESC").fetchall()
            items = [self._row_to_evidence(r) for r in rows]
        return EvidenceListResponse(evidence=items, total=len(items))

    def record_access(self, evidence_id: str, actor: str = "investigator", purpose: str = "download") -> None:
        with connect(self.db_path) as conn:
            row = conn.execute("SELECT case_id FROM evidence WHERE evidence_id = ?", (evidence_id,)).fetchone()
            if row:
                append_audit(conn, evidence_id, row["case_id"], "accessed", actor, {"purpose": purpose})

    def set_processing_status(
        self, evidence_id: str, status: str, details: Optional[dict[str, Any]] = None, actor: str = "analysis"
    ) -> None:
        with connect(self.db_path) as conn:
            row = conn.execute("SELECT case_id FROM evidence WHERE evidence_id = ?", (evidence_id,)).fetchone()
            if not row:
                return
            conn.execute("UPDATE evidence SET processing_status = ? WHERE evidence_id = ?", (status, evidence_id))
            if status in {"processed", "skipped", "error"}:
                append_audit(conn, evidence_id, row["case_id"], "analyzed", actor, {"status": status, **(details or {})})

    # ------------------------------------------------------------ integrity
    def verify_evidence(self, evidence_id: str, actor: str = "system") -> Optional[EvidenceVerifyResponse]:
        """Re-hash the stored file and compare to the hash recorded at ingestion."""
        with connect(self.db_path) as conn:
            row = conn.execute("SELECT * FROM evidence WHERE evidence_id = ?", (evidence_id,)).fetchone()
            if not row:
                return None
            stored_hash = row["file_hash"]
            file_path = Path(row["file_path"])
            now = utcnow()
            if not file_path.is_file():
                computed, integrity, message = "file_not_found", "failed", "Evidence file is missing from local storage."
            else:
                with open(file_path, "rb") as f:
                    computed, _ = self.compute_sha256(f)
                if computed == stored_hash:
                    integrity = "verified"
                    message = "Integrity check passed. SHA-256 fingerprint matches original ingest state."
                else:
                    integrity = "failed"
                    message = "File hash does not match stored value. Evidence has been modified or corrupted."
            append_audit(conn, evidence_id, row["case_id"], "verified", actor,
                         {"stored_hash": stored_hash, "computed_hash": computed, "integrity": integrity})
        return EvidenceVerifyResponse(
            evidence_id=evidence_id, file_name=row["file_name"], stored_hash=stored_hash,
            computed_hash=computed, integrity=integrity, checked_at=now, message=message,
        )

    def delete_evidence(self, evidence_id: str, actor: str = "investigator") -> bool:
        """Delete the evidence file and metadata; the audit trail is preserved."""
        with connect(self.db_path) as conn:
            row = conn.execute("SELECT * FROM evidence WHERE evidence_id = ?", (evidence_id,)).fetchone()
            if not row:
                return False
            file_path = Path(row["file_path"])
            if file_path.is_file():
                try:
                    file_path.unlink()
                    if file_path.parent.is_dir() and not any(file_path.parent.iterdir()):
                        file_path.parent.rmdir()
                except OSError as err:
                    logger.warning("Could not delete file %s: %s", file_path, err)
            conn.execute("DELETE FROM evidence WHERE evidence_id = ?", (evidence_id,))
            append_audit(conn, evidence_id, row["case_id"], "deleted", actor, {"file_name": row["file_name"]})
        return True

    # ---------------------------------------------------------------- audit
    def has_audit(self, evidence_id: str) -> bool:
        with connect(self.db_path) as conn:
            return conn.execute(
                "SELECT 1 FROM evidence_audit WHERE evidence_id = ? LIMIT 1", (evidence_id,)
            ).fetchone() is not None

    def get_audit_trail(self, evidence_id: str) -> list[EvidenceAuditRecord]:
        with connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM evidence_audit WHERE evidence_id = ? ORDER BY rowid ASC", (evidence_id,)
            ).fetchall()
        return [
            EvidenceAuditRecord(
                audit_id=r["audit_id"], evidence_id=r["evidence_id"], case_id=r["case_id"], action=r["action"],
                actor=r["actor"], timestamp=r["timestamp"], details=json.loads(r["details"]),
                prev_hash=r["prev_hash"], record_hash=r["record_hash"],
            )
            for r in rows
        ]

    def verify_audit_chain(self, evidence_id: str) -> AuditChainVerifyResponse:
        with connect(self.db_path) as conn:
            result = verify_audit_chain(conn, evidence_id)
        return AuditChainVerifyResponse(evidence_id=evidence_id, **result)

    def _row_to_evidence(self, row: sqlite3.Row) -> EvidenceResponse:
        try:
            metadata = json.loads(row["metadata"])
        except Exception:
            metadata = {}
        return EvidenceResponse(
            evidence_id=row["evidence_id"], case_id=row["case_id"], file_name=row["file_name"],
            file_hash=row["file_hash"], file_size_bytes=row["file_size_bytes"], source_type=row["source_type"],
            processing_status=row["processing_status"], ingested_at=row["ingested_at"], metadata=metadata,
        )

    def _file_path_row(self, evidence_id: str) -> Optional[dict[str, Any]]:
        with connect(self.db_path) as conn:
            row = conn.execute("SELECT * FROM evidence WHERE evidence_id = ?", (evidence_id,)).fetchone()
        return dict(row) if row else None

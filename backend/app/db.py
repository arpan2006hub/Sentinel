"""SQLite persistence helpers shared by all backend services.

SQLite is the current local-first store (single file under ``STORAGE_PATH``).
The schema mirrors docs/architecture/database-schema.md closely enough that a
later move to PostgreSQL only needs to swap this module.

Audit records form a per-evidence **hash chain**: each record stores the hash
of the previous record for the same evidence item plus its own SHA-256 over
its content. Editing or deleting any row breaks the chain, which
``verify_audit_chain`` detects.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

GENESIS_HASH = "0" * 64

SCHEMA = [
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
    """,
    "CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status)",
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
    """,
    "CREATE INDEX IF NOT EXISTS idx_evidence_case ON evidence(case_id)",
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
    """,
    "CREATE INDEX IF NOT EXISTS idx_audit_evidence ON evidence_audit(evidence_id)",
    """
    CREATE TABLE IF NOT EXISTS analysis_runs (
        run_id TEXT PRIMARY KEY,
        case_id TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        started_at TEXT,
        finished_at TEXT,
        options TEXT NOT NULL DEFAULT '{}',
        summary TEXT NOT NULL DEFAULT '{}',
        evidence_results TEXT NOT NULL DEFAULT '[]',
        error TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_runs_case ON analysis_runs(case_id)",
]

# Columns added after the first release; applied with ALTER TABLE if missing.
MIGRATIONS = {
    "evidence_audit": {"prev_hash": "TEXT", "record_hash": "TEXT"},
}

_initialised: set[str] = set()


def utcnow() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


def init_schema(db_path: Path) -> None:
    """Create tables and apply additive migrations (idempotent)."""
    key = str(Path(db_path).resolve())
    if key in _initialised and Path(db_path).exists():
        return
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=30)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        for statement in SCHEMA:
            conn.execute(statement)
        for table, columns in MIGRATIONS.items():
            existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
            for column, col_type in columns.items():
                if column not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        conn.commit()
    finally:
        conn.close()
    _initialised.add(key)


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    """Open a connection, commit on success, roll back on error, always close."""
    init_schema(db_path)
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _record_digest(prev_hash: str, record: dict[str, Any]) -> str:
    payload = json.dumps({"prev_hash": prev_hash, **record}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def append_audit(
    conn: sqlite3.Connection,
    evidence_id: str,
    case_id: str,
    action: str,
    actor: str,
    details: dict[str, Any],
) -> dict[str, Any]:
    """Append a hash-chained audit record for an evidence item.

    Takes the database write lock before reading the chain head, so two
    concurrent appends for the same evidence cannot fork the chain.
    """
    if not conn.in_transaction:
        conn.execute("BEGIN IMMEDIATE")
    last = conn.execute(
        "SELECT record_hash FROM evidence_audit WHERE evidence_id = ? AND record_hash IS NOT NULL "
        "ORDER BY rowid DESC LIMIT 1",
        (evidence_id,),
    ).fetchone()
    prev_hash = last["record_hash"] if last else GENESIS_HASH
    record = {
        "audit_id": new_id(),
        "evidence_id": evidence_id,
        "case_id": case_id,
        "action": action,
        "actor": actor,
        "timestamp": utcnow(),
        "details": json.dumps(details, sort_keys=True, default=str),
    }
    record_hash = _record_digest(prev_hash, record)
    conn.execute(
        """
        INSERT INTO evidence_audit (audit_id, evidence_id, case_id, action, actor, timestamp, details,
                                    prev_hash, record_hash)
        VALUES (:audit_id, :evidence_id, :case_id, :action, :actor, :timestamp, :details, :prev_hash, :record_hash)
        """,
        {**record, "prev_hash": prev_hash, "record_hash": record_hash},
    )
    return {**record, "prev_hash": prev_hash, "record_hash": record_hash}


def verify_audit_chain(conn: sqlite3.Connection, evidence_id: str) -> dict[str, Any]:
    """Recompute the audit hash chain for one evidence item."""
    rows = conn.execute(
        "SELECT * FROM evidence_audit WHERE evidence_id = ? ORDER BY rowid ASC", (evidence_id,)
    ).fetchall()
    expected_prev = GENESIS_HASH
    legacy = 0
    for index, row in enumerate(rows):
        if row["record_hash"] is None:
            legacy += 1  # written before hash chaining existed; cannot be verified
            continue
        record = {k: row[k] for k in ("audit_id", "evidence_id", "case_id", "action", "actor", "timestamp", "details")}
        if row["prev_hash"] != expected_prev:
            return {"valid": False, "records": len(rows), "legacy_unverifiable": legacy, "broken_at_index": index,
                    "broken_audit_id": row["audit_id"], "reason": "previous-hash link mismatch (record removed or reordered)"}
        if _record_digest(row["prev_hash"], record) != row["record_hash"]:
            return {"valid": False, "records": len(rows), "legacy_unverifiable": legacy, "broken_at_index": index,
                    "broken_audit_id": row["audit_id"], "reason": "record content does not match its hash (record edited)"}
        expected_prev = row["record_hash"]
    return {"valid": True, "records": len(rows), "legacy_unverifiable": legacy,
            "broken_at_index": None, "broken_audit_id": None, "reason": None}

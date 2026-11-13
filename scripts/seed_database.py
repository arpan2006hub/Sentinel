#!/usr/bin/env python3
"""seed_database.py — Initialise the Sentinel SQLite database (idempotent).

Creates/migrates all tables in ``$STORAGE_PATH/sentinel.db``. Use
``scripts/demo.py`` to additionally create a populated demo case.

PostgreSQL + Alembic are planned (see docs/decisions/ADR-003-storage.md); the
current local-first build uses SQLite.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in (PROJECT_ROOT, PROJECT_ROOT / "backend"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.config import get_settings  # noqa: E402
from app.db import connect  # noqa: E402


def main() -> None:
    settings = get_settings()
    with connect(settings.db_path) as conn:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    print(f"[seed_database] Database ready: {settings.db_path}")
    print(f"[seed_database] Tables: {', '.join(tables)}")


if __name__ == "__main__":
    main()

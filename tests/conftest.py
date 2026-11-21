"""Shared pytest fixtures.

Every test gets its own temporary STORAGE_PATH / ARTIFACTS_DIR and an empty
TimeSformer cache dir, so tests never touch the developer's evidence store and
never load the 485 MB video model (keeps the suite fast on CPU-only laptops).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for _path in (PROJECT_ROOT, PROJECT_ROOT / "backend"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    storage = tmp_path / "evidence_store"
    artifacts = tmp_path / "artifacts"
    monkeypatch.setenv("STORAGE_PATH", str(storage))
    monkeypatch.setenv("ARTIFACTS_DIR", str(artifacts))
    monkeypatch.setenv("TIMESFORMER_CACHE_DIR", str(tmp_path / "no-weights"))
    monkeypatch.delenv("TIMESFORMER_MODEL_PATH", raising=False)
    monkeypatch.setenv("VIDEO_AUTO_DOWNLOAD", "false")
    from app.services import reset_services

    reset_services()
    yield {"tmp": tmp_path, "storage": storage, "artifacts": artifacts}
    reset_services()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def scenario_dir(tmp_path_factory) -> Path:
    """Synthetic 'Night Copy' scenario generated once per test session (~1 s)."""
    out = tmp_path_factory.mktemp("scenario")
    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "generate_demo_data.py"), "--output", str(out)],
        check=True, capture_output=True,
    )
    return out

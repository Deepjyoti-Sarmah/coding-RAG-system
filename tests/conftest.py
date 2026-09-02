"""Shared fixtures: tmp_db with WAL cleanup, tmp_repo."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_db(tmp_path):
    """Temp SQLite path with automatic WAL/SHM cleanup."""
    db = tmp_path / "index.sqlite"
    yield str(db)
    # Cleanup WAL sidecars that sqlite WAL mode leaves behind
    for suffix in ("", "-wal", "-shm", "-journal"):
        p = Path(str(db) + suffix) if suffix else db
        try:
            if p.exists():
                p.unlink()
        except OSError:
            pass


@pytest.fixture
def tmp_repo(tmp_path):
    """Empty repo directory for indexing tests."""
    repo = tmp_path / "repo"
    repo.mkdir()
    return repo

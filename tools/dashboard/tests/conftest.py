"""Pytest fixtures for dashboard tests."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_project_structure(temp_dir: Path):
    """Create a mock project structure with audiobee_* directories.

    Creates:
    - audiobee_test_hs/ (healthsparq - has config in healthsparq/configs/)
    - audiobee_test_sp/ (sapphire - has config in sapphire/configs/)
    - audiobee_test_standalone/ (standalone - no config anywhere)
    - audiobee_test_marker/ (has .healthsparq marker file)
    - audiobee_test_env/ (has SCRAPER_SITE_TYPE in .env)
    """
    # Create healthsparq config directory
    hs_configs = temp_dir / "healthsparq" / "configs"
    hs_configs.mkdir(parents=True)
    (hs_configs / "test_hs.yaml").write_text("# healthsparq config\n")
    (hs_configs / "_base.yaml").write_text("# base config - should be ignored\n")

    # Create sapphire config directory
    sp_configs = temp_dir / "sapphire" / "configs"
    sp_configs.mkdir(parents=True)
    (sp_configs / "test_sp.yaml").write_text("# sapphire config\n")

    # Create project directories
    projects = {
        "audiobee_test_hs": {"platform": "healthsparq"},
        "audiobee_test_sp": {"platform": "sapphire"},
        "audiobee_test_standalone": {"platform": "standalone"},
        "audiobee_test_marker": {"platform": "healthsparq", "marker": True},
        "audiobee_test_env": {"platform": "sapphire", "env": True},
    }

    for name, config in projects.items():
        project_dir = temp_dir / name
        project_dir.mkdir()

        # Add marker file if specified
        if config.get("marker"):
            (project_dir / ".healthsparq").touch()

        # Add .env file if specified
        if config.get("env"):
            (project_dir / ".env").write_text("SCRAPER_SITE_TYPE=sapphire\n")

    yield temp_dir


@pytest.fixture
def mock_run_structure(temp_dir: Path):
    """Create mock project with run folders and databases.

    Structure:
    - audiobee_test/
      - 20260110/
        - providers.db (SQLiteFS - has 'files' table)
        - cache.db (not SQLiteFS - no 'files' table)
      - 20260111/
        - data.db (SQLiteFS)
      - not_a_date/
        - ignored.db
    """
    project_dir = temp_dir / "audiobee_test"
    project_dir.mkdir()

    # Create run folders
    run1 = project_dir / "20260110"
    run1.mkdir()

    run2 = project_dir / "20260111"
    run2.mkdir()

    # Create non-date folder (should be ignored)
    other = project_dir / "not_a_date"
    other.mkdir()

    # Create SQLiteFS database (has 'files' table)
    sqlitefs_db = run1 / "providers.db"
    conn = sqlite3.connect(str(sqlitefs_db))
    conn.execute("""
        CREATE TABLE files (
            path TEXT PRIMARY KEY,
            content BLOB,
            metadata TEXT
        )
    """)
    conn.execute("INSERT INTO files (path, content) VALUES ('/', '')")
    conn.commit()
    conn.close()

    # Create non-SQLiteFS database (no 'files' table)
    regular_db = run1 / "cache.db"
    conn = sqlite3.connect(str(regular_db))
    conn.execute("CREATE TABLE cache (key TEXT, value TEXT)")
    conn.commit()
    conn.close()

    # Create another SQLiteFS database in second run
    sqlitefs_db2 = run2 / "data.db"
    conn = sqlite3.connect(str(sqlitefs_db2))
    conn.execute("""
        CREATE TABLE files (
            path TEXT PRIMARY KEY,
            content BLOB,
            metadata TEXT
        )
    """)
    conn.commit()
    conn.close()

    # Create database in non-date folder (should be ignored)
    ignored_db = other / "ignored.db"
    conn = sqlite3.connect(str(ignored_db))
    conn.execute("CREATE TABLE files (path TEXT)")
    conn.commit()
    conn.close()

    yield temp_dir


@pytest.fixture
def mock_state_db(temp_dir: Path):
    """Create a mock state database for active runs."""
    import time

    state_db = temp_dir / "state.db"
    conn = sqlite3.connect(str(state_db))
    conn.execute("""
        CREATE TABLE runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT NOT NULL,
            pid INTEGER NOT NULL,
            phase TEXT DEFAULT '',
            progress REAL DEFAULT 0.0,
            records INTEGER DEFAULT 0,
            started_at REAL NOT NULL,
            heartbeat REAL NOT NULL,
            completed INTEGER DEFAULT 0
        )
    """)

    # Add some test runs
    now = time.time()
    conn.execute(
        "INSERT INTO runs (project, pid, phase, progress, records, started_at, heartbeat) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("audiobee_test1", 1234, "search", 0.5, 100, now - 300, now),
    )
    conn.execute(
        "INSERT INTO runs (project, pid, phase, progress, records, started_at, heartbeat) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("audiobee_test2", 5678, "details", 0.25, 50, now - 600, now),
    )
    # Add stale run (old heartbeat)
    conn.execute(
        "INSERT INTO runs (project, pid, phase, progress, records, started_at, heartbeat) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("audiobee_stale", 9999, "search", 0.1, 10, now - 3600, now - 3600),
    )

    conn.commit()
    conn.close()

    yield state_db

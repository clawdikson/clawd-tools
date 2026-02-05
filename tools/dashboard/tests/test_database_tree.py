"""Tests for database tree widget and SQLiteFS validation.

Tests:
1. SQLiteFS database validation (has 'files' table)
2. Run folder detection (20* pattern)
3. Database discovery in run folders
4. Lazy loading behavior
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tools.dashboard.widgets.database_tree import DatabaseTree


class TestSQLiteFSValidation:
    """Test SQLiteFS database validation."""

    def test_is_sqlitefs_db_valid(self, mock_run_structure: Path):
        """Test validation of valid SQLiteFS database."""
        tree = DatabaseTree()

        sqlitefs_db = mock_run_structure / "audiobee_test" / "20260110" / "providers.db"
        assert tree._is_sqlitefs_db(sqlitefs_db) is True

    def test_is_sqlitefs_db_invalid(self, mock_run_structure: Path):
        """Test validation rejects non-SQLiteFS database."""
        tree = DatabaseTree()

        regular_db = mock_run_structure / "audiobee_test" / "20260110" / "cache.db"
        assert tree._is_sqlitefs_db(regular_db) is False

    def test_is_sqlitefs_db_nonexistent(self, temp_dir: Path):
        """Test validation handles non-existent database."""
        tree = DatabaseTree()

        nonexistent = temp_dir / "nonexistent.db"
        assert tree._is_sqlitefs_db(nonexistent) is False

    def test_is_sqlitefs_db_caching(self, mock_run_structure: Path):
        """Test that validation results are cached (instance-level)."""
        tree = DatabaseTree()

        sqlitefs_db = mock_run_structure / "audiobee_test" / "20260110" / "providers.db"

        # First call should add to cache
        result1 = tree._is_sqlitefs_db(sqlitefs_db)

        # Verify it's in cache (instance-level)
        assert str(sqlitefs_db) in tree._db_cache

        # Second call should use cache
        result2 = tree._is_sqlitefs_db(sqlitefs_db)

        assert result1 == result2 == True

    def test_is_sqlitefs_db_corrupted(self, temp_dir: Path):
        """Test validation handles corrupted database."""
        tree = DatabaseTree()

        # Create corrupted database file
        corrupted_db = temp_dir / "corrupted.db"
        corrupted_db.write_bytes(b"not a valid sqlite database")

        assert tree._is_sqlitefs_db(corrupted_db) is False


class TestDatabaseDiscovery:
    """Test database discovery in run folders."""

    def test_get_sqlitefs_databases(self, mock_run_structure: Path):
        """Test discovery finds only SQLiteFS databases."""
        tree = DatabaseTree()

        run_folder = mock_run_structure / "audiobee_test" / "20260110"
        databases = tree._get_sqlitefs_databases(run_folder)

        # Should find providers.db but not cache.db
        db_names = [db.name for db in databases]
        assert "providers.db" in db_names
        assert "cache.db" not in db_names

    def test_get_sqlitefs_databases_empty_folder(self, temp_dir: Path):
        """Test discovery handles empty folder."""
        tree = DatabaseTree()

        empty_folder = temp_dir / "empty"
        empty_folder.mkdir()

        databases = tree._get_sqlitefs_databases(empty_folder)
        assert databases == []

    def test_get_sqlitefs_databases_sorted(self, mock_run_structure: Path):
        """Test databases are returned sorted by name."""
        tree = DatabaseTree()

        # Create additional databases in a run folder
        run_folder = mock_run_structure / "audiobee_test" / "20260110"

        for name in ["zebra.db", "alpha.db"]:
            db_path = run_folder / name
            conn = sqlite3.connect(str(db_path))
            conn.execute("CREATE TABLE files (path TEXT)")
            conn.commit()
            conn.close()

        databases = tree._get_sqlitefs_databases(run_folder)
        db_names = [db.name for db in databases]

        assert db_names == sorted(db_names)


class TestRunFolderDetection:
    """Test run folder detection."""

    def test_date_pattern_valid(self):
        """Test DATE_PATTERN matches valid dates."""
        valid_dates = [
            "20260101",
            "20251231",
            "20200101",
            "20999999",  # Pattern doesn't validate actual date
        ]

        for date in valid_dates:
            assert DatabaseTree.DATE_PATTERN.match(date), f"Should match {date}"

    def test_date_pattern_invalid(self):
        """Test DATE_PATTERN rejects invalid formats."""
        invalid = [
            "19990101",  # Starts with 19
            "21000101",  # Starts with 21
            "2026010",   # Too short
            "202601011", # Too long
            "2026-01-01",  # Has dashes
            "abcdefgh",  # Not numbers
            "20260101a",  # Has letter
        ]

        for value in invalid:
            assert not DatabaseTree.DATE_PATTERN.match(value), f"Should not match {value}"


class TestSharedState:
    """Test SharedState service for active runs."""

    def test_shared_state_init_creates_db(self, temp_dir: Path):
        """Test SharedState creates database on init."""
        from tools.dashboard.services.state import SharedState

        db_path = temp_dir / "state.db"
        state = SharedState(db_path=db_path)

        assert db_path.exists()

    def test_get_active_runs(self, mock_state_db: Path):
        """Test get_active_runs returns recent runs."""
        from tools.dashboard.services.state import SharedState

        state = SharedState(db_path=mock_state_db)
        runs = state.get_active_runs(timeout_seconds=30)

        # Should find 2 active runs (not the stale one)
        assert len(runs) == 2

        projects = [r["project"] for r in runs]
        assert "audiobee_test1" in projects
        assert "audiobee_test2" in projects
        assert "audiobee_stale" not in projects  # Too old

    def test_get_active_runs_with_stale(self, mock_state_db: Path):
        """Test get_active_runs includes stale runs with high timeout."""
        from tools.dashboard.services.state import SharedState

        state = SharedState(db_path=mock_state_db)
        # Use very high timeout to include stale run
        runs = state.get_active_runs(timeout_seconds=7200)

        assert len(runs) == 3
        projects = [r["project"] for r in runs]
        assert "audiobee_stale" in projects

    def test_register_run(self, temp_dir: Path):
        """Test registering a new run."""
        from tools.dashboard.services.state import SharedState

        db_path = temp_dir / "state.db"
        state = SharedState(db_path=db_path)

        run_id = state.register_run("audiobee_new", pid=1234)

        assert run_id is not None
        assert run_id > 0

        # Verify run exists
        run = state.get_run(run_id)
        assert run is not None
        assert run["project"] == "audiobee_new"
        assert run["pid"] == 1234

    def test_update_progress(self, temp_dir: Path):
        """Test updating run progress."""
        from tools.dashboard.services.state import SharedState

        db_path = temp_dir / "state.db"
        state = SharedState(db_path=db_path)

        run_id = state.register_run("audiobee_test", pid=1234)
        state.update_progress(run_id, "details", 0.75, 500)

        run = state.get_run(run_id)
        assert run["phase"] == "details"
        assert run["progress"] == 0.75
        assert run["records"] == 500

    def test_complete_run(self, temp_dir: Path):
        """Test marking run as complete removes from active."""
        from tools.dashboard.services.state import SharedState

        db_path = temp_dir / "state.db"
        state = SharedState(db_path=db_path)

        run_id = state.register_run("audiobee_test", pid=1234)

        # Should be active
        runs = state.get_active_runs()
        assert len(runs) == 1

        # Complete it
        state.complete_run(run_id)

        # Should not be in active runs
        runs = state.get_active_runs()
        assert len(runs) == 0

    def test_cleanup_stale(self, mock_state_db: Path):
        """Test cleanup removes stale runs."""
        from tools.dashboard.services.state import SharedState

        state = SharedState(db_path=mock_state_db)

        # Cleanup runs older than 1 hour
        removed = state.cleanup_stale(timeout_seconds=3600)

        # Should remove the stale run
        assert removed >= 1

        # Verify it's gone - use high timeout to see all that remain
        runs = state.get_active_runs(timeout_seconds=7200)
        projects = [r["project"] for r in runs]
        assert "audiobee_stale" not in projects


class TestValidationService:
    """Test validation service."""

    def test_validator_init(self):
        """Test Validator initializes correctly."""
        from tools.dashboard.services.validator import Validator

        validator = Validator()
        assert validator is not None

    def test_validate_env_missing_env(self, temp_dir: Path):
        """Test validation detects missing .env file."""
        from tools.dashboard.services.validator import Validator

        project_dir = temp_dir / "audiobee_test"
        project_dir.mkdir()

        validator = Validator()
        results = validator.validate_env(project_dir)

        # Should have error/warning for missing .env
        has_env_issue = any(
            "env" in r.category.lower() or ".env" in r.message.lower()
            for r in results
        )
        assert has_env_issue

    def test_validate_env_with_env(self, temp_dir: Path):
        """Test validation passes with .env file."""
        from tools.dashboard.services.validator import Validator

        project_dir = temp_dir / "audiobee_test"
        project_dir.mkdir()
        (project_dir / ".env").write_text("SCRAPER_PROJECT_NAME=test\n")

        validator = Validator()
        results = validator.validate_env(project_dir)

        # Should pass env check
        env_results = [r for r in results if "env" in r.category.lower()]
        for r in env_results:
            assert r.status != "error"

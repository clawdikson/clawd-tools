"""Tests for SQLiteFS Explorer TUI components.

Tests follow TDD approach - written before implementation.
"""

import sqlite3
import tempfile
from pathlib import Path

import pytest

# Tests for LazyTreeBackend
class TestLazyTreeBackend:
    """Tests for the LazyTreeBackend class."""

    @pytest.fixture
    def sample_db(self, tmp_path: Path) -> Path:
        """Create a sample SQLiteFS database for testing."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY,
                data BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Insert test data with hierarchical paths
        test_files = [
            ("20251230/raw/search/IL_60601.json", b'{"results": []}'),
            ("20251230/raw/search/IL_60602.json", b'{"results": []}'),
            ("20251230/raw/details/1234567890.json", b'{"npi": "1234567890"}'),
            ("20251230/raw/details/0987654321.json", b'{"npi": "0987654321"}'),
            ("20251230/processed/providers.jsonl", b'{"npi": "1234567890"}\n'),
            ("config.json", b'{"version": "1.0"}'),
        ]
        conn.executemany(
            "INSERT INTO files (path, data) VALUES (?, ?)",
            test_files
        )
        conn.commit()
        conn.close()
        return db_path

    def test_get_readonly_conn_creates_new_connection(self, sample_db: Path):
        """Test that _get_readonly_conn creates a new read-only connection."""
        from tools.sqlitefs_explorer.backend import LazyTreeBackend

        backend = LazyTreeBackend(str(sample_db))
        conn = backend._get_readonly_conn()

        # Should be a valid connection
        assert conn is not None
        # Should be able to read
        cursor = conn.execute("SELECT COUNT(*) FROM files")
        count = cursor.fetchone()[0]
        assert count == 6
        conn.close()

    def test_iter_children_root_level(self, sample_db: Path):
        """Test getting children at root level returns top-level entries."""
        from tools.sqlitefs_explorer.backend import LazyTreeBackend

        backend = LazyTreeBackend(str(sample_db))
        children = list(backend._iter_children(""))

        # Should have 2 top-level entries: "20251230" dir and "config.json" file
        assert len(children) == 2
        # Directories should come first, then files
        assert "20251230" in children
        assert "config.json" in children

    def test_iter_children_first_level_dir(self, sample_db: Path):
        """Test getting children of a first-level directory."""
        from tools.sqlitefs_explorer.backend import LazyTreeBackend

        backend = LazyTreeBackend(str(sample_db))
        children = list(backend._iter_children("20251230"))

        # Should have "raw" and "processed" directories
        assert len(children) == 2
        assert "20251230/raw" in children
        assert "20251230/processed" in children

    def test_iter_children_second_level_dir(self, sample_db: Path):
        """Test getting children of a second-level directory."""
        from tools.sqlitefs_explorer.backend import LazyTreeBackend

        backend = LazyTreeBackend(str(sample_db))
        children = list(backend._iter_children("20251230/raw"))

        # Should have "search" and "details" directories
        assert len(children) == 2
        assert "20251230/raw/search" in children
        assert "20251230/raw/details" in children

    def test_iter_children_leaf_level(self, sample_db: Path):
        """Test getting children of a directory with only files."""
        from tools.sqlitefs_explorer.backend import LazyTreeBackend

        backend = LazyTreeBackend(str(sample_db))
        children = list(backend._iter_children("20251230/raw/search"))

        # Should have 2 JSON files
        assert len(children) == 2
        assert "20251230/raw/search/IL_60601.json" in children
        assert "20251230/raw/search/IL_60602.json" in children

    def test_get_child_count(self, sample_db: Path):
        """Test getting child count for a directory."""
        from tools.sqlitefs_explorer.backend import LazyTreeBackend

        backend = LazyTreeBackend(str(sample_db))

        # Root level: all 6 files under ""
        assert backend.get_child_count("") == 6

        # 20251230: 5 files total
        assert backend.get_child_count("20251230") == 5

        # raw: 4 files
        assert backend.get_child_count("20251230/raw") == 4

        # search: 2 files
        assert backend.get_child_count("20251230/raw/search") == 2

    def test_is_directory_true(self, sample_db: Path):
        """Test is_directory returns True for directories."""
        from tools.sqlitefs_explorer.backend import LazyTreeBackend

        backend = LazyTreeBackend(str(sample_db))

        assert backend.is_directory("20251230") is True
        assert backend.is_directory("20251230/raw") is True
        assert backend.is_directory("20251230/raw/search") is True

    def test_is_directory_false_for_files(self, sample_db: Path):
        """Test is_directory returns False for leaf files."""
        from tools.sqlitefs_explorer.backend import LazyTreeBackend

        backend = LazyTreeBackend(str(sample_db))

        assert backend.is_directory("config.json") is False
        assert backend.is_directory("20251230/raw/search/IL_60601.json") is False

    def test_get_file_data(self, sample_db: Path):
        """Test reading file data from database."""
        from tools.sqlitefs_explorer.backend import LazyTreeBackend

        backend = LazyTreeBackend(str(sample_db))
        data = backend.get_file_data("config.json")

        assert data is not None
        assert data == b'{"version": "1.0"}'

    def test_get_file_data_missing(self, sample_db: Path):
        """Test reading non-existent file returns None."""
        from tools.sqlitefs_explorer.backend import LazyTreeBackend

        backend = LazyTreeBackend(str(sample_db))
        data = backend.get_file_data("nonexistent.json")

        assert data is None

    def test_get_db_stats(self, sample_db: Path):
        """Test getting database statistics."""
        from tools.sqlitefs_explorer.backend import LazyTreeBackend

        backend = LazyTreeBackend(str(sample_db))
        stats = backend.get_db_stats()

        assert stats["file_count"] == 6
        assert stats["db_size"] > 0
        assert "db_path" in stats

    def test_caching(self, sample_db: Path):
        """Test that children are cached after first load."""
        from tools.sqlitefs_explorer.backend import LazyTreeBackend

        backend = LazyTreeBackend(str(sample_db))

        # First call should populate cache
        children1 = backend.get_children_sync("20251230/raw")
        assert "20251230" not in backend._children_cache
        assert "20251230/raw" in backend._children_cache

        # Second call should return cached result
        children2 = backend.get_children_sync("20251230/raw")
        assert children1 == children2


class TestJSONViewer:
    """Tests for the JSONViewer widget."""

    def test_render_empty_state(self):
        """Test rendering with no data shows placeholder."""
        from tools.sqlitefs_explorer.widgets.viewer import JSONViewer

        viewer = JSONViewer()
        # Widget should render placeholder when no data
        assert viewer._data is None

    def test_render_with_dict(self):
        """Test rendering a dictionary."""
        from tools.sqlitefs_explorer.widgets.viewer import JSONViewer

        viewer = JSONViewer()
        viewer.set_data({"npi": "1234567890", "name": "Dr. Smith"})

        assert viewer._data == {"npi": "1234567890", "name": "Dr. Smith"}

    def test_render_with_list(self):
        """Test rendering a list."""
        from tools.sqlitefs_explorer.widgets.viewer import JSONViewer

        viewer = JSONViewer()
        viewer.set_data([{"id": 1}, {"id": 2}])

        assert viewer._data == [{"id": 1}, {"id": 2}]

    def test_truncation_warning_for_large_json(self):
        """Test that large JSON gets truncation flag."""
        from tools.sqlitefs_explorer.widgets.viewer import JSONViewer

        viewer = JSONViewer()
        # Create a large JSON object
        large_data = {"data": "x" * (11 * 1024 * 1024)}  # > 10MB
        viewer.set_data(large_data, warn_truncation=True)

        assert viewer._truncation_warning is True


class TestAppIntegration:
    """Integration tests for the main app."""

    @pytest.fixture
    def sample_db(self, tmp_path: Path) -> Path:
        """Create a sample SQLiteFS database for testing."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY,
                data BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        test_files = [
            ("20251230/raw/search/IL_60601.json", b'{"results": [{"npi": "123"}]}'),
            ("config.json", b'{"version": "1.0"}'),
        ]
        conn.executemany(
            "INSERT INTO files (path, data) VALUES (?, ?)",
            test_files
        )
        conn.commit()
        conn.close()
        return db_path

    @pytest.mark.asyncio
    async def test_app_creation(self, sample_db: Path):
        """Test that the app can be created with a valid database."""
        from tools.sqlitefs_explorer.app import SQLiteFSExplorerApp

        app = SQLiteFSExplorerApp(db_path=str(sample_db))
        assert app.db_path == str(sample_db)

    @pytest.mark.asyncio
    async def test_app_rejects_invalid_db(self, tmp_path: Path):
        """Test that the app raises error for invalid database path."""
        from tools.sqlitefs_explorer.app import SQLiteFSExplorerApp

        nonexistent = tmp_path / "nonexistent.db"
        with pytest.raises(FileNotFoundError):
            SQLiteFSExplorerApp(db_path=str(nonexistent))


class TestCLI:
    """Tests for the CLI entry point."""

    def test_cli_help(self):
        """Test that CLI help works."""
        from typer.testing import CliRunner
        from tools.sqlitefs_explorer.__main__ import app

        runner = CliRunner()
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "SQLiteFS Explorer" in result.output or "db_path" in result.output

    def test_cli_requires_db_path(self):
        """Test that CLI requires a database path argument."""
        from typer.testing import CliRunner
        from tools.sqlitefs_explorer.__main__ import app

        runner = CliRunner()
        result = runner.invoke(app, [])
        # Should fail without required argument
        assert result.exit_code != 0

    def test_cli_validates_db_exists(self, tmp_path: Path):
        """Test that CLI validates database file exists."""
        from typer.testing import CliRunner
        from tools.sqlitefs_explorer.__main__ import app

        runner = CliRunner()
        nonexistent = tmp_path / "nonexistent.db"
        result = runner.invoke(app, [str(nonexistent)])
        # Should fail with appropriate error
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "does not exist" in result.output.lower()

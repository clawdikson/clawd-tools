"""Tests for backend module - LazyTreeBackend metadata methods."""

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from tools.sqlitefs_explorer.backend import LazyTreeBackend


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database with test data."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE files (
            path TEXT PRIMARY KEY,
            data BLOB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insert test files
    test_files = [
        ("20251230/raw/search/IL_60601.json", b'{"zip": "60601"}', "2025-12-30 10:00:00", "2025-12-30 10:30:00"),
        ("20251230/raw/search/IL_60602.json", b'{"zip": "60602"}', "2025-12-30 11:00:00", "2025-12-30 11:30:00"),
        ("20251230/raw/details/npi_123.json", b'{"npi": "123", "name": "Dr. Smith"}', "2025-12-30 12:00:00", "2025-12-30 12:30:00"),
        ("20251230/processed/providers.json", b'[{"npi": "123"}]', "2025-12-31 09:00:00", "2025-12-31 09:30:00"),
        ("20260101/raw/search/IL_60601.json", b'{"zip": "60601", "v": 2}', "2026-01-01 08:00:00", "2026-01-01 08:30:00"),
    ]

    for path, data, created, updated in test_files:
        conn.execute(
            "INSERT INTO files (path, data, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (path, data, created, updated)
        )

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


class TestGetFileMetadata:
    """Tests for LazyTreeBackend.get_file_metadata method."""

    def test_get_file_metadata_exists(self, temp_db):
        """Test getting metadata for existing file."""
        backend = LazyTreeBackend(temp_db)
        result = backend.get_file_metadata("20251230/raw/search/IL_60601.json")

        assert result is not None
        assert result["path"] == "20251230/raw/search/IL_60601.json"
        assert result["size"] > 0
        assert result["created_at"] == "2025-12-30 10:00:00"
        assert result["updated_at"] == "2025-12-30 10:30:00"

    def test_get_file_metadata_not_found(self, temp_db):
        """Test getting metadata for non-existent file."""
        backend = LazyTreeBackend(temp_db)
        result = backend.get_file_metadata("nonexistent/file.json")

        assert result is None

    def test_get_file_metadata_size_correct(self, temp_db):
        """Test that size is correctly calculated from blob length."""
        backend = LazyTreeBackend(temp_db)
        result = backend.get_file_metadata("20251230/raw/search/IL_60601.json")

        expected_size = len(b'{"zip": "60601"}')
        assert result["size"] == expected_size


class TestGetChildrenWithMetadata:
    """Tests for LazyTreeBackend.get_children_with_metadata method."""

    def test_get_children_root(self, temp_db):
        """Test getting root children with metadata."""
        backend = LazyTreeBackend(temp_db)
        children = backend.get_children_with_metadata("")

        assert len(children) == 2  # 20251230 and 20260101
        paths = [c["path"] for c in children]
        assert "20251230" in paths
        assert "20260101" in paths

    def test_get_children_directory(self, temp_db):
        """Test getting children of a directory."""
        backend = LazyTreeBackend(temp_db)
        children = backend.get_children_with_metadata("20251230/raw")

        assert len(children) == 2  # search and details
        names = [c["name"] for c in children]
        assert "search" in names
        assert "details" in names

    def test_get_children_aggregated_size(self, temp_db):
        """Test that directory size is aggregated from children."""
        backend = LazyTreeBackend(temp_db)
        children = backend.get_children_with_metadata("20251230/raw")

        # Find the search directory
        search_dir = next(c for c in children if c["name"] == "search")
        assert search_dir["is_dir"] is True
        assert search_dir["file_count"] == 2  # Two files in search dir
        assert search_dir["size"] > 0

    def test_get_children_file_count(self, temp_db):
        """Test that file_count is correctly aggregated."""
        backend = LazyTreeBackend(temp_db)
        children = backend.get_children_with_metadata("")

        # 20251230 has 4 files total
        dir_20251230 = next(c for c in children if c["name"] == "20251230")
        assert dir_20251230["file_count"] == 4

        # 20260101 has 1 file
        dir_20260101 = next(c for c in children if c["name"] == "20260101")
        assert dir_20260101["file_count"] == 1

    def test_get_children_newest_update(self, temp_db):
        """Test that newest_update is correct."""
        backend = LazyTreeBackend(temp_db)
        children = backend.get_children_with_metadata("")

        # 20251230's newest update is from processed/providers.json
        dir_20251230 = next(c for c in children if c["name"] == "20251230")
        assert "2025-12-31" in dir_20251230["newest_update"]

    def test_get_children_oldest_create(self, temp_db):
        """Test that oldest_create is correct."""
        backend = LazyTreeBackend(temp_db)
        children = backend.get_children_with_metadata("")

        # 20251230's oldest creation is from search/IL_60601.json
        dir_20251230 = next(c for c in children if c["name"] == "20251230")
        assert "2025-12-30 10:00:00" == dir_20251230["oldest_create"]

    def test_get_children_sorted_dirs_first(self, temp_db):
        """Test that directories are sorted before files."""
        backend = LazyTreeBackend(temp_db)
        children = backend.get_children_with_metadata("20251230/raw/search")

        # Should be files only, sorted by name
        for child in children:
            assert child["is_dir"] is False
        names = [c["name"] for c in children]
        assert names == sorted(names, key=str.lower)

    def test_get_children_empty_prefix(self, temp_db):
        """Test getting children with empty string prefix (root)."""
        backend = LazyTreeBackend(temp_db)
        children = backend.get_children_with_metadata("")

        assert len(children) > 0
        for child in children:
            assert child["is_dir"] is True  # Root only has directories


class TestIterAllPaths:
    """Tests for LazyTreeBackend.iter_all_paths method."""

    def test_iter_all_paths(self, temp_db):
        """Test iterating all paths."""
        backend = LazyTreeBackend(temp_db)
        paths = list(backend.iter_all_paths())

        assert len(paths) == 5
        assert "20251230/raw/search/IL_60601.json" in paths
        assert "20251230/processed/providers.json" in paths

    def test_iter_all_paths_sorted(self, temp_db):
        """Test that paths are sorted."""
        backend = LazyTreeBackend(temp_db)
        paths = list(backend.iter_all_paths())

        assert paths == sorted(paths)


class TestIterAllFiles:
    """Tests for LazyTreeBackend.iter_all_files method."""

    def test_iter_all_files(self, temp_db):
        """Test iterating all files with content."""
        backend = LazyTreeBackend(temp_db)
        files = list(backend.iter_all_files())

        assert len(files) == 5
        paths = [f[0] for f in files]
        assert "20251230/raw/search/IL_60601.json" in paths

    def test_iter_all_files_content(self, temp_db):
        """Test that file content is correctly returned."""
        backend = LazyTreeBackend(temp_db)
        files = dict(backend.iter_all_files())

        content = files["20251230/raw/search/IL_60601.json"]
        assert isinstance(content, bytes)
        parsed = json.loads(content)
        assert parsed["zip"] == "60601"

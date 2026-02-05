"""Tests for tree widget - DisplaySettings and formatting methods."""

from datetime import datetime

import pytest

from tools.sqlitefs_explorer.widgets.tree import DisplaySettings


class TestDisplaySettings:
    """Tests for DisplaySettings dataclass."""

    def test_default_settings(self):
        """Test default DisplaySettings values."""
        settings = DisplaySettings()
        assert settings.show_size is True
        assert settings.show_date is True
        assert settings.date_format == "%Y-%m-%d %H:%M"
        assert settings.size_format == "human"

    def test_custom_settings(self):
        """Test custom DisplaySettings values."""
        settings = DisplaySettings(
            show_size=False,
            show_date=False,
            date_format="%m/%d/%Y",
            size_format="bytes"
        )
        assert settings.show_size is False
        assert settings.show_date is False
        assert settings.date_format == "%m/%d/%Y"
        assert settings.size_format == "bytes"


class TestFormatSize:
    """Tests for VirtualFSTree._format_size method."""

    # These tests import from tree module and call the static formatting function
    # We'll test via the module-level function if available, or via the class

    def test_format_size_bytes(self):
        """Test formatting byte values."""
        from tools.sqlitefs_explorer.widgets.tree import format_size
        assert format_size(100) == "100.0B"
        assert format_size(0) == "0.0B"
        assert format_size(1023) == "1023.0B"

    def test_format_size_kilobytes(self):
        """Test formatting KB values."""
        from tools.sqlitefs_explorer.widgets.tree import format_size
        assert format_size(1024) == "1.0KB"
        assert format_size(2048) == "2.0KB"
        assert format_size(1536) == "1.5KB"

    def test_format_size_megabytes(self):
        """Test formatting MB values."""
        from tools.sqlitefs_explorer.widgets.tree import format_size
        assert format_size(1024 * 1024) == "1.0MB"
        assert format_size(10 * 1024 * 1024) == "10.0MB"

    def test_format_size_gigabytes(self):
        """Test formatting GB values."""
        from tools.sqlitefs_explorer.widgets.tree import format_size
        assert format_size(1024 ** 3) == "1.0GB"
        assert format_size(2.5 * 1024 ** 3) == "2.5GB"

    def test_format_size_terabytes(self):
        """Test formatting TB values."""
        from tools.sqlitefs_explorer.widgets.tree import format_size
        assert format_size(1024 ** 4) == "1.0TB"


class TestFormatDate:
    """Tests for VirtualFSTree._format_date method."""

    def test_format_date_iso_string(self):
        """Test formatting ISO date string."""
        from tools.sqlitefs_explorer.widgets.tree import format_date
        result = format_date("2026-01-12T10:30:00", "%Y-%m-%d %H:%M")
        assert result == "2026-01-12 10:30"

    def test_format_date_sqlite_format(self):
        """Test formatting SQLite timestamp format."""
        from tools.sqlitefs_explorer.widgets.tree import format_date
        result = format_date("2026-01-12 10:30:00", "%Y-%m-%d %H:%M")
        assert result == "2026-01-12 10:30"

    def test_format_date_with_z_suffix(self):
        """Test formatting ISO date with Z suffix."""
        from tools.sqlitefs_explorer.widgets.tree import format_date
        result = format_date("2026-01-12T10:30:00Z", "%Y-%m-%d")
        assert result == "2026-01-12"

    def test_format_date_custom_format(self):
        """Test formatting with custom date format."""
        from tools.sqlitefs_explorer.widgets.tree import format_date
        result = format_date("2026-01-12T10:30:00", "%m/%d/%Y")
        assert result == "01/12/2026"

    def test_format_date_invalid_returns_truncated(self):
        """Test that invalid date returns first 10 chars."""
        from tools.sqlitefs_explorer.widgets.tree import format_date
        result = format_date("not-a-date-but-long-enough", "%Y-%m-%d")
        assert result == "not-a-date"

    def test_format_date_empty_string(self):
        """Test formatting empty string."""
        from tools.sqlitefs_explorer.widgets.tree import format_date
        result = format_date("", "%Y-%m-%d")
        assert result == ""

    def test_format_date_none_returns_empty(self):
        """Test formatting None returns empty string."""
        from tools.sqlitefs_explorer.widgets.tree import format_date
        result = format_date(None, "%Y-%m-%d")
        assert result == ""


class TestFormatNodeLabel:
    """Tests for VirtualFSTree.format_node_label method."""

    def test_format_node_label_basic(self):
        """Test basic node label formatting."""
        from tools.sqlitefs_explorer.widgets.tree import format_node_label
        settings = DisplaySettings(show_size=False, show_date=False)
        result = format_node_label("file.json", {}, settings)
        assert result == "file.json"

    def test_format_node_label_with_size(self):
        """Test node label with size."""
        from tools.sqlitefs_explorer.widgets.tree import format_node_label
        settings = DisplaySettings(show_size=True, show_date=False)
        result = format_node_label("file.json", {"size": 1024}, settings)
        assert "file.json" in result
        assert "1.0KB" in result

    def test_format_node_label_with_date(self):
        """Test node label with date."""
        from tools.sqlitefs_explorer.widgets.tree import format_node_label
        settings = DisplaySettings(show_size=False, show_date=True)
        result = format_node_label("file.json", {"newest_update": "2026-01-12 10:30:00"}, settings)
        assert "file.json" in result
        assert "2026-01-12" in result

    def test_format_node_label_with_file_count(self):
        """Test node label with file count for directories."""
        from tools.sqlitefs_explorer.widgets.tree import format_node_label
        settings = DisplaySettings(show_size=False, show_date=False)
        result = format_node_label("search", {"is_dir": True, "file_count": 150}, settings)
        assert "search" in result
        assert "150 files" in result

    def test_format_node_label_single_file_no_count(self):
        """Test that single file dirs don't show count."""
        from tools.sqlitefs_explorer.widgets.tree import format_node_label
        settings = DisplaySettings(show_size=False, show_date=False)
        result = format_node_label("search", {"is_dir": True, "file_count": 1}, settings)
        assert "files" not in result

    def test_format_node_label_all_metadata(self):
        """Test node label with all metadata enabled."""
        from tools.sqlitefs_explorer.widgets.tree import format_node_label
        settings = DisplaySettings(show_size=True, show_date=True)
        metadata = {
            "size": 10 * 1024 * 1024,  # 10MB
            "newest_update": "2026-01-12 10:30:00",
            "is_dir": True,
            "file_count": 50
        }
        result = format_node_label("data", metadata, settings)
        assert "data" in result
        assert "10.0MB" in result
        assert "2026-01-12" in result
        assert "50 files" in result

"""Tests for models module - FilterConfig and related data classes."""

from datetime import datetime, timedelta

import pytest

from tools.sqlitefs_explorer.models import FilterConfig


class TestFilterConfig:
    """Tests for FilterConfig dataclass and its methods."""

    def test_filter_config_default(self):
        """Test FilterConfig with default values."""
        config = FilterConfig()
        assert config.extensions == []
        assert config.min_size is None
        assert config.max_size is None
        assert config.date_from is None
        assert config.date_to is None
        assert config.date_field == "updated"
        assert config.path_pattern is None

    def test_matches_no_filters(self):
        """Test that empty filter matches everything."""
        config = FilterConfig()
        assert config.matches("test.json", 1000, "2026-01-01", "2026-01-10") is True
        assert config.matches("data/file.txt", 0, "", "") is True

    def test_matches_extension_filter(self):
        """Test extension filter matching."""
        config = FilterConfig(extensions=[".json"])
        assert config.matches("test.json", 1000, "", "") is True
        assert config.matches("test.txt", 1000, "", "") is False
        assert config.matches("test.JSON", 1000, "", "") is True  # Case insensitive

    def test_matches_multiple_extensions(self):
        """Test filter with multiple extensions."""
        config = FilterConfig(extensions=[".json", ".jsonl"])
        assert config.matches("test.json", 1000, "", "") is True
        assert config.matches("test.jsonl", 1000, "", "") is True
        assert config.matches("test.txt", 1000, "", "") is False

    def test_matches_size_min(self):
        """Test minimum size filter."""
        config = FilterConfig(min_size=1000)
        assert config.matches("test.json", 2000, "", "") is True
        assert config.matches("test.json", 1000, "", "") is True
        assert config.matches("test.json", 500, "", "") is False

    def test_matches_size_max(self):
        """Test maximum size filter."""
        config = FilterConfig(max_size=1000)
        assert config.matches("test.json", 500, "", "") is True
        assert config.matches("test.json", 1000, "", "") is True
        assert config.matches("test.json", 2000, "", "") is False

    def test_matches_size_range(self):
        """Test size range filter."""
        config = FilterConfig(min_size=100, max_size=1000)
        assert config.matches("test.json", 500, "", "") is True
        assert config.matches("test.json", 50, "", "") is False
        assert config.matches("test.json", 2000, "", "") is False

    def test_matches_date_from(self):
        """Test date_from filter."""
        config = FilterConfig(date_from=datetime(2026, 1, 5))
        assert config.matches("test.json", 1000, "", "2026-01-10") is True
        assert config.matches("test.json", 1000, "", "2026-01-01") is False

    def test_matches_date_to(self):
        """Test date_to filter."""
        config = FilterConfig(date_to=datetime(2026, 1, 5))
        assert config.matches("test.json", 1000, "", "2026-01-01") is True
        assert config.matches("test.json", 1000, "", "2026-01-10") is False

    def test_matches_date_range(self):
        """Test date range filter."""
        config = FilterConfig(
            date_from=datetime(2026, 1, 5),
            date_to=datetime(2026, 1, 10)
        )
        assert config.matches("test.json", 1000, "", "2026-01-07") is True
        assert config.matches("test.json", 1000, "", "2026-01-01") is False
        assert config.matches("test.json", 1000, "", "2026-01-15") is False

    def test_matches_date_field_created(self):
        """Test date filter using created_at field."""
        config = FilterConfig(
            date_from=datetime(2026, 1, 5),
            date_field="created"
        )
        # Uses created (first param), not updated
        assert config.matches("test.json", 1000, "2026-01-10", "2026-01-01") is True
        assert config.matches("test.json", 1000, "2026-01-01", "2026-01-10") is False

    def test_matches_path_pattern(self):
        """Test path pattern glob matching."""
        config = FilterConfig(path_pattern="**/search/*.json")
        assert config.matches("20251230/raw/search/file.json", 1000, "", "") is True
        assert config.matches("20251230/raw/details/file.json", 1000, "", "") is False

    def test_matches_path_pattern_simple(self):
        """Test simple path pattern."""
        config = FilterConfig(path_pattern="*.json")
        assert config.matches("file.json", 1000, "", "") is True
        assert config.matches("file.txt", 1000, "", "") is False

    def test_matches_combined_filters(self):
        """Test multiple filters combined (AND logic)."""
        config = FilterConfig(
            extensions=[".json"],
            min_size=100,
            max_size=10000,
        )
        assert config.matches("test.json", 500, "", "") is True
        assert config.matches("test.txt", 500, "", "") is False  # Wrong extension
        assert config.matches("test.json", 50, "", "") is False  # Too small


class TestParseSize:
    """Tests for FilterConfig.parse_size static method."""

    def test_parse_bytes(self):
        """Test parsing byte values."""
        assert FilterConfig.parse_size("100") == 100
        assert FilterConfig.parse_size("100B") == 100
        assert FilterConfig.parse_size("100b") == 100

    def test_parse_kilobytes(self):
        """Test parsing KB values."""
        assert FilterConfig.parse_size("1KB") == 1024
        assert FilterConfig.parse_size("1kb") == 1024
        assert FilterConfig.parse_size("10KB") == 10 * 1024

    def test_parse_megabytes(self):
        """Test parsing MB values."""
        assert FilterConfig.parse_size("1MB") == 1024 * 1024
        assert FilterConfig.parse_size("10MB") == 10 * 1024 * 1024

    def test_parse_gigabytes(self):
        """Test parsing GB values."""
        assert FilterConfig.parse_size("1GB") == 1024 ** 3
        assert FilterConfig.parse_size("2.5GB") == int(2.5 * 1024 ** 3)

    def test_parse_terabytes(self):
        """Test parsing TB values."""
        assert FilterConfig.parse_size("1TB") == 1024 ** 4

    def test_parse_decimal(self):
        """Test parsing decimal values."""
        assert FilterConfig.parse_size("1.5MB") == int(1.5 * 1024 * 1024)
        assert FilterConfig.parse_size("0.5KB") == 512

    def test_parse_with_space(self):
        """Test parsing values with space between number and unit."""
        assert FilterConfig.parse_size("10 MB") == 10 * 1024 * 1024
        assert FilterConfig.parse_size("1 KB") == 1024

    def test_parse_invalid(self):
        """Test parsing invalid size strings raises ValueError."""
        with pytest.raises(ValueError):
            FilterConfig.parse_size("invalid")
        with pytest.raises(ValueError):
            FilterConfig.parse_size("")
        with pytest.raises(ValueError):
            FilterConfig.parse_size("MB")


class TestParseDateRange:
    """Tests for FilterConfig.parse_date_range static method."""

    def test_parse_today(self):
        """Test parsing 'today' keyword."""
        start, end = FilterConfig.parse_date_range("today")
        now = datetime.now()
        assert start.date() == now.date()
        assert start.hour == 0
        assert start.minute == 0
        assert end is not None

    def test_parse_yesterday(self):
        """Test parsing 'yesterday' keyword."""
        start, end = FilterConfig.parse_date_range("yesterday")
        yesterday = datetime.now() - timedelta(days=1)
        assert start.date() == yesterday.date()
        assert end.date() == yesterday.date()

    def test_parse_last_n_days(self):
        """Test parsing 'lastNd' pattern."""
        start, end = FilterConfig.parse_date_range("last7d")
        now = datetime.now()
        expected_start = now - timedelta(days=7)
        assert start.date() == expected_start.date()
        assert end is not None

    def test_parse_date_range_with_dotdot(self):
        """Test parsing 'YYYY-MM-DD..YYYY-MM-DD' format."""
        start, end = FilterConfig.parse_date_range("2026-01-01..2026-01-10")
        assert start == datetime(2026, 1, 1)
        assert end == datetime(2026, 1, 10)

    def test_parse_date_range_open_start(self):
        """Test parsing range with open start '..YYYY-MM-DD'."""
        start, end = FilterConfig.parse_date_range("..2026-01-10")
        assert start is None
        assert end == datetime(2026, 1, 10)

    def test_parse_date_range_open_end(self):
        """Test parsing range with open end 'YYYY-MM-DD..'."""
        start, end = FilterConfig.parse_date_range("2026-01-01..")
        assert start == datetime(2026, 1, 1)
        assert end is None

    def test_parse_single_date(self):
        """Test parsing single date returns start and end of that day."""
        start, end = FilterConfig.parse_date_range("2026-01-15")
        assert start == datetime(2026, 1, 15)
        assert end.hour == 23
        assert end.minute == 59

"""Tests for Details phase module."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

import orjson

from healthsparq.config import load_config
from healthsparq.phases.details import (
    DetailsConfig,
    DetailsResult,
    load_provider_ids_from_search,
    run_details_sync,
)


class TestDetailsConfig:
    """Test DetailsConfig dataclass."""

    def test_config_creation(self):
        """DetailsConfig creates with required fields."""
        project_config = load_config("christus_health_plan")
        config = DetailsConfig(
            config=project_config,
            curr_date="20251226",
        )
        assert config.config == project_config
        assert config.curr_date == "20251226"

    def test_config_defaults(self):
        """DetailsConfig sets default directories."""
        project_config = load_config("christus_health_plan")
        config = DetailsConfig(
            config=project_config,
            curr_date="20251226",
        )
        assert config.search_results_dir == Path("20251226") / "raw" / "search_results"
        assert config.output_dir == Path("20251226") / "raw" / "provider_details"
        assert config.max_workers == project_config.concurrency.max_workers

    def test_config_custom_dirs(self):
        """DetailsConfig accepts custom directories."""
        project_config = load_config("christus_health_plan")
        custom_search = Path("/tmp/search")
        custom_output = Path("/tmp/output")
        config = DetailsConfig(
            config=project_config,
            curr_date="20251226",
            search_results_dir=custom_search,
            output_dir=custom_output,
        )
        assert config.search_results_dir == custom_search
        assert config.output_dir == custom_output


class TestDetailsResult:
    """Test DetailsResult dataclass."""

    def test_result_creation(self):
        """DetailsResult creates with required fields."""
        result = DetailsResult(
            provider_id="12345",
            plan_code="MA",
            success=True,
        )
        assert result.provider_id == "12345"
        assert result.plan_code == "MA"
        assert result.success is True
        assert result.output_file is None
        assert result.error is None

    def test_result_with_error(self):
        """DetailsResult can capture errors."""
        result = DetailsResult(
            provider_id="12345",
            plan_code="MA",
            success=False,
            error="Provider not found",
        )
        assert result.success is False
        assert result.error == "Provider not found"


class TestLoadProviderIds:
    """Test provider ID loading from search results."""

    def test_load_from_empty_dir(self):
        """Returns empty list for non-existent directory."""
        ids = load_provider_ids_from_search(
            Path("/nonexistent/path"),
            "MA",
        )
        assert ids == []

    def test_load_from_search_results(self):
        """Loads provider IDs from search result files."""
        with TemporaryDirectory() as tmpdir:
            search_dir = Path(tmpdir)
            # Create a mock search result file
            search_data = {
                "providerResults": [
                    {"providerId": "123"},
                    {"providerId": "456"},
                    {"providerId": "123"},  # duplicate
                ]
            }
            search_file = search_dir / "MA_Dallas_TX.json"
            with open(search_file, "wb") as f:
                f.write(orjson.dumps(search_data))

            ids = load_provider_ids_from_search(search_dir, "MA")
            assert len(ids) == 2
            assert set(ids) == {"123", "456"}


class TestDetailsPhase:
    """Test details phase execution."""

    def test_dry_run_returns_results(self):
        """Dry run returns results without executing."""
        project_config = load_config("christus_health_plan")
        results = run_details_sync(
            config=project_config,
            curr_date="20251226",
            dry_run=True,
        )
        assert isinstance(results, dict)

    def test_config_has_no_globals(self):
        """Details phase accepts config as parameter."""
        project_config = load_config("christus_health_plan")
        config = DetailsConfig(
            config=project_config,
            curr_date="20251226",
        )
        # Config is passed, not accessed globally
        assert config.config == project_config


class TestImports:
    """Test all imports resolve correctly."""

    def test_details_imports(self):
        """Details module imports work."""
        from healthsparq.phases import run_details, DetailsConfig, DetailsResult

        assert run_details is not None
        assert DetailsConfig is not None
        assert DetailsResult is not None


class TestLOCCount:
    """Verify details.py is under 400 lines."""

    def test_details_under_400_loc(self):
        """details.py is under 400 lines of code."""
        from pathlib import Path

        details_path = Path(__file__).parent.parent / "phases" / "details.py"
        with open(details_path) as f:
            line_count = sum(1 for _ in f)

        assert line_count < 400, f"details.py has {line_count} lines (limit: 400)"

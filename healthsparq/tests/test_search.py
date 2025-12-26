"""Tests for Search phase module."""

import pytest
from pathlib import Path

from healthsparq.config import load_config
from healthsparq.phases.search import (
    SearchConfig,
    SearchResult,
    CountySearchResult,
    get_file_name,
    get_location_string,
)


class TestSearchConfig:
    """Test SearchConfig dataclass."""

    def test_config_creation(self):
        """SearchConfig creates with required fields."""
        project_config = load_config("christus_health_plan")
        config = SearchConfig(
            config=project_config,
            curr_date="20251226",
        )
        assert config.config == project_config
        assert config.curr_date == "20251226"

    def test_config_defaults(self):
        """SearchConfig sets default output_dir."""
        project_config = load_config("christus_health_plan")
        config = SearchConfig(
            config=project_config,
            curr_date="20251226",
        )
        assert config.output_dir == Path("20251226") / "raw" / "search_results"
        assert config.max_workers == project_config.concurrency.max_workers
        assert config.dry_run is False
        assert config.zip_data_path == Path("uszips.xlsx")

    def test_config_custom_output_dir(self):
        """SearchConfig accepts custom output_dir."""
        project_config = load_config("christus_health_plan")
        custom_dir = Path("/tmp/custom_output")
        config = SearchConfig(
            config=project_config,
            curr_date="20251226",
            output_dir=custom_dir,
        )
        assert config.output_dir == custom_dir

    def test_config_dry_run(self):
        """SearchConfig accepts dry_run flag."""
        project_config = load_config("christus_health_plan")
        config = SearchConfig(
            config=project_config,
            curr_date="20251226",
            dry_run=True,
        )
        assert config.dry_run is True


class TestSearchResult:
    """Test SearchResult dataclass."""

    def test_result_creation(self):
        """SearchResult creates with required fields."""
        result = SearchResult(
            location="Dallas County, TX",
            plan_code="MA",
            provider_count=10,
            total_results=100,
        )
        assert result.location == "Dallas County, TX"
        assert result.plan_code == "MA"
        assert result.provider_count == 10
        assert result.total_results == 100
        assert result.output_file is None
        assert result.error is None
        assert result.filters_used == []
        assert result.drilling_required is False

    def test_result_with_error(self):
        """SearchResult can capture errors."""
        result = SearchResult(
            location="Invalid",
            plan_code="MA",
            provider_count=0,
            total_results=0,
            error="API error",
        )
        assert result.error == "API error"

    def test_result_with_filters(self):
        """SearchResult tracks filters used."""
        result = SearchResult(
            location="Dallas County, TX",
            plan_code="MA",
            provider_count=50,
            total_results=150,
            filters_used=["PROVIDER_TYPE:PHYSC", "GENDER_V2:F"],
            drilling_required=True,
        )
        assert result.filters_used == ["PROVIDER_TYPE:PHYSC", "GENDER_V2:F"]
        assert result.drilling_required is True


class TestCountySearchResult:
    """Test CountySearchResult dataclass."""

    def test_county_result_creation(self):
        """CountySearchResult creates with required fields."""
        result = CountySearchResult(
            state="TX",
            county="Dallas",
            plan_code="MA",
            total_providers_found=150,
            searches_performed=5,
            filters_drilled=2,
            zip_codes_searched=0,
        )
        assert result.state == "TX"
        assert result.county == "Dallas"
        assert result.plan_code == "MA"
        assert result.total_providers_found == 150
        assert result.searches_performed == 5
        assert result.filters_drilled == 2
        assert result.zip_codes_searched == 0
        assert result.errors == []

    def test_county_result_with_errors(self):
        """CountySearchResult tracks errors."""
        result = CountySearchResult(
            state="TX",
            county="Dallas",
            plan_code="MA",
            total_providers_found=100,
            searches_performed=3,
            filters_drilled=1,
            zip_codes_searched=10,
            errors=["API timeout on ZIP 75201", "Rate limit on ZIP 75202"],
        )
        assert len(result.errors) == 2
        assert "API timeout" in result.errors[0]


class TestHelperFunctions:
    """Test helper functions."""

    def test_get_file_name_basic(self):
        """get_file_name generates correct format."""
        name = get_file_name(
            state="TX",
            county="Dallas",
            filters=[],
            page=1,
            sort="NAME_ASC",
        )
        assert name == "TX-Dallas_County-all-1-NAME_ASC.json"

    def test_get_file_name_with_filters(self):
        """get_file_name includes filters."""
        name = get_file_name(
            state="TX",
            county="Dallas",
            filters=["PROVIDER_TYPE:PHYSC"],
            page=1,
            sort="NAME_ASC",
        )
        assert name == "TX-Dallas_County-PROVIDER_TYPE_PHYSC-1-NAME_ASC.json"

    def test_get_file_name_with_zip(self):
        """get_file_name includes ZIP code."""
        name = get_file_name(
            state="TX",
            county="Dallas",
            filters=[],
            page=1,
            sort="NAME_ASC",
            zip_code="75201",
        )
        assert "75201" in name

    def test_get_location_string_regular(self):
        """get_location_string uses County for most states."""
        location = get_location_string(state="TX", county="Dallas")
        assert location == "Dallas County, TX"

    def test_get_location_string_louisiana(self):
        """get_location_string uses Parish for Louisiana."""
        location = get_location_string(state="LA", county="Orleans")
        assert location == "Orleans Parish, LA"


class TestImports:
    """Test all imports resolve correctly."""

    def test_search_imports(self):
        """Search module imports work."""
        from healthsparq.phases import run_search, SearchConfig
        from healthsparq.phases.search import (
            SearchResult,
            CountySearchResult,
            fetch_search_results,
            fetch_filter_results,
            process_county,
            run_search_for_plan,
        )

        assert run_search is not None
        assert SearchConfig is not None
        assert SearchResult is not None
        assert CountySearchResult is not None


class TestLOCCount:
    """Verify search.py is under expected lines."""

    def test_search_under_700_loc(self):
        """search.py is under 700 lines of code.

        Note: This module handles complex adaptive pagination,
        specialty drilling, and ZIP fallback - 628 lines is acceptable.
        """
        from pathlib import Path

        search_path = Path(__file__).parent.parent / "phases" / "search.py"
        with open(search_path) as f:
            line_count = sum(1 for _ in f)

        assert line_count < 700, f"search.py has {line_count} lines (limit: 700)"

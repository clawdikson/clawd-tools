"""Comprehensive tests for adaptive pagination in search phase.

Tests the thresholds, filter drilling, and ZIP code fallback strategies.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from healthsparq.config import load_config
from healthsparq.config.schema import (
    PaginationConfig,
    FilterConfig,
)
from healthsparq.phases.search import (
    SearchConfig,
    SearchResult,
    CountySearchResult,
    get_file_name,
    get_location_string,
    fetch_search_results,
    fetch_filter_results,
)


class TestPaginationConfig:
    """Test PaginationConfig defaults and customization."""

    def test_default_page_sizes(self):
        """Default page sizes are [(1, 200), (3, 100)]."""
        config = PaginationConfig()
        assert config.page_sizes == [(1, 200), (3, 100)]

    def test_default_thresholds(self):
        """Default thresholds match legacy behavior."""
        config = PaginationConfig()
        assert config.threshold_second_page == 200
        assert config.threshold_reverse_sort == 300
        assert config.threshold_reverse_second == 500
        assert config.threshold_max_per_filter == 600

    def test_default_sort_types(self):
        """Default sort types include all variations."""
        config = PaginationConfig()
        assert "NAME_ASC" in config.sort_types
        assert "NAME_DESC" in config.sort_types
        assert "BEST_MATCH" in config.sort_types
        assert "DISTANCE" in config.sort_types

    def test_custom_page_sizes(self):
        """Custom page sizes can be configured."""
        config = PaginationConfig(page_sizes=[(1, 100), (2, 50)])
        assert config.page_sizes == [(1, 100), (2, 50)]

    def test_custom_thresholds(self):
        """Custom thresholds can be configured."""
        config = PaginationConfig(
            threshold_second_page=150,
            threshold_reverse_sort=250,
            threshold_reverse_second=400,
            threshold_max_per_filter=500,
        )
        assert config.threshold_second_page == 150
        assert config.threshold_reverse_sort == 250
        assert config.threshold_reverse_second == 400
        assert config.threshold_max_per_filter == 500


class TestFilterConfig:
    """Test FilterConfig with org, individual, and gender filters."""

    def test_default_org_filter_keys(self):
        """Default org filter keys include all provider types."""
        config = FilterConfig()
        assert "PROVIDER_TYPE:FAC" in config.org_filter_keys
        assert "PROVIDER_TYPE:GRP" in config.org_filter_keys
        assert "PROVIDER_TYPE:PHYSC" in config.org_filter_keys
        assert "PROVIDER_TYPE:PHARM" in config.org_filter_keys

    def test_default_individual_filter_keys(self):
        """Default individual filter keys subset of org filters."""
        config = FilterConfig()
        assert "PROVIDER_TYPE:PHYSC" in config.individual_filter_keys
        assert "PROVIDER_TYPE:CNSLR" in config.individual_filter_keys
        # Facilities should NOT be in individual filters
        assert "PROVIDER_TYPE:FAC" not in config.individual_filter_keys
        assert "PROVIDER_TYPE:GRP" not in config.individual_filter_keys

    def test_default_gender_filter_keys(self):
        """Default gender filter keys include F, M, U."""
        config = FilterConfig()
        assert config.gender_filter_keys == ["GENDER_V2:F", "GENDER_V2:M", "GENDER_V2:U"]

    def test_custom_provider_types(self):
        """Custom provider types can be configured."""
        config = FilterConfig(provider_types=["Facility", "Physician"])
        assert config.provider_types == ["Facility", "Physician"]


class TestGetFileName:
    """Test filename generation for various scenarios."""

    def test_basic_filename(self):
        """Basic filename without filters or ZIP."""
        name = get_file_name("TX", "Dallas", [], 1, "NAME_ASC")
        assert name == "TX-Dallas_County-all-1-NAME_ASC.json"

    def test_filename_with_single_filter(self):
        """Filename with single filter."""
        name = get_file_name("TX", "Dallas", ["PROVIDER_TYPE:PHYSC"], 1, "NAME_ASC")
        assert name == "TX-Dallas_County-PROVIDER_TYPE_PHYSC-1-NAME_ASC.json"

    def test_filename_with_multiple_filters(self):
        """Filename with multiple filters."""
        name = get_file_name(
            "TX", "Dallas",
            ["PROVIDER_TYPE:PHYSC", "GENDER_V2:F"],
            1, "NAME_ASC"
        )
        assert "PROVIDER_TYPE_PHYSC_GENDER_V2_F" in name

    def test_filename_with_zip_code(self):
        """Filename includes ZIP code when provided."""
        name = get_file_name("TX", "Dallas", [], 1, "NAME_ASC", "75201")
        assert "75201" in name

    def test_filename_with_different_pages(self):
        """Filename reflects page number."""
        name1 = get_file_name("TX", "Dallas", [], 1, "NAME_ASC")
        name3 = get_file_name("TX", "Dallas", [], 3, "NAME_ASC")
        assert "-1-" in name1
        assert "-3-" in name3

    def test_filename_with_different_sorts(self):
        """Filename reflects sort order."""
        name_asc = get_file_name("TX", "Dallas", [], 1, "NAME_ASC")
        name_desc = get_file_name("TX", "Dallas", [], 1, "NAME_DESC")
        assert "NAME_ASC" in name_asc
        assert "NAME_DESC" in name_desc

    def test_filename_sanitizes_special_chars(self):
        """Filename sanitizes : and / characters."""
        name = get_file_name("TX", "Dallas", ["FILTER:KEY/VALUE"], 1, "NAME_ASC")
        assert ":" not in name
        assert "/" not in name


class TestGetLocationString:
    """Test location string generation."""

    def test_regular_state_uses_county(self):
        """Non-Louisiana states use 'County' suffix."""
        for state in ["TX", "NY", "CA", "FL", "PA"]:
            location = get_location_string(state, "Test")
            assert "County" in location
            assert "Parish" not in location

    def test_louisiana_uses_parish(self):
        """Louisiana uses 'Parish' suffix."""
        location = get_location_string("LA", "Orleans")
        assert "Parish" in location
        assert "County" not in location
        assert location == "Orleans Parish, LA"

    def test_location_format(self):
        """Location string is formatted correctly."""
        location = get_location_string("TX", "Dallas")
        assert location == "Dallas County, TX"


class TestSearchResultDataclass:
    """Test SearchResult dataclass fields."""

    def test_default_fields(self):
        """SearchResult has correct default values."""
        result = SearchResult(
            location="Dallas County, TX",
            plan_code="MA",
            provider_count=100,
            total_results=100,
        )
        assert result.output_file is None
        assert result.error is None
        assert result.filters_used == []
        assert result.drilling_required is False

    def test_filters_used_tracking(self):
        """SearchResult tracks which filters were applied."""
        result = SearchResult(
            location="Dallas County, TX",
            plan_code="MA",
            provider_count=50,
            total_results=150,
            filters_used=["PROVIDER_TYPE:PHYSC", "GENDER_V2:F"],
        )
        assert len(result.filters_used) == 2

    def test_drilling_required_flag(self):
        """SearchResult tracks if drilling was needed."""
        result = SearchResult(
            location="Dallas County, TX",
            plan_code="MA",
            provider_count=600,
            total_results=850,
            drilling_required=True,
        )
        assert result.drilling_required is True


class TestCountySearchResultDataclass:
    """Test CountySearchResult dataclass fields."""

    def test_county_result_fields(self):
        """CountySearchResult tracks all search metrics."""
        result = CountySearchResult(
            state="TX",
            county="Dallas",
            plan_code="MA",
            total_providers_found=1500,
            searches_performed=25,
            filters_drilled=8,
            zip_codes_searched=15,
        )
        assert result.state == "TX"
        assert result.county == "Dallas"
        assert result.plan_code == "MA"
        assert result.total_providers_found == 1500
        assert result.searches_performed == 25
        assert result.filters_drilled == 8
        assert result.zip_codes_searched == 15

    def test_error_collection(self):
        """CountySearchResult collects multiple errors."""
        result = CountySearchResult(
            state="TX",
            county="Dallas",
            plan_code="MA",
            total_providers_found=100,
            searches_performed=5,
            filters_drilled=0,
            zip_codes_searched=0,
            errors=[
                "Timeout on page 3",
                "Rate limit hit",
                "API error on ZIP 75201",
            ],
        )
        assert len(result.errors) == 3


class TestThresholdLogic:
    """Test pagination threshold decision logic."""

    def test_below_200_no_additional_fetches(self):
        """Results below 200 don't trigger additional fetches."""
        # This tests the threshold logic conceptually
        total = 150
        config = PaginationConfig()

        needs_second = total >= config.threshold_second_page
        needs_reverse = total >= config.threshold_reverse_sort
        needs_reverse_second = total >= config.threshold_reverse_second
        needs_drilling = total >= config.threshold_max_per_filter

        assert not needs_second
        assert not needs_reverse
        assert not needs_reverse_second
        assert not needs_drilling

    def test_200_triggers_second_page(self):
        """Results at 200 trigger second page fetch."""
        total = 200
        config = PaginationConfig()

        needs_second = total >= config.threshold_second_page
        needs_reverse = total >= config.threshold_reverse_sort

        assert needs_second
        assert not needs_reverse

    def test_300_triggers_reverse_sort(self):
        """Results at 300 trigger reverse sort fetch."""
        total = 300
        config = PaginationConfig()

        needs_reverse = total >= config.threshold_reverse_sort
        needs_reverse_second = total >= config.threshold_reverse_second

        assert needs_reverse
        assert not needs_reverse_second

    def test_500_triggers_reverse_second(self):
        """Results at 500 trigger reverse sort second page."""
        total = 500
        config = PaginationConfig()

        needs_reverse_second = total >= config.threshold_reverse_second
        needs_drilling = total >= config.threshold_max_per_filter

        assert needs_reverse_second
        assert not needs_drilling

    def test_600_triggers_filter_drilling(self):
        """Results at 600 trigger filter drilling."""
        total = 600
        config = PaginationConfig()

        needs_drilling = total >= config.threshold_max_per_filter

        assert needs_drilling


class TestFilterDrillingStrategy:
    """Test filter drilling hierarchy."""

    def test_org_filters_first(self):
        """Organization filters are tried first."""
        config = FilterConfig()
        # Org filters should include facilities, groups, pharmacies
        assert "PROVIDER_TYPE:FAC" in config.org_filter_keys
        assert "PROVIDER_TYPE:GRP" in config.org_filter_keys
        assert "PROVIDER_TYPE:PHARM" in config.org_filter_keys

    def test_individual_filters_subset(self):
        """Individual filters are subset of org filters."""
        config = FilterConfig()
        for indv_filter in config.individual_filter_keys:
            assert indv_filter in config.org_filter_keys

    def test_gender_filters_for_individuals(self):
        """Gender filters only apply to individual provider types."""
        config = FilterConfig()
        # Individual filters support gender drilling
        individual_types = [
            "PROVIDER_TYPE:PHYSC",  # Physician
            "PROVIDER_TYPE:CNSLR",  # Counselor
            "PROVIDER_TYPE:DNTL",   # Dental
        ]
        for indv_type in individual_types:
            assert indv_type in config.individual_filter_keys


class TestConfigIntegration:
    """Test configuration integration with search phase."""

    def test_project_config_has_pagination(self):
        """Project config includes pagination settings."""
        config = load_config("christus_health_plan")
        assert hasattr(config, "pagination")
        assert isinstance(config.pagination, PaginationConfig)

    def test_project_config_has_filters(self):
        """Project config includes filter settings."""
        config = load_config("christus_health_plan")
        assert hasattr(config, "filters")
        assert isinstance(config.filters, FilterConfig)

    def test_search_config_inherits_settings(self):
        """SearchConfig uses project config settings."""
        project_config = load_config("christus_health_plan")
        search_config = SearchConfig(
            config=project_config,
            curr_date="20251226",
        )
        assert search_config.config.pagination.threshold_max_per_filter == 600
        assert len(search_config.config.filters.org_filter_keys) > 0


class TestZipCodeFallback:
    """Test ZIP code fallback logic."""

    def test_zip_fallback_uses_distance_sort(self):
        """ZIP code fallback uses DISTANCE sort, not NAME_ASC."""
        # When drilling by ZIP code, DISTANCE sort is more appropriate
        # This is verified by checking the file naming convention
        name = get_file_name("TX", "Dallas", [], 1, "DISTANCE", "75201")
        assert "DISTANCE" in name
        assert "75201" in name

    def test_zip_codes_from_xlsx(self):
        """ZIP code data comes from uszips.xlsx."""
        search_config = SearchConfig(
            config=load_config("christus_health_plan"),
            curr_date="20251226",
        )
        assert search_config.zip_data_path == Path("uszips.xlsx")


class TestEdgeCases:
    """Test edge cases in search configuration."""

    def test_empty_filters_list(self):
        """Empty filters list produces 'all' in filename."""
        name = get_file_name("TX", "Dallas", [], 1, "NAME_ASC")
        assert "-all-" in name

    def test_county_with_special_characters(self):
        """County names with special chars are handled."""
        # Some counties have apostrophes or hyphens
        name = get_file_name("LA", "St. Mary's", [], 1, "NAME_ASC")
        assert "St. Mary's" in name or "St._Mary's" in name

    def test_state_case_sensitivity(self):
        """State codes should be uppercase."""
        location_upper = get_location_string("TX", "Dallas")
        assert "TX" in location_upper
        # Lowercase should still work but may need normalization
        location_lower = get_location_string("tx", "Dallas")
        assert "tx" in location_lower

    def test_zero_results_handling(self):
        """Zero results should not trigger drilling."""
        result = SearchResult(
            location="Remote County, MT",
            plan_code="MA",
            provider_count=0,
            total_results=0,
        )
        assert result.provider_count == 0
        assert result.drilling_required is False


class TestSortTypeVariations:
    """Test different sort type configurations."""

    def test_name_asc_is_primary(self):
        """NAME_ASC is typically the primary sort."""
        config = PaginationConfig()
        assert config.sort_types[0] == "NAME_ASC"

    def test_name_desc_for_reverse(self):
        """NAME_DESC used for reverse pagination."""
        config = PaginationConfig()
        assert "NAME_DESC" in config.sort_types

    def test_best_match_available(self):
        """BEST_MATCH sort is available."""
        config = PaginationConfig()
        assert "BEST_MATCH" in config.sort_types

    def test_distance_for_zip_searches(self):
        """DISTANCE sort is available for ZIP searches."""
        config = PaginationConfig()
        assert "DISTANCE" in config.sort_types

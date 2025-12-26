"""Tests for HealthSparq configuration system."""

import pytest
from pathlib import Path
from pydantic import ValidationError

from healthsparq.config import load_config, list_projects, HealthSparqProjectConfig
from healthsparq.config.schema import (
    PlanConfig,
    SiteConfig,
    CoverageConfig,
    FilterConfig,
    ConcurrencyConfig,
    OutputConfig,
    ProjectMetadata,
)


class TestPydanticModels:
    """Test Pydantic model validation."""

    def test_plan_config_minimal(self):
        """PlanConfig requires product_code and name."""
        plan = PlanConfig(product_code="MA", name="Medicare Advantage")
        assert plan.product_code == "MA"
        assert plan.name == "Medicare Advantage"
        assert plan.enabled is True
        assert plan.insurer_code is None

    def test_plan_config_with_overrides(self):
        """PlanConfig can override insurer/brand codes."""
        plan = PlanConfig(
            product_code="HIX",
            name="ACA Plan",
            insurer_code="CUSTOM_I",
            brand_code="CUSTOM",
            state="TX",
        )
        assert plan.insurer_code == "CUSTOM_I"
        assert plan.brand_code == "CUSTOM"
        assert plan.state == "TX"

    def test_site_config_validation(self):
        """SiteConfig requires domain, brand_code, insurer_code."""
        site = SiteConfig(
            domain="example.healthsparq.com",
            brand_code="EXAMPLE",
            insurer_code="EXAMPLE_I",
        )
        assert site.api_version == "v4"

    def test_coverage_config_state_validation(self):
        """CoverageConfig validates state codes."""
        coverage = CoverageConfig(states=["TX", "LA", "NM"])
        assert len(coverage.states) == 3

    def test_coverage_config_invalid_state(self):
        """CoverageConfig rejects invalid state codes."""
        with pytest.raises(ValidationError) as exc_info:
            CoverageConfig(states=["XX"])
        assert "Invalid state code" in str(exc_info.value)

    def test_concurrency_config_defaults(self):
        """ConcurrencyConfig has sensible defaults."""
        config = ConcurrencyConfig()
        assert config.max_workers == 100
        assert config.max_browsers == 1
        assert config.retry_attempts == 3

    def test_concurrency_config_range_validation(self):
        """ConcurrencyConfig enforces value ranges."""
        with pytest.raises(ValidationError):
            ConcurrencyConfig(max_workers=0)  # must be >= 1
        with pytest.raises(ValidationError):
            ConcurrencyConfig(max_workers=600)  # must be <= 500
        with pytest.raises(ValidationError):
            ConcurrencyConfig(max_browsers=60)  # must be <= 50


class TestConfigLoader:
    """Test YAML config loading."""

    def test_list_projects(self):
        """list_projects returns available project slugs."""
        projects = list_projects()
        assert isinstance(projects, list)
        assert "christus_health_plan" in projects

    def test_load_christus_config(self):
        """load_config loads and validates christus_health_plan."""
        config = load_config("christus_health_plan")
        assert isinstance(config, HealthSparqProjectConfig)
        assert config.project.slug == "christus_health_plan"
        assert config.project.name == "Christus Health Plan"

    def test_christus_site_config(self):
        """Christus site config matches legacy values."""
        config = load_config("christus_health_plan")
        assert config.site.domain == "christushealthplan.healthsparq.com"
        assert config.site.brand_code == "CHRISTUS"
        assert config.site.insurer_code == "CHRISTUS_I"
        assert config.site.api_version == "v4"

    def test_christus_plans(self):
        """Christus plans match legacy config values."""
        config = load_config("christus_health_plan")
        product_codes = [p.product_code for p in config.plans]
        assert "USFHP" in product_codes
        assert "Networks" in product_codes
        assert "MA" in product_codes
        assert "HIX" in product_codes
        assert len(config.plans) == 4

    def test_christus_coverage(self):
        """Christus coverage states match legacy values."""
        config = load_config("christus_health_plan")
        assert set(config.coverage.states) == {"LA", "NM", "TX"}

    def test_christus_concurrency(self):
        """Christus concurrency matches legacy MAX_WORKERS."""
        config = load_config("christus_health_plan")
        assert config.concurrency.max_workers == 25
        assert config.concurrency.max_browsers == 25

    def test_plan_inherits_site_auth_codes(self):
        """Plans inherit insurer/brand codes from site if not specified."""
        config = load_config("christus_health_plan")
        for plan in config.plans:
            assert plan.insurer_code == "CHRISTUS_I"
            assert plan.brand_code == "CHRISTUS"

    def test_load_nonexistent_project(self):
        """load_config raises FileNotFoundError for missing projects."""
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent_project")


class TestBaseConfigInheritance:
    """Test base config inheritance and merging."""

    def test_filter_defaults_from_base(self):
        """Filters inherit defaults from _base.yaml."""
        config = load_config("christus_health_plan")
        assert "Facility" in config.filters.provider_types
        assert "Physician" in config.filters.provider_types

    def test_output_defaults_from_base(self):
        """Output config inherits from _base.yaml."""
        config = load_config("christus_health_plan")
        assert config.output.raw_subdir == "raw"
        assert config.output.processed_subdir == "processed"

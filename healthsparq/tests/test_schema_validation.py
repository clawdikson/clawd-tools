"""Comprehensive schema validation tests for HealthSparq configuration.

Tests edge cases and boundary conditions for all Pydantic models in schema.py.
"""

import pytest
from pydantic import ValidationError

from healthsparq.config.schema import (
    CoverageConfig,
    PlanConfig,
    SiteConfig,
    ConcurrencyConfig,
    FilterConfig,
    HealthSparqProjectConfig,
    ProjectMetadata,
    OutputConfig,
)


class TestCoverageConfigStateValidation:
    """Test CoverageConfig state validation edge cases."""

    def test_empty_states_list_raises_validation_error(self):
        """Empty states list should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CoverageConfig(states=[])
        
        error = str(exc_info.value)
        assert "min_length" in error.lower() or "at least 1" in error.lower()

    def test_duplicate_states_in_list_is_allowed(self):
        """Duplicate states in list should work (validator doesn't prevent it)."""
        # Pydantic doesn't enforce uniqueness unless we add a custom validator
        config = CoverageConfig(states=["TX", "TX", "LA"])
        assert len(config.states) == 3
        assert config.states == ["TX", "TX", "LA"]

    def test_lowercase_state_codes_raise_validation_error(self):
        """Lowercase state codes should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CoverageConfig(states=["tx", "la"])
        
        assert "Invalid state code: tx" in str(exc_info.value)

    def test_invalid_state_code_zz_raises_error(self):
        """Invalid state code 'ZZ' should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CoverageConfig(states=["ZZ"])
        
        assert "Invalid state code: ZZ" in str(exc_info.value)

    def test_invalid_state_code_uk_raises_error(self):
        """Invalid state code 'UK' should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CoverageConfig(states=["UK"])
        
        assert "Invalid state code: UK" in str(exc_info.value)

    def test_invalid_state_code_xx_raises_error(self):
        """Invalid state code 'XX' should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CoverageConfig(states=["XX"])
        
        assert "Invalid state code: XX" in str(exc_info.value)

    def test_mixed_valid_invalid_states_raises_error(self):
        """Mix of valid and invalid state codes should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CoverageConfig(states=["TX", "ZZ", "LA"])
        
        assert "Invalid state code: ZZ" in str(exc_info.value)

    def test_all_51_valid_states_including_dc(self):
        """All 51 valid state codes including DC should pass validation."""
        all_states = [
            "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL",
            "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
            "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
            "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
            "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
        ]
        
        config = CoverageConfig(states=all_states)
        assert len(config.states) == 51
        assert "DC" in config.states

    def test_dc_is_valid_state_code(self):
        """DC (District of Columbia) should be a valid state code."""
        config = CoverageConfig(states=["DC"])
        assert config.states == ["DC"]

    def test_optional_counties_field(self):
        """Counties field is optional and can be None."""
        config = CoverageConfig(states=["TX"])
        assert config.counties is None

    def test_counties_field_with_data(self):
        """Counties field can contain state-to-county mappings."""
        config = CoverageConfig(
            states=["TX", "LA"],
            counties={
                "TX": ["Harris", "Dallas", "Travis"],
                "LA": ["Orleans", "Jefferson"],
            }
        )
        assert config.counties["TX"] == ["Harris", "Dallas", "Travis"]
        assert config.counties["LA"] == ["Orleans", "Jefferson"]


class TestPlanConfigEdgeCases:
    """Test PlanConfig edge cases and validation."""

    def test_empty_product_code_is_allowed(self):
        """Empty product_code is technically allowed by Pydantic (no min_length constraint)."""
        # Pydantic doesn't reject empty strings for required fields unless we add validation
        plan = PlanConfig(product_code="", name="Test Plan")
        assert plan.product_code == ""
        assert plan.name == "Test Plan"

    def test_empty_name_is_allowed(self):
        """Empty name is technically allowed by Pydantic (no min_length constraint)."""
        # Pydantic doesn't reject empty strings for required fields unless we add validation
        plan = PlanConfig(product_code="MA", name="")
        assert plan.product_code == "MA"
        assert plan.name == ""

    def test_whitespace_only_product_code(self):
        """Whitespace-only product_code is technically allowed by Pydantic."""
        # Pydantic doesn't strip or validate whitespace unless we add a custom validator
        plan = PlanConfig(product_code="   ", name="Test")
        assert plan.product_code == "   "

    def test_whitespace_only_name(self):
        """Whitespace-only name is technically allowed by Pydantic."""
        plan = PlanConfig(product_code="MA", name="   ")
        assert plan.name == "   "

    def test_very_long_product_code(self):
        """Very long product codes should be accepted."""
        long_code = "A" * 1000
        plan = PlanConfig(product_code=long_code, name="Test Plan")
        assert plan.product_code == long_code
        assert len(plan.product_code) == 1000

    def test_very_long_name(self):
        """Very long names should be accepted."""
        long_name = "Medicare Advantage Plan " * 100
        plan = PlanConfig(product_code="MA", name=long_name)
        assert len(plan.name) > 1000

    def test_optional_insurer_code_is_none_by_default(self):
        """insurer_code is optional and defaults to None."""
        plan = PlanConfig(product_code="MA", name="Test")
        assert plan.insurer_code is None

    def test_optional_brand_code_is_none_by_default(self):
        """brand_code is optional and defaults to None."""
        plan = PlanConfig(product_code="MA", name="Test")
        assert plan.brand_code is None

    def test_optional_state_is_none_by_default(self):
        """state is optional and defaults to None."""
        plan = PlanConfig(product_code="MA", name="Test")
        assert plan.state is None

    def test_enabled_defaults_to_true(self):
        """enabled field defaults to True."""
        plan = PlanConfig(product_code="MA", name="Test")
        assert plan.enabled is True

    def test_all_optional_fields_can_be_none(self):
        """All optional fields can be explicitly set to None."""
        plan = PlanConfig(
            product_code="MA",
            name="Test",
            insurer_code=None,
            brand_code=None,
            state=None,
        )
        assert plan.insurer_code is None
        assert plan.brand_code is None
        assert plan.state is None

    def test_enabled_can_be_false(self):
        """enabled field can be set to False."""
        plan = PlanConfig(product_code="MA", name="Test", enabled=False)
        assert plan.enabled is False

    def test_plan_with_all_fields_populated(self):
        """Plan with all fields populated should validate."""
        plan = PlanConfig(
            product_code="HIX",
            name="ACA Marketplace Plan",
            insurer_code="INSURER_I",
            brand_code="BRAND",
            state="TX",
            enabled=True,
        )
        assert plan.product_code == "HIX"
        assert plan.name == "ACA Marketplace Plan"
        assert plan.insurer_code == "INSURER_I"
        assert plan.brand_code == "BRAND"
        assert plan.state == "TX"
        assert plan.enabled is True


class TestSiteConfigValidation:
    """Test SiteConfig validation edge cases."""

    def test_empty_domain_is_allowed(self):
        """Empty domain is technically allowed by Pydantic (no min_length constraint)."""
        # Pydantic doesn't reject empty strings for required fields unless we add validation
        site = SiteConfig(domain="", brand_code="BRAND", insurer_code="INS_I")
        assert site.domain == ""

    def test_empty_brand_code_is_allowed(self):
        """Empty brand_code is technically allowed by Pydantic (no min_length constraint)."""
        # Pydantic doesn't reject empty strings for required fields unless we add validation
        site = SiteConfig(domain="example.healthsparq.com", brand_code="", insurer_code="INS_I")
        assert site.brand_code == ""

    def test_empty_insurer_code_is_allowed(self):
        """Empty insurer_code is technically allowed by Pydantic (no min_length constraint)."""
        # Pydantic doesn't reject empty strings for required fields unless we add validation
        site = SiteConfig(domain="example.healthsparq.com", brand_code="BRAND", insurer_code="")
        assert site.insurer_code == ""

    def test_valid_domain_formats(self):
        """Various valid domain formats should be accepted."""
        domains = [
            "example.healthsparq.com",
            "sub.example.healthsparq.com",
            "example-test.healthsparq.com",
            "localhost",
            "127.0.0.1",
        ]
        
        for domain in domains:
            site = SiteConfig(domain=domain, brand_code="BRAND", insurer_code="INS_I")
            assert site.domain == domain

    def test_api_version_defaults_to_v4(self):
        """api_version defaults to 'v4'."""
        site = SiteConfig(domain="example.healthsparq.com", brand_code="BRAND", insurer_code="INS_I")
        assert site.api_version == "v4"

    def test_api_version_v3_is_valid(self):
        """api_version can be set to 'v3'."""
        site = SiteConfig(
            domain="example.healthsparq.com",
            brand_code="BRAND",
            insurer_code="INS_I",
            api_version="v3"
        )
        assert site.api_version == "v3"

    def test_api_version_custom_value(self):
        """api_version can be set to any string value (no enum validation)."""
        site = SiteConfig(
            domain="example.healthsparq.com",
            brand_code="BRAND",
            insurer_code="INS_I",
            api_version="v5"
        )
        assert site.api_version == "v5"

    def test_api_version_invalid_format_accepted(self):
        """api_version accepts any string (no validation constraint)."""
        site = SiteConfig(
            domain="example.healthsparq.com",
            brand_code="BRAND",
            insurer_code="INS_I",
            api_version="invalid"
        )
        assert site.api_version == "invalid"


class TestConcurrencyConfigBoundaryTests:
    """Test ConcurrencyConfig boundary conditions."""

    def test_max_workers_zero_raises_error(self):
        """max_workers=0 should raise ValidationError (must be >= 1)."""
        with pytest.raises(ValidationError) as exc_info:
            ConcurrencyConfig(max_workers=0)
        
        error = str(exc_info.value)
        assert "max_workers" in error.lower()

    def test_max_workers_minimum_value_one(self):
        """max_workers=1 is the minimum valid value."""
        config = ConcurrencyConfig(max_workers=1)
        assert config.max_workers == 1

    def test_max_workers_maximum_value_500(self):
        """max_workers=500 is the maximum valid value."""
        config = ConcurrencyConfig(max_workers=500)
        assert config.max_workers == 500

    def test_max_workers_501_raises_error(self):
        """max_workers=501 should raise ValidationError (must be <= 500)."""
        with pytest.raises(ValidationError) as exc_info:
            ConcurrencyConfig(max_workers=501)
        
        error = str(exc_info.value)
        assert "max_workers" in error.lower()

    def test_max_browsers_zero_raises_error(self):
        """max_browsers=0 should raise ValidationError (must be >= 1)."""
        with pytest.raises(ValidationError) as exc_info:
            ConcurrencyConfig(max_browsers=0)
        
        error = str(exc_info.value)
        assert "max_browsers" in error.lower()

    def test_max_browsers_minimum_value_one(self):
        """max_browsers=1 is the minimum valid value."""
        config = ConcurrencyConfig(max_browsers=1)
        assert config.max_browsers == 1

    def test_max_browsers_maximum_value_50(self):
        """max_browsers=50 is the maximum valid value."""
        config = ConcurrencyConfig(max_browsers=50)
        assert config.max_browsers == 50

    def test_max_browsers_51_raises_error(self):
        """max_browsers=51 should raise ValidationError (must be <= 50)."""
        with pytest.raises(ValidationError) as exc_info:
            ConcurrencyConfig(max_browsers=51)
        
        error = str(exc_info.value)
        assert "max_browsers" in error.lower()

    def test_request_delay_ms_negative_raises_error(self):
        """request_delay_ms=-1 should raise ValidationError (must be >= 0)."""
        with pytest.raises(ValidationError) as exc_info:
            ConcurrencyConfig(request_delay_ms=-1)
        
        error = str(exc_info.value)
        assert "request_delay_ms" in error.lower()

    def test_request_delay_ms_zero_is_valid(self):
        """request_delay_ms=0 is valid (no delay)."""
        config = ConcurrencyConfig(request_delay_ms=0)
        assert config.request_delay_ms == 0

    def test_request_delay_ms_large_value(self):
        """request_delay_ms can be a large value."""
        config = ConcurrencyConfig(request_delay_ms=100000)
        assert config.request_delay_ms == 100000

    def test_retry_attempts_zero_raises_error(self):
        """retry_attempts=0 should raise ValidationError (must be >= 1)."""
        with pytest.raises(ValidationError) as exc_info:
            ConcurrencyConfig(retry_attempts=0)
        
        error = str(exc_info.value)
        assert "retry_attempts" in error.lower()

    def test_retry_attempts_minimum_value_one(self):
        """retry_attempts=1 is the minimum valid value."""
        config = ConcurrencyConfig(retry_attempts=1)
        assert config.retry_attempts == 1

    def test_retry_attempts_maximum_value_10(self):
        """retry_attempts=10 is the maximum valid value."""
        config = ConcurrencyConfig(retry_attempts=10)
        assert config.retry_attempts == 10

    def test_retry_attempts_11_raises_error(self):
        """retry_attempts=11 should raise ValidationError (must be <= 10)."""
        with pytest.raises(ValidationError) as exc_info:
            ConcurrencyConfig(retry_attempts=11)
        
        error = str(exc_info.value)
        assert "retry_attempts" in error.lower()

    def test_retry_delay_ms_below_minimum_raises_error(self):
        """retry_delay_ms=99 should raise ValidationError (must be >= 100)."""
        with pytest.raises(ValidationError) as exc_info:
            ConcurrencyConfig(retry_delay_ms=99)
        
        error = str(exc_info.value)
        assert "retry_delay_ms" in error.lower()

    def test_retry_delay_ms_minimum_value_100(self):
        """retry_delay_ms=100 is the minimum valid value."""
        config = ConcurrencyConfig(retry_delay_ms=100)
        assert config.retry_delay_ms == 100

    def test_retry_delay_ms_large_value(self):
        """retry_delay_ms can be a large value."""
        config = ConcurrencyConfig(retry_delay_ms=100000)
        assert config.retry_delay_ms == 100000

    def test_all_fields_at_boundaries(self):
        """All fields can be set to boundary values simultaneously."""
        config = ConcurrencyConfig(
            max_workers=500,
            max_browsers=50,
            request_delay_ms=0,
            retry_attempts=10,
            retry_delay_ms=100,
        )
        assert config.max_workers == 500
        assert config.max_browsers == 50
        assert config.request_delay_ms == 0
        assert config.retry_attempts == 10
        assert config.retry_delay_ms == 100


class TestFilterConfigDefaults:
    """Test FilterConfig default values."""

    def test_default_provider_types_list(self):
        """Default provider_types includes all standard types."""
        config = FilterConfig()
        
        expected_types = ["Facility", "Group", "Pharmacy", "Dental", "Physician", "Other"]
        assert config.provider_types == expected_types

    def test_specialties_default_is_none(self):
        """specialties field defaults to None."""
        config = FilterConfig()
        assert config.specialties is None

    def test_languages_default_is_none(self):
        """languages field defaults to None."""
        config = FilterConfig()
        assert config.languages is None

    def test_gender_filters_default_is_none(self):
        """gender_filters field defaults to None."""
        config = FilterConfig()
        assert config.gender_filters is None

    def test_organization_filters_default_is_none(self):
        """organization_filters field defaults to None."""
        config = FilterConfig()
        assert config.organization_filters is None

    def test_custom_provider_types_override(self):
        """provider_types can be overridden with custom list."""
        config = FilterConfig(provider_types=["Physician", "Facility"])
        assert config.provider_types == ["Physician", "Facility"]

    def test_all_optional_fields_populated(self):
        """All optional filter fields can be populated."""
        config = FilterConfig(
            provider_types=["Physician"],
            specialties=["Cardiology", "Neurology"],
            languages=["English", "Spanish"],
            gender_filters=["Male", "Female"],
            organization_filters=["Hospital", "Clinic"],
        )
        
        assert config.provider_types == ["Physician"]
        assert config.specialties == ["Cardiology", "Neurology"]
        assert config.languages == ["English", "Spanish"]
        assert config.gender_filters == ["Male", "Female"]
        assert config.organization_filters == ["Hospital", "Clinic"]


class TestHealthSparqProjectConfigIntegration:
    """Test HealthSparqProjectConfig integration and validation."""

    def test_minimal_valid_config(self):
        """Minimal valid configuration with all required fields."""
        config = HealthSparqProjectConfig(
            project=ProjectMetadata(
                name="Test Project",
                slug="test_project",
            ),
            site=SiteConfig(
                domain="test.healthsparq.com",
                brand_code="TEST",
                insurer_code="TEST_I",
            ),
            plans=[
                PlanConfig(product_code="MA", name="Medicare Advantage"),
            ],
            coverage=CoverageConfig(states=["TX"]),
        )
        
        assert config.project.name == "Test Project"
        assert config.project.slug == "test_project"
        assert len(config.plans) == 1
        assert config.coverage.states == ["TX"]

    def test_config_with_all_optional_fields(self):
        """Configuration with all optional fields populated."""
        config = HealthSparqProjectConfig(
            project=ProjectMetadata(
                name="Comprehensive Project",
                slug="comprehensive_project",
                description="A fully configured test project",
                version="2.0",
            ),
            site=SiteConfig(
                domain="comprehensive.healthsparq.com",
                brand_code="COMP",
                insurer_code="COMP_I",
                api_version="v3",
            ),
            plans=[
                PlanConfig(
                    product_code="MA",
                    name="Medicare Advantage",
                    insurer_code="CUSTOM_I",
                    brand_code="CUSTOM",
                    state="TX",
                    enabled=True,
                ),
                PlanConfig(
                    product_code="HIX",
                    name="ACA Plan",
                    enabled=False,
                ),
            ],
            coverage=CoverageConfig(
                states=["TX", "LA", "NM"],
                counties={"TX": ["Harris", "Dallas"]},
            ),
            filters=FilterConfig(
                provider_types=["Physician", "Facility"],
                specialties=["Cardiology"],
                languages=["English", "Spanish"],
            ),
            concurrency=ConcurrencyConfig(
                max_workers=50,
                max_browsers=10,
                request_delay_ms=500,
            ),
            output=OutputConfig(
                base_dir="/custom/output",
                raw_subdir="raw_data",
                processed_subdir="processed_data",
            ),
        )
        
        assert config.project.description == "A fully configured test project"
        assert config.project.version == "2.0"
        assert config.site.api_version == "v3"
        assert len(config.plans) == 2
        assert config.coverage.counties["TX"] == ["Harris", "Dallas"]
        assert config.filters.specialties == ["Cardiology"]
        assert config.concurrency.max_workers == 50
        assert config.output.base_dir == "/custom/output"

    def test_missing_required_project_field(self):
        """Missing required project.name should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            HealthSparqProjectConfig(
                project=ProjectMetadata(slug="test"),
                site=SiteConfig(domain="test.com", brand_code="T", insurer_code="T_I"),
                plans=[PlanConfig(product_code="MA", name="Test")],
                coverage=CoverageConfig(states=["TX"]),
            )
        
        error = str(exc_info.value)
        assert "name" in error.lower()

    def test_missing_required_site_field(self):
        """Missing required site.domain should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            HealthSparqProjectConfig(
                project=ProjectMetadata(name="Test", slug="test"),
                site=SiteConfig(brand_code="T", insurer_code="T_I"),  # Missing domain
                plans=[PlanConfig(product_code="MA", name="Test")],
                coverage=CoverageConfig(states=["TX"]),
            )
        
        error = str(exc_info.value)
        assert "domain" in error.lower()

    def test_empty_plans_list_raises_error(self):
        """Empty plans list should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            HealthSparqProjectConfig(
                project=ProjectMetadata(name="Test", slug="test"),
                site=SiteConfig(domain="test.com", brand_code="T", insurer_code="T_I"),
                plans=[],  # Empty list
                coverage=CoverageConfig(states=["TX"]),
            )
        
        error = str(exc_info.value)
        assert "plans" in error.lower() or "min_length" in error.lower()

    def test_missing_coverage_states_raises_error(self):
        """Missing coverage.states should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            HealthSparqProjectConfig(
                project=ProjectMetadata(name="Test", slug="test"),
                site=SiteConfig(domain="test.com", brand_code="T", insurer_code="T_I"),
                plans=[PlanConfig(product_code="MA", name="Test")],
                coverage=CoverageConfig(states=[]),  # Empty states
            )
        
        error = str(exc_info.value)
        assert "states" in error.lower() or "min_length" in error.lower()

    def test_plans_inherit_from_site_config(self):
        """Plans should be able to override site config codes."""
        config = HealthSparqProjectConfig(
            project=ProjectMetadata(name="Test", slug="test"),
            site=SiteConfig(
                domain="test.healthsparq.com",
                brand_code="SITE_BRAND",
                insurer_code="SITE_INS_I",
            ),
            plans=[
                # Plan without overrides (inherits from site in application logic)
                PlanConfig(product_code="MA", name="Default Plan"),
                # Plan with overrides
                PlanConfig(
                    product_code="HIX",
                    name="Custom Plan",
                    brand_code="CUSTOM_BRAND",
                    insurer_code="CUSTOM_INS_I",
                ),
            ],
            coverage=CoverageConfig(states=["TX"]),
        )
        
        # Plan 1 has no overrides (None values, would inherit in application logic)
        assert config.plans[0].brand_code is None
        assert config.plans[0].insurer_code is None
        
        # Plan 2 has explicit overrides
        assert config.plans[1].brand_code == "CUSTOM_BRAND"
        assert config.plans[1].insurer_code == "CUSTOM_INS_I"
        
        # Site config remains unchanged
        assert config.site.brand_code == "SITE_BRAND"
        assert config.site.insurer_code == "SITE_INS_I"

    def test_default_factory_fields_created_automatically(self):
        """Fields with default_factory should be created automatically."""
        config = HealthSparqProjectConfig(
            project=ProjectMetadata(name="Test", slug="test"),
            site=SiteConfig(domain="test.com", brand_code="T", insurer_code="T_I"),
            plans=[PlanConfig(product_code="MA", name="Test")],
            coverage=CoverageConfig(states=["TX"]),
            # Not specifying filters, concurrency, output - they should use defaults
        )
        
        # Filters should have default provider_types
        assert isinstance(config.filters, FilterConfig)
        assert "Physician" in config.filters.provider_types
        
        # Concurrency should have default values
        assert isinstance(config.concurrency, ConcurrencyConfig)
        assert config.concurrency.max_workers == 100
        
        # Output should have default subdirs
        assert isinstance(config.output, OutputConfig)
        assert config.output.raw_subdir == "raw"
        assert config.output.processed_subdir == "processed"

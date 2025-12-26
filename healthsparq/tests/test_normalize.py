"""Tests for Normalize phase module."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

import orjson

from healthsparq.config import load_config
from healthsparq.phases.normalize import (
    NormalizeConfig,
    NormalizeResult,
    deduplicate_by_npi,
    get_provider_data,
    get_specialties,
    map_to_schema,
    merge_provider_data,
    run_normalize_sync,
)


class TestNormalizeConfig:
    """Test NormalizeConfig dataclass."""

    def test_config_creation(self):
        """NormalizeConfig creates with required fields."""
        project_config = load_config("christus_health_plan")
        config = NormalizeConfig(
            config=project_config,
            curr_date="20251226",
        )
        assert config.config == project_config
        assert config.curr_date == "20251226"

    def test_config_defaults(self):
        """NormalizeConfig sets default directories."""
        project_config = load_config("christus_health_plan")
        config = NormalizeConfig(
            config=project_config,
            curr_date="20251226",
        )
        assert config.raw_dir == Path("20251226") / "raw" / "provider_details"
        assert config.output_dir == Path("20251226") / "processed"

    def test_config_custom_dirs(self):
        """NormalizeConfig accepts custom directories."""
        project_config = load_config("christus_health_plan")
        custom_raw = Path("/tmp/raw")
        custom_output = Path("/tmp/processed")
        config = NormalizeConfig(
            config=project_config,
            curr_date="20251226",
            raw_dir=custom_raw,
            output_dir=custom_output,
        )
        assert config.raw_dir == custom_raw
        assert config.output_dir == custom_output


class TestNormalizeResult:
    """Test NormalizeResult dataclass."""

    def test_result_creation(self):
        """NormalizeResult creates with required fields."""
        result = NormalizeResult(
            total_raw=100,
            total_normalized=80,
            duplicates_merged=20,
        )
        assert result.total_raw == 100
        assert result.total_normalized == 80
        assert result.duplicates_merged == 20
        assert result.output_file is None
        assert result.error is None

    def test_result_with_error(self):
        """NormalizeResult can capture errors."""
        result = NormalizeResult(
            total_raw=0,
            total_normalized=0,
            duplicates_merged=0,
            error="File not found",
        )
        assert result.error == "File not found"


class TestGetProviderData:
    """Test provider data extraction."""

    def test_individual_provider(self):
        """Extracts individual provider data correctly."""
        data = {
            "providerCategoryCode": "P",
            "provider": {
                "fullName": "Smith, John",
                "firstName": "John",
                "lastName": "Smith",
            },
            "npi": "1234567890",
            "GENDER": "M",
            "degreeCredentials": ["MD"],
        }
        result = get_provider_data(data)
        assert result["provider_type"] == "individual"
        assert result["npi"] == "1234567890"
        assert result["gender"] == "M"
        assert result["first_name"] == "John"
        assert result["last_name"] == "Smith"

    def test_organization_provider(self):
        """Extracts organization provider data correctly."""
        data = {
            "providerCategoryCode": "O",
            "provider": {
                "fullName": "ABC Hospital",
            },
            "npi": "0987654321",
        }
        result = get_provider_data(data)
        assert result["provider_type"] == "organization"
        assert result["facility_name"] == "ABC Hospital"


class TestGetSpecialties:
    """Test specialty extraction."""

    def test_extracts_specialties(self):
        """Extracts specialties from locations."""
        data = {
            "locations": [
                {
                    "attributes": [
                        {"key": "SPECIALTY", "value": ["Family Medicine", "Internal Medicine"]}
                    ]
                }
            ]
        }
        result = get_specialties(data)
        names = {s["name"] for s in result}
        assert "Family Medicine" in names
        assert "Internal Medicine" in names


class TestMapToSchema:
    """Test schema mapping."""

    def test_returns_empty_without_v2(self):
        """Returns empty structure if no v2 data."""
        data = {"npi": "123"}
        result = map_to_schema(data)
        assert result["networks"] == []
        assert result["provider"] == {}

    def test_maps_v2_data(self):
        """Maps v2 data to schema."""
        data = {
            "npi": "1234567890",
            "v2": {
                "providerCategoryCode": "P",
                "provider": {"fullName": "Smith, John"},
                "attributes": [],
                "locations": [],
            },
        }
        result = map_to_schema(data)
        assert result["provider"]["npi"] == "1234567890"


class TestMergeProviderData:
    """Test provider data merging."""

    def test_merges_networks(self):
        """Merges unique networks."""
        existing = {
            "networks": [{"name": "Network A", "tier": None}],
            "addresses": [],
            "group_affiliations": [],
            "hospital_affiliations": [],
            "specialties": [],
            "provider": {"license_number": None},
        }
        new = {
            "networks": [{"name": "Network B", "tier": None}],
            "addresses": [],
            "group_affiliations": [],
            "hospital_affiliations": [],
            "specialties": [],
            "provider": {"license_number": None},
        }
        result = merge_provider_data(existing, new)
        network_names = {n["name"] for n in result["networks"]}
        assert "Network A" in network_names
        assert "Network B" in network_names


class TestDeduplicateByNpi:
    """Test NPI deduplication."""

    def test_deduplicates_by_npi(self):
        """Deduplicates records by NPI."""
        records = [
            {
                "provider": {"npi": "123", "license_number": None},
                "networks": [{"name": "A", "tier": None}],
                "addresses": [],
                "group_affiliations": [],
                "hospital_affiliations": [],
                "specialties": [],
            },
            {
                "provider": {"npi": "123", "license_number": None},
                "networks": [{"name": "B", "tier": None}],
                "addresses": [],
                "group_affiliations": [],
                "hospital_affiliations": [],
                "specialties": [],
            },
        ]
        result, merge_count = deduplicate_by_npi(records)
        assert len(result) == 1
        assert merge_count == 1
        network_names = {n["name"] for n in result[0]["networks"]}
        assert "A" in network_names
        assert "B" in network_names

    def test_keeps_no_npi_records(self):
        """Keeps records without NPI separately."""
        records = [
            {
                "provider": {"npi": None},
                "networks": [],
                "addresses": [],
                "group_affiliations": [],
                "hospital_affiliations": [],
                "specialties": [],
            },
        ]
        result, merge_count = deduplicate_by_npi(records)
        assert len(result) == 1
        assert merge_count == 0


class TestNormalizePhase:
    """Test normalize phase execution."""

    def test_normalize_empty_dir(self):
        """Normalize handles empty directory."""
        with TemporaryDirectory() as tmpdir:
            project_config = load_config("christus_health_plan")
            config = NormalizeConfig(
                config=project_config,
                curr_date="20251226",
                raw_dir=Path(tmpdir),
                output_dir=Path(tmpdir) / "processed",
            )
            from healthsparq.phases.normalize import run_normalize

            result = run_normalize(config)
            assert result.total_raw == 0
            assert result.total_normalized == 0


class TestImports:
    """Test all imports resolve correctly."""

    def test_normalize_imports(self):
        """Normalize module imports work."""
        from healthsparq.phases import run_normalize, NormalizeConfig, NormalizeResult

        assert run_normalize is not None
        assert NormalizeConfig is not None
        assert NormalizeResult is not None


class TestLOCCount:
    """Verify normalize.py is under 400 lines."""

    def test_normalize_under_400_loc(self):
        """normalize.py is under 400 lines of code."""
        from pathlib import Path

        normalize_path = Path(__file__).parent.parent / "phases" / "normalize.py"
        with open(normalize_path) as f:
            line_count = sum(1 for _ in f)

        assert line_count < 400, f"normalize.py has {line_count} lines (limit: 400)"

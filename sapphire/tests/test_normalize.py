"""Tests for Sapphire normalization phase."""

import pytest

from sapphire.phases.normalize import (
    default_sapphire_mapper,
    _format_address,
    NormalizeConfig,
    NormalizeResult,
)


class TestFormatAddress:
    """Tests for address formatting function."""

    def test_basic_address(self):
        """Basic address formatting."""
        data = {
            "addr_line1": "123 Main St",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
        }
        result = _format_address(data)
        assert result["street_line_1"] == "123 Main St"
        assert result["city"] == "Chicago"
        assert result["state"] == "IL"
        assert result["zip"] == "60601"

    def test_zip_normalization(self):
        """ZIP codes are normalized to 5 digits."""
        data = {
            "addr_line1": "123 Main St",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601-1234",
        }
        result = _format_address(data)
        assert result["zip"] == "60601"

    def test_address_with_line2(self):
        """Address with street line 2."""
        data = {
            "addr_line1": "123 Main St",
            "addr_line2": "Suite 100",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
        }
        result = _format_address(data)
        assert result["street_line_2"] == "Suite 100"
        assert "Suite 100" in result["address_string"]

    def test_phone_formatting(self):
        """Phone numbers are formatted."""
        data = {
            "addr_line1": "123 Main St",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
            "phone": "312-555-0100",
            "fax": "(312) 555-0101",
        }
        result = _format_address(data)
        assert len(result["phones"]) == 2
        # Check phone formatting removed dashes/parens
        assert result["phones"][0]["value"] == "3125550100"
        assert result["phones"][1]["type"] == "fax"

    def test_languages(self):
        """Languages are formatted correctly."""
        data = {
            "addr_line1": "123 Main St",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
            "languages": ["English", "Spanish"],
        }
        result = _format_address(data)
        assert len(result["languages"]) == 2
        assert result["languages"][0]["name"] == "English"
        assert result["languages"][0]["type"] == "primary"

    def test_pcp_from_is_pcp(self):
        """PCP flag from is_pcp field."""
        data = {
            "addr_line1": "123 Main St",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
            "is_pcp": True,
        }
        result = _format_address(data)
        assert result["pcp"] is True

    def test_pcp_from_identifiers(self):
        """PCP flag from identifiers array."""
        data = {
            "addr_line1": "123 Main St",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
            "is_pcp": False,
            "identifiers": [
                {"type_code": "PCP", "value": "PCP123"}
            ],
        }
        result = _format_address(data)
        assert result["pcp"] is True
        assert result["pcp_id"] == "PCP123"

    def test_accepting_new_patients_boolean(self):
        """Accepting new patients from boolean."""
        data = {
            "addr_line1": "123 Main St",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
            "accepting_new_patients": True,
        }
        result = _format_address(data)
        assert result["accepting_new_patients"] is True

    def test_accepting_new_patients_string(self):
        """Accepting new patients from string."""
        for yes_value in ["Y", "YES", "TRUE", "1"]:
            data = {
                "addr_line1": "123 Main St",
                "city": "Chicago",
                "state": "IL",
                "postal_code": "60601",
                "accepting_new_patients": yes_value,
            }
            result = _format_address(data)
            assert result["accepting_new_patients"] is True

    def test_location_id_external_id(self):
        """Location ID becomes external_id."""
        data = {
            "addr_line1": "123 Main St",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
            "location_id": "loc_001",
        }
        result = _format_address(data)
        assert result["external_id"] == "loc_001"


class TestDefaultSapphireMapper:
    """Tests for the default Sapphire mapper function."""

    def test_individual_provider(self, sample_provider_data):
        """Maps individual provider correctly."""
        result = default_sapphire_mapper(sample_provider_data)

        assert result["provider"]["provider_type"] == "individual"
        assert result["provider"]["npi"] == "1234567890"
        assert result["provider"]["first_name"] == "John"
        assert result["provider"]["last_name"] == "Smith"
        assert result["provider"]["gender"] == "M"

    def test_organization_provider(self):
        """Maps organization provider correctly."""
        data = {
            "npi": "9876543210",
            "name": "Medical Group LLC",
            "provider_type": "O",
            "addr_line1": "456 Oak Ave",
            "city": "Springfield",
            "state": "IL",
            "postal_code": "62701",
        }
        result = default_sapphire_mapper(data)

        assert result["provider"]["provider_type"] == "organization"
        assert result["provider"]["facility_name"] == "Medical Group LLC"
        assert result["provider"]["first_name"] is None

    def test_provider_type_inference(self):
        """Provider type inferred from name fields."""
        # Individual (has first/last name)
        individual = default_sapphire_mapper({
            "npi": "1234567890",
            "first_name": "John",
            "last_name": "Smith",
            "addr_line1": "123 Main St",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
        })
        assert individual["provider"]["provider_type"] == "individual"

        # Organization (no first/last name)
        org = default_sapphire_mapper({
            "npi": "9876543210",
            "name": "Test Clinic",
            "addr_line1": "123 Main St",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
        })
        assert org["provider"]["provider_type"] == "organization"

    def test_networks_extraction(self, sample_provider_data):
        """Networks are extracted correctly."""
        result = default_sapphire_mapper(sample_provider_data)

        assert len(result["networks"]) == 1
        assert result["networks"][0]["name"] == "Test Network 1"
        assert result["networks"][0]["tier"] is None

    def test_networks_from_dict(self):
        """Networks extracted from dict format."""
        data = {
            "npi": "1234567890",
            "name": "Test Provider",
            "addr_line1": "123 Main St",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
            "networks": [
                {"name": "Network A", "tier": "Tier 1"},
                {"name": "Network B"},
            ],
        }
        result = default_sapphire_mapper(data)

        assert len(result["networks"]) == 2
        network_a = next(n for n in result["networks"] if n["name"] == "Network A")
        assert network_a["tier"] == "Tier 1"

    def test_networks_deduplicated(self):
        """Duplicate networks are removed."""
        data = {
            "npi": "1234567890",
            "name": "Test Provider",
            "addr_line1": "123 Main St",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
            "networks": ["Network A", "Network A", "Network B"],
        }
        result = default_sapphire_mapper(data)

        assert len(result["networks"]) == 2

    def test_addresses_extraction(self, sample_provider_data):
        """Addresses are extracted correctly."""
        result = default_sapphire_mapper(sample_provider_data)

        assert len(result["addresses"]) == 1
        addr = result["addresses"][0]
        assert addr["street_line_1"] == "123 Main St"
        assert addr["zip"] == "60601"

    def test_other_locations(self):
        """Other provider locations are included."""
        data = {
            "npi": "1234567890",
            "name": "Test Provider",
            "addr_line1": "123 Main St",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
            "other_provider_locations": [
                {
                    "addr_line1": "456 Oak Ave",
                    "city": "Springfield",
                    "state": "IL",
                    "postal_code": "62701",
                }
            ],
        }
        result = default_sapphire_mapper(data)

        assert len(result["addresses"]) == 2

    def test_affiliations_extraction(self, sample_provider_data):
        """Affiliations are extracted correctly."""
        result = default_sapphire_mapper(sample_provider_data)

        assert len(result["group_affiliations"]) == 1
        assert result["group_affiliations"][0]["name"] == "Medical Group A"

        assert len(result["hospital_affiliations"]) == 1
        assert result["hospital_affiliations"][0]["name"] == "General Hospital"

    def test_specialties_extraction(self, sample_provider_data):
        """Specialties are extracted correctly."""
        result = default_sapphire_mapper(sample_provider_data)

        assert len(result["specialties"]) == 1
        assert result["specialties"][0]["name"] == "Family Medicine"

    def test_multiple_specialties(self):
        """Multiple specialties are collected."""
        data = {
            "npi": "1234567890",
            "name": "Test Provider",
            "addr_line1": "123 Main St",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
            "primary_specialty": "Family Medicine",
            "additional_specialties": ["Internal Medicine", "Geriatrics"],
            "relevant_specialty": "Sports Medicine",
        }
        result = default_sapphire_mapper(data)

        spec_names = {s["name"] for s in result["specialties"]}
        assert "Family Medicine" in spec_names
        assert "Internal Medicine" in spec_names
        assert "Geriatrics" in spec_names
        assert "Sports Medicine" in spec_names

    def test_gender_normalization(self):
        """Gender is normalized correctly."""
        for gender in ["M", "F", "O"]:
            data = {
                "npi": "1234567890",
                "name": "Test",
                "gender": gender,
                "addr_line1": "123 Main St",
                "city": "Chicago",
                "state": "IL",
                "postal_code": "60601",
            }
            result = default_sapphire_mapper(data)
            assert result["provider"]["gender"] == gender

    def test_invalid_gender(self):
        """Invalid gender returns None."""
        data = {
            "npi": "1234567890",
            "name": "Test",
            "gender": "Unknown",
            "addr_line1": "123 Main St",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
        }
        result = default_sapphire_mapper(data)
        assert result["provider"]["gender"] is None

    def test_degree_title(self):
        """Degree types become title."""
        data = {
            "npi": "1234567890",
            "first_name": "John",
            "last_name": "Smith",
            "degree_types": ["MD", "PhD"],
            "addr_line1": "123 Main St",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
        }
        result = default_sapphire_mapper(data)
        assert result["provider"]["title"] == "MD PhD"

    def test_empty_data(self):
        """Empty data returns valid structure."""
        result = default_sapphire_mapper({})

        assert "provider" in result
        assert "addresses" in result
        assert "networks" in result
        assert result["addresses"] == []  # No valid addresses

    def test_addresses_filtered(self):
        """Addresses without required fields are filtered."""
        data = {
            "npi": "1234567890",
            "name": "Test Provider",
            # Primary address missing zip
            "addr_line1": "123 Main St",
            "city": "Chicago",
            "state": "IL",
            # No postal_code
        }
        result = default_sapphire_mapper(data)
        assert len(result["addresses"]) == 0


class TestNormalizeConfig:
    """Tests for NormalizeConfig dataclass."""

    def test_defaults(self):
        """Default config values."""
        config = NormalizeConfig()
        assert config.validate is False
        assert config.deduplicate is True
        assert config.output_format == "jsonl"

    def test_custom_values(self):
        """Custom config values."""
        config = NormalizeConfig(
            validate=True,
            deduplicate=False,
            output_format="json",
        )
        assert config.validate is True
        assert config.deduplicate is False
        assert config.output_format == "json"


class TestNormalizeResult:
    """Tests for NormalizeResult dataclass."""

    def test_basic_result(self):
        """Basic result creation."""
        result = NormalizeResult(
            total_records=100,
            unique_npis=80,
            duplicates_removed=20,
        )
        assert result.total_records == 100
        assert result.unique_npis == 80
        assert result.duplicates_removed == 20

    def test_result_with_error(self):
        """Result with error."""
        result = NormalizeResult(
            total_records=0,
            unique_npis=0,
            duplicates_removed=0,
            error="File not found",
        )
        assert result.error == "File not found"

    def test_validation_errors(self):
        """Result with validation errors."""
        result = NormalizeResult(
            total_records=100,
            unique_npis=90,
            duplicates_removed=5,
            validation_errors=10,
        )
        assert result.validation_errors == 10

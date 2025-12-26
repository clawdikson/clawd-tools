"""Comprehensive edge case tests for normalize phase data transformations.

Tests cover:
- Provider data extraction edge cases
- Network extraction edge cases
- Address extraction edge cases
- Deduplication edge cases
- File processing edge cases
- Config variations
"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import orjson
import pytest

from healthsparq.config import load_config
from healthsparq.phases.normalize import (
    NormalizeConfig,
    deduplicate_by_npi,
    get_addresses,
    get_network_names,
    get_provider_data,
    load_raw_details,
    map_to_schema,
    merge_provider_data,
    run_normalize,
)


# ============================================================================
# Provider Data Extraction Edge Cases
# ============================================================================


class TestProviderDataEdgeCases:
    """Test edge cases in provider data extraction."""

    def test_missing_provider_fields(self):
        """Handles missing fields in provider object gracefully."""
        data = {
            "providerCategoryCode": "P",
            "provider": {},  # Empty provider object
            "npi": "1234567890",
        }
        result = get_provider_data(data)
        assert result["npi"] == "1234567890"
        assert result["first_name"] is None
        assert result["last_name"] is None
        assert result["unparsed_name"] == ""

    def test_missing_provider_key(self):
        """Handles missing provider key entirely."""
        data = {
            "providerCategoryCode": "P",
            "npi": "1234567890",
            # No "provider" key at all
        }
        result = get_provider_data(data)
        assert result["npi"] == "1234567890"
        assert result["unparsed_name"] == ""

    def test_empty_string_vs_none_fields(self):
        """Distinguishes between empty strings and None."""
        data = {
            "providerCategoryCode": "P",
            "provider": {
                "fullName": "",  # Empty string
                "firstName": None,  # Explicit None
                "lastName": "",  # Empty string
            },
            "npi": "1234567890",
        }
        result = get_provider_data(data)
        assert result["unparsed_name"] == ""
        assert result["first_name"] is None
        assert result["last_name"] == ""

    def test_npi_validation_10_digits(self):
        """Accepts valid 10-digit NPI."""
        data = {
            "providerCategoryCode": "P",
            "provider": {"fullName": "Smith, John"},
            "npi": "1234567890",  # Valid 10 digits
        }
        result = get_provider_data(data)
        assert result["npi"] == "1234567890"

    def test_npi_invalid_format_too_short(self):
        """Handles NPI that's too short."""
        data = {
            "providerCategoryCode": "P",
            "provider": {"fullName": "Smith, John"},
            "npi": "12345",  # Too short
        }
        result = get_provider_data(data)
        assert result["npi"] == "12345"  # Function doesn't validate, just passes through

    def test_npi_invalid_format_too_long(self):
        """Handles NPI that's too long."""
        data = {
            "providerCategoryCode": "P",
            "provider": {"fullName": "Smith, John"},
            "npi": "12345678901234",  # Too long
        }
        result = get_provider_data(data)
        assert result["npi"] == "12345678901234"

    def test_npi_non_numeric(self):
        """Handles non-numeric NPI."""
        data = {
            "providerCategoryCode": "P",
            "provider": {"fullName": "Smith, John"},
            "npi": "ABC1234567",  # Non-numeric
        }
        result = get_provider_data(data)
        assert result["npi"] == "ABC1234567"

    def test_npi_none(self):
        """Handles None NPI."""
        data = {
            "providerCategoryCode": "P",
            "provider": {"fullName": "Smith, John"},
            "npi": None,
        }
        result = get_provider_data(data)
        assert result["npi"] is None

    def test_name_parsing_comma_separated(self):
        """Parses comma-separated 'Last, First' correctly."""
        data = {
            "providerCategoryCode": "P",
            "provider": {"fullName": "Smith, John"},
            "npi": "1234567890",
        }
        result = get_provider_data(data)
        assert result["unparsed_name"] == "John Smith"

    def test_name_parsing_multiple_commas(self):
        """Handles names with multiple commas."""
        data = {
            "providerCategoryCode": "P",
            "provider": {"fullName": "Smith, Jr., John"},
            "npi": "1234567890",
        }
        result = get_provider_data(data)
        # split(",") creates ["Smith", " Jr.", " John"]
        # reversed() gives [" John", " Jr.", " Smith"]
        # " ".join() gives "John  Jr.  Smith" (extra spaces)
        # .strip() gives "John  Jr.  Smith"
        assert "John" in result["unparsed_name"]
        assert "Smith" in result["unparsed_name"]

    def test_name_no_comma_organization(self):
        """Handles organization name without comma."""
        data = {
            "providerCategoryCode": "O",  # Organization
            "provider": {"fullName": "ABC Medical Center"},
            "npi": "0987654321",
        }
        result = get_provider_data(data)
        assert result["unparsed_name"] == "ABC Medical Center"
        assert result["facility_name"] == "ABC Medical Center"
        assert result["provider_type"] == "organization"

    def test_name_no_comma_individual(self):
        """Handles individual name without comma (unusual)."""
        data = {
            "providerCategoryCode": "P",  # Individual
            "provider": {"fullName": "JohnSmith"},  # No comma
            "npi": "1234567890",
        }
        result = get_provider_data(data)
        # No comma means split(",") returns ["JohnSmith"]
        # reversed() gives ["JohnSmith"]
        # join() gives "JohnSmith"
        assert result["unparsed_name"] == "JohnSmith"

    def test_gender_valid_m(self):
        """Accepts valid gender 'M'."""
        data = {
            "providerCategoryCode": "P",
            "provider": {"fullName": "Smith, John"},
            "npi": "1234567890",
            "GENDER": "M",
        }
        result = get_provider_data(data)
        assert result["gender"] == "M"

    def test_gender_valid_f(self):
        """Accepts valid gender 'F'."""
        data = {
            "providerCategoryCode": "P",
            "provider": {"fullName": "Smith, Jane"},
            "npi": "1234567890",
            "GENDER": "F",
        }
        result = get_provider_data(data)
        assert result["gender"] == "F"

    def test_gender_valid_o(self):
        """Accepts valid gender 'O' (Other)."""
        data = {
            "providerCategoryCode": "P",
            "provider": {"fullName": "Smith, Alex"},
            "npi": "1234567890",
            "GENDER": "O",
        }
        result = get_provider_data(data)
        assert result["gender"] == "O"

    def test_gender_invalid_lowercase(self):
        """Rejects lowercase gender values."""
        data = {
            "providerCategoryCode": "P",
            "provider": {"fullName": "Smith, John"},
            "npi": "1234567890",
            "GENDER": "male",  # Invalid - not M/F/O
        }
        result = get_provider_data(data)
        assert result["gender"] is None  # Invalid values set to None

    def test_gender_invalid_female_string(self):
        """Rejects 'female' string."""
        data = {
            "providerCategoryCode": "P",
            "provider": {"fullName": "Smith, Jane"},
            "npi": "1234567890",
            "GENDER": "female",
        }
        result = get_provider_data(data)
        assert result["gender"] is None

    def test_gender_none(self):
        """Handles None gender."""
        data = {
            "providerCategoryCode": "P",
            "provider": {"fullName": "Smith, John"},
            "npi": "1234567890",
            "GENDER": None,
        }
        result = get_provider_data(data)
        assert result["gender"] is None

    def test_gender_missing_key(self):
        """Handles missing GENDER key."""
        data = {
            "providerCategoryCode": "P",
            "provider": {"fullName": "Smith, John"},
            "npi": "1234567890",
            # No GENDER key
        }
        result = get_provider_data(data)
        assert result["gender"] is None

    def test_provider_category_code_p(self):
        """Recognizes 'P' as individual provider."""
        data = {
            "providerCategoryCode": "P",
            "provider": {"fullName": "Smith, John"},
            "npi": "1234567890",
        }
        result = get_provider_data(data)
        assert result["provider_type"] == "individual"
        assert result["facility_name"] is None

    def test_provider_category_code_non_p(self):
        """Treats non-'P' as organization."""
        for code in ["O", "F", "G", "", None]:
            data = {
                "providerCategoryCode": code,
                "provider": {"fullName": "ABC Hospital"},
                "npi": "0987654321",
            }
            result = get_provider_data(data)
            assert result["provider_type"] == "organization"
            assert result["facility_name"] == "ABC Hospital"

    def test_degree_credentials_multiple(self):
        """Combines multiple degree credentials."""
        data = {
            "providerCategoryCode": "P",
            "provider": {"fullName": "Smith, John"},
            "npi": "1234567890",
            "degreeCredentials": ["MD", "PhD", "FACP"],
        }
        result = get_provider_data(data)
        assert result["title"] == "MD PhD FACP"

    def test_degree_credentials_empty(self):
        """Handles empty degree credentials."""
        data = {
            "providerCategoryCode": "P",
            "provider": {"fullName": "Smith, John"},
            "npi": "1234567890",
            "degreeCredentials": [],
        }
        result = get_provider_data(data)
        assert result["title"] == ""

    def test_degree_credentials_none(self):
        """Handles missing degree credentials."""
        data = {
            "providerCategoryCode": "P",
            "provider": {"fullName": "Smith, John"},
            "npi": "1234567890",
            # No degreeCredentials key
        }
        result = get_provider_data(data)
        assert result["title"] == ""


# ============================================================================
# Network Extraction Edge Cases
# ============================================================================


class TestNetworkExtractionEdgeCases:
    """Test edge cases in network extraction."""

    def test_empty_networks_list(self):
        """Handles empty networks list."""
        data = {"locations": []}
        result = get_network_names(data)
        assert result == []

    def test_missing_locations_key(self):
        """Handles missing locations key."""
        data = {}  # No locations
        result = get_network_names(data)
        assert result == []

    def test_nested_network_structures(self):
        """Extracts from deeply nested network structures."""
        data = {
            "locations": [
                {
                    "attributes": [
                        {
                            "key": "PLANS_ACCEPTED",
                            "value": [
                                {
                                    "subCategories": [
                                        {
                                            "plans": [
                                                {"name": "Network A"},
                                                {"name": "Network B"},
                                            ]
                                        },
                                        {
                                            "plans": [
                                                {"name": "Network C"},
                                            ]
                                        },
                                    ]
                                }
                            ],
                        }
                    ],
                }
            ]
        }
        result = get_network_names(data)
        network_names = {n["name"] for n in result}
        assert "Network A" in network_names
        assert "Network B" in network_names
        assert "Network C" in network_names

    def test_missing_plan_name_field(self):
        """Handles missing planName field."""
        data = {
            "locations": [
                {
                    "PLANS_ACCEPTED": [
                        {
                            "subCategories": [
                                {
                                    "plans": [
                                        {},  # No "name" field
                                        {"name": None},  # Explicit None
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        result = get_network_names(data)
        # get("name", "") returns "" for missing, None for explicit None
        network_names = {n["name"] for n in result}
        assert "" in network_names or None in network_names

    def test_duplicate_network_names(self):
        """Deduplicates network names using set."""
        data = {
            "locations": [
                {
                    "PLANS_ACCEPTED": [
                        {
                            "subCategories": [
                                {
                                    "plans": [
                                        {"name": "Network A"},
                                        {"name": "Network A"},  # Duplicate
                                        {"name": "Network B"},
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        result = get_network_names(data)
        network_names = [n["name"] for n in result]
        assert network_names.count("Network A") == 1  # Deduplicated
        assert "Network B" in network_names

    def test_network_tier_always_none(self):
        """Verifies tier is always None in current implementation."""
        data = {
            "locations": [
                {
                    "PLANS_ACCEPTED": [
                        {
                            "subCategories": [
                                {"plans": [{"name": "Network A", "tier": "Gold"}]}
                            ]
                        }
                    ]
                }
            ]
        }
        result = get_network_names(data)
        for network in result:
            assert network["tier"] is None  # Current implementation ignores tier


# ============================================================================
# Address Extraction Edge Cases
# ============================================================================


class TestAddressExtractionEdgeCases:
    """Test edge cases in address extraction."""

    def test_missing_address_fields(self):
        """Handles missing required address fields."""
        data = {
            "locations": [
                {
                    "address": {
                        # Missing line1
                        "city": "Boston",
                        "state": "MA",
                        # Missing zip
                    },
                    "attributes": [],
                    "elevatedAttributes": [],
                }
            ]
        }
        result = get_addresses(data)
        assert result == []  # No addresses without line1 and zip

    def test_address_with_street_line_1_only(self):
        """Includes address with only street_line_1 and zip."""
        data = {
            "locations": [
                {
                    "address": {
                        "line1": "123 Main St",
                        "zip": "02101",
                        # No line2, city, state
                    },
                    "id": "LOC123",
                    "attributes": [],
                    "elevatedAttributes": [],
                }
            ]
        }
        result = get_addresses(data)
        assert len(result) == 1
        assert result[0]["street_line_1"] == "123 Main St"
        assert result[0]["zip"] == "02101"
        assert result[0]["city"] is None
        assert result[0]["state"] is None

    def test_multiple_addresses_one_provider(self):
        """Extracts multiple addresses for one provider."""
        data = {
            "locations": [
                {
                    "id": "LOC1",
                    "address": {
                        "line1": "123 Main St",
                        "city": "Boston",
                        "state": "MA",
                        "zip": "02101",
                    },
                    "attributes": [],
                    "elevatedAttributes": [],
                },
                {
                    "id": "LOC2",
                    "address": {
                        "line1": "456 Oak Ave",
                        "city": "Cambridge",
                        "state": "MA",
                        "zip": "02138",
                    },
                    "attributes": [],
                    "elevatedAttributes": [],
                },
            ]
        }
        result = get_addresses(data)
        assert len(result) == 2
        assert result[0]["street_line_1"] == "123 Main St"
        assert result[1]["street_line_1"] == "456 Oak Ave"

    def test_accepting_new_patients_accepting_all(self):
        """Recognizes 'elevated.anp.acceptingAll' as accepting."""
        data = {
            "locations": [
                {
                    "id": "LOC1",
                    "address": {"line1": "123 Main St", "zip": "02101"},
                    "attributes": [
                        {
                            "key": "PLANS_ACCEPTED",
                            "value": [
                                {
                                    "acceptingPatients": {
                                        "labelKey": "elevated.anp.acceptingAll"
                                    }
                                }
                            ],
                        }
                    ],
                    "elevatedAttributes": [],
                }
            ]
        }
        result = get_addresses(data)
        assert result[0]["accepting_new_patients"] is True

    def test_accepting_new_patients_accepting_some(self):
        """Recognizes 'elevated.anp.acceptingSome' as accepting."""
        data = {
            "locations": [
                {
                    "id": "LOC1",
                    "address": {"line1": "123 Main St", "zip": "02101"},
                    "attributes": [
                        {
                            "key": "PLANS_ACCEPTED",
                            "value": [
                                {
                                    "acceptingPatients": {
                                        "labelKey": "elevated.anp.acceptingSome"
                                    }
                                }
                            ],
                        }
                    ],
                    "elevatedAttributes": [],
                }
            ]
        }
        result = get_addresses(data)
        assert result[0]["accepting_new_patients"] is True

    def test_accepting_new_patients_not_accepting(self):
        """Recognizes other labelKeys as not accepting."""
        data = {
            "locations": [
                {
                    "id": "LOC1",
                    "address": {"line1": "123 Main St", "zip": "02101"},
                    "attributes": [
                        {
                            "key": "PLANS_ACCEPTED",
                            "value": [
                                {
                                    "acceptingPatients": {
                                        "labelKey": "elevated.anp.notAccepting"
                                    }
                                }
                            ],
                        }
                    ],
                    "elevatedAttributes": [],
                }
            ]
        }
        result = get_addresses(data)
        assert result[0]["accepting_new_patients"] is False

    def test_accepting_new_patients_missing_field(self):
        """Defaults to False when acceptingPatients missing."""
        data = {
            "locations": [
                {
                    "id": "LOC1",
                    "address": {"line1": "123 Main St", "zip": "02101"},
                    "attributes": [],
                    "elevatedAttributes": [],
                }
            ]
        }
        result = get_addresses(data)
        assert result[0]["accepting_new_patients"] is False

    def test_invalid_zip_codes(self):
        """Accepts invalid ZIP codes (no validation)."""
        for invalid_zip in ["123", "ABCDE", "12345678", ""]:
            data = {
                "locations": [
                    {
                        "id": "LOC1",
                        "address": {"line1": "123 Main St", "zip": invalid_zip},
                        "attributes": [],
                        "elevatedAttributes": [],
                    }
                ]
            }
            result = get_addresses(data)
            if invalid_zip:  # Empty string treated as None?
                assert len(result) == 1
                assert result[0]["zip"] == invalid_zip

    def test_empty_phone_numbers(self):
        """Handles empty phone numbers."""
        data = {
            "locations": [
                {
                    "id": "LOC1",
                    "address": {"line1": "123 Main St", "zip": "02101"},
                    "attributes": [
                        {
                            "key": "CONTACT",
                            "value": [
                                {"type": "phone", "values": []},  # Empty values
                            ],
                        }
                    ],
                    "elevatedAttributes": [],
                }
            ]
        }
        result = get_addresses(data)
        assert result[0]["phones"] == []

    def test_multiple_phone_types(self):
        """Extracts phone and fax numbers."""
        data = {
            "locations": [
                {
                    "id": "LOC1",
                    "address": {"line1": "123 Main St", "zip": "02101"},
                    "attributes": [
                        {
                            "key": "CONTACT",
                            "value": [
                                {"type": "phone", "values": [{"display": "617-555-0100"}]},
                                {"type": "fax", "values": [{"display": "617-555-0101"}]},
                                {
                                    "type": "email",
                                    "values": [{"display": "test@example.com"}],
                                },  # Not included
                            ],
                        }
                    ],
                    "elevatedAttributes": [],
                }
            ]
        }
        result = get_addresses(data)
        phones = result[0]["phones"]
        assert len(phones) == 2
        phone_types = {p["type"] for p in phones}
        assert "phone" in phone_types
        assert "fax" in phone_types
        assert "email" not in phone_types  # Only phone/fax included

    def test_address_without_location_data(self):
        """Includes address even without location coordinates."""
        data = {
            "locations": [
                {
                    "id": "LOC1",
                    "address": {
                        "line1": "123 Main St",
                        "zip": "02101",
                        # No latitude/longitude
                    },
                    "attributes": [],
                    "elevatedAttributes": [],
                }
            ]
        }
        result = get_addresses(data)
        assert len(result) == 1
        assert result[0]["street_line_1"] == "123 Main St"

    def test_pcp_from_elevated_attributes(self):
        """Detects PCP from elevatedAttributes."""
        data = {
            "locations": [
                {
                    "id": "LOC1",
                    "address": {"line1": "123 Main St", "zip": "02101"},
                    "attributes": [],
                    "elevatedAttributes": [
                        {"labelKey": "elevated.pcp.true", "style": "success"}
                    ],
                }
            ]
        }
        result = get_addresses(data)
        assert result[0]["pcp"] is True

    def test_pcp_from_plans_accepted(self):
        """Detects PCP from PLANS_ACCEPTED pcpEligible."""
        data = {
            "locations": [
                {
                    "id": "LOC1",
                    "address": {"line1": "123 Main St", "zip": "02101"},
                    "attributes": [
                        {
                            "key": "PLANS_ACCEPTED",
                            "value": [{"pcpEligible": True}],
                        }
                    ],
                    "elevatedAttributes": [],
                }
            ]
        }
        result = get_addresses(data)
        assert result[0]["pcp"] is True

    def test_address_string_with_line2(self):
        """Formats address string with line2."""
        data = {
            "locations": [
                {
                    "id": "LOC1",
                    "address": {
                        "line1": "123 Main St",
                        "line2": "Suite 200",
                        "city": "Boston",
                        "state": "MA",
                        "zip": "02101",
                    },
                    "attributes": [],
                    "elevatedAttributes": [],
                }
            ]
        }
        result = get_addresses(data)
        expected = "123 Main St, Suite 200, Boston, MA 02101"
        assert result[0]["address_string"] == expected

    def test_address_string_without_line2(self):
        """Formats address string without line2."""
        data = {
            "locations": [
                {
                    "id": "LOC1",
                    "address": {
                        "line1": "123 Main St",
                        "city": "Boston",
                        "state": "MA",
                        "zip": "02101",
                    },
                    "attributes": [],
                    "elevatedAttributes": [],
                }
            ]
        }
        result = get_addresses(data)
        expected = "123 Main St, Boston, MA 02101"
        assert result[0]["address_string"] == expected


# ============================================================================
# Deduplication Edge Cases
# ============================================================================


class TestDeduplicationEdgeCases:
    """Test edge cases in NPI deduplication."""

    def test_multiple_records_same_npi(self):
        """Merges multiple records with same NPI."""
        records = [
            {
                "provider": {"npi": "1234567890", "license_number": None},
                "networks": [{"name": "Network A", "tier": None}],
                "addresses": [{"external_id": "LOC1"}],
                "group_affiliations": [],
                "hospital_affiliations": [],
                "specialties": [],
            },
            {
                "provider": {"npi": "1234567890", "license_number": "LIC123"},
                "networks": [{"name": "Network B", "tier": None}],
                "addresses": [{"external_id": "LOC2"}],
                "group_affiliations": [],
                "hospital_affiliations": [],
                "specialties": [],
            },
            {
                "provider": {"npi": "1234567890", "license_number": None},
                "networks": [{"name": "Network C", "tier": None}],
                "addresses": [{"external_id": "LOC3"}],
                "group_affiliations": [],
                "hospital_affiliations": [],
                "specialties": [],
            },
        ]
        result, merge_count = deduplicate_by_npi(records)
        assert len(result) == 1
        assert merge_count == 2
        # Verify all data merged
        network_names = {n["name"] for n in result[0]["networks"]}
        assert network_names == {"Network A", "Network B", "Network C"}
        addr_ids = {a["external_id"] for a in result[0]["addresses"]}
        assert addr_ids == {"LOC1", "LOC2", "LOC3"}
        assert result[0]["provider"]["license_number"] == "LIC123"

    def test_records_different_npis(self):
        """Keeps records with different NPIs separate."""
        records = [
            {
                "provider": {"npi": "1111111111", "license_number": None},
                "networks": [],
                "addresses": [],
                "group_affiliations": [],
                "hospital_affiliations": [],
                "specialties": [],
            },
            {
                "provider": {"npi": "2222222222", "license_number": None},
                "networks": [],
                "addresses": [],
                "group_affiliations": [],
                "hospital_affiliations": [],
                "specialties": [],
            },
        ]
        result, merge_count = deduplicate_by_npi(records)
        assert len(result) == 2
        assert merge_count == 0

    def test_partial_duplicates_same_npi_different_addresses(self):
        """Merges addresses when same NPI."""
        records = [
            {
                "provider": {"npi": "1234567890", "license_number": None},
                "networks": [],
                "addresses": [
                    {
                        "external_id": "LOC1",
                        "street_line_1": "123 Main St",
                        "zip": "02101",
                    }
                ],
                "group_affiliations": [],
                "hospital_affiliations": [],
                "specialties": [],
            },
            {
                "provider": {"npi": "1234567890", "license_number": None},
                "networks": [],
                "addresses": [
                    {
                        "external_id": "LOC2",
                        "street_line_1": "456 Oak Ave",
                        "zip": "02138",
                    }
                ],
                "group_affiliations": [],
                "hospital_affiliations": [],
                "specialties": [],
            },
        ]
        result, merge_count = deduplicate_by_npi(records)
        assert len(result) == 1
        assert merge_count == 1
        assert len(result[0]["addresses"]) == 2

    def test_records_with_none_npi(self):
        """Keeps records with None NPI separate."""
        records = [
            {
                "provider": {"npi": None, "license_number": None},
                "networks": [{"name": "Network A", "tier": None}],
                "addresses": [],
                "group_affiliations": [],
                "hospital_affiliations": [],
                "specialties": [],
            },
            {
                "provider": {"npi": None, "license_number": None},
                "networks": [{"name": "Network B", "tier": None}],
                "addresses": [],
                "group_affiliations": [],
                "hospital_affiliations": [],
                "specialties": [],
            },
        ]
        result, merge_count = deduplicate_by_npi(records)
        assert len(result) == 2  # Not merged
        assert merge_count == 0

    def test_mixed_npi_and_none(self):
        """Handles mix of NPI and None records."""
        records = [
            {
                "provider": {"npi": "1234567890", "license_number": None},
                "networks": [],
                "addresses": [],
                "group_affiliations": [],
                "hospital_affiliations": [],
                "specialties": [],
            },
            {
                "provider": {"npi": None, "license_number": None},
                "networks": [],
                "addresses": [],
                "group_affiliations": [],
                "hospital_affiliations": [],
                "specialties": [],
            },
            {
                "provider": {"npi": "1234567890", "license_number": None},
                "networks": [],
                "addresses": [],
                "group_affiliations": [],
                "hospital_affiliations": [],
                "specialties": [],
            },
        ]
        result, merge_count = deduplicate_by_npi(records)
        assert len(result) == 2  # 1 merged NPI record + 1 None NPI record
        assert merge_count == 1


# ============================================================================
# File Processing Edge Cases
# ============================================================================


class TestFileProcessingEdgeCases:
    """Test edge cases in file loading and processing."""

    def test_empty_input_file(self):
        """Handles empty input directory."""
        with TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "raw"
            raw_dir.mkdir()
            result = load_raw_details(raw_dir)
            assert result == []

    def test_malformed_json_lines(self):
        """Skips malformed JSON files."""
        with TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "raw"
            raw_dir.mkdir()

            # Create valid file
            valid_file = raw_dir / "valid.json"
            with open(valid_file, "wb") as f:
                f.write(orjson.dumps({"npi": "123"}))

            # Create malformed file
            invalid_file = raw_dir / "invalid.json"
            with open(invalid_file, "w") as f:
                f.write("{invalid json")

            result = load_raw_details(raw_dir)
            assert len(result) == 1
            assert result[0]["npi"] == "123"

    def test_very_large_files_memory_handling(self):
        """Processes large number of records."""
        with TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "raw"
            raw_dir.mkdir()

            # Create 1000 small JSON files
            for i in range(1000):
                file_path = raw_dir / f"provider_{i}.json"
                with open(file_path, "wb") as f:
                    f.write(orjson.dumps({"npi": f"{i:010d}"}))

            result = load_raw_details(raw_dir)
            assert len(result) == 1000

    def test_unicode_in_provider_names(self):
        """Handles Unicode characters in provider names."""
        data = {
            "npi": "1234567890",
            "v2": {
                "providerCategoryCode": "P",
                "provider": {"fullName": "García, José"},
                "attributes": [],
                "locations": [],
            },
        }
        result = map_to_schema(data)
        assert "García" in result["provider"]["unparsed_name"]
        assert "José" in result["provider"]["unparsed_name"]

    def test_special_characters_in_addresses(self):
        """Handles special characters in addresses."""
        data = {
            "npi": "1234567890",
            "v2": {
                "providerCategoryCode": "P",
                "provider": {"fullName": "Smith, John"},
                "attributes": [],
                "locations": [
                    {
                        "id": "LOC1",
                        "address": {
                            "line1": "123 O'Brien St",
                            "line2": "Apt #5-B",
                            "city": "Saint-Denis",
                            "state": "QC",
                            "zip": "H2J 1K8",
                        },
                        "attributes": [],
                        "elevatedAttributes": [],
                    }
                ],
            },
        }
        result = map_to_schema(data)
        assert len(result["addresses"]) == 1
        assert "O'Brien" in result["addresses"][0]["street_line_1"]
        assert "#5-B" in result["addresses"][0]["street_line_2"]

    def test_emoji_in_facility_names(self):
        """Handles emoji in facility names."""
        data = {
            "npi": "1234567890",
            "v2": {
                "providerCategoryCode": "O",
                "provider": {"fullName": "🏥 ABC Medical Center"},
                "attributes": [],
                "locations": [],
            },
        }
        result = map_to_schema(data)
        assert "🏥" in result["provider"]["facility_name"]


# ============================================================================
# Config Variations
# ============================================================================


class TestConfigVariations:
    """Test different config variations."""

    def test_custom_output_directories(self):
        """Uses custom output directories."""
        with TemporaryDirectory() as tmpdir:
            project_config = load_config("christus_health_plan")
            custom_output = Path(tmpdir) / "custom_output"
            custom_raw = Path(tmpdir) / "custom_raw"
            custom_raw.mkdir(parents=True)

            config = NormalizeConfig(
                config=project_config,
                curr_date="20251226",
                raw_dir=custom_raw,
                output_dir=custom_output,
            )

            result = run_normalize(config)
            assert result.error is None
            assert custom_output.exists()

    def test_different_date_formats(self):
        """Handles different date formats."""
        project_config = load_config("christus_health_plan")
        for date_format in ["20251226", "2025-12-26", "2025_12_26"]:
            config = NormalizeConfig(
                config=project_config,
                curr_date=date_format,
            )
            assert config.curr_date == date_format
            assert str(date_format) in str(config.raw_dir)

    def test_missing_raw_data_directory(self):
        """Handles missing raw data directory."""
        with TemporaryDirectory() as tmpdir:
            project_config = load_config("christus_health_plan")
            non_existent = Path(tmpdir) / "non_existent"

            config = NormalizeConfig(
                config=project_config,
                curr_date="20251226",
                raw_dir=non_existent,
                output_dir=Path(tmpdir) / "output",
            )

            result = run_normalize(config)
            assert result.total_raw == 0
            assert result.total_normalized == 0
            assert result.error is None  # Not an error, just no data


# ============================================================================
# Integration Tests
# ============================================================================


class TestNormalizeIntegration:
    """Integration tests combining multiple edge cases."""

    def test_full_pipeline_with_edge_cases(self):
        """Tests complete normalization with various edge cases."""
        with TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "raw" / "provider_details"
            raw_dir.mkdir(parents=True)

            # Create test data with edge cases
            test_records = [
                # Valid record
                {
                    "npi": "1234567890",
                    "v2": {
                        "providerCategoryCode": "P",
                        "provider": {"fullName": "Smith, John"},
                        "attributes": [],
                        "locations": [
                            {
                                "id": "LOC1",
                                "address": {"line1": "123 Main St", "zip": "02101"},
                                "attributes": [],
                                "elevatedAttributes": [],
                            }
                        ],
                    },
                },
                # Duplicate NPI
                {
                    "npi": "1234567890",
                    "v2": {
                        "providerCategoryCode": "P",
                        "provider": {"fullName": "Smith, John"},
                        "attributes": [],
                        "locations": [
                            {
                                "id": "LOC2",
                                "address": {"line1": "456 Oak Ave", "zip": "02138"},
                                "attributes": [],
                                "elevatedAttributes": [],
                            }
                        ],
                    },
                },
                # No NPI
                {
                    "npi": None,
                    "v2": {
                        "providerCategoryCode": "O",
                        "provider": {"fullName": "ABC Hospital"},
                        "attributes": [],
                        "locations": [],
                    },
                },
                # Unicode name
                {
                    "npi": "9876543210",
                    "v2": {
                        "providerCategoryCode": "P",
                        "provider": {"fullName": "García, José"},
                        "attributes": [],
                        "locations": [],
                    },
                },
                # No v2 data
                {"npi": "5555555555"},
            ]

            # Write test files
            for i, record in enumerate(test_records):
                file_path = raw_dir / f"provider_{i}.json"
                with open(file_path, "wb") as f:
                    f.write(orjson.dumps(record))

            # Run normalization
            project_config = load_config("christus_health_plan")
            config = NormalizeConfig(
                config=project_config,
                curr_date="20251226",
                raw_dir=raw_dir,
                output_dir=Path(tmpdir) / "processed",
            )

            result = run_normalize(config)

            # Verify results
            assert result.total_raw == 5
            assert result.total_normalized == 3  # 1 merged, 1 no NPI, 1 unicode, 1 skipped (no v2)
            assert result.duplicates_merged == 1
            assert result.error is None

            # Verify output file
            output_file = Path(result.output_file)
            assert output_file.exists()

            # Read and verify output
            with open(output_file, "rb") as f:
                lines = f.readlines()
                assert len(lines) == 3

            # Parse and verify merged record
            records = [orjson.loads(line) for line in lines]
            merged_record = [r for r in records if r["provider"]["npi"] == "1234567890"][
                0
            ]
            assert len(merged_record["addresses"]) == 2  # Both addresses merged

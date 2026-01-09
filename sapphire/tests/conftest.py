"""Pytest fixtures for Sapphire tests."""

import json
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config_yaml():
    """Sample YAML configuration content."""
    return """
project:
  name: Test Project
  slug: test_project
  description: Test project description

site:
  domain: test.providerfinderonline.com
  ci: test-ci
  config_signature: "{1292}-{1397|51}-{}"

networks:
  - id: "210000001"
    name: "Test Network 1"
    state: IL
  - id: "210000002"
    name: "Test Network 2"
    state: IL

coverage:
  states: [IL]
  geo_strategy: dual

api:
  endpoints:
    facets: /api/providers/facets.json
    summary: /api/providers/summary.json
  common_params:
    locale: en

concurrency:
  max_workers: 10
  batch_size: 100

output:
  storage_backend: sqlite

session:
  browser_type: camoufox
  proxy:
    server: http://proxy.example.com:8080
"""


@pytest.fixture
def sample_geo_codes():
    """Sample geo codes in new format."""
    return {
        "geo_codes": [
            {
                "state": "IL",
                "coords": [40.0793621, -89.1681558],
                "radius": 240,
                "geo_num": 0
            }
        ]
    }


@pytest.fixture
def sample_geo_codes_legacy():
    """Sample geo codes in legacy format."""
    return {
        "IL": {
            "coords": [
                {"lat": 40.0793621, "lng": -89.1681558, "radius": 240}
            ]
        }
    }


@pytest.fixture
def sample_provider_data():
    """Sample raw provider data from Sapphire API."""
    return {
        "provider_id": "123456",
        "npi": "1234567890",
        "name": "John Smith, MD",
        "first_name": "John",
        "last_name": "Smith",
        "gender": "M",
        "provider_type": "P",
        "primary_specialty": "Family Medicine",
        "degree_types": ["MD"],
        "addr_line1": "123 Main St",
        "city": "Chicago",
        "state": "IL",
        "postal_code": "60601-1234",
        "phone": "312-555-0100",
        "accepting_new_patients": True,
        "is_pcp": True,
        "location_id": "loc_001",
        "languages": ["English", "Spanish"],
        "networks": ["Test Network 1"],
        "group_affiliations": [{"name": "Medical Group A"}],
        "hospital_affiliations": [{"name": "General Hospital"}],
    }


@pytest.fixture
def sample_normalized_provider():
    """Sample normalized provider in Ideon format."""
    return {
        "networks": [{"name": "Test Network 1", "tier": None}],
        "provider": {
            "unparsed_name": "John Smith, MD",
            "gender": "M",
            "provider_type": "individual",
            "npi": "1234567890",
            "license_number": None,
            "facility_name": None,
            "first_name": "John",
            "middle_name": None,
            "last_name": "Smith",
            "title": "MD",
            "suffix": None,
            "rating": {"score": None, "scale": None},
        },
        "addresses": [
            {
                "street_line_1": "123 Main St",
                "street_line_2": None,
                "city": "Chicago",
                "state": "IL",
                "zip": "60601",
                "office_name": None,
                "address_string": "123 Main St, Chicago, IL 60601",
                "phones": [{"type": "phone", "value": "3125550100"}],
                "languages": [
                    {"name": "English", "type": "primary"},
                    {"name": "Spanish", "type": "primary"},
                ],
                "pcp": True,
                "pcp_id": None,
                "accepting_new_patients": True,
                "external_id": "loc_001",
            }
        ],
        "group_affiliations": [{"name": "Medical Group A"}],
        "hospital_affiliations": [{"name": "General Hospital"}],
        "specialties": [{"name": "Family Medicine"}],
    }


@pytest.fixture
def config_dir(temp_dir, sample_config_yaml):
    """Create a config directory with sample files."""
    configs_dir = temp_dir / "configs"
    configs_dir.mkdir()

    # Write sample config
    (configs_dir / "test_project.yaml").write_text(sample_config_yaml)

    # Write base config
    base_yaml = """
concurrency:
  max_workers: 25
  max_pages: 2
  batch_size: 1000
  retry_attempts: 5
  request_timeout_ms: 120000
  retry_delay_ms: 2000
  page_refresh_interval: 5000

output:
  storage_backend: sqlite
  raw_subdir: raw
  processed_subdir: processed
"""
    (configs_dir / "_base.yaml").write_text(base_yaml)

    return configs_dir


@pytest.fixture
def geo_codes_dir(temp_dir, sample_geo_codes):
    """Create a geo_codes directory with sample files."""
    geo_dir = temp_dir / "data" / "geo_codes"
    geo_dir.mkdir(parents=True)

    # Write geo codes files
    (geo_dir / "small.json").write_text(json.dumps(sample_geo_codes))
    (geo_dir / "complete.json").write_text(json.dumps(sample_geo_codes))

    return geo_dir

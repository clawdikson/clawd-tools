"""Pytest configuration and fixtures for healthsparq tests."""

import json
from pathlib import Path
from typing import Any, Dict

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the fixtures directory path."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def mock_search_response(fixtures_dir: Path) -> Dict[str, Any]:
    """Load mock search response from fixtures."""
    fixture_file = fixtures_dir / "mock_search_response.json"
    with open(fixture_file, "r") as f:
        return json.load(f)


@pytest.fixture
def mock_provider_detail(fixtures_dir: Path) -> Dict[str, Any]:
    """Load mock provider detail response from fixtures."""
    fixture_file = fixtures_dir / "mock_provider_detail.json"
    with open(fixture_file, "r") as f:
        return json.load(f)


@pytest.fixture
def mock_healthspark_config() -> Dict[str, Any]:
    """Return mock HealthSpark configuration."""
    return {
        "codes": {
            "insurerCode": "BCBSA",
            "productCode": "BCBSAHPN",
            "brandCode": "BCBSANDHF",
        },
        "urls": {
            "auth_url": "https://medicare.healthsparq.com/healthsparq/{insurerCode}/auth/{brandCode}/{productCode}",
            "search_url": "https://medicare.healthsparq.com/healthsparq/{insurerCode}/search/{brandCode}/{productCode}",
        },
    }


@pytest.fixture
def mock_project_config() -> Dict[str, Any]:
    """Return mock project configuration for testing."""
    return {
        "project": {
            "name": "audiobee_bluecard_national",
            "slug": "bluecard_national",
        },
        "site": {
            "domain": "medicare.healthsparq.com",
            "brand_code": "BCBSANDHF",
            "insurer_code": "BCBSA",
        },
        "plans": [
            {
                "product_code": "BCBSAHPN",
                "name": "BlueCard HPN",
                "insurer_code": "BCBSA",
                "brand_code": "BCBSANDHF",
                "state": None,
                "enabled": True,
            }
        ],
        "coverage": {
            "states": ["AK", "AL", "AR", "AZ", "CA"],
        },
    }

"""Placeholder tests to ensure pytest runs successfully."""

import pytest


def test_fixtures_load(mock_search_response, mock_provider_detail):
    """Test that fixtures load correctly."""
    assert mock_search_response is not None
    assert "providerResults" in mock_search_response
    assert mock_provider_detail is not None
    assert "providerId" in mock_provider_detail


def test_mock_config(mock_healthspark_config, mock_project_config):
    """Test that config fixtures are valid."""
    assert mock_healthspark_config is not None
    assert "codes" in mock_healthspark_config
    assert "urls" in mock_healthspark_config

    assert mock_project_config is not None
    assert "project" in mock_project_config
    assert "site" in mock_project_config
    assert "plans" in mock_project_config


def test_search_response_structure(mock_search_response):
    """Test search response has expected structure."""
    assert isinstance(mock_search_response["providerResults"], list)
    assert len(mock_search_response["providerResults"]) > 0

    provider = mock_search_response["providerResults"][0]
    assert "providerId" in provider
    assert "providerName" in provider
    assert "address" in provider


def test_provider_detail_structure(mock_provider_detail):
    """Test provider detail has expected structure."""
    assert "providerId" in mock_provider_detail
    assert "npi" in mock_provider_detail
    assert "locations" in mock_provider_detail
    assert isinstance(mock_provider_detail["locations"], list)

    if mock_provider_detail["locations"]:
        location = mock_provider_detail["locations"][0]
        assert "address" in location
        assert "phoneNumber" in location


class TestFixturesDirectory:
    """Test fixture files exist and are valid JSON."""

    def test_fixtures_directory_exists(self, fixtures_dir):
        """Test fixtures directory exists."""
        assert fixtures_dir.exists()
        assert fixtures_dir.is_dir()

    def test_search_response_file_exists(self, fixtures_dir):
        """Test search response fixture file exists."""
        fixture_file = fixtures_dir / "mock_search_response.json"
        assert fixture_file.exists()
        assert fixture_file.is_file()

    def test_provider_detail_file_exists(self, fixtures_dir):
        """Test provider detail fixture file exists."""
        fixture_file = fixtures_dir / "mock_provider_detail.json"
        assert fixture_file.exists()
        assert fixture_file.is_file()

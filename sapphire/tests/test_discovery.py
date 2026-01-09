"""Tests for Sapphire discovery phase."""

import json
import pytest
from pathlib import Path

from sapphire.phases.discovery import (
    GeoCircle,
    load_geo_codes,
    extract_provider_ids,
    has_provider_ids,
    build_facets_url,
    DiscoveryConfig,
    DiscoveryResult,
)
from sapphire.config.schema import (
    SapphireProjectConfig,
    ProjectMetadata,
    SiteConfig,
    NetworkConfig,
    CoverageConfig,
    APIConfig,
    StorageBackend,
)


class TestGeoCircle:
    """Tests for GeoCircle dataclass."""

    def test_basic_geocircle(self):
        """Create a basic GeoCircle."""
        circle = GeoCircle(
            state="IL",
            lat=40.0,
            lng=-89.0,
            radius=100,
            geo_num=1,
        )
        assert circle.state == "IL"
        assert circle.lat == 40.0
        assert circle.lng == -89.0
        assert circle.radius == 100

    def test_default_geo_num(self):
        """Default geo_num is 0."""
        circle = GeoCircle(state="IL", lat=40.0, lng=-89.0, radius=100)
        assert circle.geo_num == 0


class TestLoadGeoCodes:
    """Tests for load_geo_codes function."""

    def test_load_new_format(self, temp_dir, sample_geo_codes):
        """Load geo codes in new format."""
        geo_dir = temp_dir / "geo_codes"
        geo_dir.mkdir()
        (geo_dir / "small.json").write_text(json.dumps(sample_geo_codes))

        result = load_geo_codes(temp_dir, "small")

        assert "IL" in result
        assert len(result["IL"]) == 1
        circle = result["IL"][0]
        assert circle.state == "IL"
        assert circle.lat == 40.0793621
        assert circle.lng == -89.1681558
        assert circle.radius == 240

    def test_load_legacy_format(self, temp_dir, sample_geo_codes_legacy):
        """Load geo codes in legacy format."""
        geo_dir = temp_dir / "geo_codes"
        geo_dir.mkdir()
        (geo_dir / "complete.json").write_text(json.dumps(sample_geo_codes_legacy))

        result = load_geo_codes(temp_dir, "complete")

        assert "IL" in result
        assert len(result["IL"]) == 1
        circle = result["IL"][0]
        assert circle.state == "IL"
        assert circle.lat == 40.0793621
        assert circle.radius == 240

    def test_load_missing_file(self, temp_dir):
        """Missing file returns empty dict."""
        result = load_geo_codes(temp_dir, "nonexistent")
        assert result == {}

    def test_load_multiple_states(self, temp_dir):
        """Load geo codes for multiple states."""
        geo_data = {
            "geo_codes": [
                {"state": "IL", "coords": [40.0, -89.0], "radius": 100, "geo_num": 1},
                {"state": "IL", "coords": [41.0, -88.0], "radius": 50, "geo_num": 2},
                {"state": "IN", "coords": [39.0, -86.0], "radius": 100, "geo_num": 3},
            ]
        }
        geo_dir = temp_dir / "geo_codes"
        geo_dir.mkdir()
        (geo_dir / "small.json").write_text(json.dumps(geo_data))

        result = load_geo_codes(temp_dir, "small")

        assert "IL" in result
        assert "IN" in result
        assert len(result["IL"]) == 2
        assert len(result["IN"]) == 1


class TestExtractProviderIds:
    """Tests for extract_provider_ids function."""

    def test_extract_valid_ids(self):
        """Extract provider IDs from valid response."""
        data = {
            "facets": {
                "provider_id": [
                    {"value": "123"},
                    {"value": "456"},
                    {"value": "789"},
                ]
            }
        }
        result = extract_provider_ids(data)
        assert result == ["123", "456", "789"]

    def test_extract_empty_facets(self):
        """Empty facets returns empty list."""
        data = {"facets": {"provider_id": []}}
        result = extract_provider_ids(data)
        assert result == []

    def test_extract_missing_facets(self):
        """Missing facets returns empty list."""
        data = {}
        result = extract_provider_ids(data)
        assert result == []

    def test_extract_invalid_structure(self):
        """Invalid structure returns empty list."""
        data = {"facets": "invalid"}
        result = extract_provider_ids(data)
        assert result == []

    def test_extract_filters_empty_values(self):
        """Empty values are filtered out."""
        data = {
            "facets": {
                "provider_id": [
                    {"value": "123"},
                    {"value": ""},
                    {"value": None},
                    {"value": "456"},
                ]
            }
        }
        result = extract_provider_ids(data)
        assert result == ["123", "456"]


class TestHasProviderIds:
    """Tests for has_provider_ids function."""

    def test_has_ids_true(self):
        """Returns True when provider IDs exist."""
        data = {
            "facets": {
                "provider_id": [{"value": "123"}]
            }
        }
        assert has_provider_ids(data) is True

    def test_has_ids_false_empty(self):
        """Returns False when provider IDs empty."""
        data = {"facets": {"provider_id": []}}
        assert has_provider_ids(data) is False

    def test_has_ids_false_missing(self):
        """Returns False when facets missing."""
        data = {}
        assert has_provider_ids(data) is False


class TestBuildFacetsUrl:
    """Tests for build_facets_url function."""

    @pytest.fixture
    def sample_config(self):
        """Create sample config for URL building."""
        return SapphireProjectConfig(
            project=ProjectMetadata(name="Test", slug="test"),
            site=SiteConfig(
                domain="test.providerfinderonline.com",
                ci="test-ci",
            ),
            networks=[
                NetworkConfig(id="210000001", name="Test Network", state="IL"),
            ],
            coverage=CoverageConfig(states=["IL"]),
            api=APIConfig(
                common_params={"locale": "en", "data_language": "en"},
            ),
        )

    def test_build_url_structure(self, sample_config):
        """URL has correct structure."""
        network = sample_config.networks[0]
        geo = GeoCircle(state="IL", lat=40.0, lng=-89.0, radius=100, geo_num=1)

        url = build_facets_url(sample_config, network, geo)

        assert url.startswith("https://test.providerfinderonline.com")
        assert "/api/providers/facets.json" in url
        assert "network_id=210000001" in url
        assert "geo_location=40.0%2C-89.0" in url or "geo_location=40.0,-89.0" in url
        assert "radius=100" in url

    def test_build_url_fulltext(self, sample_config):
        """URL includes fulltext=*."""
        network = sample_config.networks[0]
        geo = GeoCircle(state="IL", lat=40.0, lng=-89.0, radius=100)

        url = build_facets_url(sample_config, network, geo)

        assert "fulltext=%2A" in url or "fulltext=*" in url

    def test_build_url_provider_id_facet(self, sample_config):
        """URL requests unlimited provider IDs."""
        network = sample_config.networks[0]
        geo = GeoCircle(state="IL", lat=40.0, lng=-89.0, radius=100)

        url = build_facets_url(sample_config, network, geo)

        # Should have facet[provider_id[limit]]=-1
        assert "provider_id" in url
        assert "-1" in url


class TestDiscoveryConfig:
    """Tests for DiscoveryConfig dataclass."""

    def test_defaults(self):
        """Default config values."""
        config = DiscoveryConfig()
        assert config.geo_strategy == "dual"
        assert config.storage_backend == StorageBackend.SQLITE

    def test_custom_values(self):
        """Custom config values."""
        config = DiscoveryConfig(
            geo_strategy="small",
            storage_backend=StorageBackend.JSONL,
        )
        assert config.geo_strategy == "small"
        assert config.storage_backend == StorageBackend.JSONL


class TestDiscoveryResult:
    """Tests for DiscoveryResult dataclass."""

    def test_basic_result(self):
        """Create basic discovery result."""
        result = DiscoveryResult(
            total_providers=1000,
            providers_by_network={"Net1": 500, "Net2": 500},
            providers_by_state={"IL": 1000},
            geo_circles_queried=10,
            output_file=Path("/tmp/output.json"),
        )
        assert result.total_providers == 1000
        assert len(result.providers_by_network) == 2

    def test_duration_default(self):
        """Duration defaults to 0."""
        result = DiscoveryResult(
            total_providers=0,
            providers_by_network={},
            providers_by_state={},
            geo_circles_queried=0,
            output_file=Path("/tmp/output.json"),
        )
        assert result.duration_seconds == 0.0

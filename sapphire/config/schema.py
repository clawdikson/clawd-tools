"""
Sapphire Project Configuration Schema.

Pydantic models for validating YAML project configurations.
Adapted from HealthSparq patterns for Sapphire (ProviderFinderOnline) sites.
"""

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class StorageBackend(str, Enum):
    """Storage backend types for raw data.

    Attributes:
        JSON_FILES: Individual JSON files on disk (default, human-readable)
        SQLITE: SQLite database (15x faster writes, ACID guarantees)
        JSONL: Line-delimited JSON file (append-only, streaming)
        AUTO: Auto-detect from path (falls back to JSON_FILES)
    """

    JSON_FILES = "json_files"
    SQLITE = "sqlite"
    JSONL = "jsonl"
    AUTO = "auto"


class ProjectMetadata(BaseModel):
    """Project metadata."""

    name: str = Field(..., min_length=1, description="Full project name")
    slug: str = Field(..., min_length=1, description="Project slug (used in CLI)")
    description: Optional[str] = Field(default=None, description="Project description")
    version: str = Field(default="1.0", min_length=1, description="Config schema version")


class SiteConfig(BaseModel):
    """Sapphire site configuration."""

    domain: str = Field(
        ..., min_length=1, description="Sapphire domain (e.g., molina.sapphirethreesixtyfive.com)"
    )
    ci: str = Field(..., min_length=1, description="Client identifier")
    config_signature: str = Field(
        default="{2}-{1104}-{}",
        description="Site-specific config signature pattern",
    )
    api_version: str = Field(default="v1", description="API version")


class NetworkConfig(BaseModel):
    """Individual network configuration for state-based network mapping."""

    id: str = Field(..., min_length=1, description="Network ID")
    name: str = Field(..., min_length=1, description="Human-readable network name")
    state: str = Field(..., min_length=2, max_length=2, description="2-character state code")
    enabled: bool = Field(default=True, description="Whether to scrape this network")

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        """Validate and uppercase state code."""
        return v.upper()


class CoverageConfig(BaseModel):
    """Geographic coverage configuration."""

    states: list[str] = Field(..., min_length=1, description="List of state codes")
    geo_strategy: Literal["small", "complete", "dual"] = Field(
        default="dual",
        description="Geographic search strategy: small (dense circles), complete (state-wide), dual (both)",
    )

    @field_validator("states")
    @classmethod
    def validate_states(cls, v: list[str]) -> list[str]:
        """Validate all state codes are valid US state abbreviations."""
        valid_states = {
            "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL",
            "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
            "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
            "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
            "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
        }
        result = []
        for state in v:
            upper_state = state.upper()
            if upper_state not in valid_states:
                raise ValueError(f"Invalid state code: {state}")
            result.append(upper_state)
        return result


class APIConfig(BaseModel):
    """Sapphire API configuration."""

    endpoints: dict[str, str] = Field(
        default_factory=lambda: {
            "facets": "/api/providers/facets.json",
            "summary": "/api/providers/summary.json",
            "locations": "/api/providers/{provider_id}/locations/{location_id}/other_locations.json",
            "affiliations": "/api/providers/{provider_id}/locations/{location_id}/affiliations.json",
            "networks": "/api/providers/{provider_id}/locations/{location_id}/networks_accepted.json",
        },
        description="API endpoint patterns",
    )
    common_params: dict[str, str] = Field(
        default_factory=lambda: {
            "locale": "en",
            "data_language": "en",
            "account_id": "2",
        },
        description="Common API parameters",
    )


class ConcurrencyConfig(BaseModel):
    """Concurrency and rate limiting configuration."""

    max_workers: int = Field(
        default=10, ge=1, le=50, description="Max Playwright worker threads"
    )
    max_pages: int = Field(
        default=2, ge=1, le=10, description="Max browser pages (round-robin)"
    )
    batch_size: int = Field(
        default=1000, ge=100, le=10000, description="Providers per batch"
    )
    retry_attempts: int = Field(
        default=5, ge=1, le=10, description="Max retry attempts"
    )
    retry_delay_ms: int = Field(
        default=1000, ge=100, description="Delay between retries in ms"
    )
    page_refresh_interval: int = Field(
        default=5000, ge=1000, description="Requests before page refresh"
    )
    request_timeout_ms: int = Field(
        default=120000, ge=10000, description="Request timeout in ms"
    )


class OutputConfig(BaseModel):
    """Output directory configuration."""

    base_dir: Optional[str] = Field(
        default=None, description="Override default output directory"
    )
    raw_subdir: str = Field(
        default="raw", min_length=1, description="Raw output subdirectory"
    )
    processed_subdir: str = Field(
        default="processed", min_length=1, description="Processed output subdirectory"
    )
    storage_backend: StorageBackend = Field(
        default=StorageBackend.SQLITE,
        description="Storage backend: sqlite (default), json_files, jsonl, auto",
    )


class NormalizeConfig(BaseModel):
    """Normalization configuration."""

    mapper: Optional[str] = Field(
        default=None,
        description="Custom mapper module path (e.g., sapphire.mappers.bcbs_mn.normalize_provider)",
    )
    field_overrides: dict[str, str] = Field(
        default_factory=dict,
        description="Field value overrides (e.g., network_name_prefix)",
    )


class ProxyConfig(BaseModel):
    """Proxy configuration."""

    server: str = Field(
        default="http://gw.dataimpulse.com:10001",
        description="Proxy server URL",
    )
    location: str = Field(
        default="us",
        description="Proxy location (us, ca, uk)",
    )


class SessionConfig(BaseModel):
    """Browser session configuration."""

    browser_type: Literal["camoufox", "playwright", "patchright"] = Field(
        default="camoufox",
        description="Browser backend type",
    )
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)


class SapphireProjectConfig(BaseModel):
    """Complete Sapphire project configuration."""

    project: ProjectMetadata
    site: SiteConfig
    networks: list[NetworkConfig] = Field(default_factory=list)
    coverage: CoverageConfig
    api: APIConfig = Field(default_factory=APIConfig)
    concurrency: ConcurrencyConfig = Field(default_factory=ConcurrencyConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    normalize: NormalizeConfig = Field(default_factory=NormalizeConfig)
    session: SessionConfig = Field(default_factory=SessionConfig)

    def get_networks_for_state(self, state: str) -> list[NetworkConfig]:
        """Get networks configured for a specific state."""
        state_upper = state.upper()
        return [n for n in self.networks if n.state == state_upper and n.enabled]

    def get_all_network_ids(self) -> list[str]:
        """Get all enabled network IDs."""
        return [n.id for n in self.networks if n.enabled]

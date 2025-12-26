"""
HealthSparq Project Configuration Schema.

Pydantic models for validating YAML project configurations.
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class PlanConfig(BaseModel):
    """Individual plan configuration."""

    product_code: str = Field(..., description="HealthSparq product code")
    name: str = Field(..., description="Human-readable plan name")
    insurer_code: Optional[str] = Field(
        default=None, description="API insurer code (defaults to site.insurer_code)"
    )
    brand_code: Optional[str] = Field(
        default=None, description="API brand code (defaults to site.brand_code)"
    )
    state: Optional[str] = Field(
        default=None, description="State-specific plan (e.g., 'IA' for Iowa-only plans)"
    )
    enabled: bool = Field(default=True, description="Whether to scrape this plan")


class SiteConfig(BaseModel):
    """HealthSparq site configuration."""

    domain: str = Field(
        ..., description="HealthSparq domain (e.g., excellusbcbs.healthsparq.com)"
    )
    brand_code: str = Field(..., description="Brand code for API auth")
    insurer_code: str = Field(..., description="Insurer code for API auth")
    api_version: str = Field(default="v4", description="API version (v3, v4)")


class CoverageConfig(BaseModel):
    """Geographic coverage configuration."""

    states: list[str] = Field(..., min_length=1, description="List of state codes")
    counties: Optional[dict[str, list[str]]] = Field(
        default=None, description="Optional county overrides per state"
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
        for state in v:
            if state not in valid_states:
                raise ValueError(f"Invalid state code: {state}")
        return v


class PaginationConfig(BaseModel):
    """Pagination configuration for adaptive search strategy."""

    # Page/size combinations to use: [(page, size), ...]
    # Default: fetch page 1 with 200, then page 3 with 100 (offset pagination)
    page_sizes: list[tuple[int, int]] = Field(
        default=[(1, 200), (3, 100)],
        description="Page/size tuples for pagination strategy",
    )

    # Result thresholds that trigger additional requests
    threshold_second_page: int = Field(
        default=200,
        ge=0,
        description="Results above this trigger second page fetch",
    )
    threshold_reverse_sort: int = Field(
        default=300,
        ge=0,
        description="Results above this trigger reverse sort fetch",
    )
    threshold_reverse_second: int = Field(
        default=500,
        ge=0,
        description="Results above this trigger reverse sort second page",
    )
    threshold_max_per_filter: int = Field(
        default=600,
        ge=0,
        description="Max results per filter before drilling down",
    )

    # Sort types for extended searches
    sort_types: list[str] = Field(
        default=["NAME_ASC", "NAME_DESC", "BEST_MATCH", "DISTANCE"],
        description="Sort orders to use for comprehensive coverage",
    )


class FilterConfig(BaseModel):
    """Search filter configuration."""

    provider_types: list[str] = Field(
        default=["Facility", "Group", "Pharmacy", "Dental", "Physician", "Other"],
        description="Provider types to search",
    )
    specialties: Optional[list[str]] = Field(
        default=None, description="Specialty filters"
    )
    languages: Optional[list[str]] = Field(default=None, description="Language filters")
    gender_filters: Optional[list[str]] = Field(
        default=None, description="Gender filters"
    )
    organization_filters: Optional[list[str]] = Field(
        default=None, description="Organization filters"
    )

    # Organization filter keys for drilling down large result sets
    org_filter_keys: list[str] = Field(
        default=[
            "PROVIDER_TYPE:FAC",
            "PROVIDER_TYPE:GRP",
            "PROVIDER_TYPE:OTHR",
            "PROVIDER_TYPE:SUP",
            "PROVIDER_TYPE:PHARM",
            "PROVIDER_TYPE:CNSLR",
            "PROVIDER_TYPE:DNTL",
            "PROVIDER_TYPE:OTHMED",
            "PROVIDER_TYPE:OPROFF",
            "PROVIDER_TYPE:PHYAST",
            "PROVIDER_TYPE:PHYSC",
        ],
        description="Organization filter keys for drilling down",
    )

    # Individual provider filter keys (subset of org filters)
    individual_filter_keys: list[str] = Field(
        default=[
            "PROVIDER_TYPE:CNSLR",
            "PROVIDER_TYPE:DNTL",
            "PROVIDER_TYPE:OTHMED",
            "PROVIDER_TYPE:OPROFF",
            "PROVIDER_TYPE:PHYAST",
            "PROVIDER_TYPE:PHYSC",
        ],
        description="Individual provider filter keys (support gender drilling)",
    )

    # Gender filter keys
    gender_filter_keys: list[str] = Field(
        default=["GENDER_V2:F", "GENDER_V2:M", "GENDER_V2:U"],
        description="Gender filter keys",
    )


class ConcurrencyConfig(BaseModel):
    """Concurrency and rate limiting configuration."""

    max_workers: int = Field(
        default=100, ge=1, le=500, description="Max concurrent API requests"
    )
    max_browsers: int = Field(
        default=1, ge=1, le=50, description="Max browser instances"
    )
    request_delay_ms: int = Field(
        default=0, ge=0, description="Delay between requests in ms"
    )
    retry_attempts: int = Field(
        default=3, ge=1, le=10, description="Max retry attempts"
    )
    retry_delay_ms: int = Field(
        default=1000, ge=100, description="Delay between retries"
    )


class OutputConfig(BaseModel):
    """Output directory configuration."""

    base_dir: Optional[str] = Field(
        default=None, description="Override default output directory"
    )
    raw_subdir: str = Field(default="raw", description="Raw output subdirectory")
    processed_subdir: str = Field(
        default="processed", description="Processed output subdirectory"
    )


class ProjectMetadata(BaseModel):
    """Project metadata."""

    name: str = Field(..., description="Full project name")
    slug: str = Field(..., description="Project slug (used in CLI)")
    description: Optional[str] = Field(default=None, description="Project description")
    version: str = Field(default="1.0", description="Config schema version")


class HealthSparqProjectConfig(BaseModel):
    """Complete project configuration."""

    project: ProjectMetadata
    site: SiteConfig
    plans: list[PlanConfig] = Field(..., min_length=1)
    coverage: CoverageConfig
    filters: FilterConfig = Field(default_factory=FilterConfig)
    pagination: PaginationConfig = Field(default_factory=PaginationConfig)
    concurrency: ConcurrencyConfig = Field(default_factory=ConcurrencyConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)

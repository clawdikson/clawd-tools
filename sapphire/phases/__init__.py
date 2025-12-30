"""Sapphire pipeline phases.

Phase 1 (Discovery): Geographic provider ID discovery via facet queries
Phase 2 (Details): Provider detail extraction (summary, locations, affiliations, networks)
Phase 3 (Normalize): Normalization with mapper injection, NPI deduplication
Phase 4 (QA): Schema validation + comparison with previous run
Phase 5 (Report): Excel reports + sample generation
"""

# Phase implementations - uncomment Phase 4/5 as they're built
# from sapphire.phases.qa import run_qa, QAResult
# from sapphire.phases.report import run_report, ReportResult

from sapphire.phases.discovery import (
    DiscoveryConfig,
    DiscoveryResult,
    GeoCircle,
    load_geo_codes,
    load_geo_codes_from_config,
    run_discovery,
    run_discovery_sync,
)

from sapphire.phases.details import (
    DetailsConfig,
    DetailsResult,
    ProviderData,
    copy_missing_from_previous,
    load_provider_ids_from_phase1,
    run_details,
    run_details_sync,
)

from sapphire.phases.normalize import (
    NormalizeConfig,
    NormalizeResult,
    default_sapphire_mapper,
    run_normalize,
    run_normalize_sync,
)

__all__ = [
    # Phase 1: Discovery
    "DiscoveryConfig",
    "DiscoveryResult",
    "GeoCircle",
    "load_geo_codes",
    "load_geo_codes_from_config",
    "run_discovery",
    "run_discovery_sync",
    # Phase 2: Details
    "DetailsConfig",
    "DetailsResult",
    "ProviderData",
    "run_details",
    "run_details_sync",
    "load_provider_ids_from_phase1",
    "copy_missing_from_previous",
    # Phase 3: Normalize
    "NormalizeConfig",
    "NormalizeResult",
    "default_sapphire_mapper",
    "run_normalize",
    "run_normalize_sync",
]

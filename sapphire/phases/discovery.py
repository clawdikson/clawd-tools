"""Phase 1: Provider ID Discovery via Geographic Facet Queries.

Discovers provider IDs by querying Sapphire API facets endpoint with
geographic circles across all covered states and networks.

Key features:
- State-aware network selection (only query networks for covered states)
- Dual geo-strategy: small circles first, then complete for catch-all
- Progress logging at 10% intervals
- Retry logic with exponential backoff (tenacity)
- BoundedSet for memory-safe deduplication
- DataStore abstraction for flexible storage backends
"""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Optional
from urllib.parse import urlencode

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from core.io import BoundedSet, create_store, DataStore
from sapphire.config.schema import (
    SapphireProjectConfig,
    StorageBackend,
    NetworkConfig,
)
from sapphire.core.exceptions import APIError
from sapphire.core.storage import create_phase_store

# Use core.logging if available, fallback to stdlib
try:
    from core.logging import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from sapphire.core.sapphire_api import SapphireAPI


# =============================================================================
# Configuration Dataclasses
# =============================================================================


@dataclass
class DiscoveryConfig:
    """Configuration for Phase 1 discovery.

    Attributes:
        geo_strategy: Geographic search strategy
            - "small": Dense coverage circles only
            - "complete": State-wide coverage circles only
            - "dual": Both small and complete circles (recommended)
        output_dir: Base output directory (e.g., Path("20251230"))
        max_workers: Maximum concurrent workers (follows HealthSparq pattern)
        storage_backend: Storage backend for raw results
    """

    geo_strategy: Literal["small", "complete", "dual"] = "dual"
    output_dir: Optional[Path] = None
    max_workers: Optional[int] = None
    storage_backend: StorageBackend = StorageBackend.SQLITE

    def __post_init__(self) -> None:
        """Set defaults after initialization (HealthSparq pattern)."""
        if self.output_dir is None:
            self.output_dir = Path(".")


@dataclass
class DiscoveryResult:
    """Result of Phase 1 discovery.

    Attributes:
        total_providers: Total unique providers discovered
        providers_by_network: Provider counts per network ID
        providers_by_state: Provider counts per state
        geo_circles_queried: Number of geographic circles processed
        output_file: Path to the provider_ids_network_map output
        duration_seconds: Elapsed time in seconds
        started_at: ISO timestamp when phase started
        completed_at: ISO timestamp when phase completed
    """

    total_providers: int
    providers_by_network: dict[str, int]
    providers_by_state: dict[str, int]
    geo_circles_queried: int
    output_file: Path
    duration_seconds: float = 0.0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


# =============================================================================
# Geographic Data Loading
# =============================================================================


@dataclass
class GeoCircle:
    """Geographic circle for provider discovery.

    Attributes:
        state: 2-character state code
        lat: Latitude
        lng: Longitude
        radius: Radius in miles
        geo_num: Circle identifier for logging
    """

    state: str
    lat: float
    lng: float
    radius: int
    geo_num: int = 0


def load_geo_codes(
    data_dir: Path, geo_type: Literal["small", "complete"]
) -> dict[str, list[GeoCircle]]:
    """Load geographic circles from JSON files.

    Supports two JSON formats:
    1. New format: {"geo_codes": [{"state": "IL", "coords": [lat, lng], "radius": 100}]}
    2. Legacy format: {"IL": {"coords": [{"lat": 40.0, "lng": -89.0, "radius": 100}]}}

    Args:
        data_dir: Path to sapphire/data directory
        geo_type: Type of circles to load ("small" or "complete")

    Returns:
        Dictionary mapping state codes to lists of GeoCircle objects
    """
    geo_file = data_dir / "geo_codes" / f"{geo_type}.json"

    if not geo_file.exists():
        logger.warning(f"Geo codes file not found: {geo_file}")
        return {}

    with open(geo_file, encoding="utf-8") as f:
        raw_data = json.load(f)

    result: dict[str, list[GeoCircle]] = {}

    # New format: {"geo_codes": [{"state": "IL", "coords": [lat, lng], "radius": 100}]}
    if "geo_codes" in raw_data:
        for entry in raw_data["geo_codes"]:
            state = entry.get("state", "").upper()
            coords = entry.get("coords", [])
            radius = entry.get("radius", 100)
            geo_num = entry.get("geo_num", 0)

            if not state or len(coords) < 2:
                continue

            circle = GeoCircle(
                state=state,
                lat=coords[0],
                lng=coords[1],
                radius=radius,
                geo_num=geo_num,
            )

            if state not in result:
                result[state] = []
            result[state].append(circle)
        return result

    # Legacy format: {"IL": {"coords": [{"lat": 40.0, "lng": -89.0, "radius": 100}]}}
    geo_num = 1
    for state, state_data in raw_data.items():
        circles = []
        coords = state_data.get("coords", [])
        for coord in coords:
            circles.append(
                GeoCircle(
                    state=state.upper(),
                    lat=coord.get("lat", 0),
                    lng=coord.get("lng", 0),
                    radius=coord.get("radius", 100),
                    geo_num=geo_num,
                )
            )
            geo_num += 1
        if circles:
            result[state.upper()] = circles

    return result


def load_geo_codes_from_config(
    config: SapphireProjectConfig,
) -> tuple[dict[str, list[GeoCircle]], dict[str, list[GeoCircle]]]:
    """Load geo codes based on project configuration.

    Args:
        config: Project configuration

    Returns:
        Tuple of (small_circles, complete_circles) by state
    """
    data_dir = Path(__file__).parent.parent / "data"

    small_circles: dict[str, list[GeoCircle]] = {}
    complete_circles: dict[str, list[GeoCircle]] = {}

    geo_strategy = config.coverage.geo_strategy

    if geo_strategy in ("small", "dual"):
        small_circles = load_geo_codes(data_dir, "small")

    if geo_strategy in ("complete", "dual"):
        complete_circles = load_geo_codes(data_dir, "complete")

    # Filter to only covered states
    covered_states = set(config.coverage.states)

    small_circles = {k: v for k, v in small_circles.items() if k in covered_states}
    complete_circles = {
        k: v for k, v in complete_circles.items() if k in covered_states
    }

    return small_circles, complete_circles


# =============================================================================
# API Request Building
# =============================================================================


def build_facets_url(
    config: SapphireProjectConfig,
    network: NetworkConfig,
    geo: GeoCircle,
) -> str:
    """Build the facets API URL for a network and geo location.

    Args:
        config: Project configuration
        network: Network configuration
        geo: Geographic circle

    Returns:
        Full URL for facets API request
    """
    geo_location = f"{geo.lat},{geo.lng}"

    params = {
        **config.api.common_params,
        "fulltext": "*",
        "network_id": network.id,
        "geo_location": geo_location,
        "page": "1",
        "radius": str(geo.radius),
        "sort": "distance asc, has_ep002 desc",
        "facet[provider_id[value]]": "true",
        "facet[provider_id[limit]]": "-1",
        "transaction_id": str(uuid.uuid4()),
        "ci": config.site.ci,
    }

    base_url = f"https://{config.site.domain}{config.api.endpoints['facets']}"
    return f"{base_url}?{urlencode(params)}"


# =============================================================================
# Provider Data Extraction
# =============================================================================


def extract_provider_ids(data: dict[str, Any]) -> list[str]:
    """Extract provider IDs from facets API response.

    Args:
        data: API response data

    Returns:
        List of provider ID strings
    """
    if not data or not isinstance(data, dict):
        return []

    facets = data.get("facets", {})
    if not isinstance(facets, dict):
        return []

    providers = facets.get("provider_id", [])
    if not isinstance(providers, list):
        return []

    return [str(p.get("value", "")) for p in providers if isinstance(p, dict) and p.get("value")]


def has_provider_ids(data: dict[str, Any]) -> bool:
    """Check if response data contains provider IDs."""
    provider_ids = data.get("facets", {}).get("provider_id", [])
    return bool(provider_ids and len(provider_ids) > 0)


# =============================================================================
# Core Discovery Logic
# =============================================================================


class DiscoveryProcessor:
    """Processes geographic discovery of provider IDs.

    Handles the core logic of querying the facets API across
    geographic circles and networks, with caching and deduplication.
    """

    def __init__(
        self,
        config: SapphireProjectConfig,
        store: DataStore,
        api: "SapphireAPI",
    ):
        self.config = config
        self.store = store
        self.api = api

        # Provider-to-network mapping
        self.provider_network_map: dict[str, list[str]] = {}

        # Provider counts per network (uses set for unique counting)
        self.network_counts: dict[str, set[str]] = {}

        # Provider counts per state
        self.state_counts: dict[str, set[str]] = {}

        # Memory-safe deduplication
        self.seen_providers = BoundedSet(max_size=500_000)

        # Tracking
        self.circles_processed = 0
        self.total_circles = 0

    def _get_cache_key(
        self, network: NetworkConfig, geo: GeoCircle, geo_type: str
    ) -> str:
        """Generate cache key for a network/geo combination."""
        return f"provider_ids_{network.id}_loc{geo.geo_num}_{geo_type}.json"

    async def _fetch_provider_data(
        self,
        network: NetworkConfig,
        geo: GeoCircle,
        geo_type: str,
    ) -> dict[str, Any]:
        """Fetch provider data from cache or API.

        Args:
            network: Network configuration
            geo: Geographic circle
            geo_type: "small" or "complete"

        Returns:
            API response data
        """
        cache_key = self._get_cache_key(network, geo, geo_type)

        # Check cache first
        if self.store.exists(cache_key):
            cached_data = self.store.get(cache_key)
            if cached_data and has_provider_ids(cached_data):
                logger.debug(f"Cache hit: {cache_key}")
                return cached_data

        # Build URL and fetch from API
        url = build_facets_url(self.config, network, geo)
        logger.debug(f"Requesting {url}")

        @retry(
            stop=stop_after_attempt(self.config.concurrency.retry_attempts),
            wait=wait_exponential(
                multiplier=1,
                min=self.config.concurrency.retry_delay_ms / 1000,
                max=10,
            ),
            retry=retry_if_exception_type((ConnectionError, TimeoutError, APIError)),
            reraise=True,
        )
        async def _fetch_with_retry() -> dict[str, Any]:
            data = await self.api.request(url)
            if data is None:
                raise APIError("API returned None", endpoint=url)
            if data.get("error"):
                raise APIError(
                    f"API error: {data.get('statusText', 'Unknown')}",
                    status_code=data.get("status"),
                    endpoint=url,
                )
            return data

        try:
            data = await _fetch_with_retry()

            # Validate and save
            if has_provider_ids(data):
                self.store.put(cache_key, data)
                provider_count = len(data.get("facets", {}).get("provider_id", []))
                logger.info(
                    f"Fetched {provider_count} providers for network {network.id} "
                    f"(geo {geo.geo_num}, {geo_type})"
                )
            else:
                logger.warning(
                    f"No provider IDs found for network {network.id} "
                    f"(geo {geo.geo_num}, {geo_type})"
                )
                data = {"facets": {"provider_id": []}}

            return data

        except Exception as e:
            logger.error(
                f"Failed to fetch data for network {network.id} "
                f"(geo {geo.geo_num}, {geo_type}): {e}"
            )
            return {"facets": {"provider_id": []}}

    def _process_provider_facets(
        self,
        data: dict[str, Any],
        network: NetworkConfig,
        state: str,
    ) -> int:
        """Process provider facets and update tracking structures.

        Args:
            data: API response data
            network: Network configuration
            state: State code

        Returns:
            Number of new providers processed
        """
        provider_ids = extract_provider_ids(data)

        # Initialize tracking sets if needed
        if network.name not in self.network_counts:
            self.network_counts[network.name] = set()
        if state not in self.state_counts:
            self.state_counts[state] = set()

        new_providers = 0
        for provider_id in provider_ids:
            if not provider_id:
                continue

            # Track by network and state
            self.network_counts[network.name].add(provider_id)
            self.state_counts[state].add(provider_id)

            # Build provider-to-network mapping
            if provider_id not in self.provider_network_map:
                self.provider_network_map[provider_id] = []

            if network.id not in self.provider_network_map[provider_id]:
                self.provider_network_map[provider_id].append(network.id)
                new_providers += 1

            # Memory-safe deduplication tracking
            self.seen_providers.add(provider_id)

        return new_providers

    async def process_geo_location(
        self,
        geo: GeoCircle,
        geo_type: str,
    ) -> None:
        """Process a single geographic location across all relevant networks.

        Args:
            geo: Geographic circle
            geo_type: "small" or "complete"
        """
        state = geo.state
        networks = self.config.get_networks_for_state(state)

        if not networks:
            logger.warning(f"No networks configured for state {state}")
            return

        logger.info(
            f"Location {geo.geo_num} ({geo_type}): {state} - "
            f"{geo.lat},{geo.lng} ({geo.radius}mi) - {len(networks)} networks"
        )

        for network in networks:
            try:
                data = await self._fetch_provider_data(network, geo, geo_type)
                provider_count = self._process_provider_facets(data, network, state)
                logger.debug(
                    f"  Network {network.id} ({network.name}): "
                    f"{len(extract_provider_ids(data))} providers"
                )
            except Exception as e:
                logger.error(f"  Error processing network {network.id}: {e}")
                continue

        self.circles_processed += 1

        # Progress logging at 10% intervals
        if self.total_circles > 0:
            progress = (self.circles_processed / self.total_circles) * 100
            if progress % 10 < (1 / self.total_circles) * 100:
                logger.info(f"Progress: {progress:.0f}% ({self.circles_processed}/{self.total_circles})")

    async def run(
        self,
        small_circles: dict[str, list[GeoCircle]],
        complete_circles: dict[str, list[GeoCircle]],
    ) -> None:
        """Run discovery across all geographic circles.

        Args:
            small_circles: Small coverage circles by state
            complete_circles: Complete coverage circles by state
        """
        # Calculate total circles
        total_small = sum(len(circles) for circles in small_circles.values())
        total_complete = sum(len(circles) for circles in complete_circles.values())
        self.total_circles = total_small + total_complete

        logger.info(
            f"Starting discovery: {total_small} small + "
            f"{total_complete} complete = {self.total_circles} circles"
        )

        # Process small circles first
        if small_circles:
            logger.info("=" * 70)
            logger.info("PROCESSING SMALL CIRCLES")
            logger.info("=" * 70)

            for state, circles in sorted(small_circles.items()):
                for geo in circles:
                    await self.process_geo_location(geo, "small")

        # Process complete circles
        if complete_circles:
            logger.info("=" * 70)
            logger.info("PROCESSING COMPLETE CIRCLES")
            logger.info("=" * 70)

            for state, circles in sorted(complete_circles.items()):
                for geo in circles:
                    await self.process_geo_location(geo, "complete")

    def get_result_summary(self) -> tuple[dict[str, int], dict[str, int]]:
        """Get summary counts from discovery.

        Returns:
            Tuple of (providers_by_network, providers_by_state)
        """
        providers_by_network = {
            name: len(providers) for name, providers in self.network_counts.items()
        }
        providers_by_state = {
            state: len(providers) for state, providers in self.state_counts.items()
        }
        return providers_by_network, providers_by_state


# =============================================================================
# Public API
# =============================================================================


async def run_discovery(
    config: SapphireProjectConfig,
    curr_date: str,
    api: Optional["SapphireAPI"] = None,
    discovery_config: Optional[DiscoveryConfig] = None,
) -> DiscoveryResult:
    """Run Phase 1: Provider ID Discovery.

    Discovers provider IDs by querying Sapphire facets API with geographic
    circles across all covered states and networks.

    Args:
        config: Sapphire project configuration
        curr_date: Current date string (YYYYMMDD)
        api: SapphireAPI instance (required for actual API calls)
        discovery_config: Optional discovery configuration

    Returns:
        DiscoveryResult with discovery statistics

    Raises:
        ValueError: If api is None (required for actual discovery)
    """
    import time

    start_time = time.time()

    if discovery_config is None:
        discovery_config = DiscoveryConfig(
            geo_strategy=config.coverage.geo_strategy,
            output_dir=Path(curr_date),
            storage_backend=config.output.storage_backend,
        )

    # Load geo codes
    small_circles, complete_circles = load_geo_codes_from_config(config)

    # Validate we have data to process
    if not small_circles and not complete_circles:
        logger.warning("No geographic circles found for configured states")
        return DiscoveryResult(
            total_providers=0,
            providers_by_network={},
            providers_by_state={},
            geo_circles_queried=0,
            output_file=Path(curr_date) / "raw" / "provider_ids_network_map.json",
            duration_seconds=0.0,
        )

    if api is None:
        raise ValueError("SapphireAPI instance is required for discovery")

    # Create store for raw discovery results
    base_dir = Path(curr_date)
    with create_phase_store(
        base_dir,
        "provider_ids",
        discovery_config.storage_backend,
    ) as store:
        processor = DiscoveryProcessor(config, store, api)
        await processor.run(small_circles, complete_circles)

        # Get summary
        providers_by_network, providers_by_state = processor.get_result_summary()

        # Save provider-to-network mapping
        output_dir = base_dir / "raw"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "provider_ids_network_map.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(processor.provider_network_map, f, indent=2)

        logger.info(f"Saved provider-network mapping to {output_file}")

        # Print summary
        logger.info(f"\nTotal unique providers: {len(processor.provider_network_map)}")
        for network_name, count in sorted(providers_by_network.items()):
            logger.info(f"  Network: {network_name} - {count} providers")
        for state, count in sorted(providers_by_state.items()):
            logger.info(f"  State: {state} - {count} providers")

        duration = time.time() - start_time

        return DiscoveryResult(
            total_providers=len(processor.provider_network_map),
            providers_by_network=providers_by_network,
            providers_by_state=providers_by_state,
            geo_circles_queried=processor.circles_processed,
            output_file=output_file,
            duration_seconds=duration,
        )


def run_discovery_sync(
    config: SapphireProjectConfig,
    curr_date: str,
    api: Optional["SapphireAPI"] = None,
    discovery_config: Optional[DiscoveryConfig] = None,
) -> DiscoveryResult:
    """Synchronous wrapper for run_discovery.

    Args:
        config: Sapphire project configuration
        curr_date: Current date string (YYYYMMDD)
        api: SapphireAPI instance (required for actual API calls)
        discovery_config: Optional discovery configuration

    Returns:
        DiscoveryResult with discovery statistics
    """
    return asyncio.run(
        run_discovery(
            config=config,
            curr_date=curr_date,
            api=api,
            discovery_config=discovery_config,
        )
    )


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "DiscoveryConfig",
    "DiscoveryResult",
    "GeoCircle",
    "load_geo_codes",
    "load_geo_codes_from_config",
    "run_discovery",
    "run_discovery_sync",
]

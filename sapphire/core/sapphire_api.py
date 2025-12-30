"""
Sapphire API Wrapper.

High-level API wrapper for ProviderFinderOnline (Sapphire) sites.
Provides typed methods for facets, summary, affiliations, locations, and networks.

All configuration is injected via SapphireProjectConfig - no hardcoded domains
or API keys.

Usage:
    async with SapphireAPI(config, network_id, geo_location) as api:
        facets = await api.get_facets()
        providers = await api.get_summary(specialty_id="980000012")
        affiliations = await api.get_affiliations(provider_id, location_id)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
from uuid import uuid4

from sapphire.config.schema import SapphireProjectConfig
from sapphire.core.exceptions import APIError, SessionError
from sapphire.core.session import SapphireBrowserQueue, SapphireSessionConfig

# Use core.logging if available, fallback to stdlib
try:
    from core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class SapphireAPIConfig:
    """Configuration for Sapphire API wrapper.

    Extracted from SapphireProjectConfig for API-specific settings.
    """

    # Site configuration
    domain: str
    ci: str
    config_signature: str = "{2}-{1104}-{}"

    # Network and geo configuration
    network_id: str = ""
    geo_location: str = ""

    # API endpoints
    endpoints: Dict[str, str] = field(default_factory=lambda: {
        "facets": "/api/providers/facets.json",
        "summary": "/api/providers/summary.json",
        "locations": "/api/providers/{provider_id}/locations/{location_id}/other_locations.json",
        "affiliations": "/api/providers/{provider_id}/locations/{location_id}/affiliations.json",
        "networks": "/api/providers/{provider_id}/locations/{location_id}/networks_accepted.json",
    })

    # Common parameters for all requests
    common_params: Dict[str, str] = field(default_factory=lambda: {
        "locale": "en",
        "data_language": "en",
    })

    # Request settings
    max_retries: int = 5
    timeout_seconds: float = 120.0

    # API credentials (captured from browser or configured)
    api_key: Optional[str] = None

    @classmethod
    def from_project_config(
        cls,
        config: SapphireProjectConfig,
        network_id: str,
        geo_location: str,
    ) -> "SapphireAPIConfig":
        """Create API config from project configuration."""
        return cls(
            domain=config.site.domain,
            ci=config.site.ci,
            config_signature=config.site.config_signature,
            network_id=network_id,
            geo_location=geo_location,
            endpoints=config.api.endpoints,
            common_params=config.api.common_params,
            max_retries=config.concurrency.retry_attempts,
            timeout_seconds=config.concurrency.request_timeout_ms / 1000.0,
        )

    @property
    def base_url(self) -> str:
        """Base URL for API requests."""
        return f"https://{self.domain}"


class SapphireAPI:
    """
    High-level API wrapper for Sapphire (ProviderFinderOnline) sites.

    Provides typed methods for:
    - get_facets(): Specialty and filter categories
    - get_summary(): Provider search results
    - get_affiliations(): Group/hospital affiliations for a provider
    - get_locations(): Other practice locations for a provider
    - get_networks(): Networks accepted at a location

    Uses SapphireBrowserQueue for all requests to handle anti-bot measures.

    Usage:
        async with SapphireAPI(config, "210002020", "39.88,-88.83") as api:
            facets = await api.get_facets()
            providers = await api.get_summary(specialty_id="980000012", page=1)
    """

    def __init__(
        self,
        config: SapphireProjectConfig,
        network_id: str,
        geo_location: str,
        browser_queue: Optional[SapphireBrowserQueue] = None,
    ):
        """Initialize Sapphire API wrapper.

        Args:
            config: Project configuration
            network_id: Network ID for API calls
            geo_location: Geo coordinates (lat,lng format)
            browser_queue: Optional pre-initialized browser queue
        """
        self._project_config = config
        self._api_config = SapphireAPIConfig.from_project_config(
            config, network_id, geo_location
        )
        self._session_config = SapphireSessionConfig.from_project_config(
            config, network_id, geo_location
        )

        # Browser queue (created on demand if not provided)
        self._browser_queue = browser_queue
        self._owns_queue = browser_queue is None

        # Initialization state
        self._initialized = False
        self._init_lock = asyncio.Lock()

        logger.debug(
            f"SapphireAPI: initialized for domain={self._api_config.domain}, "
            f"network_id={network_id}"
        )

    async def _ensure_initialized(self) -> None:
        """Ensure browser queue is initialized."""
        async with self._init_lock:
            if self._initialized:
                return

            if self._browser_queue is None:
                self._browser_queue = SapphireBrowserQueue(self._session_config)
                await self._browser_queue.start()
                self._owns_queue = True

            self._initialized = True
            logger.info(f"SapphireAPI: ready (domain={self._api_config.domain})")

    async def close(self) -> None:
        """Close the API and release resources."""
        if self._owns_queue and self._browser_queue:
            await self._browser_queue.stop()
            self._browser_queue = None

        self._initialized = False
        logger.debug("SapphireAPI: closed")

    async def __aenter__(self) -> "SapphireAPI":
        """Async context manager entry."""
        await self._ensure_initialized()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    def _build_url(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Build full URL with parameters.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            Full URL with query string
        """
        base = self._api_config.base_url + endpoint
        if params:
            return f"{base}?{urlencode(params, doseq=True)}"
        return base

    def _get_common_params(self) -> Dict[str, str]:
        """Get common parameters for all API requests."""
        params = {
            **self._api_config.common_params,
            "transaction_id": str(uuid4()),
            "config_signature": self._api_config.config_signature,
        }

        if self._api_config.geo_location:
            params["geo_location"] = self._api_config.geo_location

        return params

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {
            "accept": "application/json, text/plain, */*",
            "x-nonce": str(uuid4()),
        }

        if self._api_config.api_key:
            headers["x-api-key"] = self._api_config.api_key

        return headers

    async def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make an API request.

        Args:
            endpoint: API endpoint path
            params: Query parameters
            extra_headers: Additional headers

        Returns:
            Response data as dict

        Raises:
            APIError: If request fails
        """
        await self._ensure_initialized()

        if not self._browser_queue:
            raise SessionError("Browser queue not initialized")

        # Build URL with parameters
        all_params = self._get_common_params()
        if params:
            all_params.update(params)

        url = self._build_url(endpoint, all_params)

        # Build headers
        headers = self._get_headers()
        if extra_headers:
            headers.update(extra_headers)

        # Make request through browser queue
        return await self._browser_queue.make_request(url, headers)

    # =========================================================================
    # Public API Methods
    # =========================================================================

    async def get_facets(
        self,
        specialty_id: Optional[str] = None,
        radius: int = 210,
    ) -> Dict[str, Any]:
        """Get facets (specialty categories and counts).

        Args:
            specialty_id: Optional specialty filter
            radius: Search radius in miles

        Returns:
            Facets response with specialty counts

        Raises:
            APIError: If request fails
        """
        endpoint = self._api_config.endpoints.get("facets", "/api/providers/facets.json")

        params = {
            "network_id": self._api_config.network_id,
            "radius": str(radius),
        }

        if specialty_id:
            params["search_specialty_id"] = specialty_id

        logger.debug(f"SapphireAPI: get_facets(specialty_id={specialty_id}, radius={radius})")

        result = await self._make_request(endpoint, params)

        # Validate response structure
        if not isinstance(result, dict):
            raise APIError(
                "Invalid facets response: expected dict",
                endpoint=endpoint,
            )

        return result

    async def get_summary(
        self,
        specialty_id: Optional[str] = None,
        provider_id: Optional[str] = None,
        page: int = 1,
        limit: int = 10,
        radius: int = 210,
        sort: str = "distance asc",
    ) -> Dict[str, Any]:
        """Get provider summary/search results.

        Args:
            specialty_id: Filter by specialty
            provider_id: Filter by specific provider
            page: Page number (1-indexed)
            limit: Results per page
            radius: Search radius in miles
            sort: Sort order

        Returns:
            Summary response with providers list

        Raises:
            APIError: If request fails
        """
        endpoint = self._api_config.endpoints.get("summary", "/api/providers/summary.json")

        params = {
            "network_id": self._api_config.network_id,
            "page": str(page),
            "limit": str(limit),
            "radius": str(radius),
            "sort": sort,
        }

        if specialty_id:
            params["search_specialty_id"] = specialty_id

        if provider_id:
            params["provider_id"] = provider_id

        logger.debug(
            f"SapphireAPI: get_summary(specialty_id={specialty_id}, "
            f"provider_id={provider_id}, page={page})"
        )

        result = await self._make_request(endpoint, params)

        # Validate response structure
        if not isinstance(result, dict):
            raise APIError(
                "Invalid summary response: expected dict",
                endpoint=endpoint,
            )

        return result

    async def get_affiliations(
        self,
        provider_id: str,
        location_id: str,
    ) -> Dict[str, Any]:
        """Get group/hospital affiliations for a provider location.

        Args:
            provider_id: Provider ID
            location_id: Location ID

        Returns:
            Affiliations response with group_affiliations list

        Raises:
            APIError: If request fails
        """
        endpoint_template = self._api_config.endpoints.get(
            "affiliations",
            "/api/providers/{provider_id}/locations/{location_id}/affiliations.json"
        )
        endpoint = endpoint_template.format(
            provider_id=provider_id,
            location_id=location_id
        )

        params = {
            "provider_id": provider_id,
            "location_id": location_id,
        }

        logger.debug(
            f"SapphireAPI: get_affiliations(provider_id={provider_id}, location_id={location_id})"
        )

        result = await self._make_request(endpoint, params)

        # Validate response structure
        if result is not None and not isinstance(result, dict):
            raise APIError(
                "Invalid affiliations response: expected dict or null",
                endpoint=endpoint,
            )

        return result or {}

    async def get_locations(
        self,
        provider_id: str,
        location_id: str,
    ) -> Dict[str, Any]:
        """Get other practice locations for a provider.

        Args:
            provider_id: Provider ID
            location_id: Location ID

        Returns:
            Locations response with other_locations list

        Raises:
            APIError: If request fails
        """
        endpoint_template = self._api_config.endpoints.get(
            "locations",
            "/api/providers/{provider_id}/locations/{location_id}/other_locations.json"
        )
        endpoint = endpoint_template.format(
            provider_id=provider_id,
            location_id=location_id
        )

        params = {
            "provider_id": provider_id,
            "location_id": location_id,
        }

        logger.debug(
            f"SapphireAPI: get_locations(provider_id={provider_id}, location_id={location_id})"
        )

        result = await self._make_request(endpoint, params)

        # Validate response structure
        if result is not None and not isinstance(result, dict):
            raise APIError(
                "Invalid locations response: expected dict or null",
                endpoint=endpoint,
            )

        return result or {}

    async def get_networks(
        self,
        provider_id: str,
        location_id: str,
    ) -> Dict[str, Any]:
        """Get networks accepted at a provider location.

        Args:
            provider_id: Provider ID
            location_id: Location ID

        Returns:
            Networks response with networks_accepted list

        Raises:
            APIError: If request fails
        """
        endpoint_template = self._api_config.endpoints.get(
            "networks",
            "/api/providers/{provider_id}/locations/{location_id}/networks_accepted.json"
        )
        endpoint = endpoint_template.format(
            provider_id=provider_id,
            location_id=location_id
        )

        params = {
            "provider_id": provider_id,
            "location_id": location_id,
        }

        logger.debug(
            f"SapphireAPI: get_networks(provider_id={provider_id}, location_id={location_id})"
        )

        result = await self._make_request(endpoint, params)

        # Validate response structure
        if result is not None and not isinstance(result, dict):
            raise APIError(
                "Invalid networks response: expected dict or null",
                endpoint=endpoint,
            )

        return result or {}

    async def get_provider_details(
        self,
        provider_id: str,
    ) -> Dict[str, Any]:
        """Get full provider details including summary data.

        This is a convenience method that fetches the summary for a specific
        provider ID.

        Args:
            provider_id: Provider ID

        Returns:
            Provider summary data

        Raises:
            APIError: If request fails
        """
        return await self.get_summary(provider_id=provider_id)

    async def get_provider_full(
        self,
        provider_id: str,
        location_id: str,
        include_affiliations: bool = True,
        include_locations: bool = True,
        include_networks: bool = True,
    ) -> Dict[str, Any]:
        """Get complete provider data including affiliations, locations, and networks.

        Args:
            provider_id: Provider ID
            location_id: Location ID
            include_affiliations: Include group/hospital affiliations
            include_locations: Include other practice locations
            include_networks: Include accepted networks

        Returns:
            Combined provider data dict with nested affiliations, locations, networks

        Raises:
            APIError: If any request fails
        """
        logger.debug(
            f"SapphireAPI: get_provider_full(provider_id={provider_id}, "
            f"location_id={location_id})"
        )

        # Start with summary
        result = await self.get_summary(provider_id=provider_id)

        # Fetch additional data in parallel
        tasks = []
        task_names = []

        if include_affiliations:
            tasks.append(self.get_affiliations(provider_id, location_id))
            task_names.append("affiliations")

        if include_locations:
            tasks.append(self.get_locations(provider_id, location_id))
            task_names.append("locations")

        if include_networks:
            tasks.append(self.get_networks(provider_id, location_id))
            task_names.append("networks")

        if tasks:
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            for name, response in zip(task_names, responses):
                if isinstance(response, Exception):
                    logger.warning(
                        f"SapphireAPI: failed to get {name} for "
                        f"provider_id={provider_id}: {response}"
                    )
                    result[name] = {}
                else:
                    result[name] = response

        return result

    # =========================================================================
    # Batch Operations
    # =========================================================================

    async def get_providers_batch(
        self,
        provider_location_pairs: List[tuple[str, str]],
        include_affiliations: bool = True,
        include_locations: bool = True,
        include_networks: bool = True,
        concurrency: int = 10,
    ) -> List[Dict[str, Any]]:
        """Fetch full details for multiple providers in parallel.

        Args:
            provider_location_pairs: List of (provider_id, location_id) tuples
            include_affiliations: Include group/hospital affiliations
            include_locations: Include other practice locations
            include_networks: Include accepted networks
            concurrency: Max concurrent requests

        Returns:
            List of provider data dicts (maintains order)
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def fetch_one(pair: tuple[str, str]) -> Dict[str, Any]:
            provider_id, location_id = pair
            async with semaphore:
                try:
                    return await self.get_provider_full(
                        provider_id,
                        location_id,
                        include_affiliations=include_affiliations,
                        include_locations=include_locations,
                        include_networks=include_networks,
                    )
                except Exception as e:
                    logger.error(
                        f"SapphireAPI: batch fetch failed for "
                        f"provider_id={provider_id}: {e}"
                    )
                    return {"error": str(e), "provider_id": provider_id}

        tasks = [fetch_one(pair) for pair in provider_location_pairs]
        results = await asyncio.gather(*tasks)

        return list(results)

    @property
    def stats(self) -> Dict[str, Any]:
        """Get API statistics."""
        if self._browser_queue:
            return {
                "queue_stats": self._browser_queue.stats,
                "queue_size": self._browser_queue.queue_size,
                "is_running": self._browser_queue.is_running,
            }
        return {"initialized": False}


# Convenience factory function
async def create_sapphire_api(
    config: SapphireProjectConfig,
    network_id: str,
    geo_location: str,
) -> SapphireAPI:
    """Create and initialize a Sapphire API wrapper.

    Args:
        config: Project configuration
        network_id: Network ID for API calls
        geo_location: Geo coordinates (lat,lng format)

    Returns:
        Initialized SapphireAPI instance
    """
    api = SapphireAPI(config, network_id, geo_location)
    await api._ensure_initialized()
    return api

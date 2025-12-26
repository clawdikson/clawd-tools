"""HealthSpark API wrapper for HealthSparq provider directories.

Provides async methods for searching providers and fetching details.
All configuration is injected - no hardcoded domains or plan codes.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urlencode

from healthsparq.config import HealthSparqProjectConfig

from .session import HealthSparqSession, create_session


@dataclass
class HealthSparkConfig:
    """Configuration for HealthSpark API wrapper.

    All fields are required and come from project configuration.
    No defaults that would hardcode domain or plan values.
    """

    # Site configuration
    domain: str
    insurer_code: str
    brand_code: str
    product_code: str
    api_version: str = "v4"

    # Request configuration
    max_retries: int = 5
    timeout: float = 30.0
    max_concurrent: int = 100

    # Output directories
    geocode_dir: Optional[str] = None

    @classmethod
    def from_project_config(
        cls,
        config: HealthSparqProjectConfig,
        product_code: str,
        geocode_dir: Optional[str] = None,
    ) -> "HealthSparkConfig":
        """Create HealthSparkConfig from project configuration.

        Args:
            config: Project configuration
            product_code: Product code for this scraping session
            geocode_dir: Directory for geocode cache files

        Returns:
            Configured HealthSparkConfig instance
        """
        return cls(
            domain=config.site.domain,
            insurer_code=config.site.insurer_code,
            brand_code=config.site.brand_code,
            product_code=product_code,
            api_version=config.site.api_version,
            max_retries=config.concurrency.retry_attempts,
            max_concurrent=config.concurrency.max_workers,
            geocode_dir=geocode_dir,
        )

    @property
    def base_url(self) -> str:
        """Base URL for API requests."""
        return f"https://{self.domain}/healthsparq/public/service"

    @property
    def auth_url(self) -> str:
        """URL for authentication."""
        return (
            f"{self.base_url}/login?"
            f"insurerCode={self.insurer_code}&"
            f"brandCode={self.brand_code}"
        )

    @property
    def search_url(self) -> str:
        """URL for provider search."""
        return f"{self.base_url}/{self.api_version}/search"

    @property
    def profile_url(self) -> str:
        """URL for provider profile."""
        return f"{self.base_url}/profile"

    @property
    def profile_url_v2(self) -> str:
        """URL for provider profile (v2)."""
        return f"{self.base_url}/v2/profile"

    @property
    def geocode_url(self) -> str:
        """URL for geocoding."""
        return f"{self.base_url}/geocode"

    @property
    def filter_url(self) -> str:
        """URL for search filters."""
        return f"{self.base_url}/v3/search/filters"


class HealthSpark:
    """HealthSparq API wrapper for provider directory scraping.

    All configuration is injected via HealthSparkConfig.
    Supports async context manager for proper resource cleanup.
    """

    def __init__(self, config: HealthSparkConfig):
        """Initialize HealthSpark with configuration.

        Args:
            config: HealthSparkConfig with all required settings
        """
        self.config = config
        self._session: Optional[HealthSparqSession] = None
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._lock = asyncio.Lock()
        self._initialized = False

        self._search_request_base = {
            "productCode": config.product_code,
            "clientCode": config.brand_code,
            "languageCode": "EN",
            "page": 1,
            "pageSize": 200,
            "searchType": "advanced",
            "sort": "DISTANCE",
        }

    async def _ensure_session(self) -> HealthSparqSession:
        """Ensure session is initialized and logged in."""
        async with self._lock:
            if self._session is None:
                self._session = create_session(
                    timeout=self.config.timeout,
                    max_retries=self.config.max_retries,
                )
                self._semaphore = asyncio.Semaphore(self.config.max_concurrent)

                # Login using browser to get auth cookies
                await self._session.login(self.config.auth_url)

                self._initialized = True
            return self._session

    async def close(self) -> None:
        """Close the session and clean up resources."""
        if self._session:
            await self._session.close()
            self._session = None
            self._initialized = False

    async def __aenter__(self) -> "HealthSpark":
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def search(
        self,
        location: str,
        additional_params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Search for providers at a location.

        Args:
            location: Location string (e.g., "Dallas, TX" or ZIP code)
            additional_params: Additional search parameters

        Returns:
            Search response dict with providerResults and metadata
        """
        session = await self._ensure_session()

        search_request = {**self._search_request_base}
        if additional_params:
            search_request.update(additional_params)
        search_request["location"] = location

        async with self._semaphore:
            response = await session.post(
                self.config.search_url,
                json_data=search_request,
            )

        if response.status_code != 200:
            raise Exception(
                f"Search failed: {response.status_code} - {response.text[:500]}"
            )

        return response.json()

    async def get_provider_details(
        self,
        provider_id: str,
        product_code: Optional[str] = None,
        brand_code: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get detailed information for a provider.

        Args:
            provider_id: HealthSparq provider ID
            product_code: Override product code (optional)
            brand_code: Override brand code (optional)

        Returns:
            Provider detail dict
        """
        session = await self._ensure_session()

        query_params = urlencode(
            {
                "providerId": provider_id,
                "clientCode": brand_code or self.config.brand_code,
                "productCode": product_code or self.config.product_code,
            }
        )

        async with self._semaphore:
            response = await session.get(f"{self.config.profile_url}?{query_params}")

        if response.status_code != 200:
            raise Exception(
                f"Provider details failed: {response.status_code} - {provider_id}"
            )

        return response.json().get("provider", {})

    async def get_geocode(self, location: str) -> dict[str, Any]:
        """Get geocode information for a location.

        Args:
            location: Location string

        Returns:
            Geocode result dict with lat/lng
        """
        session = await self._ensure_session()

        async with self._semaphore:
            response = await session.get(
                self.config.geocode_url,
                params={"location": location},
            )

        if response.status_code != 200:
            raise Exception(f"Geocode failed: {response.status_code} - {location}")

        data = response.json().get("data", [])
        if not data:
            raise Exception(f"No geocode results for: {location}")

        return data[0]

    async def get_search_filters(
        self,
        location: str,
        filters: Optional[list[str]] = None,
        sort: str = "NAME_ASC",
    ) -> dict[str, Any]:
        """Get available search filters for a location.

        Args:
            location: Location string (e.g., "Dallas County, TX")
            filters: Current active filters
            sort: Sort order

        Returns:
            Filter response with available categories
        """
        session = await self._ensure_session()

        filter_request = {
            "productCode": self.config.product_code,
            "clientCode": self.config.brand_code,
            "languageCode": "EN",
            "location": location,
            "filters": filters or [],
            "sort": sort,
        }

        async with self._semaphore:
            response = await session.post(
                self.config.filter_url,
                json_data=filter_request,
            )

        if response.status_code != 200:
            raise Exception(
                f"Filter request failed: {response.status_code} - {response.text[:500]}"
            )

        return response.json()

    async def search_with_params(
        self,
        location: str,
        page: int = 1,
        page_size: int = 200,
        sort: str = "NAME_ASC",
        filters: Optional[list[str]] = None,
        location_details: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Search with full parameter control.

        Args:
            location: Location string
            page: Page number
            page_size: Results per page
            sort: Sort order
            filters: Active filters
            location_details: Optional location details (for ZIP-based searches)

        Returns:
            Search response dict
        """
        session = await self._ensure_session()

        search_request = {
            "productCode": self.config.product_code,
            "clientCode": self.config.brand_code,
            "languageCode": "EN",
            "page": page,
            "pageSize": page_size,
            "searchType": "advanced",
            "sort": sort,
            "location": location,
            "filters": filters or [],
        }

        if location_details:
            search_request["locationDetails"] = location_details

        async with self._semaphore:
            response = await session.post(
                self.config.search_url,
                json_data=search_request,
            )

        if response.status_code != 200:
            raise Exception(
                f"Search failed: {response.status_code} - {response.text[:500]}"
            )

        return response.json()

"""Phase 2: Provider Detail Extraction module.

Fetches detailed information for providers discovered in Phase 1.
All configuration is injected - no global state.

Endpoints fetched per provider:
- summary: Provider summary data (name, specialty, location_id)
- locations: Other locations for this provider
- affiliations: Group and hospital affiliations
- networks: Network eligibility data

Storage backends:
- SQLITE (default): SQLite database (15x faster for large datasets)
- JSON_FILES: Individual JSON files on disk (backwards compatible)
- JSONL: Line-delimited JSON file (streaming, append-only)

Based on:
- audiobee_bcbs_il/index_1_v3.py (workflow pattern)
- healthsparq/phases/details.py (phase structure)
"""

from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

import orjson
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from sapphire.config.schema import SapphireProjectConfig, StorageBackend
from sapphire.core.exceptions import APIError, StorageError
from sapphire.core.storage import create_phase_store

# Use core.logging if available, fallback to stdlib
try:
    from core.logging import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from core.io.base import DataStore


# Type alias for browser request function
BrowserRequestFunc = Callable[[str, dict[str, str], int], Any]


@dataclass
class DetailsConfig:
    """Configuration for details extraction phase.

    Attributes:
        batch_size: Number of providers to process per batch (default: 1000)
        concurrent_requests: Max concurrent requests within a batch (default: 50)
        retry_attempts: Max retry attempts per request (default: 5)
        endpoints: API endpoints to fetch (default: summary, locations, affiliations, networks)
        request_timeout_ms: Request timeout in milliseconds (default: 120000)
    """

    batch_size: int = 1000
    concurrent_requests: int = 50
    retry_attempts: int = 5
    endpoints: list[str] = field(
        default_factory=lambda: ["summary", "locations", "affiliations", "networks"]
    )
    request_timeout_ms: int = 120000


@dataclass
class DetailsResult:
    """Result of the details extraction phase.

    Attributes:
        total_providers: Total number of providers to process
        successful: Number of successfully processed providers
        failed: Number of failed providers
        skipped_cached: Number of providers skipped (already cached)
        checkpoint_file: Path to checkpoint file for resumption
        errors: List of (provider_id, error_message) tuples
        duration_seconds: Elapsed time in seconds
        started_at: ISO timestamp when phase started
        completed_at: ISO timestamp when phase completed
    """

    total_providers: int
    successful: int
    failed: int
    skipped_cached: int
    checkpoint_file: Path | None = None
    errors: list[tuple[str, str]] = field(default_factory=list)
    duration_seconds: float = 0.0
    started_at: str | None = None
    completed_at: str | None = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        processed = self.successful + self.failed
        if processed == 0:
            return 0.0
        return (self.successful / processed) * 100

    @property
    def is_complete(self) -> bool:
        """Check if all providers were processed."""
        return self.successful + self.failed + self.skipped_cached >= self.total_providers


@dataclass
class ProviderData:
    """Container for provider data from all endpoints.

    Attributes:
        provider_id: Provider identifier
        network_id: Network identifier for this provider
        summary: Summary endpoint response
        location_id: Location ID extracted from summary
        locations: Locations endpoint response
        affiliations: Affiliations endpoint response
        networks: Networks endpoint response
    """

    provider_id: str
    network_id: str
    summary: dict[str, Any] | None = None
    location_id: str | None = None
    locations: dict[str, Any] | None = None
    affiliations: dict[str, Any] | None = None
    networks: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "provider_id": self.provider_id,
            "network_id": self.network_id,
            "summary": self.summary,
            "location_id": self.location_id,
            "locations": self.locations,
            "affiliations": self.affiliations,
            "networks": self.networks,
        }


def load_provider_ids_from_phase1(
    base_dir: Path,
    curr_date: str,
    storage_backend: StorageBackend = StorageBackend.SQLITE,
) -> dict[str, list[str]]:
    """Load provider IDs and network mappings from Phase 1 output.

    Looks for provider_ids_network_map in the Phase 1 output directory.
    Falls back to reading from JSON file if DataStore not found.

    Args:
        base_dir: Base output directory
        curr_date: Current date string (YYYYMMDD)
        storage_backend: Storage backend used in Phase 1

    Returns:
        Dictionary mapping provider_id to list of network_ids

    Raises:
        StorageError: If Phase 1 output not found or unreadable
    """
    date_dir = base_dir / curr_date
    raw_dir = date_dir / "raw"

    # Try JSON file first (common output format from Phase 1)
    json_file = raw_dir / "provider_ids_network_map.json"
    if json_file.exists():
        try:
            with open(json_file, "rb") as f:
                data = orjson.loads(f.read())
            logger.info(f"Loaded {len(data)} provider IDs from {json_file}")
            return data
        except (orjson.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read {json_file}: {e}")

    # Try DataStore
    try:
        with create_phase_store(
            date_dir, "provider_ids", storage_backend, read_only=True
        ) as store:
            # Look for network map record
            network_map = store.get("provider_ids_network_map.json")
            if network_map:
                logger.info(f"Loaded provider IDs from DataStore")
                return network_map

            # Reconstruct from individual records
            provider_map: dict[str, list[str]] = {}
            for key, record in store:
                if "provider_id" in record and "network_id" in record:
                    pid = record["provider_id"]
                    nid = record["network_id"]
                    if pid not in provider_map:
                        provider_map[pid] = []
                    if nid not in provider_map[pid]:
                        provider_map[pid].append(nid)
            logger.info(f"Reconstructed {len(provider_map)} provider IDs from DataStore")
            return provider_map
    except Exception as e:
        raise StorageError(
            f"Failed to load Phase 1 output from {date_dir}",
            details={"error": str(e)},
        ) from e


def _build_summary_url(
    config: SapphireProjectConfig,
    provider_id: str,
    network_id: str,
    geo_location: str | None = None,
) -> str:
    """Build summary endpoint URL with parameters.

    Args:
        config: Project configuration
        provider_id: Provider ID to fetch
        network_id: Network ID for the request
        geo_location: Optional geo coordinates (lat,lon)

    Returns:
        Fully constructed URL with query parameters
    """
    from urllib.parse import urlencode

    base_url = f"https://{config.site.domain}{config.api.endpoints['summary']}"
    params = {
        **config.api.common_params,
        "provider_id": provider_id,
        "network_id": network_id,
        "transaction_id": str(uuid.uuid4()),
        "config_signature": config.site.config_signature,
    }
    if geo_location:
        params["geo_location"] = geo_location
    return f"{base_url}?{urlencode(params)}"


def _build_detail_url(
    config: SapphireProjectConfig,
    endpoint: str,
    provider_id: str,
    location_id: str,
    geo_location: str | None = None,
) -> str:
    """Build detail endpoint URL (locations, affiliations, networks).

    Args:
        config: Project configuration
        endpoint: Endpoint name (locations, affiliations, networks)
        provider_id: Provider ID
        location_id: Location ID from summary response
        geo_location: Optional geo coordinates

    Returns:
        Fully constructed URL with query parameters
    """
    from urllib.parse import urlencode

    endpoint_template = config.api.endpoints.get(endpoint, "")
    endpoint_path = endpoint_template.format(
        provider_id=provider_id, location_id=location_id
    )
    base_url = f"https://{config.site.domain}{endpoint_path}"

    params = {
        **config.api.common_params,
        "provider_id": provider_id,
        "location_id": location_id,
        "transaction_id": str(uuid.uuid4()),
        "config_signature": config.site.config_signature,
    }
    if endpoint == "locations":
        params["limit"] = "100"
    if geo_location:
        params["geo_location"] = geo_location

    return f"{base_url}?{urlencode(params)}"


def _get_headers(config: SapphireProjectConfig) -> dict[str, str]:
    """Generate request headers for Sapphire API.

    Args:
        config: Project configuration

    Returns:
        Headers dictionary with API key and nonce
    """
    return {
        "accept": "application/json, text/plain, */*",
        "x-api-key": "03220e47-16eb-44d3-b1ca-4e3641973a97",
        "x-nonce": str(uuid.uuid4()),
    }


async def _fetch_with_retry(
    url: str,
    headers: dict[str, str],
    browser_request: BrowserRequestFunc,
    timeout_ms: int,
    retry_attempts: int,
    expected_key: str | None = None,
) -> dict[str, Any]:
    """Fetch URL with retry logic.

    Args:
        url: URL to fetch
        headers: Request headers
        browser_request: Browser request function
        timeout_ms: Request timeout in milliseconds
        retry_attempts: Maximum retry attempts
        expected_key: Optional key that must exist in response for validation

    Returns:
        JSON response data

    Raises:
        APIError: If all retries fail or response validation fails
    """
    last_error: Exception | None = None

    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(retry_attempts),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((Exception,)),
        reraise=True,
    ):
        with attempt:
            try:
                response = await browser_request(url, headers, timeout_ms)
                if hasattr(response, "json"):
                    response_data = await response.json()
                else:
                    response_data = response

                # Validate response structure if expected_key provided
                if expected_key and not isinstance(response_data, dict):
                    raise ValueError(f"Expected dict response, got {type(response_data)}")
                if expected_key and expected_key not in response_data:
                    raise ValueError(f"Missing expected key: {expected_key}")

                return response_data
            except Exception as e:
                last_error = e
                logger.debug(f"Retry attempt failed: {e}")
                raise

    # Should not reach here, but handle edge case
    raise APIError(
        f"Failed after {retry_attempts} attempts",
        endpoint=url,
        details={"last_error": str(last_error)},
    )


async def _process_summary(
    config: SapphireProjectConfig,
    provider_id: str,
    network_id: str,
    browser_request: BrowserRequestFunc,
    details_config: DetailsConfig,
    store: "DataStore",
    geo_location: str | None = None,
    is_missing: bool = False,
) -> dict[str, Any] | None:
    """Fetch and cache provider summary.

    Args:
        config: Project configuration
        provider_id: Provider ID to fetch
        network_id: Network ID
        browser_request: Browser request function
        details_config: Details phase configuration
        store: DataStore for caching
        geo_location: Optional geo coordinates
        is_missing: Whether this is a missing provider (for tagging)

    Returns:
        Summary response data or None if already cached
    """
    tag = "_missing" if is_missing else ""
    cache_key = f"provider_details/{provider_id}{tag}.json"
    cache_key_alt = f"provider_details/{provider_id}.json"

    # Check cache (both tagged and untagged)
    for key in [cache_key, cache_key_alt]:
        if store.exists(key):
            data = store.get(key)
            if data and isinstance(data, dict) and "providers" in data:
                logger.debug(f"Cached summary found: {provider_id}")
                return data
            # Invalid cache entry - will re-fetch
            logger.warning(f"Invalid cache entry {key}, re-fetching")

    # Fetch from API
    url = _build_summary_url(config, provider_id, network_id, geo_location)
    headers = _get_headers(config)
    logger.debug(f"Fetching summary: {provider_id}")

    try:
        response_data = await _fetch_with_retry(
            url,
            headers,
            browser_request,
            details_config.request_timeout_ms,
            details_config.retry_attempts,
            expected_key="providers",
        )
    except Exception as e:
        logger.error(f"Failed to fetch summary for {provider_id}: {e}")
        raise

    # Cache result
    store.put(cache_key, response_data)
    return response_data


async def _process_detail_endpoint(
    config: SapphireProjectConfig,
    endpoint: str,
    provider_id: str,
    location_id: str,
    browser_request: BrowserRequestFunc,
    details_config: DetailsConfig,
    store: "DataStore",
    geo_location: str | None = None,
    expected_key: str | None = None,
) -> dict[str, Any] | None:
    """Fetch and cache a detail endpoint (locations, affiliations, networks).

    Args:
        config: Project configuration
        endpoint: Endpoint name
        provider_id: Provider ID
        location_id: Location ID
        browser_request: Browser request function
        details_config: Details phase configuration
        store: DataStore for caching
        geo_location: Optional geo coordinates
        expected_key: Expected key in response for validation

    Returns:
        Endpoint response data or None if already cached
    """
    cache_key = f"{endpoint}/{provider_id}_{location_id}.json"

    # Check cache
    if store.exists(cache_key):
        logger.debug(f"Cached {endpoint} found: {provider_id}_{location_id}")
        return None  # Already cached, no need to return data

    # Fetch from API
    url = _build_detail_url(config, endpoint, provider_id, location_id, geo_location)
    headers = _get_headers(config)
    logger.debug(f"Fetching {endpoint}: {provider_id}_{location_id}")

    try:
        response_data = await _fetch_with_retry(
            url,
            headers,
            browser_request,
            details_config.request_timeout_ms,
            details_config.retry_attempts,
            expected_key=expected_key,
        )
    except Exception as e:
        logger.error(f"Failed to fetch {endpoint} for {provider_id}_{location_id}: {e}")
        raise

    # Cache result
    store.put(cache_key, response_data)
    return response_data


async def _process_provider(
    config: SapphireProjectConfig,
    provider_id: str,
    network_id: str,
    browser_request: BrowserRequestFunc,
    details_config: DetailsConfig,
    store: "DataStore",
    geo_location: str | None = None,
    is_missing: bool = False,
    fetch_networks: bool = False,
) -> tuple[bool, str | None]:
    """Process a single provider - fetch all endpoints.

    Args:
        config: Project configuration
        provider_id: Provider ID to process
        network_id: Network ID
        browser_request: Browser request function
        details_config: Details phase configuration
        store: DataStore for caching
        geo_location: Optional geo coordinates
        is_missing: Whether this is a missing provider
        fetch_networks: Whether to fetch networks endpoint (for missing providers)

    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Step 1: Fetch summary to get location_id
        summary = await _process_summary(
            config,
            provider_id,
            network_id,
            browser_request,
            details_config,
            store,
            geo_location,
            is_missing,
        )

        if summary is None:
            # Already cached, need to load for location_id
            tag = "_missing" if is_missing else ""
            cache_key = f"provider_details/{provider_id}{tag}.json"
            summary = store.get(cache_key)
            if not summary:
                cache_key = f"provider_details/{provider_id}.json"
                summary = store.get(cache_key)

        if not summary or not summary.get("providers"):
            logger.debug(f"No providers in summary for {provider_id}")
            return True, None  # Not an error, just empty

        # Extract location_id from summary
        provider_details = summary["providers"][0]
        location_id = provider_details.get("location_id")
        if not location_id:
            logger.warning(f"No location_id in summary for {provider_id}")
            return True, None

        # Step 2: Fetch detail endpoints in parallel
        # Expected response keys for validation
        endpoint_keys = {
            "locations": "other_provider_locations",
            "affiliations": "group_affiliations",
            "networks": "networks_accepted",
        }

        async def safe_fetch(endpoint: str) -> None:
            """Safely fetch an endpoint, logging errors."""
            if endpoint not in details_config.endpoints:
                return
            # Only fetch networks for missing providers
            if endpoint == "networks" and not fetch_networks and not is_missing:
                return
            try:
                await _process_detail_endpoint(
                    config,
                    endpoint,
                    provider_id,
                    location_id,
                    browser_request,
                    details_config,
                    store,
                    geo_location,
                    expected_key=endpoint_keys.get(endpoint),
                )
            except Exception as e:
                logger.warning(f"Error fetching {endpoint} for {provider_id}: {e}")

        # Run parallel fetches
        tasks = [
            safe_fetch("locations"),
            safe_fetch("affiliations"),
        ]
        if is_missing or fetch_networks:
            tasks.append(safe_fetch("networks"))

        await asyncio.gather(*tasks)
        return True, None

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to process provider {provider_id}: {error_msg}")
        return False, error_msg


def _check_provider_cached(
    provider_id: str,
    store: "DataStore",
    existing_summaries: set[str] | None = None,
) -> bool:
    """Check if provider details are already cached.

    Args:
        provider_id: Provider ID to check
        store: DataStore for checking
        existing_summaries: Pre-computed set of existing summary files (optimization)

    Returns:
        True if provider is fully cached, False otherwise
    """
    # Fast path: check pre-computed set
    if existing_summaries is not None:
        summary_key = f"{provider_id}.json"
        summary_key_tagged = f"{provider_id}_missing.json"
        return summary_key in existing_summaries or summary_key_tagged in existing_summaries

    # Slow path: check store directly
    if store.exists(f"provider_details/{provider_id}.json"):
        return True
    if store.exists(f"provider_details/{provider_id}_missing.json"):
        return True
    return False


def _save_checkpoint(
    checkpoint_file: Path,
    processed_ids: set[str],
    failed_ids: dict[str, str],
) -> None:
    """Save checkpoint for resumption.

    Args:
        checkpoint_file: Path to checkpoint file
        processed_ids: Set of successfully processed provider IDs
        failed_ids: Dict mapping failed provider IDs to error messages
    """
    checkpoint_data = {
        "processed_ids": list(processed_ids),
        "failed_ids": failed_ids,
    }
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
    with open(checkpoint_file, "wb") as f:
        f.write(orjson.dumps(checkpoint_data))
    logger.debug(f"Saved checkpoint: {len(processed_ids)} processed, {len(failed_ids)} failed")


def _load_checkpoint(checkpoint_file: Path) -> tuple[set[str], dict[str, str]]:
    """Load checkpoint for resumption.

    Args:
        checkpoint_file: Path to checkpoint file

    Returns:
        Tuple of (processed_ids set, failed_ids dict)
    """
    if not checkpoint_file.exists():
        return set(), {}
    try:
        with open(checkpoint_file, "rb") as f:
            data = orjson.loads(f.read())
        processed = set(data.get("processed_ids", []))
        failed = data.get("failed_ids", {})
        logger.info(f"Loaded checkpoint: {len(processed)} processed, {len(failed)} failed")
        return processed, failed
    except (orjson.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to load checkpoint {checkpoint_file}: {e}")
        return set(), {}


async def _process_batch(
    config: SapphireProjectConfig,
    batch: list[tuple[str, str]],
    batch_num: int,
    total_providers: int,
    browser_request: BrowserRequestFunc,
    details_config: DetailsConfig,
    store: "DataStore",
    geo_location: str | None = None,
    missing_provider_ids: set[str] | None = None,
    semaphore: asyncio.Semaphore | None = None,
) -> tuple[int, int, list[tuple[str, str]]]:
    """Process a batch of providers.

    Args:
        config: Project configuration
        batch: List of (provider_id, network_id) tuples
        batch_num: Current batch number
        total_providers: Total number of providers
        browser_request: Browser request function
        details_config: Details phase configuration
        store: DataStore for caching
        geo_location: Optional geo coordinates
        missing_provider_ids: Set of provider IDs marked as missing
        semaphore: Semaphore for concurrency control

    Returns:
        Tuple of (successful_count, failed_count, errors_list)
    """
    batch_start = batch_num * details_config.batch_size
    batch_end = min(batch_start + len(batch), total_providers)

    logger.info(
        f"Processing batch {batch_num + 1}: providers {batch_start + 1}-{batch_end} of {total_providers}"
    )

    successful = 0
    failed = 0
    errors: list[tuple[str, str]] = []

    if semaphore is None:
        semaphore = asyncio.Semaphore(details_config.concurrent_requests)

    async def process_with_semaphore(
        provider_id: str, network_id: str
    ) -> tuple[bool, str | None]:
        """Process provider with concurrency control."""
        async with semaphore:
            is_missing = missing_provider_ids and provider_id in missing_provider_ids
            return await _process_provider(
                config,
                provider_id,
                network_id,
                browser_request,
                details_config,
                store,
                geo_location,
                is_missing=is_missing,
                fetch_networks=is_missing,
            )

    # Create tasks for all providers in batch
    tasks = [process_with_semaphore(pid, nid) for pid, nid in batch]

    # Process tasks as they complete
    for i, coro in enumerate(asyncio.as_completed(tasks)):
        try:
            success, error_msg = await coro
            if success:
                successful += 1
            else:
                failed += 1
                errors.append((batch[i][0], error_msg or "Unknown error"))
        except Exception as e:
            failed += 1
            errors.append((batch[i][0], str(e)))
            logger.error(f"Unexpected error processing provider: {e}")

    logger.info(f"Batch {batch_num + 1} complete: {successful} successful, {failed} failed")
    return successful, failed, errors


async def run_details(
    config: SapphireProjectConfig,
    curr_date: str,
    provider_ids: dict[str, list[str]] | None = None,
    browser_request: BrowserRequestFunc | None = None,
    details_config: DetailsConfig | None = None,
    base_dir: Path | None = None,
    geo_location: str | None = None,
    missing_provider_ids: set[str] | None = None,
    resume: bool = True,
) -> DetailsResult:
    """Run Phase 2: Provider Detail Extraction.

    Fetches detailed information for all provider IDs discovered in Phase 1.
    Uses batch processing with configurable concurrency and retry logic.
    Supports checkpointing for resumption after failures.

    Args:
        config: Sapphire project configuration
        curr_date: Current date string (YYYYMMDD)
        provider_ids: Optional dict mapping provider_id to list of network_ids.
                     If None, loads from Phase 1 output.
        browser_request: Async function to make browser requests.
                        Signature: (url, headers, timeout_ms) -> response
        details_config: Phase configuration (uses defaults if None)
        base_dir: Base output directory (default: current directory)
        geo_location: Optional geo coordinates for requests (lat,lon string)
        missing_provider_ids: Set of provider IDs to tag as missing
        resume: If True, resume from checkpoint if available

    Returns:
        DetailsResult with processing statistics

    Raises:
        StorageError: If Phase 1 output not found
        ValueError: If browser_request not provided

    Example:
        async with SapphireBrowserQueue(session_config) as browser:
            result = await run_details(
                config=project_config,
                curr_date="20251230",
                browser_request=browser.async_request,
            )
            print(f"Processed {result.successful} providers")
    """
    if browser_request is None:
        raise ValueError("browser_request function is required")

    if details_config is None:
        details_config = DetailsConfig(
            batch_size=config.concurrency.batch_size,
            concurrent_requests=config.concurrency.max_workers,
            retry_attempts=config.concurrency.retry_attempts,
            request_timeout_ms=config.concurrency.request_timeout_ms,
        )

    if base_dir is None:
        base_dir = Path.cwd()

    # Load provider IDs from Phase 1 if not provided
    if provider_ids is None:
        provider_ids = load_provider_ids_from_phase1(
            base_dir, curr_date, config.output.storage_backend
        )

    if not provider_ids:
        logger.warning("No provider IDs to process")
        return DetailsResult(
            total_providers=0,
            successful=0,
            failed=0,
            skipped_cached=0,
        )

    # Setup checkpoint
    date_dir = base_dir / curr_date
    checkpoint_file = date_dir / "raw" / "details_checkpoint.json"

    # Load checkpoint if resuming
    if resume:
        processed_ids, failed_checkpoint = _load_checkpoint(checkpoint_file)
    else:
        processed_ids = set()
        failed_checkpoint = {}

    # Flatten provider_ids to list of (provider_id, network_id) tuples
    # Use first network_id for each provider
    all_providers = [
        (pid, networks[0])
        for pid, networks in provider_ids.items()
        if networks and pid not in processed_ids
    ]

    total_providers = len(provider_ids)
    skipped_from_checkpoint = len(processed_ids)

    logger.info(
        f"Phase 2: Processing {len(all_providers)} providers "
        f"({skipped_from_checkpoint} skipped from checkpoint)"
    )

    # Open DataStore for caching
    storage_backend = config.output.storage_backend

    successful = 0
    failed = 0
    all_errors: list[tuple[str, str]] = list(failed_checkpoint.items())
    skipped_cached = 0

    with create_phase_store(
        date_dir, "provider_details", storage_backend
    ) as summary_store:
        # Pre-compute existing summaries for fast cache checking
        existing_summaries = set(summary_store.keys("*.json"))

        # Filter out already cached providers
        providers_to_process = []
        for pid, nid in all_providers:
            if _check_provider_cached(pid, summary_store, existing_summaries):
                skipped_cached += 1
                processed_ids.add(pid)
            else:
                providers_to_process.append((pid, nid))

        logger.info(
            f"Filtered: {skipped_cached} already cached, "
            f"{len(providers_to_process)} to process"
        )

        # Create stores for other endpoints
        with create_phase_store(date_dir, "locations", storage_backend) as loc_store:
            with create_phase_store(date_dir, "affiliations", storage_backend) as aff_store:
                with create_phase_store(date_dir, "networks", storage_backend) as net_store:
                    # Create a unified store adapter that routes to appropriate backend
                    class MultiStore:
                        """Adapter that routes puts to correct store based on key prefix."""

                        def __init__(self):
                            self.stores = {
                                "provider_details": summary_store,
                                "locations": loc_store,
                                "affiliations": aff_store,
                                "networks": net_store,
                            }

                        def put(self, key: str, data: dict) -> None:
                            prefix = key.split("/")[0] if "/" in key else "provider_details"
                            store = self.stores.get(prefix, summary_store)
                            store.put(key, data)

                        def get(self, key: str) -> dict | None:
                            prefix = key.split("/")[0] if "/" in key else "provider_details"
                            store = self.stores.get(prefix, summary_store)
                            return store.get(key)

                        def exists(self, key: str) -> bool:
                            prefix = key.split("/")[0] if "/" in key else "provider_details"
                            store = self.stores.get(prefix, summary_store)
                            return store.exists(key)

                        def keys(self, pattern: str = "*") -> set[str]:
                            # For checking summaries
                            return set(summary_store.keys(pattern))

                    multi_store = MultiStore()

                    # Process in batches
                    batch_size = details_config.batch_size
                    num_batches = (len(providers_to_process) + batch_size - 1) // batch_size

                    logger.info(
                        f"Processing in {num_batches} batch(es) of up to {batch_size} providers"
                    )

                    semaphore = asyncio.Semaphore(details_config.concurrent_requests)

                    for batch_num in range(num_batches):
                        batch_start = batch_num * batch_size
                        batch_end = min(batch_start + batch_size, len(providers_to_process))
                        batch = providers_to_process[batch_start:batch_end]

                        batch_success, batch_failed, batch_errors = await _process_batch(
                            config,
                            batch,
                            batch_num,
                            total_providers,
                            browser_request,
                            details_config,
                            multi_store,
                            geo_location,
                            missing_provider_ids,
                            semaphore,
                        )

                        successful += batch_success
                        failed += batch_failed
                        all_errors.extend(batch_errors)

                        # Update processed IDs
                        for pid, _ in batch:
                            if pid not in [e[0] for e in batch_errors]:
                                processed_ids.add(pid)

                        # Save checkpoint after each batch
                        failed_ids_dict = dict(all_errors)
                        _save_checkpoint(checkpoint_file, processed_ids, failed_ids_dict)

                        # Flush stores after each batch
                        for store in [summary_store, loc_store, aff_store, net_store]:
                            store.flush()

    # Final checkpoint save
    _save_checkpoint(checkpoint_file, processed_ids, dict(all_errors))

    result = DetailsResult(
        total_providers=total_providers,
        successful=successful,
        failed=failed,
        skipped_cached=skipped_cached + skipped_from_checkpoint,
        checkpoint_file=checkpoint_file if all_errors else None,
        errors=all_errors,
    )

    logger.info(
        f"Phase 2 complete: {result.successful} successful, "
        f"{result.failed} failed, {result.skipped_cached} cached, "
        f"success rate: {result.success_rate:.1f}%"
    )

    return result


def run_details_sync(
    config: SapphireProjectConfig,
    curr_date: str,
    provider_ids: dict[str, list[str]] | None = None,
    browser_request: BrowserRequestFunc | None = None,
    details_config: DetailsConfig | None = None,
    base_dir: Path | None = None,
    geo_location: str | None = None,
    missing_provider_ids: set[str] | None = None,
    resume: bool = True,
) -> DetailsResult:
    """Synchronous wrapper for run_details.

    Args:
        config: Sapphire project configuration
        curr_date: Current date string (YYYYMMDD)
        provider_ids: Optional dict mapping provider_id to list of network_ids
        browser_request: Async function to make browser requests
        details_config: Phase configuration (uses defaults if None)
        base_dir: Base output directory
        geo_location: Optional geo coordinates for requests
        missing_provider_ids: Set of provider IDs to tag as missing
        resume: If True, resume from checkpoint if available

    Returns:
        DetailsResult with processing statistics
    """
    return asyncio.run(
        run_details(
            config=config,
            curr_date=curr_date,
            provider_ids=provider_ids,
            browser_request=browser_request,
            details_config=details_config,
            base_dir=base_dir,
            geo_location=geo_location,
            missing_provider_ids=missing_provider_ids,
            resume=resume,
        )
    )


async def copy_missing_from_previous(
    config: SapphireProjectConfig,
    curr_date: str,
    prev_date: str,
    provider_ids: list[str],
    base_dir: Path | None = None,
) -> int:
    """Copy provider data from previous run for missing providers (V1 fallback).

    Args:
        config: Project configuration
        curr_date: Current date string
        prev_date: Previous date string
        provider_ids: List of provider IDs to copy
        base_dir: Base output directory

    Returns:
        Number of providers copied
    """
    if base_dir is None:
        base_dir = Path.cwd()

    curr_dir = base_dir / curr_date
    prev_dir = base_dir / prev_date

    if not prev_dir.exists():
        logger.warning(f"Previous date directory not found: {prev_dir}")
        return 0

    copied = 0
    storage_backend = config.output.storage_backend

    # Open both current and previous stores
    try:
        with create_phase_store(
            curr_dir, "provider_details", storage_backend
        ) as curr_store:
            with create_phase_store(
                prev_dir, "provider_details", storage_backend, read_only=True
            ) as prev_store:
                for pid in provider_ids:
                    for key_suffix in [f"{pid}.json", f"{pid}_missing.json"]:
                        key = f"provider_details/{key_suffix}"
                        if prev_store.exists(key) and not curr_store.exists(key):
                            data = prev_store.get(key)
                            if data:
                                curr_store.put(key, data)
                                copied += 1
                                break

        logger.info(f"Copied {copied} providers from {prev_date}")
    except Exception as e:
        logger.error(f"Failed to copy from previous: {e}")

    return copied

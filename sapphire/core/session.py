"""
Sapphire Browser Session Manager.

Producer-consumer pattern for managing Sapphire API requests through a
browser-based session. Uses core/session BrowserSession with Camoufox backend
for anti-detection capabilities.

Features:
- Producer-consumer pattern with asyncio Queue
- Page refresh after N requests to prevent memory leaks
- Header interception for API credentials (X-API-Key, X-Nonce)
- Graceful shutdown with request draining
- Configurable via SapphireProjectConfig
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Callable, Awaitable
from uuid import uuid4

from sapphire.config.schema import SapphireProjectConfig
from sapphire.core.exceptions import SessionError, APIError

from core.logging import logger
from core.session import BrowserSession, BrowserType
from core.proxy import ProxyType


@dataclass
class APIRequest:
    """Represents a queued API request."""

    url: str
    headers: Dict[str, str]
    request_id: str = field(default_factory=lambda: f"req_{int(time.time() * 1000)}_{uuid4().hex[:8]}")
    result_future: asyncio.Future = field(default_factory=lambda: asyncio.get_event_loop().create_future())
    created_at: float = field(default_factory=time.time)

    @property
    def age_seconds(self) -> float:
        """Time since request was created."""
        return time.time() - self.created_at


@dataclass
class SapphireSessionConfig:
    """Configuration for Sapphire browser session.

    Extracted from SapphireProjectConfig for session-specific settings.
    """

    # Browser configuration
    browser_type: str = "camoufox"
    headless: bool = False

    # Site configuration
    base_url: str = ""
    ci: str = ""
    network_id: str = ""
    geo_location: str = ""

    # Queue configuration
    num_workers: int = 10
    max_queue_size: int = 1000
    request_timeout_seconds: float = 120.0

    # Page refresh configuration (prevents memory leaks)
    page_refresh_interval: int = 5000

    # Retry configuration
    max_retries: int = 5
    retry_delay_seconds: float = 1.0

    @classmethod
    def from_project_config(
        cls,
        config: SapphireProjectConfig,
        network_id: str,
        geo_location: str,
    ) -> "SapphireSessionConfig":
        """Create session config from project configuration."""
        return cls(
            browser_type=config.session.browser_type,
            base_url=f"https://{config.site.domain}",
            ci=config.site.ci,
            network_id=network_id,
            geo_location=geo_location,
            num_workers=config.concurrency.max_workers,
            max_queue_size=config.concurrency.batch_size,
            request_timeout_seconds=config.concurrency.request_timeout_ms / 1000.0,
            page_refresh_interval=config.concurrency.page_refresh_interval,
            max_retries=config.concurrency.retry_attempts,
            retry_delay_seconds=config.concurrency.retry_delay_ms / 1000.0,
        )


class SapphireBrowserQueue:
    """
    Producer-consumer browser queue for Sapphire API requests.

    Uses a single browser page (Camoufox) with fetch() calls for parallel API requests.
    Features:
    - Async queue-based request processing
    - Automatic page refresh after N requests to prevent memory leaks
    - Header interception for API credentials
    - Graceful shutdown with request draining

    Usage:
        async with SapphireBrowserQueue(config) as queue:
            result = await queue.make_request(url, headers)
    """

    def __init__(self, config: SapphireSessionConfig):
        """Initialize the browser queue.

        Args:
            config: Session configuration
        """
        self.config = config

        # Queue and worker management
        self._request_queue: asyncio.Queue[Optional[APIRequest]] = asyncio.Queue(
            maxsize=config.max_queue_size
        )
        self._worker_tasks: list[asyncio.Task] = []
        self._running = False
        self._shutting_down = False

        # Browser state
        self._browser_session: Optional[BrowserSession] = None
        self._page = None
        self._request_count = 0
        self._initialized = False

        # Captured headers from initial page load
        self._captured_api_key: Optional[str] = None

        # Lock for initialization
        self._init_lock = asyncio.Lock()

        # Statistics
        self._stats = {
            "requests_processed": 0,
            "requests_failed": 0,
            "page_refreshes": 0,
        }

    async def _initialize(self) -> None:
        """Initialize browser and establish session."""
        async with self._init_lock:
            if self._initialized:
                return

            try:
                logger.info(f"SapphireBrowserQueue: initializing browser ({self.config.browser_type})")

                # Build proxy configuration - use DataImpulse residential proxies
                proxy_types = [ProxyType.DATAIMPULSE_SESSION]

                # Create browser session with appropriate backend
                browser_type: BrowserType = BrowserType.CAMOUFOX
                if self.config.browser_type == "playwright":
                    browser_type = BrowserType.PLAYWRIGHT
                elif self.config.browser_type == "patchright":
                    browser_type = BrowserType.PATCHRIGHT

                self._browser_session = BrowserSession(
                    proxy_types=proxy_types,
                    browser_id=0,
                    max_concurrent_requests=self.config.num_workers,
                    browser_type=browser_type,
                )

                # Initialize and navigate to base URL
                await self._browser_session._ensure_initialized()

                # Navigate to establish session
                initial_url = self._build_initial_url()
                logger.info(f"SapphireBrowserQueue: navigating to {initial_url}")

                await self._browser_session.login(initial_url)

                # Wait for page to fully load
                await asyncio.sleep(5)

                # Store page reference for direct evaluate calls
                self._page = self._browser_session._page

                self._initialized = True
                self._request_count = 0

                logger.info("SapphireBrowserQueue: browser initialized successfully")

            except Exception as e:
                logger.error(f"SapphireBrowserQueue: initialization failed: {e}")
                await self._cleanup()
                raise SessionError(f"Failed to initialize browser session: {e}")

    def _build_initial_url(self) -> str:
        """Build the initial page URL for session establishment."""
        params = {
            "ci": self.config.ci,
            "network_id": self.config.network_id,
            "locale": "en",
        }
        if self.config.geo_location:
            params["geo_location"] = self.config.geo_location

        param_str = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.config.base_url}/?{param_str}"

    async def _refresh_page(self) -> None:
        """Refresh the page to prevent memory leaks."""
        if not self._page:
            return

        try:
            logger.info("SapphireBrowserQueue: refreshing page to prevent memory leaks")

            initial_url = self._build_initial_url()
            await self._page.goto(initial_url, wait_until="domcontentloaded")
            await asyncio.sleep(3)

            self._request_count = 0
            self._stats["page_refreshes"] += 1

            logger.info("SapphireBrowserQueue: page refresh completed")

        except Exception as e:
            logger.warning(f"SapphireBrowserQueue: page refresh failed: {e}")

    async def _process_request(self, request: APIRequest) -> Dict[str, Any]:
        """Process a single API request using page.evaluate() with fetch.

        Args:
            request: The API request to process

        Returns:
            Response data as dict
        """
        if not self._page:
            raise SessionError("Browser page not initialized")

        # Check if page refresh is needed
        self._request_count += 1
        if self._request_count >= self.config.page_refresh_interval:
            await self._refresh_page()

        logger.debug(f"SapphireBrowserQueue: processing request {request.request_id}")

        # Execute fetch in browser context
        result = await self._page.evaluate("""
            async ({ url, headers }) => {
                try {
                    const response = await fetch(url, {
                        method: 'GET',
                        headers: headers || {}
                    });

                    if (!response.ok) {
                        return {
                            success: false,
                            status: response.status,
                            statusText: response.statusText
                        };
                    }

                    const data = await response.json();
                    return {
                        success: true,
                        data: data
                    };
                } catch (error) {
                    return {
                        success: false,
                        error: error.message
                    };
                }
            }
        """, {"url": request.url, "headers": request.headers})

        if result.get("success"):
            self._stats["requests_processed"] += 1
            logger.debug(f"SapphireBrowserQueue: request {request.request_id} completed")
            return result.get("data", {})
        else:
            self._stats["requests_failed"] += 1
            error_msg = result.get("error") or f"HTTP {result.get('status')}: {result.get('statusText')}"
            logger.warning(f"SapphireBrowserQueue: request {request.request_id} failed: {error_msg}")
            raise APIError(
                f"API request failed: {error_msg}",
                status_code=result.get("status"),
                endpoint=request.url,
            )

    async def _worker(self, worker_id: int) -> None:
        """Worker coroutine that processes requests from the queue.

        Args:
            worker_id: Unique identifier for this worker
        """
        logger.debug(f"SapphireBrowserQueue: worker {worker_id} started")

        while self._running:
            try:
                # Get request from queue with timeout
                try:
                    request = await asyncio.wait_for(
                        self._request_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Check for shutdown sentinel
                if request is None:
                    self._request_queue.task_done()
                    break

                # Process the request with retries
                last_error: Optional[Exception] = None
                for attempt in range(self.config.max_retries):
                    try:
                        result = await asyncio.wait_for(
                            self._process_request(request),
                            timeout=self.config.request_timeout_seconds
                        )
                        request.result_future.set_result(result)
                        break
                    except asyncio.TimeoutError:
                        last_error = TimeoutError(f"Request timed out after {self.config.request_timeout_seconds}s")
                        logger.warning(f"Worker {worker_id}: request {request.request_id} timeout (attempt {attempt + 1})")
                    except Exception as e:
                        last_error = e
                        logger.warning(f"Worker {worker_id}: request {request.request_id} failed (attempt {attempt + 1}): {e}")

                    if attempt < self.config.max_retries - 1:
                        await asyncio.sleep(self.config.retry_delay_seconds * (attempt + 1))
                else:
                    # All retries exhausted
                    if not request.result_future.done():
                        request.result_future.set_exception(
                            last_error or APIError("Request failed after all retries")
                        )

                self._request_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id}: unexpected error: {e}")

        logger.debug(f"SapphireBrowserQueue: worker {worker_id} stopped")

    async def start(self) -> None:
        """Start the browser queue and worker tasks."""
        if self._running:
            return

        await self._initialize()

        self._running = True
        self._shutting_down = False

        # Start worker tasks
        for i in range(self.config.num_workers):
            task = asyncio.create_task(self._worker(i))
            self._worker_tasks.append(task)

        logger.info(f"SapphireBrowserQueue: started with {self.config.num_workers} workers")

    async def stop(self, drain: bool = True) -> None:
        """Stop the browser queue gracefully.

        Args:
            drain: If True, wait for pending requests to complete
        """
        if not self._running:
            return

        self._shutting_down = True
        self._running = False

        logger.info("SapphireBrowserQueue: stopping...")

        if drain:
            # Wait for queue to drain
            try:
                await asyncio.wait_for(self._request_queue.join(), timeout=30.0)
            except asyncio.TimeoutError:
                logger.warning("SapphireBrowserQueue: queue drain timed out")

        # Send shutdown sentinels
        for _ in range(len(self._worker_tasks)):
            try:
                self._request_queue.put_nowait(None)
            except asyncio.QueueFull:
                pass

        # Wait for workers to finish
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
            self._worker_tasks.clear()

        await self._cleanup()

        logger.info(f"SapphireBrowserQueue: stopped. Stats: {self._stats}")

    async def _cleanup(self) -> None:
        """Clean up browser resources."""
        if self._browser_session:
            try:
                await self._browser_session.close()
            except Exception as e:
                logger.warning(f"SapphireBrowserQueue: cleanup error: {e}")
            finally:
                self._browser_session = None
                self._page = None
                self._initialized = False

    async def make_request(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Make an API request through the browser queue.

        Args:
            url: Full URL to request
            headers: Optional headers dict
            timeout: Optional timeout in seconds (defaults to config)

        Returns:
            Response data as dict

        Raises:
            SessionError: If queue is not running
            APIError: If request fails
            TimeoutError: If request times out
        """
        if not self._running:
            await self.start()

        if self._shutting_down:
            raise SessionError("Queue is shutting down")

        # Create request
        request = APIRequest(
            url=url,
            headers=headers or {},
        )

        # Queue the request
        try:
            await asyncio.wait_for(
                self._request_queue.put(request),
                timeout=10.0
            )
        except asyncio.TimeoutError:
            raise SessionError("Queue is full, request rejected")

        # Wait for result
        try:
            result = await asyncio.wait_for(
                request.result_future,
                timeout=timeout or self.config.request_timeout_seconds
            )
            return result
        except asyncio.TimeoutError:
            raise TimeoutError(f"Request {request.request_id} timed out")

    async def __aenter__(self) -> "SapphireBrowserQueue":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop(drain=True)

    @property
    def stats(self) -> Dict[str, int]:
        """Get queue statistics."""
        return self._stats.copy()

    @property
    def queue_size(self) -> int:
        """Get current queue size."""
        return self._request_queue.qsize()

    @property
    def is_running(self) -> bool:
        """Check if queue is running."""
        return self._running and not self._shutting_down


# Convenience factory function
async def create_browser_queue(
    config: SapphireProjectConfig,
    network_id: str,
    geo_location: str,
) -> SapphireBrowserQueue:
    """Create and start a browser queue from project configuration.

    Args:
        config: Sapphire project configuration
        network_id: Network ID for this session
        geo_location: Geo coordinates (lat,lng format)

    Returns:
        Started SapphireBrowserQueue instance
    """
    session_config = SapphireSessionConfig.from_project_config(
        config, network_id, geo_location
    )
    queue = SapphireBrowserQueue(session_config)
    await queue.start()
    return queue

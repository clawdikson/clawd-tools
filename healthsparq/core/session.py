"""Session management for HealthSparq API requests.

Uses shared_package for browser-based authentication and fast HTTP requests.
Pattern:
1. ResilientBrowserSession for login (gets cookies)
2. HttpSession for fast API calls (uses extracted cookies)
"""

import asyncio
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# Add shared_package to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared_package.proxy import ProxyType
from shared_package.session import HttpSession, ResilientBrowserSession


@dataclass
class SessionConfig:
    """Configuration for HTTP session."""

    timeout: float = 30.0
    max_retries: int = 5
    backoff_factor: float = 2.0
    max_backoff: float = 30.0
    user_agent: Optional[str] = None
    cookies: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    proxy_types: list[ProxyType] = field(default_factory=lambda: [ProxyType.DECODO_DC_STATIC])


class HealthSparqSession:
    """Async HTTP session for HealthSparq API requests.

    Uses browser-based login to extract cookies, then fast HTTP for API calls.
    """

    def __init__(self, config: SessionConfig):
        self.config = config
        self._browser_session: Optional[ResilientBrowserSession] = None
        self._http_session: Optional[HttpSession] = None
        self._lock = asyncio.Lock()
        self._initialized = False

    async def login(self, auth_url: str) -> None:
        """Login using browser session and extract cookies for HTTP session.

        Args:
            auth_url: The authentication URL to visit
        """
        async with self._lock:
            if self._initialized:
                return

            # Use browser for login to get cookies
            self._browser_session = ResilientBrowserSession(
                proxy_types=self.config.proxy_types
            )
            await self._browser_session.login(auth_url)

            # Extract cookies and user agent from browser
            cookies = await self._browser_session.get_cookies()
            user_agent = await self._browser_session.get_user_agent()

            # Create native HTTP session with extracted auth
            self._http_session = HttpSession()
            await self._http_session.initialize_from_browser(cookies, user_agent)

            # Close browser (no longer needed after auth extraction)
            await self._browser_session.close()
            self._browser_session = None

            self._initialized = True

    async def _ensure_http_session(self) -> HttpSession:
        """Ensure HTTP session exists."""
        if self._http_session is None:
            raise RuntimeError("Session not initialized. Call login() first.")
        return self._http_session

    async def get(
        self,
        url: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ):
        """Make GET request."""
        session = await self._ensure_http_session()
        return await self._request_with_retry(
            session.get, url, params=params, headers=headers
        )

    async def post(
        self,
        url: str,
        json_data: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ):
        """Make POST request."""
        session = await self._ensure_http_session()
        return await self._request_with_retry(
            session.post, url, json_data=json_data, data=data, headers=headers
        )

    async def _request_with_retry(self, method, url: str, **kwargs):
        """Execute request with exponential backoff retry."""
        last_exception: Optional[Exception] = None

        for attempt in range(self.config.max_retries):
            try:
                response = await method(url, **{k: v for k, v in kwargs.items() if v is not None})

                # Check for auth errors that might need session refresh
                if response.status_code in [401, 403]:
                    # Invalidate session for refresh
                    self._initialized = False
                    last_exception = Exception(
                        f"Auth error: {response.status_code} - {url}"
                    )
                elif response.status_code < 500:
                    return response
                else:
                    last_exception = Exception(
                        f"Server error: {response.status_code} - {url}"
                    )

            except Exception as e:
                last_exception = e

            if attempt < self.config.max_retries - 1:
                sleep_time = min(
                    self.config.backoff_factor ** attempt,
                    self.config.max_backoff,
                )
                await asyncio.sleep(sleep_time)

        if last_exception:
            raise last_exception
        raise RuntimeError("Request failed with no exception")

    async def close(self) -> None:
        """Close all sessions."""
        if self._browser_session:
            await self._browser_session.close()
            self._browser_session = None
        if self._http_session:
            await self._http_session.close()
            self._http_session = None
        self._initialized = False

    async def __aenter__(self) -> "HealthSparqSession":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()


def create_session(
    cookies: Optional[dict[str, str]] = None,
    user_agent: Optional[str] = None,
    timeout: float = 30.0,
    max_retries: int = 5,
    proxy_types: Optional[list[ProxyType]] = None,
) -> HealthSparqSession:
    """Create a configured HealthSparq session.

    Args:
        cookies: Optional cookies dict (not used with browser auth)
        user_agent: Optional user agent string
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
        proxy_types: Proxy types for browser session

    Returns:
        Configured HealthSparqSession instance
    """
    config = SessionConfig(
        timeout=timeout,
        max_retries=max_retries,
        user_agent=user_agent,
        cookies=cookies or {},
        proxy_types=proxy_types or [ProxyType.DECODO_DC_STATIC],
    )
    return HealthSparqSession(config)

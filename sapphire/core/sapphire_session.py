"""Session wrapper for Sapphire API requests.

Uses core package for browser-based authentication and fast HTTP requests.
Follows HealthSparqSession architecture.
"""

import asyncio
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

_core_path = Path(__file__).parent.parent.parent / "core"
if _core_path.exists() and str(_core_path.parent) not in sys.path:
    sys.path.insert(0, str(_core_path.parent))

from core.logging import logger
from core.proxy import ProxyType
from core.session import HttpSession, ResilientBrowserSession, RetryConfig
from core.session.backend import BrowserType

from sapphire.core.exceptions import SessionError


@dataclass
class SessionConfig:
    """Configuration for Sapphire HTTP session."""

    timeout: float = 30.0
    max_retries: int = 5
    backoff_factor: float = 2.0
    max_backoff: float = 30.0
    user_agent: Optional[str] = None
    cookies: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    proxy_types: list[ProxyType] = field(
        default_factory=lambda: [ProxyType.DATAIMPULSE_SESSION]
    )
    browser_type: BrowserType = BrowserType.CAMOUFOX


class SapphireSession:
    """Async HTTP session for Sapphire API requests."""

    def __init__(self, config: SessionConfig):
        self.config = config
        self._browser_session: Optional[ResilientBrowserSession] = None
        self._http_session: Optional[HttpSession] = None
        self._lock = asyncio.Lock()
        self._initialized = False

    async def _invalidate_session(self) -> None:
        logger.warning("SapphireSession: session invalidated due to auth error")
        self._initialized = False

    async def initialize(self, auth_url: str) -> None:
        async with self._lock:
            if self._initialized:
                return

            logger.info(f"SapphireSession: initializing with {auth_url}")

            self._browser_session = ResilientBrowserSession(
                proxy_types=self.config.proxy_types,
                browser_type=self.config.browser_type,
            )
            await self._browser_session.login(auth_url)
            logger.debug("SapphireSession: browser login complete")

            cookies = await self._browser_session.get_cookies()
            user_agent = await self._browser_session.get_user_agent()
            logger.debug(f"SapphireSession: extracted {len(cookies)} cookies")

            retry_config = None
            if RetryConfig is not None:
                retry_config = RetryConfig(
                    max_retries=self.config.max_retries,
                    backoff_factor=self.config.backoff_factor,
                    max_backoff=self.config.max_backoff,
                )
            self._http_session = HttpSession(
                retry_config=retry_config,
                on_auth_error=self._invalidate_session,
            )
            await self._http_session.initialize_from_browser(cookies, user_agent)
            logger.info("SapphireSession: HTTP session created from browser")

            await self._browser_session.close()
            self._browser_session = None

            self._initialized = True

    async def request(self, url: str, **kwargs: Any) -> Any:
        if not self._initialized or self._http_session is None:
            raise SessionError("Session not initialized. Call initialize() first.")
        return await self._http_session.get(url, **kwargs)

    async def get(
        self,
        url: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> Any:
        if not self._initialized or self._http_session is None:
            raise SessionError("Session not initialized")
        return await self._http_session.get(url, params=params, headers=headers or {})

    async def post(
        self,
        url: str,
        json_data: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> Any:
        if not self._initialized or self._http_session is None:
            raise SessionError("Session not initialized")
        return await self._http_session.post(url, json_data=json_data, headers=headers or {})

    async def close(self) -> None:
        logger.debug("SapphireSession: closing")
        if self._browser_session:
            await self._browser_session.close()
            self._browser_session = None
        if self._http_session:
            await self._http_session.close()
            self._http_session = None
        self._initialized = False

    async def __aenter__(self) -> "SapphireSession":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    @property
    def is_initialized(self) -> bool:
        return self._initialized


def create_session(
    timeout: float = 30.0,
    max_retries: int = 5,
    proxy_types: Optional[list[ProxyType]] = None,
    browser_type: Optional[BrowserType] = None,
) -> SapphireSession:
    config = SessionConfig(
        timeout=timeout,
        max_retries=max_retries,
        proxy_types=proxy_types or [ProxyType.DATAIMPULSE_SESSION],
        browser_type=browser_type or BrowserType.CAMOUFOX,
    )
    return SapphireSession(config)

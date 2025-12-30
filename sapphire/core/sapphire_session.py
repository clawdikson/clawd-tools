"""Session wrapper for Sapphire API requests.

Uses ResilientBrowserSession for all requests - no HTTP session fallback.
All requests go through browser's page.request API.
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
from core.session import ResilientBrowserSession
from core.session.backend import BrowserType

from sapphire.core.exceptions import SessionError


@dataclass
class SessionConfig:
    """Configuration for Sapphire browser session."""

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
    """Browser-based session for Sapphire API requests.

    All requests use ResilientBrowserSession.get/post which go through
    the browser's page.request API - no curl_cffi/httpx fallback.
    """

    def __init__(self, config: SessionConfig):
        self.config = config
        self._browser_session: Optional[ResilientBrowserSession] = None
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self, auth_url: str) -> None:
        async with self._lock:
            if self._initialized:
                return

            logger.info(f"SapphireSession: initializing browser with {auth_url}")

            self._browser_session = ResilientBrowserSession(
                login_url=auth_url,
                proxy_types=self.config.proxy_types,
                browser_type=self.config.browser_type,
            )
            await self._browser_session.login(auth_url)

            self._initialized = True
            logger.info("SapphireSession: browser session ready")

    async def request(self, url: str, **kwargs: Any) -> Any:
        if not self._initialized or self._browser_session is None:
            raise SessionError("Session not initialized. Call initialize() first.")
        response = await self._browser_session.get(url, **kwargs)
        return response.json() if hasattr(response, 'json') else response

    async def get(
        self,
        url: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> Any:
        if not self._initialized or self._browser_session is None:
            raise SessionError("Session not initialized")
        response = await self._browser_session.get(url, params=params, headers=headers)
        return response.json() if hasattr(response, 'json') else response

    async def post(
        self,
        url: str,
        json_data: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> Any:
        if not self._initialized or self._browser_session is None:
            raise SessionError("Session not initialized")
        response = await self._browser_session.post(url, json_data=json_data or {}, headers=headers)
        return response.json() if hasattr(response, 'json') else response

    async def get_cookies(self) -> list[dict]:
        if not self._browser_session:
            raise SessionError("Session not initialized")
        return await self._browser_session.get_cookies()

    async def get_user_agent(self) -> str:
        if not self._browser_session:
            raise SessionError("Session not initialized")
        return await self._browser_session.get_user_agent()

    async def close(self) -> None:
        logger.debug("SapphireSession: closing")
        if self._browser_session:
            await self._browser_session.close()
            self._browser_session = None
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

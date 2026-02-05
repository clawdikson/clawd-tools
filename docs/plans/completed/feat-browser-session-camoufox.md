# BrowserSession Backend Selection (Patchright/Playwright/Camoufox) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a selectable browser backend to `BrowserSession` enabling callers to choose between Patchright, Playwright, and Camoufox while maintaining the existing async interface.

**Architecture:** Enum-based backend selection with backend-specific initialization/cleanup in BrowserSession. The existing concurrency patterns (\_init_lock, \_request_semaphore, \_active_cond) remain unchanged. ResilientBrowserSession passes through the new parameter without modification to its session lifecycle.

**Tech Stack:** patchright>=1.0.0 (existing), playwright>=1.55.0 (new), camoufox[geoip]>=0.4.11 (new)

---

## Reference: Existing Implementation Analysis

### Current BrowserSession Architecture (`core/session/browser_session.py`)

**Key concurrency patterns (MUST preserve):**

- `_init_lock`: AsyncIO Lock for single-flight initialization (lines 66, 169)
- `_request_semaphore`: Semaphore for concurrent request limiting (lines 63, 324, 352, 376)
- `_active_cond`: Condition for active operation tracking (lines 69-70, 133-152)
- `_closing` flag: Prevents new work during shutdown (lines 54, 136, 173, 277)

**Current instance variables (lines 47-60):**

```python
self._playwright = None
self._browser: Browser | None = None
self._context: BrowserContext | None = None
self._page: Page | None = None
self._initialized = False
self._page_ready = False
self._closing = False
```

**Initialization flow (`_ensure_initialized`, lines 158-213):**

1. Fast path check without lock (line 163)
2. Get proxy config before lock (line 167)
3. Double-check under lock (lines 169-174)
4. Start playwright (line 179)
5. Launch Chromium with args (lines 181-196)
6. Create context with proxy auth (lines 198-204)
7. Create page (line 206)

**Cleanup flow (`close`, lines 267-304):**

1. Set `_closing = True` under lock (line 277)
2. Wait for active operations (line 279)
3. Close page → context → browser → playwright.stop() (lines 288-295)

### ResilientBrowserSession (`core/session/resilient_session.py`)

**Creates BrowserSession at lines 140-145:**

```python
new_session = BrowserSession(
    proxy_types=self._proxy_types,
    proxy_manager=proxy_manager,
    browser_id=self._browser_id,
    max_concurrent_requests=self._max_concurrent_requests,
)
```

**Key pattern:** ResilientBrowserSession only needs to pass through `browser_type` - no other changes required.

### Camoufox Reference Implementation (`audiobee_anthem_new/browser/browser_hrequests.py`)

**AsyncCamoufox usage pattern (lines 130-148):**

```python
async with AsyncCamoufox(
    headless=True,
    enable_cache=True,
    proxy=proxy_config,  # dict: {server, username, password}
    exclude_addons=[DefaultAddons.UBO],
) as browser:
    page = await browser.new_page()
    await page.goto("https://findcare.anthem.com")
```

**Key differences from Playwright/Patchright:**

- `AsyncCamoufox` returns a context-like object (not a browser)
- No separate `async_playwright().start()` call
- Proxy format: dict with server/username/password (not separate http_credentials)
- Cleanup via context manager `__aexit__()` (not explicit close calls)

---

## Implementation Steps

### Task 1: Add BrowserType Enum and Update Dependencies

**Files:**

- Create: `core/session/backend.py`
- Modify: `core/session/__init__.py:1-6`
- Modify: `core/pyproject.toml:6-26`

**Step 1: Create backend enum module**

Create file `core/session/backend.py`:

```python
"""Browser backend type definitions."""

from enum import Enum


class BrowserType(str, Enum):
    """Supported browser automation backends.

    PATCHRIGHT: Playwright fork with anti-detection (default, current behavior)
    PLAYWRIGHT: Standard Playwright library
    CAMOUFOX: Firefox-based anti-detection browser
    """

    PATCHRIGHT = "patchright"
    PLAYWRIGHT = "playwright"
    CAMOUFOX = "camoufox"
```

**Step 2: Run test to verify module loads**

Run: `python -c "from core.session.backend import BrowserType; print(BrowserType.PATCHRIGHT)"`
Expected: `BrowserType.PATCHRIGHT`

**Step 3: Update session **init**.py exports**

Modify `core/session/__init__.py`:

```python
from .backend import BrowserType
from .browser_session import BrowserSession
from .http_session import HttpSession, RetryConfig
from .resilient_session import ResilientBrowserSession

__all__ = ["BrowserType", "BrowserSession", "HttpSession", "ResilientBrowserSession", "RetryConfig"]
```

**Step 4: Add dependencies to pyproject.toml**

Modify `core/pyproject.toml` dependencies array (add after line 14 `patchright>=1.0.0`):

```toml
    "playwright>=1.55.0",
    "camoufox[geoip]>=0.4.11",
```

**Step 5: Update lock file**

Run: `cd core && uv lock`
Expected: Lock file updated with playwright and camoufox dependencies

**Step 6: Commit**

```bash
git add core/session/backend.py core/session/__init__.py core/pyproject.toml core/uv.lock
git commit -m "feat(session): add BrowserType enum and backend dependencies

- Add BrowserType enum (PATCHRIGHT, PLAYWRIGHT, CAMOUFOX)
- Add playwright>=1.55.0 and camoufox[geoip]>=0.4.11 to dependencies
- Export BrowserType from core.session"
```

---

### Task 2: Add browser_type Parameter to BrowserSession

**Files:**

- Modify: `core/session/browser_session.py:29-70`
- Test: manual verification

**Step 1: Import BrowserType enum**

Modify `core/session/browser_session.py` line 16, change:

```python
from patchright.async_api import async_playwright, Browser, BrowserContext, Page
```

To:

```python
from patchright.async_api import async_playwright as patchright_playwright
from patchright.async_api import Browser, BrowserContext, Page

from .backend import BrowserType
```

**Step 2: Add browser_type parameter to **init****

Modify `core/session/browser_session.py` `__init__` method (around lines 40-60), add `browser_type` parameter:

```python
def __init__(
    self,
    proxy_types: List[ProxyType] | List[str] | None = None,
    proxy_manager: ProxyManager | None = None,
    browser_id: int = 0,
    max_concurrent_requests: int = 5,
    browser_type: BrowserType | str = BrowserType.PATCHRIGHT,
):
    # Normalize browser_type to enum
    if isinstance(browser_type, str):
        browser_type = BrowserType(browser_type.lower())
    self._browser_type = browser_type

    self._playwright = None
    self._browser: Browser | None = None
    self._context: BrowserContext | None = None
    self._page: Page | None = None

    # Camoufox-specific: stores the AsyncCamoufox instance
    self._camoufox = None
```

Keep all existing instance variables after the new ones.

**Step 3: Verify the parameter is accepted**

Run: `python -c "from core.session import BrowserSession, BrowserType; BrowserSession(browser_type=BrowserType.PATCHRIGHT)"`
Expected: No error (session object created)

**Step 4: Commit**

```bash
git add core/session/browser_session.py
git commit -m "feat(session): add browser_type parameter to BrowserSession

- Accept BrowserType enum or string (auto-converted)
- Default to PATCHRIGHT (preserves current behavior)
- Add _camoufox instance variable for Camoufox backend"
```

---

### Task 3: Implement Backend-Specific Initialization

**Files:**

- Modify: `core/session/browser_session.py:158-213`

**Step 1: Add lazy imports at module level**

Add after line 19 in `core/session/browser_session.py`:

```python
# Lazy imports for optional backends
_playwright_module = None
_camoufox_module = None


def _get_playwright():
    """Lazy import for standard Playwright."""
    global _playwright_module
    if _playwright_module is None:
        from playwright.async_api import async_playwright
        _playwright_module = async_playwright
    return _playwright_module


def _get_camoufox():
    """Lazy import for Camoufox."""
    global _camoufox_module
    if _camoufox_module is None:
        from camoufox.async_api import AsyncCamoufox
        _camoufox_module = AsyncCamoufox
    return _camoufox_module
```

**Step 2: Replace `_ensure_initialized` with backend-aware version**

Replace the entire `_ensure_initialized` method (lines 158-213) with:

```python
async def _ensure_initialized(self) -> None:
    """
    Initialize browser if not already running (single-flight, concurrency-safe).
    Routes to backend-specific initialization based on self._browser_type.
    """
    # Check fast path without lock
    if self._initialized:
        return

    # Get proxy config before acquiring lock (safe to call multiple times)
    proxy_config = await self._get_proxy_config()

    async with self._init_lock:
        # Double-check after acquiring lock
        if self._initialized:
            return
        if self._closing:
            raise RuntimeError("BrowserSession is closing; cannot initialize.")

        # Route to backend-specific initialization
        try:
            if self._browser_type == BrowserType.CAMOUFOX:
                await self._init_camoufox(proxy_config)
            else:
                await self._init_playwright(proxy_config)

            self._page_ready = False
            self._initialized = True
        except Exception:
            # Best-effort cleanup, then re-raise
            await self._force_close_locked()
            raise

async def _init_playwright(self, proxy_config) -> None:
    """Initialize Patchright or Playwright backend."""
    if self._browser_type == BrowserType.PLAYWRIGHT:
        self._playwright = await _get_playwright()().start()
    else:
        # Default: Patchright
        self._playwright = await patchright_playwright().start()

    req_args = [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
    ]

    if proxy_config and not proxy_config.is_empty():
        logger.info(f"BrowserSession: launching {self._browser_type.value} with proxy={proxy_config.server}")
        req_args.append(f"--proxy-server={proxy_config.server}")
    else:
        logger.info(f"BrowserSession: launching {self._browser_type.value} without proxy")

    self._browser = await self._playwright.chromium.launch(
        headless=False,
        args=req_args,
    )

    if proxy_config and not proxy_config.is_empty():
        logger.debug("BrowserSession: creating context with proxy auth")
        self._context = await self._browser.new_context(
            http_credentials=proxy_config.to_http_credentials()
        )
    else:
        self._context = await self._browser.new_context()

    self._page = await self._context.new_page()

async def _init_camoufox(self, proxy_config) -> None:
    """Initialize Camoufox backend.

    Camoufox AsyncCamoufox returns a context-like object directly.
    We store the AsyncCamoufox instance for cleanup via __aexit__.
    """
    AsyncCamoufox = _get_camoufox()

    # Build proxy dict for Camoufox (different format than Playwright)
    camoufox_proxy = None
    if proxy_config and not proxy_config.is_empty():
        logger.info(f"BrowserSession: launching camoufox with proxy={proxy_config.server}")
        camoufox_proxy = {
            "server": f"http://{proxy_config.server}",
            "username": proxy_config.username,
            "password": proxy_config.password,
        }
    else:
        logger.info("BrowserSession: launching camoufox without proxy")

    # Create AsyncCamoufox instance
    self._camoufox = AsyncCamoufox(
        headless=False,
        proxy=camoufox_proxy,
    )

    # Enter the context manager to get the browser context
    self._context = await self._camoufox.__aenter__()

    # Camoufox returns a context, not a browser
    self._browser = None
    self._playwright = None

    # Create page from context
    self._page = await self._context.new_page()
```

**Step 3: Verify Patchright still works**

Run: `python -c "
import asyncio
from core.session import BrowserSession, BrowserType

async def test():
session = BrowserSession(browser_type=BrowserType.PATCHRIGHT)
await session.\_ensure_initialized()
print(f'Initialized: {session.\_initialized}')
print(f'Page: {session.\_page is not None}')
await session.close()

asyncio.run(test())
"`

Expected:

```
BrowserSession: launching patchright without proxy
Initialized: True
Page: True
BrowserSession: closed
```

**Step 4: Commit**

```bash
git add core/session/browser_session.py
git commit -m "feat(session): implement backend-specific initialization

- Add lazy imports for playwright and camoufox
- Route _ensure_initialized to backend-specific methods
- _init_playwright handles PATCHRIGHT and PLAYWRIGHT
- _init_camoufox handles CAMOUFOX with context manager pattern"
```

---

### Task 4: Implement Backend-Specific Cleanup

**Files:**

- Modify: `core/session/browser_session.py:231-304`

**Step 1: Update \_force_close_locked for Camoufox**

Replace `_force_close_locked` method (lines 231-254) with:

```python
async def _force_close_locked(self) -> None:
    """
    Force close resources. Caller must hold _init_lock.
    Does NOT wait for in-flight operations (used only when init failed or as a last resort).
    """
    # Camoufox cleanup via __aexit__
    if self._camoufox:
        try:
            await self._camoufox.__aexit__(None, None, None)
        except Exception:
            pass
        self._camoufox = None

    # Playwright/Patchright cleanup
    for resource in [self._page, self._context, self._browser]:
        if resource:
            try:
                await resource.close()
            except Exception:
                pass

    if self._playwright:
        try:
            await self._playwright.stop()
        except Exception:
            pass

    self._page = None
    self._context = None
    self._browser = None
    self._playwright = None
    self._page_ready = False
    self._initialized = False
```

**Step 2: Update close method for Camoufox**

Replace `close` method (lines 267-304) with:

```python
async def close(self) -> None:
    """
    Graceful close:
    - Prevents new operations from starting
    - Waits for in-flight operations to finish
    - Then closes resources
    """
    async with self._init_lock:
        if not self._initialized:
            return
        self._closing = True

    await self._wait_for_no_active_operations()

    async with self._init_lock:
        # Another coroutine might have already closed
        if not self._initialized:
            self._closing = False
            return

        try:
            # Camoufox cleanup via __aexit__
            if self._camoufox:
                await self._camoufox.__aexit__(None, None, None)
                self._camoufox = None
            else:
                # Playwright/Patchright cleanup
                if self._page:
                    await self._page.close()
                if self._context:
                    await self._context.close()
                if self._browser:
                    await self._browser.close()
                if self._playwright:
                    await self._playwright.stop()

            logger.info(f"BrowserSession: closed ({self._browser_type.value})")
        finally:
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None
            self._camoufox = None
            self._page_ready = False
            self._initialized = False
            self._closing = False
```

**Step 3: Verify cleanup works**

Run: `python -c "
import asyncio
from core.session import BrowserSession, BrowserType

async def test():
session = BrowserSession(browser_type=BrowserType.PATCHRIGHT)
await session.\_ensure_initialized()
await session.close()
print(f'After close - initialized: {session.\_initialized}')
print(f'After close - page: {session.\_page}')

asyncio.run(test())
"`

Expected:

```
BrowserSession: closed (patchright)
After close - initialized: False
After close - page: None
```

**Step 4: Commit**

```bash
git add core/session/browser_session.py
git commit -m "feat(session): implement backend-specific cleanup

- Handle Camoufox cleanup via __aexit__ pattern
- Clean up _camoufox instance variable on close
- Log browser_type in close message"
```

---

### Task 5: Update ResilientBrowserSession

**Files:**

- Modify: `core/session/resilient_session.py:63-100, 140-145`

**Step 1: Import BrowserType**

Add to imports in `core/session/resilient_session.py` line 12:

```python
from .backend import BrowserType
```

**Step 2: Add browser_type to **init****

Modify `__init__` method (lines 73-85) to add `browser_type` parameter:

```python
def __init__(
    self,
    login_url: str | None = None,
    proxy_types: List[ProxyType] | List[str] | None = None,
    proxy_manager: ProxyManager | None = None,
    browser_id: int = 0,
    max_concurrent_requests: int = 5,
    browser_type: BrowserType | str = BrowserType.PATCHRIGHT,
):
    self._login_url = login_url
    self._proxy_types = proxy_types
    self._proxy_manager = proxy_manager
    self._browser_id = browser_id
    self._max_concurrent_requests = max_concurrent_requests

    # Normalize and store browser_type
    if isinstance(browser_type, str):
        browser_type = BrowserType(browser_type.lower())
    self._browser_type = browser_type
```

**Step 3: Pass browser_type to BrowserSession creation**

Modify `_ensure_session` method, around lines 140-145 where BrowserSession is created:

```python
# Create new session with new proxy config
new_session = BrowserSession(
    proxy_types=self._proxy_types,
    proxy_manager=proxy_manager,
    browser_id=self._browser_id,
    max_concurrent_requests=self._max_concurrent_requests,
    browser_type=self._browser_type,
)
```

**Step 4: Verify ResilientBrowserSession passes through browser_type**

Run: `python -c "
import asyncio
from core.session import ResilientBrowserSession, BrowserType

async def test():
session = ResilientBrowserSession(browser_type=BrowserType.PATCHRIGHT)
print(f'Browser type: {session.\_browser_type}')

asyncio.run(test())
"`

Expected: `Browser type: BrowserType.PATCHRIGHT`

**Step 5: Commit**

```bash
git add core/session/resilient_session.py
git commit -m "feat(session): add browser_type to ResilientBrowserSession

- Accept browser_type parameter (enum or string)
- Pass browser_type to BrowserSession creation"
```

---

### Task 6: Update HealthSparqSession (Optional Enhancement)

**Files:**

- Modify: `healthsparq/core/session.py:39-51, 87-89`

**Step 1: Import BrowserType**

Add to imports in `healthsparq/core/session.py` after line 24:

```python
try:
    from core.session.backend import BrowserType
except ImportError:
    from shared_package.session.backend import BrowserType
```

**Step 2: Add browser_type to SessionConfig**

Modify `SessionConfig` dataclass (lines 39-51):

```python
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
    browser_type: BrowserType = BrowserType.PATCHRIGHT
```

**Step 3: Pass browser_type to ResilientBrowserSession**

Modify `login` method around line 87-89:

```python
self._browser_session = ResilientBrowserSession(
    proxy_types=self.config.proxy_types,
    browser_type=self.config.browser_type,
)
```

**Step 4: Update create_session factory**

Modify `create_session` function (lines 172-199) to accept browser_type:

```python
def create_session(
    cookies: Optional[dict[str, str]] = None,
    user_agent: Optional[str] = None,
    timeout: float = 30.0,
    max_retries: int = 5,
    proxy_types: Optional[list[ProxyType]] = None,
    browser_type: BrowserType | str = BrowserType.PATCHRIGHT,
) -> HealthSparqSession:
    """Create a configured HealthSparq session.

    Args:
        cookies: Optional cookies dict (not used with browser auth)
        user_agent: Optional user agent string
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
        proxy_types: Proxy types for browser session
        browser_type: Browser backend (patchright, playwright, camoufox)

    Returns:
        Configured HealthSparqSession instance
    """
    # Normalize browser_type
    if isinstance(browser_type, str):
        browser_type = BrowserType(browser_type.lower())

    logger.debug(f"HealthSparqSession: creating session (timeout={timeout}, max_retries={max_retries}, browser={browser_type.value})")
    config = SessionConfig(
        timeout=timeout,
        max_retries=max_retries,
        user_agent=user_agent,
        cookies=cookies or {},
        proxy_types=proxy_types or [ProxyType.DECODO_DC_STATIC],
        browser_type=browser_type,
    )
    return HealthSparqSession(config)
```

**Step 5: Commit**

```bash
git add healthsparq/core/session.py
git commit -m "feat(healthsparq): expose browser_type in HealthSparqSession

- Add browser_type to SessionConfig dataclass
- Pass browser_type to ResilientBrowserSession
- Update create_session factory with browser_type parameter"
```

---

### Task 7: Write Unit Tests

**Files:**

- Create: `core/tests/test_browser_backend.py`

**Step 1: Create test file**

Create `core/tests/test_browser_backend.py`:

```python
"""Tests for browser backend selection."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from core.session import BrowserSession, ResilientBrowserSession, BrowserType
from core.session.backend import BrowserType


class TestBrowserType:
    """Tests for BrowserType enum."""

    def test_enum_values(self):
        """BrowserType has expected values."""
        assert BrowserType.PATCHRIGHT.value == "patchright"
        assert BrowserType.PLAYWRIGHT.value == "playwright"
        assert BrowserType.CAMOUFOX.value == "camoufox"

    def test_from_string(self):
        """BrowserType can be created from string."""
        assert BrowserType("patchright") == BrowserType.PATCHRIGHT
        assert BrowserType("playwright") == BrowserType.PLAYWRIGHT
        assert BrowserType("camoufox") == BrowserType.CAMOUFOX


class TestBrowserSessionBackend:
    """Tests for BrowserSession backend selection."""

    def test_default_backend_is_patchright(self):
        """Default browser_type is PATCHRIGHT."""
        session = BrowserSession()
        assert session._browser_type == BrowserType.PATCHRIGHT

    def test_accepts_enum(self):
        """BrowserSession accepts BrowserType enum."""
        session = BrowserSession(browser_type=BrowserType.PLAYWRIGHT)
        assert session._browser_type == BrowserType.PLAYWRIGHT

    def test_accepts_string(self):
        """BrowserSession accepts string and converts to enum."""
        session = BrowserSession(browser_type="camoufox")
        assert session._browser_type == BrowserType.CAMOUFOX

    def test_invalid_string_raises(self):
        """Invalid browser_type string raises ValueError."""
        with pytest.raises(ValueError):
            BrowserSession(browser_type="invalid")

    def test_camoufox_instance_variable_initialized(self):
        """Camoufox backend has _camoufox instance variable."""
        session = BrowserSession(browser_type=BrowserType.CAMOUFOX)
        assert session._camoufox is None  # Not initialized until _ensure_initialized


class TestResilientBrowserSessionBackend:
    """Tests for ResilientBrowserSession backend passthrough."""

    def test_default_backend_is_patchright(self):
        """Default browser_type is PATCHRIGHT."""
        session = ResilientBrowserSession()
        assert session._browser_type == BrowserType.PATCHRIGHT

    def test_accepts_enum(self):
        """ResilientBrowserSession accepts BrowserType enum."""
        session = ResilientBrowserSession(browser_type=BrowserType.CAMOUFOX)
        assert session._browser_type == BrowserType.CAMOUFOX

    def test_accepts_string(self):
        """ResilientBrowserSession accepts string and converts."""
        session = ResilientBrowserSession(browser_type="playwright")
        assert session._browser_type == BrowserType.PLAYWRIGHT


@pytest.mark.asyncio
class TestBrowserSessionInitialization:
    """Tests for backend-specific initialization (mocked)."""

    async def test_patchright_uses_patchright_import(self):
        """PATCHRIGHT backend uses patchright module."""
        session = BrowserSession(browser_type=BrowserType.PATCHRIGHT)

        with patch("core.session.browser_session.patchright_playwright") as mock_pw:
            mock_playwright = AsyncMock()
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()

            mock_pw.return_value.start = AsyncMock(return_value=mock_playwright)
            mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)

            await session._ensure_initialized()

            mock_pw.assert_called_once()

    async def test_camoufox_uses_camoufox_import(self):
        """CAMOUFOX backend uses camoufox module."""
        session = BrowserSession(browser_type=BrowserType.CAMOUFOX)

        with patch("core.session.browser_session._get_camoufox") as mock_get_cf:
            mock_camoufox_class = MagicMock()
            mock_camoufox_instance = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()

            mock_get_cf.return_value = mock_camoufox_class
            mock_camoufox_class.return_value = mock_camoufox_instance
            mock_camoufox_instance.__aenter__ = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)

            await session._ensure_initialized()

            mock_get_cf.assert_called_once()
            mock_camoufox_instance.__aenter__.assert_called_once()


@pytest.mark.asyncio
class TestBrowserSessionCleanup:
    """Tests for backend-specific cleanup (mocked)."""

    async def test_camoufox_cleanup_calls_aexit(self):
        """CAMOUFOX cleanup calls __aexit__ on the instance."""
        session = BrowserSession(browser_type=BrowserType.CAMOUFOX)

        # Simulate initialized state
        mock_camoufox = AsyncMock()
        mock_camoufox.__aexit__ = AsyncMock()
        session._camoufox = mock_camoufox
        session._initialized = True
        session._page = AsyncMock()
        session._context = AsyncMock()

        await session.close()

        mock_camoufox.__aexit__.assert_called_once_with(None, None, None)
        assert session._camoufox is None
```

**Step 2: Run tests**

Run: `cd core && pytest tests/test_browser_backend.py -v`

Expected: All tests pass

**Step 3: Commit**

```bash
git add core/tests/test_browser_backend.py
git commit -m "test(session): add browser backend selection tests

- Test BrowserType enum values and string conversion
- Test BrowserSession/ResilientBrowserSession accept browser_type
- Test backend-specific initialization routing (mocked)
- Test Camoufox cleanup calls __aexit__"
```

---

### Task 8: Update Documentation

**Files:**

- Modify: `core/CLAUDE.md` (Session Module section)

**Step 1: Update Session Module documentation**

Add to the Session Module section in `core/CLAUDE.md`:

````markdown
### Browser Backend Selection

BrowserSession supports multiple browser backends via the `browser_type` parameter:

```python
from core.session import BrowserSession, ResilientBrowserSession, BrowserType

# Default: Patchright (anti-detection Playwright fork)
session = BrowserSession()

# Standard Playwright
session = BrowserSession(browser_type=BrowserType.PLAYWRIGHT)

# Camoufox (Firefox-based anti-detection)
session = BrowserSession(browser_type=BrowserType.CAMOUFOX)

# String also accepted
session = BrowserSession(browser_type="camoufox")

# ResilientBrowserSession passes through
resilient = ResilientBrowserSession(
    login_url="https://example.com",
    browser_type=BrowserType.CAMOUFOX,
)
```
````

**Backend Comparison:**

| Backend    | Engine   | Anti-Detection | Use Case                 |
| ---------- | -------- | -------------- | ------------------------ |
| PATCHRIGHT | Chromium | Medium         | Default, most sites      |
| PLAYWRIGHT | Chromium | Low            | Sites without detection  |
| CAMOUFOX   | Firefox  | High           | Anti-bot protected sites |

````

**Step 2: Commit**

```bash
git add core/CLAUDE.md
git commit -m "docs(session): document browser backend selection

- Add Browser Backend Selection section to Session Module
- Document BrowserType enum values
- Add backend comparison table"
````

---

## Verification Checklist

After completing all tasks, verify:

- [ ] `BrowserType.PATCHRIGHT` is the default (existing behavior preserved)
- [ ] `BrowserSession(browser_type="playwright")` works
- [ ] `BrowserSession(browser_type=BrowserType.CAMOUFOX)` works
- [ ] `ResilientBrowserSession` passes through browser_type
- [ ] All existing tests still pass: `cd core && pytest`
- [ ] New tests pass: `cd core && pytest tests/test_browser_backend.py -v`
- [ ] Lock file updated: `core/uv.lock` includes playwright and camoufox

---

## Risks & Mitigations

| Risk                                  | Mitigation                                                   |
| ------------------------------------- | ------------------------------------------------------------ |
| Camoufox API changes                  | Pin version `camoufox[geoip]>=0.4.11,<0.5.0` if issues arise |
| Import errors if dependencies missing | Lazy imports only load when backend selected                 |
| Different proxy formats               | Backend-specific proxy config conversion in \_init methods   |
| Camoufox context cleanup              | Always call `__aexit__` even on errors                       |
| Breaking existing code                | Default to PATCHRIGHT preserves current behavior             |

---

## Not In Scope (Future Work)

- Camoufox-specific options (addons, geoip, screen resolution)
- Playwright browser choice (Firefox, WebKit via PLAYWRIGHT backend)
- Shared browser pool across sessions
- Dynamic backend switching mid-session

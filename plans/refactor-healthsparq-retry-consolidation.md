# Plan: Consolidate HTTP Retry Logic into Core Package

> **Date**: 2025-12-28
> **Status**: Ready for Implementation
> **Priority**: P1 (High Priority)

## Executive Summary

The `healthsparq/core/session.py` contains **duplicate HTTP retry logic** (~40 LOC) that should be consolidated into `core/session/http_session.py`. Currently:

- `core/session/http_session.py` has **NO retry logic** (just raw HTTP calls)
- `healthsparq/core/session.py` wraps `HttpSession` and adds its own `_request_with_retry()` method
- This creates **duplicate code** that should live in the central `core/` package

### Problem Statement

```
healthsparq/core/session.py:132-170  →  _request_with_retry() (40 LOC)
                                          - Exponential backoff
                                          - 5 retries
                                          - 401/403 auth error handling
                                          - 500+ server error handling

core/session/http_session.py         →  NO retry logic
                                          - Just raw HTTP calls
                                          - Any project using HttpSession must add own retries
```

### Solution

Add retry logic to `core/session/http_session.py` so:

1. All projects using `HttpSession` get retry logic automatically
2. `healthsparq/core/session.py` can remove its duplicate implementation
3. Single source of truth for HTTP retry configuration

### Key Findings

| Category               | Status                             | Details                                                                     |
| ---------------------- | ---------------------------------- | --------------------------------------------------------------------------- |
| **HTTP Retry Logic**   | ❌ Duplicate in healthsparq        | ~40 LOC should move to core/session/http_session.py                         |
| **Normalization**      | ✅ Already consolidated (Dec 2025) | `normalize_zip_code`, `deduplicate_by_npi` imported from `core/mapper/`     |
| **Browser retry**      | ✅ Correctly in core               | `ResilientBrowserSession._execute_with_recreation()` handles browser errors |
| **Session management** | ✅ Uses core                       | `HealthSparqSession` wraps `core.session.HttpSession`                       |

---

## Current Architecture

### The Problem: Two Different Retry Layers

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    HEALTHSPARQ SESSION LAYER                             │
│  healthsparq/core/session.py (HealthSparqSession)                       │
│                                                                          │
│  _request_with_retry() - 40 LOC of duplicate code:                      │
│  • for attempt in range(max_retries):                                   │
│  •     try: response = await method(url, **kwargs)                      │
│  •     if 401/403: invalidate session                                   │
│  •     if < 500: return response                                        │
│  •     else: server error                                               │
│  •     sleep(backoff_factor ** attempt)                                 │
│  • raise last_exception                                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    CORE HTTP SESSION LAYER                               │
│  core/session/http_session.py (HttpSession)                             │
│                                                                          │
│  NO RETRY LOGIC - just raw HTTP calls:                                  │
│  • get(url, params, headers) → curl_cffi request                        │
│  • post(url, json_data, headers) → curl_cffi request                    │
│  • No exponential backoff                                                │
│  • No error handling                                                     │
│  • No auth error detection                                               │
└─────────────────────────────────────────────────────────────────────────┘
```

### Browser Layer (Already Correct)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        BROWSER LAYER                                     │
│  core/session/resilient_session.py (ResilientBrowserSession)            │
│                                                                          │
│  _execute_with_recreation() - Browser-specific retry logic:             │
│  • Max 3 retries per operation                                          │
│  • Session death detection (browser crash, disconnection)               │
│  • Consecutive failure tracking (3 failures → recreate)                 │
│  • Proxy rotation on IP blocks                                          │
│  • 429 handling: 60s wait                                               │
│  • Generation-based graceful shutdown                                   │
│                                                                          │
│  This is DIFFERENT from HTTP retry and should stay separate!            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Add Retry Logic to `core/session/http_session.py`

**File**: `core/session/http_session.py`

**Changes**:

1. Add `RetryConfig` dataclass with configurable parameters
2. Add `_request_with_retry()` method to `HttpSession`
3. Update `get()` and `post()` to use retry wrapper
4. Add callback hook for auth error handling (session invalidation)

**New Code** (~50 LOC):

```python
# core/session/http_session.py

from dataclasses import dataclass, field
import asyncio
from typing import Callable, Optional, Awaitable

@dataclass
class RetryConfig:
    """Configuration for HTTP request retry behavior."""
    max_retries: int = 5
    backoff_factor: float = 2.0
    max_backoff: float = 30.0
    retry_on_status: set[int] = field(default_factory=lambda: {429, 500, 502, 503, 504})
    auth_error_status: set[int] = field(default_factory=lambda: {401, 403})

class HttpSession:
    def __init__(
        self,
        ...,
        retry_config: RetryConfig | None = None,
        on_auth_error: Callable[[], Awaitable[None]] | None = None,
    ):
        self._retry_config = retry_config or RetryConfig()
        self._on_auth_error = on_auth_error  # Callback for auth errors
        ...

    async def _request_with_retry(
        self,
        method: Callable,
        url: str,
        **kwargs,
    ) -> Response:
        """Execute HTTP request with exponential backoff retry."""
        last_exception: Exception | None = None
        config = self._retry_config

        for attempt in range(config.max_retries):
            try:
                response = await method(url, **{k: v for k, v in kwargs.items() if v is not None})

                # Handle auth errors (401/403)
                if response.status_code in config.auth_error_status:
                    logger.warning(f"HttpSession: auth error {response.status_code} - {url}")
                    if self._on_auth_error:
                        await self._on_auth_error()
                    last_exception = Exception(f"Auth error: {response.status_code}")

                # Success - return response
                elif response.status_code not in config.retry_on_status:
                    return response

                # Retryable error
                else:
                    logger.warning(f"HttpSession: retryable error {response.status_code} - {url}")
                    last_exception = Exception(f"Server error: {response.status_code}")

            except Exception as e:
                logger.error(f"HttpSession: request failed: {e}")
                last_exception = e

            # Exponential backoff before retry
            if attempt < config.max_retries - 1:
                sleep_time = min(
                    config.backoff_factor ** attempt,
                    config.max_backoff,
                )
                logger.debug(f"HttpSession: retrying after {sleep_time:.1f}s (attempt {attempt+1}/{config.max_retries})")
                await asyncio.sleep(sleep_time)

        if last_exception:
            raise last_exception
        raise RuntimeError("Request failed with no exception")

    async def get(self, url: str, params: dict | None = None, headers = {}) -> Response:
        """Make a GET request with automatic retry."""
        self._ensure_session()
        logger.debug(f"HttpSession: GET {url}")
        return await self._request_with_retry(
            self._session.get, url, params=params, headers=headers
        )

    async def post(self, url: str, json_data: dict | None = None, headers = {}) -> Response:
        """Make a POST request with automatic retry."""
        self._ensure_session()
        logger.debug(f"HttpSession: POST {url}")
        return await self._request_with_retry(
            self._session.post, url, json=json_data, headers=headers
        )
```

---

### Phase 2: Simplify `healthsparq/core/session.py`

**File**: `healthsparq/core/session.py`

**Changes**:

1. Remove `_request_with_retry()` method (40 LOC)
2. Pass `on_auth_error` callback to `HttpSession` for session invalidation
3. Simplify `get()` and `post()` to just delegate to `HttpSession`

**Before** (current):

```python
# healthsparq/core/session.py

async def get(self, url: str, params=None, headers=None):
    session = await self._ensure_http_session()
    return await self._request_with_retry(
        session.get, url, params=params, headers=headers
    )

async def _request_with_retry(self, method, url: str, **kwargs):
    # 40 lines of retry logic...
```

**After** (consolidated):

```python
# healthsparq/core/session.py

async def _invalidate_session(self):
    """Callback for auth errors - invalidate session for refresh."""
    self._initialized = False

async def get(self, url: str, params=None, headers=None):
    session = await self._ensure_http_session()
    return await session.get(url, params=params, headers=headers)
    # Retry logic now handled by HttpSession internally
```

---

### Phase 3: Update Tests

**Files**:

- `core/tests/test_session.py` - Add tests for retry logic
- `healthsparq/tests/test_session.py` - Update tests for simplified session

**Test Cases**:

```python
# core/tests/test_session.py

@pytest.mark.asyncio
async def test_http_session_retries_on_500():
    """Verify HttpSession retries on 500 status codes."""
    ...

@pytest.mark.asyncio
async def test_http_session_exponential_backoff():
    """Verify exponential backoff timing."""
    ...

@pytest.mark.asyncio
async def test_http_session_auth_error_callback():
    """Verify on_auth_error callback is called on 401/403."""
    ...

@pytest.mark.asyncio
async def test_http_session_no_retry_on_success():
    """Verify successful responses don't trigger retry."""
    ...
```

---

## Code Diff Summary

### Files Modified

| File                                | Change Type | LOC Change | Description                              |
| ----------------------------------- | ----------- | ---------- | ---------------------------------------- |
| `core/session/http_session.py`      | ADD         | +50        | Add RetryConfig + \_request_with_retry() |
| `core/session/__init__.py`          | ADD         | +1         | Export RetryConfig                       |
| `healthsparq/core/session.py`       | REMOVE      | -40        | Remove duplicate \_request_with_retry()  |
| `core/tests/test_session.py`        | ADD         | +80        | Add retry logic tests                    |
| `healthsparq/tests/test_session.py` | UPDATE      | ~20        | Update tests for simplified session      |

**Net Impact**: ~+10 LOC (moving 40 LOC to core, adding 50 LOC with tests)

---

## Design Decisions

### Why Add to HttpSession (Not ResilientBrowserSession)?

| Layer                     | Purpose           | Retry Strategy                     |
| ------------------------- | ----------------- | ---------------------------------- |
| `ResilientBrowserSession` | Browser lifecycle | Session recreation, proxy rotation |
| `HttpSession`             | HTTP API calls    | Exponential backoff, auth handling |

**These are fundamentally different**:

- Browser errors = need new browser instance (expensive, 3 retries)
- HTTP errors = just retry the request (cheap, 5 retries)

### Why Callback Pattern for Auth Errors?

The `on_auth_error` callback allows `HealthSparqSession` to invalidate its session state without `HttpSession` knowing about the higher-level session management:

```python
# HealthSparqSession can inject session-specific logic
http_session = HttpSession(
    retry_config=RetryConfig(max_retries=5),
    on_auth_error=self._invalidate_session,  # Sets self._initialized = False
)
```

### Backward Compatibility

- **Default behavior unchanged**: `RetryConfig()` uses sensible defaults (5 retries, 2.0 backoff)
- **Opt-out available**: Pass `retry_config=None` to disable retries (raw HTTP)
- **Existing imports work**: No changes to public API

---

## Acceptance Criteria

- [ ] `core/session/http_session.py` has `RetryConfig` dataclass
- [ ] `core/session/http_session.py` has `_request_with_retry()` method
- [ ] `HttpSession.get()` and `HttpSession.post()` use retry logic
- [ ] `on_auth_error` callback is called on 401/403 responses
- [ ] `healthsparq/core/session.py` removes duplicate `_request_with_retry()`
- [ ] All existing tests pass
- [ ] New tests cover retry scenarios
- [ ] No behavior changes for healthsparq scraping

---

## References

### Internal Files

- `healthsparq/core/session.py:132-170` - Current duplicate retry logic
- `core/session/http_session.py` - Target for consolidation
- `core/session/resilient_session.py:261-314` - Browser retry logic (keep separate)

### External Best Practices

- [Tenacity Documentation](https://tenacity.readthedocs.io/) - Recommended retry library patterns
- [AWS Exponential Backoff](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/) - Jitter patterns
- [Multi-Layer Retry Architecture](https://blog.bytebytego.com/p/a-guide-to-retry-pattern-in-distributed) - ByteByteGo

---

## Next Steps

1. **Create bd issue** for implementation tracking
2. **Implement Phase 1**: Add retry logic to `core/session/http_session.py`
3. **Implement Phase 2**: Simplify `healthsparq/core/session.py`
4. **Implement Phase 3**: Add/update tests
5. **Verify**: Run healthsparq tests to ensure no behavior changes

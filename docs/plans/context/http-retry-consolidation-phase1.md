# Phase 1 Context: Add Retry Logic to core/session/http_session.py

> **Parent Plan**: `plans/refactor-healthsparq-retry-consolidation.md`
> **Phase**: 1 of 3
> **Status**: Ready for Implementation

## Objective

Add HTTP retry logic with exponential backoff to `core/session/http_session.py` so all projects using `HttpSession` get retry logic automatically.

## Background

### Current State

**File**: `core/session/http_session.py`

The current `HttpSession` class has NO retry logic - just raw HTTP calls:

```python
async def get(self, url: str, params: dict | None = None, headers = {}) -> Response:
    self._ensure_session()
    logger.debug(f"HttpSession: GET {url}")
    response = await self._session.get(url, params=params, headers=headers)
    return Response(response.text, response.status_code)

async def post(self, url: str, json_data: dict | None = None, headers = {}) -> Response:
    self._ensure_session()
    logger.debug(f"HttpSession: POST {url}")
    response = await self._session.post(url, json=json_data, headers=headers)
    return Response(response.text, response.status_code)
```

### Problem

- `healthsparq/core/session.py` has duplicate retry logic (~40 LOC)
- Any project using `HttpSession` must add its own retry logic
- No centralized retry configuration

### Reference Implementation

The retry logic to port from `healthsparq/core/session.py:132-170`:

```python
async def _request_with_retry(self, method, url: str, **kwargs):
    """Execute request with exponential backoff retry."""
    last_exception: Optional[Exception] = None

    for attempt in range(self.config.max_retries):
        try:
            response = await method(url, **{k: v for k, v in kwargs.items() if v is not None})

            # Check for auth errors that might need session refresh
            if response.status_code in [401, 403]:
                logger.warning(f"HealthSparqSession: auth error {response.status_code} - {url}")
                # Invalidate session for refresh
                self._initialized = False
                last_exception = Exception(
                    f"Auth error: {response.status_code} - {url}"
                )
            elif response.status_code < 500:
                return response
            else:
                logger.warning(f"HealthSparqSession: server error {response.status_code} - {url}")
                last_exception = Exception(
                    f"Server error: {response.status_code} - {url}"
                )

        except Exception as e:
            logger.error(f"HealthSparqSession: request failed: {e}")
            last_exception = e

        if attempt < self.config.max_retries - 1:
            sleep_time = min(
                self.config.backoff_factor ** attempt,
                self.config.max_backoff,
            )
            logger.debug(f"HealthSparqSession: retrying after {sleep_time:.1f}s (attempt {attempt+1}/{self.config.max_retries})")
            await asyncio.sleep(sleep_time)

    if last_exception:
        raise last_exception
    raise RuntimeError("Request failed with no exception")
```

## Implementation Tasks

### Task 1.1: Add RetryConfig Dataclass

**Location**: `core/session/http_session.py` (top of file, after imports)

```python
from dataclasses import dataclass, field

@dataclass
class RetryConfig:
    """Configuration for HTTP request retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts (default: 5)
        backoff_factor: Multiplier for exponential backoff (default: 2.0)
        max_backoff: Maximum delay cap in seconds (default: 30.0)
        retry_on_status: HTTP status codes to retry (default: 429, 500-504)
        auth_error_status: Status codes that indicate auth errors (default: 401, 403)
    """
    max_retries: int = 5
    backoff_factor: float = 2.0
    max_backoff: float = 30.0
    retry_on_status: set[int] = field(default_factory=lambda: {429, 500, 502, 503, 504})
    auth_error_status: set[int] = field(default_factory=lambda: {401, 403})
```

### Task 1.2: Add \_request_with_retry() Method

**Location**: `core/session/http_session.py` (in HttpSession class)

```python
async def _request_with_retry(
    self,
    method: Callable,
    url: str,
    **kwargs,
) -> Response:
    """Execute HTTP request with exponential backoff retry.

    Args:
        method: The HTTP method to call (self._session.get or self._session.post)
        url: Request URL
        **kwargs: Additional arguments to pass to the method

    Returns:
        Response object

    Raises:
        Exception: If all retries exhausted
    """
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

            # Success - return response (not in retry list)
            elif response.status_code not in config.retry_on_status:
                return Response(response.text, response.status_code)

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
```

### Task 1.3: Update **init**() Method

**Location**: `core/session/http_session.py` (HttpSession.**init**)

Add new parameters:

```python
def __init__(
    self,
    proxy_types: List[ProxyType] | List[str] | None = None,
    proxy_manager: ProxyManager | None = None,
    browser_id: int = 0,
    max_concurrent_requests: int = 10,
    retry_config: RetryConfig | None = None,  # NEW
    on_auth_error: Callable[[], Awaitable[None]] | None = None,  # NEW
):
    # ... existing code ...
    self._retry_config = retry_config or RetryConfig()  # NEW
    self._on_auth_error = on_auth_error  # NEW
```

### Task 1.4: Update get() Method

**Location**: `core/session/http_session.py` (HttpSession.get)

```python
async def get(self, url: str, params: dict | None = None, headers = {}) -> Response:
    """Make a GET request with automatic retry."""
    self._ensure_session()
    logger.debug(f"HttpSession: GET {url}")
    return await self._request_with_retry(
        self._session.get, url, params=params, headers=headers
    )
```

### Task 1.5: Update post() Method

**Location**: `core/session/http_session.py` (HttpSession.post)

```python
async def post(self, url: str, json_data: dict | None = None, headers = {}) -> Response:
    """Make a POST request with automatic retry."""
    self._ensure_session()
    logger.debug(f"HttpSession: POST {url}")
    return await self._request_with_retry(
        self._session.post, url, json=json_data, headers=headers
    )
```

### Task 1.6: Export RetryConfig

**Location**: `core/session/__init__.py`

Add to exports:

```python
from .http_session import HttpSession, RetryConfig
```

## Key Files

| File                                  | Purpose                          |
| ------------------------------------- | -------------------------------- |
| `core/session/http_session.py`        | Main implementation file         |
| `core/session/__init__.py`            | Public exports                   |
| `healthsparq/core/session.py:132-170` | Reference implementation to port |

## Imports Required

```python
import asyncio
from dataclasses import dataclass, field
from typing import Callable, Awaitable
```

## Acceptance Criteria

- [ ] `RetryConfig` dataclass exists with all fields
- [ ] `_request_with_retry()` method exists and handles all status codes
- [ ] `HttpSession.__init__()` accepts `retry_config` and `on_auth_error`
- [ ] `get()` uses `_request_with_retry()`
- [ ] `post()` uses `_request_with_retry()`
- [ ] `RetryConfig` exported from `core/session/__init__.py`
- [ ] Existing code using HttpSession still works (backward compatible)

## Testing Notes

After implementation, test with:

```python
# Basic usage (default retry)
http = HttpSession()
await http.initialize()
response = await http.get("https://example.com")

# Custom retry config
config = RetryConfig(max_retries=3, backoff_factor=1.5)
http = HttpSession(retry_config=config)

# With auth error callback
async def on_auth_error():
    print("Auth error occurred!")
http = HttpSession(on_auth_error=on_auth_error)
```

## Learnings (Completed - Dec 28, 2025)

### Implementation Notes

1. **RetryConfig was already defined**: The dataclass was already in http_session.py with correct defaults, just needed to export it from **init**.py.

2. **Callable type import**: Added `Callable` and `Awaitable` to the imports from typing module.

3. **Updated docstrings**: Added examples 3 and 4 to HttpSession class docstring showing retry configuration and auth error callback usage.

4. **Response wrapping**: The `_request_with_retry` method wraps the response in `Response(response.text, response.status_code)` to match the expected return type.

5. **Backward compatibility**: All parameters are optional with sensible defaults, so existing code using HttpSession continues to work unchanged.

### Files Modified

- `core/session/http_session.py`: Added \_request_with_retry(), updated **init**, get(), post()
- `core/session/__init__.py`: Added RetryConfig export

### Verification

```bash
python3 << 'EOF'
from core.session.http_session import HttpSession, RetryConfig
# All imports work, defaults verified
EOF
```

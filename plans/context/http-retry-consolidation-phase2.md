# Phase 2 Context: Simplify healthsparq/core/session.py

> **Parent Plan**: `plans/refactor-healthsparq-retry-consolidation.md`
> **Phase**: 2 of 3
> **Depends On**: Phase 1 (core/session/http_session.py must have retry logic)
> **Status**: Blocked - Waiting for Phase 1

## Objective

Remove duplicate retry logic from `healthsparq/core/session.py` and use the consolidated implementation from `core/session/http_session.py`.

## Background

### Current State

**File**: `healthsparq/core/session.py`

The `HealthSparqSession` class currently has its own `_request_with_retry()` method (lines 132-170, ~40 LOC) that duplicates logic that should be in `core/`.

```python
# Current structure (before consolidation)
class HealthSparqSession:
    async def get(self, url, params, headers):
        session = await self._ensure_http_session()
        return await self._request_with_retry(  # Uses local retry
            session.get, url, params=params, headers=headers
        )

    async def _request_with_retry(self, method, url, **kwargs):
        # 40 lines of retry logic that duplicates core
        ...
```

### Target State

```python
# After consolidation
class HealthSparqSession:
    async def get(self, url, params, headers):
        session = await self._ensure_http_session()
        return await session.get(url, params=params, headers=headers)
        # Retry logic now in HttpSession
```

## Implementation Tasks

### Task 2.1: Add \_invalidate_session() Callback

**Location**: `healthsparq/core/session.py` (in HealthSparqSession class)

Add a callback method that will be called by `HttpSession` on auth errors:

```python
async def _invalidate_session(self) -> None:
    """Callback for auth errors - invalidate session for refresh.

    This is called by HttpSession when it encounters 401/403 errors.
    """
    logger.warning("HealthSparqSession: session invalidated due to auth error")
    self._initialized = False
```

### Task 2.2: Update HttpSession Initialization

**Location**: `healthsparq/core/session.py:90-91` (in login() method)

Current:

```python
self._http_session = HttpSession()
await self._http_session.initialize_from_browser(cookies, user_agent)
```

After:

```python
from core.session import RetryConfig

# Create HTTP session with retry config and auth callback
self._http_session = HttpSession(
    retry_config=RetryConfig(
        max_retries=self.config.max_retries,
        backoff_factor=self.config.backoff_factor,
        max_backoff=self.config.max_backoff,
    ),
    on_auth_error=self._invalidate_session,
)
await self._http_session.initialize_from_browser(cookies, user_agent)
```

### Task 2.3: Remove \_request_with_retry() Method

**Location**: `healthsparq/core/session.py:132-170`

Delete the entire `_request_with_retry()` method (~40 LOC).

### Task 2.4: Simplify get() Method

**Location**: `healthsparq/core/session.py:107-117`

Before:

```python
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
```

After:

```python
async def get(
    self,
    url: str,
    params: Optional[dict[str, Any]] = None,
    headers: Optional[dict[str, str]] = None,
):
    """Make GET request."""
    session = await self._ensure_http_session()
    return await session.get(url, params=params, headers=headers)
```

### Task 2.5: Simplify post() Method

**Location**: `healthsparq/core/session.py:119-130`

Before:

```python
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
```

After:

```python
async def post(
    self,
    url: str,
    json_data: Optional[dict[str, Any]] = None,
    data: Optional[dict[str, Any]] = None,
    headers: Optional[dict[str, str]] = None,
):
    """Make POST request."""
    session = await self._ensure_http_session()
    return await session.post(url, json_data=json_data, headers=headers)
```

### Task 2.6: Clean Up SessionConfig (Optional)

**Location**: `healthsparq/core/session.py:38-49`

The `SessionConfig` dataclass has fields that were only used by the now-removed `_request_with_retry()`. These can be kept for backward compatibility or removed:

```python
@dataclass
class SessionConfig:
    """Configuration for HTTP session."""
    timeout: float = 30.0
    max_retries: int = 5        # Still useful for RetryConfig
    backoff_factor: float = 2.0  # Still useful for RetryConfig
    max_backoff: float = 30.0    # Still useful for RetryConfig
    # ... rest unchanged
```

**Decision**: Keep these fields - they're passed to `RetryConfig` in Task 2.2.

## Key Files

| File                           | Purpose                            |
| ------------------------------ | ---------------------------------- |
| `healthsparq/core/session.py`  | Main file to modify                |
| `core/session/http_session.py` | Source of consolidated retry logic |
| `core/session/__init__.py`     | Import RetryConfig from here       |

## Import Changes

Add at top of `healthsparq/core/session.py`:

```python
try:
    from core.session import HttpSession, ResilientBrowserSession, RetryConfig
except ImportError:
    from shared_package.session import HttpSession, ResilientBrowserSession
    # RetryConfig won't exist in legacy - handle gracefully
    RetryConfig = None
```

## Acceptance Criteria

- [ ] `_invalidate_session()` callback method exists
- [ ] `HttpSession` initialized with `RetryConfig` and `on_auth_error` callback
- [ ] `_request_with_retry()` method removed (~40 LOC deleted)
- [ ] `get()` method delegates to `session.get()` directly
- [ ] `post()` method delegates to `session.post()` directly
- [ ] All existing healthsparq tests pass
- [ ] No behavior changes in actual scraping

## Testing Notes

After implementation, verify:

1. **Unit tests pass**:

   ```bash
   cd healthsparq && pytest tests/ -v
   ```

2. **Manual verification** (optional):

   ```bash
   python -m healthsparq run medica_sg --curr 20251228 --dry-run
   ```

3. **Auth error handling works**:
   - Session should invalidate on 401/403
   - Should allow re-login on next request

## Learnings (Completed - Dec 28, 2025)

### Implementation Notes

1. **RetryConfig fallback**: Added `RetryConfig = None` fallback for legacy shared_package environments.

2. **Graceful RetryConfig handling**: Check `if RetryConfig is not None:` before creating config to handle legacy imports.

3. **Headers default value**: Changed headers parameter default from `None` to `headers or {}` to ensure we always pass a dict to HttpSession methods.

4. **Removed ~40 LOC**: Successfully removed `_request_with_retry()` method from HealthSparqSession.

5. **data parameter warning**: Added note that `data` parameter in post() is not used since HttpSession.post() only accepts json_data.

### Files Modified

- `healthsparq/core/session.py`:
  - Added RetryConfig import
  - Added \_invalidate_session() callback
  - Updated login() to pass RetryConfig and on_auth_error to HttpSession
  - Simplified get() and post() to delegate directly to HttpSession
  - Removed ~40 LOC of duplicate \_request_with_retry()

### Verification

```bash
python3 << 'EOF'
from healthsparq.core.session import HealthSparqSession, SessionConfig
session = HealthSparqSession(SessionConfig())
assert not hasattr(session, "_request_with_retry")  # Removed
assert hasattr(session, "_invalidate_session")  # Added
EOF
```

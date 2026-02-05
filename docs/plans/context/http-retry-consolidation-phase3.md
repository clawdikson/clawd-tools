# Phase 3 Context: Update Tests

> **Parent Plan**: `plans/refactor-healthsparq-retry-consolidation.md`
> **Phase**: 3 of 3
> **Depends On**: Phase 1 and Phase 2
> **Status**: Blocked - Waiting for Phase 1 & 2

## Objective

Add comprehensive tests for the new retry logic in `core/session/http_session.py` and update `healthsparq` tests for the simplified session.

## Background

### Test Coverage Needed

1. **core/session** - New retry logic tests
2. **healthsparq/session** - Update tests for simplified session

### Testing Approach

- Use `pytest-asyncio` for async tests
- Mock HTTP responses to test retry behavior
- Verify exponential backoff timing
- Test callback invocation on auth errors

## Implementation Tasks

### Task 3.1: Add Test for Retry on 500 Status Codes

**Location**: `core/tests/test_session.py` (create if doesn't exist)

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from core.session import HttpSession, RetryConfig


@pytest.fixture
def mock_response():
    """Create a mock response object."""
    def _create(status_code: int, text: str = ""):
        response = MagicMock()
        response.status_code = status_code
        response.text = text
        return response
    return _create


@pytest.mark.asyncio
async def test_http_session_retries_on_500(mock_response):
    """Verify HttpSession retries on 500 status codes."""
    # Setup: First two calls return 500, third returns 200
    responses = [
        mock_response(500, "Server Error"),
        mock_response(500, "Server Error"),
        mock_response(200, '{"success": true}'),
    ]

    with patch("core.session.http_session.AsyncSession") as mock_session_cls:
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(side_effect=responses)
        mock_session_cls.return_value = mock_session

        http = HttpSession(retry_config=RetryConfig(max_retries=5, backoff_factor=0.01))
        await http.initialize()

        response = await http.get("https://example.com/api")

        assert response.status_code == 200
        assert mock_session.get.call_count == 3
```

### Task 3.2: Add Test for Exponential Backoff Timing

**Location**: `core/tests/test_session.py`

```python
@pytest.mark.asyncio
async def test_http_session_exponential_backoff(mock_response):
    """Verify exponential backoff timing between retries."""
    responses = [
        mock_response(500, "Server Error"),
        mock_response(500, "Server Error"),
        mock_response(200, "OK"),
    ]

    sleep_times = []
    original_sleep = asyncio.sleep

    async def mock_sleep(seconds):
        sleep_times.append(seconds)
        await original_sleep(0.001)  # Minimal actual sleep

    with patch("core.session.http_session.AsyncSession") as mock_session_cls:
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(side_effect=responses)
        mock_session_cls.return_value = mock_session

        with patch("asyncio.sleep", mock_sleep):
            http = HttpSession(retry_config=RetryConfig(
                max_retries=5,
                backoff_factor=2.0,
                max_backoff=30.0
            ))
            await http.initialize()

            await http.get("https://example.com/api")

            # Verify exponential backoff: 2^0=1, 2^1=2
            assert len(sleep_times) == 2
            assert sleep_times[0] == 1.0  # 2^0
            assert sleep_times[1] == 2.0  # 2^1
```

### Task 3.3: Add Test for Auth Error Callback

**Location**: `core/tests/test_session.py`

```python
@pytest.mark.asyncio
async def test_http_session_auth_error_callback(mock_response):
    """Verify on_auth_error callback is called on 401/403."""
    callback_called = False

    async def auth_callback():
        nonlocal callback_called
        callback_called = True

    responses = [mock_response(401, "Unauthorized")]

    with patch("core.session.http_session.AsyncSession") as mock_session_cls:
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(side_effect=responses * 5)  # All 401s
        mock_session_cls.return_value = mock_session

        http = HttpSession(
            retry_config=RetryConfig(max_retries=3, backoff_factor=0.01),
            on_auth_error=auth_callback
        )
        await http.initialize()

        with pytest.raises(Exception, match="Auth error"):
            await http.get("https://example.com/api")

        assert callback_called is True


@pytest.mark.asyncio
async def test_http_session_auth_error_403(mock_response):
    """Verify 403 also triggers auth error callback."""
    callback_count = 0

    async def auth_callback():
        nonlocal callback_count
        callback_count += 1

    responses = [mock_response(403, "Forbidden")] * 3

    with patch("core.session.http_session.AsyncSession") as mock_session_cls:
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(side_effect=responses)
        mock_session_cls.return_value = mock_session

        http = HttpSession(
            retry_config=RetryConfig(max_retries=3, backoff_factor=0.01),
            on_auth_error=auth_callback
        )
        await http.initialize()

        with pytest.raises(Exception, match="Auth error"):
            await http.get("https://example.com/api")

        # Callback called on each 403
        assert callback_count == 3
```

### Task 3.4: Add Test for Success Without Retry

**Location**: `core/tests/test_session.py`

```python
@pytest.mark.asyncio
async def test_http_session_no_retry_on_success(mock_response):
    """Verify successful responses don't trigger retry."""
    responses = [mock_response(200, '{"data": "test"}')]

    with patch("core.session.http_session.AsyncSession") as mock_session_cls:
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(side_effect=responses)
        mock_session_cls.return_value = mock_session

        http = HttpSession(retry_config=RetryConfig(max_retries=5))
        await http.initialize()

        response = await http.get("https://example.com/api")

        assert response.status_code == 200
        assert mock_session.get.call_count == 1  # No retries


@pytest.mark.asyncio
async def test_http_session_no_retry_on_4xx(mock_response):
    """Verify 4xx errors (except 401/403/429) don't retry."""
    for status in [400, 404, 405, 422]:
        responses = [mock_response(status, "Client Error")]

        with patch("core.session.http_session.AsyncSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session.get = AsyncMock(side_effect=responses)
            mock_session_cls.return_value = mock_session

            http = HttpSession(retry_config=RetryConfig(max_retries=5))
            await http.initialize()

            response = await http.get("https://example.com/api")

            assert response.status_code == status
            assert mock_session.get.call_count == 1  # No retry
```

### Task 3.5: Add Test for RetryConfig Defaults

**Location**: `core/tests/test_session.py`

```python
def test_retry_config_defaults():
    """Verify RetryConfig has sensible defaults."""
    config = RetryConfig()

    assert config.max_retries == 5
    assert config.backoff_factor == 2.0
    assert config.max_backoff == 30.0
    assert 429 in config.retry_on_status
    assert 500 in config.retry_on_status
    assert 502 in config.retry_on_status
    assert 503 in config.retry_on_status
    assert 504 in config.retry_on_status
    assert 401 in config.auth_error_status
    assert 403 in config.auth_error_status


def test_retry_config_custom():
    """Verify RetryConfig accepts custom values."""
    config = RetryConfig(
        max_retries=3,
        backoff_factor=1.5,
        max_backoff=60.0,
        retry_on_status={500, 503},
        auth_error_status={401}
    )

    assert config.max_retries == 3
    assert config.backoff_factor == 1.5
    assert config.max_backoff == 60.0
    assert config.retry_on_status == {500, 503}
    assert config.auth_error_status == {401}
```

### Task 3.6: Update healthsparq Session Tests

**Location**: `healthsparq/tests/test_session.py`

Update existing tests to verify:

1. `HealthSparqSession` no longer has `_request_with_retry()` method
2. `get()` and `post()` delegate to `HttpSession`
3. Auth error callback invalidates session

```python
@pytest.mark.asyncio
async def test_healthsparq_session_delegates_to_http():
    """Verify HealthSparqSession delegates to HttpSession."""
    # Mock HttpSession
    with patch("healthsparq.core.session.HttpSession") as mock_http_cls:
        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=MagicMock(status_code=200))
        mock_http_cls.return_value = mock_http

        session = HealthSparqSession(SessionConfig())
        session._http_session = mock_http
        session._initialized = True

        await session.get("https://example.com/api")

        mock_http.get.assert_called_once()


@pytest.mark.asyncio
async def test_healthsparq_no_request_with_retry():
    """Verify _request_with_retry method no longer exists."""
    session = HealthSparqSession(SessionConfig())

    assert not hasattr(session, "_request_with_retry")
```

## Key Files

| File                                | Purpose               |
| ----------------------------------- | --------------------- |
| `core/tests/test_session.py`        | New retry logic tests |
| `healthsparq/tests/test_session.py` | Updated session tests |

## Test Dependencies

```
pytest>=7.0
pytest-asyncio>=0.21
```

## Running Tests

```bash
# Run core session tests
cd core && pytest tests/test_session.py -v

# Run healthsparq session tests
cd healthsparq && pytest tests/test_session.py -v

# Run all tests
pytest core/tests/ healthsparq/tests/ -v
```

## Acceptance Criteria

- [ ] `test_http_session_retries_on_500` passes
- [ ] `test_http_session_exponential_backoff` passes
- [ ] `test_http_session_auth_error_callback` passes
- [ ] `test_http_session_no_retry_on_success` passes
- [ ] `test_retry_config_defaults` passes
- [ ] `test_healthsparq_session_delegates_to_http` passes
- [ ] All existing tests still pass
- [ ] Test coverage for retry logic ≥80%

## Learnings (To Be Filled by Subagent)

_This section will be updated by the implementing subagent with any discoveries, gotchas, or implementation notes._

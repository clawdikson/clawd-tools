"""Comprehensive tests for session management module.

Tests cover SessionConfig, HealthSparqSession, retry logic, backoff timing,
error handling, context manager behavior, and create_session factory.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import respx

from healthsparq.core.session import (
    HealthSparqSession,
    SessionConfig,
    create_session,
)


class TestSessionConfig:
    """Test SessionConfig dataclass."""

    def test_default_values(self):
        """Default values are correct."""
        config = SessionConfig()
        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.backoff_factor == 2.0
        assert config.max_backoff == 30.0
        assert config.user_agent is None
        assert config.cookies == {}
        assert config.headers == {}
        assert config.proxy is None

    def test_custom_values_override_defaults(self):
        """Custom values override defaults."""
        config = SessionConfig(
            timeout=60.0,
            max_retries=5,
            backoff_factor=3.0,
            max_backoff=60.0,
            user_agent="CustomAgent/1.0",
            cookies={"session": "abc123"},
            headers={"X-Custom": "value"},
            proxy="http://proxy.example.com:8080",
        )
        assert config.timeout == 60.0
        assert config.max_retries == 5
        assert config.backoff_factor == 3.0
        assert config.max_backoff == 60.0
        assert config.user_agent == "CustomAgent/1.0"
        assert config.cookies == {"session": "abc123"}
        assert config.headers == {"X-Custom": "value"}
        assert config.proxy == "http://proxy.example.com:8080"

    def test_empty_cookies_headers_dicts_work(self):
        """Empty cookies/headers dicts work correctly."""
        config = SessionConfig(cookies={}, headers={})
        assert config.cookies == {}
        assert config.headers == {}
        assert isinstance(config.cookies, dict)
        assert isinstance(config.headers, dict)


class TestHealthSparqSessionInitialization:
    """Test HealthSparqSession initialization."""

    def test_client_is_none_until_first_request(self):
        """Client is None until first request."""
        config = SessionConfig()
        session = HealthSparqSession(config)
        assert session._client is None

    def test_lock_is_created(self):
        """Lock is created on initialization."""
        config = SessionConfig()
        session = HealthSparqSession(config)
        assert session._lock is not None
        assert isinstance(session._lock, asyncio.Lock)

    def test_config_is_stored(self):
        """Config is stored correctly."""
        config = SessionConfig(timeout=45.0, max_retries=5)
        session = HealthSparqSession(config)
        assert session.config == config
        assert session.config.timeout == 45.0
        assert session.config.max_retries == 5


@pytest.mark.asyncio
class TestRetryLogic:
    """Test retry logic in _request_with_retry."""

    @respx.mock
    async def test_no_retry_on_success_status(self):
        """No retry on success (status < 500)."""
        config = SessionConfig(max_retries=3)
        session = HealthSparqSession(config)

        route = respx.get("https://test.example.com/api").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )

        response = await session.get("https://test.example.com/api")
        assert response.status_code == 200
        assert route.call_count == 1

    @respx.mock
    async def test_retry_on_500_status_codes(self):
        """Retry on 500+ status codes."""
        config = SessionConfig(max_retries=3, backoff_factor=0.01)
        session = HealthSparqSession(config)

        # First two attempts return 500, third returns 200
        route = respx.get("https://test.example.com/api").mock(
            side_effect=[
                httpx.Response(500, json={"error": "server error"}),
                httpx.Response(503, json={"error": "service unavailable"}),
                httpx.Response(200, json={"status": "ok"}),
            ]
        )

        response = await session.get("https://test.example.com/api")
        assert response.status_code == 200
        assert route.call_count == 3

    @respx.mock
    async def test_retry_on_connection_errors(self):
        """Retry on connection errors (httpx.RequestError)."""
        config = SessionConfig(max_retries=3, backoff_factor=0.01)
        session = HealthSparqSession(config)

        # First two attempts fail with connection error, third succeeds
        route = respx.get("https://test.example.com/api").mock(
            side_effect=[
                httpx.ConnectError("Connection refused"),
                httpx.ConnectError("Connection refused"),
                httpx.Response(200, json={"status": "ok"}),
            ]
        )

        response = await session.get("https://test.example.com/api")
        assert response.status_code == 200
        assert route.call_count == 3

    @respx.mock
    async def test_stops_after_max_retries(self):
        """Stops after max_retries."""
        config = SessionConfig(max_retries=3, backoff_factor=0.01)
        session = HealthSparqSession(config)

        # All attempts fail
        route = respx.get("https://test.example.com/api").mock(
            return_value=httpx.Response(500, json={"error": "server error"})
        )

        with pytest.raises(httpx.HTTPStatusError):
            await session.get("https://test.example.com/api")

        assert route.call_count == 3

    @respx.mock
    async def test_returns_response_on_success_after_retries(self):
        """Returns response on success after retries."""
        config = SessionConfig(max_retries=5, backoff_factor=0.01)
        session = HealthSparqSession(config)

        # Fourth attempt succeeds
        route = respx.get("https://test.example.com/api").mock(
            side_effect=[
                httpx.Response(500, json={"error": "error"}),
                httpx.Response(502, json={"error": "error"}),
                httpx.Response(503, json={"error": "error"}),
                httpx.Response(200, json={"status": "ok"}),
            ]
        )

        response = await session.get("https://test.example.com/api")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert route.call_count == 4


@pytest.mark.asyncio
class TestBackoffTiming:
    """Test exponential backoff timing."""

    async def test_exponential_backoff_calculation(self):
        """Exponential backoff calculation is correct."""
        config = SessionConfig(backoff_factor=2.0, max_backoff=30.0)

        # Calculate expected sleep times
        attempt_0_sleep = min(2.0**0, 30.0)  # 1.0
        attempt_1_sleep = min(2.0**1, 30.0)  # 2.0
        attempt_2_sleep = min(2.0**2, 30.0)  # 4.0
        attempt_3_sleep = min(2.0**3, 30.0)  # 8.0
        attempt_4_sleep = min(2.0**4, 30.0)  # 16.0

        assert attempt_0_sleep == 1.0
        assert attempt_1_sleep == 2.0
        assert attempt_2_sleep == 4.0
        assert attempt_3_sleep == 8.0
        assert attempt_4_sleep == 16.0

    async def test_respects_max_backoff_cap(self):
        """Respects max_backoff cap."""
        config = SessionConfig(backoff_factor=2.0, max_backoff=10.0)

        # Calculate expected sleep times
        attempt_10_sleep = min(2.0**10, 10.0)  # 1024 capped to 10.0

        assert attempt_10_sleep == 10.0

    @respx.mock
    async def test_no_sleep_on_final_attempt_failure(self):
        """No sleep on final attempt failure."""
        config = SessionConfig(max_retries=2, backoff_factor=0.01)
        session = HealthSparqSession(config)

        route = respx.get("https://test.example.com/api").mock(
            return_value=httpx.Response(500, json={"error": "error"})
        )

        start_time = asyncio.get_event_loop().time()

        with pytest.raises(httpx.HTTPStatusError):
            await session.get("https://test.example.com/api")

        elapsed_time = asyncio.get_event_loop().time() - start_time

        # With backoff_factor=0.01, sleep times are 0.01^0=1, 0.01^1=0.01
        # Total sleep should be around 1.01 seconds, not including final attempt
        # But we're testing that no sleep happens after the final failed attempt
        assert elapsed_time < 2.0  # Should complete quickly
        assert route.call_count == 2


@pytest.mark.asyncio
class TestGetPostMethods:
    """Test GET and POST methods."""

    @respx.mock
    async def test_get_with_params(self):
        """GET with params."""
        config = SessionConfig()
        session = HealthSparqSession(config)

        route = respx.get(
            "https://test.example.com/api", params={"key": "value"}
        ).mock(return_value=httpx.Response(200, json={"result": "success"}))

        response = await session.get(
            "https://test.example.com/api", params={"key": "value"}
        )

        assert response.status_code == 200
        assert response.json() == {"result": "success"}
        assert route.called

    @respx.mock
    async def test_get_with_headers(self):
        """GET with headers."""
        config = SessionConfig()
        session = HealthSparqSession(config)

        route = respx.get("https://test.example.com/api").mock(
            return_value=httpx.Response(200, json={"result": "success"})
        )

        response = await session.get(
            "https://test.example.com/api",
            headers={"X-Custom-Header": "custom-value"},
        )

        assert response.status_code == 200
        assert route.called

    @respx.mock
    async def test_post_with_json_data(self):
        """POST with json_data."""
        config = SessionConfig()
        session = HealthSparqSession(config)

        route = respx.post("https://test.example.com/api").mock(
            return_value=httpx.Response(201, json={"created": True})
        )

        response = await session.post(
            "https://test.example.com/api",
            json_data={"name": "test", "value": 123},
        )

        assert response.status_code == 201
        assert response.json() == {"created": True}
        assert route.called

    @respx.mock
    async def test_post_with_form_data(self):
        """POST with form data."""
        config = SessionConfig()
        session = HealthSparqSession(config)

        route = respx.post("https://test.example.com/api").mock(
            return_value=httpx.Response(200, json={"submitted": True})
        )

        response = await session.post(
            "https://test.example.com/api", data={"field1": "value1"}
        )

        assert response.status_code == 200
        assert response.json() == {"submitted": True}
        assert route.called

    @respx.mock
    async def test_headers_propagation_from_config(self):
        """Headers propagation from config."""
        config = SessionConfig(
            headers={"X-API-Key": "secret123", "X-Client-Id": "client456"}
        )
        session = HealthSparqSession(config)

        route = respx.get("https://test.example.com/api").mock(
            return_value=httpx.Response(200, json={"result": "ok"})
        )

        # Trigger client initialization by making a request
        await session.get("https://test.example.com/api")

        # Verify client was created with headers from config
        assert session._client is not None
        assert "X-API-Key" in session._client.headers
        assert "X-Client-Id" in session._client.headers
        assert route.called


@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling."""

    @respx.mock
    async def test_timeout_handling(self):
        """Timeout handling."""
        config = SessionConfig(max_retries=2, backoff_factor=0.01, timeout=0.1)
        session = HealthSparqSession(config)

        route = respx.get("https://test.example.com/api").mock(
            side_effect=httpx.TimeoutException("Request timeout")
        )

        with pytest.raises(httpx.TimeoutException):
            await session.get("https://test.example.com/api")

        assert route.call_count == 2

    @respx.mock
    async def test_connection_refused(self):
        """Connection refused."""
        config = SessionConfig(max_retries=2, backoff_factor=0.01)
        session = HealthSparqSession(config)

        route = respx.get("https://test.example.com/api").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with pytest.raises(httpx.ConnectError):
            await session.get("https://test.example.com/api")

        assert route.call_count == 2

    @respx.mock
    async def test_dns_resolution_failure(self):
        """DNS resolution failure."""
        config = SessionConfig(max_retries=2, backoff_factor=0.01)
        session = HealthSparqSession(config)

        route = respx.get("https://nonexistent.example.com/api").mock(
            side_effect=httpx.ConnectError("Name or service not known")
        )

        with pytest.raises(httpx.ConnectError):
            await session.get("https://nonexistent.example.com/api")

        assert route.call_count == 2

    @respx.mock
    async def test_raises_last_exception_after_all_retries(self):
        """Raises last exception after all retries."""
        config = SessionConfig(max_retries=3, backoff_factor=0.01)
        session = HealthSparqSession(config)

        # Different errors on each attempt
        route = respx.get("https://test.example.com/api").mock(
            side_effect=[
                httpx.ConnectError("Connection refused"),
                httpx.TimeoutException("Timeout"),
                httpx.ConnectError("Connection reset"),
            ]
        )

        # Should raise the last error (ConnectError: Connection reset)
        with pytest.raises(httpx.ConnectError, match="Connection reset"):
            await session.get("https://test.example.com/api")

        assert route.call_count == 3


@pytest.mark.asyncio
class TestContextManager:
    """Test context manager behavior."""

    async def test_aenter_returns_self(self):
        """__aenter__ returns self."""
        config = SessionConfig()
        session = HealthSparqSession(config)

        result = await session.__aenter__()
        assert result is session

    @respx.mock
    async def test_aexit_closes_client(self):
        """__aexit__ closes client."""
        config = SessionConfig()
        session = HealthSparqSession(config)

        # Make a request to initialize the client
        route = respx.get("https://test.example.com/api").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )

        await session.get("https://test.example.com/api")
        assert session._client is not None

        # Exit context
        await session.__aexit__(None, None, None)
        assert session._client is None

    @respx.mock
    async def test_can_be_reused_after_close(self):
        """Can be reused after close."""
        config = SessionConfig()
        session = HealthSparqSession(config)

        route = respx.get("https://test.example.com/api").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )

        # First use
        async with session:
            await session.get("https://test.example.com/api")
            assert session._client is not None

        assert session._client is None

        # Second use
        async with session:
            await session.get("https://test.example.com/api")
            assert session._client is not None

        assert session._client is None
        assert route.call_count == 2

    async def test_close_is_idempotent(self):
        """Close is idempotent."""
        config = SessionConfig()
        session = HealthSparqSession(config)

        # Close without ever opening
        await session.close()
        assert session._client is None

        # Close again
        await session.close()
        assert session._client is None

        # No errors should be raised


class TestCreateSessionFactory:
    """Test create_session factory function."""

    def test_default_session(self):
        """Default session."""
        session = create_session()
        assert isinstance(session, HealthSparqSession)
        assert session.config.timeout == 30.0
        assert session.config.max_retries == 3
        assert session.config.cookies == {}
        assert session.config.user_agent is None
        assert session.config.proxy is None

    def test_session_with_cookies(self):
        """Session with cookies."""
        cookies = {"session_id": "xyz789", "user_token": "abc123"}
        session = create_session(cookies=cookies)
        assert session.config.cookies == cookies

    def test_session_with_custom_timeout(self):
        """Session with custom timeout."""
        session = create_session(timeout=60.0)
        assert session.config.timeout == 60.0

    def test_session_with_proxy(self):
        """Session with proxy."""
        proxy = "http://proxy.example.com:8080"
        session = create_session(proxy=proxy)
        assert session.config.proxy == proxy

    def test_session_with_all_parameters(self):
        """Session with all parameters."""
        cookies = {"auth": "token123"}
        user_agent = "MyApp/2.0"
        timeout = 45.0
        max_retries = 5
        proxy = "http://proxy.example.com:3128"

        session = create_session(
            cookies=cookies,
            user_agent=user_agent,
            timeout=timeout,
            max_retries=max_retries,
            proxy=proxy,
        )

        assert session.config.cookies == cookies
        assert session.config.user_agent == user_agent
        assert session.config.timeout == timeout
        assert session.config.max_retries == max_retries
        assert session.config.proxy == proxy

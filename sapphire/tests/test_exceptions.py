"""Tests for Sapphire exceptions module."""

import pytest

from sapphire.core.exceptions import (
    SapphireError,
    ConfigurationError,
    AuthenticationError,
    APIError,
    SessionError,
    StorageError,
    ValidationError,
)


class TestSapphireError:
    """Tests for base SapphireError exception."""

    def test_basic_error(self):
        """Basic error with message."""
        error = SapphireError("Test error")
        assert str(error) == "Test error"
        # Details defaults to empty dict, not None
        assert error.details == {}

    def test_error_with_details(self):
        """Error with details dict."""
        error = SapphireError("Test error", details={"key": "value"})
        assert "key" in error.details
        assert error.details["key"] == "value"

    def test_error_inheritance(self):
        """SapphireError inherits from Exception."""
        error = SapphireError("Test")
        assert isinstance(error, Exception)


class TestConfigurationError:
    """Tests for ConfigurationError exception."""

    def test_inheritance(self):
        """ConfigurationError inherits from SapphireError."""
        error = ConfigurationError("Bad config")
        assert isinstance(error, SapphireError)

    def test_with_details(self):
        """ConfigurationError with config details."""
        error = ConfigurationError(
            "Invalid config",
            details={"field": "networks", "reason": "empty list"}
        )
        assert error.details["field"] == "networks"


class TestAuthenticationError:
    """Tests for AuthenticationError exception."""

    def test_inheritance(self):
        """AuthenticationError inherits from SapphireError."""
        error = AuthenticationError("Auth failed")
        assert isinstance(error, SapphireError)


class TestAPIError:
    """Tests for APIError exception."""

    def test_basic_api_error(self):
        """Basic API error."""
        error = APIError("Request failed")
        assert str(error) == "Request failed"
        assert error.status_code is None
        assert error.endpoint is None

    def test_api_error_with_status(self):
        """API error with status code."""
        error = APIError("Not found", status_code=404)
        assert error.status_code == 404

    def test_api_error_with_endpoint(self):
        """API error with endpoint."""
        error = APIError(
            "Server error",
            status_code=500,
            endpoint="/api/providers/facets.json"
        )
        assert error.status_code == 500
        assert error.endpoint == "/api/providers/facets.json"

    def test_api_error_with_details(self):
        """API error with full details."""
        error = APIError(
            "Rate limited",
            status_code=429,
            endpoint="/api/test",
            details={"retry_after": 60}
        )
        assert error.status_code == 429
        assert error.details["retry_after"] == 60

    def test_api_error_inheritance(self):
        """APIError inherits from SapphireError."""
        error = APIError("Test")
        assert isinstance(error, SapphireError)


class TestSessionError:
    """Tests for SessionError exception."""

    def test_inheritance(self):
        """SessionError inherits from SapphireError."""
        error = SessionError("Browser crashed")
        assert isinstance(error, SapphireError)

    def test_with_details(self):
        """SessionError with session details."""
        error = SessionError(
            "Queue full",
            details={"queue_size": 1000, "max_size": 1000}
        )
        assert error.details["queue_size"] == 1000


class TestStorageError:
    """Tests for StorageError exception."""

    def test_inheritance(self):
        """StorageError inherits from SapphireError."""
        error = StorageError("Disk full")
        assert isinstance(error, SapphireError)

    def test_with_path_details(self):
        """StorageError with path information."""
        error = StorageError(
            "Cannot write file",
            details={"path": "/tmp/test.json", "error": "Permission denied"}
        )
        assert "path" in error.details


class TestValidationError:
    """Tests for ValidationError exception."""

    def test_inheritance(self):
        """ValidationError inherits from SapphireError."""
        error = ValidationError("Invalid NPI")
        assert isinstance(error, SapphireError)

    def test_with_field_details(self):
        """ValidationError with field validation details."""
        error = ValidationError(
            "Validation failed",
            details={
                "field": "npi",
                "value": "123",
                "reason": "NPI must be 10 digits"
            }
        )
        assert error.details["field"] == "npi"


class TestExceptionChaining:
    """Tests for exception chaining behavior."""

    def test_raise_from(self):
        """Exceptions can be chained with raise from."""
        original = ValueError("Original error")
        try:
            try:
                raise original
            except ValueError as e:
                raise APIError("Wrapped error", status_code=500) from e
        except APIError as e:
            assert e.__cause__ is original

    def test_catch_base_type(self):
        """All custom exceptions can be caught as SapphireError."""
        exceptions = [
            ConfigurationError("config"),
            AuthenticationError("auth"),
            APIError("api"),
            SessionError("session"),
            StorageError("storage"),
            ValidationError("validation"),
        ]

        for exc in exceptions:
            try:
                raise exc
            except SapphireError:
                pass  # Should be caught
            except Exception:
                pytest.fail(f"{type(exc).__name__} not caught as SapphireError")

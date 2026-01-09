"""Exception hierarchy for Sapphire package."""


class SapphireError(Exception):
    """Base exception for all Sapphire errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(SapphireError):
    """Configuration loading or validation failed."""

    pass


class AuthenticationError(SapphireError):
    """Authentication with Sapphire API failed."""

    pass


class APIError(SapphireError):
    """Sapphire API request failed."""

    def __init__(
        self,
        message: str,
        url: str = "",
        status_code: int = 0,
        response_text: str = "",
        details: dict | None = None,
        endpoint: str = "",
    ):
        super().__init__(message, details)
        self.url = url or endpoint
        self.status_code = status_code
        self.response_text = response_text
        self.endpoint = self.url


class SessionError(SapphireError):
    """Browser session management error."""

    pass


class StorageError(SapphireError):
    """Data storage operation failed."""

    pass


class ValidationError(SapphireError):
    """Data validation failed."""

    def __init__(
        self,
        message: str,
        invalid_records: int = 0,
        validation_errors: list[dict] | None = None,
        details: dict | None = None,
    ):
        super().__init__(message, details)
        self.invalid_records = invalid_records
        self.validation_errors = validation_errors or []

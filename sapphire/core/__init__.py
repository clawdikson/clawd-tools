"""Core utilities for Sapphire scrapers."""

from sapphire.core.exceptions import (
    SapphireError,
    ConfigurationError,
    AuthenticationError,
    APIError,
    SessionError,
    StorageError,
    ValidationError,
)
from sapphire.core.session import (
    SapphireBrowserQueue,
    SapphireSessionConfig,
)
from sapphire.core.sapphire_api import (
    SapphireAPI,
    SapphireAPIConfig,
    create_sapphire_api,
)

__all__ = [
    # Exceptions
    "SapphireError",
    "ConfigurationError",
    "AuthenticationError",
    "APIError",
    "SessionError",
    "StorageError",
    "ValidationError",
    # Browser Queue Session
    "SapphireBrowserQueue",
    "SapphireSessionConfig",
    # API
    "SapphireAPI",
    "SapphireAPIConfig",
    "create_sapphire_api",
]

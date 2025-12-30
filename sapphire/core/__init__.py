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
    APIRequest,
    create_browser_queue,
)
from sapphire.core.sapphire_api import (
    SapphireAPI,
    SapphireAPIConfig,
    create_sapphire_api,
)
from sapphire.core.sapphire_session import (
    SapphireSession,
    SessionConfig,
    create_session,
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
    "APIRequest",
    "create_browser_queue",
    # HTTP Session (HealthSparq-aligned pattern)
    "SapphireSession",
    "SessionConfig",
    "create_session",
    # API
    "SapphireAPI",
    "SapphireAPIConfig",
    "create_sapphire_api",
]

# Implementation Plan: core/integrations/ Module

**Generated:** 2026-01-24
**Author:** plan-agent
**Status:** Ready for Implementation

---

## Goal

Extract reusable cloud service clients from `tools/` into `core/integrations/`, creating a unified integration layer that:

1. Consolidates duplicated OAuth, retry, and lazy-loading patterns
2. Follows existing `core/` conventions (Pydantic Settings, SecretStr, feature flags)
3. Maintains backward compatibility via thin wrappers in `tools/`
4. Enables clean integration from `core/qa/` and platform libraries

---

## Research Summary

### Existing Codebase Patterns (VERIFIED)

| Pattern | Location | Description |
|---------|----------|-------------|
| **Pydantic Settings** | `core/config/base.py:42-57` | `SCRAPER_*` env prefix, `SettingsConfigDict` |
| **SecretStr credentials** | `core/config/proxy.py:21-38` | All credentials wrapped in `SecretStr` |
| **Optional imports** | `core/__init__.py:41-63` | Try/except with `_*_AVAILABLE` flags |
| **QAResult[T] pattern** | `core/qa/base.py:61-98` | Generic result with outcome + metrics |
| **Lazy loading** | `tools/drive_uploader.py:64-96` | Global vars + `_load_*_libs()` functions |
| **Retry with backoff** | `core/session/resilient_session.py:271-324` | Max retries, exponential backoff, jitter |

### Code Duplication Analysis

| Duplicated Code | Files | Lines | Root Cause |
|-----------------|-------|-------|------------|
| OAuth 2.0 flow | `drive_uploader.py:182-215`, `xlsx_to_clickup.py:502-543` | ~70 | No shared auth module |
| Lazy import pattern | 3 files | ~60 | Each file reinvents lazy loading |
| Logger fallback | 4 files | ~20 | Copy-paste pattern |
| Retry logic | `drive_uploader.py:349-400`, `xlsx_to_clickup.py:342-384` | ~80 | No shared retry decorator |
| sys.path hacks | 3 files | ~15 | tools/ not properly packaged |

---

## Target Architecture

```
core/integrations/
|-- __init__.py             # Public API exports + feature flags
|-- base.py                 # IntegrationError, IntegrationResult[T], retry decorator
|-- config.py               # IntegrationSettings (Pydantic + SecretStr)
|-- oauth.py                # Unified Google OAuth flow
|-- google_drive.py         # DriveUploader class
|-- s3.py                   # S3Uploader class
|-- gmail.py                # GmailClient class
|-- clickup.py              # ClickUpClient class
+-- CLAUDE.md               # Module documentation

core/reports/
|-- __init__.py
+-- screenshots.py          # generate_xlsx_screenshot()
```

---

## Public API Design

### core/integrations/__init__.py

```python
"""Cloud integration layer with optional dependencies.

Usage:
    from core.integrations import DriveUploader, upload_archive
    from core.integrations import S3Uploader, S3Config
    from core.integrations import GmailClient, ClickUpClient

Feature Detection:
    from core.integrations import DRIVE_AVAILABLE, S3_AVAILABLE, GMAIL_AVAILABLE
"""

# Feature flags (set during import based on optional deps)
DRIVE_AVAILABLE: bool  # google-api-python-client installed
S3_AVAILABLE: bool      # boto3 installed
GMAIL_AVAILABLE: bool   # google-api-python-client + google-auth-oauthlib

# Base types (always available)
from .base import (
    IntegrationError,
    IntegrationResult,
    retry_with_backoff,
)
from .config import IntegrationSettings

# Conditional exports
if DRIVE_AVAILABLE:
    from .google_drive import DriveUploader, upload_archive
if S3_AVAILABLE:
    from .s3 import S3Uploader, S3Config
if GMAIL_AVAILABLE:
    from .gmail import GmailClient, send_email
    from .clickup import ClickUpClient
```

### core/integrations/base.py

```python
"""Base types for integrations module."""

from __future__ import annotations
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from typing import TypeVar, Generic, Callable, Any
import asyncio
import random
import time

T = TypeVar("T")

class IntegrationError(Exception):
    """Base exception for integration failures."""
    def __init__(
        self,
        message: str,
        service: str,
        context: dict[str, Any] | None = None,
        recoverable: bool = False,
    ):
        super().__init__(message)
        self.service = service
        self.context = context or {}
        self.recoverable = recoverable

class AuthenticationError(IntegrationError):
    """Authentication failed."""
    pass

class RateLimitError(IntegrationError):
    """Rate limited by service."""
    def __init__(self, message: str, service: str, retry_after: int | None = None):
        super().__init__(message, service, recoverable=True)
        self.retry_after = retry_after

class UploadError(IntegrationError):
    """File upload failed."""
    pass

@dataclass
class IntegrationResult(Generic[T]):
    """Result wrapper for integration operations."""
    success: bool
    data: T | None = None
    error: IntegrationError | None = None
    elapsed_seconds: float = 0.0
    warnings: list[str] = field(default_factory=list)

    @property
    def is_success(self) -> bool:
        return self.success and self.error is None

def retry_with_backoff(
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 64.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (RateLimitError,),
    retryable_status_codes: tuple = (429, 500, 502, 503, 504),
) -> Callable:
    """Decorator for retry with exponential backoff and jitter.

    Follows existing pattern from core/session/resilient_session.py.

    Args:
        max_retries: Maximum retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap
        jitter: Add random jitter to delay
        retryable_exceptions: Exceptions to retry on
        retryable_status_codes: HTTP status codes to retry on

    Example:
        @retry_with_backoff(max_retries=3)
        def upload_file(path):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_error = e
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    if jitter:
                        delay += random.random()
                    if isinstance(e, RateLimitError) and e.retry_after:
                        delay = max(delay, e.retry_after)
                    if attempt < max_retries - 1:
                        time.sleep(delay)
            raise last_error

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_error = e
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    if jitter:
                        delay += random.random()
                    if isinstance(e, RateLimitError) and e.retry_after:
                        delay = max(delay, e.retry_after)
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)
            raise last_error

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator
```

### core/integrations/config.py

```python
"""Integration settings with SecretStr credentials."""

from __future__ import annotations
from pathlib import Path
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class IntegrationSettings(BaseSettings):
    """Configuration for cloud integrations.

    Follows core/config/proxy.py pattern for SecretStr handling.
    """
    model_config = SettingsConfigDict(
        env_prefix="",  # No prefix for backward compat with existing env vars
        extra="ignore",
    )

    # Google (Drive/Gmail)
    google_service_account_file: Path | None = Field(
        default=None,
        description="Path to service account JSON"
    )
    google_oauth_credentials: Path | None = Field(
        default=None,
        description="Path to OAuth client credentials JSON"
    )
    google_oauth_token_dir: Path = Field(
        default=Path.home() / ".cache" / "ideon" / "oauth",
        description="Directory to store OAuth tokens"
    )

    # AWS S3
    aws_access_key_id: SecretStr = SecretStr("")
    aws_secret_access_key: SecretStr = SecretStr("")
    aws_default_region: str = "us-east-1"
    s3_bucket_name: str = ""
    s3_presigned_expiry: int = 604800  # 7 days

    # ClickUp
    clickup_api_token: SecretStr = SecretStr("")

    # Drive folder mapping
    drive_folder_mapping_path: Path | None = Field(
        default=None,
        description="Path to drive_folder_mapping.json"
    )

    def get_aws_credentials(self) -> tuple[str, str]:
        """Get AWS credentials as plain strings."""
        return (
            self.aws_access_key_id.get_secret_value(),
            self.aws_secret_access_key.get_secret_value(),
        )

    def get_clickup_token(self) -> str:
        """Get ClickUp API token as plain string."""
        return self.clickup_api_token.get_secret_value()

    def __repr__(self) -> str:
        return "IntegrationSettings(credentials=hidden)"
```

### core/integrations/oauth.py

```python
"""Unified Google OAuth 2.0 flow.

Consolidates duplicated OAuth logic from:
- tools/drive_uploader.py:182-215
- tools/xlsx_to_clickup.py:502-543
"""

from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from google.oauth2.credentials import Credentials

# Lazy imports
_oauth_libs_loaded = False
_Credentials = None
_InstalledAppFlow = None
_Request = None

def _load_oauth_libs():
    """Lazy-load Google OAuth libraries."""
    global _oauth_libs_loaded, _Credentials, _InstalledAppFlow, _Request
    if _oauth_libs_loaded:
        return
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        _Credentials = Credentials
        _InstalledAppFlow = InstalledAppFlow
        _Request = Request
        _oauth_libs_loaded = True
    except ImportError as e:
        raise ImportError(
            "Google OAuth dependencies not installed. Run:\n"
            "  pip install google-auth google-auth-oauthlib"
        ) from e

class GoogleOAuth:
    """Unified OAuth 2.0 handler for Google services (Drive, Gmail).

    Example:
        oauth = GoogleOAuth(
            credentials_path=Path("oauth_credentials.json"),
            token_path=Path(".cache/drive_token.json"),
            scopes=["https://www.googleapis.com/auth/drive"],
        )
        credentials = oauth.get_credentials()
    """

    def __init__(
        self,
        credentials_path: Path,
        token_path: Path,
        scopes: list[str],
    ):
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self.scopes = scopes
        self._credentials: Credentials | None = None

    def get_credentials(self) -> "Credentials":
        """Get valid OAuth credentials.

        Loads from token file if available, refreshes if expired,
        or runs browser flow if no valid token exists.
        """
        _load_oauth_libs()

        # Return cached if still valid
        if self._credentials and self._credentials.valid:
            return self._credentials

        # Try loading from token file
        if self.token_path.exists():
            self._credentials = _Credentials.from_authorized_user_file(
                str(self.token_path), self.scopes
            )

        # Refresh or re-authenticate
        if not self._credentials or not self._credentials.valid:
            if (
                self._credentials
                and self._credentials.expired
                and self._credentials.refresh_token
            ):
                self._credentials.refresh(_Request())
            else:
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f"OAuth credentials not found: {self.credentials_path}"
                    )
                flow = _InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), self.scopes
                )
                self._credentials = flow.run_local_server(port=0)

            # Save token for future use
            self._save_token()

        return self._credentials

    def _save_token(self) -> None:
        """Save credentials to token file."""
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_path, "w") as f:
            f.write(self._credentials.to_json())

    def invalidate(self) -> None:
        """Clear cached credentials and token file."""
        self._credentials = None
        if self.token_path.exists():
            self.token_path.unlink()
```

### core/integrations/google_drive.py

```python
"""Google Drive uploader with resumable upload support."""

from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Callable, Any

from .base import (
    IntegrationError,
    IntegrationResult,
    UploadError,
    RateLimitError,
    retry_with_backoff,
)
from .oauth import GoogleOAuth

try:
    from core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# Constants
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]
CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_RETRIES = 5
RETRYABLE_STATUS_CODES = (429, 500, 502, 503, 504)

# Lazy imports
_drive_libs_loaded = False
_service_account = None
_build = None
_MediaFileUpload = None
_HttpError = None

def _load_drive_libs():
    """Lazy-load Google Drive libraries."""
    global _drive_libs_loaded, _service_account, _build, _MediaFileUpload, _HttpError
    if _drive_libs_loaded:
        return
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from googleapiclient.errors import HttpError
        _service_account = service_account
        _build = build
        _MediaFileUpload = MediaFileUpload
        _HttpError = HttpError
        _drive_libs_loaded = True
    except ImportError as e:
        raise ImportError(
            "Google Drive dependencies not installed. Run:\n"
            "  pip install google-api-python-client google-auth"
        ) from e

class DriveUploader:
    """Upload files to Google Drive with resumable upload support.

    Supports two authentication methods:
    1. Service Account (default) - for Shared Drives
    2. OAuth 2.0 (use_oauth=True) - for personal Drive folders

    Example:
        uploader = DriveUploader()
        result = uploader.upload_file(
            file_path=Path("archive.7z"),
            folder_id="1abc...",
        )
        print(result.data["webViewLink"])
    """

    def __init__(
        self,
        credentials_path: Path | None = None,
        mapping_path: Path | None = None,
        use_oauth: bool = False,
        token_dir: Path | None = None,
    ):
        _load_drive_libs()

        # Resolve paths with sensible defaults
        self.use_oauth = use_oauth
        self.credentials_path = self._resolve_credentials_path(credentials_path)
        self.mapping_path = mapping_path or self._default_mapping_path()
        self.token_dir = token_dir or Path.home() / ".cache" / "ideon" / "oauth"

        self._service = None
        self._oauth: GoogleOAuth | None = None
        self._folder_mapping: dict[str, str] = {}

    def _resolve_credentials_path(self, path: Path | None) -> Path:
        """Resolve credentials path with fallback to env vars."""
        import os
        if path:
            return Path(path)
        if self.use_oauth:
            env_path = os.environ.get("GOOGLE_OAUTH_CREDENTIALS")
        else:
            env_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
        if env_path:
            return Path(env_path)
        # Default location
        secrets_dir = Path(__file__).parent.parent.parent / "tools" / "secrets"
        if self.use_oauth:
            return secrets_dir / "oauth_credentials.json"
        return secrets_dir / "google_drive_credentials.json"

    def _default_mapping_path(self) -> Path:
        """Get default folder mapping path."""
        return Path(__file__).parent.parent.parent / "tools" / "drive_folder_mapping.json"

    @property
    def service(self):
        """Lazy-load authenticated Drive API service."""
        if self._service is None:
            if self.use_oauth:
                self._oauth = GoogleOAuth(
                    credentials_path=self.credentials_path,
                    token_path=self.token_dir / "drive_token.json",
                    scopes=DRIVE_SCOPES,
                )
                credentials = self._oauth.get_credentials()
            else:
                credentials = _service_account.Credentials.from_service_account_file(
                    str(self.credentials_path),
                    scopes=DRIVE_SCOPES,
                )
            self._service = _build("drive", "v3", credentials=credentials)
            auth_type = "OAuth 2.0" if self.use_oauth else "Service Account"
            logger.info(f"Authenticated with Google Drive ({auth_type})")
        return self._service

    def load_folder_mapping(self) -> dict[str, str]:
        """Load project -> folder ID mapping."""
        if not self._folder_mapping:
            if not self.mapping_path.exists():
                raise FileNotFoundError(
                    f"Folder mapping not found: {self.mapping_path}"
                )
            with open(self.mapping_path) as f:
                data = json.load(f)
                self._folder_mapping = data.get("projects", data)
        return self._folder_mapping

    def get_folder_id(self, project_name: str) -> str:
        """Get Drive folder ID for a project."""
        mapping = self.load_folder_mapping()
        if project_name not in mapping:
            raise KeyError(f"No folder mapping for project: {project_name}")
        return mapping[project_name]

    def validate_folder_access(self, folder_id: str) -> dict:
        """Validate access to folder before upload."""
        try:
            return self.service.files().get(
                fileId=folder_id,
                fields="id, name, mimeType",
                supportsAllDrives=True,
            ).execute()
        except _HttpError as e:
            status = e.resp.status
            if status == 404:
                raise IntegrationError(
                    f"Folder not found: {folder_id}",
                    service="google_drive",
                    context={"folder_id": folder_id},
                )
            elif status == 403:
                raise IntegrationError(
                    f"Permission denied for folder: {folder_id}",
                    service="google_drive",
                    context={"folder_id": folder_id},
                )
            raise

    @retry_with_backoff(max_retries=MAX_RETRIES)
    def upload_file(
        self,
        file_path: Path,
        folder_id: str,
        custom_name: str | None = None,
        progress_callback: Callable[[float], None] | None = None,
    ) -> IntegrationResult[dict]:
        """Upload a file to Google Drive.

        Args:
            file_path: Local path to file
            folder_id: Target folder ID
            custom_name: Optional custom filename
            progress_callback: Called with progress (0.0-1.0)

        Returns:
            IntegrationResult with upload metadata
        """
        start_time = time.monotonic()
        file_path = Path(file_path)

        if not file_path.exists():
            return IntegrationResult(
                success=False,
                error=IntegrationError(
                    f"File not found: {file_path}",
                    service="google_drive",
                ),
            )

        file_name = custom_name or file_path.name
        file_size = file_path.stat().st_size
        logger.info(f"Uploading {file_name} ({file_size / 1024 / 1024:.1f} MB)")

        file_metadata = {
            "name": file_name,
            "parents": [folder_id],
        }

        media = _MediaFileUpload(
            str(file_path),
            mimetype="application/x-7z-compressed",
            chunksize=CHUNK_SIZE,
            resumable=True,
        )

        request = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, name, webViewLink",
            supportsAllDrives=True,
        )

        try:
            response = self._execute_resumable_upload(request, progress_callback)
            elapsed = time.monotonic() - start_time
            return IntegrationResult(
                success=True,
                data=response,
                elapsed_seconds=elapsed,
            )
        except _HttpError as e:
            elapsed = time.monotonic() - start_time
            return IntegrationResult(
                success=False,
                error=UploadError(
                    f"Upload failed: {e}",
                    service="google_drive",
                    context={"status": e.resp.status},
                ),
                elapsed_seconds=elapsed,
            )

    def _execute_resumable_upload(
        self,
        request,
        progress_callback: Callable[[float], None] | None,
    ) -> dict:
        """Execute resumable upload with retry logic."""
        response = None
        retries = 0

        while response is None:
            try:
                status, response = request.next_chunk()
                if status and progress_callback:
                    progress_callback(status.progress())
                retries = 0
            except _HttpError as e:
                if e.resp.status in RETRYABLE_STATUS_CODES:
                    retries += 1
                    if retries > MAX_RETRIES:
                        raise
                    wait = min(2 ** retries + random.random(), 64)
                    if e.resp.status == 429:
                        raise RateLimitError(
                            "Rate limited by Google Drive",
                            service="google_drive",
                            retry_after=int(wait),
                        )
                    time.sleep(wait)
                else:
                    raise

        logger.info(f"Upload complete! File ID: {response.get('id')}")
        return response


def upload_archive(
    project_name: str,
    curr_date: str,
    base_path: Path | None = None,
    use_oauth: bool = False,
    dry_run: bool = False,
    progress_callback: Callable[[float], None] | None = None,
) -> IntegrationResult[dict]:
    """High-level API for uploading project archives.

    This is the main entry point for integration with run_all.py.

    Args:
        project_name: Project name (e.g., "audiobee_bcbs_il")
        curr_date: Date in YYYYMMDD format
        base_path: Base directory (defaults to project_name/)
        use_oauth: Use OAuth instead of service account
        dry_run: Validate without uploading
        progress_callback: Progress callback

    Returns:
        IntegrationResult with upload metadata

    Example:
        result = upload_archive("audiobee_bcbs_il", "20260120")
        if result.is_success:
            print(f"Uploaded: {result.data['webViewLink']}")
    """
    base_path = Path(project_name) if base_path is None else Path(base_path)
    archive_path = base_path / curr_date / f"{curr_date}.7z"

    if not archive_path.exists():
        return IntegrationResult(
            success=False,
            error=IntegrationError(
                f"Archive not found: {archive_path}",
                service="google_drive",
            ),
        )

    uploader = DriveUploader(use_oauth=use_oauth)
    folder_id = uploader.get_folder_id(project_name)
    uploader.validate_folder_access(folder_id)

    if dry_run:
        return IntegrationResult(
            success=True,
            data={"id": "dry-run", "name": archive_path.name},
            warnings=["Dry run - no upload performed"],
        )

    return uploader.upload_file(
        file_path=archive_path,
        folder_id=folder_id,
        progress_callback=progress_callback,
    )
```

### core/integrations/s3.py

```python
"""AWS S3 uploader with presigned URL generation."""

from __future__ import annotations
import json
import time
from dataclasses import dataclass
from pathlib import Path

from pydantic import SecretStr
from .base import IntegrationError, IntegrationResult, UploadError

try:
    from core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# Lazy imports
_boto3_loaded = False
_boto3 = None
_Config = None

def _load_boto3():
    """Lazy-load boto3."""
    global _boto3_loaded, _boto3, _Config
    if _boto3_loaded:
        return
    try:
        import boto3
        from botocore.config import Config
        _boto3 = boto3
        _Config = Config
        _boto3_loaded = True
    except ImportError as e:
        raise ImportError(
            "boto3 not installed. Run:\n  pip install boto3"
        ) from e

@dataclass
class S3Config:
    """S3 configuration."""
    bucket_name: str
    region: str = "us-east-1"
    presigned_expiry: int = 604800  # 7 days
    access_key_id: str | None = None
    secret_access_key: str | None = None

    @classmethod
    def from_env(cls) -> "S3Config":
        """Load from environment or credentials file."""
        import os

        # Try credentials file first
        creds_path = Path(__file__).parent.parent.parent / "tools" / "secrets" / "aws_credentials.json"
        if creds_path.exists():
            with open(creds_path) as f:
                creds = json.load(f)
            return cls(
                bucket_name=creds.get("bucket_name", ""),
                region=creds.get("region", "us-east-1"),
                access_key_id=creds.get("aws_access_key_id"),
                secret_access_key=creds.get("aws_secret_access_key"),
            )

        # Fall back to env vars
        bucket = os.environ.get("S3_BUCKET_NAME")
        if not bucket:
            raise ValueError(
                "S3 not configured. Set S3_BUCKET_NAME or create aws_credentials.json"
            )
        return cls(
            bucket_name=bucket,
            region=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
        )

class S3Uploader:
    """S3 client for file uploads with presigned URL generation."""

    def __init__(self, config: S3Config):
        self.config = config
        self._client = None

    @property
    def client(self):
        """Lazy-load S3 client."""
        if self._client is None:
            _load_boto3()
            boto_config = _Config(
                signature_version='s3v4',
                retries={'max_attempts': 5, 'mode': 'standard'},
            )
            self._client = _boto3.client(
                's3',
                region_name=self.config.region,
                config=boto_config,
                aws_access_key_id=self.config.access_key_id,
                aws_secret_access_key=self.config.secret_access_key,
            )
        return self._client

    def upload_file(
        self,
        local_path: Path,
        object_key: str,
        content_type: str = "application/octet-stream",
    ) -> IntegrationResult[str]:
        """Upload file to S3.

        Returns:
            IntegrationResult with object key
        """
        start_time = time.monotonic()
        local_path = Path(local_path)

        if not local_path.exists():
            return IntegrationResult(
                success=False,
                error=IntegrationError(
                    f"File not found: {local_path}",
                    service="s3",
                ),
            )

        try:
            self.client.upload_file(
                str(local_path),
                self.config.bucket_name,
                object_key,
                ExtraArgs={"ContentType": content_type},
            )
            elapsed = time.monotonic() - start_time
            logger.info(f"Uploaded to s3://{self.config.bucket_name}/{object_key}")
            return IntegrationResult(
                success=True,
                data=object_key,
                elapsed_seconds=elapsed,
            )
        except Exception as e:
            elapsed = time.monotonic() - start_time
            return IntegrationResult(
                success=False,
                error=UploadError(str(e), service="s3"),
                elapsed_seconds=elapsed,
            )

    def generate_presigned_url(
        self,
        object_key: str,
        expiration: int | None = None,
    ) -> str:
        """Generate presigned URL for S3 object."""
        expiry = expiration or self.config.presigned_expiry
        return self.client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': self.config.bucket_name,
                'Key': object_key,
            },
            ExpiresIn=expiry,
        )

    def upload_and_get_url(
        self,
        local_path: Path,
        project_name: str,
        curr_date: str,
    ) -> tuple[str, str]:
        """Upload and return (object_key, presigned_url)."""
        object_key = f"{project_name}-{curr_date}.jsonl"
        result = self.upload_file(
            local_path,
            object_key,
            content_type="application/x-ndjson",
        )
        if not result.is_success:
            raise result.error
        presigned_url = self.generate_presigned_url(object_key)
        return object_key, presigned_url
```

### core/integrations/gmail.py

```python
"""Gmail client with OAuth authentication."""

from __future__ import annotations
import base64
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path
from typing import Any

from .base import IntegrationError, IntegrationResult
from .oauth import GoogleOAuth

try:
    from core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# Lazy imports
_gmail_libs_loaded = False
_build = None

def _load_gmail_libs():
    global _gmail_libs_loaded, _build
    if _gmail_libs_loaded:
        return
    try:
        from googleapiclient.discovery import build
        _build = build
        _gmail_libs_loaded = True
    except ImportError as e:
        raise ImportError(
            "Gmail dependencies not installed. Run:\n"
            "  pip install google-api-python-client google-auth-oauthlib"
        ) from e

class GmailClient:
    """Gmail API client for sending emails."""

    def __init__(
        self,
        credentials_path: Path | None = None,
        token_path: Path | None = None,
    ):
        _load_gmail_libs()

        # Resolve paths
        secrets_dir = Path(__file__).parent.parent.parent / "tools" / "secrets"
        self.credentials_path = credentials_path or secrets_dir / "oauth_credentials.json"
        token_dir = Path.home() / ".cache" / "ideon" / "oauth"
        self.token_path = token_path or token_dir / "gmail_token.json"

        self._service = None
        self._oauth: GoogleOAuth | None = None

    @property
    def service(self):
        """Lazy-load Gmail service."""
        if self._service is None:
            self._oauth = GoogleOAuth(
                credentials_path=self.credentials_path,
                token_path=self.token_path,
                scopes=GMAIL_SCOPES,
            )
            credentials = self._oauth.get_credentials()
            self._service = _build("gmail", "v1", credentials=credentials)
            logger.info("Authenticated with Gmail API")
        return self._service

    def send_email(
        self,
        to: list[str],
        subject: str,
        body: str,
        attachment_path: Path | None = None,
        attachment_name: str | None = None,
        cc: list[str] | None = None,
    ) -> IntegrationResult[dict]:
        """Send email with optional attachment.

        Returns:
            IntegrationResult with message_id
        """
        # Build message
        msg = MIMEMultipart()
        msg["To"] = ", ".join(to)
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = ", ".join(cc)

        msg.attach(MIMEText(body, "plain"))

        # Add attachment
        if attachment_path and Path(attachment_path).exists():
            with open(attachment_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                filename = attachment_name or Path(attachment_path).name
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={filename}",
                )
                msg.attach(part)

        # Send
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        try:
            result = self.service.users().messages().send(
                userId="me",
                body={"raw": raw_message},
            ).execute()
            logger.info(f"Email sent! Message ID: {result.get('id')}")
            return IntegrationResult(
                success=True,
                data={"message_id": result.get("id")},
            )
        except Exception as e:
            return IntegrationResult(
                success=False,
                error=IntegrationError(str(e), service="gmail"),
            )
```

### core/integrations/clickup.py

```python
"""ClickUp API client."""

from __future__ import annotations
import time
from pathlib import Path

import requests

from .base import IntegrationError, IntegrationResult, RateLimitError

try:
    from core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

class ClickUpClient:
    """ClickUp API v2 client."""

    BASE_URL = "https://api.clickup.com/api/v2"

    def __init__(self, api_token: str, max_retries: int = 3):
        self.api_token = api_token
        self.max_retries = max_retries

    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> dict:
        """Make API request with retry logic."""
        url = f"{self.BASE_URL}{endpoint}"
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = self.api_token

        for attempt in range(self.max_retries):
            response = requests.request(method, url, headers=headers, **kwargs)
            if response.status_code == 429:
                wait = 2 ** attempt
                logger.warning(f"Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response.json()

        raise RateLimitError(
            f"Max retries exceeded for {endpoint}",
            service="clickup",
        )

    def upload_attachment(
        self,
        task_id: str,
        file_path: Path,
        filename: str | None = None,
    ) -> IntegrationResult[dict]:
        """Upload file as task attachment."""
        endpoint = f"/task/{task_id}/attachment"
        upload_name = filename or Path(file_path).name

        with open(file_path, "rb") as f:
            files = {"attachment": (upload_name, f, "image/png")}
            try:
                result = self._request("POST", endpoint, files=files)
                return IntegrationResult(success=True, data=result)
            except Exception as e:
                return IntegrationResult(
                    success=False,
                    error=IntegrationError(str(e), service="clickup"),
                )

    def add_comment(self, task_id: str, text: str) -> IntegrationResult[dict]:
        """Add comment to task."""
        endpoint = f"/task/{task_id}/comment"
        try:
            result = self._request(
                "POST",
                endpoint,
                json={"comment_text": text},
                headers={"Content-Type": "application/json"},
            )
            return IntegrationResult(success=True, data=result)
        except Exception as e:
            return IntegrationResult(
                success=False,
                error=IntegrationError(str(e), service="clickup"),
            )
```

### core/reports/screenshots.py

```python
"""Generate screenshots from XLSX reports."""

from __future__ import annotations
import tempfile
from pathlib import Path

import pandas as pd

try:
    from core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

def generate_xlsx_screenshot(
    xlsx_path: Path,
    output_path: Path | None = None,
    dpi: int = 150,
) -> Path:
    """Generate PNG screenshot from XLSX state report.

    Creates a compact summary image from the first 5 rows.

    Args:
        xlsx_path: Path to XLSX file
        output_path: Output PNG path (auto-generated if None)
        dpi: Image resolution

    Returns:
        Path to generated PNG
    """
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    df = pd.read_excel(xlsx_path, sheet_name=0, engine="openpyxl")

    if df.empty:
        raise ValueError(f"Empty Excel file: {xlsx_path}")

    # Extract summary rows
    summary_rows = []
    for idx, row in df.iterrows():
        desc = str(row.get("Description", "")).strip()
        data = str(row.get("Data", "")).strip()
        if desc and desc != "nan" and idx < 5:
            summary_rows.append((desc.rstrip(":"), data if data != "nan" else ""))

    if not summary_rows:
        raise ValueError(f"No summary data in: {xlsx_path}")

    # Create figure
    fig, ax = plt.subplots(figsize=(8, 3), facecolor="white")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, len(summary_rows) + 1)
    ax.axis("off")

    # Background box
    bg = FancyBboxPatch(
        (0.1, 0.3), 9.8, len(summary_rows) + 0.4,
        boxstyle="round,pad=0.02,rounding_size=0.1",
        facecolor="#f8f9fa", edgecolor="#dee2e6", linewidth=1,
    )
    ax.add_patch(bg)

    # Render rows
    y = len(summary_rows)
    for label, value in summary_rows:
        ax.text(0.3, y, f"{label}:", fontsize=11, fontweight="bold", color="#333")
        ax.text(5.0, y, value, fontsize=11, color="#1a5276")
        y -= 1

    plt.tight_layout(pad=0.5)

    if output_path is None:
        output_path = Path(tempfile.mktemp(suffix=".png"))

    fig.savefig(str(output_path), dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    return output_path
```

---

## Implementation Phases

### Phase 1: Foundation (Day 1)

**Goal:** Create core infrastructure without breaking existing code.

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `core/integrations/__init__.py` | ~50 | Public API, feature flags |
| `core/integrations/base.py` | ~120 | Errors, Result[T], retry decorator |
| `core/integrations/config.py` | ~60 | IntegrationSettings |
| `core/integrations/oauth.py` | ~100 | Unified OAuth |

**Steps:**

1. Create `core/integrations/` directory
2. Implement `base.py` with IntegrationError, IntegrationResult[T], retry_with_backoff
3. Implement `config.py` with IntegrationSettings (Pydantic + SecretStr)
4. Implement `oauth.py` consolidating OAuth from both files
5. Create `__init__.py` with feature flags for optional deps
6. Add tests in `core/tests/test_integrations/`

**Acceptance Criteria:**

- [ ] `from core.integrations import IntegrationError, IntegrationResult` works
- [ ] `from core.integrations import IntegrationSettings` works
- [ ] Optional import handling works when google-auth not installed
- [ ] `retry_with_backoff` decorator works with sync and async functions

**Commands:**

```bash
# Create module structure
mkdir -p core/integrations
mkdir -p core/tests/test_integrations

# Test imports work
.venv/bin/python -c "from core.integrations import IntegrationError, IntegrationResult"

# Run new tests
.venv/bin/pytest core/tests/test_integrations/ -v
```

### Phase 2: Cloud Providers (Day 2)

**Goal:** Migrate DriveUploader and S3Uploader to core.

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `core/integrations/google_drive.py` | ~250 | DriveUploader, upload_archive() |
| `core/integrations/s3.py` | ~150 | S3Uploader, S3Config |

**Steps:**

1. Implement `google_drive.py` using oauth.py and retry decorator
2. Implement `s3.py` with lazy boto3 loading
3. Update `__init__.py` with conditional exports
4. Create backward-compat shim in `tools/drive_uploader.py`
5. Create backward-compat shim in `tools/s3_uploader.py`

**Backward Compatibility Shim (tools/drive_uploader.py):**

```python
"""Backward compatibility shim.

DEPRECATED: Use core.integrations instead:
    from core.integrations import DriveUploader, upload_archive
"""
import warnings

def _warn():
    warnings.warn(
        "tools.drive_uploader is deprecated. "
        "Use 'from core.integrations import DriveUploader' instead.",
        DeprecationWarning,
        stacklevel=3,
    )

# Re-export from new location
from core.integrations.google_drive import DriveUploader as _DriveUploader
from core.integrations.google_drive import upload_archive as _upload_archive

class DriveUploader(_DriveUploader):
    def __init__(self, *args, **kwargs):
        _warn()
        super().__init__(*args, **kwargs)

def upload_archive(*args, **kwargs):
    _warn()
    return _upload_archive(*args, **kwargs)

# Keep CLI working
if __name__ == "__main__":
    from core.integrations.google_drive import app
    app()
```

**Acceptance Criteria:**

- [ ] `from core.integrations import DriveUploader, upload_archive` works
- [ ] `from core.integrations import S3Uploader, S3Config` works
- [ ] `from tools.drive_uploader import upload_archive` still works (with warning)
- [ ] All existing tools/tests/ pass

### Phase 3: Email/ClickUp Clients (Day 3)

**Goal:** Migrate EmailClient and ClickUpClient.

**Files to create:**

| File | Lines | Purpose |
|------|-------|---------|
| `core/integrations/gmail.py` | ~120 | GmailClient |
| `core/integrations/clickup.py` | ~100 | ClickUpClient |
| `core/reports/__init__.py` | ~10 | Reports module |
| `core/reports/screenshots.py` | ~80 | generate_xlsx_screenshot() |

**Steps:**

1. Implement `gmail.py` using oauth.py
2. Implement `clickup.py` with retry logic
3. Create `core/reports/screenshots.py` from xlsx_to_clickup
4. Update `__init__.py` exports
5. Create backward-compat shim in `tools/xlsx_to_clickup.py`

**Acceptance Criteria:**

- [ ] `from core.integrations import GmailClient, ClickUpClient` works
- [ ] `from core.reports import generate_xlsx_screenshot` works
- [ ] `from tools.xlsx_to_clickup import send_report_email` still works

### Phase 4: Refactor core/qa Integration (Day 4 AM)

**Goal:** Remove sys.path hacks from core/qa/upload_and_submit_message.py.

**Files to modify:**

| File | Changes |
|------|---------|
| `core/qa/upload_and_submit_message.py` | Use core.integrations directly |

**Before:**

```python
def _ensure_tools_importable() -> None:
    tools_path = _get_tools_path()
    tools_parent = str(tools_path.parent)
    if tools_parent not in sys.path:
        sys.path.insert(0, tools_parent)

# ...
_ensure_tools_importable()
from tools.drive_uploader import upload_archive
```

**After:**

```python
from core.integrations import upload_archive, DriveUploader
from core.integrations import GmailClient
from core.reports import generate_xlsx_screenshot
```

**Acceptance Criteria:**

- [ ] No sys.path manipulation in core/qa/
- [ ] `from core.qa import upload_to_drive, send_email_report` works
- [ ] Existing callers unaffected

### Phase 5: Documentation & Cleanup (Day 4 PM)

**Goal:** Document module, move tests, update CLAUDE.md files.

**Files to create/update:**

| File | Purpose |
|------|---------|
| `core/integrations/CLAUDE.md` | Module documentation |
| `core/CLAUDE.md` | Add integrations section |
| `tools/README.md` | Add deprecation notice |

**Steps:**

1. Create `core/integrations/CLAUDE.md` with API docs
2. Update `core/CLAUDE.md` to include integrations module
3. Move relevant tests from `tools/tests/` to `core/tests/test_integrations/`
4. Update `tools/README.md` with deprecation notices
5. Delete `tools/project_config.py` (duplicates core/config/)

**Acceptance Criteria:**

- [ ] All tests pass from new locations
- [ ] Documentation complete
- [ ] Deprecation warnings in tools/ shims

---

## Testing Strategy

### Unit Tests (core/tests/test_integrations/)

```python
# test_base.py
def test_integration_result_success():
    result = IntegrationResult(success=True, data={"id": "123"})
    assert result.is_success
    assert result.data["id"] == "123"

def test_integration_result_failure():
    result = IntegrationResult(
        success=False,
        error=IntegrationError("Failed", service="test"),
    )
    assert not result.is_success
    assert result.error.service == "test"

def test_retry_decorator_retries_on_rate_limit():
    call_count = 0

    @retry_with_backoff(max_retries=3, base_delay=0.01)
    def flaky():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RateLimitError("Slow down", service="test")
        return "success"

    result = flaky()
    assert result == "success"
    assert call_count == 3

# test_config.py
def test_integration_settings_secrets():
    """Ensure credentials don't leak in repr/str."""
    settings = IntegrationSettings(
        aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
        aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    )
    assert "AKIAIOSFODNN7EXAMPLE" not in repr(settings)
    assert "wJalrXUtnFEMI" not in str(settings)
```

### Integration Tests

```python
# test_drive_integration.py
@pytest.mark.integration
def test_drive_upload_dry_run(tmp_path):
    """Test Drive upload in dry-run mode."""
    archive = tmp_path / "20260120" / "20260120.7z"
    archive.parent.mkdir(parents=True)
    archive.write_bytes(b"test")

    result = upload_archive(
        project_name="test_project",
        curr_date="20260120",
        base_path=tmp_path,
        dry_run=True,
    )
    assert result.is_success
    assert "Dry run" in result.warnings[0]
```

### Backward Compatibility Tests

```python
# test_backward_compat.py
import warnings

def test_tools_import_warns():
    """Importing from tools/ emits deprecation warning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        from tools.drive_uploader import DriveUploader
        assert len(w) == 1
        assert "deprecated" in str(w[0].message).lower()
```

---

## Migration Steps for Existing Code

### healthsparq/ Integration

Currently: Calls tools/ indirectly via core/qa/upload_and_submit_message.py

```python
# healthsparq/phases/report.py (no changes needed)
from core.qa import upload_to_drive, send_email_report

# These functions are updated internally to use core.integrations
result = upload_to_drive(project_name, curr_date)
```

### sapphire/ Integration (Future)

When adding Phase 6 (Upload) to sapphire:

```python
# sapphire/phases/upload.py (new file)
from core.integrations import upload_archive, DriveUploader
from core.integrations import GmailClient
from core.reports import generate_xlsx_screenshot

async def run_upload_phase(config: SapphireConfig) -> PhaseResult:
    # Direct usage of core.integrations
    result = upload_archive(
        project_name=config.project_name,
        curr_date=config.curr_date,
        base_path=config.output_dir,
    )
    if not result.is_success:
        return PhaseResult(success=False, error=str(result.error))

    return PhaseResult(
        success=True,
        metadata={"drive_link": result.data["webViewLink"]},
    )
```

---

## Configuration Schema

### Environment Variables

```bash
# Google (Drive/Gmail)
GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/service_account.json
GOOGLE_OAUTH_CREDENTIALS=/path/to/oauth_credentials.json

# AWS S3
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=my-bucket

# ClickUp
CLICKUP_API_TOKEN=pk_12345...
```

### Credentials File Locations

| Service | Default Path | Env Override |
|---------|--------------|--------------|
| Drive (Service Account) | `tools/secrets/google_drive_credentials.json` | `GOOGLE_SERVICE_ACCOUNT_FILE` |
| Drive/Gmail (OAuth) | `tools/secrets/oauth_credentials.json` | `GOOGLE_OAUTH_CREDENTIALS` |
| OAuth Tokens | `~/.cache/ideon/oauth/` | - |
| AWS | `tools/secrets/aws_credentials.json` | `AWS_*` env vars |
| Folder Mapping | `tools/drive_folder_mapping.json` | - |

---

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Import cycles | Medium | High | Use TYPE_CHECKING, test at each phase |
| Optional deps break core/ | Medium | High | Lazy imports + feature flags everywhere |
| Existing callers break | Low | Medium | Shims with DeprecationWarning |
| Test coverage gaps | Medium | Medium | Require tests pass each phase |
| OAuth token invalidation | Low | Low | Document manual token refresh |

---

## Estimated Complexity

| Phase | Files | Lines | Effort |
|-------|-------|-------|--------|
| Phase 1: Foundation | 4 | ~330 | 1 day |
| Phase 2: Cloud Providers | 4 | ~400 | 1 day |
| Phase 3: Email/ClickUp | 4 | ~310 | 1 day |
| Phase 4: QA Integration | 1 | -150 (removal) | 0.5 day |
| Phase 5: Documentation | 3 | ~200 | 0.5 day |
| **Total** | **16** | **~1,090 new** | **4 days** |

**Code Reduction:** ~400 lines removed from duplication.
**Net Change:** +690 lines (structured, tested, documented).

---

## Success Criteria

1. All existing tools/tests/ pass (backward compat)
2. All new core/tests/test_integrations/ pass
3. `from core.integrations import DriveUploader, S3Uploader, GmailClient` works
4. `from tools.drive_uploader import upload_archive` works with warning
5. No sys.path manipulation in core/
6. Optional deps (google-auth, boto3) don't break core/ imports
7. healthsparq/ and sapphire/ require zero code changes
8. CLAUDE.md documentation complete

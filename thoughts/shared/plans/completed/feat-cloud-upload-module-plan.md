# Feature Plan: Cloud Upload Module for core/

Created: 2026-01-24
Author: architect-agent

## Overview

Move cloud upload and reporting functionality from `tools/` into `core/` package as a new `core/cloud/` module. This consolidates Google Drive upload, S3 upload, Gmail email sending, and ClickUp integration into the shared utilities package with proper optional dependency handling, Pydantic Settings configuration, and integration points for healthsparq/sapphire pipelines.

## Requirements

- [ ] Create new `core/cloud/` module with upload and notification clients
- [ ] Handle external service configs via Pydantic Settings (Drive, S3, Gmail, ClickUp)
- [ ] Make all dependencies optional (google-api, boto3, etc.)
- [ ] Define clean public API surface with factory functions
- [ ] Integrate into healthsparq/sapphire Phase 5 (Report) pipeline
- [ ] Maintain backward compatibility with existing `tools/` usage
- [ ] Return QAResult-style result types for consistency

## Design

### Architecture

```
core/
├── cloud/                          # NEW: Cloud services module
│   ├── __init__.py                 # Public API exports
│   ├── base.py                     # CloudError exception, CloudResult type
│   ├── config.py                   # CloudSettings (Pydantic Settings)
│   ├── drive.py                    # DriveUploader - Google Drive uploads
│   ├── s3.py                       # S3Uploader - AWS S3 uploads
│   ├── gmail.py                    # GmailClient - Email sending
│   ├── clickup.py                  # ClickUpClient - Task attachments
│   └── factory.py                  # create_*() factory functions
│
├── qa/
│   └── upload_and_submit_message.py  # UPDATE: Use core.cloud instead of tools/
│
└── __init__.py                     # UPDATE: Add cloud exports if available
```

### Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `base.py` | CloudError exception, CloudResult[T] generic type, CloudStatus enum |
| `config.py` | CloudSettings with Drive/S3/Gmail/ClickUp credentials |
| `drive.py` | DriveUploader class - resumable uploads, OAuth/ServiceAccount auth |
| `s3.py` | S3Uploader class - presigned URLs, boto3 integration |
| `gmail.py` | GmailClient class - OAuth email sending with attachments |
| `clickup.py` | ClickUpClient class - task attachments, comments |
| `factory.py` | create_drive_uploader(), create_s3_uploader(), etc. |

### Interfaces

```python
# core/cloud/base.py
from dataclasses import dataclass, field
from enum import Enum
from typing import TypeVar, Generic, Any

class CloudStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    DRY_RUN = "dry_run"

@dataclass
class CloudOutcome:
    """Outcome details for cloud operations."""
    status: CloudStatus
    message: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0

T = TypeVar("T")

@dataclass
class CloudResult(Generic[T]):
    """Result wrapper for cloud operations (mirrors QAResult pattern)."""
    outcome: CloudOutcome
    metrics: T
    
    @property
    def is_success(self) -> bool:
        return self.outcome.status == CloudStatus.SUCCESS


class CloudError(Exception):
    """Base exception for cloud operations."""
    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message)
        self.context = context or {}


# core/cloud/config.py
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class CloudSettings(BaseSettings):
    """Cloud service configuration.
    
    Credentials loaded from environment or secrets files.
    No SCRAPER_* prefix - matches existing tools/ behavior.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # Google Drive
    google_service_account_file: Path | None = Field(
        default=None,
        description="Path to service account JSON"
    )
    google_oauth_credentials: Path | None = Field(
        default=None,
        description="Path to OAuth client credentials JSON"
    )
    drive_folder_mapping_file: Path | None = Field(
        default=None,
        description="Path to project->folder ID mapping JSON"
    )
    
    # AWS S3
    s3_bucket_name: str | None = Field(default=None)
    aws_access_key_id: SecretStr | None = Field(default=None)
    aws_secret_access_key: SecretStr | None = Field(default=None)
    aws_default_region: str = Field(default="us-east-1")
    s3_presigned_expiry: int = Field(default=604800, description="7 days")
    
    # Gmail
    gmail_token_path: Path | None = Field(default=None)
    
    # ClickUp
    clickup_api_token: SecretStr | None = Field(default=None)


# core/cloud/drive.py
@dataclass
class DriveUploadMetrics:
    """Metrics for Drive upload operation."""
    file_id: str | None = None
    web_link: str | None = None
    file_size_bytes: int = 0
    archive_path: str | None = None
    folder_name: str | None = None

class DriveUploader:
    """Google Drive uploader with resumable upload support."""
    
    def __init__(
        self,
        settings: CloudSettings | None = None,
        use_oauth: bool = False,
    ):
        """Initialize Drive uploader.
        
        Args:
            settings: Cloud settings (auto-loads if None)
            use_oauth: Use OAuth instead of service account
        """
        ...
    
    def upload_file(
        self,
        file_path: Path,
        folder_id: str,
        custom_name: str | None = None,
        progress_callback: Callable[[float], None] | None = None,
    ) -> CloudResult[DriveUploadMetrics]:
        """Upload file to Google Drive folder."""
        ...
    
    def get_folder_id(self, project_name: str) -> str:
        """Get folder ID from project name mapping."""
        ...


# core/cloud/s3.py
@dataclass
class S3UploadMetrics:
    """Metrics for S3 upload operation."""
    object_key: str | None = None
    presigned_url: str | None = None
    file_size_bytes: int = 0

class S3Uploader:
    """S3 uploader with presigned URL generation."""
    
    def __init__(self, settings: CloudSettings | None = None):
        ...
    
    def upload_file(
        self,
        local_path: Path,
        object_key: str,
    ) -> CloudResult[S3UploadMetrics]:
        """Upload file to S3."""
        ...
    
    def generate_presigned_url(
        self,
        object_key: str,
        expiration: int | None = None,
    ) -> str:
        """Generate presigned download URL."""
        ...


# core/cloud/gmail.py
@dataclass
class EmailMetrics:
    """Metrics for email send operation."""
    message_id: str | None = None
    recipients: list[str] = field(default_factory=list)
    subject: str | None = None
    has_attachment: bool = False

class GmailClient:
    """Gmail API client for sending emails."""
    
    def __init__(self, settings: CloudSettings | None = None):
        ...
    
    def send_email(
        self,
        to: list[str],
        subject: str,
        body: str,
        attachment_path: Path | None = None,
        attachment_name: str | None = None,
        cc: list[str] | None = None,
    ) -> CloudResult[EmailMetrics]:
        """Send email via Gmail API."""
        ...


# core/cloud/clickup.py
@dataclass
class ClickUpMetrics:
    """Metrics for ClickUp operations."""
    task_id: str | None = None
    attachment_id: str | None = None
    comment_id: str | None = None

class ClickUpClient:
    """ClickUp API client for task attachments."""
    
    def __init__(self, settings: CloudSettings | None = None):
        ...
    
    def upload_attachment(
        self,
        task_id: str,
        file_path: Path,
        filename: str | None = None,
    ) -> CloudResult[ClickUpMetrics]:
        """Upload attachment to ClickUp task."""
        ...
    
    def add_comment(
        self,
        task_id: str,
        comment_text: str,
    ) -> CloudResult[ClickUpMetrics]:
        """Add comment to ClickUp task."""
        ...


# core/cloud/factory.py
def create_drive_uploader(
    use_oauth: bool = False,
    settings: CloudSettings | None = None,
) -> DriveUploader:
    """Factory function for Drive uploader."""
    ...

def create_s3_uploader(
    settings: CloudSettings | None = None,
) -> S3Uploader:
    """Factory function for S3 uploader."""
    ...

def create_gmail_client(
    settings: CloudSettings | None = None,
) -> GmailClient:
    """Factory function for Gmail client."""
    ...

def create_clickup_client(
    settings: CloudSettings | None = None,
) -> ClickUpClient:
    """Factory function for ClickUp client."""
    ...
```

### Data Flow

```
User/Pipeline calls upload_to_drive()
         │
         ▼
┌─────────────────────────────────┐
│  core.qa.upload_to_drive()      │  <-- Existing wrapper (updated)
│  - Finds archive path           │
│  - Calls core.cloud             │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  core.cloud.DriveUploader       │
│  - Loads CloudSettings          │
│  - Gets folder ID from mapping  │
│  - Executes resumable upload    │
│  - Returns CloudResult          │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Google Drive API               │
│  (google-api-python-client)     │
└─────────────────────────────────┘
```

### Dependency Handling Pattern

Follow existing `_MAPPER_AVAILABLE` pattern from `core/__init__.py`:

```python
# core/cloud/__init__.py
"""Cloud services module for uploads and notifications.

Optional dependencies:
- Google APIs: pip install google-api-python-client google-auth google-auth-oauthlib
- AWS S3: pip install boto3
"""

from .base import CloudError, CloudOutcome, CloudResult, CloudStatus

# Always available
__all__ = [
    "CloudError",
    "CloudOutcome", 
    "CloudResult",
    "CloudStatus",
]

# Google Drive (optional)
_DRIVE_AVAILABLE = False
try:
    from .drive import DriveUploader, DriveUploadMetrics
    from .gmail import GmailClient, EmailMetrics
    _DRIVE_AVAILABLE = True
    __all__.extend([
        "DriveUploader",
        "DriveUploadMetrics",
        "GmailClient", 
        "EmailMetrics",
    ])
except ImportError:
    pass

# AWS S3 (optional)
_S3_AVAILABLE = False
try:
    from .s3 import S3Uploader, S3UploadMetrics
    _S3_AVAILABLE = True
    __all__.extend([
        "S3Uploader",
        "S3UploadMetrics",
    ])
except ImportError:
    pass

# ClickUp (always available - uses requests)
from .clickup import ClickUpClient, ClickUpMetrics
__all__.extend([
    "ClickUpClient",
    "ClickUpMetrics",
])

# Config always available
from .config import CloudSettings
__all__.append("CloudSettings")

# Factory functions
from .factory import (
    create_drive_uploader,
    create_gmail_client,
    create_s3_uploader,
    create_clickup_client,
)
__all__.extend([
    "create_drive_uploader",
    "create_gmail_client",
    "create_s3_uploader",
    "create_clickup_client",
])


# Feature flags for consumers
def is_drive_available() -> bool:
    return _DRIVE_AVAILABLE

def is_s3_available() -> bool:
    return _S3_AVAILABLE

__all__.extend(["is_drive_available", "is_s3_available"])
```

### Lazy Import Pattern for Heavy Dependencies

Inside each client class, use lazy imports to avoid loading google-api/boto3 until actually needed:

```python
# core/cloud/drive.py
_google_loaded = False
service_account = None
build = None
MediaFileUpload = None
HttpError = None

def _load_google_libs():
    """Lazy-load Google libraries on first use."""
    global _google_loaded, service_account, build, MediaFileUpload, HttpError
    if _google_loaded:
        return
    try:
        from google.oauth2 import service_account as sa
        from googleapiclient.discovery import build as bld
        from googleapiclient.http import MediaFileUpload as mfu
        from googleapiclient.errors import HttpError as he
        service_account = sa
        build = bld
        MediaFileUpload = mfu
        HttpError = he
        _google_loaded = True
    except ImportError as e:
        raise ImportError(
            "Google Drive dependencies not installed. Run:\n"
            "  pip install google-api-python-client google-auth google-auth-oauthlib"
        ) from e
```

## Dependencies

| Dependency | Type | Reason |
|------------|------|--------|
| `pydantic-settings` | Internal | CloudSettings configuration |
| `google-api-python-client` | External (optional) | Drive and Gmail APIs |
| `google-auth` | External (optional) | Service account auth |
| `google-auth-oauthlib` | External (optional) | OAuth flow |
| `boto3` | External (optional) | S3 uploads |
| `requests` | Internal | ClickUp API (already in core) |

## Implementation Phases

### Phase 1: Foundation (base.py, config.py)
**Files to create:**
- `core/cloud/__init__.py` - Module init with feature flags
- `core/cloud/base.py` - CloudError, CloudResult, CloudStatus
- `core/cloud/config.py` - CloudSettings Pydantic model

**Acceptance:**
- [ ] Types compile and are importable
- [ ] CloudSettings loads from environment
- [ ] Feature flags work correctly

**Estimated effort:** Small (1-2 hours)

### Phase 2: Drive Upload (drive.py)
**Files to create:**
- `core/cloud/drive.py` - DriveUploader class

**Dependencies:** Phase 1

**Acceptance:**
- [ ] DriveUploader initializes with settings
- [ ] Lazy import pattern works
- [ ] Upload returns CloudResult[DriveUploadMetrics]
- [ ] OAuth and service account auth both work
- [ ] Resumable upload with progress callback works

**Estimated effort:** Medium (3-4 hours)

### Phase 3: S3 Upload (s3.py)
**Files to create:**
- `core/cloud/s3.py` - S3Uploader class

**Dependencies:** Phase 1

**Acceptance:**
- [ ] S3Uploader initializes with settings
- [ ] Lazy import pattern works
- [ ] Upload returns CloudResult[S3UploadMetrics]
- [ ] Presigned URL generation works

**Estimated effort:** Small (2 hours)

### Phase 4: Gmail Client (gmail.py)
**Files to create:**
- `core/cloud/gmail.py` - GmailClient class

**Dependencies:** Phase 1

**Acceptance:**
- [ ] GmailClient initializes with settings
- [ ] OAuth flow works
- [ ] Email with attachment sends correctly
- [ ] Returns CloudResult[EmailMetrics]

**Estimated effort:** Small (2 hours)

### Phase 5: ClickUp Client (clickup.py)
**Files to create:**
- `core/cloud/clickup.py` - ClickUpClient class

**Dependencies:** Phase 1

**Acceptance:**
- [ ] ClickUpClient initializes with settings
- [ ] Attachment upload works
- [ ] Comment posting works
- [ ] Returns CloudResult[ClickUpMetrics]

**Estimated effort:** Small (1-2 hours)

### Phase 6: Factory Functions (factory.py)
**Files to create:**
- `core/cloud/factory.py` - create_*() functions

**Dependencies:** Phases 2-5

**Acceptance:**
- [ ] All factory functions work
- [ ] Auto-load settings when not provided
- [ ] Graceful errors when dependencies missing

**Estimated effort:** Small (1 hour)

### Phase 7: QA Integration
**Files to modify:**
- `core/qa/upload_and_submit_message.py` - Use core.cloud instead of tools/
- `core/qa/__init__.py` - Update exports if needed

**Dependencies:** Phases 1-6

**Acceptance:**
- [ ] `upload_to_drive()` uses core.cloud.DriveUploader
- [ ] `send_email_report()` uses core.cloud.GmailClient
- [ ] Backward compatible result types (QAResult)
- [ ] Existing CLI commands still work

**Estimated effort:** Medium (2-3 hours)

### Phase 8: Pipeline Integration
**Files to modify:**
- `healthsparq/phases/report.py` - Optional upload after archive
- `sapphire/phases/report.py` - Optional upload after archive

**Dependencies:** Phase 7

**Acceptance:**
- [ ] Phase 5 can optionally upload archive to Drive
- [ ] Phase 5 can optionally send email report
- [ ] Controlled via CLI flags (--upload, --email)

**Estimated effort:** Medium (3-4 hours)

### Phase 9: Documentation and Testing
**Files to create:**
- `core/cloud/CLAUDE.md` - Module documentation
- `core/tests/test_cloud/` - Unit tests

**Dependencies:** All previous phases

**Acceptance:**
- [ ] CLAUDE.md documents all public APIs
- [ ] Unit tests cover happy path and error cases
- [ ] Optional dependency tests (skip if not installed)

**Estimated effort:** Medium (3-4 hours)

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| OAuth token refresh issues | Medium | Follow existing tools/ patterns exactly |
| Credentials file path resolution | Medium | Use Path resolution relative to tools/secrets/ |
| Breaking existing tools/ users | High | Keep tools/ functional, add deprecation warnings |
| Large file upload failures | Medium | Preserve resumable upload with retry logic |
| Missing dependencies at runtime | Low | Clear error messages with install instructions |

## Open Questions

- [ ] Should `tools/drive_folder_mapping.json` be moved to `core/cloud/data/` or stay in tools/?
  - **Recommendation:** Keep in tools/ but allow CloudSettings to specify path
  
- [ ] Should we add a CLI to core.cloud (`python -m core.cloud upload ...`)?
  - **Recommendation:** Not initially. Keep CLI in core.qa or let tools/ CLI delegate

- [ ] Should ClickUp integration move to core/cloud?
  - **Recommendation:** Yes, for consistency. It's lightweight (requests only)

## Success Criteria

1. All 4 upload/notification services work via core.cloud module
2. Optional dependencies handled gracefully (no import errors)
3. CloudResult pattern consistent with QAResult pattern
4. healthsparq/sapphire can upload archives in Phase 5
5. Existing core.qa upload_to_drive() and send_email_report() work unchanged
6. tools/ scripts work via deprecation shim (imports from core.cloud)

## Configuration Migration

### Current tools/ Pattern
```bash
# Credentials in tools/secrets/
tools/secrets/google_drive_credentials.json  # Service account
tools/secrets/oauth_credentials.json         # OAuth client
tools/secrets/gmail_token.json               # OAuth token
tools/secrets/aws_credentials.json           # S3 credentials

# Mapping file
tools/drive_folder_mapping.json              # Project -> folder ID
```

### New core/cloud Pattern
```bash
# Environment variables (recommended)
GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/google_drive_credentials.json
GOOGLE_OAUTH_CREDENTIALS=/path/to/oauth_credentials.json
DRIVE_FOLDER_MAPPING_FILE=/path/to/drive_folder_mapping.json
S3_BUCKET_NAME=my-bucket
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
CLICKUP_API_TOKEN=pk_xxx

# Or CloudSettings with file paths
settings = CloudSettings(
    google_service_account_file=Path("tools/secrets/google_drive_credentials.json"),
    drive_folder_mapping_file=Path("tools/drive_folder_mapping.json"),
)
```

## Backward Compatibility

Update `core/qa/upload_and_submit_message.py` to use core.cloud internally:

```python
# core/qa/upload_and_submit_message.py
def upload_to_drive(...) -> QAResult[UploadMetrics]:
    """Upload 7z archive to Google Drive.
    
    Now uses core.cloud.DriveUploader internally.
    """
    try:
        from core.cloud import create_drive_uploader, is_drive_available
        
        if not is_drive_available():
            # Fall back to tools/ for backward compatibility
            _ensure_tools_importable()
            from tools.drive_uploader import upload_archive
            # ... existing code ...
        
        uploader = create_drive_uploader(use_oauth=use_oauth)
        result = uploader.upload_file(...)
        
        # Convert CloudResult to QAResult for API compatibility
        return QAResult(
            outcome=QAOutcome(
                status=QAStatus.SUCCESS if result.is_success else QAStatus.ERROR,
                message=result.outcome.message,
                ...
            ),
            metrics=UploadMetrics(
                file_id=result.metrics.file_id,
                ...
            ),
        )
    except ImportError:
        # Graceful fallback to tools/
        ...
```

This ensures:
1. Existing `from core.qa import upload_to_drive` works unchanged
2. Return type remains `QAResult[UploadMetrics]`
3. Falls back to tools/ if core.cloud not fully available

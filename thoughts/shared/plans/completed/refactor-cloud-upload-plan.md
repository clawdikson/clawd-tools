# Refactoring Plan: Cloud Upload and Reporting Migration to core/
Created: 2026-01-24
Author: phoenix-agent

## Overview
**Goal:** Consolidate cloud upload (Drive, S3) and reporting (Email, ClickUp) functionality from `tools/` into `core/`, eliminating code duplication while maintaining backward compatibility.

**Risk Level:** Medium
**Estimated Effort:** 3-4 days

## Current State Analysis

### Files to Migrate (2,617 total lines)

| File | Lines | Purpose |
|------|-------|---------|
| `tools/drive_uploader.py` | 689 | DriveUploader class, OAuth/ServiceAccount auth, CLI |
| `tools/s3_uploader.py` | 266 | S3Uploader class, presigned URLs |
| `tools/xlsx_to_clickup.py` | 1,146 | EmailClient, ClickUpClient, screenshot generation, CLI |
| `tools/project_config.py` | 159 | ProjectConfig loader (audiobee/healthsparq detection) |
| `core/qa/upload_and_submit_message.py` | 362 | Thin wrappers calling tools/ functions |

### Code Smells Identified

| Smell | Location | Severity | Lines |
|-------|----------|----------|-------|
| **Duplicated OAuth flow** | `drive_uploader.py:182-215`, `xlsx_to_clickup.py:502-543` | High | ~70 lines |
| **Duplicated lazy loading** | `drive_uploader.py:64-96`, `s3_uploader.py:125-141`, `xlsx_to_clickup.py:457-479` | Medium | ~60 lines |
| **Duplicated logger fallback** | All 4 files | Low | ~20 lines |
| **sys.path manipulation** | `drive_uploader.py:498`, `xlsx_to_clickup.py:50-54`, `upload_and_submit_message.py:66-69` | Medium | ~15 lines |
| **Retry logic duplication** | `drive_uploader.py:349-400`, `xlsx_to_clickup.py:342-384` | Medium | ~80 lines |

### Dependency Graph

```
core/qa/upload_and_submit_message.py
  |
  +-- tools/drive_uploader.py
  |     |-- google-api-python-client (optional)
  |     |-- google-auth (optional)
  |     |-- google-auth-oauthlib (optional)
  |     +-- tools/project_config.py
  |
  +-- tools/xlsx_to_clickup.py
        |-- google-api-python-client (optional)
        |-- google-auth-oauthlib (optional)
        |-- matplotlib (required for screenshots)
        |-- pandas (required)
        |-- openpyxl (required)
        |-- requests (required for ClickUp)
        +-- tools/s3_uploader.py
              +-- boto3 (optional)
```

### Test Coverage

- `tools/tests/test_s3_uploader.py`: 370 lines, good coverage
- `tools/tests/test_xlsx_to_clickup.py`: 393 lines, good coverage
- `tools/tests/test_drive_integration.py`: 170 lines, integration tests
- `core/qa/upload_and_submit_message.py`: No dedicated tests (uses tools/ tests)

## Refactoring Strategy

### Approach: Extract & Consolidate

1. Create new `core/cloud/` module for unified cloud operations
2. Extract shared patterns (OAuth, lazy loading, retry) into reusable components
3. Keep tools/ CLIs as thin wrappers calling core/
4. Migrate core/qa/upload_and_submit_message.py to use core/cloud directly

### Target Architecture

```
core/
├── cloud/                          # NEW MODULE
│   ├── __init__.py                 # Public exports
│   ├── base.py                     # CloudProvider Protocol, CloudConfig
│   ├── auth/                       # Authentication (consolidated)
│   │   ├── __init__.py
│   │   ├── oauth.py                # GoogleOAuth class (consolidated)
│   │   └── service_account.py      # ServiceAccountAuth class
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── drive.py                # DriveUploader (from tools/)
│   │   ├── s3.py                   # S3Uploader (from tools/)
│   │   └── gmail.py                # GmailClient (from xlsx_to_clickup.py)
│   ├── clients/
│   │   └── clickup.py              # ClickUpClient (from xlsx_to_clickup.py)
│   └── utils/
│       ├── lazy_import.py          # Unified lazy loading pattern
│       └── retry.py                # Unified retry with backoff
│
├── reporting/                      # NEW MODULE (or extend qa/)
│   ├── __init__.py
│   ├── screenshot.py               # generate_screenshot() from xlsx_to_clickup
│   └── xlsx_parser.py              # resolve_xlsx_path, parse_run_timestamps
│
└── qa/
    ├── upload_and_submit_message.py  # REFACTORED: use core/cloud directly
    └── ...
```

### Before (tools/drive_uploader.py OAuth flow)

```python
# tools/drive_uploader.py:182-215 (duplicated in xlsx_to_clickup.py)
def _get_oauth_credentials(self):
    """Get OAuth credentials, prompting for browser login if needed."""
    if InstalledAppFlow is None:
        raise ImportError(...)
    creds = None
    if self.token_path and self.token_path.exists():
        creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(...)
            creds = flow.run_local_server(port=0)
        with open(self.token_path, "w") as token_file:
            token_file.write(creds.to_json())
    return creds
```

### After (core/cloud/auth/oauth.py)

```python
# core/cloud/auth/oauth.py - Consolidated OAuth handler
from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

from ..utils.lazy_import import lazy_import_google_auth

if TYPE_CHECKING:
    from google.oauth2.credentials import Credentials

class GoogleOAuth:
    """Unified Google OAuth 2.0 handler for Drive and Gmail.
    
    Consolidates duplicated OAuth logic from drive_uploader.py and xlsx_to_clickup.py.
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
        """Get valid OAuth credentials, refreshing or re-authenticating as needed."""
        Credentials, InstalledAppFlow = lazy_import_google_auth()
        
        if self._credentials and self._credentials.valid:
            return self._credentials
        
        # Load existing token
        if self.token_path.exists():
            self._credentials = Credentials.from_authorized_user_file(
                str(self.token_path), self.scopes
            )
        
        # Refresh or re-auth
        if not self._credentials or not self._credentials.valid:
            if self._credentials and self._credentials.expired and self._credentials.refresh_token:
                from google.auth.transport.requests import Request
                self._credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), self.scopes
                )
                self._credentials = flow.run_local_server(port=0)
            
            # Save token
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_path, "w") as f:
                f.write(self._credentials.to_json())
        
        return self._credentials
```

## Implementation Phases

### Phase 0: Safety Net (0.5 day)
**Goal:** Ensure we can detect breakage during migration

**Tasks:**
- [ ] Run existing tools/tests/ to establish baseline
- [ ] Document current import paths used by healthsparq/sapphire
- [ ] Create integration test that calls all public APIs

**Commands:**
```bash
.venv/bin/pytest tools/tests/ -v --tb=short
```

**Acceptance:**
- [ ] All 20+ existing tests pass
- [ ] Import paths documented

### Phase 1: Create core/cloud/ Foundation (1 day)
**Goal:** Build shared infrastructure without breaking existing code

**Tasks:**
- [ ] Create `core/cloud/__init__.py` with public API stubs
- [ ] Create `core/cloud/utils/lazy_import.py` - unified lazy loading
- [ ] Create `core/cloud/utils/retry.py` - unified retry logic
- [ ] Create `core/cloud/auth/oauth.py` - consolidated OAuth
- [ ] Create `core/cloud/auth/service_account.py` - service account auth
- [ ] Add optional dependency handling in `core/__init__.py`

**New Files:**
```
core/cloud/__init__.py
core/cloud/base.py
core/cloud/utils/__init__.py
core/cloud/utils/lazy_import.py
core/cloud/utils/retry.py
core/cloud/auth/__init__.py
core/cloud/auth/oauth.py
core/cloud/auth/service_account.py
```

**Rollback:** `git checkout -- core/`

**Acceptance:**
- [ ] `from core.cloud import GoogleOAuth` works
- [ ] Optional imports don't break when google-auth not installed

### Phase 2: Migrate Uploaders (1 day)
**Goal:** Move DriveUploader and S3Uploader to core/cloud/providers/

**Tasks:**
- [ ] Create `core/cloud/providers/drive.py` from `tools/drive_uploader.py`
- [ ] Create `core/cloud/providers/s3.py` from `tools/s3_uploader.py`
- [ ] Update to use `core/cloud/auth/oauth.py`
- [ ] Update to use `core/cloud/utils/lazy_import.py`
- [ ] Add backward-compat shim to `tools/drive_uploader.py`:
  ```python
  # tools/drive_uploader.py (becomes thin shim)
  """Backward compatibility shim. Use core.cloud.providers.drive instead."""
  import warnings
  warnings.warn(
      "tools.drive_uploader is deprecated. Use core.cloud.DriveUploader instead.",
      DeprecationWarning,
      stacklevel=2,
  )
  from core.cloud.providers.drive import DriveUploader, upload_archive
  # Re-export for backward compatibility
  __all__ = ["DriveUploader", "upload_archive"]
  ```

**Rollback:** `git checkout -- core/cloud/providers/ tools/drive_uploader.py tools/s3_uploader.py`

**Acceptance:**
- [ ] `from core.cloud import DriveUploader, S3Uploader` works
- [ ] `from tools.drive_uploader import upload_archive` still works (with warning)
- [ ] All tools/tests/ pass

### Phase 3: Migrate Email/ClickUp Clients (1 day)
**Goal:** Move EmailClient and ClickUpClient to core/

**Tasks:**
- [ ] Create `core/cloud/providers/gmail.py` from EmailClient
- [ ] Create `core/cloud/clients/clickup.py` from ClickUpClient
- [ ] Create `core/reporting/screenshot.py` from generate_screenshot
- [ ] Create `core/reporting/xlsx_parser.py` for resolve_xlsx_path, parse_run_timestamps
- [ ] Add backward-compat shim to `tools/xlsx_to_clickup.py`

**Rollback:** `git checkout -- core/cloud/providers/gmail.py core/cloud/clients/ core/reporting/`

**Acceptance:**
- [ ] `from core.cloud import GmailClient, ClickUpClient` works
- [ ] `from tools.xlsx_to_clickup import send_report_email` still works
- [ ] All tools/tests/ pass

### Phase 4: Refactor core/qa/upload_and_submit_message.py (0.5 day)
**Goal:** Remove sys.path hacks, use core/cloud directly

**Tasks:**
- [ ] Update imports to use `core.cloud.*` instead of `tools.*`
- [ ] Remove `_ensure_tools_importable()` and sys.path manipulation
- [ ] Simplify error handling (core/cloud provides better errors)
- [ ] Update docstrings

**Before:**
```python
def _ensure_tools_importable() -> None:
    """Ensure tools module is importable by adding to sys.path if needed."""
    tools_path = _get_tools_path()
    tools_parent = str(tools_path.parent)
    if tools_parent not in sys.path:
        sys.path.insert(0, tools_parent)
```

**After:**
```python
# No sys.path manipulation needed - core/cloud is in same package
from core.cloud import DriveUploader, upload_archive, GmailClient, send_report_email
```

**Rollback:** `git checkout -- core/qa/upload_and_submit_message.py`

**Acceptance:**
- [ ] `from core.qa import upload_to_drive, send_email_report` works
- [ ] No sys.path manipulation in core/qa/

### Phase 5: Cleanup & Documentation (0.5 day)
**Goal:** Remove deprecated code, update documentation

**Tasks:**
- [ ] Move tests from `tools/tests/` to `core/tests/test_cloud/`
- [ ] Update `core/CLAUDE.md` with cloud module documentation
- [ ] Create `core/cloud/CLAUDE.md` module documentation
- [ ] Update tools/README.md with deprecation notices
- [ ] Delete tools/project_config.py (functionality in core/config/)

**Acceptance:**
- [ ] All tests pass from new location
- [ ] Documentation updated
- [ ] healthsparq/ and sapphire/ unchanged (still work)

## Backward Compatibility

### Breaking Changes
| Change | Impact | Migration Path |
|--------|--------|----------------|
| None (shims provided) | None | N/A |

### Deprecation Strategy

```python
# tools/drive_uploader.py (shim)
"""
DEPRECATED: This module is deprecated and will be removed in v4.0.
Use core.cloud.providers.drive instead.

Migration:
    # Old
    from tools.drive_uploader import DriveUploader, upload_archive
    
    # New
    from core.cloud import DriveUploader, upload_archive
"""
import warnings

def _emit_deprecation_warning():
    warnings.warn(
        "tools.drive_uploader is deprecated. "
        "Use 'from core.cloud import DriveUploader, upload_archive' instead. "
        "This shim will be removed in v4.0.",
        DeprecationWarning,
        stacklevel=3,
    )

# Re-export from new location
from core.cloud.providers.drive import DriveUploader as _DriveUploader
from core.cloud.providers.drive import upload_archive as _upload_archive

def upload_archive(*args, **kwargs):
    _emit_deprecation_warning()
    return _upload_archive(*args, **kwargs)

class DriveUploader(_DriveUploader):
    def __init__(self, *args, **kwargs):
        _emit_deprecation_warning()
        super().__init__(*args, **kwargs)
```

### Tools CLI Preservation

Keep CLIs working during transition:

```python
# tools/drive_uploader.py CLI section (keep working)
if __name__ == "__main__":
    # Import from core but keep CLI here
    from core.cloud.providers.drive import app
    app()
```

Or better, create `tools/cli/` with thin CLI wrappers:

```python
# tools/cli/drive.py
"""Drive upload CLI - delegates to core.cloud."""
from core.cloud.providers.drive import app

if __name__ == "__main__":
    app()
```

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Import cycles | Medium | High | Test imports at each phase; use TYPE_CHECKING |
| Missing optional deps break core/ | Medium | High | Lazy imports everywhere; test without google-auth |
| External consumers break | Low | Medium | Shims emit warnings; document migration path |
| Test coverage gaps | Medium | Medium | Require tests pass at each phase |

## Metrics

### Code Reduction Estimate

| Component | Before | After | Reduction |
|-----------|--------|-------|-----------|
| OAuth logic | ~70 lines x2 | ~50 lines x1 | ~90 lines (64%) |
| Lazy loading | ~25 lines x3 | ~40 lines x1 | ~35 lines (47%) |
| Logger fallback | ~5 lines x4 | ~5 lines x1 | ~15 lines (75%) |
| Retry logic | ~50 lines x2 | ~40 lines x1 | ~60 lines (60%) |
| **Total** | **~2,617** | **~2,200** | **~400 lines (15%)** |

### Architectural Improvements

| Metric | Before | After |
|--------|--------|-------|
| Files with sys.path hacks | 3 | 0 |
| Duplicated auth code locations | 2 | 1 |
| Optional dep handling patterns | 3 | 1 |
| Test file locations | 1 (tools/tests/) | 1 (core/tests/test_cloud/) |

## Success Criteria

1. All existing tests pass (tools/tests/ + core/tests/)
2. `from tools.drive_uploader import upload_archive` still works (with warning)
3. `from core.cloud import DriveUploader, S3Uploader, GmailClient` works
4. healthsparq/ and sapphire/ require zero code changes
5. Optional dependencies (google-auth, boto3) don't break core/ imports
6. Code reduced by ~15% (400+ lines)
7. No sys.path manipulation in core/

## File-Level Migration Map

| Source | Destination | Notes |
|--------|-------------|-------|
| `tools/drive_uploader.py` | `core/cloud/providers/drive.py` | Keep CLI in tools/ |
| `tools/s3_uploader.py` | `core/cloud/providers/s3.py` | - |
| `tools/xlsx_to_clickup.py` EmailClient | `core/cloud/providers/gmail.py` | - |
| `tools/xlsx_to_clickup.py` ClickUpClient | `core/cloud/clients/clickup.py` | - |
| `tools/xlsx_to_clickup.py` generate_screenshot | `core/reporting/screenshot.py` | - |
| `tools/xlsx_to_clickup.py` resolve_xlsx_path | `core/reporting/xlsx_parser.py` | - |
| `tools/project_config.py` | DELETE (use core/config/) | Duplicate of core/config/ |
| OAuth (both files) | `core/cloud/auth/oauth.py` | Consolidated |
| Lazy loading (3 files) | `core/cloud/utils/lazy_import.py` | Consolidated |

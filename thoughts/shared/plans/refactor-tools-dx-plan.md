# Refactoring Plan: tools/ Directory DX Improvements
Created: 2025-01-24
Author: phoenix-agent

## Overview
**Goal:** Consolidate duplicated patterns, standardize error handling and logging, migrate to Typer CLI, and improve type safety across 12+ tool scripts
**Risk Level:** Medium (tools are auxiliary, not core pipeline)
**Estimated Effort:** ~25-30 hours across 5 phases

## Current State Analysis

### Code Smells Identified
| Smell | Location | Severity |
|-------|----------|----------|
| Duplicated lazy loading pattern | `drive_uploader.py:55-96`, `s3_uploader.py:119-141`, `xlsx_to_clickup.py:450-478` | High |
| Duplicated OAuth flow | `drive_uploader.py:182-215`, `xlsx_to_clickup.py:502-543` | High |
| Inconsistent config loading | `project_config.py`, `project_registry.py`, inline in `drive_uploader.py` | Medium |
| argparse vs Typer mix | `validate_env.py`, `validate_migration.py`, `rollback_migration.py`, `find_hardcoded_credentials.py` use argparse; rest use Typer | Medium |
| Mixed logging approaches | `core.logging` with stdlib fallback everywhere, plus print statements | Medium |
| Mixed data structures | `ProjectConfig` uses NamedTuple, `S3Config` uses dataclass, others use raw dicts | Low |
| Silent exception handling | `validate_migration.py:34` catches generic Exception silently | High |
| subprocess without timeout | `sample_run_all.py:69-72`, `rollback_migration.py:25-31` | Medium |
| Hardcoded recipients | `xlsx_to_clickup.py:937` hardcodes email addresses | Low |

### Dependency Graph
```
tools/
  |-- drive_uploader.py
  |     \-- project_config.py (load_project_config)
  |-- s3_uploader.py (standalone)
  |-- xlsx_to_clickup.py
  |     |-- project_config.py
  |     \-- s3_uploader.py
  |-- project_registry.py (standalone, reads projects.yaml)
  |-- project_config.py (standalone)
  |-- validate_env.py (standalone)
  |-- validate_migration.py (standalone)
  |-- rollback_migration.py (standalone)
  |-- find_hardcoded_credentials.py (standalone)
  |-- sample_run_all.py
  |     |-- drive_uploader.py
  |     \-- xlsx_to_clickup.py
  |-- migrate_datastore/ (well-structured, uses Typer)
  |-- sqlitefs_explorer/ (well-structured, Textual app)
  \-- dashboard/ (well-structured, Textual app)
```

### Test Coverage
- Current coverage: ~40% (based on test files present)
- Tests exist: Yes (`tools/tests/` has 8 test files)
- Integration tests: Partial (mock-based for Drive/S3)
- **Gap:** No tests for `validate_env.py`, `validate_migration.py`, `rollback_migration.py`, `find_hardcoded_credentials.py`

## Refactoring Strategy

### Approach: Extract & Consolidate
1. Create `tools/common/` package for shared utilities
2. Extract lazy loading, OAuth, and logging into reusable modules
3. Migrate argparse CLIs to Typer
4. Standardize on dataclasses for config objects
5. Add proper exception hierarchy

## Implementation Phases

### Phase 0: Safety Net
**Goal:** Ensure we can detect breakage
**Tasks:**
- [ ] Add tests for `validate_env.py` core functions
- [ ] Add tests for `find_hardcoded_credentials.py` scan functions
- [ ] Add tests for `rollback_migration.py` git operations (mocked)
- [ ] Verify existing tests pass: `pytest tools/tests/ -v`

**Acceptance:** 60%+ coverage on target files

---

### Phase 1: Create Common Package
**Goal:** Extract shared patterns into `tools/common/`
**Files to create:**
```
tools/common/
  __init__.py
  lazy_loader.py      # Generic lazy import pattern
  google_auth.py      # OAuth + Service Account flows
  logging_setup.py    # Unified logging with core.logging fallback
  config_types.py     # Dataclass configs (ProjectConfig, S3Config, etc.)
  exceptions.py       # ToolsError hierarchy
  cli_utils.py        # Typer helpers (error formatting, progress bars)
```

**Before (lazy loading in 3 files):**
```python
# drive_uploader.py
_google_libs_loaded = False
service_account = None
build = None
# ... 15 more lines

def _load_google_libs():
    global _google_libs_loaded, service_account, build, ...
    if _google_libs_loaded:
        return
    try:
        from google.oauth2 import service_account as sa
        # ... more imports
```

**After:**
```python
# tools/common/lazy_loader.py
from typing import TypeVar, Callable
from functools import lru_cache

T = TypeVar('T')

def lazy_import(module_path: str, attr: str | None = None) -> Callable[[], T]:
    """Create a lazy importer for a module or attribute."""
    @lru_cache(maxsize=1)
    def loader() -> T:
        import importlib
        mod = importlib.import_module(module_path)
        return getattr(mod, attr) if attr else mod
    return loader

# Usage in drive_uploader.py:
from tools.common.lazy_loader import lazy_import

service_account = lazy_import("google.oauth2.service_account")
build = lazy_import("googleapiclient.discovery", "build")
```

**Tasks:**
- [ ] Create `tools/common/__init__.py`
- [ ] Create `tools/common/lazy_loader.py` with generic lazy import
- [ ] Create `tools/common/google_auth.py` extracting OAuth from drive_uploader + xlsx_to_clickup
- [ ] Create `tools/common/logging_setup.py` with `get_logger()` function
- [ ] Create `tools/common/exceptions.py` with base `ToolsError`
- [ ] Add tests for common module

**Rollback:** Git revert to commit before phase

**Acceptance:**
- [ ] All existing tests pass
- [ ] `tools/common/` has 80%+ test coverage

---

### Phase 2: Migrate to Common Package
**Goal:** Update existing tools to use common package
**Tasks:**
- [ ] Update `drive_uploader.py` to use `tools.common.google_auth`
- [ ] Update `s3_uploader.py` to use `tools.common.lazy_loader`
- [ ] Update `xlsx_to_clickup.py` to use `tools.common.google_auth` (remove 100+ lines of OAuth code)
- [ ] Update all tools to use `tools.common.logging_setup.get_logger()`
- [ ] Convert `ProjectConfig` from NamedTuple to dataclass in `tools/common/config_types.py`
- [ ] Move `S3Config` to `tools/common/config_types.py`

**Before (xlsx_to_clickup.py OAuth - 90 lines):**
```python
# Lazy-loaded Google libraries
_gmail_libs_loaded = False
GmailCredentials = None
GmailInstalledAppFlow = None
gmail_build = None

def _load_gmail_libs():
    """Lazy-load Google Gmail libraries on first use."""
    # ... 20 lines

class EmailClient:
    def _get_credentials(self):
        # ... 40 lines duplicating drive_uploader.py
```

**After:**
```python
from tools.common.google_auth import get_gmail_service

class EmailClient:
    @property
    def service(self):
        if self._service is None:
            self._service = get_gmail_service(
                credentials_path=self.credentials_path,
                token_path=self.token_path,
            )
        return self._service
```

**Rollback:** Git revert

**Acceptance:**
- [ ] All tests pass
- [ ] No behavior change (same CLI interface)
- [ ] Drive upload still works
- [ ] Email sending still works

---

### Phase 3: Migrate argparse to Typer
**Goal:** Consistent CLI experience across all tools
**Files to migrate:**
- [ ] `validate_env.py` (argparse -> Typer)
- [ ] `validate_migration.py` (argparse -> Typer)
- [ ] `rollback_migration.py` (argparse -> Typer)
- [ ] `find_hardcoded_credentials.py` (argparse -> Typer)

**Before (validate_env.py):**
```python
import argparse

def main():
    parser = argparse.ArgumentParser(description="Validate environment configuration")
    parser.add_argument("--project", help="Project name")
    parser.add_argument("--site-type", help="Site type")
    parser.add_argument("--env-file", help="Path to .env file")
    parser.add_argument("--check-all", action="store_true")
    args = parser.parse_args()
    # ...

if __name__ == "__main__":
    main()
```

**After:**
```python
import typer
from pathlib import Path
from typing import Annotated

app = typer.Typer(
    name="validate-env",
    help="Validate environment configuration for scraping projects",
)

@app.command()
def validate(
    project: Annotated[str | None, typer.Option("--project", "-p", help="Project name")] = None,
    site_type: Annotated[str | None, typer.Option("--site-type", "-t", help="Site type")] = None,
    env_file: Annotated[Path | None, typer.Option("--env-file", "-f", help="Path to .env file")] = None,
    check_all: Annotated[bool, typer.Option("--check-all", help="Check all .env files")] = False,
):
    """Validate environment configuration."""
    # ...

if __name__ == "__main__":
    app()
```

**Rollback:** Git revert

**Acceptance:**
- [ ] CLI help matches existing behavior
- [ ] All existing command patterns still work
- [ ] Exit codes unchanged

---

### Phase 4: Error Handling Standardization
**Goal:** Replace broad Exception catches with specific error handling
**Tasks:**
- [ ] Create `tools/common/exceptions.py`:
  ```python
  class ToolsError(Exception):
      """Base exception for tools package."""
      pass

  class ConfigurationError(ToolsError):
      """Invalid or missing configuration."""
      pass

  class CredentialsError(ToolsError):
      """Authentication/credentials issue."""
      pass

  class MigrationError(ToolsError):
      """Data migration failure."""
      pass

  class ValidationError(ToolsError):
      """Validation failure."""
      pass
  ```
- [ ] Update `validate_migration.py:34` - replace `except Exception` with specific catches
- [ ] Update `find_hardcoded_credentials.py:94` - replace `except Exception`
- [ ] Add timeout to subprocess calls in `sample_run_all.py` and `rollback_migration.py`:
  ```python
  result = subprocess.run(
      cmd,
      cwd=cwd,
      capture_output=True,
      text=True,
      timeout=300,  # 5 minute timeout
  )
  ```
- [ ] Remove silent exception swallowing - always log errors

**Rollback:** Git revert

**Acceptance:**
- [ ] No silent failures
- [ ] All subprocess calls have timeouts
- [ ] Specific error types for different failure modes

---

### Phase 5: Cleanup & Documentation
**Goal:** Remove deprecated code, update documentation
**Tasks:**
- [ ] Remove hardcoded email addresses, move to config:
  ```python
  # Before: xlsx_to_clickup.py
  DEFAULT_RECIPIENTS = ["operations@audiobee.ai", "dikson@audiobee.ai"]
  
  # After: tools/common/config_types.py
  @dataclass
  class EmailConfig:
      default_recipients: list[str] = field(default_factory=lambda: os.environ.get(
          "TOOLS_DEFAULT_RECIPIENTS", 
          "operations@audiobee.ai,dikson@audiobee.ai"
      ).split(","))
  ```
- [ ] Update `tools/README.md` with new structure
- [ ] Add docstrings to all public functions in `tools/common/`
- [ ] Create `tools/common/README.md` explaining the shared utilities

**Rollback:** Git revert

**Acceptance:**
- [ ] No hardcoded credentials or emails
- [ ] All public APIs documented
- [ ] README.md updated

---

## Backward Compatibility

### Breaking Changes
| Change | Impact | Migration Path |
|--------|--------|----------------|
| None expected | N/A | CLI interfaces preserved |

### Import Path Changes
| Old Import | New Import | Deprecation |
|------------|------------|-------------|
| N/A | All new imports are additions | N/A |

## Risks & Mitigations
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| OAuth flow regression | Medium | High | Manual test Google Drive upload before merging |
| Import cycle | Low | Medium | Careful dependency ordering in common/ |
| Test flakiness | Low | Low | Use mocks for external services |

## Metrics
| Metric | Before | Target |
|--------|--------|--------|
| Lines of duplicated code | ~300 | <50 |
| argparse-based CLIs | 4 | 0 |
| Exception catches without type | 8 | 0 |
| Test coverage | 40% | 70% |
| Subprocess without timeout | 4 | 0 |

## Success Criteria
1. All tests pass
2. No regression in CLI functionality
3. Drive upload, S3 upload, and email sending work correctly
4. Duplicated OAuth code eliminated (~150 lines removed)
5. All tools use Typer for CLI
6. No subprocess calls without timeout
7. Test coverage above 70%

## Quick Wins (Can Do Immediately)

These changes are low-risk and high-value:

1. **Add subprocess timeouts** (~30 min)
   - `sample_run_all.py:69-72`
   - `rollback_migration.py:25-31`
   
2. **Fix silent exception handling** (~15 min)
   - `validate_migration.py:34-36` - log the error before continuing
   
3. **Move hardcoded emails to env var** (~15 min)
   - `xlsx_to_clickup.py:937`

## Recommended Sequence

1. Phase 0 first (safety net)
2. Phase 1 + Phase 2 together (creates value faster)
3. Phase 3 (argparse migration - can be parallelized)
4. Phase 4 (error handling - independent)
5. Phase 5 last (cleanup)

Total estimated time with parallelization: **20-25 hours**

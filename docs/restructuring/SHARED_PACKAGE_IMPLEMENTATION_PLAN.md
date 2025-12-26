# Shared Package Implementation Plan

**Version**: 2.0
**Status**: Revised Based on Expert Reviews
**Created**: 2025-12-26
**Updated**: 2025-12-26 (Incorporated feedback from 9 specialized reviewers)
**Scope**: Enhance existing shared_package for 95+ scraper projects

---

## Executive Summary

**REVISED v2.0**: This plan incorporates feedback from 9 specialized expert reviews (Security, Performance, Architecture, Migration, Testing, Logging, API Design, DevOps, Packaging). Key changes include:

- **NEW Phase 0**: Migration Tooling (critical pre-requisite)
- **Security**: All credentials MUST use `SecretStr`
- **Performance**: Memory-bounded deduplication, async-safe logging
- **Architecture**: Registry pattern, TYPE_CHECKING guards
- **Migration**: Support function exports, preserve auto-init behavior
- **Testing**: Mock infrastructure before coverage targets

### Review Summary

| Reviewer         | Verdict              | Key Action             |
| ---------------- | -------------------- | ---------------------- |
| Python Packaging | APPROVE_WITH_CHANGES | Flat layout fix        |
| Security         | **NEEDS_WORK**       | SecretStr required     |
| Performance      | ACCEPTABLE           | Bound dedup sets       |
| API Design       | NEEDS_REFINEMENT     | @overload types        |
| DevOps           | **NEEDS_WORK**       | validate_env.py        |
| Testing          | NEEDS_TEST_STRATEGY  | Mock infra first       |
| Architecture     | ACCEPTABLE           | Circular import guards |
| Migration        | **RISKY**            | Breaking changes exist |
| Logging          | NEEDS_IMPROVEMENT    | Rich context format    |

### Current State Analysis

**ALREADY IMPLEMENTED** (functional):

- `proxy/` - Complete multi-provider system (5 providers, 8 tiers)
- `session/` - BrowserSession, HttpSession, ResilientBrowserSession (Patchright-based)
- `localdataclass/response.py` - Response dataclass
- `config.py` - Basic dotenv-based configuration (74 lines)

**CRITICAL GAPS** (from reviews):

1. **Security**: Credentials stored as plaintext strings (MUST fix)
2. **Migration**: Function exports (`_get_headers`, `REVERSE_NETWORKS_MAP`) not supported
3. **Migration**: Auto-directory creation at import time breaks
4. **Migration**: UUID generation timing (field defaults vs default_factory)
5. **Performance**: Unbounded `_seen_keys` sets will exhaust memory
6. **DevOps**: No `tools/validate_env.py` for production safety
7. **Architecture**: Dual dotenv loading (proxy/**init**.py + config.py)
8. **Logging**: Missing project_name, trace_id, timing in format

---

## Architecture Overview

### Target Structure (ENHANCED v2.0)

```
scraping/
├── tools/                       # NEW: Migration/validation tools
│   ├── validate_env.py          # Environment validation
│   ├── validate_migration.py    # Output comparison
│   ├── rollback_migration.py    # Safe rollback
│   └── find_hardcoded_credentials.py  # Security scan
│
└── shared_package/
    ├── pyproject.toml           # Flat layout package config
    ├── __init__.py              # Version, exports
    ├── config.py                # KEEP: Backward compat layer
    │
    ├── config/                  # NEW: Pydantic Settings
    │   ├── __init__.py          # Exports with @overload
    │   ├── base.py              # BaseConfig (TYPE_CHECKING guards)
    │   ├── proxy.py             # ProxySettings (SecretStr!)
    │   ├── registry.py          # ConfigRegistry pattern
    │   ├── sapphire.py          # @ConfigRegistry.register('sapphire')
    │   ├── healthsparq.py       # @ConfigRegistry.register('healthsparq')
    │   ├── carrier.py           # @ConfigRegistry.register('carrier')
    │   ├── anthem.py            # @ConfigRegistry.register('anthem')
    │   └── factory.py           # load_config() with @overload
    │
    ├── io/                      # NEW: File I/O
    │   ├── __init__.py
    │   ├── jsonl.py             # JSONLWriter (LRU-bounded dedup!)
    │   └── file_manager.py      # AtomicWriter
    │
    ├── logging/                 # NEW: Loguru setup
    │   ├── __init__.py
    │   ├── logger.py            # setup_logging(enqueue=True!)
    │   └── intercept.py         # InterceptHandler for stdlib
    │
    ├── validation/              # NEW: Schema + Response
    │   ├── __init__.py
    │   ├── schema.py            # Provider/Location models
    │   └── response.py          # Moved from localdataclass
    │
    ├── proxy/                   # EXISTING (minor update)
    │   └── __init__.py          # REMOVE dotenv loading
    │
    ├── session/                 # EXISTING (unchanged)
    ├── localdataclass/          # DEPRECATED (keep for compat)
    │
    └── tests/                   # NEW: Test infrastructure
        ├── conftest.py          # Mock fixtures (Patchright, curl_cffi)
        ├── test_config.py
        ├── test_session_concurrency.py  # NEW
        └── ...
```

---

## Phase Breakdown (Revised Order)

### Recommended Execution Order

Based on Architecture Reviewer's recommendation:

```
Week 1:
├── Phase 0: Migration Tooling (NEW - CRITICAL)
├── Phase 1: Package Infrastructure
└── Phase 2: Environment Setup

Week 2:
├── Phase 3: Configuration System
└── Phase 4: Backward Compatibility

Week 3:
├── Phase 5: File I/O Utilities
├── Phase 6: Logging System
└── Phase 7: Queue & Validation

Week 4:
└── Phase 8: Testing & Documentation
```

---

### Phase 0: Migration Tooling (Priority: P0) [NEW]

**Goal**: Create safety net before any code changes

**Rationale**: Migration Expert identified that "zero breaking changes" claim is FALSE. We need validation and rollback mechanisms BEFORE touching code.

**Tasks**:

1. Create `tools/validate_migration.py` - Output comparison tool
2. Create `tools/rollback_migration.py` - Safe revert mechanism
3. Create `tools/find_hardcoded_credentials.py` - Security scan
4. Pilot test on 3 diverse projects (Sapphire, Healthsparq, Carrier)

**Deliverables**:

```python
# tools/validate_migration.py
"""
Validates that scraper output is identical before/after migration.

Usage:
    python tools/validate_migration.py audiobee_bcbs_il --compare-outputs
    python tools/validate_migration.py --scan-all --report migration_report.json
"""
import argparse
import hashlib
import json
from pathlib import Path

def compare_outputs(project: str, date: str) -> dict:
    """Compare JSONL outputs byte-for-byte."""
    project_dir = Path(project)
    processed_dir = project_dir / date / "processed"

    results = {"project": project, "date": date, "files": {}}

    for jsonl_file in processed_dir.glob("*.jsonl"):
        content = jsonl_file.read_bytes()
        results["files"][jsonl_file.name] = {
            "size": len(content),
            "lines": content.count(b'\n'),
            "hash": hashlib.sha256(content).hexdigest()
        }

    return results

def validate_imports(project: str) -> list[str]:
    """Check that all existing imports still work."""
    errors = []
    project_dir = Path(project)

    for py_file in project_dir.glob("*.py"):
        if py_file.name.startswith("index_") or py_file.name == "config.py":
            # Try importing in subprocess to avoid side effects
            # ...
            pass

    return errors
```

```python
# tools/rollback_migration.py
"""
Safely rollback a migration using git.

Usage:
    python tools/rollback_migration.py audiobee_bcbs_il
    python tools/rollback_migration.py --all --dry-run
"""
import subprocess
from pathlib import Path

def rollback_project(project: str, dry_run: bool = False) -> bool:
    """Revert project files to pre-migration state."""
    files_to_revert = [
        f"{project}/config.py",
        f"{project}/index_1.py",
        f"{project}/index_2.py",
        f"{project}/index_3.py",
    ]

    for file_path in files_to_revert:
        if Path(file_path).exists():
            cmd = ["git", "checkout", "HEAD~1", "--", file_path]
            if dry_run:
                print(f"Would run: {' '.join(cmd)}")
            else:
                subprocess.run(cmd, check=True)

    return True
```

```python
# tools/find_hardcoded_credentials.py
"""
Scan all projects for hardcoded credentials.

Usage:
    python tools/find_hardcoded_credentials.py --scan-all
    python tools/find_hardcoded_credentials.py audiobee_*
"""
import re
from pathlib import Path

CREDENTIAL_PATTERNS = [
    r'password\s*[=:]\s*["\'][^"\']+["\']',
    r'api_key\s*[=:]\s*["\'][^"\']+["\']',
    r'username\s*[=:]\s*["\'][^"\']+["\']',
    r'secret\s*[=:]\s*["\'][^"\']+["\']',
    r'token\s*[=:]\s*["\'][^"\']+["\']',
]

def scan_file(file_path: Path) -> list[dict]:
    """Scan a file for hardcoded credentials."""
    findings = []
    content = file_path.read_text()

    for i, line in enumerate(content.splitlines(), 1):
        for pattern in CREDENTIAL_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                findings.append({
                    "file": str(file_path),
                    "line": i,
                    "pattern": pattern,
                    "content": line.strip()[:100]
                })

    return findings
```

**Verification**:

```bash
# Scan for hardcoded credentials
python tools/find_hardcoded_credentials.py --scan-all

# Validate a pilot project
python tools/validate_migration.py audiobee_bcbs_il --compare-outputs

# Test rollback (dry run)
python tools/rollback_migration.py audiobee_bcbs_il --dry-run
```

**Success Criteria**:

- [ ] `find_hardcoded_credentials.py` identifies all exposed credentials
- [ ] `validate_migration.py` can compare output hashes
- [ ] `rollback_migration.py` successfully reverts in dry-run mode
- [ ] 3 pilot projects validated before full rollout

---

### Phase 1: Package Infrastructure (Priority: P0)

**Goal**: Make existing package installable via pip/uv

**CHANGES FROM REVIEW**:

- Flat layout fix: `packages = ["shared_package"]` (not `["."]`)
- Pin pydantic-settings version: `>=2.0.0,<3.0.0`

**pyproject.toml** (REVISED):

```toml
[project]
name = "shared-package"
version = "0.1.0"
description = "Shared utilities for Ideon scraping projects"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.0.0,<3.0.0",
    "pydantic-settings>=2.0.0,<3.0.0",  # PINNED per Packaging review
    "python-dotenv>=1.0.0",
    "loguru>=0.7.0",
    "orjson>=3.9.0",
    "httpx>=0.27.0",
    "curl-cffi>=0.7.0",
    "patchright>=1.0.0",
    "tenacity>=8.0.0",
    "tqdm>=4.66.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.0.0",
    "pytest-timeout>=2.2.0",       # NEW: Timeout handling
    "pytest-mock>=3.12.0",         # NEW: Mocker fixture
    "respx>=0.20.0",               # NEW: httpx mocking
    "hypothesis>=6.0.0",           # NEW: Property testing
    "aiofiles>=23.0.0",            # NEW: Async file I/O
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["shared_package"]      # FIXED: Flat layout
only-include = ["shared_package"]

[tool.hatch.build.targets.sdist]
include = ["shared_package"]

[tool.pytest.ini_options]
asyncio_mode = "auto"              # NEW: Per Testing review
asyncio_default_fixture_loop_scope = "function"
testpaths = ["shared_package/tests"]
timeout = 30                       # NEW: Prevent hanging tests
```

**Verification**:

```bash
cd /Users/dikson/Work/ideon_scraping/scraping
uv pip install -e shared_package/
python -c "import shared_package; print(shared_package.__version__)"
python -c "from shared_package.session import BrowserSession"
python -c "from shared_package.proxy import ProxyManager"
```

---

### Phase 2: Environment Setup (Priority: P0)

**Goal**: Standardize environment configuration

**CHANGES FROM REVIEW**:

- Create `tools/validate_env.py` (CRITICAL - was missing)
- Document .env hierarchy loading order

**Deliverables**:

```
scraping/
├── .env.example             # Template with all variables
├── .gitignore               # MUST include .env patterns
└── tools/
    └── validate_env.py      # Environment validation
```

**tools/validate_env.py** (NEW):

```python
#!/usr/bin/env python3
"""
Validate environment configuration for scraper projects.

Usage:
    python tools/validate_env.py                    # Validate current directory
    python tools/validate_env.py audiobee_bcbs_il   # Validate specific project
    python tools/validate_env.py --all              # Validate all projects
"""
import os
import sys
from pathlib import Path
from typing import Optional

REQUIRED_VARS = {
    # Proxy credentials (at least one pair required)
    "NORD_USERNAME": "NordVPN proxy username",
    "NORD_PASSWORD": "NordVPN proxy password",
}

OPTIONAL_VARS = {
    "SURFSHARK_USERNAME": "Surfshark proxy username",
    "SURFSHARK_PASSWORD": "Surfshark proxy password",
    "SMARTPROXY_USERNAME": "SmartProxy username",
    "SMARTPROXY_PASSWORD": "SmartProxy password",
    "DATAIMPULSE_USERNAME": "DataImpulse username",
    "DATAIMPULSE_PASSWORD": "DataImpulse password",
}

def find_env_files(project_path: Path) -> list[Path]:
    """Find .env files in hierarchy (project -> parent -> root)."""
    env_files = []
    current = project_path.resolve()

    while current != current.parent:
        env_file = current / ".env"
        if env_file.exists():
            env_files.append(env_file)
        current = current.parent

    return env_files

def validate_project(project_path: Path) -> dict:
    """Validate environment for a project."""
    from dotenv import dotenv_values

    env_files = find_env_files(project_path)

    # Merge values (later files override earlier)
    merged_env = {}
    for env_file in reversed(env_files):
        merged_env.update(dotenv_values(env_file))

    # Also check actual environment
    for key in list(REQUIRED_VARS.keys()) + list(OPTIONAL_VARS.keys()):
        if key in os.environ and key not in merged_env:
            merged_env[key] = os.environ[key]

    result = {
        "project": str(project_path),
        "env_files_found": [str(f) for f in env_files],
        "missing_required": [],
        "missing_optional": [],
        "empty_values": [],
        "valid": True,
    }

    for var, desc in REQUIRED_VARS.items():
        value = merged_env.get(var, "")
        if not value:
            result["missing_required"].append(f"{var}: {desc}")
            result["valid"] = False
        elif value.strip() == "":
            result["empty_values"].append(var)
            result["valid"] = False

    for var, desc in OPTIONAL_VARS.items():
        if var not in merged_env:
            result["missing_optional"].append(f"{var}: {desc}")

    return result

if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Validate environment configuration")
    parser.add_argument("project", nargs="?", default=".", help="Project directory")
    parser.add_argument("--all", action="store_true", help="Validate all audiobee_* projects")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.all:
        projects = list(Path(".").glob("audiobee_*"))
    else:
        projects = [Path(args.project)]

    results = []
    for project in projects:
        if project.is_dir():
            result = validate_project(project)
            results.append(result)

            if not args.json:
                status = "OK" if result["valid"] else "FAIL"
                print(f"{project}: {status}")
                if result["missing_required"]:
                    for var in result["missing_required"]:
                        print(f"  MISSING: {var}")

    if args.json:
        print(json.dumps(results, indent=2))

    # Exit with error if any validation failed
    if not all(r["valid"] for r in results):
        sys.exit(1)
```

**.env hierarchy documentation** (add to ENV_MANAGEMENT_GUIDE.md):

```markdown
## .env Loading Order (Precedence)

When loading configuration, values are resolved in this order (highest priority first):

1. **Constructor arguments** - Passed directly to config class
2. **Environment variables** - `SCRAPER_*` prefixed variables
3. **Project .env** - `.env` in the project directory (e.g., `audiobee_bcbs_il/.env`)
4. **Parent .env files** - Walking up: `../.env`, `../../.env`, etc.
5. **Root .env** - `scraping/.env`
6. **Field defaults** - Defined in Pydantic Settings class

### Important Notes

- Later sources OVERRIDE earlier sources (project .env beats root .env)
- Empty string values are treated as "not set"
- CWD affects discovery - always run from project directory
```

---

### Phase 3: Configuration System (Priority: P0)

**Goal**: Implement Pydantic Settings with proper security and type safety

**CHANGES FROM REVIEW**:

1. **Security**: All credentials MUST use `SecretStr`
2. **API Design**: Use `@overload` for type-safe `load_config()`
3. **Architecture**: Use `TYPE_CHECKING` guards to prevent circular imports
4. **Architecture**: Registry pattern for self-registering configs
5. **Architecture**: Remove dotenv loading from `proxy/__init__.py`

**config/proxy.py** (SECURITY FIX):

```python
"""Proxy settings with secure credential handling."""
from pydantic import SecretStr
from pydantic_settings import BaseSettings

class ProxySettings(BaseSettings):
    """Proxy credentials - ALL use SecretStr for security."""

    # NordVPN
    nord_username: SecretStr = SecretStr("")
    nord_password: SecretStr = SecretStr("")

    # Surfshark
    surfshark_username: SecretStr = SecretStr("")
    surfshark_password: SecretStr = SecretStr("")

    # SmartProxy
    smartproxy_username: SecretStr = SecretStr("")
    smartproxy_password: SecretStr = SecretStr("")

    # DataImpulse
    dataimpulse_username: SecretStr = SecretStr("")
    dataimpulse_password: SecretStr = SecretStr("")

    # Decodo
    decodo_username: SecretStr = SecretStr("")
    decodo_password: SecretStr = SecretStr("")

    class Config:
        env_prefix = ""  # No prefix for backward compat

    def get_nord_auth(self) -> tuple[str, str]:
        """Get NordVPN credentials as plain strings (for internal use only)."""
        return (
            self.nord_username.get_secret_value(),
            self.nord_password.get_secret_value()
        )

    def __repr__(self) -> str:
        """Never expose credentials in repr."""
        return "ProxySettings(***)"

    def __str__(self) -> str:
        """Never expose credentials in str."""
        return "ProxySettings(credentials=hidden)"
```

**config/registry.py** (NEW - Architecture pattern):

```python
"""Registry pattern for config classes."""
from typing import Type, TypeVar

T = TypeVar('T', bound='BaseConfig')

class ConfigRegistry:
    """Self-registering config class registry."""

    _configs: dict[str, Type['BaseConfig']] = {}

    @classmethod
    def register(cls, site_type: str):
        """Decorator to register a config class for a site type."""
        def decorator(config_class: Type[T]) -> Type[T]:
            cls._configs[site_type] = config_class
            return config_class
        return decorator

    @classmethod
    def get(cls, site_type: str) -> Type['BaseConfig']:
        """Get config class for site type."""
        if site_type not in cls._configs:
            available = ', '.join(cls._configs.keys())
            raise ValueError(
                f"Unknown site type: '{site_type}'. "
                f"Available: {available}"
            )
        return cls._configs[site_type]

    @classmethod
    def list_types(cls) -> list[str]:
        """List all registered site types."""
        return list(cls._configs.keys())
```

**config/base.py** (with TYPE_CHECKING guards):

```python
"""Base configuration with Pydantic Settings."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional
from uuid import uuid4

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from .proxy import ProxySettings

class BaseConfig(BaseSettings):
    """Base configuration for all scraper projects."""

    model_config = SettingsConfigDict(
        env_prefix="SCRAPER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core identifiers
    project_name: str = Field(..., description="Project identifier")
    site_type: str = Field(..., description="Site type (sapphire, healthsparq, etc.)")

    # Dates
    curr_date: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y%m%d"),
        description="Current run date (YYYYMMDD)"
    )
    prev_date: str = Field(default="", description="Previous run date (YYYYMMDD)")

    # Transaction ID - use default_factory for unique per-instance!
    transaction_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique transaction ID"
    )

    # Directories (computed on init)
    _dirs: dict[str, Path] = {}

    @field_validator('curr_date', 'prev_date', mode='before')
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Validate date is YYYYMMDD format."""
        if not v:
            return v
        if len(v) != 8 or not v.isdigit():
            raise ValueError(f"Date must be YYYYMMDD format, got: {v}")
        return v

    def model_post_init(self, __context: Any) -> None:
        """Initialize computed properties after model creation."""
        # Auto-create directories at init time (preserves existing behavior!)
        self._dirs = self._compute_dirs()
        self._ensure_dirs()

    def _compute_dirs(self) -> dict[str, Path]:
        """Compute directory structure from curr_date."""
        base = Path(self.curr_date)
        return {
            "raw": base / "raw",
            "search_results": base / "raw" / "search_results",
            "provider_details": base / "raw" / "provider_details",
            "processed": base / "processed",
        }

    def _ensure_dirs(self) -> None:
        """Create directories if they don't exist."""
        for dir_path in self._dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)

    @property
    def dirs(self) -> dict[str, Path]:
        """Get directory structure."""
        return self._dirs
```

**config/factory.py** (with @overload for type safety):

```python
"""Factory function with proper type annotations."""
from typing import Literal, Optional, overload

from .base import BaseConfig
from .registry import ConfigRegistry
from .sapphire import SapphireConfig
from .healthsparq import HealthsparqConfig
from .carrier import CarrierConfig
from .anthem import AnthemConfig

# Type-safe overloads per API Design review
@overload
def load_config(
    site_type: Literal["sapphire"],
    project_name: str,
    **kwargs
) -> SapphireConfig: ...

@overload
def load_config(
    site_type: Literal["healthsparq"],
    project_name: str,
    **kwargs
) -> HealthsparqConfig: ...

@overload
def load_config(
    site_type: Literal["carrier"],
    project_name: str,
    **kwargs
) -> CarrierConfig: ...

@overload
def load_config(
    site_type: Literal["anthem"],
    project_name: str,
    **kwargs
) -> AnthemConfig: ...

@overload
def load_config(
    site_type: str,
    project_name: str,
    **kwargs
) -> BaseConfig: ...

def load_config(
    site_type: str,
    project_name: str,
    **kwargs
) -> BaseConfig:
    """
    Load configuration for a scraper project.

    Args:
        site_type: Type of site (sapphire, healthsparq, carrier, anthem)
        project_name: Project identifier (e.g., 'audiobee_bcbs_il')
        **kwargs: Additional config overrides

    Returns:
        Site-specific config instance

    Example:
        >>> config = load_config("sapphire", "audiobee_bcbs_il", network_id="210002020")
        >>> reveal_type(config)  # SapphireConfig
    """
    config_class = ConfigRegistry.get(site_type)
    return config_class(
        project_name=project_name,
        site_type=site_type,
        **kwargs
    )
```

**config/sapphire.py** (example with registry):

```python
"""Sapphire site type configuration."""
from typing import Optional

from pydantic import Field

from .base import BaseConfig
from .registry import ConfigRegistry

@ConfigRegistry.register("sapphire")
class SapphireConfig(BaseConfig):
    """Configuration for Sapphire (ProviderFinderOnline) sites."""

    network_id: str = Field(..., description="Network ID for API calls")
    api_key: Optional[str] = Field(default=None, description="API key if required")

    # Sapphire-specific settings
    max_results_per_page: int = Field(default=100, ge=1, le=500)
    search_radius_miles: int = Field(default=50, ge=1, le=100)
```

---

### Phase 4: Backward Compatibility (Priority: P0)

**Goal**: Ensure existing projects continue working - INCLUDING function exports

**CHANGES FROM REVIEW** (Migration Expert):

1. Support function exports (`_get_headers`, `REVERSE_NETWORKS_MAP`)
2. Preserve auto-directory creation at import time
3. Fix UUID generation timing (use `default_factory`)

**shared_package/config.py** (backward compat layer):

```python
"""
Backward compatibility layer for legacy config patterns.

This module maintains compatibility with existing projects that use:
    from config import PREV_DATE, CURR_DATE, DIRS, _get_headers

DO NOT MODIFY the exports without checking all 95+ projects!
"""
import os
import warnings
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv

# Load .env for backward compatibility
load_dotenv()

# ============================================================
# CREDENTIAL EXPORTS (Deprecated - use ProxySettings instead)
# ============================================================

def _get_env_str(key: str, default: str = "") -> str:
    """Get environment variable as string."""
    return os.getenv(key, default)

# These are deprecated but must remain for backward compat
NORD_USERNAME = _get_env_str("NORD_USERNAME")
NORD_PASSWORD = _get_env_str("NORD_PASSWORD")
SURFSHARK_USERNAME = _get_env_str("SURFSHARK_USERNAME")
SURFSHARK_PASSWORD = _get_env_str("SURFSHARK_PASSWORD")
SMARTPROXY_USERNAME = _get_env_str("SMARTPROXY_USERNAME")
SMARTPROXY_PASSWORD = _get_env_str("SMARTPROXY_PASSWORD")
DATAIMPULSE_USERNAME = _get_env_str("DATAIMPULSE_USERNAME")
DATAIMPULSE_PASSWORD = _get_env_str("DATAIMPULSE_PASSWORD")

# ============================================================
# FUNCTION EXPORTS (Critical - projects import these!)
# ============================================================

def get_default_proxy() -> dict:
    """Get default proxy configuration."""
    return {
        "server": f"http://{NORD_USERNAME}:{NORD_PASSWORD}@us.socks.nordhold.net:1080"
    }

# Projects may define these in their local config.py and import from here
# We provide a placeholder that can be overridden
_project_functions: dict[str, Callable] = {}

def register_function(name: str, func: Callable) -> None:
    """Register a project-specific function for export."""
    _project_functions[name] = func

def __getattr__(name: str) -> Any:
    """
    Dynamic attribute access for backward compatibility.

    This allows projects to do:
        from shared_package.config import _get_headers

    Even if _get_headers is defined in the project's config.py
    """
    if name in _project_functions:
        return _project_functions[name]
    raise AttributeError(f"module 'shared_package.config' has no attribute '{name}'")

# ============================================================
# NEW: Migration helper
# ============================================================

def create_compat_exports(project_config) -> dict[str, Any]:
    """
    Create backward-compatible exports from a new config object.

    Usage in project config.py:
        from shared_package.config import load_config, create_compat_exports

        config = load_config("sapphire", "audiobee_bcbs_il", network_id="210002020")

        # Create backward compat exports
        _exports = create_compat_exports(config)
        PREV_DATE = _exports["PREV_DATE"]
        CURR_DATE = _exports["CURR_DATE"]
        DIRS = _exports["DIRS"]
    """
    return {
        "PREV_DATE": project_config.prev_date,
        "CURR_DATE": project_config.curr_date,
        "PROJECT_NAME": project_config.project_name,
        "DIRS": {k: str(v) for k, v in project_config.dirs.items()},
    }
```

---

### Phase 5: File I/O Utilities (Priority: P1)

**Goal**: Thread-safe, memory-efficient file operations

**CHANGES FROM REVIEW** (Performance Engineer):

1. Use LRU-bounded or bloom filter for `_seen_keys`
2. Flush operations OUTSIDE the lock
3. Consider aiofiles for async I/O

**io/jsonl.py** (with bounded deduplication):

```python
"""JSONL read/write utilities with bounded memory usage."""
import os
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable, Iterator, Optional

import orjson

class BoundedSet:
    """LRU-bounded set for memory-safe deduplication."""

    def __init__(self, max_size: int = 1_000_000):
        self._data: OrderedDict[str, None] = OrderedDict()
        self._max_size = max_size

    def add(self, key: str) -> bool:
        """Add key, return True if new (not duplicate)."""
        if key in self._data:
            self._data.move_to_end(key)
            return False
        if len(self._data) >= self._max_size:
            self._data.popitem(last=False)  # Remove oldest
        self._data[key] = None
        return True

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __len__(self) -> int:
        return len(self._data)


class JSONLWriter:
    """
    Thread-safe JSONL writer with bounded deduplication.

    Performance optimizations (per Performance review):
    - LRU-bounded dedup set (prevents memory exhaustion)
    - Flush outside lock (allows concurrent writes to other files)
    - Batch orjson serialization
    """

    def __init__(
        self,
        base_dir: str | Path,
        buffer_size: int = 100,
        dedup_max_size: int = 1_000_000,
    ):
        self.base_dir = Path(base_dir)
        self.buffer_size = buffer_size
        self.dedup_max_size = dedup_max_size

        self._buffers: dict[str, list[dict]] = {}
        self._seen_keys: dict[str, BoundedSet] = {}
        self._lock = threading.Lock()

        self.base_dir.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        record: dict,
        filename: str,
        dedup_key: Optional[str] = None,
    ) -> bool:
        """
        Write record to JSONL file with optional deduplication.

        Returns True if written, False if duplicate.
        """
        flush_data: Optional[tuple[str, list[dict]]] = None

        with self._lock:
            # Deduplication check
            if dedup_key is not None:
                key_value = record.get(dedup_key)
                if key_value is not None:
                    if filename not in self._seen_keys:
                        self._seen_keys[filename] = BoundedSet(self.dedup_max_size)

                    if not self._seen_keys[filename].add(str(key_value)):
                        return False  # Duplicate

            # Buffer the record
            if filename not in self._buffers:
                self._buffers[filename] = []
            self._buffers[filename].append(record)

            # Check if flush needed
            if len(self._buffers[filename]) >= self.buffer_size:
                flush_data = (filename, self._buffers[filename])
                self._buffers[filename] = []

        # Flush OUTSIDE lock (allows concurrent writes to other files)
        if flush_data:
            self._do_flush(flush_data[0], flush_data[1])

        return True

    def _do_flush(self, filename: str, buffer: list[dict]) -> None:
        """Flush buffer to disk (called outside lock)."""
        if not buffer:
            return

        filepath = self.base_dir / filename

        # Batch serialize for efficiency
        data = b'\n'.join(orjson.dumps(record) for record in buffer) + b'\n'

        with open(filepath, 'ab') as f:
            f.write(data)

    def flush_all(self) -> None:
        """Flush all buffers to disk."""
        buffers_to_flush: list[tuple[str, list[dict]]] = []

        with self._lock:
            for filename, buffer in self._buffers.items():
                if buffer:
                    buffers_to_flush.append((filename, buffer))
            self._buffers.clear()

        for filename, buffer in buffers_to_flush:
            self._do_flush(filename, buffer)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.flush_all()


class JSONLReader:
    """Streaming JSONL reader."""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)

    def __iter__(self) -> Iterator[dict]:
        """Stream records without loading entire file."""
        with open(self.file_path, 'rb') as f:
            for line in f:
                line = line.strip()
                if line:
                    yield orjson.loads(line)

    def count(self) -> int:
        """Count records without loading all into memory."""
        return sum(1 for _ in self)
```

---

### Phase 6: Logging System (Priority: P1)

**Goal**: Structured logging with rich context

**CHANGES FROM REVIEW** (Logging Expert):

1. Use `enqueue=True` for async-safe file writes (CRITICAL)
2. Add `InterceptHandler` for stdlib logging compatibility
3. Include project_name, trace_id, timing in log format
4. Add run_id for cross-scraper correlation

**logging/logger.py** (REVISED):

```python
"""Structured logging with loguru."""
import logging
import os
import sys
from contextvars import ContextVar
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Optional
from uuid import uuid4

from loguru import logger as _logger

# Context variables for async-safe trace tracking
_trace_ctx: ContextVar[str] = ContextVar("trace_id", default="none")
_run_ctx: ContextVar[str] = ContextVar("run_id", default="standalone")

def get_trace_id() -> str:
    """Get current trace ID."""
    return _trace_ctx.get()

def get_run_id() -> str:
    """Get current run ID (for cross-scraper correlation)."""
    return _run_ctx.get()

def set_run_id(run_id: str) -> None:
    """Set run ID (called by run_parallel.py)."""
    _run_ctx.set(run_id)

def with_trace(func):
    """Decorator to add trace ID to async function."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        trace_id = uuid4().hex[:8]
        token = _trace_ctx.set(trace_id)
        try:
            return await func(*args, **kwargs)
        finally:
            _trace_ctx.reset(token)
    return wrapper


class InterceptHandler(logging.Handler):
    """
    Intercept stdlib logging and redirect to loguru.

    This captures logs from third-party libraries (httpx, curl_cffi, etc.)
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = _logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        _logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging(
    project_name: str,
    phase: str = "main",
    log_dir: Optional[str | Path] = None,
    level: str = "INFO",
    rotation: str = "00:00",  # Daily at midnight
    retention: str = "14 days",
) -> None:
    """
    Configure logging for a scraper project.

    Args:
        project_name: Project identifier (e.g., 'audiobee_bcbs_il')
        phase: Current phase (search, details, map)
        log_dir: Directory for log files (default: logs/)
        level: Minimum log level
        rotation: When to rotate files
        retention: How long to keep old files
    """
    # Remove default handler
    _logger.remove()

    # Get run_id from environment (set by run_parallel.py)
    run_id = os.getenv("SCRAPER_RUN_ID", "standalone")
    set_run_id(run_id)

    # Rich console format with all context
    console_format = (
        "<green>{time:HH:mm:ss.SSS}</green> | "
        "<level>{level: <5}</level> | "
        "<cyan>{extra[project]: <15}</cyan> | "
        "<yellow>{extra[phase]: <8}</yellow> | "
        "<magenta>{extra[trace_id]: <8}</magenta> | "
        "{message}"
    )

    # Add console handler
    _logger.add(
        sys.stderr,
        format=console_format,
        level=level,
        colorize=True,
    )

    # File logging with enqueue=True (CRITICAL for async safety!)
    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # Main log file (daily rotation)
        _logger.add(
            log_path / f"{project_name}_{{time:YYYYMMDD}}.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <5} | {extra[project]} | {extra[phase]} | {extra[trace_id]} | {extra[run_id]} | {message}",
            level=level,
            rotation=rotation,
            retention=retention,
            compression="gz",
            enqueue=True,  # CRITICAL: Async-safe writes
        )

        # Error-only log (size-based rotation)
        _logger.add(
            log_path / f"{project_name}_errors.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {extra[project]} | {message}\n{exception}",
            level="ERROR",
            rotation="50MB",
            retention="30 days",
            enqueue=True,
        )

        # Optional: JSON log for machine parsing
        _logger.add(
            log_path / f"{project_name}_{{time:YYYYMMDD}}.jsonl",
            format="{message}",
            level=level,
            rotation=rotation,
            retention="7 days",
            serialize=True,
            enqueue=True,
        )

    # Configure to use our context
    _logger.configure(
        extra={
            "project": project_name,
            "phase": phase,
            "trace_id": "init",
            "run_id": run_id,
        }
    )

    # Intercept stdlib logging (for third-party libs)
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Specifically capture these noisy loggers
    for logger_name in ["httpx", "httpcore", "urllib3", "asyncio"]:
        logging.getLogger(logger_name).handlers = [InterceptHandler()]


def get_logger(phase: str):
    """
    Get a phase-bound logger.

    Args:
        phase: Current phase (search, details, map)

    Returns:
        Logger bound to the phase with trace context
    """
    return _logger.bind(
        phase=phase,
        trace_id=get_trace_id(),
        run_id=get_run_id(),
    )
```

---

### Phase 7: Queue & Validation (Priority: P2)

**Goal**: Task queue and schema validation

**Tasks**:

1. Create asyncio.Queue-based task manager
2. Move `localdataclass/response.py` to `validation/response.py`
3. Create Pydantic models for provider data

---

### Phase 8: Testing & Documentation (Priority: P1)

**Goal**: Mock infrastructure BEFORE coverage targets

**CHANGES FROM REVIEW** (Testing Specialist):

1. Create `tests/conftest.py` with mock fixtures FIRST
2. Add concurrency tests for session semaphores/locks
3. Configure pytest-asyncio properly
4. Separate unit/integration/live test suites

**tests/conftest.py** (NEW - per Testing review):

```python
"""
Test fixtures and configuration.

IMPORTANT: This file must be created BEFORE setting coverage targets!
Mock infrastructure is required for realistic testing.
"""
import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ============================================================
# pytest-asyncio configuration
# ============================================================

@pytest.fixture(scope="session")
def event_loop_policy():
    """Use default event loop policy."""
    return asyncio.DefaultEventLoopPolicy()


# ============================================================
# Mock fixtures for external dependencies
# ============================================================

@pytest.fixture
def mock_playwright():
    """Mock Patchright/Playwright for browser tests."""
    mock = AsyncMock()
    mock.chromium.launch.return_value = AsyncMock()
    mock.chromium.launch.return_value.new_context.return_value = AsyncMock()
    mock.chromium.launch.return_value.new_context.return_value.new_page.return_value = AsyncMock()
    return mock


@pytest.fixture
def mock_curl_session():
    """Mock curl_cffi AsyncSession for HTTP tests."""
    mock = AsyncMock()
    mock.get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"data": "test"},
        text="test response",
    )
    return mock


@pytest.fixture
def mock_proxy_config():
    """Reusable ProxyConfig fixture."""
    from shared_package.proxy.base import ProxyConfig
    return ProxyConfig(
        host="test.proxy.com",
        port=8080,
        username="test",
        password="test123",
    )


# ============================================================
# Environment fixtures
# ============================================================

@pytest.fixture
def temp_env(tmp_path, monkeypatch):
    """Set up temporary .env files for testing."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SCRAPER_CURR_DATE=20251226\n"
        "SCRAPER_PREV_DATE=20251126\n"
        "NORD_USERNAME=test_user\n"
        "NORD_PASSWORD=test_pass\n"
    )
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def temp_env_hierarchy(tmp_path, monkeypatch):
    """Create hierarchical .env files for testing precedence."""
    # Root .env
    root_env = tmp_path / ".env"
    root_env.write_text("SCRAPER_CURR_DATE=20251201\n")

    # Project .env (overrides root)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    project_env = project_dir / ".env"
    project_env.write_text("SCRAPER_CURR_DATE=20251226\n")

    monkeypatch.chdir(project_dir)
    return project_dir


# ============================================================
# Concurrency test helpers
# ============================================================

@pytest.fixture
def concurrency_tracker():
    """Track concurrent operations for testing semaphores/locks."""
    class Tracker:
        def __init__(self):
            self.max_concurrent = 0
            self.current_concurrent = 0
            self._lock = asyncio.Lock()

        async def enter(self):
            async with self._lock:
                self.current_concurrent += 1
                self.max_concurrent = max(self.max_concurrent, self.current_concurrent)

        async def exit(self):
            async with self._lock:
                self.current_concurrent -= 1

    return Tracker()


# ============================================================
# Test markers
# ============================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "live: marks tests that use real proxies")
    config.addinivalue_line("markers", "slow: marks tests that are slow")
    config.addinivalue_line("markers", "integration: marks integration tests")
```

**tests/test_session_concurrency.py** (NEW - per Testing review):

```python
"""Concurrency tests for session modules."""
import asyncio

import pytest

from shared_package.session.browser_session import BrowserSession


@pytest.mark.asyncio
async def test_concurrent_requests_respect_semaphore(
    mock_playwright,
    concurrency_tracker,
):
    """Verify max_concurrent_requests is enforced."""
    max_concurrent = 3
    total_requests = 10

    # Patch BrowserSession to use our tracker
    # ...

    # Run concurrent requests
    async def make_request(session, i):
        await concurrency_tracker.enter()
        await asyncio.sleep(0.1)  # Simulate work
        await concurrency_tracker.exit()

    # Assert max concurrent never exceeded
    assert concurrency_tracker.max_concurrent <= max_concurrent


@pytest.mark.asyncio
async def test_close_waits_for_active_operations(mock_playwright):
    """Verify close() blocks until in-flight requests complete."""
    # Test that closing a session waits for active requests
    pass


@pytest.mark.asyncio
async def test_recreation_is_single_flight(mock_playwright):
    """Verify only one recreation happens when multiple fail simultaneously."""
    # Test that ResilientBrowserSession only recreates once
    pass
```

---

## Implementation Order (REVISED)

```
Week 1:
├── Phase 0: Migration Tooling (NEW - CRITICAL FIRST)
│   ├── tools/validate_migration.py
│   ├── tools/rollback_migration.py
│   └── tools/find_hardcoded_credentials.py
├── Phase 1: Package Infrastructure
│   └── pyproject.toml (flat layout fix)
└── Phase 2: Environment Setup
    └── tools/validate_env.py (CRITICAL)

Week 2:
├── Phase 3: Configuration System
│   ├── SecretStr for all credentials
│   ├── Registry pattern
│   ├── @overload for load_config()
│   └── TYPE_CHECKING guards
└── Phase 4: Backward Compatibility
    ├── Function exports support
    ├── Auto-directory creation
    └── UUID default_factory fix

Week 3:
├── Phase 5: File I/O Utilities
│   ├── LRU-bounded deduplication
│   └── Flush outside lock
├── Phase 6: Logging System
│   ├── enqueue=True (async-safe)
│   ├── InterceptHandler (stdlib compat)
│   └── Rich context format
└── Phase 7: Queue & Validation

Week 4:
└── Phase 8: Testing & Documentation
    ├── conftest.py with mock fixtures FIRST
    ├── Concurrency tests
    └── Coverage targets (realistic with mocks)
```

---

## Risk Mitigation (REVISED)

| Risk                       | Impact       | Mitigation                                | Status |
| -------------------------- | ------------ | ----------------------------------------- | ------ |
| Breaking existing projects | **CRITICAL** | Phase 0 tooling + pilot migration         | NEW    |
| Function exports missing   | **CRITICAL** | Dynamic `__getattr__` in config.py        | NEW    |
| Directory auto-creation    | **HIGH**     | `model_post_init()` pattern               | NEW    |
| Credential exposure        | **HIGH**     | SecretStr + find_hardcoded_credentials.py | NEW    |
| Memory exhaustion          | **HIGH**     | LRU-bounded dedup sets                    | NEW    |
| Test coverage unrealistic  | **MEDIUM**   | Mock infrastructure first                 | NEW    |
| Circular imports           | **MEDIUM**   | TYPE_CHECKING guards                      | NEW    |
| Async log blocking         | **MEDIUM**   | enqueue=True                              | NEW    |

---

## Open Questions (RESOLVED)

1. **Python 3.10 or 3.11+?** → **3.11+** (Performance improvements, TaskGroups)
2. **Proxy credentials required or optional?** → **Optional with validation warnings**
3. **Add aiofiles?** → **Yes, add to dev dependencies, consider for P2**
4. **Include rate limiter?** → **Yes, in queue/ module (P2)**
5. **Handle version conflicts?** → **Pin pydantic-settings>=2.0.0,<3.0.0**

---

## Success Metrics (UPDATED)

1. **Phase 0 Completion**: 3 pilot projects migrated with validated outputs
2. **Zero Credential Exposure**: find_hardcoded_credentials.py passes
3. **Import Success**: All 95+ projects import without errors
4. **Test Coverage**: >80% for config/ (with mock infrastructure)
5. **Memory Bounded**: JSONLWriter handles 10M+ records without exhaustion
6. **Async Safe**: No logging I/O blocking in concurrent scrapers

---

## Related Documents

- [RESTRUCTURING_PLAN.md](./RESTRUCTURING_PLAN.md) - Overall restructuring vision
- [SHARED_PACKAGE_SPEC.md](./SHARED_PACKAGE_SPEC.md) - Technical specification
- [ENV_MANAGEMENT_GUIDE.md](./ENV_MANAGEMENT_GUIDE.md) - Environment best practices
- [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) - Step-by-step migration
- [SHARED_PACKAGE_PROGRESS.json](./SHARED_PACKAGE_PROGRESS.json) - Progress tracker with action items

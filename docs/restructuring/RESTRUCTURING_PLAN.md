# Scraping Infrastructure Restructuring Plan

**Status**: Draft
**Created**: 2025-12-26
**Scope**: 95+ scraper projects

---

## Executive Summary

Restructure the Ideon Scraping monorepo from flat project directories to a standardized architecture with:

1. **Centralized shared_package** - Installable Python package for common utilities
2. **Standardized project structure** - Consistent layout across all 95+ scrapers
3. **Improved environment management** - Pydantic Settings replacing raw dotenv
4. **Better separation of concerns** - scraper/, service/, infrastructure/ layers

---

## Current State Analysis

### Existing shared_package Implementations

| Location                                         | Features                        | Issues                          |
| ------------------------------------------------ | ------------------------------- | ------------------------------- |
| `audiobee_uhc_behavioral_health/shared_package/` | Sessions, Response dataclass    | Local copy, .env in package dir |
| `audiobee_bluecard_national/shared_package/`     | Full proxy management, sessions | Most complete, but still local  |

### Current .env Dependency Problems

```python
# audiobee_bluecard_national/shared_package/config.py (CURRENT)
import dotenv
dotenv.load_dotenv()  # Loads from CWD - non-deterministic!

NORD_USERNAME = os.getenv("NORD_USERNAME", "")  # No validation
NORD_PASSWORD = os.getenv("NORD_PASSWORD", "")  # Empty default = silent failure
```

**Issues:**

1. `.env` location depends on CWD (non-deterministic)
2. No validation - empty strings cause runtime errors later
3. No type coercion - manual `int()` calls
4. No hierarchy - can't have base + project-specific overrides
5. Module-level loading - can't reload or override programmatically

---

## Proposed Architecture

### Directory Structure

```
scraping/
├── pyproject.toml                    # UV workspace root
├── uv.lock                           # Single lockfile
├── .env.example                      # Template for all projects
├── .env                              # Root-level shared secrets (gitignored)
│
├── shared_package/                   # Installable shared utilities
│   ├── pyproject.toml
│   └── src/
│       └── shared_package/
│           ├── __init__.py
│           ├── config/               # Pydantic Settings configs
│           │   ├── __init__.py
│           │   ├── base.py           # BaseConfig class
│           │   ├── proxy.py          # ProxyConfig with validation
│           │   ├── sapphire.py       # SapphireConfig
│           │   ├── healthsparq.py    # HealthsparqConfig
│           │   ├── carrier.py        # CarrierConfig
│           │   ├── anthem.py         # AnthemConfig
│           │   └── factory.py        # load_config()
│           ├── session/              # Browser/HTTP sessions
│           │   ├── __init__.py
│           │   ├── browser_session.py
│           │   ├── http_session.py
│           │   └── resilient_session.py
│           ├── proxy/                # Proxy management
│           │   ├── __init__.py
│           │   ├── base.py           # ProxyType, ProxyConfig
│           │   ├── manager.py        # ProxyManager
│           │   └── providers/        # Provider implementations
│           ├── io/                   # File utilities
│           │   ├── __init__.py
│           │   ├── jsonl.py          # JSONLReader, JSONLWriter
│           │   └── file_manager.py   # AtomicWriter
│           ├── logging/              # Centralized logging
│           │   ├── __init__.py
│           │   └── logger.py         # Loguru configuration
│           └── validation/           # Schema validation
│               ├── __init__.py
│               └── schema.py         # Pydantic models
│
├── audiobee_<project_name>/          # Individual scraper projects
│   ├── pyproject.toml                # References shared_package
│   ├── config.py                     # Inherits from BaseConfig
│   ├── .env                          # Project-specific overrides (optional)
│   ├── 20*/                          # Date-versioned data
│   │   ├── raw/
│   │   └── processed/
│   ├── logs/                         # Project logs
│   ├── scraper/                      # Actual scrape code
│   │   ├── __init__.py
│   │   ├── main.py                   # Entry point
│   │   ├── service/                  # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── search.py             # Search/discovery service
│   │   │   ├── details.py            # Detail fetching service
│   │   │   └── normalize.py          # Normalization service
│   │   ├── infrastructure/           # Project-specific infra
│   │   │   ├── __init__.py
│   │   │   └── api_client.py         # Project-specific API client
│   │   └── pipeline/                 # Phase execution pipeline
│   │       ├── __init__.py
│   │       ├── orchestrator.py       # Pipeline runner
│   │       └── task_queue.py         # asyncio.Queue implementation
│   ├── run_all.py                    # CLI orchestrator (Typer)
│   └── mapper.py                     # Data normalization
│
├── tools/                            # Execution tools (run_parallel.py)
├── output_generator/                 # Existing QA utilities
└── docs/                             # Documentation
```

---

## Environment Management Solution

### Problem: Current .env Loading

```python
# CURRENT: Non-deterministic, no validation
dotenv.load_dotenv()  # Where does it load from?
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD", "")  # Empty = silent failure
```

### Solution: Pydantic Settings with Hierarchy

```python
# shared_package/src/shared_package/config/base.py
from pathlib import Path
from typing import List, Optional
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    """
    Base configuration with environment variable loading.

    Loading priority (highest to lowest):
    1. Explicit constructor arguments
    2. Environment variables (SCRAPER_* prefix)
    3. Project-specific .env file
    4. Root-level .env file
    5. Defaults
    """

    model_config = SettingsConfigDict(
        # Load from multiple .env files (later overrides earlier)
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        env_prefix="SCRAPER_",
        case_sensitive=False,
        extra="ignore",
    )

    # Project identification
    project_name: str = Field(description="Project identifier")

    # Date management (REQUIRED - no defaults)
    prev_date: str = Field(description="Previous run date (YYYYMMDD)")
    curr_date: str = Field(description="Current run date (YYYYMMDD)")

    # Logging
    log_level: str = Field(default="INFO")
    log_to_file: bool = Field(default=True)

    @field_validator("prev_date", "curr_date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        if len(v) != 8 or not v.isdigit():
            raise ValueError(f"Date must be YYYYMMDD format, got: {v}")
        return v

    @property
    def dirs(self) -> dict[str, Path]:
        """Computed directory structure from curr_date."""
        base = Path(self.curr_date)
        return {
            "raw": base / "raw",
            "search_results": base / "raw" / "search_results",
            "provider_details": base / "raw" / "provider_details",
            "processed": base / "processed",
            "logs": Path("logs"),
        }

    def ensure_dirs(self) -> None:
        """Create all required directories."""
        for dir_path in self.dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)


class ProxyConfig(BaseSettings):
    """
    Proxy configuration with validation.

    Environment variables:
    - PROXY_NORD_USERNAME, PROXY_NORD_PASSWORD
    - PROXY_SURFSHARK_USERNAME, PROXY_SURFSHARK_PASSWORD
    - PROXY_DATAIMPULSE_*, PROXY_SMARTPROXY_*
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_prefix="PROXY_",
        extra="ignore",
    )

    # VPN credentials (SecretStr hides in logs)
    nord_username: SecretStr = Field(default=SecretStr(""))
    nord_password: SecretStr = Field(default=SecretStr(""))
    surfshark_username: SecretStr = Field(default=SecretStr(""))
    surfshark_password: SecretStr = Field(default=SecretStr(""))

    # DataImpulse
    dataimpulse_server: str = Field(default="http://gw.dataimpulse.com:823")
    dataimpulse_username: SecretStr = Field(default=SecretStr(""))
    dataimpulse_password: SecretStr = Field(default=SecretStr(""))

    # SmartProxy
    smartproxy_host: str = Field(default="us.smartproxy.net")
    smartproxy_port: int = Field(default=3120)
    smartproxy_username: SecretStr = Field(default=SecretStr(""))
    smartproxy_password: SecretStr = Field(default=SecretStr(""))

    def has_nord(self) -> bool:
        return bool(self.nord_username.get_secret_value())

    def has_dataimpulse(self) -> bool:
        return bool(self.dataimpulse_username.get_secret_value())
```

### Environment File Structure

```bash
# scraping/.env (root level - shared secrets)
# This file contains credentials used by ALL projects
# NEVER commit this file!

# =============================================================================
# PROXY CREDENTIALS (Required for browser scrapers)
# =============================================================================
PROXY_NORD_USERNAME=your_nord_username
PROXY_NORD_PASSWORD=your_nord_password
PROXY_SURFSHARK_USERNAME=your_surfshark_username
PROXY_SURFSHARK_PASSWORD=your_surfshark_password

# DataImpulse Residential Proxy
PROXY_DATAIMPULSE_USERNAME=your_dataimpulse_id
PROXY_DATAIMPULSE_PASSWORD=your_dataimpulse_password

# SmartProxy
PROXY_SMARTPROXY_USERNAME=your_smartproxy_user
PROXY_SMARTPROXY_PASSWORD=your_smartproxy_pass

# =============================================================================
# API KEYS (Per-carrier, add as needed)
# =============================================================================
SAPPHIRE_API_KEY=default_sapphire_key
```

```bash
# audiobee_bcbs_il/.env (project-level overrides)
# Only include values that DIFFER from root .env

SCRAPER_PROJECT_NAME=audiobee_bcbs_il
SCRAPER_PREV_DATE=20251110
SCRAPER_CURR_DATE=20251210

# Project-specific API key (overrides root)
SAPPHIRE_API_KEY=bcbs_il_specific_key
```

### Enforcing Same .env Structure

**Option 1: Schema Validation Script**

```python
# tools/validate_env.py
"""Validate .env files across all projects."""

from pathlib import Path
from pydantic import ValidationError
from shared_package.config import BaseConfig, ProxyConfig

REQUIRED_VARS = [
    "SCRAPER_PREV_DATE",
    "SCRAPER_CURR_DATE",
]

def validate_project_env(project_dir: Path) -> list[str]:
    """Validate a project's .env file."""
    errors = []
    env_file = project_dir / ".env"

    if not env_file.exists():
        # Check if root .env exists (acceptable)
        if not (project_dir.parent / ".env").exists():
            errors.append(f"No .env file found for {project_dir.name}")
        return errors

    # Try to load config
    try:
        config = BaseConfig(project_name=project_dir.name)
    except ValidationError as e:
        errors.append(f"{project_dir.name}: {e}")

    return errors

if __name__ == "__main__":
    for project in Path(".").glob("audiobee_*/"):
        errors = validate_project_env(project)
        if errors:
            print(f"❌ {project.name}: {errors}")
        else:
            print(f"✅ {project.name}")
```

**Option 2: Pre-commit Hook**

```yaml
# .pre-commit-config.yaml
repos:
    - repo: local
      hooks:
          - id: validate-env
            name: Validate .env files
            entry: python tools/validate_env.py
            language: python
            pass_filenames: false
```

**Option 3: Symlink Root .env (Recommended for Shared Secrets)**

```bash
# One-time setup: symlink root .env to all projects
for dir in audiobee_*/; do
  ln -sf ../.env "$dir/.env"
done
```

---

## Implementation Phases

### Phase 1: Create shared_package (Week 1)

1. Create `shared_package/` at repo root with src layout
2. Migrate `audiobee_bluecard_national/shared_package/` as base
3. Implement Pydantic Settings config system
4. Add pyproject.toml with UV workspace support
5. Test with 3 pilot projects (one per site type)

### Phase 2: Standardize Config Loading (Week 2)

1. Create `.env.example` template at root
2. Migrate hardcoded API keys to environment variables
3. Update config.py files to use `load_config()` factory
4. Maintain backward compatibility exports

### Phase 3: Restructure Project Directories (Week 3-4)

1. Create `scraper/` subdirectory structure for new projects
2. Add `run_all.py` with Typer CLI
3. Implement logging with loguru
4. Create migration script for existing projects (optional)

### Phase 4: Add Pipeline/Queue System (Week 5)

1. Implement `asyncio.Queue` based task manager
2. Add progress tracking and resumability
3. Integrate with run_all.py CLI

---

## Backward Compatibility

All changes maintain backward compatibility:

```python
# Old code continues to work:
from config import PREV_DATE, CURR_DATE, DIRS

# New code can use:
from shared_package.config import load_config
config = load_config("sapphire", "audiobee_bcbs_il")
```

**Migration is optional** - legacy config.py files continue working.

---

## Related Documents

- [SHARED_PACKAGE_SPEC.md](./SHARED_PACKAGE_SPEC.md) - Detailed shared_package architecture
- [ENV_MANAGEMENT_GUIDE.md](./ENV_MANAGEMENT_GUIDE.md) - Environment variable best practices
- [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) - Step-by-step project migration
- [implementation_research/](../implementation_research/) - Original research documents

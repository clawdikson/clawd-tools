# Environment Variable Management Guide

**Purpose**: Standardize environment configuration across 95+ scraper projects
**Problem Solved**: Non-deterministic .env loading, hardcoded secrets, no validation

---

## Current Problems

### 1. Non-Deterministic .env Location

```python
# CURRENT (audiobee_bluecard_national/shared_package/config.py)
import dotenv
dotenv.load_dotenv()  # Loads from CWD - WHERE?

# If run from different directories:
# cd scraping && python audiobee_bcbs_il/index_1.py  → loads scraping/.env
# cd audiobee_bcbs_il && python index_1.py          → loads audiobee_bcbs_il/.env
```

### 2. Silent Failures

```python
# Empty defaults cause runtime errors later
NORD_USERNAME = os.getenv("NORD_USERNAME", "")  # Empty string if not set
NORD_PASSWORD = os.getenv("NORD_PASSWORD", "")

# Later in code... boom!
proxy_url = f"http://{NORD_USERNAME}:{NORD_PASSWORD}@..."  # Invalid URL
```

### 3. Hardcoded Secrets

```python
# Found in 15+ config.py files
HEADERS = {
    "x-api-key": "03220e47-16eb-44d3-b1ca-4e3641973a97",  # EXPOSED IN CODE!
}
```

---

## Solution: Pydantic Settings with Hierarchy

### Loading Priority

Pydantic Settings loads values in this order (highest priority first):

1. **Constructor arguments** - Explicit values in code
2. **Environment variables** - `SCRAPER_CURR_DATE=20251210`
3. **Project .env file** - `audiobee_bcbs_il/.env`
4. **Parent .env files** - `../.env`, `../../.env`
5. **Field defaults** - In class definition

### File Structure

```
scraping/
├── .env                          # Root: Shared secrets (REQUIRED)
├── .env.example                  # Template (committed to git)
├── .gitignore                    # Contains: .env
│
├── audiobee_bcbs_il/
│   └── .env                      # Project: Date overrides (OPTIONAL)
│
├── audiobee_anthem/
│   └── .env                      # Project: Date overrides (OPTIONAL)
│
└── shared_package/
    └── config/
        └── base.py               # Loads from all .env files
```

---

## .env File Templates

### Root .env (scraping/.env)

```bash
# =============================================================================
# SCRAPING INFRASTRUCTURE - ROOT ENVIRONMENT
# =============================================================================
# This file contains SHARED SECRETS used by ALL projects.
# NEVER commit this file to git!
#
# Copy from .env.example and fill in your credentials.
# =============================================================================

# =============================================================================
# DEFAULT DATES (Override per-project in project/.env)
# =============================================================================
SCRAPER_PREV_DATE=20251110
SCRAPER_CURR_DATE=20251210

# =============================================================================
# PROXY CREDENTIALS - REQUIRED FOR BROWSER SCRAPERS
# =============================================================================

# NordVPN (Tier 4)
PROXY_NORD_USERNAME=your_nord_username
PROXY_NORD_PASSWORD=your_nord_password

# Surfshark (Tier 3)
PROXY_SURFSHARK_USERNAME=your_surfshark_username
PROXY_SURFSHARK_PASSWORD=your_surfshark_password

# DataImpulse Residential (Tier 5-6)
PROXY_DATAIMPULSE_SERVER=http://gw.dataimpulse.com:823
PROXY_DATAIMPULSE_USERNAME=your_dataimpulse_id__cr.us
PROXY_DATAIMPULSE_PASSWORD=your_dataimpulse_password

# SmartProxy/Decodo Residential (Tier 7-8)
PROXY_SMARTPROXY_HOST=us.smartproxy.net
PROXY_SMARTPROXY_PORT=3120
PROXY_SMARTPROXY_USERNAME=your_smartproxy_user
PROXY_SMARTPROXY_PASSWORD=your_smartproxy_pass

# Decodo Datacenter Static (Tier 2)
PROXY_DECODO_DC_HOST=dc.smartproxy.com
PROXY_DECODO_DC_USERNAME=your_decodo_dc_user
PROXY_DECODO_DC_PASSWORD=your_decodo_dc_pass

# =============================================================================
# API KEYS - PER CARRIER (Add as needed)
# =============================================================================

# Sapphire/ProviderFinderOnline (Multiple carriers)
SAPPHIRE_API_KEY=default_sapphire_key

# Multiplan
MULTIPLAN_SUBSCRIPTION_KEY=your_multiplan_key

# =============================================================================
# LOGGING & DEBUG
# =============================================================================
SCRAPER_LOG_LEVEL=INFO
SCRAPER_LOG_TO_FILE=true
SCRAPER_DEBUG=false

# =============================================================================
# RATE LIMITING
# =============================================================================
SCRAPER_BATCH_SIZE=100
SCRAPER_MAX_CONCURRENT=10
SCRAPER_REQUEST_DELAY_MIN=0.5
SCRAPER_REQUEST_DELAY_MAX=2.0
```

### Project .env (audiobee_bcbs_il/.env)

```bash
# =============================================================================
# AUDIOBEE_BCBS_IL - PROJECT ENVIRONMENT
# =============================================================================
# Only include values that DIFFER from root .env
# Inherits all values from ../.env automatically
# =============================================================================

# Project identification
SCRAPER_PROJECT_NAME=audiobee_bcbs_il

# Date overrides for this run
SCRAPER_PREV_DATE=20251125
SCRAPER_CURR_DATE=20251226

# Project-specific API key (overrides root)
SAPPHIRE_API_KEY=bcbs_il_specific_api_key

# Project-specific settings
SCRAPER_REQ_STATES=IL,IN,WI
```

### .env.example (committed to git)

```bash
# =============================================================================
# SCRAPING INFRASTRUCTURE - ENVIRONMENT TEMPLATE
# =============================================================================
# Copy this file to .env and fill in your credentials:
#   cp .env.example .env
#
# DO NOT commit .env to git!
# =============================================================================

# Dates
SCRAPER_PREV_DATE=YYYYMMDD
SCRAPER_CURR_DATE=YYYYMMDD

# Proxy credentials (get from team lead)
PROXY_NORD_USERNAME=
PROXY_NORD_PASSWORD=
PROXY_SURFSHARK_USERNAME=
PROXY_SURFSHARK_PASSWORD=
PROXY_DATAIMPULSE_USERNAME=
PROXY_DATAIMPULSE_PASSWORD=
PROXY_SMARTPROXY_USERNAME=
PROXY_SMARTPROXY_PASSWORD=

# API keys (get from team lead)
SAPPHIRE_API_KEY=
MULTIPLAN_SUBSCRIPTION_KEY=

# Settings
SCRAPER_LOG_LEVEL=INFO
SCRAPER_DEBUG=false
```

---

## Enforcing Consistency

### Option 1: Validation Script

Create `tools/validate_env.py`:

```python
#!/usr/bin/env python3
"""Validate .env files across all projects."""

import os
import sys
from pathlib import Path

# Add shared_package to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared_package.config import BaseConfig
from shared_package.config.proxy import ProxySettings
from pydantic import ValidationError


def validate_root_env() -> list[str]:
    """Validate root .env has required proxy credentials."""
    errors = []
    root_env = Path(".env")

    if not root_env.exists():
        return ["Root .env file not found! Copy from .env.example"]

    try:
        proxy = ProxySettings()
        available = proxy.get_available_types()
        if not available:
            errors.append("No proxy credentials configured in root .env")
    except ValidationError as e:
        errors.append(f"Proxy config error: {e}")

    return errors


def validate_project(project_dir: Path) -> list[str]:
    """Validate a single project's configuration."""
    errors = []

    # Check if config.py exists
    config_py = project_dir / "config.py"
    if not config_py.exists():
        return []  # Not a scraper project

    # Try to load configuration
    project_name = project_dir.name

    # Change to project directory to test .env loading
    original_cwd = os.getcwd()
    os.chdir(project_dir)

    try:
        # This will load from project .env → parent .env
        config = BaseConfig(project_name=project_name)

        # Validate dates
        if not config.curr_date or len(config.curr_date) != 8:
            errors.append(f"Invalid SCRAPER_CURR_DATE")
        if not config.prev_date or len(config.prev_date) != 8:
            errors.append(f"Invalid SCRAPER_PREV_DATE")

    except ValidationError as e:
        errors.append(f"Config validation error: {e}")
    except Exception as e:
        errors.append(f"Unexpected error: {e}")
    finally:
        os.chdir(original_cwd)

    return errors


def main():
    """Validate all .env files."""
    print("=" * 60)
    print("Environment Validation")
    print("=" * 60)

    all_errors = []

    # 1. Validate root .env
    print("\n[1/2] Checking root .env...")
    root_errors = validate_root_env()
    if root_errors:
        all_errors.extend(root_errors)
        for err in root_errors:
            print(f"  ❌ {err}")
    else:
        print("  ✅ Root .env is valid")

    # 2. Validate all projects
    print("\n[2/2] Checking project configurations...")
    projects = sorted(Path(".").glob("audiobee_*/"))

    for project in projects:
        errors = validate_project(project)
        if errors:
            all_errors.extend([f"{project.name}: {e}" for e in errors])
            print(f"  ❌ {project.name}")
            for err in errors:
                print(f"      - {err}")
        else:
            print(f"  ✅ {project.name}")

    # Summary
    print("\n" + "=" * 60)
    if all_errors:
        print(f"❌ {len(all_errors)} errors found")
        sys.exit(1)
    else:
        print("✅ All configurations valid")
        sys.exit(0)


if __name__ == "__main__":
    main()
```

### Option 2: Pre-commit Hook

Add to `.pre-commit-config.yaml`:

```yaml
repos:
    - repo: local
      hooks:
          - id: validate-env
            name: Validate environment files
            entry: python tools/validate_env.py
            language: python
            pass_filenames: false
            additional_dependencies:
                - pydantic>=2.0
                - pydantic-settings>=2.0
```

### Option 3: Symlink Root .env

For projects that ONLY need root credentials (no project-specific overrides):

```bash
#!/bin/bash
# tools/setup_env_symlinks.sh

# Create symlinks from project directories to root .env
for dir in audiobee_*/; do
  if [ -f "$dir/config.py" ]; then
    # Remove existing .env if it's not a symlink
    if [ -f "$dir/.env" ] && [ ! -L "$dir/.env" ]; then
      echo "Backing up $dir/.env to $dir/.env.backup"
      mv "$dir/.env" "$dir/.env.backup"
    fi

    # Create symlink
    ln -sf "../.env" "$dir/.env"
    echo "Linked $dir/.env → ../.env"
  fi
done
```

---

## Usage Patterns

### Pattern 1: Direct Config Loading

```python
# audiobee_bcbs_il/config.py
from shared_package.config import load_config

# Load with auto-detection of .env hierarchy
config = load_config(
    "sapphire",
    "audiobee_bcbs_il",
    network_id="210002020",
)

# Access validated values
print(config.curr_date)        # "20251226"
print(config.dirs["raw"])      # Path("20251226/raw")
```

### Pattern 2: CLI Override

```bash
# Override date via environment variable
SCRAPER_CURR_DATE=20251230 python run_all.py

# Or via CLI argument (if using Typer)
python run_all.py --curr 20251230
```

### Pattern 3: Programmatic Override

```python
# Override in code (highest priority)
config = load_config(
    "sapphire",
    "audiobee_bcbs_il",
    curr_date="20251230",  # This wins over .env
    prev_date="20251125",
)
```

---

## Security Best Practices

### 1. Never Commit Secrets

```gitignore
# .gitignore
.env
.env.local
.env.*.local
*.env

# But DO commit template
!.env.example
```

### 2. Use SecretStr for Credentials

```python
from pydantic import SecretStr

class ProxySettings(BaseSettings):
    password: SecretStr = Field(default=SecretStr(""))

# SecretStr prevents logging
print(settings.password)  # SecretStr('**********')

# Explicit access when needed
actual_password = settings.password.get_secret_value()
```

### 3. Rotate Credentials Regularly

- Update root `.env` with new credentials
- All projects automatically use new values
- No code changes required

### 4. Audit Hardcoded Secrets

```bash
# Find hardcoded API keys
grep -r "x-api-key" audiobee_*/config.py
grep -r "Subscription-Key" audiobee_*/config.py
grep -r "password.*=" audiobee_*/config.py | grep -v "os.getenv"
```

---

## Troubleshooting

### "Date must be YYYYMMDD format"

```bash
# Check your .env files
cat .env | grep DATE
cat audiobee_bcbs_il/.env | grep DATE

# Ensure no quotes around date
# WRONG: SCRAPER_CURR_DATE="20251226"
# RIGHT: SCRAPER_CURR_DATE=20251226
```

### "No proxy credentials configured"

```bash
# Verify root .env has proxy settings
cat .env | grep PROXY_

# Test proxy loading
python -c "from shared_package.config.proxy import get_proxy_settings; print(get_proxy_settings().get_available_types())"
```

### "Config loading from wrong .env"

```python
# Debug which .env files are being loaded
from shared_package.config import BaseConfig

# Check model_config
print(BaseConfig.model_config.get("env_file"))
# Should show: ('.env', '../.env', '../../.env')

# Check current working directory
import os
print(f"CWD: {os.getcwd()}")
```

---

## Migration Checklist

- [ ] Create `scraping/.env` with all shared secrets
- [ ] Create `scraping/.env.example` template
- [ ] Add `.env` to `.gitignore`
- [ ] Remove hardcoded API keys from config.py files
- [ ] Update config.py to use `load_config()`
- [ ] Run `tools/validate_env.py` to verify
- [ ] Test each scraper type with new config

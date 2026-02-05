# Configuration System Design

**Technology**: Pydantic Settings v2
**Pattern**: Site-type inheritance with factory function

---

## Current State Analysis

### Common Fields Across All 95+ Scrapers

| Field | Occurrence | Example |
|-------|------------|---------|
| `PREV_DATE` | 100% | `"20251110"` |
| `CURR_DATE` | 100% | `"20251210"` |
| `PROJECT_NAME` | 95% | `"audiobee_bcbs_il"` |
| `DIRS` | 100% | Computed from CURR_DATE |
| `REQ_STATES` | 95% | `["IL", "IN", "WI"]` |
| `BASE_URLS` | 85% | Dict of API endpoints |
| `HEADERS` | 70% | HTTP headers |

### Security Issue: Hardcoded API Keys

Found 15+ files with hardcoded secrets:

```python
# audiobee_bcbs_il/config.py
HEADERS = {
    "x-api-key": "03220e47-16eb-44d3-b1ca-4e3641973a97",  # EXPOSED!
}
```

---

## Solution: Pydantic Settings

### Why Pydantic over dataclasses

| Feature | Pydantic | dataclass |
|---------|----------|-----------|
| Validation | Built-in | Manual |
| Env vars | Native | Requires dotenv |
| Secrets | SecretStr | None |
| Computed | @computed_field | @property |
| JSON | Built-in | Manual |

---

## Implementation

### Base Configuration Class

```python
# shared/config/base.py

from datetime import datetime
from typing import Dict, List, Optional, Literal
import os

from pydantic import (
    Field,
    field_validator,
    computed_field,
    model_validator,
    SecretStr,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    """
    Base configuration for all scraper projects.

    Features:
    - Environment variable override (PREV_DATE, CURR_DATE, etc.)
    - .env file loading
    - Automatic DIRS computation
    - Validation on all fields

    Usage:
        config = BaseConfig(
            project_name="audiobee_bcbs_il",
            site_type="sapphire",
            prev_date="20251110",
            curr_date="20251210",
        )

        # Or from environment variables:
        # PREV_DATE=20251110 CURR_DATE=20251210 python index_1.py
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Project identification
    project_name: str = Field(description="Project identifier")
    site_type: Literal[
        "sapphire", "healthsparq", "carrier", "anthem",
        "werally", "provider_lenz", "healthtrio"
    ] = Field(description="Site type category")

    # Date management
    prev_date: str = Field(
        description="Previous run date (YYYYMMDD)",
        pattern=r"^\d{8}$"
    )
    curr_date: str = Field(
        description="Current run date (YYYYMMDD)",
        pattern=r"^\d{8}$"
    )

    # Geographic configuration
    req_states: List[str] = Field(
        default_factory=list,
        description="Required states for scraping"
    )

    # Concurrency
    batch_size: int = Field(default=100, ge=1, le=10000)
    semaphore: int = Field(default=10, ge=1, le=100)

    # Debug
    debug: bool = Field(default=False)

    @field_validator('prev_date', 'curr_date')
    @classmethod
    def validate_date(cls, v: str) -> str:
        """Validate date format."""
        try:
            datetime.strptime(v, "%Y%m%d")
        except ValueError:
            raise ValueError(f"Invalid date: {v}. Expected YYYYMMDD")
        return v

    @field_validator('req_states')
    @classmethod
    def validate_states(cls, v: List[str]) -> List[str]:
        """Validate state codes."""
        valid = {
            "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL",
            "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
            "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
            "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "PR",
            "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
            "WI", "WY"
        }
        for state in v:
            if state.upper() not in valid:
                raise ValueError(f"Invalid state: {state}")
        return [s.upper() for s in v]

    @model_validator(mode='after')
    def validate_date_order(self) -> 'BaseConfig':
        """Ensure prev_date < curr_date."""
        if self.prev_date > self.curr_date:
            raise ValueError(
                f"prev_date ({self.prev_date}) must be before "
                f"curr_date ({self.curr_date})"
            )
        return self

    @computed_field
    @property
    def dirs(self) -> Dict[str, str]:
        """Compute DIRS from curr_date."""
        return {
            "raw": os.path.join(self.curr_date, "raw"),
            "search_results": os.path.join(self.curr_date, "raw", "search_results"),
            "provider_details": os.path.join(self.curr_date, "raw", "provider_details"),
            "processed": os.path.join(self.curr_date, "processed"),
        }

    @computed_field
    @property
    def prev_dirs(self) -> Dict[str, str]:
        """Compute PREV_DIRS from prev_date."""
        return {
            "raw": os.path.join(self.prev_date, "raw"),
            "search_results": os.path.join(self.prev_date, "raw", "search_results"),
            "provider_details": os.path.join(self.prev_date, "raw", "provider_details"),
            "processed": os.path.join(self.prev_date, "processed"),
        }

    def setup_directories(self) -> None:
        """Create all required directories."""
        for dir_path in self.dirs.values():
            os.makedirs(dir_path, exist_ok=True)
```

### Sapphire Configuration

```python
# shared/config/sapphire.py

from typing import Dict
from pydantic import Field, computed_field, SecretStr
from .base import BaseConfig


class SapphireConfig(BaseConfig):
    """
    Configuration for Sapphire/ProviderFinderOnline scrapers.

    Used by: audiobee_bcbs_il, audiobee_bcbs_kc, audiobee_molina, etc.
    """

    site_type: str = "sapphire"

    # Network
    network_id: str = Field(description="Network ID for API")

    # API Key - from environment!
    api_key: SecretStr = Field(
        description="x-api-key (from SAPPHIRE_API_KEY env var)"
    )

    # Geographic
    geo_coords: str = Field(
        description="Center coordinates (lat,lng)",
        pattern=r"^-?\d+\.?\d*,-?\d+\.?\d*$"
    )
    radius: int = Field(default=100, ge=1, le=500)

    # API
    base_domain: str = Field(
        default="https://my.providerfinderonline.com"
    )

    @computed_field
    @property
    def base_urls(self) -> Dict[str, str]:
        """Compute API URLs."""
        return {
            "summary": f"{self.base_domain}/api/providers/summary.json",
            "affiliations": f"{self.base_domain}/api/providers/{{provider_id}}/locations/{{location_id}}/affiliations.json",
            "networks": f"{self.base_domain}/api/providers/{{provider_id}}/locations/{{location_id}}/networks_accepted.json",
        }

    def get_headers(self) -> Dict[str, str]:
        """Get HTTP headers with API key."""
        from uuid import uuid4
        return {
            "accept": "application/json",
            "x-api-key": self.api_key.get_secret_value(),
            "x-nonce": str(uuid4()),
        }
```

### Healthsparq Configuration

```python
# shared/config/healthsparq.py

from typing import Dict, List
from pydantic import Field, computed_field
from .base import BaseConfig


class HealthsparqConfig(BaseConfig):
    """
    Configuration for Healthsparq scrapers.

    Used by: audiobee_mvp_health, audiobee_medica, etc.
    Requires healthsparq-server on specified port.
    """

    site_type: str = "healthsparq"

    # Browser server
    puppeteer_port: int = Field(default=1018, ge=1000, le=65535)

    # Plans
    plans: List[Dict[str, str]] = Field(default_factory=list)

    # Domain
    domain: str = Field(description="Healthsparq subdomain")

    @computed_field
    @property
    def base_urls(self) -> Dict[str, str]:
        """Compute Healthsparq URLs."""
        base = f"https://{self.domain}.healthsparq.com/healthsparq/public/service"
        return {
            "search_url": f"{base}/v4/search",
            "profile_url": f"{base}/profile",
            "filter_url": f"{base}/v3/search/filters",
        }
```

### Carrier Configuration

```python
# shared/config/carrier.py

from typing import Dict, Optional
from pydantic import Field, SecretStr
from .base import BaseConfig


class CarrierConfig(BaseConfig):
    """
    Configuration for Carrier (direct API) scrapers.

    Used by: audiobee_florida_blue, audiobee_multiplan, etc.
    """

    site_type: str = "carrier"

    # API auth
    api_key: Optional[SecretStr] = Field(default=None)
    subscription_key: Optional[SecretStr] = Field(default=None)

    # API
    base_url: str = Field(description="Base URL for carrier API")
    page_size: int = Field(default=100, ge=1, le=1000)

    def get_headers(self) -> Dict[str, str]:
        """Get HTTP headers with auth."""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key.get_secret_value()
        if self.subscription_key:
            headers["Ocp-Apim-Subscription-Key"] = self.subscription_key.get_secret_value()
        return headers
```

### Anthem Configuration

```python
# shared/config/anthem.py

from typing import Dict, Optional, Literal
from pydantic import Field, computed_field
from .base import BaseConfig


class AnthemConfig(BaseConfig):
    """
    Configuration for Anthem/Wellpoint scrapers.

    Used by: audiobee_anthem, audiobee_amerigroup, etc.
    """

    site_type: str = "anthem"

    # Brand
    brand_code: Literal["ABCBS", "WLP", "AMG", "HLB", "SMP"] = Field(
        default="ABCBS"
    )

    # Browser
    browser_count: int = Field(default=1, ge=1, le=30)
    port: int = Field(default=5001)

    # Proxy
    proxy_url: Optional[str] = Field(default=None)

    @computed_field
    @property
    def base_domain(self) -> str:
        """Get domain for brand."""
        domains = {
            "ABCBS": "findcare.anthem.com",
            "WLP": "findcare.wellpoint.com",
            "AMG": "findcare.amerigroup.com",
            "HLB": "findcare.healthybluela.com",
            "SMP": "findcare.simplyhealthcareplans.com",
        }
        return domains.get(self.brand_code, "findcare.anthem.com")
```

### Factory Function

```python
# shared/config/factory.py

from typing import Type, Dict, Any, Optional
from .base import BaseConfig
from .sapphire import SapphireConfig
from .healthsparq import HealthsparqConfig
from .carrier import CarrierConfig
from .anthem import AnthemConfig


CONFIG_CLASSES: Dict[str, Type[BaseConfig]] = {
    "sapphire": SapphireConfig,
    "healthsparq": HealthsparqConfig,
    "carrier": CarrierConfig,
    "anthem": AnthemConfig,
}


def load_config(
    site_type: str,
    project_name: str,
    *,
    curr_date: Optional[str] = None,
    prev_date: Optional[str] = None,
    **overrides: Any
) -> BaseConfig:
    """
    Factory function to load configuration.

    Priority:
    1. Explicit overrides
    2. Environment variables
    3. .env file
    4. Defaults

    Args:
        site_type: "sapphire", "healthsparq", "carrier", "anthem"
        project_name: Project identifier
        curr_date: Override current date
        prev_date: Override previous date
        **overrides: Additional config values

    Returns:
        Configured BaseConfig subclass

    Example:
        config = load_config(
            "sapphire",
            "audiobee_bcbs_il",
            curr_date="20251210",
            network_id="210002020",
        )
    """
    config_class = CONFIG_CLASSES.get(site_type.lower())
    if not config_class:
        raise ValueError(f"Unknown site_type: {site_type}")

    values = {
        "project_name": project_name,
        "site_type": site_type.lower(),
    }

    if curr_date:
        values["curr_date"] = curr_date
    if prev_date:
        values["prev_date"] = prev_date

    values.update(overrides)

    return config_class(**values)
```

---

## Migration Guide

### Before (Legacy config.py)

```python
# audiobee_bcbs_il/config.py (BEFORE)

import os

PREV_DATE = "20251110"
CURR_DATE = "20251210"
PROJECT_NAME = "audiobee_bcbs_il"

DIRS = {
    "raw": os.path.join(CURR_DATE, "raw"),
    "search_results": os.path.join(CURR_DATE, "raw", "search_results"),
    ...
}

HEADERS = {
    "x-api-key": "03220e47-16eb-44d3-b1ca-4e3641973a97",  # EXPOSED!
}
```

### After (Migrated config.py)

```python
# audiobee_bcbs_il/config.py (AFTER)

"""
Configuration using shared utilities.
Backward compatible - all existing imports still work.
"""

from shared.config import load_config

# Load from .env + environment
_config = load_config(
    site_type="sapphire",
    project_name="audiobee_bcbs_il",
    network_id="210002020",
    geo_coords="39.883875,-88.834467",
    radius=210,
    req_states=["IL"],
)

# Backward compatibility exports
PREV_DATE = _config.prev_date
CURR_DATE = _config.curr_date
PROJECT_NAME = _config.project_name
DIRS = _config.dirs
PREV_DIRS = _config.prev_dirs
REQ_STATES = _config.req_states

# Setup directories
_config.setup_directories()

# For new code
config = _config
```

### Environment File

```bash
# audiobee_bcbs_il/.env

PREV_DATE=20251110
CURR_DATE=20251210
SAPPHIRE_API_KEY=03220e47-16eb-44d3-b1ca-4e3641973a97
```

---

## Environment Template

Create `.env.template` in project root:

```bash
# .env.template - Copy to .env and fill values

# =============================================================================
# DATES (Required)
# =============================================================================
PREV_DATE=20251110
CURR_DATE=20251210

# =============================================================================
# API KEYS - SECRETS
# =============================================================================
# Sapphire (providerfinderonline)
SAPPHIRE_API_KEY=your-api-key

# Multiplan
MULTIPLAN_SUBSCRIPTION_KEY=your-key

# =============================================================================
# PROXY (Optional)
# =============================================================================
# PROXY_URL=http://user:pass@proxy:8080

# =============================================================================
# SETTINGS
# =============================================================================
BATCH_SIZE=100
SEMAPHORE=10
DEBUG=false
```

---

## Dependencies

```toml
# shared/pyproject.toml

[project]
name = "shared"
version = "0.1.0"
requires-python = ">=3.12"

dependencies = [
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "python-dotenv>=1.0.0",
]
```

---

## Benefits

1. **Security**: API keys in .env, not in code
2. **Validation**: Invalid dates caught at load time
3. **Type Safety**: IDE autocomplete, mypy compatible
4. **Env Override**: `CURR_DATE=20251212 python index_1.py`
5. **DRY**: Computed DIRS, no manual path construction
6. **Backward Compatible**: Existing imports unchanged

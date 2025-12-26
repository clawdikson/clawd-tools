# HealthSparq Project Configuration Schema

## Overview

Each healthsparq project is defined by a YAML configuration file. Configs inherit from `_base.yaml` and override only project-specific values.

---

## Schema Definition

### Pydantic Models

```python
# healthsparq/config/schema.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional

class PlanConfig(BaseModel):
    """Individual plan configuration.

    IMPORTANT: insurer_code and brand_code are required for API authentication.
    If not specified per plan, they default to site-level values during loading.
    (Based on data integrity review 2025-12-26)
    """
    product_code: str = Field(..., description="HealthSparq product code")
    name: str = Field(..., description="Human-readable plan name")
    insurer_code: Optional[str] = Field(default=None, description="API insurer code (defaults to site.insurer_code)")
    brand_code: Optional[str] = Field(default=None, description="API brand code (defaults to site.brand_code)")
    state: Optional[str] = Field(default=None, description="State-specific plan (e.g., 'IA' for Iowa-only plans)")
    enabled: bool = Field(default=True, description="Whether to scrape this plan")

class SiteConfig(BaseModel):
    """HealthSparq site configuration."""
    domain: str = Field(..., description="HealthSparq domain (e.g., excellusbcbs.healthsparq.com)")
    brand_code: str = Field(..., description="Brand code for API auth")
    insurer_code: str = Field(..., description="Insurer code for API auth")
    api_version: str = Field(default="v4", description="API version (v3, v4)")

class CoverageConfig(BaseModel):
    """Geographic coverage configuration."""
    states: list[str] = Field(..., min_length=1, description="List of state codes")
    counties: Optional[dict[str, list[str]]] = Field(default=None, description="Optional county overrides per state")

    @field_validator("states")
    @classmethod
    def validate_states(cls, v):
        valid_states = {"AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL",
                       "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
                       "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
                       "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
                       "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"}
        for state in v:
            if state not in valid_states:
                raise ValueError(f"Invalid state code: {state}")
        return v

class FilterConfig(BaseModel):
    """Search filter configuration."""
    provider_types: list[str] = Field(
        default=["Facility", "Group", "Pharmacy", "Dental", "Physician", "Other"],
        description="Provider types to search"
    )
    specialties: Optional[list[str]] = Field(default=None, description="Specialty filters")
    languages: Optional[list[str]] = Field(default=None, description="Language filters")
    gender_filters: Optional[list[str]] = Field(default=None, description="Gender filters")
    organization_filters: Optional[list[str]] = Field(default=None, description="Organization filters")

class ConcurrencyConfig(BaseModel):
    """Concurrency and rate limiting configuration."""
    max_workers: int = Field(default=100, ge=1, le=500, description="Max concurrent API requests")
    max_browsers: int = Field(default=1, ge=1, le=5, description="Max browser instances")
    request_delay_ms: int = Field(default=0, ge=0, description="Delay between requests in ms")
    retry_attempts: int = Field(default=3, ge=1, le=10, description="Max retry attempts")
    retry_delay_ms: int = Field(default=1000, ge=100, description="Delay between retries")

class OutputConfig(BaseModel):
    """Output directory configuration."""
    base_dir: Optional[str] = Field(default=None, description="Override default output directory")
    raw_subdir: str = Field(default="raw", description="Raw output subdirectory")
    processed_subdir: str = Field(default="processed", description="Processed output subdirectory")

class ProjectMetadata(BaseModel):
    """Project metadata."""
    name: str = Field(..., description="Full project name")
    slug: str = Field(..., description="Project slug (used in CLI)")
    description: Optional[str] = Field(default=None, description="Project description")
    version: str = Field(default="1.0", description="Config schema version")

class HealthSparqProjectConfig(BaseModel):
    """Complete project configuration."""
    project: ProjectMetadata
    site: SiteConfig
    plans: list[PlanConfig]
    coverage: CoverageConfig
    filters: FilterConfig = Field(default_factory=FilterConfig)
    concurrency: ConcurrencyConfig = Field(default_factory=ConcurrencyConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
```

---

## YAML Examples

### Base Configuration (`_base.yaml`)

```yaml
# configs/_base.yaml
# Shared defaults for all projects

filters:
    provider_types:
        - Facility
        - Group
        - Pharmacy
        - Dental
        - Physician
        - Other

concurrency:
    max_workers: 100
    max_browsers: 1
    request_delay_ms: 0
    retry_attempts: 3
    retry_delay_ms: 1000

output:
    raw_subdir: raw
    processed_subdir: processed
```

### Project: CHRISTUS Health Plan

```yaml
# configs/christus_health_plan.yaml
project:
    name: audiobee_christus_health_plan
    slug: christus_health_plan
    description: "CHRISTUS Health Plan - Medicare Advantage, ACA"
    version: "1.0"

site:
    domain: christushealthplan.healthsparq.com
    brand_code: CHRISTUS
    insurer_code: CHRISTUS_I
    api_version: v4

plans:
    - product_code: USFHP
      name: "US Family Health Plan"
    - product_code: Networks
      name: "Provider Networks"
    - product_code: MA
      name: "Medicare Advantage"
    - product_code: HIX
      name: "ACA/Health Insurance Exchange"

coverage:
    states: [LA, NM, TX]
# Inherits filters from _base.yaml
# Inherits concurrency from _base.yaml
```

### Project: Excellus BCBS

```yaml
# configs/excellus.yaml
project:
    name: audiobee_excellus
    slug: excellus
    description: "Excellus BCBS - Medicare Advantage, Medicaid, ACA"
    version: "1.0"

site:
    domain: excellusbcbs.healthsparq.com
    brand_code: EXCELLUS
    insurer_code: EXCELLUS_BCBS
    api_version: v4

plans:
    - product_code: MA
      name: "Medicare Advantage"
    - product_code: MEDICAID
      name: "Medicaid"
    - product_code: HIX
      name: "ACA"

coverage:
    states: [NY]

concurrency:
    max_workers: 50 # Override due to rate limits
```

### Project: BlueCard National

```yaml
# configs/bluecard_national.yaml
project:
    name: audiobee_bluecard_national
    slug: bluecard_national
    description: "BlueCard National - All 50 states + DC"
    version: "1.0"

site:
    domain: provider.bcbs.com
    brand_code: BLUECARD
    insurer_code: BCBS_NATIONAL
    api_version: v4

plans:
    - product_code: HPN
      name: "BlueCard HPN"
    - product_code: PPO_EPO
      name: "BlueCard PPO/EPO"
    - product_code: PPO_BASIC
      name: "BlueCard PPO Basic"
    - product_code: TRADITIONAL
      name: "BlueCard Traditional"

coverage:
    states:
        - AL
        - AK
        - AZ
        - AR
        - CA
        - CO
        - CT
        - DE
        - DC
        - FL
        - GA
        - HI
        - ID
        - IL
        - IN
        - IA
        - KS
        - KY
        - LA
        - ME
        - MD
        - MA
        - MI
        - MN
        - MS
        - MO
        - MT
        - NE
        - NV
        - NH
        - NJ
        - NM
        - NY
        - NC
        - ND
        - OH
        - OK
        - OR
        - PA
        - RI
        - SC
        - SD
        - TN
        - TX
        - UT
        - VT
        - VA
        - WA
        - WV
        - WI
        - WY

concurrency:
    max_workers: 100
    max_browsers: 1
```

### Project: Independence (IBX)

```yaml
# configs/ibx.yaml
project:
    name: audiobee_ibx
    slug: ibx
    description: "Independence Blue Cross - ACA"
    version: "1.0"

site:
    domain: ibx.healthsparq.com
    brand_code: IBX
    insurer_code: IBX_PA
    api_version: v4

plans:
    - product_code: ACA_INDIVIDUAL
      name: "ACA Individual"
    - product_code: ACA_FAMILY
      name: "ACA Family"

coverage:
    states: [PA]
```

---

## Configuration Loading

```python
# healthsparq/config/loader.py
import yaml
from pathlib import Path
from typing import Optional
from .schema import HealthSparqProjectConfig

def load_config(project_slug: str, config_dir: Optional[Path] = None) -> HealthSparqProjectConfig:
    """Load and validate project configuration."""
    if config_dir is None:
        config_dir = Path(__file__).parent.parent / "configs"

    # Load base config
    base_path = config_dir / "_base.yaml"
    base_config = {}
    if base_path.exists():
        with open(base_path) as f:
            base_config = yaml.safe_load(f)

    # Load project config
    project_path = config_dir / f"{project_slug}.yaml"
    if not project_path.exists():
        raise FileNotFoundError(f"Config not found: {project_path}")

    with open(project_path) as f:
        project_config = yaml.safe_load(f)

    # Merge configs (project overrides base)
    merged = deep_merge(base_config, project_config)

    # Inherit site-level auth codes to plans if not specified
    # (Data integrity requirement: plans must have auth info at runtime)
    site = merged.get("site", {})
    site_insurer = site.get("insurer_code")
    site_brand = site.get("brand_code")
    for plan in merged.get("plans", []):
        if plan.get("insurer_code") is None:
            plan["insurer_code"] = site_insurer
        if plan.get("brand_code") is None:
            plan["brand_code"] = site_brand

    # Validate with Pydantic
    return HealthSparqProjectConfig(**merged)

def deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result

def list_projects(config_dir: Optional[Path] = None) -> list[str]:
    """List all available project slugs."""
    if config_dir is None:
        config_dir = Path(__file__).parent.parent / "configs"

    return [
        p.stem for p in config_dir.glob("*.yaml")
        if not p.name.startswith("_")
    ]
```

---

## Validation Rules

| Field                     | Type      | Required | Validation                           |
| ------------------------- | --------- | -------- | ------------------------------------ |
| `project.name`            | str       | Yes      | Non-empty                            |
| `project.slug`            | str       | Yes      | Lowercase, alphanumeric + underscore |
| `site.domain`             | str       | Yes      | Valid domain format                  |
| `site.brand_code`         | str       | Yes      | Uppercase alphanumeric               |
| `site.insurer_code`       | str       | Yes      | Uppercase alphanumeric + underscore  |
| `plans`                   | list      | Yes      | Min 1 plan                           |
| `plans[].product_code`    | str       | Yes      | Non-empty                            |
| `plans[].insurer_code`    | str       | No\*     | Defaults to site.insurer_code        |
| `plans[].brand_code`      | str       | No\*     | Defaults to site.brand_code          |
| `plans[].state`           | str       | No       | Valid 2-letter state code            |
| `coverage.states`         | list[str] | Yes      | Valid 2-letter state codes           |
| `concurrency.max_workers` | int       | No       | 1-500                                |

\*Plan-level auth codes inherit from site config if not specified. At runtime, all plans will have insurer_code and brand_code populated.

---

## Migration from Legacy config.py

### Before (Legacy)

```python
# audiobee_christus_health_plan/config.py
PREV_DATE = "20251114"
CURR_DATE = "20251214"
PROJECT_NAME = "audiobee_christus_health_plan"
MAX_WORKERS = 100

PLANS = [
    {"insurerCode": "CHRISTUS_I", "brandCode": "CHRISTUS", "productCode": "USFHP"},
    {"insurerCode": "CHRISTUS_I", "brandCode": "CHRISTUS", "productCode": "Networks"},
    {"insurerCode": "CHRISTUS_I", "brandCode": "CHRISTUS", "productCode": "MA"},
    {"insurerCode": "CHRISTUS_I", "brandCode": "CHRISTUS", "productCode": "HIX"},
]
REQ_STATES = ["LA", "NM", "TX"]
```

### After (Singleton YAML)

```yaml
# healthsparq/configs/christus_health_plan.yaml
project:
    name: audiobee_christus_health_plan
    slug: christus_health_plan

site:
    domain: christushealthplan.healthsparq.com
    brand_code: CHRISTUS
    insurer_code: CHRISTUS_I

# Plans inherit brand_code/insurer_code from site config (no need to repeat)
plans:
    - product_code: USFHP
      name: "US Family Health Plan"
    - product_code: Networks
      name: "Provider Networks"
    - product_code: MA
      name: "Medicare Advantage"
    - product_code: HIX
      name: "ACA"

coverage:
    states: [LA, NM, TX]

concurrency:
    max_workers: 100
```

**Key Changes from Legacy**:

- `insurerCode`/`brandCode` moved to `site` config (inherited by all plans)
- Plans only need `product_code` and `name` (auth codes inherited)
- `PREV_DATE`/`CURR_DATE` passed via CLI arguments, not stored in config

### Example: State-Specific Plan Override

Some projects have plans that require different auth codes per state:

```yaml
# healthsparq/configs/wellmark.yaml
site:
    domain: wellmark.healthsparq.com
    brand_code: WELLMARK
    insurer_code: WELLMARK_BCBS

plans:
    # Most plans inherit site auth codes
    - product_code: EPO
      name: "EPO Plan"
    - product_code: PPO
      name: "PPO Plan"
    # Iowa-specific plan with different insurer code
    - product_code: IA_MEDICAID
      name: "Iowa Medicaid"
      state: IA
      insurer_code: WELLMARK_MEDICAID_IA # Override site default
```

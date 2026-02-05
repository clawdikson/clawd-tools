---
date: 2026-01-11
type: migration-plan
scope: core-updates
parent: INDEX.md
---

# Core Package Updates for Migration

Required changes to `core/` to support audiobee_* project migrations.

## Summary

| Update | Priority | Effort | Status |
|--------|----------|--------|--------|
| AnthemConfig enhancement | High | Low | Pending |
| UHCConfig creation | High | Medium | Pending |
| Mapper registry pattern | Medium | Medium | Pending |
| Additional proxy providers | Low | Low | Pending |

---

## 1. AnthemConfig Enhancement

**Priority**: High
**Effort**: Low
**Location**: `core/config/anthem.py`

### Current State

```python
class AnthemConfig(BaseConfig):
    brand: str = ""
    camoufox: bool = True
    max_workers: int = 5
```

### Required Changes

Add fields for Anthem/Wellpoint/SydneyHealth platform:

```python
class AnthemConfig(BaseConfig):
    # Existing
    brand: str = ""
    camoufox: bool = True
    max_workers: int = 5

    # New fields needed
    sydney_health_url: str = "https://www.sydneyhealth.com"
    api_version: str = "v2"
    auth_type: Literal["oauth", "cookie"] = "cookie"
    tenant_id: str = ""
    plan_type: Literal["commercial", "medicaid", "medicare"] = "commercial"
```

### Projects Using This

- `audiobee_amerigroup`
- `audiobee_anthem`
- `audiobee_blueshield_ca`
- `audiobee_elderplan`
- `audiobee_healthy_blue`

---

## 2. UHCConfig Creation

**Priority**: High
**Effort**: Medium
**Location**: `core/config/uhc.py` (new file)

### Design

```python
from core.config.base import BaseConfig

class UHCConfig(BaseConfig):
    """Configuration for UnitedHealthcare/Optum platforms."""

    site_type: str = "uhc"

    # UHC-specific
    optum_api_url: str = "https://api.optum.com"
    uhc_portal_url: str = "https://www.uhc.com"
    api_key: SecretStr = ""
    member_type: Literal["individual", "medicaid", "behavioral"] = "individual"

    # Search parameters
    search_radius_miles: int = 50
    max_results_per_page: int = 100

    # Rate limiting
    requests_per_minute: int = 60
    concurrent_requests: int = 5
```

### Registry Update

Add to `core/config/registry.py`:

```python
CONFIG_TYPES = {
    "sapphire": SapphireConfig,
    "healthsparq": HealthsparqConfig,
    "carrier": CarrierConfig,
    "anthem": AnthemConfig,
    "uhc": UHCConfig,  # New
}
```

### Projects Using This

- `audiobee_uhc_behavioral_health`
- `audiobee_uhc_individual`
- `audiobee_uhc_medicaid`

---

## 3. Mapper Registry Pattern

**Priority**: Medium
**Effort**: Medium
**Location**: `core/mapper/registry.py` (new file)

### Problem

HealthSparq uses factory pattern (`make_mapper()`), Sapphire uses registry pattern (`register_mapper()`). Should unify for consistency.

### Proposed Solution

Create unified registry in core that both platforms can use:

```python
# core/mapper/registry.py

from typing import Callable
from collections import defaultdict

MapperFunc = Callable[[dict], dict]

_MAPPERS: dict[str, dict[str, MapperFunc]] = defaultdict(dict)

def register_mapper(platform: str, project: str, mapper: MapperFunc) -> None:
    """Register a project-specific mapper.

    Args:
        platform: Platform name (healthsparq, sapphire, anthem, uhc)
        project: Project slug
        mapper: Mapper function
    """
    _MAPPERS[platform][project] = mapper

def get_mapper(platform: str, project: str, default: MapperFunc | None = None) -> MapperFunc:
    """Get mapper for project, or default."""
    return _MAPPERS[platform].get(project, default)

def list_mappers(platform: str) -> list[str]:
    """List registered mappers for a platform."""
    return list(_MAPPERS[platform].keys())
```

### Migration Path

1. Add `core/mapper/registry.py`
2. Update HealthSparq to use registry (keep `make_mapper()` as wrapper)
3. Update Sapphire to use core registry
4. Deprecate platform-specific registries

---

## 4. Additional Proxy Providers

**Priority**: Low
**Effort**: Low
**Location**: `core/proxy/providers/`

### Potentially Needed

Some projects may use different proxy providers. Check during migration:

- Oxylabs (if used)
- Bright Data (if used)
- Custom proxy pools

### Action

Survey projects during migration; add providers as discovered.

---

## Testing Requirements

### Unit Tests

For each new config class:

```python
# core/tests/test_config.py

def test_uhc_config_defaults():
    config = UHCConfig()
    assert config.site_type == "uhc"
    assert config.search_radius_miles == 50

def test_uhc_config_from_env(monkeypatch):
    monkeypatch.setenv("SCRAPER_OPTUM_API_URL", "https://custom.optum.com")
    config = UHCConfig()
    assert config.optum_api_url == "https://custom.optum.com"
```

### Integration Tests

Validate config loading works end-to-end:

```python
def test_load_uhc_config():
    config = load_config("uhc", project_name="uhc_individual")
    assert isinstance(config, UHCConfig)
```

---

## Implementation Order

1. **AnthemConfig enhancement** - Quick win, enables Anthem migrations
2. **UHCConfig creation** - Enables UHC migrations
3. **Mapper registry** - Can be done in parallel
4. **Additional proxy providers** - As needed during migrations

---

## Related Documents

- [INDEX.md](./INDEX.md) - Master migration index
- [healthsparq-updates.md](./healthsparq-updates.md) - HealthSparq updates
- [sapphire-updates.md](./sapphire-updates.md) - Sapphire updates

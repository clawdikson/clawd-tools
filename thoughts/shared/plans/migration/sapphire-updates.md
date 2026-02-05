---
date: 2026-01-11
type: migration-plan
scope: sapphire-updates
parent: INDEX.md
---

# Sapphire Package Updates for Migration

Required changes to `sapphire/` to support 11 new project migrations.

## Summary

| Update | Priority | Effort | Status |
|--------|----------|--------|--------|
| Add 11 new YAML configs | High | Medium | Pending |
| Config template creation | High | Low | Pending |
| Recovery phase (Phase 6) | Medium | Medium | Pending |
| Geo strategy enhancements | Low | Low | Pending |
| Documentation updates | Low | Low | Pending |

---

## 1. New YAML Configs (11)

**Priority**: High
**Location**: `sapphire/configs/`

### Config Template

Create `sapphire/configs/_template.yaml`:

```yaml
# Template for new Sapphire project configs
# Copy this file and rename to {project_slug}.yaml

project:
  name: "Project Name"           # Human-readable name
  slug: project_slug             # URL-safe identifier

site:
  base_url: https://pfo.example.com
  api_version: v2
  tenant_id: TENANT              # From PFO site

plans:
  - network_id: "12345"
    name: "PPO Network"
    product_type: ppo
  # Add more plans as needed

coverage:
  states: [XX, YY]               # State abbreviations
  geo_strategy: small            # small | complete | dual

search:
  max_radius_miles: 50
  provider_types:
    - physician
    - facility
    - ancillary

output:
  storage_backend: sqlite        # sqlite | json_files | jsonl
  raw_subdir: raw
  processed_subdir: processed

advanced:
  browser_type: camoufox         # camoufox | playwright | patchright
  max_concurrent: 5
  request_timeout: 30
  checkpoint_enabled: true
```

### Configs to Create

| Project | Config File | Base URL (to discover) |
|---------|-------------|------------------------|
| `bcbs_kc` | `bcbs_kc.yaml` | pfo.bcbskc.com |
| `bcbs_la` | `bcbs_la.yaml` | pfo.bcbsla.com |
| `bcbs_mn` | `bcbs_mn.yaml` | pfo.bluecrossmn.com |
| `bcbs_nm` | `bcbs_nm.yaml` | pfo.bcbsnm.com |
| `bcbs_sc_medicaid` | `bcbs_sc_medicaid.yaml` | pfo.bluechoicesc.com |
| `bcbs_tx` | `bcbs_tx.yaml` | pfo.bcbstx.com |
| `bcbs_vt` | `bcbs_vt.yaml` | pfo.bcbsvt.com |
| `carefirst` | `carefirst.yaml` | pfo.carefirst.com |
| `cox_health_plans` | `cox_health_plans.yaml` | - |
| `horizon` | `horizon.yaml` | pfo.horizonblue.com |
| `instil_health` | `instil_health.yaml` | - |
| `molina` | `molina.yaml` | pfo.molinahealthcare.com |
| `st_lukes` | `st_lukes.yaml` | - |

### Config Discovery Process

For each project:

1. Read existing project code to find:
   - PFO base URL
   - Tenant ID
   - Network IDs and product types
   - State coverage
   - Geo strategy used

2. Create YAML config from template

3. Validate with `python -m sapphire validate {project}`

---

## 2. Recovery Phase (Phase 6)

**Priority**: Medium
**Effort**: Medium
**Location**: `sapphire/phases/recovery.py` (new file)

### Problem

HealthSparq has a Phase 6 (Recovery) for retrying failed providers. Sapphire lacks this.

### Proposed Solution

Port recovery phase from healthsparq with adaptations:

```python
# sapphire/phases/recovery.py

from core.io import DataStore

async def run_recovery(
    config: SapphireProjectConfig,
    curr_date: str,
    max_retries: int = 3,
) -> RecoveryResult:
    """Retry failed provider detail fetches.

    Args:
        config: Project configuration
        curr_date: Current date string (YYYYMMDD)
        max_retries: Maximum retry attempts per provider

    Returns:
        RecoveryResult with success/failure counts
    """
    # Load checkpoint to find failed IDs
    checkpoint = load_checkpoint(config, curr_date)
    failed_ids = checkpoint.get("failed_provider_ids", [])

    if not failed_ids:
        return RecoveryResult(recovered=0, still_failed=0)

    # Retry with exponential backoff
    recovered = []
    still_failed = []

    for provider_id in failed_ids:
        for attempt in range(max_retries):
            try:
                details = await fetch_provider_details(config, provider_id)
                if details:
                    save_provider_details(config, curr_date, details)
                    recovered.append(provider_id)
                    break
            except Exception:
                if attempt == max_retries - 1:
                    still_failed.append(provider_id)
                await asyncio.sleep(2 ** attempt)

    return RecoveryResult(
        recovered=len(recovered),
        still_failed=len(still_failed),
    )
```

### CLI Integration

```python
# sapphire/cli.py

@app.command()
def run(
    project: str,
    curr: str = typer.Option(...),
    phase: int = typer.Option(None),
    recovery: bool = typer.Option(False, help="Run recovery phase"),
):
    if recovery:
        result = asyncio.run(run_recovery(config, curr))
        typer.echo(f"Recovered: {result.recovered}, Failed: {result.still_failed}")
```

---

## 3. Geo Strategy Enhancements

**Priority**: Low
**Effort**: Low
**Location**: `sapphire/core/geo.py`

### Current Strategies

| Strategy | Description | Best For |
|----------|-------------|----------|
| `small` | Dense overlapping circles (5-10mi) | Urban areas |
| `complete` | State-wide sweeps | Full coverage |
| `dual` | Both strategies combined | Comprehensive |

### Potential Enhancements

#### 3a. County-Based Strategy

For projects with county-specific networks:

```python
def get_county_centroids(states: list[str]) -> list[GeoPoint]:
    """Get centroid for each county in given states."""
    # Load county centroids from bundled data
    return [...]
```

#### 3b. Adaptive Density

Adjust circle density based on provider count in area:

```python
def adaptive_circles(
    state: str,
    min_radius: float = 5,
    max_radius: float = 50,
    target_overlap: float = 0.3,
) -> list[Circle]:
    """Generate circles with adaptive density."""
    # Dense in urban areas, sparse in rural
    ...
```

### Decision

Defer until specific project requires it. Current strategies sufficient for 11 migrations.

---

## 4. Browser Pool Enhancements

**Priority**: Low
**Location**: `sapphire/core/browser_queue.py`

### Current State

`SapphireBrowserQueue` manages browser instances for anti-bot handling.

### Potential Enhancement

Add browser recycling after N requests to avoid fingerprinting:

```python
class SapphireBrowserQueue:
    def __init__(
        self,
        max_browsers: int = 5,
        requests_per_browser: int = 100,  # New
    ):
        self.requests_per_browser = requests_per_browser
        self._request_counts: dict[int, int] = {}

    async def get_browser(self) -> Browser:
        browser = await self._pool.acquire()
        browser_id = id(browser)

        self._request_counts[browser_id] = self._request_counts.get(browser_id, 0) + 1

        if self._request_counts[browser_id] >= self.requests_per_browser:
            # Recycle browser
            await self._recycle_browser(browser)
            browser = await self._pool.acquire()

        return browser
```

### Decision

Implement only if anti-bot issues arise during migrations.

---

## 5. Documentation Updates

**Priority**: Low

### Files to Update

| File | Updates Needed |
|------|----------------|
| `sapphire/CLAUDE.md` | Add migration section |
| `sapphire/README.md` | Update project list |
| `sapphire/configs/README.md` | Document config format |

---

## Migration Checklist Per Project

For each Sapphire project migration:

- [ ] Analyze existing `audiobee_{project}/` code
- [ ] Extract base_url, tenant_id
- [ ] Extract network_ids and product_types
- [ ] Extract state coverage and geo_strategy
- [ ] Create `sapphire/configs/{project}.yaml`
- [ ] Run `python -m sapphire validate {project}`
- [ ] Test with `python -m sapphire run {project} --curr YYYYMMDD --dry-run`
- [ ] Compare output with legacy scraper
- [ ] Create thin wrapper if custom mapper needed
- [ ] Archive legacy `audiobee_{project}/` directory

---

## Existing Configs (Reference)

Already migrated projects to use as templates:

### bcbs_il.yaml

```yaml
project:
  name: "BCBS Illinois"
  slug: bcbs_il

site:
  base_url: https://pfo.bcbsil.com
  api_version: v2

plans:
  - network_id: "IL_PPO"
    name: "BlueChoice PPO"
    product_type: ppo

coverage:
  states: [IL]
  geo_strategy: complete
```

### bcbs_mt.yaml

```yaml
project:
  name: "BCBS Montana"
  slug: bcbs_mt

site:
  base_url: https://pfo.bcbsmt.com
  api_version: v2

plans:
  - network_id: "MT_PPO"
    name: "Blue Options PPO"
    product_type: ppo

coverage:
  states: [MT]
  geo_strategy: complete
```

---

## Related Documents

- [INDEX.md](./INDEX.md) - Master migration index
- [core-updates.md](./core-updates.md) - Core package updates
- [healthsparq-updates.md](./healthsparq-updates.md) - HealthSparq updates

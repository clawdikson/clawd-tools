---
date: 2026-01-11
type: migration-plan
project: bcbs_la
platform: sapphire
status: planned
parent: ../INDEX.md
---

# BCBS Louisiana Migration Plan

Migrate `audiobee_bcbs_la/` to use `sapphire/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Blue Cross Blue Shield Louisiana |
| Project Slug | `bcbs_la` |
| Platform | sapphire (PFO) |
| States | LA |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Analysis

### Platform Indicators

- Platform: Sapphire/ProviderFinderOnline (confirmed)
- Base URL: pfo.bcbsla.com
- API Version: v2
- Geo Strategy: complete

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# sapphire/configs/bcbs_la.yaml

project:
  name: "Blue Cross Blue Shield Louisiana"
  slug: bcbs_la

site:
  base_url: https://pfo.bcbsla.com
  api_version: v2
  tenant_id: TBD

plans:
  - network_id: TBD
    name: "PPO Network"
    product_type: ppo

coverage:
  states: [LA]
  geo_strategy: complete

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m sapphire validate bcbs_la
python -m sapphire run bcbs_la --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- Single state coverage
- Reference implementation: `audiobee_bcbs_il/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

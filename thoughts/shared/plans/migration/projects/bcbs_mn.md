---
date: 2026-01-11
type: migration-plan
project: bcbs_mn
platform: sapphire
status: planned
parent: ../INDEX.md
---

# BCBS Minnesota Migration Plan

Migrate `audiobee_bcbs_mn/` to use `sapphire/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Blue Cross Blue Shield Minnesota |
| Project Slug | `bcbs_mn` |
| Platform | sapphire (PFO) |
| States | MN |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Analysis

### Platform Indicators

- Platform: Sapphire/ProviderFinderOnline (confirmed)
- Base URL: pfo.bluecrossmn.com
- API Version: v2
- Geo Strategy: complete

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# sapphire/configs/bcbs_mn.yaml

project:
  name: "Blue Cross Blue Shield Minnesota"
  slug: bcbs_mn

site:
  base_url: https://pfo.bluecrossmn.com
  api_version: v2
  tenant_id: TBD

plans:
  - network_id: TBD
    name: "PPO Network"
    product_type: ppo

coverage:
  states: [MN]
  geo_strategy: complete

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m sapphire validate bcbs_mn
python -m sapphire run bcbs_mn --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- Note: Different from `audiobee_medica` (HealthSparq platform)
- Reference implementation: `audiobee_bcbs_il/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

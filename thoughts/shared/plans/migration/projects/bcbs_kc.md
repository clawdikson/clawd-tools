---
date: 2026-01-11
type: migration-plan
project: bcbs_kc
platform: sapphire
status: planned
parent: ../INDEX.md
---

# BCBS Kansas City Migration Plan

Migrate `audiobee_bcbs_kc/` to use `sapphire/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Blue Cross Blue Shield Kansas City |
| Project Slug | `bcbs_kc` |
| Platform | sapphire (PFO) |
| States | KS, MO |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Analysis

### Platform Indicators

- Platform: Sapphire/ProviderFinderOnline (confirmed)
- Base URL: pfo.bcbskc.com
- API Version: v2
- Geo Strategy: complete (recommended for multi-state)

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# sapphire/configs/bcbs_kc.yaml

project:
  name: "Blue Cross Blue Shield Kansas City"
  slug: bcbs_kc

site:
  base_url: https://pfo.bcbskc.com
  api_version: v2
  tenant_id: TBD

plans:
  - network_id: TBD
    name: "PPO Network"
    product_type: ppo

coverage:
  states: [KS, MO]
  geo_strategy: complete

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m sapphire validate bcbs_kc
python -m sapphire run bcbs_kc --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- Multi-state coverage (Kansas City metro area)
- Reference implementation: `audiobee_bcbs_il/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

---
date: 2026-01-11
type: migration-plan
project: st_lukes
platform: sapphire
status: planned
parent: ../INDEX.md
---

# St. Luke's Migration Plan

Migrate `audiobee_st_lukes/` to use `sapphire/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | St. Luke's Health Plan |
| Project Slug | `st_lukes` |
| Platform | sapphire (PFO) |
| States | TBD |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# sapphire/configs/st_lukes.yaml

project:
  name: "St. Luke's Health Plan"
  slug: st_lukes

site:
  base_url: TBD
  api_version: v2
  tenant_id: TBD

coverage:
  states: []  # TBD
  geo_strategy: small  # Regional health system

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m sapphire validate st_lukes
python -m sapphire run st_lukes --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- Regional health system
- Need to identify state coverage
- Reference implementation: `audiobee_bcbs_il/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

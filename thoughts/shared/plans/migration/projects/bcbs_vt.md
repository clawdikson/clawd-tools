---
date: 2026-01-11
type: migration-plan
project: bcbs_vt
platform: sapphire
status: planned
parent: ../INDEX.md
---

# BCBS Vermont Migration Plan

Migrate `audiobee_bcbs_vt/` to use `sapphire/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Blue Cross Blue Shield Vermont |
| Project Slug | `bcbs_vt` |
| Platform | sapphire (PFO) |
| States | VT |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# sapphire/configs/bcbs_vt.yaml

project:
  name: "Blue Cross Blue Shield Vermont"
  slug: bcbs_vt

site:
  base_url: https://pfo.bcbsvt.com
  api_version: v2
  tenant_id: TBD

coverage:
  states: [VT]
  geo_strategy: complete

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m sapphire validate bcbs_vt
python -m sapphire run bcbs_vt --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- Small state, low volume
- Reference implementation: `audiobee_bcbs_il/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

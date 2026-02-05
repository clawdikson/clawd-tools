---
date: 2026-01-11
type: migration-plan
project: bcbs_nm
platform: sapphire
status: planned
parent: ../INDEX.md
---

# BCBS New Mexico Migration Plan

Migrate `audiobee_bcbs_nm/` to use `sapphire/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Blue Cross Blue Shield New Mexico |
| Project Slug | `bcbs_nm` |
| Platform | sapphire (PFO) |
| States | NM |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# sapphire/configs/bcbs_nm.yaml

project:
  name: "Blue Cross Blue Shield New Mexico"
  slug: bcbs_nm

site:
  base_url: https://pfo.bcbsnm.com
  api_version: v2
  tenant_id: TBD

coverage:
  states: [NM]
  geo_strategy: complete

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m sapphire validate bcbs_nm
python -m sapphire run bcbs_nm --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- Reference implementation: `audiobee_bcbs_il/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

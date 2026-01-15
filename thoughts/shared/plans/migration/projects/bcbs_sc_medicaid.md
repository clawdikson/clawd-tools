---
date: 2026-01-11
type: migration-plan
project: bcbs_sc_medicaid
platform: sapphire
status: planned
parent: ../INDEX.md
---

# BCBS SC Medicaid Migration Plan

Migrate `audiobee_bcbs_sc_medicaid/` to use `sapphire/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Blue Cross Blue Shield SC Medicaid |
| Project Slug | `bcbs_sc_medicaid` |
| Platform | sapphire (PFO) |
| States | SC |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# sapphire/configs/bcbs_sc_medicaid.yaml

project:
  name: "Blue Cross Blue Shield SC Medicaid"
  slug: bcbs_sc_medicaid

site:
  base_url: https://pfo.bluechoicesc.com
  api_version: v2
  tenant_id: TBD

plans:
  - network_id: TBD
    name: "Medicaid"
    product_type: medicaid

coverage:
  states: [SC]
  geo_strategy: complete

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m sapphire validate bcbs_sc_medicaid
python -m sapphire run bcbs_sc_medicaid --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- Medicaid product variant
- Reference implementation: `audiobee_bcbs_il/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

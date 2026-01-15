---
date: 2026-01-11
type: migration-plan
project: health_plan_nv_medicaid
platform: healthsparq
status: planned
parent: ../INDEX.md
---

# Health Plan NV Medicaid Migration Plan

Migrate `audiobee_health_plan_nv_medicaid/` to use `healthsparq/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Health Plan of Nevada Medicaid |
| Project Slug | `health_plan_nv_medicaid` |
| Platform | healthsparq |
| States | NV |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# healthsparq/configs/health_plan_nv_medicaid.yaml

project:
  name: "Health Plan of Nevada Medicaid"
  slug: health_plan_nv_medicaid

site:
  domain: TBD
  brand_code: HPNV
  insurer_code: TBD

plans:
  - product_code: MEDICAID
    name: "Medicaid"

coverage:
  states: [NV]

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m healthsparq validate health_plan_nv_medicaid
python -m healthsparq run health_plan_nv_medicaid --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- Medicaid-focused product
- Reference implementation: `audiobee_wellmark/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

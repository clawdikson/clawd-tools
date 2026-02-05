---
date: 2026-01-11
type: migration-plan
project: amerihealth_caritas_fl
platform: healthsparq
status: planned
parent: ../INDEX.md
---

# AmeriHealth Caritas FL Migration Plan

Migrate `audiobee_amerihealth_caritas_fl/` to use `healthsparq/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | AmeriHealth Caritas Florida |
| Project Slug | `amerihealth_caritas_fl` |
| Platform | healthsparq |
| States | FL |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Analysis

### Platform Indicators

- Platform: HealthSparq (AmeriHealth family)
- Domain: TBD (extract from legacy)
- Brand Code: AMERIHEALTH_CARITAS
- Medicaid focus

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# healthsparq/configs/amerihealth_caritas_fl.yaml

project:
  name: "AmeriHealth Caritas Florida"
  slug: amerihealth_caritas_fl

site:
  domain: TBD
  brand_code: AMERIHEALTH_CARITAS
  insurer_code: TBD

plans:
  - product_code: MEDICAID
    name: "Medicaid"

coverage:
  states: [FL]

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m healthsparq validate amerihealth_caritas_fl
python -m healthsparq run amerihealth_caritas_fl --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- AmeriHealth Caritas is Medicaid focused
- Part of AmeriHealth family
- Reference implementation: `audiobee_wellmark/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

---
date: 2026-01-11
type: migration-plan
project: amerihealth_nj
platform: healthsparq
status: planned
parent: ../INDEX.md
---

# AmeriHealth NJ Migration Plan

Migrate `audiobee_amerihealth_nj/` to use `healthsparq/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | AmeriHealth New Jersey |
| Project Slug | `amerihealth_nj` |
| Platform | healthsparq |
| States | NJ |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Analysis

### Platform Indicators

- Platform: HealthSparq (AmeriHealth family)
- Domain: TBD (extract from legacy)
- Brand Code: AMERIHEALTH_NJ
- Commercial/Medicaid

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# healthsparq/configs/amerihealth_nj.yaml

project:
  name: "AmeriHealth New Jersey"
  slug: amerihealth_nj

site:
  domain: TBD
  brand_code: AMERIHEALTH_NJ
  insurer_code: TBD

coverage:
  states: [NJ]

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m healthsparq validate amerihealth_nj
python -m healthsparq run amerihealth_nj --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

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

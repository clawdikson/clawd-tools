---
date: 2026-01-11
type: migration-plan
project: amerihealth_caritas_vip_de
platform: healthsparq
status: planned
parent: ../INDEX.md
---

# AmeriHealth Caritas VIP DE Migration Plan

Migrate `audiobee_amerihealth_caritas_vip_de/` to use `healthsparq/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | AmeriHealth Caritas VIP Delaware |
| Project Slug | `amerihealth_caritas_vip_de` |
| Platform | healthsparq |
| States | DE |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Analysis

### Platform Indicators

- Platform: HealthSparq (AmeriHealth family)
- Domain: TBD (extract from legacy)
- Brand Code: AMERIHEALTH_CARITAS_VIP
- VIP/Medicare focus

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# healthsparq/configs/amerihealth_caritas_vip_de.yaml

project:
  name: "AmeriHealth Caritas VIP Delaware"
  slug: amerihealth_caritas_vip_de

site:
  domain: TBD
  brand_code: AMERIHEALTH_CARITAS_VIP
  insurer_code: TBD

coverage:
  states: [DE]

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m healthsparq validate amerihealth_caritas_vip_de
python -m healthsparq run amerihealth_caritas_vip_de --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- VIP indicates Medicare Advantage product
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

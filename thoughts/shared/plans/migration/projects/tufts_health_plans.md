---
date: 2026-01-11
type: migration-plan
project: tufts_health_plans
platform: healthsparq
status: planned
parent: ../INDEX.md
---

# Tufts Health Plans Migration Plan

Migrate `audiobee_tufts_health_plans/` to use `healthsparq/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Tufts Health Plans |
| Project Slug | `tufts_health_plans` |
| Platform | healthsparq |
| States | MA |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Analysis

### Platform Indicators

- Platform: HealthSparq (confirmed)
- Domain: tufts.healthsparq.com
- Brand Code: TUFTS
- Insurer Code: TBD

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# healthsparq/configs/tufts_health_plans.yaml

project:
  name: "Tufts Health Plans"
  slug: tufts_health_plans

site:
  domain: tufts.healthsparq.com
  brand_code: TUFTS
  insurer_code: TBD

coverage:
  states: [MA]

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m healthsparq validate tufts_health_plans
python -m healthsparq run tufts_health_plans --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- Massachusetts focus
- Reference implementation: `audiobee_wellmark/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

---
date: 2026-01-11
type: migration-plan
project: excellus
platform: healthsparq
status: planned
parent: ../INDEX.md
---

# Excellus Migration Plan

Migrate `audiobee_excellus/` to use `healthsparq/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Excellus BlueCross BlueShield |
| Project Slug | `excellus` |
| Platform | healthsparq |
| States | NY |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Analysis

### Platform Indicators

- Platform: HealthSparq (confirmed)
- Domain: excellus.healthsparq.com
- Brand Code: EXCELLUS
- Insurer Code: TBD

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# healthsparq/configs/excellus.yaml

project:
  name: "Excellus BlueCross BlueShield"
  slug: excellus

site:
  domain: excellus.healthsparq.com
  brand_code: EXCELLUS
  insurer_code: TBD

coverage:
  states: [NY]

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m healthsparq validate excellus
python -m healthsparq run excellus --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- Upstate NY focus
- Reference implementation: `audiobee_wellmark/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

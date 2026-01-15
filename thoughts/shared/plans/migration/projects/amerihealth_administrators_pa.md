---
date: 2026-01-11
type: migration-plan
project: amerihealth_administrators_pa
platform: healthsparq
status: planned
parent: ../INDEX.md
---

# AmeriHealth Administrators PA Migration Plan

Migrate `audiobee_amerihealth_administrators_pa/` to use `healthsparq/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | AmeriHealth Administrators PA |
| Project Slug | `amerihealth_administrators_pa` |
| Platform | healthsparq |
| States | PA |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Analysis

### Platform Indicators

- Platform: HealthSparq (AmeriHealth family)
- Domain: TBD (extract from legacy)
- Brand Code: AMERIHEALTH
- Part of AmeriHealth family of projects

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# healthsparq/configs/amerihealth_administrators_pa.yaml

project:
  name: "AmeriHealth Administrators PA"
  slug: amerihealth_administrators_pa

site:
  domain: TBD
  brand_code: AMERIHEALTH
  insurer_code: TBD

coverage:
  states: [PA]

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m healthsparq validate amerihealth_administrators_pa
python -m healthsparq run amerihealth_administrators_pa --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- Part of AmeriHealth family
- May share configuration patterns with other AmeriHealth projects
- Reference implementation: `audiobee_wellmark/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

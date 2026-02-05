---
date: 2026-01-11
type: migration-plan
project: bcbs_ne
platform: healthsparq
status: planned
parent: ../INDEX.md
---

# BCBS Nebraska Migration Plan

Migrate `audiobee_bcbs_ne/` to use `healthsparq/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Blue Cross Blue Shield Nebraska |
| Project Slug | `bcbs_ne` |
| Platform | healthsparq |
| States | NE |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Analysis

### Platform Indicators

- Platform: HealthSparq (confirmed)
- Domain: bcbsne.healthsparq.com (likely)
- Brand Code: BCBSNE
- Single state coverage

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# healthsparq/configs/bcbs_ne.yaml

project:
  name: "Blue Cross Blue Shield Nebraska"
  slug: bcbs_ne

site:
  domain: bcbsne.healthsparq.com
  brand_code: BCBSNE
  insurer_code: TBD

coverage:
  states: [NE]

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m healthsparq validate bcbs_ne
python -m healthsparq run bcbs_ne --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- Reference implementation: `audiobee_wellmark/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

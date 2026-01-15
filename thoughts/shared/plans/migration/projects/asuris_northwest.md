---
date: 2026-01-11
type: migration-plan
project: asuris_northwest
platform: healthsparq
status: planned
parent: ../INDEX.md
---

# Asuris Northwest Migration Plan

Migrate `audiobee_asuris_northwest/` to use `healthsparq/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Asuris Northwest Health |
| Project Slug | `asuris_northwest` |
| Platform | healthsparq |
| States | WA, OR |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Analysis

### Platform Indicators

- Platform: HealthSparq (confirmed)
- Domain: asuris.healthsparq.com (likely)
- Brand Code: ASURIS
- Pacific Northwest focus

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# healthsparq/configs/asuris_northwest.yaml

project:
  name: "Asuris Northwest Health"
  slug: asuris_northwest

site:
  domain: asuris.healthsparq.com
  brand_code: ASURIS
  insurer_code: TBD

coverage:
  states: [WA, OR]

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m healthsparq validate asuris_northwest
python -m healthsparq run asuris_northwest --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- Part of Cambia Health Solutions family
- Reference implementation: `audiobee_wellmark/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

---
date: 2026-01-11
type: migration-plan
project: mvp_health
platform: healthsparq
status: planned
parent: ../INDEX.md
---

# MVP Health Migration Plan

Migrate `audiobee_mvp_health/` to use `healthsparq/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | MVP Health Care |
| Project Slug | `mvp_health` |
| Platform | healthsparq |
| States | NY, VT |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# healthsparq/configs/mvp_health.yaml

project:
  name: "MVP Health Care"
  slug: mvp_health

site:
  domain: mvphealthcare.healthsparq.com
  brand_code: MVP
  insurer_code: TBD

coverage:
  states: [NY, VT]

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m healthsparq validate mvp_health
python -m healthsparq run mvp_health --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- Northeast regional health plan
- Multi-state coverage (NY, VT)
- Reference implementation: `audiobee_wellmark/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

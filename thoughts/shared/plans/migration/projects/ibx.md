---
date: 2026-01-11
type: migration-plan
project: ibx
platform: healthsparq
status: planned
parent: ../INDEX.md
---

# Independence Blue Cross (IBX) Migration Plan

Migrate `audiobee_ibx/` to use `healthsparq/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Independence Blue Cross |
| Project Slug | `ibx` |
| Platform | healthsparq |
| States | PA |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Analysis

### Platform Indicators

- Platform: HealthSparq (confirmed)
- Domain: ibx.healthsparq.com
- Brand Code: IBX
- Insurer Code: TBD

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# healthsparq/configs/ibx.yaml

project:
  name: "Independence Blue Cross"
  slug: ibx

site:
  domain: ibx.healthsparq.com
  brand_code: IBX
  insurer_code: TBD

coverage:
  states: [PA]

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m healthsparq validate ibx
python -m healthsparq run ibx --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- Philadelphia area focus
- Reference implementation: `audiobee_wellmark/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

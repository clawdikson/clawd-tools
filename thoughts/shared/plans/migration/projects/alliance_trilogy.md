---
date: 2026-01-11
type: migration-plan
project: alliance_trilogy
platform: healthsparq
status: planned
parent: ../INDEX.md
---

# Alliance Trilogy Migration Plan

Migrate `audiobee_alliance_trilogy/` to use `healthsparq/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Alliance Trilogy |
| Project Slug | `alliance_trilogy` |
| Platform | healthsparq |
| States | TBD |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Analysis

### Platform Indicators

- Platform: HealthSparq (confirmed)
- Domain: TBD (extract from legacy)
- Brand Code: TBD
- Insurer Code: TBD

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# healthsparq/configs/alliance_trilogy.yaml

project:
  name: "Alliance Trilogy"
  slug: alliance_trilogy

site:
  domain: TBD
  brand_code: TBD
  insurer_code: TBD

coverage:
  states: []  # TBD

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m healthsparq validate alliance_trilogy
python -m healthsparq run alliance_trilogy --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- Need to extract state coverage from legacy code
- Reference implementation: `audiobee_wellmark/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

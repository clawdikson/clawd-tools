---
date: 2026-01-11
type: migration-plan
project: hma
platform: healthsparq
status: planned
parent: ../INDEX.md
---

# HMA Migration Plan

Migrate `audiobee_hma/` to use `healthsparq/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | HMA |
| Project Slug | `hma` |
| Platform | healthsparq |
| States | TBD |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# healthsparq/configs/hma.yaml

project:
  name: "HMA"
  slug: hma

site:
  domain: TBD
  brand_code: HMA
  insurer_code: TBD

coverage:
  states: []  # TBD

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m healthsparq validate hma
python -m healthsparq run hma --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- Need to identify state coverage from legacy code
- Reference implementation: `audiobee_wellmark/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

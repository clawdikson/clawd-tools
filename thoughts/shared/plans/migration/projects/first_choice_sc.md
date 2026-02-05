---
date: 2026-01-11
type: migration-plan
project: first_choice_sc
platform: healthsparq
status: planned
parent: ../INDEX.md
---

# First Choice SC Migration Plan

Migrate `audiobee_first_choice_sc/` to use `healthsparq/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | First Choice Health |
| Project Slug | `first_choice_sc` |
| Platform | healthsparq |
| States | SC |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# healthsparq/configs/first_choice_sc.yaml

project:
  name: "First Choice Health"
  slug: first_choice_sc

site:
  domain: TBD
  brand_code: FIRSTCHOICE
  insurer_code: TBD

coverage:
  states: [SC]

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m healthsparq validate first_choice_sc
python -m healthsparq run first_choice_sc --curr $(date +%Y%m%d) --dry-run
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

---
date: 2026-01-11
type: migration-plan
project: maine_community_health_options
platform: healthsparq
status: planned
parent: ../INDEX.md
---

# Maine Community Health Options Migration Plan

Migrate `audiobee_maine_community_health_options/` to use `healthsparq/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Maine Community Health Options |
| Project Slug | `maine_community_health_options` |
| Platform | healthsparq |
| States | ME |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# healthsparq/configs/maine_community_health_options.yaml

project:
  name: "Maine Community Health Options"
  slug: maine_community_health_options

site:
  domain: TBD
  brand_code: MCHO
  insurer_code: TBD

coverage:
  states: [ME]

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m healthsparq validate maine_community_health_options
python -m healthsparq run maine_community_health_options --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- Small state, single state coverage
- Reference implementation: `audiobee_wellmark/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

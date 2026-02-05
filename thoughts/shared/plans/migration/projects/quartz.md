---
date: 2026-01-11
type: migration-plan
project: quartz
platform: healthsparq
status: planned
parent: ../INDEX.md
---

# Quartz Migration Plan

Migrate `audiobee_quartz/` to use `healthsparq/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Quartz Health Solutions |
| Project Slug | `quartz` |
| Platform | healthsparq |
| States | WI |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# healthsparq/configs/quartz.yaml

project:
  name: "Quartz Health Solutions"
  slug: quartz

site:
  domain: quartz.healthsparq.com
  brand_code: QUARTZ
  insurer_code: TBD

coverage:
  states: [WI]

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m healthsparq validate quartz
python -m healthsparq run quartz --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- Wisconsin-based insurer
- Reference implementation: `audiobee_wellmark/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

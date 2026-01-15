---
date: 2026-01-11
type: migration-plan
project: wellmark_medicare
platform: healthsparq
status: planned
parent: ../INDEX.md
---

# Wellmark Medicare Migration Plan

Migrate `audiobee_wellmark_medicare/` to use `healthsparq/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Wellmark Medicare |
| Project Slug | `wellmark_medicare` |
| Platform | healthsparq |
| States | IA, SD |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# healthsparq/configs/wellmark_medicare.yaml

project:
  name: "Wellmark Medicare"
  slug: wellmark_medicare

site:
  domain: wellmark.healthsparq.com
  brand_code: WELLMARK
  insurer_code: WMRK_M  # Medicare variant

plans:
  - product_code: MA
    name: "Medicare Advantage"

coverage:
  states: [IA, SD]

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m healthsparq validate wellmark_medicare
python -m healthsparq run wellmark_medicare --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- Related to `audiobee_wellmark` (already migrated)
- Medicare Advantage product variant
- Same domain, different product codes
- Reference implementation: `audiobee_wellmark/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

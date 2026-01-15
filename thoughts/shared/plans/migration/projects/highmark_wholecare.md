---
date: 2026-01-11
type: migration-plan
project: highmark_wholecare
platform: healthsparq
status: planned
parent: ../INDEX.md
---

# Highmark Wholecare Migration Plan

Migrate `audiobee_highmark_wholecare/` to use `healthsparq/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Highmark Wholecare |
| Project Slug | `highmark_wholecare` |
| Platform | healthsparq |
| States | PA |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# healthsparq/configs/highmark_wholecare.yaml

project:
  name: "Highmark Wholecare"
  slug: highmark_wholecare

site:
  domain: TBD
  brand_code: HIGHMARK_WHOLECARE
  insurer_code: TBD

coverage:
  states: [PA]

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m healthsparq validate highmark_wholecare
python -m healthsparq run highmark_wholecare --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- Part of Highmark family (also see capital_blue)
- Reference implementation: `audiobee_wellmark/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

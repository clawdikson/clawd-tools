---
date: 2026-01-11
type: migration-plan
project: sentara
platform: healthsparq
status: planned
parent: ../INDEX.md
---

# Sentara Migration Plan

Migrate `audiobee_sentara/` to use `healthsparq/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Sentara Health Plans |
| Project Slug | `sentara` |
| Platform | healthsparq |
| States | VA |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# healthsparq/configs/sentara.yaml

project:
  name: "Sentara Health Plans"
  slug: sentara

site:
  domain: sentara.healthsparq.com
  brand_code: SENTARA
  insurer_code: TBD

coverage:
  states: [VA]

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m healthsparq validate sentara
python -m healthsparq run sentara --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- Virginia-based health system
- Reference implementation: `audiobee_wellmark/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

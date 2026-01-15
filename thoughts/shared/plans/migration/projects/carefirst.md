---
date: 2026-01-11
type: migration-plan
project: carefirst
platform: sapphire
status: planned
parent: ../INDEX.md
---

# CareFirst Migration Plan

Migrate `audiobee_carefirst/` to use `sapphire/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | CareFirst BlueCross BlueShield |
| Project Slug | `carefirst` |
| Platform | sapphire (PFO) |
| States | MD, DC, VA |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# sapphire/configs/carefirst.yaml

project:
  name: "CareFirst BlueCross BlueShield"
  slug: carefirst

site:
  base_url: https://pfo.carefirst.com
  api_version: v2
  tenant_id: TBD

coverage:
  states: [MD, DC, VA]
  geo_strategy: complete

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m sapphire validate carefirst
python -m sapphire run carefirst --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- Mid-Atlantic region (DC metro area)
- Multi-state coverage
- Reference implementation: `audiobee_bcbs_il/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

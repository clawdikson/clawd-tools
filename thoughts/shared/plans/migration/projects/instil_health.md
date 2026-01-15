---
date: 2026-01-11
type: migration-plan
project: instil_health
platform: sapphire
status: planned
parent: ../INDEX.md
---

# Instil Health Migration Plan

Migrate `audiobee_instil_health/` to use `sapphire/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Instil Health |
| Project Slug | `instil_health` |
| Platform | sapphire (PFO) |
| States | TBD |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# sapphire/configs/instil_health.yaml

project:
  name: "Instil Health"
  slug: instil_health

site:
  base_url: TBD
  api_version: v2
  tenant_id: TBD

coverage:
  states: []  # TBD
  geo_strategy: complete

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m sapphire validate instil_health
python -m sapphire run instil_health --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- Need to identify state coverage from legacy code
- Reference implementation: `audiobee_bcbs_il/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

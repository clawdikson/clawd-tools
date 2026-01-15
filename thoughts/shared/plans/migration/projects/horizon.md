---
date: 2026-01-11
type: migration-plan
project: horizon
platform: sapphire
status: planned
parent: ../INDEX.md
---

# Horizon Migration Plan

Migrate `audiobee_horizon/` to use `sapphire/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Horizon Blue Cross Blue Shield |
| Project Slug | `horizon` |
| Platform | sapphire (PFO) |
| States | NJ |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# sapphire/configs/horizon.yaml

project:
  name: "Horizon Blue Cross Blue Shield"
  slug: horizon

site:
  base_url: https://pfo.horizonblue.com
  api_version: v2
  tenant_id: TBD

coverage:
  states: [NJ]
  geo_strategy: complete

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m sapphire validate horizon
python -m sapphire run horizon --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- New Jersey's largest health insurer
- Reference implementation: `audiobee_bcbs_il/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

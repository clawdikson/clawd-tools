---
date: 2026-01-11
type: migration-plan
project: bcbs_tx
platform: sapphire
status: planned
parent: ../INDEX.md
---

# BCBS Texas Migration Plan

Migrate `audiobee_bcbs_tx/` to use `sapphire/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Blue Cross Blue Shield Texas |
| Project Slug | `bcbs_tx` |
| Platform | sapphire (PFO) |
| States | TX |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# sapphire/configs/bcbs_tx.yaml

project:
  name: "Blue Cross Blue Shield Texas"
  slug: bcbs_tx

site:
  base_url: https://pfo.bcbstx.com
  api_version: v2
  tenant_id: TBD

coverage:
  states: [TX]
  geo_strategy: complete

output:
  storage_backend: sqlite

advanced:
  # Texas is large - may need batch optimizations
  batch_size: 1000
```

### Step 2: Validate and Test

```bash
python -m sapphire validate bcbs_tx
python -m sapphire run bcbs_tx --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- **Large state** - Texas has high provider volume
- May need batch processing optimizations
- Reference implementation: `audiobee_bcbs_il/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

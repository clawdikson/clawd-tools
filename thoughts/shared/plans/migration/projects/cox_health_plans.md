---
date: 2026-01-11
type: migration-plan
project: cox_health_plans
platform: sapphire
status: planned
parent: ../INDEX.md
---

# Cox Health Plans Migration Plan

Migrate `audiobee_cox_health_plans/` to use `sapphire/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Cox Health Plans |
| Project Slug | `cox_health_plans` |
| Platform | sapphire (PFO) |
| States | MO |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# sapphire/configs/cox_health_plans.yaml

project:
  name: "Cox Health Plans"
  slug: cox_health_plans

site:
  base_url: TBD
  api_version: v2
  tenant_id: TBD

coverage:
  states: [MO]
  geo_strategy: small  # Regional plan

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m sapphire validate cox_health_plans
python -m sapphire run cox_health_plans --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- Regional health system in Missouri
- May have limited coverage area
- Reference implementation: `audiobee_bcbs_il/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

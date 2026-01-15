---
date: 2026-01-11
type: migration-plan
project: uhc_individual
platform: uhc
status: blocked
parent: ../INDEX.md
---

# UHC Individual Migration Plan

Migrate `audiobee_uhc_individual/` to use unified platform library (pending creation).

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | UnitedHealthcare Individual |
| Project Slug | `uhc_individual` |
| Platform | uhc (Optum) |
| States | National |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Analysis

### Platform Indicators

- Platform: UnitedHealthcare/Optum
- Individual/ACA marketplace plans
- National coverage

### Blockers

**Requires new `uhc/` platform library** - see [core-updates.md](../core-updates.md)

---

## Migration Steps

### Step 1: Create UHC Platform Library

Before this project can migrate, need to:

1. Create `uhc/` platform library
2. Implement Optum API integration
3. Add UHCConfig to core

### Step 2: Extract Configuration

```yaml
# uhc/configs/uhc_individual.yaml (pending platform creation)

project:
  name: "UnitedHealthcare Individual"
  slug: uhc_individual

site:
  optum_api_url: https://api.optum.com
  member_type: individual

coverage:
  states: []  # National
  national: true

output:
  storage_backend: sqlite
```

### Step 3: Validate and Test

```bash
python -m uhc validate uhc_individual
python -m uhc run uhc_individual --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- **Blocked**: Requires UHC platform library creation
- ACA/Individual market
- Related projects: uhc_behavioral_health, uhc_medicaid

---

## Checklist

- [ ] **UHC platform library created**
- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

---
date: 2026-01-11
type: migration-plan
project: uhc_behavioral_health
platform: uhc
status: blocked
parent: ../INDEX.md
---

# UHC Behavioral Health Migration Plan

Migrate `audiobee_uhc_behavioral_health/` to use unified platform library (pending creation).

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | UnitedHealthcare Behavioral Health |
| Project Slug | `uhc_behavioral_health` |
| Platform | uhc (Optum) |
| States | National |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Analysis

### Platform Indicators

- Platform: UnitedHealthcare/Optum
- Behavioral health specialty network
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
# uhc/configs/uhc_behavioral_health.yaml (pending platform creation)

project:
  name: "UnitedHealthcare Behavioral Health"
  slug: uhc_behavioral_health

site:
  optum_api_url: https://api.optum.com
  member_type: behavioral

coverage:
  states: []  # National
  national: true

output:
  storage_backend: sqlite
```

### Step 3: Validate and Test

```bash
python -m uhc validate uhc_behavioral_health
python -m uhc run uhc_behavioral_health --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- **Blocked**: Requires UHC platform library creation
- Behavioral health specialty
- Related projects: uhc_individual, uhc_medicaid

---

## Checklist

- [ ] **UHC platform library created**
- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

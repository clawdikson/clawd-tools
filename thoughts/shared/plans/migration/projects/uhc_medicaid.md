---
date: 2026-01-11
type: migration-plan
project: uhc_medicaid
platform: uhc
status: blocked
parent: ../INDEX.md
---

# UHC Medicaid Migration Plan

Migrate `audiobee_uhc_medicaid/` to use unified platform library (pending creation).

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | UnitedHealthcare Medicaid |
| Project Slug | `uhc_medicaid` |
| Platform | uhc (Optum) |
| States | Multi-state |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Analysis

### Platform Indicators

- Platform: UnitedHealthcare/Optum
- Medicaid managed care
- Multi-state coverage

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
# uhc/configs/uhc_medicaid.yaml (pending platform creation)

project:
  name: "UnitedHealthcare Medicaid"
  slug: uhc_medicaid

site:
  optum_api_url: https://api.optum.com
  member_type: medicaid

coverage:
  states: []  # Multi-state Medicaid

output:
  storage_backend: sqlite
```

### Step 3: Validate and Test

```bash
python -m uhc validate uhc_medicaid
python -m uhc run uhc_medicaid --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- **Blocked**: Requires UHC platform library creation
- Medicaid managed care
- Related projects: uhc_behavioral_health, uhc_individual

---

## Checklist

- [ ] **UHC platform library created**
- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

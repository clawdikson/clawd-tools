---
date: 2026-01-11
type: migration-plan
project: amerigroup
platform: anthem
status: blocked
parent: ../INDEX.md
---

# Amerigroup Migration Plan

Migrate `audiobee_amerigroup/` to use unified platform library (pending creation).

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Amerigroup |
| Project Slug | `amerigroup` |
| Platform | anthem (SydneyHealth) |
| States | Multi-state (Medicaid) |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Analysis

### Platform Indicators

- Platform: Anthem/Wellpoint/SydneyHealth
- Part of Elevance Health (formerly Anthem)
- Medicaid managed care across multiple states

### Blockers

**Requires new `anthem/` platform library** - see [core-updates.md](../core-updates.md)

---

## Migration Steps

### Step 1: Create Anthem Platform Library

Before this project can migrate, need to:

1. Create `anthem/` platform library
2. Implement SydneyHealth API integration
3. Add AnthemConfig to core

### Step 2: Extract Configuration

```yaml
# anthem/configs/amerigroup.yaml (pending platform creation)

project:
  name: "Amerigroup"
  slug: amerigroup

site:
  sydney_health_url: https://www.sydneyhealth.com
  brand: amerigroup
  plan_type: medicaid

coverage:
  states: []  # Multi-state Medicaid

output:
  storage_backend: sqlite
```

### Step 3: Validate and Test

```bash
python -m anthem validate amerigroup
python -m anthem run amerigroup --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- **Blocked**: Requires anthem platform library creation
- High priority due to Medicaid coverage
- Related projects: anthem, blueshield_ca, elderplan, healthy_blue

---

## Checklist

- [ ] **Anthem platform library created**
- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

---
date: 2026-01-11
type: migration-plan
project: anthem
platform: anthem
status: blocked
parent: ../INDEX.md
---

# Anthem Migration Plan

Migrate `audiobee_anthem/` to use unified platform library (pending creation).

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Anthem Blue Cross Blue Shield |
| Project Slug | `anthem` |
| Platform | anthem (SydneyHealth) |
| States | Multi-state |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Analysis

### Platform Indicators

- Platform: Anthem/Wellpoint/SydneyHealth
- Part of Elevance Health
- Covers commercial, Medicare, Medicaid products

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
# anthem/configs/anthem.yaml (pending platform creation)

project:
  name: "Anthem Blue Cross Blue Shield"
  slug: anthem

site:
  sydney_health_url: https://www.sydneyhealth.com
  brand: anthem
  plan_type: commercial

coverage:
  states: []  # Multi-state

output:
  storage_backend: sqlite
```

### Step 3: Validate and Test

```bash
python -m anthem validate anthem
python -m anthem run anthem --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- **Blocked**: Requires anthem platform library creation
- Core Anthem brand
- Related projects: amerigroup, blueshield_ca, elderplan, healthy_blue

---

## Checklist

- [ ] **Anthem platform library created**
- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

---
date: 2026-01-11
type: migration-plan
project: healthy_blue
platform: anthem
status: blocked
parent: ../INDEX.md
---

# Healthy Blue Migration Plan

Migrate `audiobee_healthy_blue/` to use unified platform library (pending creation).

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Healthy Blue |
| Project Slug | `healthy_blue` |
| Platform | anthem (SydneyHealth) |
| States | Multi-state (Medicaid) |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Analysis

### Platform Indicators

- Platform: Anthem/Wellpoint/SydneyHealth
- Medicaid managed care brand
- Joint venture with Anthem/Elevance

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
# anthem/configs/healthy_blue.yaml (pending platform creation)

project:
  name: "Healthy Blue"
  slug: healthy_blue

site:
  sydney_health_url: https://www.sydneyhealth.com
  brand: healthyblue
  plan_type: medicaid

coverage:
  states: []  # Multi-state Medicaid

output:
  storage_backend: sqlite
```

### Step 3: Validate and Test

```bash
python -m anthem validate healthy_blue
python -m anthem run healthy_blue --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- **Blocked**: Requires anthem platform library creation
- Medicaid focus
- Related projects: amerigroup, anthem, blueshield_ca, elderplan

---

## Checklist

- [ ] **Anthem platform library created**
- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

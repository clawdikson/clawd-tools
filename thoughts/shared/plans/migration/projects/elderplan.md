---
date: 2026-01-11
type: migration-plan
project: elderplan
platform: anthem
status: blocked
parent: ../INDEX.md
---

# Elderplan Migration Plan

Migrate `audiobee_elderplan/` to use unified platform library (pending creation).

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Elderplan |
| Project Slug | `elderplan` |
| Platform | anthem (SydneyHealth) |
| States | NY |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Analysis

### Platform Indicators

- Platform: Anthem/Wellpoint/SydneyHealth
- Medicare Advantage focus
- New York metropolitan area

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
# anthem/configs/elderplan.yaml (pending platform creation)

project:
  name: "Elderplan"
  slug: elderplan

site:
  sydney_health_url: https://www.sydneyhealth.com
  brand: elderplan
  plan_type: medicare

coverage:
  states: [NY]

output:
  storage_backend: sqlite
```

### Step 3: Validate and Test

```bash
python -m anthem validate elderplan
python -m anthem run elderplan --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- **Blocked**: Requires anthem platform library creation
- Medicare Advantage product
- Related projects: amerigroup, anthem, blueshield_ca, healthy_blue

---

## Checklist

- [ ] **Anthem platform library created**
- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

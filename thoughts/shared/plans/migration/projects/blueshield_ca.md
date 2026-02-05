---
date: 2026-01-11
type: migration-plan
project: blueshield_ca
platform: anthem
status: blocked
parent: ../INDEX.md
---

# Blue Shield of California Migration Plan

Migrate `audiobee_blueshield_ca/` to use unified platform library (pending creation).

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Blue Shield of California |
| Project Slug | `blueshield_ca` |
| Platform | anthem (SydneyHealth) |
| States | CA |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Analysis

### Platform Indicators

- Platform: Anthem/Wellpoint/SydneyHealth (confirmed)
- California-only coverage
- Large state, high provider volume

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
# anthem/configs/blueshield_ca.yaml (pending platform creation)

project:
  name: "Blue Shield of California"
  slug: blueshield_ca

site:
  sydney_health_url: https://www.sydneyhealth.com
  brand: blueshieldca
  plan_type: commercial

coverage:
  states: [CA]

output:
  storage_backend: sqlite

advanced:
  # California is large - needs optimizations
  batch_size: 1000
```

### Step 3: Validate and Test

```bash
python -m anthem validate blueshield_ca
python -m anthem run blueshield_ca --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- **Blocked**: Requires anthem platform library creation
- **Large volume**: California has high provider counts
- Related variants: blueshield_ca_server, blueshield_ca-new

---

## Checklist

- [ ] **Anthem platform library created**
- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

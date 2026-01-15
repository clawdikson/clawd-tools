---
date: 2026-01-11
type: migration-plan
project: molina
platform: sapphire
status: planned
parent: ../INDEX.md
---

# Molina Migration Plan

Migrate `audiobee_molina/` to use `sapphire/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Molina Healthcare |
| Project Slug | `molina` |
| Platform | sapphire (PFO) |
| States | Multi-state (National) |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Analysis

### Platform Indicators

- Platform: Sapphire/ProviderFinderOnline (confirmed)
- Base URL: pfo.molinahealthcare.com
- **National scope** - operates in multiple states

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# sapphire/configs/molina.yaml

project:
  name: "Molina Healthcare"
  slug: molina

site:
  base_url: https://pfo.molinahealthcare.com
  api_version: v2
  tenant_id: TBD

coverage:
  states: []  # Multiple - extract from legacy
  geo_strategy: dual  # National scope needs dual strategy

output:
  storage_backend: sqlite

advanced:
  # Large national plan - needs optimizations
  batch_size: 1000
  concurrent_requests: 10
  checkpoint_enabled: true
```

### Step 2: Validate and Test

```bash
python -m sapphire validate molina
python -m sapphire run molina --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- **High complexity**: National Medicaid managed care
- Operates in CA, FL, MI, NM, NY, OH, PR, SC, TX, WA, WI, and more
- May need state-by-state processing
- Reference implementation: `audiobee_bcbs_il/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

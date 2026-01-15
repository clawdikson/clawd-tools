---
date: 2026-01-11
type: migration-plan
project: florida_blue
platform: healthsparq
status: planned
parent: ../INDEX.md
---

# Florida Blue Migration Plan

Migrate `audiobee_florida_blue/` to use `healthsparq/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Florida Blue |
| Project Slug | `florida_blue` |
| Platform | healthsparq |
| States | FL |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Analysis

### Platform Indicators

- Platform: HealthSparq (confirmed)
- Domain: floridablue.healthsparq.com
- Brand Code: FLORIDABLUE
- Insurer Code: TBD

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# healthsparq/configs/florida_blue.yaml

project:
  name: "Florida Blue"
  slug: florida_blue

site:
  domain: floridablue.healthsparq.com
  brand_code: FLORIDABLUE
  insurer_code: TBD

coverage:
  states: [FL]

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m healthsparq validate florida_blue
python -m healthsparq run florida_blue --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- Large state coverage (FL only but high volume)
- Reference implementation: `audiobee_wellmark/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

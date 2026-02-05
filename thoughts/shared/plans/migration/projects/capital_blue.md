---
date: 2026-01-11
type: migration-plan
project: capital_blue
platform: healthsparq
status: planned
parent: ../INDEX.md
---

# Capital Blue Migration Plan

Migrate `audiobee_capital_blue/` to use `healthsparq/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Capital Blue |
| Project Slug | `capital_blue` |
| Platform | healthsparq |
| States | PA |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Analysis

### Platform Indicators

- Platform: HealthSparq (confirmed)
- Domain: capitalblue.healthsparq.com
- Brand Code: CAPITALBLUE
- Insurer Code: TBD

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# healthsparq/configs/capital_blue.yaml

project:
  name: "Capital Blue"
  slug: capital_blue

site:
  domain: capitalblue.healthsparq.com
  brand_code: CAPITALBLUE
  insurer_code: TBD

coverage:
  states: [PA]

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m healthsparq validate capital_blue
python -m healthsparq run capital_blue --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- Part of Highmark family
- Reference implementation: `audiobee_wellmark/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

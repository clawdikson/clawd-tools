---
date: 2026-01-11
type: migration-plan
project: bluecard_national
platform: healthsparq
status: planned
parent: ../INDEX.md
---

# BlueCard National Migration Plan

Migrate `audiobee_bluecard_national/` to use `healthsparq/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | BlueCard National |
| Project Slug | `bluecard_national` |
| Platform | healthsparq |
| States | National (all states) |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Analysis

### Platform Indicators

- Platform: HealthSparq (confirmed)
- Domain: bluecard.healthsparq.com (likely)
- Brand Code: BLUECARD
- **National scope** - largest coverage area

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# healthsparq/configs/bluecard_national.yaml

project:
  name: "BlueCard National"
  slug: bluecard_national

site:
  domain: bluecard.healthsparq.com
  brand_code: BLUECARD
  insurer_code: TBD

coverage:
  states: []  # National - all states
  national: true

output:
  storage_backend: sqlite

advanced:
  # May need special handling for national scope
  batch_size: 1000
  concurrent_searches: 10
```

### Step 2: Validate and Test

```bash
python -m healthsparq validate bluecard_national
python -m healthsparq run bluecard_national --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- **High complexity**: National scope means all 50 states
- May need batch processing enhancements
- Reference implementation: `audiobee_wellmark/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

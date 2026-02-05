---
date: 2026-01-11
type: migration-plan
project: medical_mutual
platform: healthsparq
status: planned
parent: ../INDEX.md
---

# Medical Mutual Migration Plan

Migrate `audiobee_medical_mutual/` to use `healthsparq/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Medical Mutual |
| Project Slug | `medical_mutual` |
| Platform | healthsparq |
| States | OH |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# healthsparq/configs/medical_mutual.yaml

project:
  name: "Medical Mutual"
  slug: medical_mutual

site:
  domain: medicalmutual.healthsparq.com
  brand_code: MEDMUTUAL
  insurer_code: TBD

coverage:
  states: [OH]

output:
  storage_backend: sqlite
```

### Step 2: Validate and Test

```bash
python -m healthsparq validate medical_mutual
python -m healthsparq run medical_mutual --curr $(date +%Y%m%d) --dry-run
```

---

## Notes

- Ohio-based insurer
- Reference implementation: `audiobee_wellmark/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived

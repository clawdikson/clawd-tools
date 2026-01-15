---
date: 2026-01-11
type: migration-plan
project: medica
platform: healthsparq
status: planned
parent: ../INDEX.md
---

# Medica Migration Plan

Migrate `audiobee_medica/` to use `healthsparq/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Medica |
| Project Slug | `medica` |
| Platform | healthsparq |
| States | MN, WI, ND, SD |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Analysis

### Current Implementation

**Location**: `audiobee_medica/`

### Platform Indicators

- Platform: HealthSparq (confirmed)
- Domain: medica.healthsparq.com
- Brand Code: MEDICA
- Insurer Code: TBD (extract from legacy)

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# healthsparq/configs/medica.yaml

project:
  name: "Medica"
  slug: medica

site:
  domain: medica.healthsparq.com
  brand_code: MEDICA
  insurer_code: TBD

plans:
  # Extract from legacy code

coverage:
  states: [MN, WI, ND, SD]

output:
  storage_backend: sqlite
```

### Step 2: Validate Configuration

```bash
python -m healthsparq validate medica
```

### Step 3: Test Dry Run

```bash
python -m healthsparq run medica --curr $(date +%Y%m%d) --dry-run
```

### Step 4: Compare Output

- [ ] Run legacy scraper
- [ ] Run library scraper
- [ ] Compare provider counts

### Step 5: Archive Legacy

```bash
mv audiobee_medica archive/audiobee_medica
```

---

## Notes

- Related project: `audiobee_medica_sg` (same platform)
- Reference implementation: `audiobee_wellmark/`

---

## Checklist

- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived
- [ ] INDEX.md updated

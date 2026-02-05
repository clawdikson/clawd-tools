---
date: 2026-01-11
type: migration-plan
project: medica_sg
platform: healthsparq
status: planned
parent: ../INDEX.md
---

# Medica SG Migration Plan

Migrate `audiobee_medica_sg/` to use `healthsparq/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | Medica SG |
| Project Slug | `medica_sg` |
| Platform | healthsparq |
| States | MN, WI, ND, SD |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Analysis

### Current Implementation

**Location**: `audiobee_medica_sg/`

**Key Files**:
- [ ] `run.py` / `main.py` - Entry point
- [ ] `scraper.py` - Core scraping logic
- [ ] `config.py` - Configuration
- [ ] `mapper.py` - Data transformation (if custom)

### Platform Indicators

- Platform: HealthSparq (confirmed)
- Domain: medica.healthsparq.com
- Brand Code: MEDICA
- Insurer Code: TBD (extract from legacy)

---

## Migration Steps

### Step 1: Extract Configuration

```yaml
# healthsparq/configs/medica_sg.yaml

project:
  name: "Medica SG"
  slug: medica_sg

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
python -m healthsparq validate medica_sg
```

### Step 3: Test Dry Run

```bash
python -m healthsparq run medica_sg --curr $(date +%Y%m%d) --dry-run
```

### Step 4: Compare Output

- [ ] Run legacy scraper
- [ ] Run library scraper
- [ ] Compare provider counts
- [ ] Compare field coverage

### Step 5: Archive Legacy

```bash
mv audiobee_medica_sg archive/audiobee_medica_sg
```

---

## Notes

- Related project: `audiobee_medica` (same platform, different product line)
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

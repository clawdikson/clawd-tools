---
date: 2026-01-11
type: migration-plan
project: {PROJECT_SLUG}
platform: {PLATFORM}
status: planned
parent: ../INDEX.md
---

# {PROJECT_NAME} Migration Plan

Migrate `audiobee_{PROJECT_SLUG}/` to use `{PLATFORM}/` library.

## Project Overview

| Property | Value |
|----------|-------|
| Project Name | {PROJECT_NAME} |
| Project Slug | `{PROJECT_SLUG}` |
| Platform | {PLATFORM} |
| States | {STATES} |
| Current Status | Legacy |
| Target Status | Library-based |

---

## Analysis

### Current Implementation

**Location**: `audiobee_{PROJECT_SLUG}/`

**Key Files**:
- [ ] `run.py` / `main.py` - Entry point
- [ ] `scraper.py` - Core scraping logic
- [ ] `config.py` - Configuration
- [ ] `mapper.py` - Data transformation (if custom)

**Dependencies**:
- [ ] List dependencies from requirements.txt/pyproject.toml

### Platform Indicators

- [ ] Confirm platform type: {PLATFORM}
- [ ] Identify domain/base URL
- [ ] Identify brand/tenant codes
- [ ] Identify network/plan codes

---

## Migration Steps

### Step 0: Create Migration Branch

```bash
git checkout -b migrate/{PROJECT_SLUG}
```

### Step 1: Extract Configuration

```yaml
# {PLATFORM}/configs/{PROJECT_SLUG}.yaml
# TODO: Extract from legacy code

project:
  name: "{PROJECT_NAME}"
  slug: {PROJECT_SLUG}

site:
  # TODO: Extract from legacy scraper

plans:
  # TODO: Extract plan/network codes

coverage:
  states: {STATES}
```

### Step 2: Validate Configuration

```bash
python -m {PLATFORM} validate {PROJECT_SLUG}
```

### Step 3: Test Dry Run

```bash
python -m {PLATFORM} run {PROJECT_SLUG} --curr $(date +%Y%m%d) --dry-run
```

### Step 4: Compare Output

- [ ] Run legacy scraper
- [ ] Run library scraper
- [ ] Compare provider counts
- [ ] Compare field coverage
- [ ] Verify NPI accuracy

### Step 5: Create Thin Wrapper (Optional)

If custom logic needed:

```python
# audiobee_{PROJECT_SLUG}/run.py
from {PLATFORM} import run_scraper_sync, load_config
from mapper import map_provider  # If custom

config = load_config("{PROJECT_SLUG}")
result = run_scraper_sync(config, curr_date, mapper=map_provider)
```

### Step 6: Archive Legacy

```bash
# After validation
mv audiobee_{PROJECT_SLUG} archive/audiobee_{PROJECT_SLUG}
```

### Step 7: Merge Migration Branch

```bash
git add .
git commit -m "migrate({PROJECT_SLUG}): complete migration to {PLATFORM} library"
git checkout master
git merge migrate/{PROJECT_SLUG}
git branch -d migrate/{PROJECT_SLUG}
```

### Rollback (If Needed)

```bash
# Revert the merge commit
git revert HEAD

# Restore legacy code
mv archive/audiobee_{PROJECT_SLUG} audiobee_{PROJECT_SLUG}
```

---

## Blockers

- [ ] None identified

---

## Notes

- Reference implementation: `audiobee_{REFERENCE_PROJECT}/`

---

## Checklist

- [ ] Migration branch created (`migrate/{PROJECT_SLUG}`)
- [ ] Configuration extracted
- [ ] YAML config created
- [ ] Config validates
- [ ] Dry run succeeds
- [ ] Output comparison passes
- [ ] Legacy archived to `archive/`
- [ ] Migration branch merged to master
- [ ] INDEX.md updated

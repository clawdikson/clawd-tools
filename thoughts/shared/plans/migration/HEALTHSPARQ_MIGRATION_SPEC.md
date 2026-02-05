# HealthSparq Migration Specification

**Generated from interview session: 2026-01-14**

## Overview

Migrate all HealthSparq-type projects to the new library-based structure using `audiobee_christus_health_plan` as reference.

## Scope

### Projects to Migrate (from projects.yaml site_type: healthsparq)

1. audiobee_alliance_trilogy
2. audiobee_amerihealth_administrators_pa
3. audiobee_amerihealth_caritas_vip_de
4. audiobee_amerihealth_nj
5. audiobee_asuris_northwest
6. audiobee_bluecard_national
7. audiobee_capital_blue
8. audiobee_excellus
9. audiobee_first_choice_sc
10. audiobee_health_plan_nv_medicaid
11. audiobee_highmark_wholecare
12. audiobee_hma
13. audiobee_ibx
14. audiobee_maine_community_health_options
15. audiobee_mass_gen
16. audiobee_medica
17. audiobee_medica_sg
18. audiobee_medical_mutual
19. audiobee_mvp_health
20. audiobee_quartz
21. audiobee_sentara
22. audiobee_tufts_health_plans
23. audiobee_wellmark_medicare

### Projects to SKIP (Already Migrated)

- audiobee_christus_health_plan
- audiobee_wellmark

**Note**: bcbs_il and bcbs_mt are Sapphire, not HealthSparq.

---

## Migration Decisions (Interview Results)

| Decision | Choice |
|----------|--------|
| **Mapper scope** | Project-local mapper.py - each project gets its own |
| **File cleanup** | Delete all unnecessary files (only keep config.yaml, mapper.py, run.py, pyproject.toml, CLAUDE.md) |
| **Git structure** | Per-project branches - create `feature/core-migration` in each project's own repo |
| **Parallelism** | All concurrent - spawn all 23 agents simultaneously |
| **Mapper style** | Analyze & decide per project - compare index_3 with default_mapper |
| **Config location** | Sync both - project config.yaml + healthsparq/configs/*.yaml |
| **PR creation** | Branch only - just push, manual PR creation later |
| **Edge cases** | Create minimal scaffold with comments + error tag file if project doesn't fit pattern |
| **CLI pattern** | Thin wrapper using create_project_cli() (~20 lines) |
| **Skip migrated** | Skip already migrated projects |
| **Commit format** | Conventional commits style |

---

## Target Structure Per Project

```
audiobee_{project}/
├── config.yaml           # Project config (synced with healthsparq/configs/)
├── mapper.py             # Custom mapper extracted from index_3.py
├── run.py                # Thin wrapper using create_project_cli()
├── pyproject.toml        # Python packaging (optional)
├── .gitignore            # Standard gitignore
├── CLAUDE.md             # Updated project documentation
└── [MIGRATION_ERROR.txt] # Only if migration had issues (edge case marker)
```

---

## Files to DELETE

Remove all legacy files including but not limited to:
- index_1.py, index_2.py, index_3.py
- config.py
- healthspark.py
- browser_pool.py, browser_session.py
- run_all.py
- compare_and_download_old_npi_4.py
- data_address_level.py
- get_per_state_counts.py, get_per_state_scraped.py
- jsonl_drop_checker.py, jsonl_searcher.py
- remove_error_file.py
- add_*_to_network_names_*.py
- import_random.py
- test.py
- uszips.xlsx
- uv.lock (will be regenerated)
- old_code/ directory
- logger/ directory
- Any other Python files not in target structure
- README.md (replaced by CLAUDE.md)

**Keep**:
- .git/ directory (this is the project's own repo)
- .env (may contain project-specific secrets)
- .env.example
- .python-version
- YYYYMMDD/ directories (output data - do not delete)

---

## Mapper Extraction Logic

For each project, the agent should:

1. **Read index_3.py** and identify these functions:
   - `get_network_names(data)`
   - `get_provider_data(data)`
   - `get_addresses(data)`
   - `get_group_affiliations(data)`
   - `get_hospital_affiliations(data)`
   - `get_specialties(data)`
   - `map_json_to_schema(data)`

2. **Compare with default_mapper** in healthsparq library:
   - If implementation is identical/similar: use `from healthsparq import default_mapper` and just call it
   - If implementation differs significantly: copy the relevant functions to mapper.py

3. **Create mapper.py** with pattern:
```python
"""Custom mapper for {Project Name}.

Extracted from legacy index_3.py during migration.
"""
from healthsparq import default_mapper

def map_provider(raw: dict) -> dict:
    """Custom mapper for {Project Name}."""
    # If default works:
    return default_mapper(raw)

    # OR if custom logic needed:
    # return custom_map_json_to_schema(raw)
```

---

## run.py Template (Thin Wrapper)

```python
#!/usr/bin/env python
"""{{ project_name }} scraper CLI (Library-based implementation)."""
from pathlib import Path
from healthsparq.cli import create_project_cli
from mapper import map_provider

app = create_project_cli(
    project_dir=Path(__file__).parent,
    mapper=map_provider,
)

if __name__ == "__main__":
    app()
```

---

## config.yaml Template

```yaml
site_type: healthsparq

project:
  name: {{ Project Name }}
  slug: {{ project_slug }}
  description: {{ Description from config.py }}
  version: "1.0"

site:
  domain: {{ domain from config.py }}
  brand_code: {{ BRAND_CODE from config.py }}
  insurer_code: {{ INSURER_CODE from config.py }}
  api_version: v4

plans:
  # Copy from config.py PLANS list
  - product_code: {{ product_code }}
    name: {{ plan name }}

coverage:
  states:
    # Copy from config.py STATE_ABBR_LIST
    - {{ state }}

concurrency:
  max_workers: 25
  max_browsers: 25
```

---

## CLAUDE.md Template

```markdown
# {{ Project Name }}

**Migrated to healthsparq library pattern (2026-01-14)**

## Quick Start

\`\`\`bash
# Run via library CLI (recommended)
python -m healthsparq run {{ project_slug }} --curr $(date +%Y%m%d)

# Or run via project CLI
cd audiobee_{{ project_slug }}
python run.py run --curr $(date +%Y%m%d)
\`\`\`

## Project Metadata

- **Project Name**: {{ Project Name }}
- **Project Slug**: {{ project_slug }}
- **State Coverage**: {{ states }}
- **Line of Coverage**: {{ coverage types }}
- **Site Type**: HealthSparq
- **Status**: Active

## Custom Mapper

This project uses a custom mapper in `mapper.py` extracted from the legacy `index_3.py`.
Key differences from default mapper:
- {{ list differences or "Uses default mapper" }}

## Output Structure

\`\`\`
YYYYMMDD/
├── raw/
│   ├── search_results.db      # Phase 1: Search results
│   └── provider_details.db    # Phase 2: Provider details
└── processed/
    └── {{ project_slug }}-YYYYMMDD.jsonl  # Phase 3: Normalized output
\`\`\`
```

---

## Git Workflow Per Project

```bash
# 1. Navigate to project directory
cd audiobee_{{ project_slug }}

# 2. Create feature branch
git checkout -b feature/core-migration

# 3. Delete legacy files (keeping .git, .env, data dirs)
# ... file deletion ...

# 4. Create new files
# ... create config.yaml, mapper.py, run.py, CLAUDE.md ...

# 5. Sync config to library (if not exists)
# Copy config.yaml to healthsparq/configs/{{ project_slug }}.yaml

# 6. Add and commit
git add -A
git commit -m "feat(migration): migrate to healthsparq library pattern

- Extract custom mapper from index_3.py to mapper.py
- Add thin wrapper run.py using create_project_cli()
- Create config.yaml (synced with healthsparq/configs/)
- Update CLAUDE.md with new usage instructions
- Remove legacy pipeline files

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

# 7. Push to remote
git push -u origin feature/core-migration
```

---

## Edge Case Handling

If a project doesn't have index_3.py or has unexpected structure:

1. Create minimal scaffold (config.yaml, run.py, mapper.py with default_mapper)
2. Add comment in mapper.py: `# TODO: Manual review needed - no index_3.py found`
3. Create `MIGRATION_ERROR.txt` with details:
   ```
   Migration Date: 2026-01-14
   Issue: No index_3.py found / Unexpected structure
   Action Needed: Manual review of legacy code to extract mapper logic
   Files Checked: [list of files examined]
   ```

---

## Verification Checklist

After migration, each project should pass:

- [ ] `python run.py validate` succeeds
- [ ] `python -m healthsparq validate {{ project_slug }}` succeeds
- [ ] config.yaml exists in project directory
- [ ] config.yaml synced to healthsparq/configs/
- [ ] mapper.py exists with map_provider function
- [ ] run.py exists with thin wrapper pattern
- [ ] CLAUDE.md updated
- [ ] No legacy .py files remain (except run.py, mapper.py)
- [ ] Git branch feature/core-migration created and pushed

---

## Agent Assignment

Spawn 23 kraken agents in parallel, one per project:

| Agent | Project |
|-------|---------|
| 1 | audiobee_alliance_trilogy |
| 2 | audiobee_amerihealth_administrators_pa |
| 3 | audiobee_amerihealth_caritas_vip_de |
| 4 | audiobee_amerihealth_nj |
| 5 | audiobee_asuris_northwest |
| 6 | audiobee_bluecard_national |
| 7 | audiobee_capital_blue |
| 8 | audiobee_excellus |
| 9 | audiobee_first_choice_sc |
| 10 | audiobee_health_plan_nv_medicaid |
| 11 | audiobee_highmark_wholecare |
| 12 | audiobee_hma |
| 13 | audiobee_ibx |
| 14 | audiobee_maine_community_health_options |
| 15 | audiobee_mass_gen |
| 16 | audiobee_medica |
| 17 | audiobee_medica_sg |
| 18 | audiobee_medical_mutual |
| 19 | audiobee_mvp_health |
| 20 | audiobee_quartz |
| 21 | audiobee_sentara |
| 22 | audiobee_tufts_health_plans |
| 23 | audiobee_wellmark_medicare |

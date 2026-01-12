---
date: 2026-01-11
type: migration-plan
scope: healthsparq-updates
parent: INDEX.md
---

# HealthSparq Package Updates for Migration

Required changes to `healthsparq/` to support 23 new project migrations.

## Summary

| Update | Priority | Effort | Status |
|--------|----------|--------|--------|
| Add 23 new YAML configs | High | Medium | Pending |
| Config template creation | High | Low | Pending |
| Custom mapper support | Medium | Low | Done (via MapperFunc) |
| Documentation updates | Low | Low | Pending |

---

## 1. New YAML Configs (23)

**Priority**: High
**Location**: `healthsparq/configs/`

### Config Template

Create `healthsparq/configs/_template.yaml`:

```yaml
# Template for new HealthSparq project configs
# Copy this file and rename to {project_slug}.yaml

project:
  name: "Project Name"           # Human-readable name
  slug: project_slug             # URL-safe identifier

site:
  domain: example.healthsparq.com
  brand_code: BRAND              # From HealthSparq site
  insurer_code: INSURER          # From HealthSparq site

plans:
  - product_code: MA             # Medicare Advantage
    name: "Medicare Advantage"
  # Add more plans as needed

coverage:
  states: [XX, YY]               # State abbreviations
  # counties: []                 # Optional: specific counties

search:
  min_distance_miles: 5
  max_radius_miles: 50
  # specialties: []              # Optional: filter specialties

output:
  storage_backend: sqlite        # sqlite | json_files | jsonl
  raw_subdir: raw
  processed_subdir: processed

advanced:
  v2_enabled: true               # Enable v2 API
  request_timeout: 30
  max_retries: 3
```

### Configs to Create

| Project | Config File | Domain (to discover) |
|---------|-------------|----------------------|
| `medica_sg` | `medica_sg.yaml` | medica.healthsparq.com |
| `medica` | `medica.yaml` | medica.healthsparq.com |
| `florida_blue` | `florida_blue.yaml` | floridablue.healthsparq.com |
| `capital_blue` | `capital_blue.yaml` | capitalblue.healthsparq.com |
| `ibx` | `ibx.yaml` | ibx.healthsparq.com |
| `excellus` | `excellus.yaml` | excellus.healthsparq.com |
| `tufts_health_plans` | `tufts_health_plans.yaml` | tufts.healthsparq.com |
| `amerihealth_administrators_pa` | `amerihealth_administrators_pa.yaml` | - |
| `amerihealth_caritas_fl` | `amerihealth_caritas_fl.yaml` | - |
| `amerihealth_caritas_vip_de` | `amerihealth_caritas_vip_de.yaml` | - |
| `amerihealth_nj` | `amerihealth_nj.yaml` | - |
| `alliance_trilogy` | `alliance_trilogy.yaml` | - |
| `asuris_northwest` | `asuris_northwest.yaml` | - |
| `bcbs_ne` | `bcbs_ne.yaml` | - |
| `bluecard_national` | `bluecard_national.yaml` | - |
| `first_choice_sc` | `first_choice_sc.yaml` | - |
| `health_plan_nv_medicaid` | `health_plan_nv_medicaid.yaml` | - |
| `highmark_wholecare` | `highmark_wholecare.yaml` | - |
| `hma` | `hma.yaml` | - |
| `maine_community_health_options` | `maine_community_health_options.yaml` | - |
| `medical_mutual` | `medical_mutual.yaml` | - |
| `mvp_health` | `mvp_health.yaml` | - |
| `quartz` | `quartz.yaml` | - |
| `sentara` | `sentara.yaml` | - |
| `wellmark_medicare` | `wellmark_medicare.yaml` | - |

### Config Discovery Process

For each project:

1. Read existing project code to find:
   - HealthSparq domain URL
   - Brand code and insurer code
   - Plan/product codes
   - State coverage

2. Create YAML config from template

3. Validate with `python -m healthsparq validate {project}`

---

## 2. Custom Mapper Registry

**Priority**: Medium
**Status**: Partially done (MapperFunc exists)

### Current State

Projects can inject custom mappers via `MapperFunc` parameter:

```python
result = run_scraper_sync(
    config=config,
    curr_date="20251230",
    mapper=my_custom_mapper,
)
```

### Enhancement

Add optional mapper auto-discovery from project directory:

```python
# healthsparq/phases/normalize.py

def get_project_mapper(project_slug: str) -> MapperFunc | None:
    """Try to load mapper from project directory."""
    try:
        # Check if audiobee_{project}/mapper.py exists
        import importlib
        module = importlib.import_module(f"audiobee_{project_slug}.mapper")
        if hasattr(module, "map_provider"):
            return module.map_provider
    except ImportError:
        pass
    return None
```

This would allow projects to have custom mappers without modifying the library entry point.

---

## 3. Doctor Command Enhancement

**Priority**: Low
**Location**: `healthsparq/cli.py`

### Current

`python -m healthsparq doctor` validates all configs.

### Enhancement

Add migration readiness check:

```python
@app.command()
def doctor(
    check_migration: bool = typer.Option(False, help="Check migration readiness"),
):
    """Validate all project configurations."""
    configs = list_projects()
    for config_name in configs:
        # Existing validation...

        if check_migration:
            # Check if audiobee_{config} directory exists
            # Check if it has legacy code that differs from library
            pass
```

---

## 4. Documentation Updates

**Priority**: Low

### Files to Update

| File | Updates Needed |
|------|----------------|
| `healthsparq/CLAUDE.md` | Add migration section |
| `healthsparq/README.md` | Update project list |
| `healthsparq/configs/README.md` | Document config format |

---

## Migration Checklist Per Project

For each HealthSparq project migration:

- [ ] Analyze existing `audiobee_{project}/` code
- [ ] Extract domain, brand_code, insurer_code
- [ ] Extract plan/product codes
- [ ] Extract state coverage
- [ ] Create `healthsparq/configs/{project}.yaml`
- [ ] Run `python -m healthsparq validate {project}`
- [ ] Test with `python -m healthsparq run {project} --curr YYYYMMDD --dry-run`
- [ ] Compare output with legacy scraper
- [ ] Create thin wrapper if custom mapper needed
- [ ] Archive legacy `audiobee_{project}/` directory

---

## Related Documents

- [INDEX.md](./INDEX.md) - Master migration index
- [core-updates.md](./core-updates.md) - Core package updates
- [sapphire-updates.md](./sapphire-updates.md) - Sapphire updates

---
date: 2026-01-11
type: research
scope: healthsparq
commit: 4b76867
parent: INDEX.md
---

# HealthSparq Platform Deep Dive

HealthSparq browser automation library for 23 insurance carrier projects.

## Overview

```
healthsparq/
├── __init__.py          # Public API exports
├── api.py               # run_scraper_sync() entry point
├── cli.py               # Typer CLI + create_project_cli()
├── config/
│   ├── loader.py        # load_config(), list_projects()
│   └── schema.py        # HealthSparqProjectConfig (Pydantic)
├── core/
│   ├── healthsparq_api.py  # HealthSpark API wrapper
│   ├── session.py          # Session management
│   └── storage.py          # create_phase_store()
├── phases/
│   ├── search.py        # Phase 1: County-by-county
│   ├── details.py       # Phase 2: Provider details (v1+v2)
│   ├── normalize.py     # Phase 3: NPI dedup + mapper
│   ├── qa.py            # Phase 4: Validation + comparison
│   ├── report.py        # Phase 5: Excel + samples
│   └── recovery.py      # Phase 6: Missing provider recovery
└── configs/
    └── *.yaml           # 23 project configs
```

## Phase Pipeline

```
Phase 1 (search) → Phase 2 (details) → Phase 3 (normalize) → Phase 4 (qa) → Phase 5 (report) → Phase 6 (recovery)
County-by-county   v1+v2 API fetch     NPI dedup + mapper    Validate+compare  Excel+samples    NPI/name search
```

### Phase Details

| Phase | Module | Description | Output |
|-------|--------|-------------|--------|
| 1 | `search.py` | County-by-county adaptive search | `raw/search_results/` |
| 2 | `details.py` | Provider details via v1+v2 API | `raw/provider_details/` |
| 3 | `normalize.py` | NPI deduplication, custom mapper | `processed/providers.jsonl` |
| 4 | `qa.py` | Schema validation, run comparison | Metrics |
| 5 | `report.py` | Excel reports, sample generation | Excel files |
| 6 | `recovery.py` | Missing provider recovery | `raw/recovered/` |

### Phase Control

**Default**: Phases 1-3 (core scraping)

**CLI Options**:
```bash
# Single phase
--phase 2

# Multiple phases
-p 2,3,5

# Range
-p 2-5

# From phase onwards
--from-phase 2

# Skip phase
--skip-phase 1
```

**QA/Report Flags**:
```bash
--qa              # Full QA (validation + comparison)
--validate        # Schema validation only (4a)
--compare         # Comparison only (4b)
--report          # Full report (Excel + samples)
--excel           # Excel only (5a)
--samples-only    # Samples only (5b)
--recover         # Recovery (requires --prev)
```

---

## API Entry Point

From `api.py:57-76`:

```python
def run_scraper_sync(
    config: HealthSparqProjectConfig,
    curr_date: str,
    prev_date: str | None = None,
    phases: set[int] | None = None,        # e.g., {1, 2, 3}
    mapper: MapperFunc | None = None,       # Custom normalization
    validate: bool = False,                 # JSON schema validation
    storage_backend: StorageBackend | None = None,
    run_qa: bool = False,
    run_validate: bool = False,
    run_compare: bool = False,
    run_report: bool = False,
    run_excel: bool = False,
    run_samples: bool = False,
    sample_count: int = 10,
    run_recovery: bool = False,
    recovery_search_mode: SearchMode = SearchMode.AUTO,
    include_recovered: bool = True,         # Include in Phase 3
) -> ScraperResult:
```

### Result Types

```python
@dataclass
class PhaseResult:
    phase: int
    success: bool
    message: str
    data: dict[str, Any]
    duration_seconds: float
    started_at: datetime | None
    completed_at: datetime | None

@dataclass
class ScraperResult:
    success: bool
    providers_count: int
    error: str | None
    phase_results: dict[int, PhaseResult]
    started_at: datetime | None
    completed_at: datetime | None
```

---

## Core Components

### HealthSpark API Wrapper

From `core/healthsparq_api.py`:

```python
async with HealthSpark(config) as hs:
    # Search
    results = await hs.search(location="Dallas, TX")

    # Provider details (3 methods)
    details_v1 = await hs.get_provider_details(provider_id)      # v1 only
    details_v2 = await hs.get_provider_details_v2(provider_id)   # v2 only
    details_full = await hs.get_provider_details_full(provider_id)  # Combined
```

**Combined Response** (`get_provider_details_full`):
- v1 fields at root level
- v2 data nested under `'v2'` key

### Session Management

From `core/session.py`:

Two-step pattern:
1. `ResilientBrowserSession` for login (extracts cookies)
2. `HttpSession` for fast API calls (uses extracted cookies)

### Storage Abstraction

From `core/storage.py`:

```python
from healthsparq.core.storage import create_phase_store

store = create_phase_store(
    output_dir=Path("20251230"),
    phase_name="provider_details",
    backend=StorageBackend.SQLITE,  # Default
)
```

---

## Configuration System

### YAML Structure

```yaml
# configs/christus_health_plan.yaml
project:
  name: "Christus Health Plan"
  slug: christus_health_plan

site:
  domain: christus.healthsparq.com
  brand_code: CHRISTUS
  insurer_code: CHRISTUS

plans:
  - product_code: MA
    name: "Medicare Advantage"

coverage:
  states: [TX, LA]

search:
  min_distance_miles: 5
  max_radius_miles: 50

output:
  storage_backend: sqlite
```

### Pydantic Model

From `config/schema.py`:

```python
class HealthSparqProjectConfig(BaseModel):
    project: ProjectInfo       # name, slug
    site: SiteConfig           # domain, brand_code, insurer_code
    plans: list[PlanConfig]    # product_code, name
    coverage: CoverageConfig   # states, counties
    search: SearchConfig       # min_distance, max_radius, specialties
    output: OutputConfig       # storage_backend, dirs
    advanced: AdvancedConfig   # v2_enabled, timeouts, retry
```

### Loader

From `config/loader.py`:

```python
from healthsparq.config import load_config, list_projects

# Load specific config
config = load_config("christus_health_plan")

# List all available projects
projects = list_projects()  # ['christus_health_plan', 'medica_sg', ...]
```

---

## Custom Mapper Injection

### Default Mapper

From `phases/normalize.py:450-500`:

```python
def default_mapper(raw: dict) -> dict:
    """Default map_to_schema implementation."""
    from core.mapper.healthsparq import HealthSparqMapper
    mapper = HealthSparqMapper()
    return mapper.map(raw)
```

### Factory Pattern

```python
def make_mapper(custom_logic: Callable[[dict], dict] | None = None) -> MapperFunc:
    """Factory for custom mappers that extend default."""
    def mapper(raw: dict) -> dict:
        result = default_mapper(raw)
        if custom_logic:
            result = custom_logic(result)
        return result
    return mapper
```

### Usage

```python
from healthsparq import run_scraper_sync, load_config, default_mapper

def my_mapper(raw: dict) -> dict:
    result = default_mapper(raw)
    if "custom_field" in raw:
        result["mapped_field"] = raw["custom_field"]
    return result

config = load_config("christus_health_plan")
result = run_scraper_sync(
    config=config,
    curr_date="20251227",
    mapper=my_mapper,
)
```

---

## CLI Usage

### Built-in CLI

```bash
# List projects
python -m healthsparq list

# Validate config
python -m healthsparq validate christus_health_plan

# Run scraper
python -m healthsparq run christus_health_plan --curr 20251230

# Run with options
python -m healthsparq run medica_sg \
    --curr 20251230 \
    --prev 20251130 \
    -p 2,3,5 \
    --storage sqlite \
    --qa --report

# Doctor (validate all configs)
python -m healthsparq doctor
```

### create_project_cli() Factory

Thin wrapper pattern for project-specific CLI:

```python
# audiobee_my_project/run.py
from pathlib import Path
from healthsparq.cli import create_project_cli
from mapper import my_custom_mapper

app = create_project_cli(
    project_dir=Path(__file__).parent,
    mapper=my_custom_mapper,
)

if __name__ == "__main__":
    app()
```

This provides:
- All standard `healthsparq run` options
- Project-local `config.yaml` support
- Custom mapper injection
- Custom command registration

---

## Adding a New Project

### 1. Create Config

```yaml
# healthsparq/configs/my_project.yaml
project:
  name: "My Project"
  slug: my_project

site:
  domain: mysite.healthsparq.com
  brand_code: MYCODE
  insurer_code: MYINS

plans:
  - product_code: MA
    name: "Medicare Advantage"

coverage:
  states: [TX, LA]
```

### 2. Validate

```bash
python -m healthsparq validate my_project
```

### 3. (Optional) Create Library-Based Project

```bash
mkdir audiobee_my_project && cd audiobee_my_project

# Copy templates
cp ../healthsparq/templates/run.py.template run.py
cp ../healthsparq/templates/mapper.py.template mapper.py

# Edit and run
python run.py run --curr 20251230
```

---

## Recovery Phase (Phase 6)

Unique to HealthSparq - recovers missing providers from previous runs.

### Search Modes

```python
from healthsparq.phases import SearchMode

# Auto mode (default) - tries NPI, falls back to name
SearchMode.AUTO

# NPI search only
SearchMode.NPI_ONLY

# Name search only
SearchMode.NAME_ONLY

# NPI first, name fallback
SearchMode.NPI_THEN_NAME
```

### Workflow

```bash
# 1. Run recovery
python -m healthsparq run medica_sg \
    --curr 20251230 \
    --prev 20251130 \
    --recover

# 2. Merge into JSONL (recovered included by default)
python -m healthsparq run medica_sg --curr 20251230 --phase 3

# 3. Re-run QA and report
python -m healthsparq run medica_sg \
    --curr 20251230 \
    --prev 20251130 \
    --qa --report
```

### Exclude Recovered

```bash
python -m healthsparq run medica_sg \
    --curr 20251230 \
    --phase 3 \
    --exclude-recovered
```

---

## Storage Backends

```bash
# SQLite (default, 15x faster)
python -m healthsparq run medica_sg --curr 20251230 --storage sqlite

# JSON Files (debugging)
python -m healthsparq run medica_sg --curr 20251230 --storage json_files

# JSONL (streaming)
python -m healthsparq run medica_sg --curr 20251230 --storage jsonl
```

---

## Output Structure

```
{curr_date}/
├── raw/
│   ├── search_results/       # Phase 1
│   ├── provider_details/     # Phase 2
│   └── recovered/            # Phase 6
└── processed/
    └── providers.jsonl       # Phase 3
```

---

## Testing

```bash
# All tests
pytest healthsparq/tests/ -v

# Specific test
pytest healthsparq/tests/test_config.py -v

# With coverage
pytest healthsparq/tests/ --cov=healthsparq

# Type checking
mypy healthsparq/
```

---

## Related Documents

- [INDEX.md](./INDEX.md) - Navigation
- [01-core-package.md](./01-core-package.md) - Core utilities
- [03-sapphire.md](./03-sapphire.md) - Sapphire comparison
- [04-patterns.md](./04-patterns.md) - Shared patterns

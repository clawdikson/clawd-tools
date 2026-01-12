---
date: 2026-01-11
type: research
scope: sapphire
commit: 4b76867
parent: INDEX.md
---

# Sapphire Platform Deep Dive

Sapphire (ProviderFinderOnline) scraping library for 15 insurance carrier projects.

## Overview

```
sapphire/
├── __init__.py          # Public API exports
├── api.py               # run_scraper_async/sync() entry points
├── cli.py               # Typer CLI
├── config/
│   ├── loader.py        # load_config(), list_projects()
│   └── schema.py        # SapphireProjectConfig (Pydantic)
├── core/
│   ├── sapphire_api.py  # SapphireAPI wrapper (browser-based)
│   ├── session.py       # Browser queue management
│   └── storage.py       # create_phase_store()
├── phases/
│   ├── discovery.py     # Phase 1: Geographic facet queries
│   ├── details.py       # Phase 2: 4 API calls per provider
│   ├── normalize.py     # Phase 3: NPI dedup + mapper
│   ├── qa.py            # Phase 4: Validation + comparison
│   └── report.py        # Phase 5: Excel + samples
├── mappers/
│   ├── __init__.py      # MapperFunc type
│   └── registry.py      # register_mapper(), get_mapper()
└── configs/
    ├── _base.yaml       # Default settings
    └── *.yaml           # 15 project configs
```

## Phase Pipeline

```
Phase 1 (discovery) → Phase 2 (details) → Phase 3 (normalize) → Phase 4 (qa) → Phase 5 (report)
Geo facet queries     4 API calls/provider   NPI dedup + mapper    Validate+compare  Excel+samples
```

### Phase Details

| Phase | Module | Description | Output |
|-------|--------|-------------|--------|
| 1 | `discovery.py` | Geographic facet queries (geo circles) | `raw/provider_ids_network_map.json` |
| 2 | `details.py` | 4 API calls: summary, affiliations, locations, networks | `raw/provider_details.db` |
| 3 | `normalize.py` | NPI deduplication, custom mapper | `processed/{project}-{date}.jsonl` |
| 4 | `qa.py` | Schema validation, run comparison | Metrics |
| 5 | `report.py` | Excel reports, sample generation | Excel files |

### Key Difference from HealthSparq

- **No Phase 6 (Recovery)** - Not yet implemented
- **Phase 1 uses geo strategy** instead of county-by-county search
- **Phase 2 makes 4 separate API calls** per provider (vs combined v1+v2)

---

## API Entry Point

From `api.py:59-81`:

```python
async def run_scraper_async(
    config: SapphireProjectConfig,
    curr_date: str,
    prev_date: str | None = None,
    phases: set[int] | None = None,        # e.g., {1, 2, 3}
    mapper: MapperFunc | None = None,       # Custom normalization
    storage_backend: StorageBackend | None = None,
    validate: bool = False,                 # JSON schema validation
    strict: bool = False,                   # Fail on any phase error
    run_qa: bool = False,
    run_validate: bool = False,
    run_compare: bool = False,
    run_report: bool = False,
    run_excel: bool = False,
    run_samples: bool = False,
    sample_count: int = 10,
    report_type: str = "extended",
    run_recovery: bool = False,             # Not implemented yet
    recovery_dry_run: bool = False,
) -> ScraperResult:
```

### Sync Wrapper

```python
def run_scraper_sync(...) -> ScraperResult:
    """Synchronous wrapper for run_scraper_async."""
    return asyncio.run(run_scraper_async(...))
```

### Result Types

Same as HealthSparq:

```python
@dataclass
class PhaseResult:
    phase: int
    success: bool
    message: str
    data: dict
    duration_seconds: float
    started_at: datetime | None
    completed_at: datetime | None

@dataclass
class ScraperResult:
    success: bool
    providers_count: int
    error: str | None
    phase_results: dict[int, PhaseResult]
```

---

## Core Components

### SapphireAPI Wrapper

From `core/sapphire_api.py`:

```python
async with SapphireAPI(config) as api:
    # Discovery
    provider_ids = await api.discover_providers(network_id, geo_params)

    # Details (4 API calls per provider)
    summary = await api.get_provider_summary(provider_id)
    affiliations = await api.get_provider_affiliations(provider_id)
    locations = await api.get_provider_locations(provider_id)
    networks = await api.get_provider_networks(provider_id)
```

**Browser-based**: Uses Camoufox by default for anti-bot handling.

### Browser Queue

From `core/session.py`:

```python
# Managed browser pool
queue = SapphireBrowserQueue(max_browsers=3)
async with queue.get_browser() as browser:
    response = await browser.fetch(url)
```

### Storage Abstraction

From `core/storage.py`:

```python
from sapphire.core.storage import create_phase_store

store = create_phase_store(
    output_dir=Path("20251230"),
    phase_name="provider_details",
    backend=StorageBackend.SQLITE,  # Default
)
```

---

## Configuration System

### YAML Structure with Inheritance

```yaml
# configs/_base.yaml (defaults)
geo:
  strategy: dual
  radii_miles:
    small: [25, 50]
    complete: 300
output:
  storage_backend: sqlite
  base_dir: "."
```

```yaml
# configs/molina.yaml
project:
  name: "Molina Healthcare"
  slug: molina

site:
  domain: providerfinder.molina.com

networks:
  - id: "12345"
    name: "Molina Network"

geo:
  strategy: dual  # Inherited, can override
```

### Pydantic Model

From `config/schema.py`:

```python
class SapphireProjectConfig(BaseModel):
    project: ProjectInfo       # name, slug
    site: SiteConfig           # domain, api_key
    networks: list[NetworkConfig]  # id, name
    geo: GeoConfig             # strategy, radii
    output: OutputConfig       # storage_backend
```

### Loader

From `config/loader.py`:

```python
from sapphire.config.loader import load_config, list_projects

# Load with _base.yaml merge
config = load_config("molina")

# List all projects
projects = list_projects()  # ['molina', 'bcbs_mn', ...]
```

---

## Geo Strategy

Controls how Phase 1 discovers providers.

| Strategy | Description | Use Case |
|----------|-------------|----------|
| `small` | Dense circles (25, 50 mile radii) | Urban areas |
| `complete` | State-wide (300 mile radius) | Full coverage |
| `dual` | Both small + complete | Most projects |

Configured per project:

```yaml
geo:
  strategy: dual
  radii_miles:
    small: [25, 50]
    complete: 300
```

---

## Custom Mapper System

### Registry Pattern

From `mappers/registry.py`:

```python
_MAPPERS: dict[str, MapperFunc] = {}

def register_mapper(slug: str, mapper: MapperFunc) -> None:
    """Register a project-specific mapper."""
    _MAPPERS[slug] = mapper

def get_mapper(slug: str) -> MapperFunc:
    """Get mapper for project, or default."""
    return _MAPPERS.get(slug, default_sapphire_mapper)
```

### Default Mapper

```python
def default_sapphire_mapper(raw: dict) -> dict:
    """Default transformation from PFO format to Ideon format."""
    return {
        "npi": raw.get("npi"),
        "first_name": raw.get("firstName"),
        "last_name": raw.get("lastName"),
        # ... more field mappings
    }
```

### Custom Mapper Usage

```python
from sapphire.mappers import register_mapper

def bcbs_mn_mapper(raw: dict) -> dict:
    # Custom transformation for BCBS MN
    result = default_sapphire_mapper(raw)
    result["custom_field"] = raw.get("bcbs_specific")
    return result

register_mapper("bcbs_mn", bcbs_mn_mapper)
```

---

## CLI Usage

```bash
# List projects
python -m sapphire list

# Validate config
python -m sapphire validate molina

# Run scraper (phases 1-3 by default)
python -m sapphire run molina --curr 20251230

# Run with options
python -m sapphire run molina \
    --curr 20251230 \
    --prev 20251130 \
    --phase 2 \
    --storage sqlite \
    --qa --report

# Doctor (validate all configs)
python -m sapphire doctor
```

### Phase Selection

Same syntax as HealthSparq:

```bash
--phase 2           # Single phase
-p 2,3,5            # Multiple phases
-p 2-5              # Range
--from-phase 2      # From phase onwards
--skip-phase 1      # Skip phase
```

---

## Adding a New Project

### 1. Create Config

```yaml
# sapphire/configs/my_project.yaml
project:
  name: "My Project"
  slug: my_project

site:
  domain: provider.mysite.com

networks:
  - id: "NET001"
    name: "Primary Network"

geo:
  strategy: dual
```

### 2. Validate

```bash
python -m sapphire validate my_project
```

### 3. (Optional) Register Custom Mapper

```python
# In project or sapphire/mappers/__init__.py
from sapphire.mappers import register_mapper

def my_mapper(raw: dict) -> dict:
    # Custom logic
    return {...}

register_mapper("my_project", my_mapper)
```

---

## Storage Backends

```bash
# SQLite (default, 15x faster)
python -m sapphire run molina --curr 20251230 --storage sqlite

# JSON Files (debugging)
python -m sapphire run molina --curr 20251230 --storage json_files

# JSONL (streaming)
python -m sapphire run molina --curr 20251230 --storage jsonl
```

---

## Output Structure

```
{curr_date}/
├── raw/
│   ├── provider_ids_network_map.json  # Phase 1
│   └── provider_details.db            # Phase 2 (SQLite)
└── processed/
    └── {project}-{date}.jsonl         # Phase 3
```

---

## Network Mapping

Phase 1 discovers provider IDs and maps them to networks:

```json
{
  "provider_123": ["NET001", "NET002"],
  "provider_456": ["NET001"]
}
```

Phase 2 uses the first network for each provider when fetching details.

---

## Checkpointing

Phase 2 saves progress to `details_checkpoint.json` for resumption:

```json
{
  "completed_ids": ["provider_123", "provider_456"],
  "failed_ids": ["provider_789"],
  "last_updated": "2025-12-30T10:00:00Z"
}
```

If interrupted, re-running Phase 2 skips completed providers.

---

## Comparison with HealthSparq

| Aspect | HealthSparq | Sapphire |
|--------|-------------|----------|
| Phases | 6 (includes recovery) | 5 (no recovery) |
| Phase 1 | County-by-county search | Geographic facet queries |
| Phase 2 | v1+v2 combined API | 4 separate API calls |
| Mapper | Factory pattern (`make_mapper`) | Registry pattern (`register_mapper`) |
| Browser | Patchright default | Camoufox default |
| Config | Direct YAML | YAML with `_base.yaml` inheritance |

---

## Testing

```bash
# All tests
pytest sapphire/tests/ -v

# Specific test
pytest sapphire/tests/test_normalize.py -v

# With coverage
pytest sapphire/tests/ --cov=sapphire
```

---

## Related Documents

- [INDEX.md](./INDEX.md) - Navigation
- [01-core-package.md](./01-core-package.md) - Core utilities
- [02-healthsparq.md](./02-healthsparq.md) - HealthSparq comparison
- [04-patterns.md](./04-patterns.md) - Shared patterns

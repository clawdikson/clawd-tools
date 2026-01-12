# Codebase Report: Sapphire Platform Library Architecture
Generated: 2026-01-10

## Summary

Sapphire is a scraping platform library for ProviderFinderOnline (PFO) healthcare provider directory sites. It consolidates 15+ individual Sapphire-based insurance site implementations into a unified library with a 6-phase pipeline architecture. The library provides both CLI and programmatic API interfaces, using browser automation to handle anti-bot protections.

**Key Metrics:**
- Total Lines of Code: ~8,549 Python LOC
- Modules: 7 top-level directories
- Phases: 6 sequential phases
- Storage Backends: 3 (SQLite default, JSON_FILES, JSONL)
- Browser Types: 3 (Camoufox default, Playwright, Patchright)

---

## Project Structure

```
sapphire/
├── __init__.py                # Package exports (API, config, phases)
├── __main__.py                # CLI entry point
├── cli.py                     # Typer-based CLI implementation
├── api.py                     # High-level programmatic API
├── config/                    # Configuration system
│   ├── schema.py              # Pydantic models for validation
│   ├── loader.py              # YAML config loading with inheritance
│   └── CLAUDE.md
├── core/                      # Core utilities
│   ├── sapphire_api.py        # API wrapper for PFO endpoints
│   ├── session.py             # Browser queue management
│   ├── storage.py             # Storage abstraction factory
│   ├── exceptions.py          # Exception hierarchy
│   └── CLAUDE.md
├── phases/                    # Phase pipeline modules
│   ├── discovery.py           # Phase 1: Provider ID discovery
│   ├── details.py             # Phase 2: Detail extraction
│   ├── normalize.py           # Phase 3: Data normalization
│   ├── qa.py                  # Phase 4: Quality assurance
│   ├── report.py              # Phase 5: Report generation
│   ├── recovery.py            # Phase 6: Missing provider recovery
│   └── CLAUDE.md
├── mappers/                   # Normalization mapper registry
│   ├── __init__.py            # Registry pattern for custom mappers
│   └── CLAUDE.md
├── utils/                     # Utilities
│   ├── phase_parser.py        # CLI phase specification parser
│   └── progress.py            # Progress reporting
├── configs/                   # YAML configuration files
│   ├── _base.yaml             # Base config (inherited by all)
│   ├── bcbs_il.yaml           # Project-specific configs
│   └── bcbs_mt.yaml
├── templates/                 # Project templates
├── tests/                     # Test suite
└── data/                      # Static data (geo codes)
```

---

## CLI Entry Points

**Main Entry Point:** `/Users/dikson/Work/ideon_scraping/scraping/sapphire/__main__.py:3-6`

**CLI App:** `/Users/dikson/Work/ideon_scraping/scraping/sapphire/cli.py:24-28`

### Commands

| Command | Location | Description |
|---------|----------|-------------|
| `sapphire run <project>` | cli.py:127-279 | Run scraper for a project |
| `sapphire list` | cli.py:66-80 | List all available projects |
| `sapphire validate <project>` | cli.py:83-101 | Validate project configuration |
| `sapphire doctor` | cli.py:103-125 | Validate all configurations |

### Factory Function

**create_project_cli()** at cli.py:281-432
- Creates thin wrapper CLIs for individual project directories
- Supports custom mappers and commands
- Used in `audiobee_*/run.py` files

---

## API Entry Points

**File:** `/Users/dikson/Work/ideon_scraping/scraping/sapphire/api.py`

### Primary API

**run_scraper_async()** (line 59-406)
```python
async def run_scraper_async(
    config: SapphireProjectConfig,
    curr_date: str,
    prev_date: str | None = None,
    phases: set[int] | None = None,
    mapper: MapperFunc | None = None,
    storage_backend: StorageBackend | None = None,
    # QA/Report/Recovery flags...
) -> ScraperResult
```

**run_scraper_sync()** (line 408-453)
- Synchronous wrapper using `asyncio.run()`

### Result Types

**ScraperResult** (line 41-56)
- `success: bool`
- `providers_count: int`
- `phase_results: dict[int, PhaseResult]`
- `duration_seconds: float` (property)

**PhaseResult** (line 28-37)
- `phase: int`
- `success: bool`
- `message: str`
- `data: dict`
- `duration_seconds: float`

---

## Configuration System

**File:** `/Users/dikson/Work/ideon_scraping/scraping/sapphire/config/schema.py`

### Root Model: SapphireProjectConfig (line 202-223)

```python
class SapphireProjectConfig(BaseModel):
    project: ProjectMetadata
    site: SiteConfig
    networks: list[NetworkConfig]
    coverage: CoverageConfig
    api: APIConfig
    concurrency: ConcurrencyConfig
    output: OutputConfig
    normalize: NormalizeConfig
    session: SessionConfig
```

### Key Enums

**StorageBackend** (line 14-28)
- `SQLITE` (default, 15x faster)
- `JSON_FILES` (human-readable)
- `JSONL` (streaming, append-only)
- `AUTO` (auto-detect)

### Configuration Loading

**File:** `/Users/dikson/Work/ideon_scraping/scraping/sapphire/config/loader.py`

**load_config()** (line 60-123)
- Resolution order: project_dir > audiobee_{slug} > sapphire/configs/
- Uses `deep_merge()` (line 19-31) for base config inheritance
- Validates with Pydantic

**list_projects()** (line 126-141)
- Returns sorted list of available project slugs

### Base Configuration

**File:** `/Users/dikson/Work/ideon_scraping/scraping/sapphire/configs/_base.yaml`

All projects inherit from this base:
- API endpoints and common params
- Concurrency defaults (10 workers, 1000 batch size)
- Storage backend (sqlite)
- Session config (camoufox browser, dataimpulse proxy)

---

## Phase Pipeline

### Phase 1: Discovery

**File:** `/Users/dikson/Work/ideon_scraping/scraping/sapphire/phases/discovery.py`

**Entry Point:** `run_discovery()` / `run_discovery_sync()`

**Purpose:** Discover provider IDs via geographic facet queries

**Input:**
- `SapphireProjectConfig`
- Geo codes from `data/geo_codes/*.json`

**Output:** `DiscoveryResult` (line 84-110)
- `{date}/raw/provider_ids_network_map.json`
- Maps provider_id → [network_ids]

**Key Features:**
- State-aware network selection
- Dual geo-strategy: small circles (dense) + complete (state-wide)
- BoundedSet for memory-safe deduplication
- Progress logging at 10% intervals

### Phase 2: Details

**File:** `/Users/dikson/Work/ideon_scraping/scraping/sapphire/phases/details.py`

**Entry Point:** `run_details()` / `run_details_sync()`

**Purpose:** Fetch full provider details (summary, locations, affiliations, networks)

**Input:**
- `provider_ids_network_map.json` from Phase 1
- Via `load_provider_ids_from_phase1()`

**Output:** `DetailsResult` (line 81-107)
- `{date}/raw/provider_details/*.json` or SQLite DB
- Per-provider cached responses

**Key Features:**
- Batch processing (default 1000 per batch)
- Concurrent requests (default 50)
- Checkpointing via `details_checkpoint.json`
- Retry logic with exponential backoff

### Phase 3: Normalize

**File:** `/Users/dikson/Work/ideon_scraping/scraping/sapphire/phases/normalize.py`

**Entry Point:** `run_normalize()` / `run_normalize_sync()`

**Purpose:** Map raw API data to Ideon schema and deduplicate by NPI

**Input:**
- Raw provider details from Phase 2

**Output:** `NormalizeResult` (line 142-159)
- `{date}/processed/{project_slug}-{date}.jsonl`
- Deduplicated by NPI

**Mapper Resolution:**
1. Explicit mapper passed to `run_normalize(mapper=...)`
2. Registered mapper via `get_mapper(config.project.slug)`
3. `default_sapphire_mapper()` fallback (line 200+)

**Key Features:**
- Uses `deduplicate_by_npi()` from core.mapper.dedup
- Normalization utils from core.mapper.normalize
- Merges duplicate NPI records

### Phase 4: QA

**File:** `/Users/dikson/Work/ideon_scraping/scraping/sapphire/phases/qa.py`

**Entry Point:** `run_qa()` / `run_qa_sync()`

**Purpose:** Schema validation and comparison with previous run

**Sub-phases:**
- 4a: Validation via `core.qa.validate()`
- 4b: Comparison via `core.qa.compare()`

**Output:** `QAResult` (line 14-32)
- Validation: valid/invalid record counts
- Comparison: added/removed/changed provider counts

**Pattern:** Non-fatal phase (failures don't stop pipeline unless --strict)

### Phase 5: Report

**File:** `/Users/dikson/Work/ideon_scraping/scraping/sapphire/phases/report.py`

**Entry Point:** `run_report()` / `run_report_sync()`

**Purpose:** Generate Excel reports and sample files

**Sub-phases:**
- 5a: Excel via `core.qa.reporter.extended_report()` or `core.qa.report()`
- 5b: Samples via `core.qa.sample()`

**Report Types:**
- `"extended"`: Full NPI metrics, scope breakdown
- `"basic"`: State counts only

**Output:** `ReportResult` (line 14-26)
- Excel file path
- Sample JSONL path
- Sample count

### Phase 6: Recovery

**File:** `/Users/dikson/Work/ideon_scraping/scraping/sapphire/phases/recovery.py`

**Entry Point:** `run_recovery()` / `run_recovery_sync()`

**Purpose:** Find and recover missing providers (NPIs in prev but not curr)

**Key Functions:**
- `find_missing_providers()` - Compare curr vs prev NPIs
- `search_npi_via_facets()` - Search for NPI in facets
- `recover_provider()` - Attempt recovery

**Output:** `RecoveryResult`
- Missing/searched/recovered/failed counts

**Pattern:** Optional phase (requires --recovery flag and prev_date)

---

## Core Components

### SapphireAPI

**File:** `/Users/dikson/Work/ideon_scraping/scraping/sapphire/core/sapphire_api.py`

**Class:** `SapphireAPI` (line 101+)

**Methods:**
- `get_facets()` - Specialty categories and counts
- `get_summary()` - Provider search results
- `get_affiliations()` - Group/hospital affiliations
- `get_locations()` - Other practice locations
- `get_networks()` - Networks accepted
- `get_provider_full()` - Parallel fetch all details
- `get_providers_batch()` - Batch provider extraction

**Configuration:** `SapphireAPIConfig` (line 38-99)
- Created via `from_project_config()` classmethod
- Contains domain, CI, endpoints, timeouts

### SapphireBrowserQueue

**File:** `/Users/dikson/Work/ideon_scraping/scraping/sapphire/core/session.py`

**Purpose:** Producer-consumer browser queue with anti-bot handling

**Features:**
- Uses Camoufox (anti-detection) by default
- Auto page refresh after N requests
- X-API-Key capture from initial page load
- Graceful shutdown with request draining

**Browser Types:** camoufox, playwright, patchright

### Storage Factory

**File:** `/Users/dikson/Work/ideon_scraping/scraping/sapphire/core/storage.py`

**Function:** `create_phase_store()` (line 15-45)
```python
def create_phase_store(
    base_dir: Path,
    phase_name: str,
    backend: StorageBackend = StorageBackend.SQLITE,
) -> DataStore
```

Returns `DataStore` abstraction from core.io

### Exception Hierarchy

**File:** `/Users/dikson/Work/ideon_scraping/scraping/sapphire/core/exceptions.py`

```
SapphireError (base)
├── ConfigurationError
├── AuthenticationError
├── APIError (has status_code, url)
├── SessionError
├── StorageError
└── ValidationError (has invalid_records)
```

---

## Mapper Registry

**File:** `/Users/dikson/Work/ideon_scraping/scraping/sapphire/mappers/__init__.py`

**Type:** `MapperFunc = Callable[[dict], dict]`

**Functions:**
- `register_mapper(project_slug, mapper)` - Register custom mapper
- `get_mapper(project_slug)` - Retrieve registered mapper

**Default Mapper:** `default_sapphire_mapper()` in phases/normalize.py

**Usage:**
```python
from sapphire.mappers import register_mapper

def custom_mapper(raw: dict) -> dict:
    # Transform raw PFO data
    return {...}

register_mapper("my_project", custom_mapper)
```

---

## Integration with Core Package

### Core.IO

**Usage:** DataStore abstraction, BoundedSet for deduplication
- `from core.io import BoundedSet, DataStore, create_store`
- Used in: discovery.py, storage.py

### Core.Logging

**Usage:** Structured logging with tqdm support
- `from core.logging import logger, tqdm_logging`
- Used throughout all phases

### Core.Session

**Usage:** Browser session management
- `from core.session import BrowserSession, BrowserType`
- Used in: core/session.py

### Core.Proxy

**Usage:** Proxy configuration
- `from core.proxy import ProxyType`
- Used in: core/session.py

### Core.QA

**Usage:** Validation, comparison, reporting
- `from core.qa import validate, compare, report, sample`
- Used in: phases/qa.py, phases/report.py

### Core.Mapper

**Usage:** Normalization utilities and deduplication
- `from core.mapper.normalize import normalize_zip_code, normalize_phone, ...`
- `from core.mapper.dedup import deduplicate_by_npi, merge_provider_records_inplace`
- Used in: phases/normalize.py

### Fallback Pattern

All core imports use try/except with fallback implementations:
```python
try:
    from core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
```

---

## Data Flow Diagram

```
Configuration (YAML)
        ↓
load_config() → SapphireProjectConfig
        ↓
┌───────────────────────────────────────┐
│ Phase 1: Discovery                    │
│ Input:  Config + geo_codes            │
│ Output: provider_ids_network_map.json│
└───────────────┬───────────────────────┘
                ↓
┌───────────────────────────────────────┐
│ Phase 2: Details                      │
│ Input:  provider_ids_network_map      │
│ Output: provider_details/*.json       │
└───────────────┬───────────────────────┘
                ↓
┌───────────────────────────────────────┐
│ Phase 3: Normalize                    │
│ Input:  Raw provider details          │
│ Process: Mapper + NPI deduplication   │
│ Output: {project}-{date}.jsonl        │
└───────────────┬───────────────────────┘
                ↓
        ┌───────┴────────┐
        ↓                ↓
┌──────────────┐  ┌─────────────┐
│ Phase 4: QA  │  │Phase 5:Rept │
│ Validation   │  │ Excel       │
│ Comparison   │  │ Samples     │
└──────────────┘  └─────────────┘
```

---

## Key Files Reference

| File | Purpose | Entry Points | Lines |
|------|---------|--------------|-------|
| `__init__.py` | Package exports | run_scraper_sync, load_config | 52 |
| `__main__.py` | CLI entry | (entry point) | 7 |
| `cli.py` | CLI commands | app, create_project_cli() | 442 |
| `api.py` | Programmatic API | run_scraper_async() | 454 |
| `config/schema.py` | Config models | SapphireProjectConfig | 223 |
| `config/loader.py` | Config loading | load_config() | 141 |
| `core/sapphire_api.py` | API wrapper | SapphireAPI | ~600 |
| `core/session.py` | Browser queue | SapphireBrowserQueue | ~500 |
| `core/storage.py` | Storage factory | create_phase_store() | 78 |
| `phases/discovery.py` | Phase 1 | run_discovery() | ~650 |
| `phases/details.py` | Phase 2 | run_details() | ~900 |
| `phases/normalize.py` | Phase 3 | run_normalize() | ~700 |
| `phases/qa.py` | Phase 4 | run_qa() | 140 |
| `phases/report.py` | Phase 5 | run_report() | 150 |
| `phases/recovery.py` | Phase 6 | run_recovery() | ~550 |
| `utils/phase_parser.py` | Phase parsing | resolve_phases() | 176 |

---

## Configuration Patterns

### Inheritance Example

**Base:** `configs/_base.yaml`
```yaml
concurrency:
  max_workers: 10
  batch_size: 1000
output:
  storage_backend: sqlite
session:
  browser_type: camoufox
```

**Project:** `configs/bcbs_il.yaml`
```yaml
project:
  name: BCBS Illinois
  slug: bcbs_il
site:
  domain: bcbsil.sapphirethreesixtyfive.com
  ci: "2"
networks:
  - id: "210002020"
    name: "BCBS IL HMO"
    state: "IL"
coverage:
  states: ["IL"]
  geo_strategy: dual
```

Merged via `deep_merge(base, project)`

---

## Summary of Discoveries

1. **6-Phase Pipeline**: Discovery → Details → Normalize → QA → Report → Recovery
2. **Dual Entry Points**: CLI (Typer) and Programmatic API (async/sync)
3. **Config Inheritance**: YAML base config + project overrides via deep_merge
4. **Storage Flexibility**: 3 backends (SQLite default, JSON_FILES, JSONL)
5. **Mapper Registry**: Custom normalization via register_mapper pattern
6. **Core Integration**: Heavy reliance on core package with fallbacks
7. **Browser Queue**: Anti-bot protection via Camoufox with proxy rotation
8. **State-Based Networks**: Networks mapped to states for geo-targeted queries
9. **Checkpointing**: Phase 2 supports resumption via checkpoint files
10. **Non-Fatal Phases**: QA/Report/Recovery failures don't stop pipeline (unless --strict)

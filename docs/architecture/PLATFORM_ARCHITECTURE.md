# Platform Architecture Documentation

> **Generated**: 2026-01-10
> **Covers**: core/ v3.0, healthsparq/ v2.0, sapphire/ v1.0

## Overview

The scraping framework consists of three main packages that work together to extract healthcare provider directory data from insurance carrier websites:

| Package        | Version | Purpose                                                     | Projects   |
| -------------- | ------- | ----------------------------------------------------------- | ---------- |
| `core/`        | 3.0.0   | Shared utilities (config, I/O, session, proxy, logging, QA) | Foundation |
| `healthsparq/` | 2.0.0   | HealthSparq browser-based platform library                  | 23         |
| `sapphire/`    | 1.0.0   | ProviderFinderOnline API platform library                   | 15         |

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Application Layer                                   │
│                         (audiobee_* scraper projects)                           │
└────────────────────────────────┬────────────────────────────────────────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│   healthsparq/      │ │     sapphire/       │ │   Individual        │
│   Platform Library  │ │  Platform Library   │ │   Carrier Scripts   │
│   (23 projects)     │ │  (15 projects)      │ │   (config.py +      │
│                     │ │                     │ │    index_1/2/3.py)  │
│   6-Phase Pipeline  │ │   5-Phase Pipeline  │ │                     │
└──────────┬──────────┘ └──────────┬──────────┘ └──────────┬──────────┘
           │                       │                       │
           └───────────────────────┼───────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                             core/ v3.0 (Shared Package)                         │
│                                                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ config/  │ │   io/    │ │ session/ │ │  proxy/  │ │ logging/ │ │   qa/    │ │
│  │          │ │          │ │          │ │          │ │          │ │          │ │
│  │ Pydantic │ │DataStore │ │ Browser  │ │Multi-    │ │ Loguru   │ │Validate  │ │
│  │ Settings │ │SQLite    │ │ HTTP     │ │provider  │ │structured│ │Compare   │ │
│  │ .env     │ │JSONL     │ │ Proxy    │ │round-    │ │trace_id  │ │Sample    │ │
│  │          │ │JSON      │ │          │ │robin     │ │          │ │Report    │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ │
│                                                                                 │
│  ┌──────────┐ ┌──────────┐                                                     │
│  │ mapper/  │ │validation│                                                     │
│  │          │ │          │                                                     │
│  │Normalize │ │Pydantic  │                                                     │
│  │Dedup     │ │Provider  │                                                     │
│  │Schema    │ │Location  │                                                     │
│  └──────────┘ └──────────┘                                                     │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## core/ Package (v3.0.0)

**Location**: `/Users/dikson/Work/ideon_scraping/scraping/core/`
**Role**: Foundation layer providing shared utilities for all 95+ scraper projects

### Module Structure

```
core/
├── __init__.py           # Public API exports, .env loading
├── exceptions.py         # 4-class hierarchy (SharedPackageError base)
├── config/               # Pydantic Settings configuration
│   ├── base.py           # BaseConfig with SCRAPER_* prefix
│   ├── proxy.py          # ProxySettings with SecretStr
│   ├── factory.py        # load_config() factory
│   ├── registry.py       # CONFIG_TYPES mapping
│   ├── sapphire.py       # SapphireConfig
│   ├── healthsparq.py    # HealthsparqConfig
│   ├── carrier.py        # CarrierConfig
│   └── anthem.py         # AnthemConfig
├── io/                   # DataStore abstraction (documented separately)
│   ├── base.py           # DataStore Protocol + BackendType
│   ├── factory.py        # create_store()
│   ├── sqlite_fs.py      # SQLiteStore (15x faster)
│   ├── jsonl.py          # JSONLStore + BoundedSet
│   └── json_files.py     # JSONFileStore
├── session/              # Browser/HTTP session management
│   ├── browser_session.py    # Patchright/Playwright/Camoufox
│   ├── http_session.py       # curl_cffi HTTP client
│   └── resilient_session.py  # Auto-recovery wrapper
├── proxy/                # Multi-provider proxy orchestration
│   ├── base.py           # ProxyType enum, BaseProxyProvider ABC
│   ├── manager.py        # ProxyManager (round-robin)
│   ├── session_manager.py    # Sticky session pool
│   └── providers/        # 8 provider implementations
├── logging/              # Loguru-based structured logging
│   └── logger.py         # setup_logging(), trace_id ContextVar
├── qa/                   # Quality assurance tools
│   ├── validator.py      # fastjsonschema validation
│   ├── comparison.py     # Polars-based diff analysis
│   ├── sampler.py        # Reservoir sampling
│   └── reporter.py       # Excel state reports
├── mapper/               # Data normalization
│   ├── base.py           # BaseMapper ABC
│   ├── normalize.py      # normalize_*, clean_* functions
│   ├── dedup.py          # NPI-based deduplication
│   └── schema.py         # JSON schema validation
└── validation/           # Pydantic models
    └── models.py         # Provider, Location schemas
```

### Key Entry Points

| Entry Point               | Location                       | Purpose                        |
| ------------------------- | ------------------------------ | ------------------------------ |
| `load_config()`           | `config/factory.py:24`         | Load site-type config from env |
| `create_store()`          | `io/factory.py:24`             | Create DataStore instance      |
| `setup_logging()`         | `logging/logger.py`            | Initialize loguru logger       |
| `ProxyManager`            | `proxy/manager.py`             | Get proxy configs              |
| `ResilientBrowserSession` | `session/resilient_session.py` | Auto-recovery browser          |

### Public API

```python

```

---

## healthsparq/ Package (v2.0.0)

**Location**: `/Users/dikson/Work/ideon_scraping/scraping/healthsparq/`
**Role**: Platform library for HealthSparq-based insurance sites (browser automation)

### Module Structure

```
healthsparq/
├── __init__.py           # Public API exports
├── api.py                # run_scraper_sync(), ScraperResult
├── cli.py                # Typer CLI (run, list, validate, doctor)
├── __main__.py           # python -m healthsparq
├── config/               # YAML configuration system
│   ├── loader.py         # load_config(), list_projects()
│   └── schema.py         # HealthSparqProjectConfig Pydantic model
├── configs/              # 23 project YAML files
│   ├── _base.yaml        # Inherited defaults
│   ├── medica_sg.yaml
│   ├── christus_health_plan.yaml
│   └── ... (23 total)
├── core/                 # Internal components
│   ├── healthspark.py    # HealthSpark API wrapper
│   └── session.py        # Two-step session pattern
├── phases/               # 6-phase pipeline
│   ├── search.py         # Phase 1: County-by-county discovery
│   ├── details.py        # Phase 2: Provider detail extraction
│   ├── normalize.py      # Phase 3: NPI dedup + schema mapping
│   ├── qa.py             # Phase 4: Validation + comparison
│   ├── report.py         # Phase 5: Excel + samples
│   └── recovery.py       # Phase 6: Missing provider recovery
├── mappers/              # Project-specific normalization
└── templates/            # Project scaffolding templates
```

### 6-Phase Pipeline

```
Phase 1 (search.py)      Phase 2 (details.py)   Phase 3 (normalize.py)
County-by-county    →    Provider detail    →    NPI deduplication
adaptive search          extraction              Schema mapping
                                                Custom mapper injection
        ↓                       ↓                       ↓
  search_results/         provider_details/       providers.jsonl

Phase 4 (qa.py)         Phase 5 (report.py)    Phase 6 (recovery.py)
Schema validation   →    Excel reports     →    Missing provider
Run comparison           Sample generation       recovery
        ↓                       ↓                       ↓
  Validation metrics      Excel files            recovered/
```

### Key Entry Points

| Entry Point            | Location              | Purpose                    |
| ---------------------- | --------------------- | -------------------------- |
| `run_scraper_sync()`   | `api.py:57`           | Main library entry (sync)  |
| `run_scraper()`        | `api.py:38`           | Main library entry (async) |
| `load_config()`        | `config/loader.py:45` | Load project YAML          |
| `list_projects()`      | `config/loader.py:23` | List available projects    |
| CLI `run`              | `cli.py:96`           | Run scraper via CLI        |
| CLI `list`             | `cli.py:61`           | List projects via CLI      |
| `create_project_cli()` | `cli.py:435`          | Factory for thin wrappers  |

### Public API

```python

```

### Configuration System

```yaml
# configs/{project}.yaml inherits from _base.yaml
project:
    name: "Human Name"
    slug: project_slug

site:
    domain: example.healthsparq.com
    brand_code: BRAND
    insurer_code: INSURER

plans:
    - product_code: MA
      name: "Medicare Advantage"
      networks:
          - network_id: "NET001"
            name: "Network Name"

coverage:
    states: [TX, LA, CA]
```

### Usage Patterns

```python
# Basic usage
from healthsparq import load_config, run_scraper_sync

config = load_config("christus_health_plan")
result = run_scraper_sync(config, "20251227")
print(f"Providers: {result.providers_count}")

# Custom mapper injection
from healthsparq import default_mapper


def my_mapper(raw: dict) -> dict:
    result = default_mapper(raw)
    result["custom_field"] = raw.get("source_field")
    return result


result = run_scraper_sync(config, "20251227", mapper=my_mapper)

# Run specific phases
result = run_scraper_sync(config, "20251227", phases={2, 3, 5})

# Run QA and Report
result = run_scraper_sync(config, "20251227", run_qa=True, run_report=True)
```

---

## sapphire/ Package (v1.0.0)

**Location**: `/Users/dikson/Work/ideon_scraping/scraping/sapphire/`
**Role**: Platform library for ProviderFinderOnline (PFO) sites (API-based)

### Module Structure

```
sapphire/
├── __init__.py           # Public API exports
├── api.py                # run_scraper_sync(), ScraperResult
├── cli.py                # Typer CLI (run, list, validate, doctor)
├── __main__.py           # python -m sapphire
├── config/               # YAML configuration system
│   ├── loader.py         # load_config(), list_projects()
│   └── schema.py         # SapphireProjectConfig Pydantic model
├── configs/              # 15 project YAML files
│   ├── _base.yaml        # Inherited defaults
│   ├── molina.yaml
│   └── ... (15 total)
├── core/                 # Internal components
│   ├── api.py            # SapphireAPI wrapper
│   ├── browser_queue.py  # Browser pool management
│   ├── storage.py        # create_phase_store()
│   └── exceptions.py     # SapphireError hierarchy
├── phases/               # 5-phase pipeline
│   ├── discovery.py      # Phase 1: Geographic facet queries
│   ├── details.py        # Phase 2: Provider detail fetch
│   ├── normalize.py      # Phase 3: NPI dedup + mapping
│   ├── qa.py             # Phase 4: Validation + comparison
│   └── report.py         # Phase 5: Excel + samples
├── mappers/              # Project-specific normalization
│   ├── registry.py       # register_mapper()
│   └── defaults.py       # default_sapphire_mapper
└── utils/                # Utilities
    ├── phase_parser.py   # Phase range parsing
    └── progress.py       # Progress reporting
```

### 5-Phase Pipeline

```
Phase 1 (discovery.py)   Phase 2 (details.py)   Phase 3 (normalize.py)
Geographic facet    →    Provider detail    →    NPI deduplication
queries (ZIP/state)      fetch                   Schema mapping
Network ID mapping                               Custom mapper
        ↓                       ↓                       ↓
  provider_ids_             provider_details.db    {project}-{date}.jsonl
  network_map.json

Phase 4 (qa.py)         Phase 5 (report.py)
Schema validation   →    Excel reports
Run comparison           Sample generation
        ↓                       ↓
  Validation metrics      Excel files
```

### Key Entry Points

| Entry Point           | Location              | Purpose                    |
| --------------------- | --------------------- | -------------------------- |
| `run_scraper_sync()`  | `api.py:408`          | Main library entry (sync)  |
| `run_scraper_async()` | `api.py:59`           | Main library entry (async) |
| `load_config()`       | `config/loader.py`    | Load project YAML          |
| `list_projects()`     | `config/loader.py`    | List available projects    |
| CLI `run`             | `cli.py`              | Run scraper via CLI        |
| `register_mapper()`   | `mappers/registry.py` | Register custom mapper     |

### Public API

```python

```

### Configuration System

```yaml
# configs/{project}.yaml inherits from _base.yaml
project:
    name: "Molina Healthcare"
    slug: molina

api:
    base_url: "https://providersearch.molina.providerfinderonline.com"
    site_id: "molina"

networks:
    - id: "NET001"
      name: "Network Name"
      states: [TX, CA]

discovery:
    strategy: dual # small, complete, or dual
    max_workers: 4
```

### Usage Patterns

```python
# Basic usage
from sapphire import load_config, run_scraper_sync

config = load_config("molina")
result = run_scraper_sync(config, curr_date="20251230")
print(f"Providers: {result.providers_count}")

# Custom mapper
from sapphire.mappers import register_mapper


def molina_mapper(raw: dict) -> dict:
    # Custom transformation
    return {...}


register_mapper("molina", molina_mapper)

# Run with QA and reports
result = run_scraper_sync(config, "20251230", prev_date="20251201", run_qa=True, run_report=True)
```

---

## Cross-Package Integration

### Dependency Flow

```
healthsparq/        sapphire/         audiobee_*/
     │                  │                  │
     └──────────┬───────┴──────────────────┘
                │
                ▼
             core/
                │
     ┌──────────┼──────────┬──────────┐
     ▼          ▼          ▼          ▼
  config/     io/      session/    proxy/
```

### Shared Patterns

| Pattern | core/                   | healthsparq/         | sapphire/            |
| ------- | ----------------------- | -------------------- | -------------------- |
| Config  | Pydantic Settings       | YAML + Pydantic      | YAML + Pydantic      |
| Storage | DataStore Protocol      | create_phase_store() | create_phase_store() |
| Session | ResilientBrowserSession | Two-step pattern     | Browser queue        |
| Logging | Loguru + trace_id       | Uses core.logging    | Uses core.logging    |
| QA      | validate/compare/sample | Phase 4              | Phase 4              |

### Import Pattern (Graceful Degradation)

All platform packages use try/except for core imports:

```python
try:
    from core.io import create_store
    from core.logging import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)
```

---

## File Locations Reference

### Entry Points Summary

| Component       | Entry Point          | File:Line                   |
| --------------- | -------------------- | --------------------------- |
| core config     | `load_config()`      | `core/config/factory.py:24` |
| core storage    | `create_store()`     | `core/io/factory.py:24`     |
| core logging    | `setup_logging()`    | `core/logging/logger.py`    |
| healthsparq API | `run_scraper_sync()` | `healthsparq/api.py:57`     |
| healthsparq CLI | `run` command        | `healthsparq/cli.py:96`     |
| sapphire API    | `run_scraper_sync()` | `sapphire/api.py:408`       |
| sapphire CLI    | `run` command        | `sapphire/cli.py`           |

### Documentation Locations

| Topic                 | Location                                                 |
| --------------------- | -------------------------------------------------------- |
| Database architecture | `docs/architecture/DATABASE_ARCHITECTURE.md`             |
| Platform architecture | `docs/architecture/PLATFORM_ARCHITECTURE.md` (this file) |
| Core package          | `core/CLAUDE.md`                                         |
| HealthSparq           | `healthsparq/CLAUDE.md`                                  |
| Sapphire              | `sapphire/CLAUDE.md`                                     |
| I/O module            | `core/io/CLAUDE.md`                                      |

---

## Architectural Decisions

### 1. YAML Configuration with Inheritance

Both platform libraries use YAML configs with a `_base.yaml` that gets merged via `deep_merge()`. This allows:

- Shared defaults across all projects
- Project-specific overrides
- Pydantic validation of merged config

### 2. Phase Pipeline Architecture

Both libraries follow a similar multi-phase approach:

- **Separation of concerns**: Each phase has single responsibility
- **Resumability**: Each phase produces persistent output
- **Testability**: Phases can run independently
- **Flexibility**: Phases can be skipped or run selectively

### 3. DataStore Abstraction

The `core/io/` module provides a unified interface for storage:

- **SQLite default**: 15x faster for large datasets
- **JSON_FILES fallback**: Human-readable for debugging
- **JSONL option**: Streaming for specific use cases

### 4. Graceful Degradation

All imports use try/except to allow:

- Running without optional dependencies
- Backwards compatibility with legacy code
- Isolated testing of components

### 5. Mapper Injection Pattern

Both libraries support custom mapper injection:

- Default mapper handles common transformations
- Projects can override with custom logic
- Registry pattern for automatic lookup (sapphire)

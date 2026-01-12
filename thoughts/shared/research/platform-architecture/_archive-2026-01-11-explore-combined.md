---
date: 2026-01-11T00:00:00Z
type: exploration
depth: deep
focus: core, healthsparq, sapphire
commit: 4b76867
---

# Codebase Exploration: Platform Libraries

Deep exploration of the three main platform libraries in the scraping monorepo.

## Summary

This scraping monorepo implements a **three-tier platform architecture** with 95+ individual scraper projects sharing common infrastructure:

- **core/** - Shared utilities package (config, I/O, logging, proxy, session, QA, mapper)
- **healthsparq/** - HealthSparq platform library (23 projects, 6-phase pipeline)
- **sapphire/** - ProviderFinderOnline platform library (15 projects, 5-phase pipeline)

The architecture follows a **zero-global-state design** - all configuration is injected, making it testable and composable.

## Structure

```
scraping/
├── core/                    # Shared utilities package (v3.0)
│   ├── config/              # Pydantic Settings with site-type registry
│   ├── io/                  # DataStore abstraction (JSONL/JSON/SQLite)
│   ├── session/             # Browser/HTTP session management
│   ├── proxy/               # Multi-provider proxy orchestration
│   ├── logging/             # Loguru-based structured logging
│   ├── qa/                  # Validation, comparison, sampling, reporting
│   └── mapper/              # Normalization utilities + schema validation
│
├── healthsparq/             # HealthSparq platform library (23 projects)
│   ├── config/              # YAML configs + schema validation
│   ├── core/                # HealthSpark API wrapper
│   ├── phases/              # 6-phase pipeline implementation
│   └── cli.py               # Typer CLI + factory functions
│
├── sapphire/                # Sapphire platform library (15 projects)
│   ├── config/              # YAML configs + schema validation
│   ├── core/                # SapphireAPI wrapper
│   ├── phases/              # 5-phase pipeline implementation
│   └── cli.py               # Typer CLI
│
└── audiobee_*/              # 95+ individual scraper projects
```

## Architecture

### Layer Analysis (from tldr arch)

| Layer | Role | Files |
|-------|------|-------|
| Entry | Controllers/handlers | `config/factory.py`, `logging/logger.py`, `session/browser_session.py` |
| Middle | Services | `proxy/providers/*`, `tests/test_qa/*` |
| Leaf | Utilities | `mapper/*`, `io/*`, `qa/*`, `session/http_session.py` |

**Circular Dependencies**: None detected

### Phase Pipeline Comparison

| Phase | HealthSparq | Sapphire |
|-------|-------------|----------|
| 1 | Search (county-by-county adaptive) | Discovery (geographic facets) |
| 2 | Details (v1+v2 API combined) | Details (4 API calls) |
| 3 | Normalize (NPI dedup, mapper) | Normalize (NPI dedup, mapper) |
| 4 | QA (validation + comparison) | QA (validation + comparison) |
| 5 | Report (Excel + samples) | Report (Excel + samples) |
| 6 | Recovery (NPI/name search) | N/A |

## Key Components

### 1. DataStore Abstraction (`core/io/`)

Protocol-based storage with 3 interchangeable backends:

| Backend | Extension | Use Case | Performance |
|---------|-----------|----------|-------------|
| SQLite | `.db` | Large datasets (100k+) | 15x faster writes |
| JSONL | `.jsonl` | Streaming, append-only | O(1) dedup via BoundedSet |
| JSON Files | `/` directory | Debugging | Individual files |

**Key Files:**
- `core/io/base.py:36-165` - DataStore Protocol
- `core/io/factory.py:24-86` - Auto-detection factory
- `core/io/sqlite_fs.py:50-100` - Buffered writes (15x speedup)

### 2. Configuration System (`core/config/`)

Pydantic Settings with factory pattern and site-type registry:

```
BaseConfig (SCRAPER_* env prefix)
    ├── SapphireConfig
    ├── HealthsparqConfig
    ├── CarrierConfig
    └── AnthemConfig
```

**Key Files:**
- `core/config/base.py:42-161` - BaseConfig with .env hierarchy
- `core/config/factory.py:18-50` - `load_config()` factory
- `core/config/registry.py` - CONFIG_TYPES mapping

### 3. Session Management (`core/session/`)

Three-tier abstraction with auto-recovery:

```
ResilientBrowserSession (auto-recovery)
         │
         └─► BrowserSession (Patchright/Playwright/Camoufox)
                    │
                    └─► HttpSession (curl_cffi, browser impersonation)
```

**Browser Transfer Pattern**: Login via browser → extract cookies → transfer to HTTP for fast API calls (10x speedup).

**Key Files:**
- `core/session/browser_session.py:100-150` - Lazy init, multi-backend
- `core/session/http_session.py:150-200` - Cookie transfer
- `core/session/resilient_session.py:100-150` - Session death detection

### 4. Mapper & Normalization (`core/mapper/`)

`MapperFunc = Callable[[dict], dict]` type alias with project-specific injection.

**HealthSparq Pattern**: Factory with `make_mapper(custom_logic)`
**Sapphire Pattern**: Registry with `register_mapper(slug, func)`

**Shared Utilities:**
- `normalize_zip_code()` - 5-digit ZIP
- `normalize_phone()` - Digits only
- `deduplicate_by_npi()` - NPI-based grouping
- `merge_provider_records_inplace()` - Union merging

**Key Files:**
- `healthsparq/phases/normalize.py:450-500` - `default_mapper()`, `make_mapper()`
- `sapphire/mappers/registry.py` - Registry pattern
- `core/mapper/dedup.py` - Deduplication utilities

### 5. QA System (`core/qa/`)

Shared validation, comparison, and reporting:

| Component | Purpose |
|-----------|---------|
| `validator.py` | Schema validation (fastjsonschema) |
| `comparison.py` | Run comparison (Polars) |
| `reporter.py` | Excel state reports |
| `sampler.py` | Reservoir sampling |

### 6. API Wrappers

**HealthSparq** (`healthsparq/core/healthspark.py`):
- `HealthSpark` class with search, details v1+v2, geocode
- `get_provider_details_full()` combines v1+v2 responses

**Sapphire** (`sapphire/core/sapphire_api.py`):
- `SapphireAPI` class (browser-based)
- 4 API calls per provider: summary, locations, affiliations, networks

## Patterns Found

### 1. Zero Global State

All configuration injected via Pydantic Settings. No global variables.

### 2. Protocol-Based Abstractions

DataStore, MapperFunc enable swappable implementations without code changes.

### 3. Graceful Degradation

Optional imports with fallback implementations:
```python
try:
    from core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
```

### 4. Memory Safety

- `BoundedSet` with LRU eviction (100k items max)
- SQLite staging for large datasets
- Buffered writes (100 record batches)

### 5. Browser → HTTP Transfer

Login via browser for anti-bot, then transfer cookies to lightweight HTTP for 10x API performance.

### 6. Dual CLI + Library Interface

Both platforms usable as:
1. CLI: `python -m healthsparq run ...`
2. Library: `from healthsparq import run_scraper_sync`
3. Template: `create_project_cli()` factory

## Dependency Relationships

```
audiobee_* projects
      │
      ├─► healthsparq/  ──┐
      │                   │
      └─► sapphire/  ─────┼─► core/
                          │     ├─► config/  (Pydantic Settings)
                          │     ├─► io/      (DataStore)
                          │     ├─► session/ (Browser/HTTP)
                          │     ├─► proxy/   (ProxyManager)
                          │     ├─► logging/ (Loguru)
                          │     ├─► qa/      (Validation/Comparison)
                          │     └─► mapper/  (Normalization)
                          │
                          └─► Third-party:
                                ├─► pydantic, pydantic-settings
                                ├─► patchright, playwright, camoufox
                                ├─► httpx, curl_cffi
                                ├─► orjson, pyyaml
                                ├─► loguru, tqdm
                                └─► polars, fastjsonschema
```

## Performance Optimizations

| Optimization | Location | Impact |
|--------------|----------|--------|
| SQLite buffered writes | `core/io/sqlite_fs.py:50-100` | 15x faster |
| BoundedSet LRU | `core/io/jsonl.py:150-200` | Bounded memory |
| SQLite NPI map | `healthsparq/phases/normalize.py:80-120` | 14% faster, 42% less memory |
| Lazy browser init | `core/session/browser_session.py:100-150` | On-demand only |
| HTTP session transfer | `core/session/http_session.py:150-200` | 10x faster API calls |

## CLI Patterns

Both platforms use Typer with identical command structure:

```bash
python -m {healthsparq|sapphire} list
python -m {healthsparq|sapphire} validate <project>
python -m {healthsparq|sapphire} run <project> --curr YYYYMMDD [options]
python -m {healthsparq|sapphire} doctor
```

**Phase Selection:**
- `--phase N` / `-p 2,3,5` / `-p 2-5` / `--from-phase 2` / `--skip-phase 1`

**QA/Report:**
- `--qa` / `--validate` / `--compare`
- `--report` / `--excel` / `--samples-only`

## References

### Core Package

| File | Purpose |
|------|---------|
| `core/__init__.py` | Public API exports |
| `core/config/base.py` | BaseConfig with SCRAPER_* prefix |
| `core/io/factory.py` | `create_store()` factory |
| `core/session/browser_session.py` | Multi-backend browser automation |
| `core/mapper/dedup.py` | NPI deduplication |

### HealthSparq

| File | Purpose |
|------|---------|
| `healthsparq/api.py` | `run_scraper_sync()` entry point |
| `healthsparq/config/schema.py` | `HealthSparqProjectConfig` Pydantic model |
| `healthsparq/core/healthspark.py` | HealthSpark API wrapper |
| `healthsparq/phases/normalize.py` | `default_mapper()`, `make_mapper()` |

### Sapphire

| File | Purpose |
|------|---------|
| `sapphire/api.py` | `run_scraper_async()` entry point |
| `sapphire/config/schema.py` | `SapphireProjectConfig` Pydantic model |
| `sapphire/core/sapphire_api.py` | SapphireAPI wrapper |
| `sapphire/mappers/registry.py` | Mapper registry pattern |

## Open Questions

1. **Recovery in Sapphire**: HealthSparq has Phase 6 (recovery), Sapphire doesn't. Is this planned?

2. **Mapper Convergence**: HealthSparq uses factory (`make_mapper()`), Sapphire uses registry (`register_mapper()`). Should these converge?

3. **Browser Backend Selection**: HealthSparq defaults to Patchright, Sapphire uses Camoufox. What determines the choice?

4. **SQLite NPI Map**: Only HealthSparq imports `SQLiteNPIMap`. Should Sapphire use it too?

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Scraping monorepo for healthcare provider directory data extraction. Contains 95+ individual scraper projects and 3 shared platform libraries.

**Repository Structure:**

- `core/` - Shared utilities (config, I/O, logging, proxy, session, QA)
- `healthsparq/` - HealthSparq platform library (23 projects)
- `sapphire/` - ProviderFinderOnline platform library (15 projects)
- `audiobee_*/` - Individual scraper projects (various platforms)

## CRITICAL: audiobee_* Projects Are Standalone Git Repos

**All `audiobee_*/` folders are independent git repositories**, not subdirectories of this monorepo.

- They are gitignored in the parent repo (`.gitignore: audiobee_*/`)
- Each has its own git history and remote (typically Bitbucket)
- To commit changes: `cd audiobee_<project>` then use git commands there
- Do NOT try to commit audiobee changes from the parent scraping repo

## Build & Run Commands

```bash
# Install dependencies (uv recommended)
uv sync

# IMPORTANT: Always use the venv in the base folder
# All python commands should use .venv/bin/python

# Run a healthsparq project
.venv/bin/python -m healthsparq run medica_sg --curr 20251230

# Run a sapphire project
.venv/bin/python -m sapphire run molina --curr 20251230

# Run QA validation
.venv/bin/python -m core.qa validate providers.jsonl

# Run tests
.venv/bin/pytest core/tests/ healthsparq/tests/ sapphire/tests/ -v
```

## Architecture

### Platform Libraries

| Library        | Platform                       | Projects | CLAUDE.md               |
| -------------- | ------------------------------ | -------- | ----------------------- |
| `healthsparq/` | HealthSparq browser automation | 23       | `healthsparq/CLAUDE.md` |
| `sapphire/`    | ProviderFinderOnline API       | 15       | `sapphire/CLAUDE.md`    |

### Core Package Modules

| Module          | Purpose                                         | CLAUDE.md                |
| --------------- | ----------------------------------------------- | ------------------------ |
| `core/config/`  | Pydantic Settings, site-type inheritance        | `core/config/CLAUDE.md`  |
| `core/io/`      | DataStore abstraction (JSONL/SQLite/JSON Files) | `core/io/CLAUDE.md`      |
| `core/logging/` | Loguru-based structured logging                 | `core/logging/CLAUDE.md` |
| `core/proxy/`   | Multi-provider proxy orchestration              | `core/proxy/CLAUDE.md`   |
| `core/session/` | Browser/HTTP session management                 | `core/session/CLAUDE.md` |
| `core/qa/`      | Validation, comparison, sampling, reporting     | `core/qa/CLAUDE.md`      |

### Phase Pipelines

Both platform libraries use similar multi-phase pipelines:

**HealthSparq (6 phases):** Search → Details → Normalize → QA → Report → Recovery

**Sapphire (5 phases):** Discovery → Details → Normalize → QA → Report

See `healthsparq/phases/CLAUDE.md` and `sapphire/phases/CLAUDE.md` for details.

## Common Patterns

### Environment Configuration

All scrapers use `SCRAPER_*` prefix environment variables:

```bash
SCRAPER_PROJECT_NAME=audiobee_bcbs_il
SCRAPER_CURR_DATE=20251230
SCRAPER_SITE_TYPE=healthsparq
```

### Storage Backends

Three interchangeable backends via DataStore abstraction:

- **SQLite** (default): 15x faster writes, best for production
- **JSON Files**: Human-readable, best for debugging
- **JSONL**: Streaming, append-only

### Proxy Configuration

```bash
PROXY_TYPES=smartproxy_session,dataimpulse_rotating
```

Multi-provider round-robin distribution by browser ID.

## Git Commits

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(healthsparq): add retry logic for search phase
fix(core): handle missing NPI in provider response
```

## Testing

```bash
# All tests
.venv/bin/pytest -v

# Specific package
.venv/bin/pytest healthsparq/tests/ -v

# Coverage
.venv/bin/pytest --cov=core --cov=healthsparq --cov=sapphire

# Type checking
.venv/bin/mypy core/ healthsparq/ sapphire/
```

## Submodule Documentation

Each module has its own CLAUDE.md with detailed API patterns:

- `core/CLAUDE.md` - Full core package documentation
- `healthsparq/CLAUDE.md` - CLI, library API, phase details
- `sapphire/CLAUDE.md` - CLI, library API, phase details
- `core/*/CLAUDE.md` - Module-specific patterns (io, session, proxy, etc.)


## Codemap

```
scraping/
├── core/                           # Shared utilities package (v3.0)
│   ├── __init__.py                 # Public API exports
│   ├── exceptions.py               # SharedPackageError hierarchy
│   ├── config/                     # Pydantic Settings configuration
│   │   ├── base.py                 # BaseConfig (SCRAPER_* env prefix)
│   │   ├── proxy.py                # ProxySettings with SecretStr
│   │   ├── factory.py              # load_config() factory
│   │   └── {healthsparq,sapphire,carrier,anthem}.py
│   ├── io/                         # DataStore abstraction
│   │   ├── base.py                 # DataStore Protocol + BackendType enum
│   │   ├── factory.py              # create_store() auto-detection
│   │   ├── jsonl.py                # JSONLStore + BoundedSet dedup
│   │   ├── json_files.py           # JSONFileStore (debugging)
│   │   └── sqlite_fs.py            # SQLiteStore (15x faster)
│   ├── logging/                    # Loguru-based logging
│   │   └── logger.py               # setup_logging(), trace_id
│   ├── proxy/                      # Multi-provider proxy orchestration
│   │   ├── base.py                 # ProxyType enum, ProxyConfig
│   │   ├── manager.py              # ProxyManager round-robin
│   │   └── providers/              # SmartProxy, DataImpulse, Decodo, VPN
│   ├── session/                    # Browser/HTTP session management
│   │   ├── browser_session.py      # BrowserSession (Patchright/Camoufox)
│   │   ├── http_session.py         # HttpSession (curl_cffi)
│   │   └── resilient_session.py    # ResilientBrowserSession auto-recovery
│   ├── qa/                         # Validation, comparison, reporting
│   │   ├── validator.py            # fastjsonschema validation
│   │   ├── comparison.py           # Polars-based diff analysis
│   │   ├── reporter.py             # Excel state reports
│   │   └── debug_reports.py        # Debug Excel generation
│   └── mapper/                     # Data normalization
│       ├── normalize.py            # ZIP/phone normalization
│       └── schema.py               # JSON schema validation
│
├── healthsparq/                    # HealthSparq platform library (23 projects)
│   ├── __init__.py                 # Public API: run_scraper_sync, load_config
│   ├── api.py                      # ScraperResult, PhaseResult dataclasses
│   ├── cli.py                      # Typer CLI + create_project_cli()
│   ├── config/                     # YAML config loading
│   │   ├── schema.py               # HealthSparqProjectConfig Pydantic model
│   │   └── loader.py               # load_config(), list_projects()
│   ├── core/                       # HealthSparq-specific
│   │   ├── healthsparq_api.py      # HealthSpark API wrapper
│   │   ├── session.py              # Two-step session (browser→HTTP)
│   │   └── storage.py              # create_phase_store()
│   ├── phases/                     # 6-phase pipeline
│   │   ├── search.py               # Phase 1: County-by-county discovery
│   │   ├── details.py              # Phase 2: Provider detail extraction
│   │   ├── normalize.py            # Phase 3: NPI dedup + schema mapping
│   │   ├── qa.py                   # Phase 4: Validation + comparison
│   │   ├── report.py               # Phase 5: Excel + samples
│   │   └── recovery.py             # Phase 6: Missing provider recovery
│   ├── configs/                    # Project YAML configs (23 projects)
│   └── templates/                  # Project scaffolding templates
│
├── sapphire/                       # Sapphire/PFO platform library (15 projects)
│   ├── __init__.py                 # Public API: run_scraper_sync, load_config
│   ├── api.py                      # ScraperResult, PhaseResult dataclasses
│   ├── cli.py                      # Typer CLI + create_project_cli()
│   ├── config/                     # YAML config loading
│   │   ├── schema.py               # SapphireProjectConfig Pydantic model
│   │   └── loader.py               # load_config(), list_projects()
│   ├── core/                       # Sapphire-specific
│   │   ├── sapphire_api.py         # SapphireAPI browser wrapper
│   │   ├── session.py              # Browser queue management
│   │   └── storage.py              # create_phase_store()
│   ├── phases/                     # 5-phase pipeline
│   │   ├── discovery.py            # Phase 1: Geographic facet queries
│   │   ├── details.py              # Phase 2: Provider detail fetching
│   │   ├── normalize.py            # Phase 3: NPI dedup + schema mapping
│   │   ├── qa.py                   # Phase 4: Validation + comparison
│   │   └── report.py               # Phase 5: Excel + samples
│   ├── mappers/                    # Project-specific mappers
│   └── configs/                    # Project YAML configs (15 projects)
│
├── audiobee_*/                     # Individual scraper projects (95+)
│   │                               # Three patterns:
│   │                               #
│   │  ─── healthsparq-based (thin wrapper) ───
│   ├── audiobee_medica_sg/         # Example: HealthSparq library project
│   │   ├── run.py                  # CLI entry point (create_project_cli)
│   │   ├── mapper.py               # Custom normalization logic
│   │   └── config.yaml             # Project configuration
│   │                               #
│   │  ─── sapphire-based (legacy + library) ───
│   ├── audiobee_molina/            # Example: Sapphire/PFO project
│   │   ├── index_0.py              # Legacy: Provider ID discovery
│   │   ├── index_1_v3.py           # Legacy: Provider detail fetching
│   │   ├── 3_map_json_to_ideon_format.py  # Legacy: Normalization
│   │   ├── playwright_queue_session.py    # Browser queue management
│   │   └── config.yaml             # Sapphire config
│   │                               #
│   │  ─── carrier-type (custom) ───
│   └── audiobee_multiplan/         # Example: Custom carrier project
│       ├── index_0.py              # Discovery script
│       ├── index_1.py              # Details script
│       ├── index_2.py              # Processing script
│       ├── index_3.py              # Normalization script
│       └── config.py               # Custom configuration
│
├── output_generator/               # Legacy output processing tools
├── scripts/                        # Utility scripts
└── tools/                          # Development tools
```

## CLI Documentation
- Always use Typer for args in CLI.
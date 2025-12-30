# Architecture

## Overview

This repository contains **~86 web scrapers** for extracting provider directory data from insurance carrier websites. Each scraper targets a specific insurance plan/carrier and extracts provider information (NPIs, names, specialties, locations, network affiliations) for healthcare data aggregation.

**Purpose**: Collect and standardize provider network data from insurance carrier directories for downstream analytics and compliance reporting.

**Execution Model**: Manual runs as needed (not automated/scheduled).

## Tech Stack

| Category | Technologies |
|----------|-------------|
| **Language** | Python 3.10+ (3.11+ for core package) |
| **Package Management** | uv, pip, setuptools |
| **HTTP Clients** | httpx, curl_cffi, requests |
| **Browser Automation** | Patchright (Playwright fork), Puppeteer (Node.js legacy) |
| **Data Processing** | pandas, polars, orjson |
| **Configuration** | Pydantic, Pydantic Settings, PyYAML |
| **Logging** | loguru |
| **Testing** | pytest, pytest-asyncio, pytest-cov |
| **Validation** | fastjsonschema, jsonschema |
| **CLI** | typer |

## Directory Structure

```
scraping/
├── audiobee_*/              # ~86 individual scraper projects
│   ├── config.py            # Configuration (URLs, params, network IDs)
│   ├── index_1.py           # Phase 1: Search/Discovery
│   ├── index_2.py           # Phase 2: Detail extraction
│   ├── index_3.py           # Phase 3: Data mapping/normalization
│   ├── run_all.py           # Orchestrator script
│   └── YYYYMMDD/            # Date-versioned output directories
│       ├── raw/             # Raw API responses (JSON/JSONL)
│       └── processed/       # Normalized output files
│
├── core/                    # Shared utilities v3.0 (git submodule)
│   ├── config/              # Pydantic Settings-based configuration
│   ├── io/                  # DataStore abstraction (JSONL, SQLite, JSON files)
│   ├── logging/             # Loguru-based structured logging
│   ├── mapper/              # Provider data normalization
│   ├── proxy/               # Multi-provider proxy orchestration
│   ├── qa/                  # QA utilities (validation, comparison, sampling)
│   ├── session/             # Browser/HTTP session management
│   └── validation/          # Pydantic models for provider data
│
├── healthsparq/             # HealthSparq library v2.0 (23 projects)
│   ├── api.py               # High-level API (run_scraper_sync)
│   ├── cli.py               # Typer CLI (list, validate, run, doctor)
│   ├── config/              # YAML configuration loading
│   ├── configs/             # Project YAML files (23 configs)
│   ├── core/                # HealthSpark API wrapper, session management
│   ├── phases/              # Pipeline phases (search, details, normalize)
│   └── templates/           # Project scaffolding templates
│
├── output_generator/        # Legacy QA utilities (deprecated → use core/qa)
│
├── docs/                    # Project documentation
│   ├── onboarding/          # Core technical guides
│   ├── extra/               # Advanced reference docs
│   └── implementation_research/  # Shared utilities research
│
├── tools/                   # Execution and automation tools
├── plans/                   # Feature/refactor plans
├── todos/                   # Completed task tracking
└── .beads/                  # AI-native issue tracking
```

## Core Components

### 1. Individual Scrapers (`audiobee_*/`)

Each scraper follows a 3-phase pipeline pattern:

```
Phase 1 (index_1.py)     → Phase 2 (index_2.py)    → Phase 3 (index_3.py)
Search/Discovery           Detail Extraction          Normalization
├── Load search params     ├── Load discovered IDs    ├── Load raw data
├── Execute searches       ├── Fetch provider details ├── Map to schema
├── Cache to raw/          ├── Cache to raw/          ├── Deduplicate by NPI
└── Extract unique IDs     └── Handle rate limiting   └── Write to processed/
```

**Orchestrator** (`run_all.py`): Sequential phase execution with progress tracking.

### 2. Core Package (`core/`)

Shared utilities for all scrapers:

| Module | Purpose |
|--------|---------|
| `config/` | Pydantic Settings with site-type inheritance, env var loading |
| `io/` | DataStore abstraction (JSONL, SQLite, JSON files), BoundedSet dedup |
| `logging/` | Loguru with trace_id, project context, async-safe handlers |
| `mapper/` | Provider normalization, NPI deduplication, schema validation |
| `proxy/` | Multi-provider proxy orchestration (SmartProxy, DataImpulse, etc.) |
| `qa/` | Validation, comparison, sampling, Excel reports |
| `session/` | BrowserSession, HttpSession, ResilientBrowserSession |
| `validation/` | Pydantic models for Provider, Location |

### 3. HealthSparq Library (`healthsparq/`)

Unified package for 23 HealthSparq-based projects:

- **Dual interface**: CLI (`python -m healthsparq`) + importable library
- **Configuration-driven**: YAML configs in `configs/`
- **Custom mapper injection**: Projects can inject custom normalization logic
- **Browser automation**: Uses `core/session/ResilientBrowserSession`

```python
# Library usage
from healthsparq import load_config, run_scraper_sync, default_mapper

config = load_config("christus_health_plan")
result = run_scraper_sync(config, "20251227")
```

## Data Flow

### Scraper Pipeline

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Phase 1       │     │   Phase 2       │     │   Phase 3       │
│   Search        │────▶│   Details       │────▶│   Normalize     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ raw/search_     │     │ raw/provider_   │     │ processed/      │
│ results/*.json  │     │ details/*.json  │     │ providers.jsonl │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Session Pattern (HealthSparq)

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ ResilientBrowser│     │   Extract       │     │   HttpSession   │
│ Session (login) │────▶│   Cookies       │────▶│   (fast API)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Site Type Architecture

Projects are categorized by underlying provider directory platform:

| Site Type | Projects | Pattern | Tech |
|-----------|----------|---------|------|
| **Carrier** | 32 | Direct REST API | httpx, async pagination |
| **HealthSparq** | 23 | Unified library | ResilientBrowserSession, YAML configs |
| **Sapphire** | 14 | ProviderFinderOnline API | network_id filtering |
| **Anthem** | 3 | Wellpoint infrastructure | Multi-phase, complex networks |
| **HealthTrioConnect** | 2 | Node.js + Python hybrid | Browser automation |
| **Werally** | 3 | UHC Platform | Grid-based geographic search |
| **Provider Lenz** | 1 | Anti-bot protected | Captcha solving |

## External Integrations

### Proxy Providers

| Provider | Type | Use Case |
|----------|------|----------|
| SmartProxy | Residential (rotating/session) | Anti-bot sites |
| DataImpulse | Residential (rotating/session) | High-volume scraping |
| Decodo DC | Datacenter static IPs | IP reputation building |
| Surfshark/NordVPN | VPN-based | Fallback |

### Storage

| Backend | Best For | Performance |
|---------|----------|-------------|
| JSONL | Streaming, append-only | Fast writes, human-readable |
| SQLite | Large datasets, exists() checks | 15x faster writes, ACID |
| JSON Files | Debugging, small datasets | Easy inspection |

## Configuration

### Environment Variables

```bash
# Proxy configuration
PROXY_TYPES=smartproxy_session,dataimpulse_rotating
SMARTPROXY_USERNAME=...
SMARTPROXY_PASSWORD=...
DATAIMPULSE_PROXY_USERNAME=...
DATAIMPULSE_PROXY_PASSWORD=...

# Project configuration
SCRAPER_PROJECT_NAME=audiobee_bcbs_il
SCRAPER_CURR_DATE=20251227
SCRAPER_PREV_DATE=20251127
```

### Project Configuration (`config.py`)

```python
PREV_DATE = "20251010"
CURR_DATE = "20251110"
PROJECT_NAME = "audiobee_*"

DIRS = {
    "raw": os.path.join(CURR_DATE, "raw"),
    "search_results": os.path.join(CURR_DATE, "raw", "search_results"),
    "provider_details": os.path.join(CURR_DATE, "raw", "provider_details"),
    "processed": os.path.join(CURR_DATE, "processed"),
}

BASE_URLS = {"search": "https://...", "details": "https://..."}
REQ_STATES = ["IL", "IN", ...]
```

## Build & Deploy

### Running a Scraper

```bash
# Navigate to project
cd audiobee_bcbs_il

# Update dates in config.py, then run phases
python index_1.py  # Discovery
python index_2.py  # Details
python index_3.py  # Normalization

# Or use orchestrator
python run_all.py
```

### HealthSparq Projects

```bash
# Install package
cd healthsparq && pip install -e .

# Run scraper
python -m healthsparq run medica_sg --curr 20251226 --prev 20251110

# Run specific phase
python -m healthsparq run medica_sg --curr 20251226 --phase 1
```

### QA Validation

```bash
# Validate output
python -m core.qa validate providers.jsonl

# Compare runs
python -m core.qa compare --curr 20251227 --prev 20251126

# Generate samples
python -m core.qa sample providers.jsonl --count 10

# Generate report
python -m core.qa report audiobee_bcbs_il --curr 20251227
```

### Parallel Execution

```bash
# Run API scrapers in parallel
python tools/run_parallel.py --list projects/api.txt --workers 8 --curr 20251210
```

## Output Schema

All scrapers produce normalized JSONL with consistent fields:

```json
{
  "npi": "1234567890",
  "first_name": "John",
  "last_name": "Smith",
  "specialty": "Family Medicine",
  "address_line_1": "123 Main St",
  "city": "Chicago",
  "state": "IL",
  "zip": "60601",
  "phone": "312-555-0100",
  "network_id": "210002020",
  "accepting_new_patients": true
}
```

## Key Files Reference

| File | Purpose |
|------|---------|
| `config.py` | Project configuration (URLs, params, dates) |
| `index_1.py` | Phase 1: Search/discovery |
| `index_2.py` | Phase 2: Detail extraction |
| `index_3.py` | Phase 3: Data normalization |
| `run_all.py` | Pipeline orchestrator |
| `CLAUDE.md` | Project-specific AI context |
| `AGENTS.md` | Agent workflow instructions |

# Ideon Scraping Project

## AI Helpers

**Issue Tracking**: This project uses **Beads** (bd) - AI-native issue tracking that lives in the repo.
**BD Usage**: Always use bd for issue tracking for any tasks. Breakdown the tasks into as small component as possible. Delegate these tasks to subagents with relevant context wherever possible for optimum performance.

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

See [AGENTS.md](AGENTS.md) for landing-the-plane checklist and session completion workflow.

**Git Commits**: Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

| Type       | Description                         |
| ---------- | ----------------------------------- |
| `feat`     | New feature                         |
| `fix`      | Bug fix                             |
| `docs`     | Documentation only                  |
| `style`    | Formatting (no code change)         |
| `refactor` | Code restructuring (no feature/fix) |
| `perf`     | Performance improvement             |
| `test`     | Adding/fixing tests                 |
| `build`    | Build system or dependencies        |
| `ci`       | CI configuration                    |
| `chore`    | Maintenance (no src/test change)    |

**Examples**:

```bash
feat(scraper): add retry logic for rate-limited requests
fix(index_2): handle missing NPI in provider response
docs: update CLAUDE.md with conventional commits guide
refactor(config): extract URL building to helper function
perf(sqlite): implement buffered writes for 15x speedup
```

<!-- AUTO-MANAGED: project-description -->

## Overview

This repository contains **~86 web scrapers** for extracting provider directory data from insurance carrier websites. Each scraper targets a specific insurance plan/carrier and extracts provider information (NPIs, names, specialties, locations, network affiliations) for healthcare data aggregation.

**Purpose**: Collect and standardize provider network data from insurance carrier directories for downstream analytics and compliance reporting.

**Execution Model**: Manual runs as needed (not automated/scheduled).

<!-- END AUTO-MANAGED -->

---

<!-- AUTO-MANAGED: architecture -->

## Project Structure

```
scraping/
├── audiobee_*/              # ~86 individual scraper projects
│   ├── config.py            # Configuration (URLs, params, network IDs)
│   ├── index_1.py           # Phase 1: Search/Discovery
│   ├── index_2.py           # Phase 2: Detail extraction
│   ├── index_3.py           # Phase 3: Data mapping/normalization
│   ├── run_all.py           # Orchestrator script
│   ├── shared_package/      # Optional: Local shared utilities (session management)
│   │   ├── session/         # BrowserSession, ResilientBrowserSession (Patchright/curl_cffi)
│   │   ├── config.py        # Proxy configuration with dotenv
│   │   └── localdataclass/  # Response objects
│   ├── YYYYMMDD/            # Date-versioned output directories
│   │   ├── raw/             # Raw API responses (JSON/JSONL)
│   │   └── processed/       # Normalized output files
│   └── CLAUDE.md            # Project-specific metadata (if present)
│
├── audiobee_anthem_new/     # Advanced Anthem scraper with alternative architectures
│   ├── task_server/         # Two-process architecture (FastAPI + browser pool)
│   ├── browser/             # Camoufox browser automation with request interception
│   ├── single_process_implementation/  # Alternative unified architecture
│   │   ├── unified_scraper.py          # Main entry point (asyncio.Queue)
│   │   ├── provider_searcher.py        # Provider search logic
│   │   ├── state_processor.py          # State processing
│   │   ├── injection_unified.html      # JS injection (page.expose_function)
│   │   └── src/                        # Shared utilities
│   ├── ANTHEM_IMPROVEMENT.md           # Architectural analysis
│   └── SINGLE_PROCESS_PLAN.md          # Single-process implementation plan
│
├── healthsparq/             # HealthSparq library v2.0 (importable + CLI + project templates)
│   ├── __init__.py          # Public API exports (run_scraper_sync, default_mapper, load_config)
│   ├── __main__.py          # CLI entry point (python -m healthsparq)
│   ├── cli.py               # Typer-based CLI commands (list, validate, run, doctor)
│   ├── api.py               # High-level scraper API (run_scraper_sync, ScraperResult)
│   ├── config/              # Configuration system
│   │   ├── schema.py        # Pydantic models for project configuration
│   │   └── loader.py        # YAML configuration loading with validation
│   ├── configs/             # Project YAML files (23 HealthSparq projects)
│   │   ├── _base.yaml       # Shared defaults for all projects
│   │   ├── christus_health_plan.yaml
│   │   ├── medica_sg.yaml
│   │   └── ...              # 20+ additional project configs
│   ├── core/                # Core scraping logic
│   │   ├── __init__.py      # Core module exports
│   │   ├── healthspark.py   # HealthSpark API wrapper (async context manager)
│   │   ├── session.py       # Session management (browser auth + HTTP)
│   │   ├── exceptions.py    # Custom exception hierarchy
│   │   └── file_writer.py   # Async file writing with worker pool
│   ├── phases/              # Execution phases (search, details, normalize)
│   │   └── normalize.py     # Supports custom mapper injection via MapperFunc
│   ├── templates/           # Project scaffolding templates
│   │   ├── run.py.template          # Typer CLI importing healthsparq library
│   │   ├── mapper.py.template       # Custom mapper extending default_mapper()
│   │   ├── .env.example             # Environment config template
│   │   ├── .gitignore.template      # Output directory ignores
│   │   ├── README.md.template       # Usage instructions
│   │   └── requirements.txt.template # Just healthsparq dependency
│   ├── tests/               # Test suite (99+ tests)
│   ├── CLAUDE.md            # Package documentation and conventions
│   ├── README.md            # Package documentation
│   └── pyproject.toml       # Python package metadata (v2.0.0)
│
├── healthsparq-server/      # Legacy browser automation server (deprecated - use healthsparq package instead)
│   ├── server.js            # Node.js/Puppeteer server (port 1018)
│   └── CLAUDE.md            # Server documentation
│
├── output_generator/        # Shared QA utilities
│   ├── type_check.py        # Output schema validation
│   ├── sample_generator.py  # Sample data extraction
│   ├── comparison_creator.py # Cross-run diff analysis
│   ├── report_generator.py  # Excel report generation
│   └── CLAUDE.md            # Utility documentation
│
├── tools/                   # Execution and automation tools
│   └── run_parallel.py      # Parallel scraper execution with retry logic
│
├── projects/                # Project categorization for parallel execution
│   └── api.txt              # API-type scrapers (37 Carrier projects)
│
├── core/                    # Shared package v3.0 (git submodule, formerly shared_package/)
│   ├── config/              # Pydantic Settings-based configuration
│   ├── io/                  # DataStore abstraction + SQLiteFS/JSONL utilities
│   │   ├── base.py          # DataStore Protocol + BackendType enum
│   │   ├── factory.py       # create_store() factory with auto-detection
│   │   ├── json_files.py    # JSONFileStore - individual JSON files
│   │   ├── jsonl.py         # JSONLStore wrapper + JSONL I/O with BoundedSet deduplication
│   │   ├── sqlite_fs.py     # SQLiteStore wrapper + SQLiteFS virtual filesystem (15x faster)
│   │   └── SQLITE_FS.md     # SQLiteFS usage documentation
│   ├── logging/             # Loguru-based logging
│   ├── validation/          # Pydantic models for provider data
│   ├── proxy/               # Multi-provider proxy orchestration
│   ├── session/             # Browser/HTTP session management
│   ├── mapper/              # Provider data normalization and mapping
│   │   ├── base.py          # BaseMapper ABC, MapperResult, MapperFunc type
│   │   ├── normalize.py     # Normalization utilities (ZIP, phone, address, gender)
│   │   ├── dedup.py         # NPI-based deduplication with record merging
│   │   ├── schema.py        # JSON Schema validation
│   │   ├── healthsparq.py   # HealthSparq mapper (v2 format, 23 projects)
│   │   ├── carrier.py       # Carrier mapper base (custom API structures)
│   │   └── README.md        # Mapper usage documentation
│   ├── data/                # Shared reference data
│   │   └── output_json_schema.json  # Provider output schema
│   ├── tests/test_mapper.py # Mapper test suite
│   └── CLAUDE.md            # Package documentation
│
├── docs/                    # Project documentation
│   ├── onboarding/          # Core technical guides
│   │   ├── INDEX.md         # Documentation navigation hub
│   │   ├── ARCHITECTURE.md  # Complete system architecture
│   │   ├── PIPELINE.md      # Pipeline phase specifications
│   │   ├── SITE_TYPES_REFERENCE.md  # Platform-specific patterns
│   │   ├── DEVELOPER_GUIDE.md       # Onboarding guide
│   │   ├── TROUBLESHOOTING.md       # Diagnostic procedures
│   │   ├── GLOSSARY.md      # Healthcare/technical terminology
│   │   └── IMPROVEMENTS.md  # Code improvement recommendations (P0-P3)
│   ├── extra/               # Advanced reference docs
│   │   ├── EXPERT_REVIEW.md # 27-expert review summary
│   │   ├── PLAN.md          # Infrastructure scaling plan
│   │   ├── SCALABILITY_BEST_PRACTICES.md  # Parallel execution patterns
│   │   └── SHARED_UTILS_IMPLEMENTATION.md # Shared utilities design
│   ├── implementation_research/  # Shared utilities research (see below)
│   ├── restructuring/       # SQLite migration documentation
│   │   └── SQLITE_STORAGE_STRATEGY.md     # SQLite technical rationale
│   ├── CLAUDE-arch_improvements-Pramod-20251227.md  # Architectural review (markdown)
│   ├── README.md            # Main documentation hub
│   ├── site-type-mapping.md # Projects by infrastructure type
│   └── quick-reference.md   # Common operations guide
│
├── docs/implementation_research/ # (Moved under docs/ - see above)
│
├── data/                    # Shared reference data
│   ├── specialties.json     # Specialty code mappings
│   └── us_zip_fips_county.xlsx  # Geographic reference
│
├── todos/                   # Task tracking (P1 issues completed)
│   ├── 003-completed-p1-sqlite-commit-per-write.md      # SQLiteFS write buffer optimization
│   ├── 006-completed-p1-jsonl-append-quadratic.md       # JSONL append performance analysis
│   ├── 007-completed-p1-sync-io-in-async.md             # Async I/O wrapper implementation
│   └── 008-completed-p1-missing-context-manager.md      # JSONLReader context manager fix
│
├── .beads/                  # Beads issue tracking (AI-native, git-synced)
│   ├── README.md            # Beads introduction and quick start
│   ├── config.yaml          # Beads configuration
│   ├── issues.jsonl         # Issue database (git-tracked with custom merge driver)
│   └── .gitignore           # Beads-specific ignores
│
├── AGENTS.md                # Agent workflow instructions (landing-the-plane checklist)
└── .gitattributes           # Custom merge driver for .beads/issues.jsonl
```

## Site Type Architecture

Projects are categorized by the underlying provider directory platform:

### 1. Carrier (32 projects)

**Direct API Integration** - REST APIs with minimal browser automation

```
Examples: audiobee_florida_blue, audiobee_multiplan, audiobee_harvard_pilgrim
Pattern:  config.py → index_1.py (search) → index_2.py (details) → index_3.py (map)
Tech:     httpx/requests, async pagination, NPI-based deduplication
```

**Characteristics**:

- Direct REST API calls (JSON responses)
- API keys/headers in config.py
- Geographic grid search (lat/lng + radius)
- Network ID-based plan filtering

### 2. Healthsparq (23 projects)

**Importable Library v2.0** - Standalone package supporting both CLI and library usage

```
Examples: medica_sg, christus_health_plan, excellus
Pattern:  python -m healthsparq run <project> --curr YYYYMMDD (CLI)
          from healthsparq import run_scraper_sync (library)
Tech:     ResilientBrowserSession (core/session), async HealthSpark API wrapper
```

**Characteristics**:

- **Dual interface**: CLI tool + importable library with custom mapper injection
- Uses `core/session.ResilientBrowserSession` for authentication
- Two-step session pattern: browser auth → fast HTTP API calls
- Configuration-driven via YAML files in `healthsparq/configs/`
- Three-phase pipeline: search → details → normalize (customizable via MapperFunc)
- Project scaffolding templates in `healthsparq/templates/`

**Architecture**:

- `healthsparq/api.py`: High-level API (`run_scraper_sync`, `ScraperResult`)
- `healthsparq/phases/normalize.py`: Supports custom mapper injection (`MapperFunc`)
- `healthsparq/templates/`: Project scaffolding (run.py, mapper.py, .env.example)
- `healthsparq/core/exceptions.py`: Structured exception hierarchy (AuthenticationError, APIError, SearchError, etc.)
- Public API exports: `run_scraper`, `default_mapper`, `load_config`, `MapperFunc`

**CLI Usage**:

```bash
python -m healthsparq list                          # List 23 available projects
python -m healthsparq validate christus_health_plan # Validate config
python -m healthsparq run christus_health_plan --curr 20251226 --prev 20251126
python -m healthsparq run medica_sg --curr 20251226 --phase 1  # Run specific phase
python -m healthsparq run medica_sg --curr 20251226 --validate # Enable schema validation
python -m healthsparq doctor                                   # Validate all configs
```

**Library Usage**:

```python
from healthsparq import load_config, run_scraper_sync, default_mapper

# Use default mapper
config = load_config("christus_health_plan")
result = run_scraper_sync(config, "20251227")

# Use custom mapper
def my_mapper(raw: dict) -> dict:
    result = default_mapper(raw)
    # Add custom logic here
    return result

result = run_scraper_sync(config, "20251227", mapper=my_mapper)

# Enable JSON schema validation (validates against core/data/output_json_schema.json)
result = run_scraper_sync(config, "20251227", validate=True)
validation_errors = result.phase_results[3].data.get("validation_errors", 0)
```

### 3. Sapphire (14 projects)

**ProviderFinderOnline Platform** - Standardized API structure

```
Examples: audiobee_bcbs_il, audiobee_molina, audiobee_bcbs_la
Pattern:  config.py → faceted search → provider details → location enrichment
Tech:     providerfinderonline.com API, network_id filtering
```

### 4. Anthem (3 projects)

**Wellpoint Infrastructure** - Multi-phase with intelligent filtering

```
Examples: audiobee_anthem, audiobee_amerigroup, audiobee_healthy_blue
Pattern:  search → filter → details → affiliations → networks
Tech:     Brand-specific URLs, complex network hierarchies
```

### 5. HealthTrioConnect (2 projects)

**Node.js + Python Hybrid** - Browser automation with Python processing

### 6. Werally (3 projects)

**UHC Platform** - Grid-based geographic search

### 7. Provider Lenz (1 project)

**Anti-Bot Protected** - Requires captcha solving

<!-- END AUTO-MANAGED -->

---

<!-- AUTO-MANAGED: build-commands -->

## Build & Development Commands

### Running a Scraper

```bash
# 1. Navigate to project
cd audiobee_bcbs_il

# 2. Update dates in config.py
PREV_DATE = "20251010"
CURR_DATE = "20251210"

# 3. Run phases sequentially
python index_1.py # Discovery
python index_2.py # Details
python index_3.py # Normalization

# Or use orchestrator
python run_all.py
```

### Parallel Execution

```bash
# Run API scrapers in parallel (from list)
python tools/run_parallel.py --list projects/api.txt --workers 8 --curr 20251210 --prev 20251110

# Run scrapers by pattern
python tools/run_parallel.py --pattern "audiobee_bcbs*" --workers 8 --curr 20251210 --prev 20251110
```

### For Healthsparq Projects

```bash
# Install package (one-time setup)
cd healthsparq
pip install -e .

# List available projects
python -m healthsparq list

# Run scraper
python -m healthsparq run medica_sg --curr 20251226 --prev 20251110

# Run specific phase only
python -m healthsparq run medica_sg --curr 20251226 --phase 1 # Search
python -m healthsparq run medica_sg --curr 20251226 --phase 2 # Details
python -m healthsparq run medica_sg --curr 20251226 --phase 3 # Normalize

# Validate configuration
python -m healthsparq validate christus_health_plan
python -m healthsparq doctor # Validate all configs
```

### Validating Output

```bash
# Check output schema compliance
python output_generator/type_check.py audiobee_bcbs_il/

# Generate diff report vs previous run
python output_generator/comparison_creator.py audiobee_bcbs_il/
```

<!-- END AUTO-MANAGED -->

---

<!-- AUTO-MANAGED: conventions -->

## Code Conventions

### Pipeline Architecture (3-4 Phases)

```
Phase 1 (index_1.py): Discovery
├── Load search parameters (ZIP codes, specialties, networks)
├── Execute paginated searches
├── Cache raw responses to {date}/raw/search_results/
└── Extract unique provider/location IDs

Phase 2 (index_2.py): Detail Extraction
├── Load discovered IDs from Phase 1
├── Fetch individual provider details
├── Cache to {date}/raw/provider_details/
└── Handle rate limiting/retries

Phase 3 (index_3.py): Normalization
├── Load raw data from Phases 1-2
├── Map to standard output schema
├── Deduplicate by NPI
└── Write to {date}/processed/

Orchestrator (run_all.py):
├── Sequential phase execution
├── Progress tracking
└── Error aggregation
```

### Configuration Pattern (config.py)

```python
# Standard config.py structure
PREV_DATE = "20251010"        # Previous run date
CURR_DATE = "20251110"        # Current run date
PROJECT_NAME = "audiobee_*"   # Project identifier

DIRS = {                      # Output directory structure
    "raw": os.path.join(CURR_DATE, "raw"),
    "search_results": os.path.join(CURR_DATE, "raw", "search_results"),
    "provider_details": os.path.join(CURR_DATE, "raw", "provider_details"),
    "processed": os.path.join(CURR_DATE, "processed"),
}

BASE_URLS = {                 # API endpoints
    "search": "https://...",
    "details": "https://...",
}

BASE_PARAMS = {               # Common request parameters
    "network_id": "...",
    "page": "1",
    "limit": "100",
}

REQ_STATES = ["IL", "IN", ...]  # Target states
```

### Output Schema

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

### Shared Package Pattern (Local vs Root)

**Root-level shared package**: `core/` submodule (formerly `shared_package`) provides v3.0 utilities:

- Config management (Pydantic Settings)
- SQLiteFS and JSONL I/O with async support
- Loguru-based logging
- Validation models
- Proxy orchestration
- Browser/HTTP session management

**Project-level shared package**: Some individual scrapers include local `shared_package/` directories for project-specific session management:

```python
# Import pattern (from project root)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared_package.session.browser_session import BrowserSession

# Usage with async/await
async def fetch_data():
    async with BrowserSession() as session:
        response = await session.get(url, params=params, headers=headers)
        return response.json()
```

**Migration note**: Root `shared_package/` submodule renamed to `core/` (Dec 2025) to clarify it as the central shared utilities package.

<!-- END AUTO-MANAGED -->

---

<!-- AUTO-MANAGED: patterns -->

## Key Files Reference

| File         | Purpose                                          |
| ------------ | ------------------------------------------------ |
| `config.py`  | Project configuration (URLs, params, dates)      |
| `index_1.py` | Phase 1: Search/discovery                        |
| `index_2.py` | Phase 2: Detail extraction                       |
| `index_3.py` | Phase 3: Data normalization                      |
| `run_all.py` | Pipeline orchestrator                            |
| `PLAN.md`    | Infrastructure scaling implementation plan       |
| `CLAUDE.md`  | Project metadata (site type, coverage, approval) |

## Coverage Types

| Type                   | Description           | Example Projects                           |
| ---------------------- | --------------------- | ------------------------------------------ |
| **Medicare Advantage** | Senior plans (65+)    | audiobee_anthem, audiobee_humana           |
| **Medicaid**           | State-funded programs | audiobee_uhc_medicaid, audiobee_amerigroup |
| **ACA**                | Marketplace plans     | audiobee_florida_blue, audiobee_bcbs_il    |
| **Large Group**        | Employer plans        | audiobee_multiplan                         |

<!-- END AUTO-MANAGED -->

---

<!-- MANUAL -->

## Shared Utilities

### healthsparq/ - Importable Library v2.0

Unified package for 23 HealthSparq projects with dual CLI + library interface:

**CLI Usage**:

```bash
# List available projects
python -m healthsparq list

# Validate configuration
python -m healthsparq validate christus_health_plan

# Run scraper (standalone - uses core/session for browser automation)
python -m healthsparq run christus_health_plan --curr 20251226 --prev 20251126

# Health checks
python -m healthsparq doctor
```

**Library Usage**:

```python
from healthsparq import load_config, run_scraper_sync, default_mapper

# Basic usage
config = load_config("christus_health_plan")
result = run_scraper_sync(config, "20251227")
print(f"Found {result.providers_count} providers")

# Custom mapper injection
def my_mapper(raw: dict) -> dict:
    result = default_mapper(raw)
    # Add custom logic here
    return result

result = run_scraper_sync(config, "20251227", mapper=my_mapper)
```

**Project Scaffolding**:

Use templates in `healthsparq/templates/` to create library-based projects:

- `run.py.template`: Typer CLI importing from healthsparq library
- `mapper.py.template`: Custom mapper extending `default_mapper()`
- `.env.example`: Environment config (proxy, browser settings)
- `requirements.txt.template`: Single dependency: `healthsparq`

**Key Features**:

- **Dual interface**: CLI tool + importable library with custom mapper injection
- **Configuration-driven**: YAML configs in `healthsparq/configs/` (no hardcoded domains/plans)
- **Custom mapping**: Projects can inject custom mapper functions via `MapperFunc` type
- **Async session management**: Browser login → cookie extraction → fast HTTP requests
- **Structured exceptions**: Custom hierarchy (AuthenticationError, APIError, SearchError, etc.)
- **Context managers**: Proper resource cleanup with `async with` pattern
- **99+ tests**: Comprehensive test suite with fixtures and integration tests

**Architecture**:

- `healthsparq/api.py`: High-level API (`run_scraper_sync`, `ScraperResult`, `PhaseResult`)
- `healthsparq/core/healthspark.py`: HealthSpark API wrapper (search, profile, geocode endpoints)
- `healthsparq/core/session.py`: HealthSparqSession with ResilientBrowserSession for auth
- `healthsparq/config/schema.py`: Pydantic models for configuration validation
- `healthsparq/phases/normalize.py`: Supports custom mapper injection via `MapperFunc` type
- `healthsparq/templates/`: Project scaffolding templates for library-based projects

### healthsparq-server (Port 1018) - Legacy Only

Browser automation server for legacy audiobee\_\* HealthSparq projects (NOT needed for unified `healthsparq/` package):

```bash
# Start server (only for legacy audiobee_* projects)
cd healthsparq-server && PORT=1018 npm start

# Server handles:
# - Session management
# - Cookie extraction
# - Stealth browser automation
# - Token refresh
```

**Note**: The unified `healthsparq/` package is standalone Python and uses `core/session/` (ResilientBrowserSession) for browser automation.

### output_generator

QA and reporting utilities:

```bash
# Validate output schema
python output_generator/type_check.py audiobee_*/

# Generate samples
python output_generator/sample_generator.py audiobee_*/

# Compare runs
python output_generator/comparison_creator.py audiobee_*/ --prev 20251010 --curr 20251110

# Create Excel report
python output_generator/report_generator.py audiobee_*/
```

### core/ - Shared Package v3.0

The `core/` submodule (formerly `shared_package/`) provides common utilities for all scrapers. **Always prefer core implementations over reinventing**.

**Mapper Module** (`core/mapper/`):

Unified provider data normalization for all scraper types:

```python
from core.mapper import run_normalize, HealthSparqMapper, CarrierMapper
from pathlib import Path

# HealthSparq projects (23 projects)
result = run_normalize(
    raw_dir=Path("20251227/raw/provider_details"),
    output_file=Path("20251227/processed/providers.jsonl"),
    validate=True,  # JSON schema validation
)
print(f"Mapped {result.total_raw} → {result.total_deduplicated} providers")

# Carrier projects (custom subclass)
class FloridaBlueMapper(CarrierMapper):
    def extract_provider(self, data: dict) -> dict:
        return {
            "npi": data.get("nationalProviderId"),
            "first_name": data.get("firstName"),
            # ... map carrier-specific fields
        }

mapper = FloridaBlueMapper(carrier_name="FloridaBlue")
result = run_carrier_normalize(
    raw_dir=Path("audiobee_florida_blue/20251227/raw"),
    output_file=Path("audiobee_florida_blue/20251227/processed/providers.jsonl"),
    mapper=mapper,
)
```

**Features**:

- HealthSparqMapper: v2 format for 23 HealthSparq projects
- CarrierMapper: Base class for custom API structures (subclass per carrier)
- Normalization: ZIP code (5 digits), phone, gender, address strings
- Deduplication: NPI-based with network/address/specialty merging
- Schema validation: Against `core/data/output_json_schema.json`
- Record merging: Combines duplicate NPIs across networks

**Logging** (`core/logging/`):

```python
from core.logging import logger, setup_logging, set_trace_id

# Setup at startup with enhanced features
setup_logging(
    project_name="audiobee_bcbs_il",
    run_id="20251227",
    log_dir="logs",
    level="INFO",
    enable_json_output=True,   # JSON .jsonl file for machine parsing
    enable_error_file=True,    # Separate error-only log for debugging
)

# Structured logging with trace_id correlation
set_trace_id(f"provider_{npi}")
logger.bind(npi=npi, phase=3).info("Processing provider")

# Log levels guide
logger.debug("Pagination details", page=5, total=100)
logger.info("Phase completed", providers=1234, elapsed="5.2s")
logger.warning("Rate limited", retry_after=60, status_code=429)
logger.error("API failure", endpoint="/search", error=str(e))
logger.critical("Session failure", reason="browser crashed")
```

**File I/O** (`core/io/`):

```python
from core.io import create_store, BackendType, JSONLWriter, JSONLReader, SQLiteFS, BoundedSet

# DataStore abstraction (unified interface for JSONL, SQLite, JSON files)
# Auto-detect backend from file extension
store = create_store("raw_data.jsonl")  # JSONL backend
store = create_store("raw_data.db")     # SQLite backend
store = create_store("raw_data/")       # JSON Files backend

# Unified API across all backends (filepath-keyed storage)
store.put("provider_details/1234567890.json", {"npi": "1234567890", ...})
store.put("search_results/TX/Dallas/page_1.json", {"results": [...]})
data = store.get("provider_details/1234567890.json")

# Check existence (optimized per backend)
if store.exists("provider_details/1234567890.json"):
    print("Provider exists")

# Iterate all records
for path, record in store:
    print(f"{path}: {record}")

# Pattern matching (glob-style)
for path in store.keys("provider_details/*.json"):
    print(path)

# Legacy direct usage (still supported)
# JSONL with auto-deduplication
with JSONLWriter("providers.jsonl", dedup_key="npi") as writer:
    writer.write(provider)  # Skips duplicates

# SQLite virtual filesystem (15x faster writes)
fs = SQLiteFS("scraper.db", buffer_size=100)
fs.write("raw/search/IL_60601.json", data)

# Memory-safe deduplication (LRU at 100k items)
seen = BoundedSet(max_size=100_000)
```

**Session Management** (`core/session/`):

```python
from core.session import ResilientBrowserSession, HttpSession
from core.proxy import ProxyType

# Browser with proxy and auto-recovery
async with ResilientBrowserSession(proxy_types=[ProxyType.SMARTPROXY_SESSION]) as session:
    await session.login(url)
    response = await session.get("/api/data")
```

**Configuration** (`core/config/`):

```python
from core.config import load_config, ProxySettings

config = load_config("sapphire", project_name="audiobee_bcbs_il")
proxy = ProxySettings()  # Auto-loads from .env
```

**Import Pattern** (backwards compatibility):

```python
try:
    from core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
```

See `core/CLAUDE.md` for complete documentation.

---

## Documentation

### Documentation Organization

Documentation is organized by audience and complexity level:

#### Core Technical Guides (docs/onboarding/)

Start here for essential project knowledge:

- **INDEX.md** - Documentation navigation hub with role-based guidance
- **ARCHITECTURE.md** - Complete system architecture with diagrams for all 7 platform types
- **PIPELINE.md** - Detailed pipeline phase specifications and data flow patterns
- **SITE_TYPES_REFERENCE.md** - Platform-specific implementation patterns with code examples
- **DEVELOPER_GUIDE.md** - Complete onboarding guide for new developers
- **TROUBLESHOOTING.md** - Diagnostic flowcharts and problem resolution procedures
- **GLOSSARY.md** - Healthcare and technical terminology reference
- **IMPROVEMENTS.md** - Prioritized code improvement recommendations (P0-P3)

#### Advanced Reference (docs/extra/)

For experienced developers and technical leadership:

- **EXPERT_REVIEW.md** - Review summary from 27 domain experts with quality scores
- **PLAN.md** - Infrastructure scaling plan (95→190 scrapers, PC + AWS EC2)
- **SCALABILITY_BEST_PRACTICES.md** - Parallel execution patterns, memory management, rate limiting
- **SHARED_UTILS_IMPLEMENTATION.md** - Shared utilities framework design

#### Implementation Research (docs/implementation_research/)

Detailed technical research for shared utilities v3.0:

- **00_EXECUTIVE_SUMMARY.md** - Research overview and findings
- **01_CODING_FRAMEWORK.md** - Directory structure standards and module responsibilities
- **02_CONFIG_SYSTEM.md** - Pydantic Settings implementation with site-type inheritance
- **03_FILE_UTILITIES.md** - Thread-safe JSON/JSONL utilities with orjson
- **04_LOGGING.md** - Centralized logging with loguru (print() replacement)
- **05_VALIDATION.md** - Raw file integrity and schema validation with Pydantic
- **06_REPORT_GENERATION.md** - Integration with output_generator QA tools
- **07_IMPLEMENTATION_PLAN.md** - Phased rollout strategy (P0-P3 priorities)
- **PC_STORAGE_SERVER_PLAN.md** - PC storage and server architecture

#### Other Documentation

- **docs/restructuring/SQLITE_STORAGE_STRATEGY.md** - SQLite storage technical rationale (15x faster writes)
- **docs/CLAUDE-arch_improvements-Pramod-20251227.md** - External architectural review (markdown version)
- **docs/README.md**, **docs/site-type-mapping.md**, **docs/quick-reference.md** - Quick reference materials

#### Documentation by Role

- **New Developers**: onboarding/GLOSSARY.md → ARCHITECTURE.md → DEVELOPER_GUIDE.md → TROUBLESHOOTING.md
- **Experienced Developers**: onboarding/PIPELINE.md → SITE_TYPES_REFERENCE.md → IMPROVEMENTS.md → extra/SCALABILITY_BEST_PRACTICES.md
- **Technical Leadership**: onboarding/ARCHITECTURE.md → extra/EXPERT_REVIEW.md → implementation_research/ → extra/PLAN.md
- **Operations**: onboarding/TROUBLESHOOTING.md → DEVELOPER_GUIDE.md → quick-reference.md

---

## Infrastructure Scaling Plan

**Simplified approach**: Scale from 95 to 190 scrapers using parallel execution on 3 Windows PCs + AWS EC2 burst capacity.

### Architecture Overview

- **Local (Primary)**: 3 Windows PCs running 8-10 API scrapers in parallel (8-10x speedup)
- **Cloud (Burst)**: AWS EC2 on-demand instances when local capacity insufficient
- **Philosophy**: Simple scripts, static configuration, cloud when needed

### Current State vs Target

- **Current**: ~86 scrapers, 3 Windows PCs, manual sequential execution (~4-8 hours per run cycle)
- **Target**: 190 scrapers, 8-10 parallel per PC for API scrapers, 3-4 parallel for browser scrapers (~6-8 hours)
- **Cost**: ~$50-150/month (S3 backup + Slack alerts, existing PCs owned)

### Resource Limits by Scraper Type

| PC RAM | API Scrapers | Browser Scrapers | Anti-bot |
| ------ | ------------ | ---------------- | -------- |
| 8 GB   | 5-6          | 2                | 1        |
| 16 GB  | 8-10         | 3-4              | 1-2      |
| 32 GB  | 15-20        | 6-8              | 2-3      |

### EC2 Instance Types

| Scraper Type | Instance  | vCPUs | RAM   | Cost/hr | Parallel |
| ------------ | --------- | ----- | ----- | ------- | -------- |
| API          | t3.medium | 2     | 4 GB  | $0.042  | 5        |
| API (bulk)   | t3.large  | 2     | 8 GB  | $0.083  | 10       |
| Browser      | t3.xlarge | 4     | 16 GB | $0.166  | 3        |

See **docs/extra/PLAN.md** for full implementation details, code samples, AMI setup, and troubleshooting guide.

---

## Notes for Developers

1. **Date Management**: Always update `PREV_DATE` and `CURR_DATE` in config.py before runs (or use `--curr`/`--prev` flags with run_parallel.py)
2. **Parallel Execution**: Use `tools/run_parallel.py` for running multiple scrapers concurrently - automatically updates config dates
3. **Rate Limiting**: Most scrapers include built-in delays; adjust as needed
4. **Deduplication**: NPI-based deduplication is standard across all projects
5. **Error Handling**: Check `{date}/raw/` for cached responses if runs fail mid-process; run_parallel.py saves error logs to `logs/{date}/`
6. **HealthSparq Projects**: Use `python -m healthsparq` CLI - standalone package with internal browser automation (no external server needed)
7. **Output Validation**: Always run type_check.py before considering a run complete
8. **Code Quality**: See `docs/onboarding/IMPROVEMENTS.md` for prioritized enhancement recommendations (security, logging, error recovery)
9. **Issue Tracking**: Use `bd` (Beads) for issue tracking - see AGENTS.md for workflow details
10. **SQLite Storage**: `core/io/sqlite_fs.py` provides 15x faster writes vs filesystem - see `docs/restructuring/SQLITE_STORAGE_STRATEGY.md` for migration rationale
11. **Performance Fixes**: P1 issues completed - SQLiteFS write buffering, async I/O wrappers, JSONLReader context manager (see `todos/` directory)
12. **HealthSparq Unified Package**: Use `python -m healthsparq` CLI for HealthSparq projects instead of individual audiobee\_\* projects - provides configuration validation, phase control, and better error handling

---

## Recent Enhancements

### DataStore Abstraction Layer (Completed - Dec 2025)

**From commit e4e4250**: Added unified DataStore abstraction to core/io module for consistent interface across storage backends.

**What Changed**:

- **core/io/base.py**: DataStore Protocol with put/get/exists/keys/iter operations
- **core/io/factory.py**: create_store() factory function with auto-detection from file extension
- **core/io/json_files.py**: JSONFileStore implementation for individual JSON files
- **core/io/jsonl.py**: JSONLStore wrapper around existing JSONLWriter/JSONLReader
- **core/io/sqlite_fs.py**: SQLiteStore wrapper around existing SQLiteFS
- **Filepath-keyed storage**: Keys are logical paths like "provider_details/1234567890.json"
- **Backend selection**: Auto-detects from extension (.jsonl, .db) or path (directory → JSON files)

**Backend Types**:

| Backend    | Best For                        | Extension | Pros                                  | Cons                     |
| ---------- | ------------------------------- | --------- | ------------------------------------- | ------------------------ |
| JSONL      | Streaming, append-only          | .jsonl    | Fast writes, human-readable           | No random access by path |
| JSON Files | Debugging, small datasets       | /         | Easy inspection, no DB overhead       | Slow with 100k+ files    |
| SQLite     | Large datasets, exists() checks | .db       | 15x faster writes, ACID, no FS limits | Binary format            |

**Key Benefits**:

- Unified API across JSONL, SQLite, and JSON files (no more switching between different APIs)
- Configuration-driven backend selection via create_store()
- Filepath-keyed interface matches existing scraper organization patterns
- Protocol-based design allows easy addition of new backends
- Backward compatibility: legacy JSONLWriter/SQLiteFS still work directly

**Usage Pattern**:

```python
from core.io import create_store, BackendType

# Auto-detect backend from extension
store = create_store("raw_data.jsonl")  # JSONL backend
store = create_store("raw_data.db")     # SQLite backend
store = create_store("raw_data/")       # JSON Files backend

# Explicit backend selection
store = create_store("raw_data", backend=BackendType.SQLITE)

# Unified API across all backends
store.put("provider_details/1234567890.json", provider_data)
data = store.get("provider_details/1234567890.json")
if store.exists("provider_details/1234567890.json"):
    print("Found provider")

# Iterate all records
for path, record in store:
    process(record)
```

**See**: `plans/feat-datastore-abstraction.md` for complete implementation details.

---

### Provider Data Mapper Module (Completed - Dec 2025)

**From commit bddc142**: Added unified mapper module to core package for provider data normalization.

**What Changed**:

- **core/mapper/**: New module for converting raw scraper output to schema-compliant JSONL
- **HealthSparqMapper**: Handles v2 format for 23 HealthSparq projects with network/address extraction
- **CarrierMapper**: Abstract base class for custom carrier API structures (subclass per carrier)
- **Normalization utilities**: ZIP code (5 digits), phone, gender, address string building
- **NPI deduplication**: Merges duplicate records across networks with network/address/specialty merging
- **Schema validation**: Against `core/data/output_json_schema.json` using jsonschema library
- **healthsparq/phases/normalize.py**: Fixed ZIP code format (5 digits) and uszips.xlsx path (commit 45566dc)

**Mapper Types**:

| Mapper Type         | Use Case                                | Projects |
| ------------------- | --------------------------------------- | -------- |
| `HealthSparqMapper` | HealthSparq platform scrapers           | 23       |
| `CarrierMapper`     | Direct API scrapers (custom structures) | 35+      |
| `HTMLCarrierMapper` | Legacy HTML scrapers (BeautifulSoup)    | TBD      |

**Key Benefits**:

- Consistent normalization across all projects (ZIP always 5 digits, phone/address format)
- Reusable base classes reduce code duplication in individual scrapers
- Schema validation catches format issues before output generation
- Proper NPI-based deduplication with record merging logic
- HealthSparq projects now output correct format matching schema requirements

**Usage Pattern**:

```python
# HealthSparq projects (automatic)
from core.mapper import run_normalize

result = run_normalize(
    raw_dir=Path("20251227/raw/provider_details"),
    output_file=Path("20251227/processed/providers.jsonl"),
    validate=True,
)

# Carrier projects (custom mapper)
class MyCarrierMapper(CarrierMapper):
    def extract_provider(self, data: dict) -> dict:
        # Map carrier-specific fields
        ...

result = run_carrier_normalize(raw_dir, output_file, mapper=MyCarrierMapper("MyCarrier"))
```

**See**: `core/mapper/README.md` for implementation guide and examples.

---

### Comprehensive Logging Enhancement (Completed - Dec 2025)

**From commit 8193314**: Added structured logging to core and healthsparq packages to enable proper debugging and monitoring.

**What Changed**:

- **core/logging/logger.py**: Enhanced loguru-based logging with JSON output support and error-only log files
- **core session modules**: Replaced all `print()` statements with `logger` calls (browser_session.py, http_session.py, resilient_session.py)
- **core I/O modules**: Added logging to sqlite_fs.py and jsonl.py for I/O visibility
- **core config modules**: Added logging to factory.py and base.py for configuration debugging
- **healthsparq modules**: Added comprehensive logging to session.py, healthspark.py, file_writer.py, search.py, and details.py

**Logging Features**:

- Structured logging with project_name, run_id, trace_id correlation
- JSON structured output for machine parsing (`.jsonl` log files)
- Error-only log files for quick debugging (`logs/{date}/{project}_error.log`)
- Async-safe context propagation via ContextVar
- InterceptHandler for third-party library integration
- Automatic log rotation (100 MB files, 30 day retention)

**Import Pattern** (all modules use this for backwards compatibility):

```python
try:
    from core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
```

**Key Benefits**:

- Visibility into browser lifecycle, session management, and API operations
- Structured error tracking with context preservation
- Performance monitoring via elapsed time tracking
- Request/response debugging with trace_id correlation
- Silent I/O operations now logged (SQLiteFS writes, JSONL deduplication)

**See**: `plans/feat-comprehensive-logging-enhancement.md` for full implementation details.

---

### HealthSparq Library Transformation (v2.0.0 - Completed)

The `healthsparq/` package has been transformed from a CLI-only tool into an importable library with custom mapper injection support.

**What Changed**:

- **v2.0.0 release**: Dual interface (CLI + importable library)
- **Public API**: `run_scraper_sync()`, `default_mapper()`, `load_config()`, `MapperFunc`
- **Custom mappers**: Projects can inject custom normalization logic via `MapperFunc` parameter
- **Project templates**: `healthsparq/templates/` for scaffolding library-based projects
- **Pilot project**: `audiobee_christus_health_plan/` demonstrates library usage pattern

**Key Benefits Achieved**:

- Projects can customize normalization logic without forking the library
- Clean imports: `from healthsparq import run_scraper_sync, default_mapper`
- No more `sys.path.insert()` hacks in library-based projects
- Better IDE support and type checking
- Single dependency in project requirements: `healthsparq`

**Migration Path**:

- Existing CLI workflow unchanged: `python -m healthsparq run <project> --curr YYYYMMDD`
- New projects can use library pattern with templates from `healthsparq/templates/`
- Pilot: `audiobee_christus_health_plan/` shows library-based approach
- Gradual migration: Projects can adopt library pattern as needed

**Next Steps**:

- Migrate additional projects to library pattern using templates
- Document custom mapper patterns for common use cases
- Evaluate subclassing support for deeper phase customization

---

## External References

1. **AGENTS.md**: Use [AGENTS.md](AGENTS.md) for AGENTS level details and additional instructions.
<!-- END MANUAL -->

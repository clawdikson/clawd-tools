# Ideon Scraping Project

## AI Helpers

**Issue Tracking**: This project uses **Beads** (bd) - AI-native issue tracking that lives in the repo.

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

This repository contains **95+ web scrapers** for extracting provider directory data from insurance carrier websites. Each scraper targets a specific insurance plan/carrier and extracts provider information (NPIs, names, specialties, locations, network affiliations) for healthcare data aggregation.

**Purpose**: Collect and standardize provider network data from insurance carrier directories for downstream analytics and compliance reporting.

**Execution Model**: Manual runs as needed (not automated/scheduled).

<!-- END AUTO-MANAGED -->

---

<!-- AUTO-MANAGED: architecture -->

## Project Structure

```
scraping/
├── audiobee_*/              # 95+ individual scraper projects
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
├── healthsparq/             # Unified HealthSparq scraper package (replaces 23 audiobee_* projects)
│   ├── __init__.py          # Package entry point with public API
│   ├── __main__.py          # CLI entry point (python -m healthsparq)
│   ├── cli.py               # Typer-based CLI commands (list, validate, run, doctor)
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
│   ├── tests/               # Test suite (99+ tests)
│   ├── README.md            # Package documentation
│   └── pyproject.toml       # Python package metadata
│
├── healthsparq-server/      # Shared browser automation server
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
│   ├── io/                  # SQLiteFS + JSONL utilities with async support
│   │   ├── sqlite_fs.py     # SQLite-backed virtual filesystem (buffered writes, 15x faster)
│   │   ├── jsonl.py         # JSONL I/O with async support, BoundedSet deduplication
│   │   └── SQLITE_FS.md     # SQLiteFS usage documentation
│   ├── logging/             # Loguru-based logging
│   ├── validation/          # Pydantic models for provider data
│   ├── proxy/               # Multi-provider proxy orchestration
│   ├── session/             # Browser/HTTP session management
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

### 1. Carrier (35 projects)

**Direct API Integration** - REST APIs with minimal browser automation

```
Examples: audiobee_bcbs_ma, audiobee_florida_blue, audiobee_multiplan
Pattern:  config.py → index_1.py (search) → index_2.py (details) → index_3.py (map)
Tech:     httpx/requests, async pagination, NPI-based deduplication
```

**Characteristics**:

- Direct REST API calls (JSON responses)
- API keys/headers in config.py
- Geographic grid search (lat/lng + radius)
- Network ID-based plan filtering

### 2. Healthsparq (24 projects)

**Browser Automation Required** - Protected sites using healthsparq-server

```
Examples: audiobee_mvp_health, audiobee_medica, audiobee_excellus
Pattern:  healthsparq-server → index_1.py (browse) → index_2.py (extract) → run_all.py
Tech:     Puppeteer + stealth, session management, anti-detection
```

**Characteristics**:

- Requires `healthsparq-server` running on port 1018
- Session token extraction via browser
- Rate limiting with delays
- Cookie/header passthrough to API calls

**Unified Package**: 23 HealthSparq projects consolidated into `healthsparq/` package:

```bash
# CLI-based execution with YAML configuration
python -m healthsparq list                          # List available projects
python -m healthsparq validate christus_health_plan # Validate config
python -m healthsparq run christus_health_plan --curr 20251226 --prev 20251126
```

**Architecture** (standalone Python, no external server):

- `healthsparq/core/`: Shared HealthSpark API wrapper with async session management
- `healthsparq/configs/`: Per-project YAML configs (domain, insurer_code, product_code)
- `healthsparq/core/session.py`: Uses `core/session/` (ResilientBrowserSession) for browser auth → cookie extraction → fast HTTP
- `healthsparq/core/exceptions.py`: Structured exception hierarchy (AuthenticationError, APIError, SearchError, etc.)
- Configuration-driven with no hardcoded domains or plan codes

### 3. Sapphire (15 projects)

**ProviderFinderOnline Platform** - Standardized API structure

```
Examples: audiobee_bcbs_il, audiobee_molina, audiobee_carefirst
Pattern:  config.py → faceted search → provider details → location enrichment
Tech:     providerfinderonline.com API, network_id filtering
```

### 4. Anthem (4 projects)

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

**Legacy (individual audiobee\_\* projects)**:

```bash
# 1. Start browser server first
cd healthsparq-server && npm start

# 2. Run scraper (in separate terminal)
cd audiobee_mvp_health
python run_all.py
```

**Unified Package (recommended)** - Standalone Python, no external server needed:

```bash
# Run unified scraper (uses core/session for browser automation)
python -m healthsparq run christus_health_plan --curr 20251226 --prev 20251126

# Run specific phase only
python -m healthsparq run medica_sg --curr 20251226 --phase 1 # Search only
python -m healthsparq run medica_sg --curr 20251226 --phase 2 # Details only

# Dry-run mode
python -m healthsparq run excellus --curr 20251226 --dry-run
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

### healthsparq/ - Unified Scraper Package

Consolidated package for 23 HealthSparq projects with CLI-based execution:

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

**Key Features**:

- **Configuration-driven**: YAML configs in `healthsparq/configs/` (no hardcoded domains/plans)
- **Async session management**: Browser login → cookie extraction → fast HTTP requests
- **Structured exceptions**: Custom hierarchy (AuthenticationError, APIError, SearchError, etc.)
- **Context managers**: Proper resource cleanup with `async with` pattern
- **99+ tests**: Comprehensive test suite with fixtures and integration tests

**Architecture**:

- `healthsparq/core/healthspark.py`: HealthSpark API wrapper (search, profile, geocode endpoints)
- `healthsparq/core/session.py`: HealthSparqSession with ResilientBrowserSession for auth
- `healthsparq/config/schema.py`: Pydantic models for configuration validation
- `healthsparq/phases/`: Phase 1 (search), Phase 2 (details), Phase 3 (normalize)

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

- **Current**: 95 scrapers, 3 Windows PCs, manual sequential execution (~4-8 hours per run cycle)
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
6. **Browser Projects**: Ensure healthsparq-server is running for Healthsparq-type projects
7. **Output Validation**: Always run type_check.py before considering a run complete
8. **Code Quality**: See `docs/onboarding/IMPROVEMENTS.md` for prioritized enhancement recommendations (security, logging, error recovery)
9. **Issue Tracking**: Use `bd` (Beads) for issue tracking - see AGENTS.md for workflow details
10. **SQLite Storage**: `core/io/sqlite_fs.py` provides 15x faster writes vs filesystem - see `docs/restructuring/SQLITE_STORAGE_STRATEGY.md` for migration rationale
11. **Performance Fixes**: P1 issues completed - SQLiteFS write buffering, async I/O wrappers, JSONLReader context manager (see `todos/` directory)
12. **HealthSparq Unified Package**: Use `python -m healthsparq` CLI for HealthSparq projects instead of individual audiobee\_\* projects - provides configuration validation, phase control, and better error handling

## External References

1. **AGENTS.md**: Use [AGENTS.md](AGENTS.md) for AGENTS level details and additional instructions.
<!-- END MANUAL -->

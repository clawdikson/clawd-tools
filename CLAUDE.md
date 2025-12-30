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

See @AGENTS.md for landing-the-plane checklist and session completion workflow.

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
│   │   ├── pyproject.toml.template  # Python packaging with uv editable dependency support
│   │   ├── requirements.txt.template # Pip-based dependency management
│   │   ├── .env.example             # Environment config template
│   │   ├── .gitignore.template      # Output directory ignores
│   │   └── README.md.template       # Usage instructions with uv installation guide
│   ├── tests/               # Test suite (99+ tests)
│   ├── CLAUDE.md            # Package documentation and conventions
│   ├── README.md            # Package documentation
│   └── pyproject.toml       # Python package metadata (v2.0.0)
│
├── healthsparq-server/      # Legacy browser automation server (deprecated - use healthsparq package instead)
│   ├── server.js            # Node.js/Puppeteer server (port 1018)
│   └── CLAUDE.md            # Server documentation
│
├── output_generator/        # Legacy QA utilities (deprecated - use core/qa instead)
│   └── CLAUDE.md            # Migration documentation
│
├── tools/                   # Execution and automation tools
│   ├── run_parallel.py      # Parallel scraper execution with retry logic
│   ├── upload_to_drive.py   # Google Drive 7z archive uploader (CLI)
│   ├── drive_uploader.py    # DriveUploader class with dual auth (service account + OAuth 2.0), resumable upload, folder validation
│   ├── xlsx_to_clickup.py   # Generate compact PNG screenshots from XLSX reports (matplotlib), send via Gmail, or upload to ClickUp
│   ├── project_config.py    # Project config loader (Audiobee config.py + HealthSparq YAML)
│   ├── drive_folder_mapping.json  # Project -> Google Drive folder ID mapping
│   ├── oauth_credentials.json     # OAuth 2.0 client credentials (shared: Drive + Gmail)
│   ├── oauth_token.json           # Cached OAuth tokens for Drive API
│   ├── gmail_token.json           # Cached OAuth tokens for Gmail API
│   ├── requirements.txt     # Dependencies (google-api-python-client, google-auth-oauthlib, typer, tqdm, matplotlib)
│   ├── tests/               # Test suite for tools
│   │   ├── test_project_config.py    # Unit tests for config detection/parsing
│   │   ├── test_drive_integration.py # Integration tests for Drive uploads
│   │   └── test_xlsx_to_clickup.py   # Unit tests for screenshot generation and email/ClickUp upload
│   └── README.md            # Tools documentation (validation, migration, upload)
│
├── scripts/                 # Development and setup scripts
│   └── clone-submodules.sh  # Submodule management (init/update/fresh/shallow/standalone)
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
│   ├── qa/                  # QA utilities v1.0 (migrated from output_generator)
│   │   ├── __init__.py      # Public API: validate, compare, sample, report, generate_debug_reports
│   │   ├── __main__.py      # CLI entry point
│   │   ├── base.py          # QAResult, QAOutcome, QAStatus, exception hierarchy
│   │   ├── config.py        # QASettings (Pydantic Settings)
│   │   ├── validator.py     # Schema validation with fastjsonschema (100x faster)
│   │   ├── comparison.py    # Cross-run diff analysis with Polars (10x faster)
│   │   ├── sampler.py       # Reservoir sampling with archive creation
│   │   ├── reporter.py      # Excel state reports with xlsxwriter streaming
│   │   ├── statistics.py    # State-level provider counts
│   │   ├── debug_reports.py # Debug Excel report generation (12 sheets + specialty pivot)
│   │   ├── cli.py           # Typer CLI framework
│   │   └── README.md        # QA module documentation
│   ├── data/                # Shared reference data with cached loading
│   │   ├── __init__.py      # Public exports for data loaders
│   │   ├── loader.py        # @cache decorators for lazy-loaded data
│   │   ├── output_json_schema.json  # Provider output schema
│   │   ├── uszips.xlsx      # ZIP-to-state mapping
│   │   └── us_states_coordinates.json  # State geographic data
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
- Five-phase pipeline: search → details → normalize → qa → report (phases 4-5 optional)
- Project scaffolding templates in `healthsparq/templates/`

**Architecture**:

- `healthsparq/api.py`: High-level API (`run_scraper_sync`, `ScraperResult`, `PhaseResult`)
- `healthsparq/phases/`: Search, Details, Normalize, QA, Report phases
- `healthsparq/templates/`: Project scaffolding (run.py, mapper.py, .env.example)
- `healthsparq/core/exceptions.py`: Structured exception hierarchy (AuthenticationError, APIError, SearchError, etc.)
- Public API exports: `run_scraper_sync`, `default_mapper`, `load_config`, `MapperFunc`, `run_qa_sync`, `run_report_sync`

**CLI Usage**:

```bash
python -m healthsparq list                          # List 23 available projects
python -m healthsparq validate christus_health_plan # Validate config
python -m healthsparq run christus_health_plan --curr 20251226 --prev 20251126
python -m healthsparq run medica_sg --curr 20251226 --phase 1 # Run specific phase (1-5)
python -m healthsparq run medica_sg --curr 20251226 --qa      # Run QA phase
python -m healthsparq run medica_sg --curr 20251226 --report  # Run Report phase
python -m healthsparq doctor                                  # Validate all configs
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

# Run QA phase (Phase 4) - validation + comparison
result = run_scraper_sync(config, "20251227", prev_date="20251127", run_qa=True)

# Run Report phase (Phase 5) - Excel + samples
result = run_scraper_sync(config, "20251227", run_report=True, sample_count=20)
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

### Submodule Setup

This project uses git submodules for shared utilities (core, healthsparq, output_generator). Use the helper script to manage them:

```bash
# Standard submodule init/update
./scripts/clone-submodules.sh

# Fresh clone (removes existing directories first)
./scripts/clone-submodules.sh --fresh

# Shallow clone (faster, depth=1)
./scripts/clone-submodules.sh --shallow

# Clone as standalone repos (not submodules)
./scripts/clone-submodules.sh --standalone

# Show help
./scripts/clone-submodules.sh --help
```

**Features**:

- Dynamically parses `.gitmodules` (no hardcoded paths)
- Supports fresh clone, shallow clone, and standalone mode
- Auto-detects and processes all submodules
- Verifies successful clone/update

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
# Install package (one-time setup, choose one)
cd healthsparq
uv pip install -e . # Recommended (fastest with uv)
pip install -e .    # Standard pip

# List available projects
python -m healthsparq list

# Run scraper
python -m healthsparq run medica_sg --curr 20251226 --prev 20251110

# Run specific phase only
python -m healthsparq run medica_sg --curr 20251226 --phase 1 # Search
python -m healthsparq run medica_sg --curr 20251226 --phase 2 # Details
python -m healthsparq run medica_sg --curr 20251226 --phase 3 # Normalize
python -m healthsparq run medica_sg --curr 20251226 --phase 4 # QA (validation + comparison)
python -m healthsparq run medica_sg --curr 20251226 --phase 5 # Report (Excel + samples)

# QA phase with granular control
python -m healthsparq run medica_sg --curr 20251226 --qa                      # Full QA
python -m healthsparq run medica_sg --curr 20251226 --validate                # Validation only (4a)
python -m healthsparq run medica_sg --curr 20251226 --prev 20251126 --compare # Comparison only (4b)

# Report phase with granular control
python -m healthsparq run medica_sg --curr 20251226 --report                         # Full report
python -m healthsparq run medica_sg --curr 20251226 --excel                          # Excel only (5a)
python -m healthsparq run medica_sg --curr 20251226 --samples-only --sample-count 20 # Samples only (5b)

# Validate configuration
python -m healthsparq validate christus_health_plan
python -m healthsparq doctor # Validate all configs
```

### Validating Output

```bash
# NEW: Use core/qa module (100x faster validation, 10x faster comparison)
python -m core.qa validate audiobee_bcbs_il/20251227/processed/providers.jsonl
python -m core.qa compare --curr 20251227 --prev 20251126 --project audiobee_bcbs_il
python -m core.qa sample audiobee_bcbs_il/20251227/processed/providers.jsonl --count 10
python -m core.qa report audiobee_bcbs_il --curr 20251227 --prev 20251126

# Legacy (deprecated - will be removed)
python output_generator/type_check.py audiobee_bcbs_il/
python output_generator/comparison_creator.py audiobee_bcbs_il/
```

### Uploading to Google Drive

```bash
# Upload 7z archive to Google Drive (requires setup - see tools/README.md)
# Audiobee project (reads CURR_DATE from config.py)
python tools/upload_to_drive.py audiobee_bcbs_il

# HealthSparq project (requires --date since no config.py)
python tools/upload_to_drive.py christus_health_plan --date 20251227

# Override date for any project
python tools/upload_to_drive.py audiobee_bcbs_il --date 20251210

# Dry run (validate without uploading)
python tools/upload_to_drive.py audiobee_bcbs_il --dry-run

# List configured projects
python tools/upload_to_drive.py list-projects

# Validate project configuration
python tools/upload_to_drive.py validate audiobee_bcbs_il
```

**Setup Requirements**:

**Service Account (Shared Drives/External Access)**:
1. Create Google Cloud project and enable Drive API
2. Create service account and download JSON credentials
3. Save credentials to `tools/google_drive_credentials.json`
4. Share Drive folders with service account email
5. Add folder mappings to `tools/drive_folder_mapping.json`

**OAuth 2.0 (Personal Drive Folders)**:
1. Create OAuth 2.0 client in Google Cloud Console
2. Download credentials and save to `tools/oauth_credentials.json`
3. Add folder mappings to `tools/drive_folder_mapping.json`
4. First run will prompt browser login and save token to `tools/oauth_token.json`
5. Token auto-refreshes on subsequent runs (no re-authentication)

See `tools/README.md` for detailed setup instructions.

### Report Distribution (Email & ClickUp)

Generate PNG screenshots from XLSX state reports and distribute via email or ClickUp:

```bash
# Send screenshot via email (Gmail OAuth)
python tools/xlsx_to_clickup.py email audiobee_bcbs_il --to recipient@example.com

# Send to multiple recipients with CC
python tools/xlsx_to_clickup.py email audiobee_bcbs_il --to r1@example.com --to r2@example.com --cc manager@example.com

# Custom subject and body
python tools/xlsx_to_clickup.py email audiobee_bcbs_il --to recipient@example.com --subject "Weekly Report" --body "Please review"

# Full workflow: generate screenshot + upload to ClickUp
python tools/xlsx_to_clickup.py run audiobee_bcbs_il --task CU12345

# With custom comment
python tools/xlsx_to_clickup.py run audiobee_bcbs_il --task CU12345 --comment "December run results"

# Override date
python tools/xlsx_to_clickup.py run audiobee_bcbs_il --task CU12345 --curr 20251210

# Dry run (validate without sending/uploading)
python tools/xlsx_to_clickup.py email audiobee_bcbs_il --to test@example.com --dry-run
python tools/xlsx_to_clickup.py run audiobee_bcbs_il --task CU12345 --dry-run

# Generate screenshot only (no send/upload)
python tools/xlsx_to_clickup.py generate audiobee_bcbs_il --output report.png

# Upload existing image to ClickUp
python tools/xlsx_to_clickup.py upload report.png --task CU12345
```

**Setup Requirements**:

For Email (Gmail OAuth):
1. Uses same OAuth credentials as Google Drive (`tools/oauth_credentials.json`)
2. Enable Gmail API in Google Cloud Console
3. First run opens browser for login, saves token to `tools/gmail_token.json`
4. Token auto-refreshes on subsequent runs

For ClickUp:
1. Set ClickUp API token: `export CLICKUP_API_TOKEN='pk_...'`
2. Install dependencies: `pip install dataframe-image openpyxl matplotlib`

**Features**:
- Auto-detects XLSX file from project's processed directory
- Generates compact summary screenshots with matplotlib (no dataframe-image dependency)
- Shows key stats: In-scope States, In-Scope/Out-of-Scope Providers (Unique/Non-Unique)
- Shared OAuth setup for Drive and Gmail (single credentials file)
- Email: Sends via Gmail API with attachments
- ClickUp: Uploads with automatic filename and metadata comment
- Supports both state_with_surrounding and state_only count files

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
- `pyproject.toml.template`: Python packaging with uv support (recommended)
- `requirements.txt.template`: Pip-based dependency management (alternative)
- `.env.example`: Environment config (proxy, browser settings)
- `README.md.template`: Usage instructions and project documentation

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

### core/qa - QA Utilities v1.0

**Migration Status**: Migrated from output_generator/ (Dec 2025) with performance optimizations.

Unified QA toolkit for validation, comparison, sampling, and reporting:

```bash
# Install (one-time)
cd core && pip install -e ".[qa]"

# CLI Usage
python -m core.qa validate providers.jsonl
python -m core.qa validate providers.jsonl --schema custom_schema.json --timeout 600
python -m core.qa compare --curr 20251227 --prev 20251126
python -m core.qa compare --curr 20251227 --prev 20251126 --project ./audiobee_bcbs_il
python -m core.qa sample providers.jsonl --count 20 --format zip
python -m core.qa report audiobee_bcbs_il --curr 20251227 --prev 20251126
python -m core.qa debug providers.jsonl --curr 20251227 --output processed
python -m core.qa version
```

**Library Usage**:

```python
from core.qa import validate, compare, sample, report, generate_debug_reports

# Validate with schema (100x faster with fastjsonschema)
result = validate("providers.jsonl", schema_path=None, deduplicate=True)
if result.is_success:
    print(f"Valid: {result.metrics.valid_records}/{result.metrics.total_records}")
    print(f"Unique NPIs: {result.metrics.unique_npis}")

# Compare runs (10x faster with Polars)
result = compare(curr_path="20251227/processed", prev_path="20251126/processed")
print(f"Added: {result.metrics.added}, Removed: {result.metrics.removed}")

# Generate samples with reservoir sampling
result = sample("providers.jsonl", output_dir="samples", count=10, format="zip")

# Generate state-level Excel report
result = report(project_name="audiobee_bcbs_il", curr_date="20251227", prev_date="20251126")

# Generate debug Excel reports (12 detail sheets + specialty pivot)
result = generate_debug_reports(
    input_file="providers.jsonl",
    output_dir="processed",
    curr_date="20251227",
)
print(f"Generated {len(result.data['files'])} debug files")
```

**Performance Improvements**:

- **fastjsonschema**: 100x faster than jsonschema for validation
- **Polars**: 10x faster DataFrame operations vs pandas
- **BoundedSet**: Memory-safe deduplication with 100k LRU cache
- **Streaming**: Single-pass processing to avoid multiple file reads
- **Timeout protection**: Default 300s with run_with_timeout()

**Key Features**:

- QAResult/QAOutcome: Unified result structure with status, metrics, errors
- Exception hierarchy: ValidationError, ComparisonError, ConfigurationError, QATimeoutError
- Timeout protection: All operations have configurable timeouts
- Graceful degradation: Handles missing prev_date, partial data
- Structured logging: Integrated with core/logging module

**Debug Reports** (NEW):

Generate detailed Excel reports for data analysis and QA:

- `debug_data-{date}.xlsx`: 12 sheets with unique value analysis (Networks, Provider Names, NPI, Zip Code Network, Zip Codes, Titles, Addresses, Phones, Languages, Groups, Hospitals, Specialties)
- `debug_specialty_network-{date}.xlsx`: Pivot table of Specialty+ZIP × Network combinations
- Matches output format from legacy `output_generator/type_check.py`
- Use via CLI: `python -m core.qa debug providers.jsonl --curr 20251227`
- Use via library: `generate_debug_reports(input_file, output_dir, curr_date)`
- Integrated into healthsparq project templates via `debug` command

See `core/qa/README.md` for complete documentation.

### output_generator (Deprecated)

**Migration Notice**: This directory is deprecated. Use `core/qa` module instead for all QA operations.

Legacy utilities (will be removed in future versions):

```bash
# Legacy commands (deprecated)
python output_generator/type_check.py audiobee_*/
python output_generator/sample_generator.py audiobee_*/
python output_generator/comparison_creator.py audiobee_*/
python output_generator/report_generator.py audiobee_*/
```

**Migration path**: See `docs/migration/OUTPUT_GENERATOR_TO_CORE_QA.md` for migration guide.

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

### core/qa - QA Utilities

Migrated from output_generator with performance improvements:

**CLI Usage**:

```bash
python -m core.qa validate providers.jsonl
python -m core.qa compare --curr 20251227 --prev 20251126
python -m core.qa sample providers.jsonl --count 10
python -m core.qa report project_name --curr 20251227
```

**Python API**:

```python
from core.qa import validate, compare, sample, report

# Validate output schema
result = validate("providers.jsonl")
if result.is_success:
    print(f"Valid: {result.metrics.valid_records}")

# Compare runs
result = compare(curr_path, prev_path)
print(f"Added: {result.metrics.added}")
```

**Key Features**:

- fastjsonschema for 100x faster validation
- Polars for 10x faster comparison
- Memory-bounded deduplication (BoundedSet)
- Timeout protection (default 5 minutes)
- Streaming Excel generation

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
13. **Google Drive Uploads**: Use `tools/upload_to_drive.py` to upload 7z archives - auto-detects project type and loads dates from config - see `tools/README.md` for setup
14. **ClickUp Report Upload**: Use `tools/xlsx_to_clickup.py` to generate PNG screenshots from XLSX state reports and upload to ClickUp tasks with automatic metadata - requires CLICKUP_API_TOKEN env var
15. **Credentials Security**: Never commit `tools/google_drive_credentials.json` or service account files - already excluded in .gitignore

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

### XLSX Screenshot Upload to ClickUp (Completed - Dec 2025)

**From commit f8b9c05**: Added CLI tool to generate PNG screenshots from XLSX state reports and upload to ClickUp with automatic metadata.

**What Changed**:

- **tools/xlsx_to_clickup.py**: Typer-based CLI tool with three commands (run, generate, upload)
- **tools/project_config.py**: Unified config loader supporting both Audiobee config.py and HealthSparq YAML
- **Screenshot generation**: Uses dataframe-image with matplotlib backend (cross-platform, no browser dependency)
- **ClickUp API client**: Exponential backoff on rate limits, automatic retry with max 3 attempts
- **Dry-run mode**: Validate paths and configuration without uploading
- **14 unit tests**: Comprehensive test coverage in tools/tests/test_xlsx_to_clickup.py
- **pyproject.toml**: Added dependencies (dataframe-image, matplotlib, openpyxl)

**Key Features**:

- Reads project configuration to auto-detect CURR_DATE (no manual date entry)
- Locates XLSX files with fallback pattern (state_with_surrounding > state_only)
- Generates styled PNG screenshots with custom DPI (default 150)
- Uploads to ClickUp with task ID and optional comment
- Proper error handling with descriptive messages
- Follows project conventions (Typer CLI, config patterns from healthsparq/core)

**Usage Pattern**:

```bash
# Full workflow: generate + upload to ClickUp
uv run python tools/xlsx_to_clickup.py run audiobee_bcbs_il --task CU12345

# Override date (instead of reading from config.py)
uv run python tools/xlsx_to_clickup.py run audiobee_bcbs_il --task CU12345 --curr 20251227

# Generate screenshot only (no upload)
uv run python tools/xlsx_to_clickup.py generate audiobee_bcbs_il --output report.png

# Upload existing image
uv run python tools/xlsx_to_clickup.py upload report.png --task CU12345 --comment "Weekly report"

# Dry run (validate without uploading)
uv run python tools/xlsx_to_clickup.py run audiobee_bcbs_il --dry-run
```

**Implementation Details**:

- File resolution priority: `{project}-{date}-state_with_surrounding-counts.xlsx` > `{project}-{date}-state_only-counts.xlsx`
- Environment variable: `CLICKUP_API_TOKEN` (required for upload)
- Screenshot styling: Blue header (#4472C4), zebra striping, centered text
- Rate limiting: Exponential backoff (2^retry seconds) with max 3 retries
- Response validation: Checks for attachment_id and upload confirmation

**See**: `plans/feat-xlsx-screenshot-clickup-upload.md` for complete implementation plan and `tools/README.md` for usage documentation.

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

### HealthSparq-Core Consolidation (Completed - Dec 2025)

**From commit 03bd525**: Successfully consolidated duplicate normalization utilities from healthsparq to core package.

**Problem Solved**: The `healthsparq/` package was duplicating ~75 lines of normalization/deduplication utilities from `core/` package, including `normalize_zip_code`, `deduplicate_by_npi`, `merge_provider_data`, and the `MapperFunc` type alias. This created maintenance burden (bug fixes in two places) and drift risk.

**Changes Implemented** (Phase 1 - Dec 28, 2025):

- **Import normalization utilities from core** (~75 LOC reduction)
  - `MapperFunc` type from `core/mapper/base.py`
  - `normalize_zip_code` from `core/mapper/normalize.py`
  - `deduplicate_by_npi`, `merge_provider_records` from `core/mapper/dedup.py`
  - **Kept local**: `clean_network_name()` (7 LOC, project-specific "medica_sg" → "medica" replacement)
  - **File modified**: `healthsparq/phases/normalize.py` only

**Impact**: All 23 HealthSparq projects now use single source of truth from core package. Output remains byte-identical. No API changes for library users.

**Rejected Phases** (Reviewer consensus - DHH & Kieran):

- **Phase 2**: Exception hierarchy unification (no practical value - "inheritance for inheritance's sake")
- **Phase 3**: Retry logic consolidation (intentionally different - HTTP vs browser session levels)
- **Phase 4**: Deprecation warnings (unnecessary for internal code)

**Verification**:

- All import-related tests pass
- Output byte-identical before/after
- No runtime behavior changes

**See**:

- `plans/feat-healthsparq-core-consolidation.md` - Master plan
- `plans/context/healthsparq-core-consolidation-phase*.md` - Detailed phase documentation with reviewer rationale

---

### HTTP Retry Logic Consolidation (Completed - Dec 2025)

**From commits f1d0dea, cabeb5d**: Consolidated duplicate HTTP retry logic from healthsparq to core package.

**Problem Solved**: The `healthsparq/core/session.py` contained ~40 lines of duplicate HTTP retry logic (exponential backoff, auth error handling) that should have been in `core/session/http_session.py`. This created:

- Code duplication (retry logic in two places)
- Inconsistent retry behavior across projects
- Maintenance burden (bug fixes needed in multiple locations)

**Changes Implemented** (3 phases - Dec 28, 2025):

**Phase 1** - Add Retry Logic to `core/session/http_session.py`:

- Added `RetryConfig` dataclass with configurable parameters (max_retries, backoff_factor, retry_on_status)
- Added `_request_with_retry()` method with exponential backoff
- Added `on_auth_error` callback hook for session invalidation on 401/403
- Updated `get()` and `post()` to use retry wrapper
- Exported `RetryConfig` from `core/session/__init__.py`

**Phase 2** - Simplify `healthsparq/core/session.py`:

- Removed duplicate `_request_with_retry()` method (~40 LOC)
- Added `_invalidate_session()` callback for auth error handling
- Updated `login()` to pass `RetryConfig` and `on_auth_error` to HttpSession
- Simplified `get()` and `post()` to delegate directly to HttpSession
- Added fallback handling for legacy environments without RetryConfig

**Phase 3** - Testing (Pending):

- Test coverage for retry logic in core/tests/test_session.py
- Updated healthsparq tests for simplified session

**Key Features**:

- **Exponential backoff**: Configurable backoff_factor (default 2.0) with max_backoff cap (30s)
- **Configurable retries**: Default 5 retries for 429/500-504 status codes
- **Auth error callbacks**: Session invalidation on 401/403 via `on_auth_error` hook
- **Backward compatible**: All parameters optional with sensible defaults

**Impact**:

- All projects using `HttpSession` now get retry logic automatically
- ~40 LOC removed from healthsparq (single source of truth in core)
- No behavior changes for existing scrapers
- Consistent retry configuration across all projects

**See**:

- `plans/refactor-healthsparq-retry-consolidation.md` - Master plan
- `plans/context/http-retry-consolidation-phase*.md` - Detailed phase documentation

---

### Google Drive 7z Archive Upload (Completed - Dec 2025)

**From commits 5eaad0e, 6b610aa, c269b2b**: Added automated Google Drive upload functionality for scraper output archives.

**Problem Solved**: Manual uploading of 7z archives to Google Drive was error-prone (wrong folder) and time-consuming for 86+ projects. No automated way to upload after scraping runs completed.

**What Changed**:

- **tools/upload_to_drive.py**: CLI tool with Typer interface for uploading archives
- **tools/drive_uploader.py**: DriveUploader class with dual authentication (service account + OAuth 2.0), resumable upload support (10 MB chunks, exponential backoff). Added validate_folder_access() for pre-upload permission checks. Enhanced error logging with chunk-level details (commits c269b2b, 838c69c, 6b610aa)
- **tools/project_config.py**: Project config loader supporting both Audiobee (config.py) and HealthSparq (YAML) projects
- **tools/drive_folder_mapping.json**: JSON mapping of project names to Google Drive folder IDs
- **tools/oauth_credentials.json**: OAuth 2.0 client credentials for personal Drive access
- **tools/oauth_token.json**: Cached OAuth tokens with automatic refresh
- **tools/tests/**: Test suite with unit tests (project_config) and integration tests (Drive uploads)
- **audiobee_bcbs_il/run_all.py**: Integration with `upload_archive()` API for automatic upload after QA with OAuth support
- **.gitignore**: Added exclusions for Google Drive credentials (google_drive_credentials.json, oauth_credentials.json, oauth_token.json, service-account*.json)

**Key Features**:

- **Dual authentication modes**: Service account (unattended automation) or OAuth 2.0 (personal Drive folders)
- **OAuth token caching**: Browser login once, auto-refresh on subsequent runs
- **Resumable uploads**: Handles network interruptions with exponential backoff (max 5 retries)
- **Folder validation**: Pre-upload access checks with validate_folder_access() to catch permission errors early
- **Auto-detection**: Detects project type (Audiobee vs HealthSparq) and loads dates from config
- **Progress reporting**: tqdm-based progress bars with elapsed/remaining time
- **Enhanced error logging**: Chunk-level debug logs and detailed HTTP error messages (404/403 with content)
- **Dry-run mode**: Validate configuration without uploading
- **Structured logging**: Integration with core.logging for debugging
- **upload_archive() API**: Programmatic API for run_all.py integration with OAuth support

**Usage Pattern**:

```bash
# CLI usage
python tools/upload_to_drive.py audiobee_bcbs_il                  # Auto-loads CURR_DATE
python tools/upload_to_drive.py christus_health_plan --date 20251227  # HealthSparq
python tools/upload_to_drive.py audiobee_bcbs_il --dry-run       # Validate only

# Programmatic usage (from run_all.py)
from tools.drive_uploader import upload_archive

# With OAuth 2.0 (personal Drive folders)
result = upload_archive(
    project_name=config.PROJECT_NAME,
    curr_date=config.CURR_DATE,
    base_path=".",  # Archive at ./{CURR_DATE}/{CURR_DATE}.7z
    use_oauth=True,  # Use OAuth instead of service account
)
print(f"Uploaded: {result.get('webViewLink')}")

# With service account (Shared Drives)
result = upload_archive(
    project_name=config.PROJECT_NAME,
    curr_date=config.CURR_DATE,
    base_path=".",
    use_oauth=False,  # Default: service account
)
print(f"Uploaded: {result.get('webViewLink')}")
```

**Setup Requirements**:

**Service Account (Shared Drives/External Access)**:
1. Create Google Cloud project and enable Drive API
2. Create service account and download JSON credentials
3. Save credentials to `tools/google_drive_credentials.json`
4. Share Drive folders with service account email (from credentials JSON)
5. Add folder mappings to `tools/drive_folder_mapping.json`

**OAuth 2.0 (Personal Drive Folders)**:
1. Create OAuth 2.0 client in Google Cloud Console
2. Download credentials and save to `tools/oauth_credentials.json`
3. Add folder mappings to `tools/drive_folder_mapping.json`
4. First run will prompt browser login and save token to `tools/oauth_token.json`
5. Token auto-refreshes on subsequent runs (no re-authentication)

**Impact**:

- Eliminates manual Drive uploads for 86+ projects
- Prevents wrong-folder upload errors
- Enables unattended automation (service account auth)
- Reduces post-scraping time (automatic upload in run_all.py)

**See**:

- `plans/feat-google-drive-7z-upload.md` - Complete implementation plan with 12 tasks
- `tools/README.md` - Setup instructions and troubleshooting guide

---

### ClickUp Report Upload Tool (Completed - Dec 2025)

**From commits 838c69c, 59f3d74**: Added automated ClickUp report upload functionality for state count XLSX files with compact summary screenshot format.

**Problem Solved**: Manual screenshot generation from XLSX reports and ClickUp upload was time-consuming. Needed automated way to share QA results with stakeholders.

**What Changed**:

- **Compact summary format** (commit 59f3d74): Replaced full DataFrame table with 5-row summary showing In-scope States, In-Scope/Out-of-Scope Providers (Unique/Non-Unique)
- **tools/xlsx_to_clickup.py**: Typer-based CLI tool for screenshot generation and ClickUp upload (commit f8b9c05)
- **Matplotlib-based rendering**: Uses matplotlib directly instead of dataframe-image for cleaner output and better control
- **pyproject.toml**: Added dependencies (google, google-auth, matplotlib, openpyxl)
- **tools/drive_uploader.py**: Added validate_folder_access() method for pre-upload permission checks. Added supportsAllDrives flag for Shared Drive compatibility. Enhanced error logging with chunk-level details and HTTP error content decoding (commit 838c69c)
- **Test coverage**: Updated test fixtures to use new XLSX format with Description/Data columns

**Key Features**:

- **Auto-detection**: Finds state count XLSX files in project's processed directory
  - Primary: `{project}-{date}-state_with_surrounding-counts.xlsx`
  - Fallback: `{project}-{date}-state_only-counts.xlsx`
- **PNG generation**: Compact summary screenshots with matplotlib (no dataframe-image dependency)
- **Summary format**: Extracts first 5 rows from XLSX (Description/Data columns) showing key provider counts
- **Styled output**: Clean background box with bold labels and colored values
- **ClickUp integration**: Uploads with automatic filename and metadata comment
- **Lazy imports**: Google Drive libraries loaded only when needed (prevents import errors)
- **Project config integration**: Uses existing `project_config.py` for date/path resolution

**Usage Pattern**:

```bash
# Full workflow: generate + upload
python tools/xlsx_to_clickup.py run audiobee_bcbs_il --task CU12345

# With custom comment
python tools/xlsx_to_clickup.py run audiobee_bcbs_il --task CU12345 --comment "December results"

# Generate screenshot only
python tools/xlsx_to_clickup.py generate audiobee_bcbs_il --output report.png

# Upload existing image
python tools/xlsx_to_clickup.py upload report.png --task CU12345
```

**Setup Requirements**:

1. Set ClickUp API token: `export CLICKUP_API_TOKEN='pk_...'`
2. Install dependencies: `pip install matplotlib openpyxl`

**Impact**:

- Automates QA report sharing with stakeholders
- Generates clean, compact summary screenshots (5-row summary instead of full table)
- Reduces manual copy-paste errors
- Enables programmatic report upload from run_all.py
- No longer requires dataframe-image library (matplotlib-only rendering)

---

### BrowserSession Backend Selection (Planned - Dec 2025)

**Implementation plan**: `plans/feat-browser-session-camoufox.md` - Add selectable browser backend to `core/session/BrowserSession` enabling choice between Patchright, Playwright, and Camoufox.

**Planned Architecture**:

- **BrowserType enum**: `PATCHRIGHT` (default), `PLAYWRIGHT`, `CAMOUFOX`
- **Backend selection**: Via `browser_type` parameter (enum or string)
- **Lazy imports**: Backend libraries loaded only when selected
- **Concurrency preservation**: Existing patterns unchanged (\_init_lock, \_request_semaphore, \_active_cond)
- **Backward compatibility**: Default to PATCHRIGHT (current behavior)

**New Dependencies** (when implemented):

- `playwright>=1.55.0` - Standard Playwright library
- `camoufox[geoip]>=0.4.11` - Firefox-based anti-detection browser

**Backend Comparison**:

| Backend    | Engine   | Anti-Detection | Use Case                 |
| ---------- | -------- | -------------- | ------------------------ |
| PATCHRIGHT | Chromium | Medium         | Default, most sites      |
| PLAYWRIGHT | Chromium | Low            | Sites without detection  |
| CAMOUFOX   | Firefox  | High           | Anti-bot protected sites |

**Implementation Tasks** (8 total):

1. Add BrowserType enum and dependencies to `core/session/backend.py`
2. Add browser_type parameter to BrowserSession `__init__`
3. Implement backend-specific initialization (\_init_playwright, \_init_camoufox)
4. Implement backend-specific cleanup (Camoufox uses `__aexit__` pattern)
5. Update ResilientBrowserSession to pass through browser_type
6. Update HealthSparqSession with browser_type support (optional)
7. Write unit tests for backend selection and initialization
8. Update `core/CLAUDE.md` documentation

**Key Features**:

- Unified async interface across all backends
- Camoufox uses AsyncCamoufox context manager (different from Playwright/Patchright)
- Backend-specific proxy configuration handling
- Preserves existing session lifecycle and error handling

**See**: `plans/feat-browser-session-camoufox.md` for complete 8-task implementation plan with code snippets.

---

## External References

1. **AGENTS.md**: Use [AGENTS.md](AGENTS.md) for AGENTS level details and additional instructions.
<!-- END MANUAL -->

## Subdirectory Contexts

Auto-load when accessing these directories:

- `healthsparq/CLAUDE.md` - HealthSparq library v2.0
- `core/CLAUDE.md` - Shared utilities v3.0
- `output_generator/CLAUDE.md` - QA utilities

## Essential Rules

1. Always update `PREV_DATE`/`CURR_DATE` in config.py before runs
2. Prefer `core/` implementations over reinventing
3. Run `type_check.py` before completing runs
4. Use `bd` for issue tracking (not TodoWrite for multi-session work). Provide enough context in the description along with important information for future usage.
5. Create enough contexts in .md files and delegate tasks to subagents.

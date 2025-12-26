# Ideon Scraping Project

## Overview

This repository contains **95+ web scrapers** for extracting provider directory data from insurance carrier websites. Each scraper targets a specific insurance plan/carrier and extracts provider information (NPIs, names, specialties, locations, network affiliations) for healthcare data aggregation.

**Purpose**: Collect and standardize provider network data from insurance carrier directories for downstream analytics and compliance reporting.

**Execution Model**: Manual runs as needed (not automated/scheduled).

---

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
├── docs/                    # Project documentation
│   ├── README.md            # Main documentation hub
│   ├── site-type-mapping.md # Projects by infrastructure type
│   ├── quick-reference.md   # Common operations guide
│   ├── IMPROVEMENTS.md      # Prioritized enhancement recommendations (P0-P3)
│   ├── SCALABILITY_BEST_PRACTICES.md  # Scalability patterns for 100+ scrapers
│   └── architecture/        # Detailed architecture docs
│
├── implementation_research/ # Shared utilities implementation research
│   ├── 00_EXECUTIVE_SUMMARY.md        # Research overview and findings
│   ├── 01_CODING_FRAMEWORK.md         # Architecture patterns, file organization
│   ├── 02_CONFIG_SYSTEM.md            # Pydantic Settings implementation
│   ├── 03_FILE_UTILITIES.md           # JSON/JSONL I/O classes
│   ├── 04_LOGGING.md                  # Logger design with loguru
│   ├── 05_VALIDATION.md               # Raw file + schema validation
│   ├── 06_REPORT_GENERATION.md        # Integration plan
│   └── 07_IMPLEMENTATION_PLAN.md      # Phased rollout strategy
│
├── data/                    # Shared reference data
│   ├── specialties.json     # Specialty code mappings
│   └── us_zip_fips_county.xlsx  # Geographic reference
│
└── PLAN.md                  # Infrastructure scaling implementation plan
```

---

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

### 3. Sapphire (15 projects)
**ProviderFinderOnline Platform** - Standardized API structure

```
Examples: audiobee_bcbs_il, audiobee_molina, audiobee_carefirst
Pattern:  config.py → faceted search → provider details → location enrichment
Tech:     providerfinderonline.com API, network_id filtering
```

**Characteristics**:
- Consistent API endpoints across carriers
- x-api-key authentication
- Transaction ID tracking
- Faceted specialty/location search

### 4. Anthem (4 projects)
**Wellpoint Infrastructure** - Multi-phase with intelligent filtering

```
Examples: audiobee_anthem, audiobee_amerigroup, audiobee_healthy_blue
Pattern:  search → filter → details → affiliations → networks
Tech:     Brand-specific URLs, complex network hierarchies
```

**Characteristics**:
- Brand variations (Anthem, Amerigroup, Simply, Healthy Blue)
- State-specific network configurations
- Multi-level affiliation tracking

**Advanced Implementation** (`audiobee_anthem_new`):

**Two-Process Architecture (Current)**:
- Three-layer architecture: Task Server (FastAPI on port 8001) → Browser Pool (Camoufox) → Data Processing
- Camoufox browser with anti-detection (humanize, geoip, stealth)
- Request interception with TTL caching (30 min)
- 10 parallel browser workers with process isolation
- HTTP communication between task server and browsers (GET/POST /tasks)

**Single-Process Architecture (Alternative - `single_process_implementation/`)**:
- Unified process using `page.expose_function()` for Python ↔ JavaScript communication
- `asyncio.Queue` for task management (eliminates HTTP overhead)
- Direct function calls: `window.getTask()`, `window.submitResult()`, `window.getToken()`
- Same Camoufox configuration (preserves anti-detection capabilities)
- Simplified deployment: one process instead of two
- See `audiobee_anthem_new/SINGLE_PROCESS_PLAN.md` for implementation details

See `audiobee_anthem_new/ANTHEM_IMPROVEMENT.md` for architectural analysis and improvement roadmap

### 5. HealthTrioConnect (2 projects)
**Node.js + Python Hybrid** - Browser automation with Python processing

```
Examples: audiobee_jefferson_health, audiobee_physicians_mi
Pattern:  Node.js browser → export CSV → Python processing
Tech:     Puppeteer scripting, CSV parsing, hybrid workflow
```

### 6. Werally (3 projects)
**UHC Platform** - Grid-based geographic search

```
Examples: audiobee_uhc_medicaid, audiobee_uhc_individual, audiobee_uhc_behavioral_health
Pattern:  ZIP grid → search → details → normalize
Tech:     Geographic grid generation, comprehensive coverage
```

**Advanced Implementation** (`audiobee_uhc_behavioral_health`):
- **Multi-plan architecture**: Separate subdirectories for employer_and_individual_plans, medicaid_plans, medicare_plans, state_exchanges
- **Shared package integration**: Local `shared_package/` with browser session management (BrowserSession, ResilientBrowserSession)
- **Browser-based sessions**: Uses Patchright (Playwright fork) for anti-detection with proxy support
- **Environment management**: python-dotenv for proxy credentials (NORD_USERNAME, NORD_PASSWORD, SURFSHARK_USERNAME, SURFSHARK_PASSWORD)
- **Async architecture**: Async/await pattern with `asyncio.gather()` for concurrent page fetching
- **Performance optimization**: orjson for fast JSON serialization, curl_cffi for HTTP requests with browser impersonation

### 7. Provider Lenz (1 project)
**Anti-Bot Protected** - Requires captcha solving

```
Example:  audiobee_elderplan
Pattern:  capsolver integration → authenticated search → extraction
Tech:     Anti-detection (Camoufox), captcha solving service
```

---

## Common Patterns

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

### Shared Package Pattern (Local)

Some projects include a local `shared_package/` for reusable session management:

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

**Components**:
- `session/browser_session.py`: BrowserSession (Patchright/Playwright) for full browser automation
- `session/resilient_session.py`: ResilientBrowserSession - wrapper with automatic session recreation on failures (202/401/403/429 status codes, browser crashes)
- `session/http_session.py`: HttpSession (curl_cffi) for lightweight HTTP with browser impersonation
- `config.py`: Proxy configuration with python-dotenv (NORD_USERNAME, NORD_PASSWORD, SURFSHARK_USERNAME, SURFSHARK_PASSWORD)
- `localdataclass/response.py`: Unified Response object

**When to Use**:
- Sites requiring login/authentication
- Anti-bot detection requiring real browser fingerprints
- Cookie extraction for subsequent API calls
- JavaScript-rendered content

---

## Shared Utilities

### healthsparq-server (Port 1018)

Browser automation server for protected Healthsparq sites:

```bash
# Start server
cd healthsparq-server && npm start

# Server handles:
# - Session management
# - Cookie extraction
# - Stealth browser automation
# - Token refresh
```

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

## Coverage Types

| Type | Description | Example Projects |
|------|-------------|------------------|
| **Medicare Advantage** | Senior plans (65+) | audiobee_anthem, audiobee_humana |
| **Medicaid** | State-funded programs | audiobee_uhc_medicaid, audiobee_amerigroup |
| **ACA** | Marketplace plans | audiobee_florida_blue, audiobee_bcbs_il |
| **Large Group** | Employer plans | audiobee_multiplan |

---

## Getting Started

### Running a Scraper

```bash
# 1. Navigate to project
cd audiobee_bcbs_il

# 2. Update dates in config.py
PREV_DATE = "20251010"
CURR_DATE = "20251210"

# 3. Run phases sequentially
python index_1.py    # Discovery
python index_2.py    # Details
python index_3.py    # Normalization

# Or use orchestrator
python run_all.py
```

### For Healthsparq Projects

```bash
# 1. Start browser server first
cd healthsparq-server && npm start

# 2. Run scraper (in separate terminal)
cd audiobee_mvp_health
python run_all.py
```

### Validating Output

```bash
# Check output schema compliance
python output_generator/type_check.py audiobee_bcbs_il/

# Generate diff report vs previous run
python output_generator/comparison_creator.py audiobee_bcbs_il/
```

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `config.py` | Project configuration (URLs, params, dates) |
| `index_1.py` | Phase 1: Search/discovery |
| `index_2.py` | Phase 2: Detail extraction |
| `index_3.py` | Phase 3: Data normalization |
| `run_all.py` | Pipeline orchestrator |
| `PLAN.md` | Infrastructure scaling implementation plan |
| `CLAUDE.md` | Project metadata (site type, coverage, approval) |
| `ANTHEM_IMPROVEMENT.md` | Architectural improvement recommendations (audiobee_anthem_new only) |
| `SINGLE_PROCESS_PLAN.md` | Single-process architecture implementation plan (audiobee_anthem_new only) |
| `single_process_implementation/unified_scraper.py` | Unified scraper main entry point using asyncio.Queue and page.expose_function() |

---

## Documentation

### Comprehensive Documentation Suite

The project now includes extensive technical documentation covering all aspects of the infrastructure:

#### Core Technical Guides
- **docs/INDEX.md** - Documentation navigation hub with role-based guidance
- **docs/ARCHITECTURE.md** - Complete system architecture with diagrams for all 7 platform types
- **docs/PIPELINE.md** - Detailed pipeline phase specifications and data flow patterns
- **docs/SITE_TYPES_REFERENCE.md** - Platform-specific implementation patterns with code examples
- **docs/DEVELOPER_GUIDE.md** - Complete onboarding guide for new developers
- **docs/TROUBLESHOOTING.md** - Diagnostic flowcharts and problem resolution procedures

#### Reference Documentation
- **docs/GLOSSARY.md** - Healthcare and technical terminology reference
- **docs/IMPROVEMENTS.md** - Prioritized code improvement recommendations (P0-P3: security, logging, error recovery, testing, monitoring)
- **docs/SCALABILITY_BEST_PRACTICES.md** - Industry best practices for parallel execution (asyncio, ProcessPoolExecutor), memory management, rate limiting patterns for 100+ scrapers
- **docs/EXPERT_REVIEW.md** - Review summary from 27 domain experts with quality scores
- **audiobee_anthem_new/ANTHEM_IMPROVEMENT.md** - Architectural analysis and improvement recommendations for advanced Anthem scraper (vs healthsparq patterns)
- **audiobee_anthem_new/SINGLE_PROCESS_PLAN.md** - Implementation plan for single-process unified architecture using page.expose_function()

#### Implementation Research
- **implementation_research/00_EXECUTIVE_SUMMARY.md** - Shared utilities framework research overview
- **implementation_research/01_CODING_FRAMEWORK.md** - Directory structure standards and module responsibilities
- **implementation_research/02_CONFIG_SYSTEM.md** - Pydantic Settings implementation with site-type inheritance
- **implementation_research/03_FILE_UTILITIES.md** - Thread-safe JSON/JSONL utilities with orjson
- **implementation_research/04_LOGGING.md** - Centralized logging with loguru (print() replacement)
- **implementation_research/05_VALIDATION.md** - Raw file integrity and schema validation with Pydantic
- **implementation_research/06_REPORT_GENERATION.md** - Integration with output_generator QA tools
- **implementation_research/07_IMPLEMENTATION_PLAN.md** - Phased rollout strategy (P0-P3 priorities)

#### Existing Documentation
- **docs/README.md** - Full project listing with links
- **docs/site-type-mapping.md** - Projects organized by platform type
- **docs/quick-reference.md** - Common operations cheatsheet
- **docs/MAINTENANCE.md** - Maintenance and update procedures

#### Documentation by Role
- **New Developers**: Start with GLOSSARY.md → ARCHITECTURE.md → DEVELOPER_GUIDE.md → TROUBLESHOOTING.md
- **Experienced Developers**: Focus on PIPELINE.md → SITE_TYPES_REFERENCE.md → IMPROVEMENTS.md → SCALABILITY_BEST_PRACTICES.md
- **Technical Leadership**: Review ARCHITECTURE.md → EXPERT_REVIEW.md → IMPROVEMENTS.md → implementation_research/ → PLAN.md
- **Operations**: Use TROUBLESHOOTING.md → DEVELOPER_GUIDE.md → quick-reference.md

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
|--------|-------------|------------------|----------|
| 8 GB   | 5-6         | 2                | 1        |
| 16 GB  | 8-10        | 3-4              | 1-2      |
| 32 GB  | 15-20       | 6-8              | 2-3      |

### Implementation Tools

**Available:**
- `tools/run_parallel.py` - Run multiple scrapers in parallel with retry logic and automatic config updates
- `projects/api.txt` - List of 37 API-type scrapers (Carrier category) for parallel execution

**Planned:**
- `tools/update_configs.py` - Mass update config.py files to use environment variables
- `tools/ec2_burst.py` - Launch EC2 instances for overflow work
- `projects/pc*.txt` - Static project assignment files per PC

### Quick Commands
```bash
# Run API scrapers in parallel (from list)
python tools/run_parallel.py --list projects/api.txt --workers 8 --curr 20251210 --prev 20251110

# Run scrapers by pattern
python tools/run_parallel.py --pattern "audiobee_bcbs*" --workers 8 --curr 20251210 --prev 20251110

# AWS EC2 burst (5 instances for overflow) - PLANNED
python tools/ec2_burst.py --projects overflow.txt --curr 20251210 --prev 20251110 --instances 5
```

### EC2 Instance Types
| Scraper Type | Instance   | vCPUs | RAM   | Cost/hr | Parallel |
|--------------|------------|-------|-------|---------|----------|
| API          | t3.medium  | 2     | 4 GB  | $0.042  | 5        |
| API (bulk)   | t3.large   | 2     | 8 GB  | $0.083  | 10       |
| Browser      | t3.xlarge  | 4     | 16 GB | $0.166  | 3        |

See **PLAN.md** for full implementation details, code samples, AMI setup, and troubleshooting guide.

---

## Notes for Developers

1. **Date Management**: Always update `PREV_DATE` and `CURR_DATE` in config.py before runs (or use `--curr`/`--prev` flags with run_parallel.py)
2. **Parallel Execution**: Use `tools/run_parallel.py` for running multiple scrapers concurrently - automatically updates config dates
3. **Rate Limiting**: Most scrapers include built-in delays; adjust as needed
4. **Deduplication**: NPI-based deduplication is standard across all projects
5. **Error Handling**: Check `{date}/raw/` for cached responses if runs fail mid-process; run_parallel.py saves error logs to `logs/{date}/`
6. **Browser Projects**: Ensure healthsparq-server is running for Healthsparq-type projects
7. **Output Validation**: Always run type_check.py before considering a run complete
8. **Code Quality**: See `docs/IMPROVEMENTS.md` for prioritized enhancement recommendations (security, logging, error recovery)

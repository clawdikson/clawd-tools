# Ideon Scraping Architecture Guide

> **Complete Technical Reference for Provider Directory Data Extraction Infrastructure**

## Executive Summary

The Ideon Scraping infrastructure is a large-scale web scraping system designed to extract, normalize, and validate healthcare provider directory data from **94+ insurance carrier websites**. The system processes data from major US health insurance carriers including BCBS affiliates, Anthem, Healthsparq-based platforms, and proprietary carrier APIs.

**Key Metrics:**
- **94 active scraper projects** across 7 distinct platform architectures
- **3-phase pipeline architecture** (Discovery → Extraction → Normalization)
- **Shared infrastructure** for browser automation and QA validation
- **NPI-based deduplication** producing standardized JSONL output

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           IDEON SCRAPING INFRASTRUCTURE                               │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                       │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐│
│  │                              SCRAPER PROJECTS (94)                                ││
│  │                                                                                   ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             ││
│  │  │   Carrier   │  │ Healthsparq │  │  Sapphire   │  │   Anthem    │             ││
│  │  │  (35 proj)  │  │  (24 proj)  │  │  (15 proj)  │  │  (4 proj)   │             ││
│  │  ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤             ││
│  │  │ Direct REST │  │  Browser +  │  │ProviderFind│  │  Wellpoint  │             ││
│  │  │    APIs     │  │   Session   │  │ erOnline   │  │Infrastruct. │             ││
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             ││
│  │         │                │                │                │                     ││
│  │  ┌──────┴────────────────┴────────────────┴────────────────┴──────┐             ││
│  │  │                     PIPELINE EXECUTOR (run_all.py)              │             ││
│  │  │   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐  │             ││
│  │  │   │ Phase 0  │───▶│ Phase 1  │───▶│ Phase 2  │───▶│ Phase 3 │  │             ││
│  │  │   │ (Setup)  │    │(Discovery)│    │(Extract) │    │ (Map)   │  │             ││
│  │  │   └──────────┘    └──────────┘    └──────────┘    └─────────┘  │             ││
│  │  └────────────────────────────────────────────────────────────────┘             ││
│  └──────────────────────────────────────────────────────────────────────────────────┘│
│                                          │                                            │
│  ┌───────────────────────────────────────┼───────────────────────────────────────┐   │
│  │                        SHARED INFRASTRUCTURE                                   │   │
│  │                                       │                                        │   │
│  │  ┌────────────────────────────────────┼────────────────────────────────────┐  │   │
│  │  │          healthsparq-server (Node.js/Puppeteer)                         │  │   │
│  │  │  ┌──────────┐  ┌──────────────┐  ┌────────────────┐  ┌───────────────┐ │  │   │
│  │  │  │ Express  │  │   Puppeteer  │  │ Anti-Detection │  │ VPN Rotation  │ │  │   │
│  │  │  │  Server  │──│    Worker    │──│   (Stealth)    │──│  (NordVPN)    │ │  │   │
│  │  │  │ :1018    │  │              │  │                │  │  1700+ IPs    │ │  │   │
│  │  │  └──────────┘  └──────────────┘  └────────────────┘  └───────────────┘ │  │   │
│  │  └─────────────────────────────────────────────────────────────────────────┘  │   │
│  │                                       │                                        │   │
│  │  ┌────────────────────────────────────┼────────────────────────────────────┐  │   │
│  │  │            output_generator (Python QA Suite)                           │  │   │
│  │  │  ┌──────────┐  ┌──────────────┐  ┌────────────────┐  ┌───────────────┐ │  │   │
│  │  │  │  Type    │  │   Sample     │  │   Comparison   │  │    Report     │ │  │   │
│  │  │  │  Check   │──│  Generator   │──│    Creator     │──│   Generator   │ │  │   │
│  │  │  └──────────┘  └──────────────┘  └────────────────┘  └───────────────┘ │  │   │
│  │  └─────────────────────────────────────────────────────────────────────────┘  │   │
│  └───────────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                            │
│  ┌───────────────────────────────────────▼───────────────────────────────────────┐   │
│  │                              OUTPUT & STORAGE                                  │   │
│  │                                                                                │   │
│  │   ┌─────────────────────────┐    ┌──────────────────────────────────────────┐ │   │
│  │   │   YYYYMMDD/raw/         │    │   YYYYMMDD/processed/                    │ │   │
│  │   │   ├── search_results/   │───▶│   └── project-YYYYMMDD.jsonl             │ │   │
│  │   │   ├── provider_details/ │    │       (Normalized NPI-deduplicated)      │ │   │
│  │   │   ├── locations/        │    └──────────────────────────────────────────┘ │   │
│  │   │   ├── affiliations/     │                                                 │   │
│  │   │   └── networks/         │                                                 │   │
│  │   └─────────────────────────┘                                                 │   │
│  └───────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Platform Architecture Types

The 94 scraper projects are categorized into 7 distinct platform architectures, each requiring specific implementation patterns:

### 1. Carrier Type (35 projects)
**Pattern**: Direct REST API integration with minimal browser automation

```
┌─────────────────────────────────────────────────────┐
│                  CARRIER ARCHITECTURE                │
├─────────────────────────────────────────────────────┤
│                                                      │
│  config.py ──▶ index_1.py ──▶ index_2.py ──▶ index_3.py
│       │            │              │              │
│       │            ▼              ▼              ▼
│  [URLs/Keys]  [Search API]  [Details API]  [Normalize]
│                   │              │              │
│                   ▼              ▼              ▼
│            {date}/raw/    {date}/raw/    {date}/processed/
│            search_results provider_details  *.jsonl
│                                                      │
└─────────────────────────────────────────────────────┘
```

**Characteristics:**
- Direct REST API calls (JSON responses)
- API keys/headers stored in `config.py`
- Geographic grid search (lat/lng + radius)
- Network ID-based plan filtering
- `httpx` or `requests` for HTTP operations
- `async/await` patterns for concurrent fetching

**Example Projects:** `audiobee_bcbs_ma`, `audiobee_florida_blue`, `audiobee_multiplan`

---

### 2. Healthsparq Type (24 projects)
**Pattern**: Browser automation with session management

```
┌─────────────────────────────────────────────────────────────┐
│                  HEALTHSPARQ ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  healthsparq-server (port 1018)                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Puppeteer + Stealth ─▶ Cookie/Token Extraction       │    │
│  └────────────────────────────┬────────────────────────┘    │
│                               │                              │
│                               ▼                              │
│  config.py ──▶ index_1.py ──────▶ index_2.py ──▶ index_3.py │
│       │            │                   │              │      │
│       │            ▼                   ▼              ▼      │
│  [Plan Codes]  [Browser Search]  [Profile API]  [Normalize] │
│  [Filters]     [County Grid]     [v1 + v2]                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Characteristics:**
- Requires `healthsparq-server` running (port 1018+)
- Session token extraction via Puppeteer browser
- Rate limiting with built-in delays
- Cookie/header passthrough to subsequent API calls
- Multi-filter expansion for complete coverage
- `ThreadPoolExecutor` for concurrent processing

**Example Projects:** `audiobee_mvp_health`, `audiobee_medica`, `audiobee_excellus`

---

### 3. Sapphire Type (15 projects)
**Pattern**: ProviderFinderOnline standardized API

```
┌─────────────────────────────────────────────────────────────┐
│                   SAPPHIRE ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ProviderFinderOnline API (*.sapphirethreesixtyfive.com)    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  /api/providers/summary.json                         │    │
│  │  /api/providers/{id}/locations/{id}/affiliations.json│    │
│  │  /api/providers/{id}/locations/{id}/networks_accepted│    │
│  │  /api/search_specialties.json                        │    │
│  │  /api/providers/facets.json                          │    │
│  └────────────────────────────┬────────────────────────┘    │
│                               │                              │
│  config.py ──▶ index_0 ──▶ index_1 ──▶ 3_map_json_*.py      │
│       │           │            │               │             │
│       │           ▼            ▼               ▼             │
│  [network_id]  [ID Discovery] [Detail Fetch] [Normalize]     │
│  [x-api-key]   [Faceted]      [Async+Retry]                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Characteristics:**
- Consistent API endpoints across carriers
- `x-api-key` + `x-nonce` authentication
- Transaction ID tracking (UUID)
- Faceted specialty/location search
- `AsyncCamoufox` for stealth browser requests
- Proxy rotation via DataImpulse

**Example Projects:** `audiobee_bcbs_il`, `audiobee_molina`, `audiobee_carefirst`

---

### 4. Anthem Type (4 projects)
**Pattern**: Wellpoint multi-phase filtering

```
┌─────────────────────────────────────────────────────────────┐
│                    ANTHEM ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Wellpoint API (findcare.wellpoint.com)                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Phase 1: counties_by_state → plan_categories        │    │
│  │  Phase 2: specialty search with network filters      │    │
│  │  Phase 3: provider details + locations               │    │
│  │  Phase 4: affiliations + network hierarchies         │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  Brand variations:                                           │
│  ├── Anthem (National)                                       │
│  ├── Amerigroup (AZ, DC, GA, IA, NJ, NM, TN, TX, WA)       │
│  ├── Healthy Blue (LA, MO, KS)                              │
│  └── Simply Healthcare (FL)                                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Characteristics:**
- Brand-specific URLs sharing common infrastructure
- State-specific network configurations
- Multi-level affiliation tracking
- Complex URL/parameter handling

**Example Projects:** `audiobee_anthem`, `audiobee_amerigroup`, `audiobee_healthy_blue`

---

### 5. HealthTrioConnect Type (2 projects)
**Pattern**: Node.js + Python hybrid pipeline

```
┌─────────────────────────────────────────────────────────────┐
│               HEALTHTRIOCONNECT ARCHITECTURE                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐    ┌──────────────────────────────┐   │
│  │  Node.js Phase   │    │       Python Phase           │   │
│  │                  │    │                              │   │
│  │  1_index.js      │───▶│  5_map_html_to_json.py       │   │
│  │  (Puppeteer)     │    │  6_map_json_to_ideon.py      │   │
│  │  CSV Export      │    │  (Parsing + Normalization)   │   │
│  └──────────────────┘    └──────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Characteristics:**
- JavaScript browser automation for initial extraction
- CSV intermediate format
- Python for HTML parsing and JSON mapping
- Custom Node.js scripts with Puppeteer

**Example Projects:** `audiobee_jefferson_health`, `audiobee_physicians_health_plan_mi`

---

### 6. Werally Type (2 projects)
**Pattern**: UHC geographic grid search

```
┌─────────────────────────────────────────────────────────────┐
│                    WERALLY ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  werally.com API (connect.werally.com)                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Geographic Grid Generation:                         │    │
│  │  ├── State-specific lat/lng coordinates             │    │
│  │  ├── Radius-based search circles                    │    │
│  │  └── Full US coverage via overlapping grids         │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  POINTS = {                                                  │
│    "state": [                                                │
│      {"lat": x, "lng": y, "radius": r},                     │
│      ...                                                     │
│    ]                                                         │
│  }                                                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Characteristics:**
- ZIP grid-based comprehensive coverage
- State-specific coordinates in config
- Network/plan filtering by state and coverage type
- Connection pooling for efficient requests

**Example Projects:** `audiobee_uhc_medicaid`, `audiobee_uhc_individual`

---

### 7. Provider Lenz Type (1 project)
**Pattern**: Anti-bot protected with CAPTCHA solving

```
┌─────────────────────────────────────────────────────────────┐
│                  PROVIDER LENZ ARCHITECTURE                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │  Anti-Detection Stack                               │     │
│  │  ├── Camoufox (stealth Firefox)                    │     │
│  │  ├── capsolver integration (CAPTCHA solving)       │     │
│  │  ├── JavaScript charset token generation           │     │
│  │  └── Low concurrency (MAX_WORKERS=2)               │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  Error Handling:                                             │
│  ├── 418 (I'm a teapot) → 5-minute sleep + retry           │
│  ├── CAPTCHA detection → capsolver service call            │
│  └── Retry with exponential backoff                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Characteristics:**
- Anti-detection tools (Camoufox stealth browser)
- External CAPTCHA solving service integration
- Custom JavaScript for request token generation
- Very low concurrency to avoid detection

**Example Projects:** `audiobee_elderplan`

---

## Data Flow Architecture

### Standard 3-Phase Pipeline

```
                    ┌─────────────────────────────────────────────────────────┐
                    │               PHASE 1: DISCOVERY                        │
                    │                                                          │
 ┌────────────┐    │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
 │ config.py  │───▶│  │ Load Search │───▶│  Execute    │───▶│   Cache     │  │
 │            │    │  │ Parameters  │    │  Paginated  │    │   Raw       │  │
 │ - URLs     │    │  │ (ZIPs,specs)│    │  Searches   │    │  Responses  │  │
 │ - Network  │    │  └─────────────┘    └─────────────┘    └──────┬──────┘  │
 │ - Dates    │    │                                               │         │
 └────────────┘    └───────────────────────────────────────────────┼─────────┘
                                                                   │
                                                                   ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │               PHASE 2: EXTRACTION                       │
                    │                                                          │
                    │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
                    │  │ Load IDs    │───▶│   Fetch     │───▶│   Cache     │  │
                    │  │ from Phase 1│    │  Provider   │    │   Detail    │  │
                    │  │             │    │  Details    │    │   Files     │  │
                    │  └─────────────┘    └─────────────┘    └──────┬──────┘  │
                    │                                               │         │
                    └───────────────────────────────────────────────┼─────────┘
                                                                   │
                                                                   ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │               PHASE 3: NORMALIZATION                    │
                    │                                                          │
                    │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
                    │  │ Load Raw    │───▶│  Transform  │───▶│  Output     │  │
                    │  │ Data from   │    │  to Schema  │    │  JSONL      │  │
                    │  │ Phases 1-2  │    │  Dedupe NPI │    │  (Final)    │  │
                    │  └─────────────┘    └─────────────┘    └─────────────┘  │
                    │                                                          │
                    └─────────────────────────────────────────────────────────┘
```

---

## Directory Structure

### Project-Level Layout

```
audiobee_project_name/
├── config.py                  # Configuration (URLs, params, network IDs, dates)
├── index_0.py                 # Phase 0: Optional setup/ID discovery
├── index_1.py                 # Phase 1: Search/discovery
├── index_2.py                 # Phase 2: Detail extraction
├── index_3.py                 # Phase 3: Data mapping/normalization
├── run_all.py                 # Pipeline orchestrator
├── CLAUDE.md                  # Project metadata (site type, coverage)
│
├── YYYYMMDD/                  # Date-versioned output directory
│   ├── raw/                   # Raw API responses
│   │   ├── search_results/    # Phase 1 JSON files
│   │   ├── provider_details/  # Phase 2 detail files
│   │   ├── locations/         # Supplementary location data
│   │   ├── affiliations/      # Hospital/group affiliations
│   │   └── networks/          # Network eligibility data
│   └── processed/             # Normalized output
│       └── project-YYYYMMDD.jsonl
│
├── data/                      # Reference data (specialties, networks, ZIPs)
│   ├── specialties.json
│   ├── networks.json
│   └── allowable_networks.json
│
└── [optional: utils.py, helpers/, old_code/]
```

### Repository-Level Layout

```
/Users/dikson/Work/ideon_scraping/scraping/
├── audiobee_*/                # 94 individual scraper projects
│
├── healthsparq-server/        # Shared browser automation server
│   ├── server.js              # Express HTTP server (port 1018)
│   ├── browserWorker.js       # Puppeteer browser worker
│   ├── config.js              # Shared configuration
│   ├── us-vpn-hostnames.json  # VPN endpoint pool (1700+)
│   └── package.json           # Node.js dependencies
│
├── output_generator/          # Shared QA utilities
│   ├── type_check.py          # Schema validation + Excel reports
│   ├── comparison_creator.py  # Version diff analysis
│   ├── report_generator.py    # Summary statistics
│   ├── sample_generator.py    # QA sample extraction
│   └── run_all.py             # QA pipeline orchestrator
│
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md        # This file
│   ├── PIPELINE.md            # Pipeline details
│   ├── SITE_TYPES.md          # Site type specifics
│   ├── DEVELOPER_GUIDE.md     # Onboarding guide
│   ├── TROUBLESHOOTING.md     # Debugging guide
│   └── IMPROVEMENTS.md        # Enhancement recommendations
│
├── data/                      # Shared reference data
│   └── us_zip_fips_county.xlsx
│
├── CLAUDE.md                  # Project-wide instructions
└── PLAN.md                    # Infrastructure scaling plan
```

---

## Output Schema

All scrapers produce standardized JSONL output:

```json
{
  "networks": [
    {"name": "Blue Cross Blue Shield of Illinois", "tier": null}
  ],
  "provider": {
    "unparsed_name": "John Michael Smith MD",
    "gender": "M",
    "provider_type": "individual",
    "npi": "1234567890",
    "license_number": null,
    "facility_name": null,
    "first_name": "John",
    "middle_name": "Michael",
    "last_name": "Smith",
    "title": "MD",
    "suffix": null,
    "rating": {"scale": null, "score": null}
  },
  "addresses": [
    {
      "street_line_1": "123 Main St",
      "street_line_2": "Suite 100",
      "city": "Chicago",
      "state": "IL",
      "zip": "60601",
      "office_name": "Main Office",
      "address_string": "123 Main St, Suite 100, Chicago, IL 60601",
      "phones": [
        {"type": "phone", "value": "312-555-0100"},
        {"type": "fax", "value": "312-555-0101"}
      ],
      "languages": [
        {"name": "English", "type": "primary"},
        {"name": "Spanish", "type": "secondary"}
      ],
      "pcp": true,
      "pcp_id": "PCP_12345",
      "accepting_new_patients": true,
      "external_id": "location_9999"
    }
  ],
  "group_affiliations": [
    {"name": "Northwestern Medical Group"}
  ],
  "hospital_affiliations": [
    {"name": "Northwestern Memorial Hospital"}
  ],
  "specialties": [
    {"name": "Family Medicine"},
    {"name": "Internal Medicine"}
  ]
}
```

---

## Shared Infrastructure

### healthsparq-server

Browser automation service for protected Healthsparq websites.

**Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│                    healthsparq-server                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────┐    ┌──────────────────────────────────┐ │
│  │  Express HTTP  │    │   Puppeteer Worker Pool          │ │
│  │  Server        │───▶│   ├── Anti-Detection Stack       │ │
│  │  (Port 1018)   │    │   │   ├── puppeteer-extra-stealth│ │
│  └────────────────┘    │   │   ├── fingerprint-injector   │ │
│                        │   │   └── puppeteer-real-browser  │ │
│  API Endpoints:        │   │                               │ │
│  ├── /setBaseUrl       │   ├── VPN Rotation                │ │
│  ├── /navigate         │   │   └── 1700+ NordVPN endpoints │ │
│  ├── /fetch            │   │                               │ │
│  ├── /getCookies       │   └── Session Persistence         │ │
│  └── /refresh          │       └── cross.json state file   │ │
│                        └──────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Usage:**
```bash
# Start server
cd healthsparq-server && npm start

# From Python scraper
import requests
SERVER_URL = "http://localhost:1018"
requests.post(f"{SERVER_URL}/setBaseUrl", json={"baseUrl": "https://..."})
```

---

### output_generator

QA and reporting utilities for all scraper projects.

**Components:**

| Component | Purpose |
|-----------|---------|
| `type_check.py` | Schema validation, Excel report generation (13 sheets) |
| `comparison_creator.py` | Cross-run diff analysis, change detection |
| `report_generator.py` | Summary statistics, state-level counts |
| `sample_generator.py` | QA sample extraction (10 random records) |

**QA Pipeline Flow:**
```
Scraper Output (JSONL)
    ↓
type_check.py ─────────────▶ Excel reports (Networks, Providers, Addresses...)
    ↓
sample_generator.py ───────▶ 10 random JSON samples
    ↓
comparison_creator.py ─────▶ Diff report (new/dropped items)
    ↓
report_generator.py ───────▶ Summary statistics
    ↓
compress_folder_to_7z ─────▶ Archived output
```

---

## Concurrency Models

### ThreadPoolExecutor (Synchronous)
Used by: Healthsparq projects (MVP Health, Medica)

```python
MAX_WORKERS = 10
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = [executor.submit(fetch_function, item) for item in items]
    for future in tqdm(as_completed(futures), total=len(futures)):
        result = future.result()
```

### Async/Await (Asynchronous)
Used by: Sapphire projects (BCBS IL, Molina)

```python
async def _process_summary(provider_id, network_id, browser_request):
    async for attempt in AsyncRetrying(stop=stop_after_attempt(2)):
        with attempt:
            response = await browser_request.get(url, timeout=120000)
            async with aiofiles.open(filepath, "wb") as f:
                await f.write(orjson.dumps(await response.json()))
```

### Worker Queue Pattern
Used by: Carrier projects (Multiplan)

```python
task_queue = queue.Queue()
workers = [PlaywrightWorker(task_queue, progress_bar) for _ in range(MAX_WORKERS)]
for worker in workers:
    worker.start()

for item in items:
    task_queue.put(payload)

task_queue.join()  # Wait for completion
```

---

## Performance Characteristics

| Site Type | Max Concurrency | Typical Runtime | Memory Usage |
|-----------|-----------------|-----------------|--------------|
| Carrier | 8-10 workers | 3-4 hours | 2-4 GB |
| Healthsparq | 10 threads | 4-8 hours | 4-6 GB |
| Sapphire | 10 async tasks | 6-10 hours | 3-5 GB |
| Anthem | 8 workers | 4-6 hours | 3-4 GB |
| Provider Lenz | 2 workers | 8-12 hours | 2-3 GB |

---

## Security Considerations

1. **API Key Management**: Keys currently stored in `config.py` (consider environment variables)
2. **Proxy Credentials**: DataImpulse SOCKS5 credentials hardcoded (security concern)
3. **VPN Authentication**: NordVPN credentials embedded in healthsparq-server
4. **Rate Limiting**: Built-in delays and retry logic to avoid IP bans
5. **Anti-Detection**: Stealth plugins, fingerprint injection, VPN rotation

---

## References

- [PLAN.md](../PLAN.md) - Infrastructure scaling implementation plan
- [PIPELINE.md](./PIPELINE.md) - Detailed pipeline phase documentation
- [SITE_TYPES.md](./SITE_TYPES.md) - Site-type specific implementation details
- [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) - Onboarding and development guide
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Debugging and error resolution
- [IMPROVEMENTS.md](./IMPROVEMENTS.md) - Enhancement recommendations

---

*Last Updated: December 2024*

# Site Types Technical Reference

> **Complete Implementation Guide for Each Platform Architecture**

## Overview

This document provides detailed technical specifications for each of the 7 platform types used in the Ideon scraping infrastructure. Each section includes API endpoints, authentication patterns, data formats, and implementation examples.

---

## Quick Reference Table

| Site Type | Projects | Tech Stack | Auth Method | Concurrency |
|-----------|----------|------------|-------------|-------------|
| **Carrier** | 35 | httpx/requests | API Key/JWT | 8-10 workers |
| **Healthsparq** | 24 | Puppeteer + Python | Browser Session | 10 threads |
| **Sapphire** | 15 | AsyncCamoufox | x-api-key + x-nonce | 10 async |
| **Anthem** | 4 | httpx | Session Cookies | 8 workers |
| **HealthTrioConnect** | 2 | Node.js + Python | Browser Session | Single |
| **Werally** | 2 | httpx | None (public) | 8 workers |
| **Provider Lenz** | 1 | Camoufox + CAPTCHA | Browser + Token | 2 workers |

---

## 1. Carrier Type (35 Projects)

### Overview
Direct REST API integrations with insurance carrier backends. These are the most straightforward to implement and maintain.

### Characteristics
- **API Type**: RESTful JSON APIs
- **Authentication**: API keys, JWT tokens, or session headers
- **Rate Limiting**: Moderate (typically 100-500 requests/minute)
- **Browser Required**: No

### API Pattern

```python
# Typical Carrier API Structure

BASE_URLS = {
    "search": "https://api.carrier.com/v1/providers/search",
    "details": "https://api.carrier.com/v1/providers/{provider_id}",
    "networks": "https://api.carrier.com/v1/networks",
}

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": "Bearer {jwt_token}",
    "X-API-Key": "your-api-key",
}
```

### Implementation Example: Multiplan

```python
# audiobee_multiplan/config.py

BASE_SEARCH_URL = "https://api-ext-az.multiplan.com/provider-ps-search/v1/searchProviders"

BASE_PAYLOAD = {
    "viewLanguage": "en",
    "productCodeList": [
        "HEOSPlus", "MPI", "PHCSPrimary", "HEOS",
        "MCMICore", "CMG", "PHCS", "BeechStreet"
    ],
    "providerTypeList": ["P", "F"],  # Practitioner, Facility
    "applyRestrictions": True,
    "siteId": "84367",
    "zipCode": "66952",  # Geographic center of US
    "distance": [5000],
    "pageSize": 100,
    "sortBy": "distance",
}

BASE_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "JWT-Token": "",  # Populated at runtime
    "Ocp-Apim-Subscription-Key": "d76df4a5c71a4ae18b6a46a22de5bd6c",
}
```

### Search Flow

```
1. POST /v1/searchProviders
   ├── Specialty-based search
   ├── Paginated results (page 1..N)
   └── Returns: providerResults[], totalMatchingPages

2. POST /v1/providerDetails
   ├── Input: alternateIDNumber (MP3ID or CREDID)
   └── Returns: Full provider profile

3. Network-specific search
   ├── selectedNetwork: "Beech Street"
   └── Additional filtering for specific networks
```

### Projects
- `audiobee_florida_blue` (FL)
- `audiobee_multiplan` (Nationwide)
- `audiobee_bcbs_ma` (MA)
- `audiobee_harvard_pilgrim` (MA, ME, NH)
- `audiobee_emblem` (National)
- `audiobee_scan_health` (CA, NV, OR, AZ)
- `audiobee_upmc` (PA)
- ... and 28 more

---

## 2. Healthsparq Type (24 Projects)

### Overview
Browser-based extraction for sites using the Healthsparq provider directory platform. Requires `healthsparq-server` running for Puppeteer automation.

### Characteristics
- **API Type**: Mixed (Browser + REST)
- **Authentication**: Session tokens via browser
- **Rate Limiting**: Strict (built-in delays required)
- **Browser Required**: Yes (healthsparq-server)

### Server Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     healthsparq-server                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Express Server (Port 1018)                                     │
│  ├── /setBaseUrl    → Initialize browser session                │
│  ├── /navigate      → Navigate to URL                           │
│  ├── /fetch         → Execute fetch in browser context          │
│  ├── /getCookies    → Extract session cookies                   │
│  └── /refresh       → Reload current page                       │
│                                                                  │
│  Puppeteer Worker                                               │
│  ├── puppeteer-extra-plugin-stealth                             │
│  ├── fingerprint-injector                                       │
│  └── VPN rotation (1700+ NordVPN endpoints)                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Configuration Pattern

```python
# audiobee_mvp_health/config.py

HEALTHSPARK_PUPPETEER_PORT = 1012  # Unique per project

URLS = {
    "auth_url": "https://mvp.healthsparq.com/healthsparq/public/service/login?insurerCode={insurerCode}&brandCode={brandCode}&productCode={productCode}",
    "search_url": "https://mvp.healthsparq.com/healthsparq/public/service/v4/search",
    "profile_url": "https://mvp.healthsparq.com/healthsparq/public/service/profile",
    "profile_url_v2": "https://mvp.healthsparq.com/healthsparq/public/service/v2/profile",
    "filter_url": "https://mvp.healthsparq.com/healthsparq/public/service/v3/search/filters",
}

PLANS = [
    {
        "insurerCode": "MVP_I",
        "brandCode": "MVP",
        "productCode": "all",
    },
]

# Filter combinations for comprehensive coverage
FILTERS = [
    [],
    ["PROVIDER_TYPE:FAC"],
    ["PROVIDER_TYPE:GRP"],
    ["PROVIDER_TYPE:FAC", "GENDER_V2:F"],
    ["PROVIDER_TYPE:GRP", "GENDER_V2:M"],
    # ... more combinations
]
```

### Search Strategy

```
1. County-by-County Grid Search
   ├── Load US counties from ZIP/FIPS reference
   └── Search each county independently

2. Progressive Filter Narrowing (when results > 600)
   ├── Apply organization type filter
   ├── If still > 600, apply gender filter
   └── If still > 600, apply specialty filter

3. Multi-Sort Coverage
   ├── BEST_MATCH sort
   ├── DISTANCE sort
   ├── NAME_ASC sort
   └── NAME_DESC sort

4. Pagination Strategy
   ├── Page 1: 200 results
   └── Page 3: 100 results (skip page 2)
```

### Projects
- `audiobee_mvp_health` (NY, VT)
- `audiobee_medica` (IA, MN, ND, NE, WI)
- `audiobee_excellus` (NY)
- `audiobee_ibx` (PA)
- `audiobee_tufts_health_plans` (MA, NH, RI)
- ... and 19 more

---

## 3. Sapphire Type (15 Projects)

### Overview
Standardized ProviderFinderOnline API platform used by multiple BCBS affiliates and other carriers. Consistent API structure across implementations.

### Characteristics
- **API Type**: REST with consistent endpoints
- **Authentication**: x-api-key + x-nonce headers
- **Rate Limiting**: Moderate
- **Browser Required**: Optional (stealth for anti-detection)

### API Endpoints

```python
# Standard Sapphire API Structure

BASE_URLS = {
    # Provider search
    "summary": "https://{domain}/api/providers/summary.json",
    "facets": "https://{domain}/api/providers/facets.json",

    # Provider details
    "affiliations": "https://{domain}/api/providers/{provider_id}/locations/{location_id}/affiliations.json",
    "locations": "https://{domain}/api/providers/{provider_id}/locations/{location_id}/other_locations.json",
    "networks": "https://{domain}/api/providers/{provider_id}/locations/{location_id}/networks_accepted.json",

    # Reference data
    "specialties": "https://{domain}/api/search_specialties.json",
}

# Domain variations
DOMAINS = {
    "bcbs_il": "my.providerfinderonline.com",
    "bcbs_kc": "bluekc.sapphirethreesixtyfive.com",
    "bcbs_la": "findcare.bcbsla.com",
    "molina": "molina.sapphirethreesixtyfive.com",
    "carefirst": "carefirst.sapphirecareselect.com",
}
```

### Authentication

```python
from uuid import uuid4
from browserforge.headers import HeaderGenerator

header_generator = HeaderGenerator()

def get_headers():
    """Generate authenticated headers with anti-detection."""
    headers = header_generator.generate()  # Realistic browser fingerprint
    headers.update({
        "accept": "application/json, text/plain, */*",
        "x-api-key": "03220e47-16eb-44d3-b1ca-4e3641973a97",
        "x-nonce": str(uuid4()),  # Unique per request
    })
    return headers
```

### Search Parameters

```python
COMMON_PARAMS = {
    "geo_location": "39.883875,-88.834467",  # IL center
    "locale": "en",
    "data_language": "en",
    "transaction_id": str(uuid4()),
    "account_id": "3",
    "ci": "bcbsla",
    "config_signature": "{3}-{}-{}",
}

BASE_PARAMS = {
    "network_id": "1",
    "search_specialty_id": "980000012",
    "page": "1",
    "limit": "10",
    "radius": "210",
    "sort": "distance asc",
    **COMMON_PARAMS,
}

# Faceted search for ID discovery
FACET_PARAMS = {
    "facet[provider_id[limit]]": "-1",  # Get ALL provider IDs
    "facet[provider_type]": "true",
    "facet[contract_accepting_new_patients]": "true",
    "facet[field_specialty_ids]": "true",
    # ... more facets
}
```

### Projects
- `audiobee_bcbs_il` (IL)
- `audiobee_bcbs_kc` (MO, KS)
- `audiobee_bcbs_la` (LA)
- `audiobee_molina` (Multi-state)
- `audiobee_carefirst` (MD, VA, DC)
- ... and 10 more

---

## 4. Anthem Type (4 Projects)

### Overview
Wellpoint/Anthem infrastructure with brand-specific variations. Complex multi-phase search with network hierarchies.

### Characteristics
- **API Type**: REST with complex parameter sets
- **Authentication**: Session cookies
- **Rate Limiting**: Moderate
- **Browser Required**: No

### API Structure

```python
# audiobee_anthem/config.py

URLS = {
    "homepage": {
        "url": "https://findcare.wellpoint.com/",
        "type": "GET"
    },
    "auth": {
        "url": "https://findcare.wellpoint.com/fad/api/utility/data-modifiedon",
        "type": "GET"
    },
    "counties_by_state": {
        "url": "https://findcare.wellpoint.com/fad/api/utility/countiesbystate/{state}",
        "type": "GET"
    },
    "plan_categories": {
        "url": "https://findcare.wellpoint.com/fad/api/utility/plan-categories",
        "type": "GET"
    },
    "search": {
        "url": "https://findcare.wellpoint.com/precare/api/search/public/v1/specialty",
        "type": "POST"
    },
    "details": {
        "url": "https://findcare.wellpoint.com/fad/api/provider/details",
        "type": "POST"
    },
}
```

### Multi-Phase Flow

```
Phase 1: Setup
├── GET homepage (establish session)
├── GET auth endpoint (validate session)
└── GET counties_by_state (geographic reference)

Phase 2: Plan Discovery
├── GET plan_categories
└── Filter by state + coverage type

Phase 3: Provider Search
├── POST specialty search
├── Filter by network
└── Paginated results

Phase 4: Detail Extraction
├── POST provider details
├── POST locations
└── POST affiliations

Phase 5: Network Mapping
├── Extract network hierarchies
└── Map to standard format
```

### Brand Variations

| Brand | States | Base URL |
|-------|--------|----------|
| Anthem | National | findcare.wellpoint.com |
| Amerigroup | AZ, DC, GA, IA, NJ, NM, TN, TX, WA | findcare.wellpoint.com |
| Healthy Blue | LA, MO, KS | findcare.wellpoint.com |
| Simply Healthcare | FL | findcare.wellpoint.com |

### Projects
- `audiobee_anthem` (National)
- `audiobee_amerigroup` (9 states)
- `audiobee_healthy_blue` (LA, MO, KS)
- `audiobee_simply_healthcare` (FL)

---

## 5. HealthTrioConnect Type (2 Projects)

### Overview
Hybrid Node.js + Python pipeline using browser automation for extraction and Python for data processing.

### Characteristics
- **API Type**: Browser automation + CSV export
- **Authentication**: Browser session
- **Rate Limiting**: Browser-paced
- **Browser Required**: Yes (Puppeteer via Node.js)

### File Structure

```
audiobee_jefferson_health/
├── 1_index.js                    # Node.js browser automation
├── 5_map_html_to_json.py         # HTML parsing
├── 6_map_json_to_ideon_format.py # Normalization
├── package.json                   # Node.js dependencies
└── run_all.py                     # Pipeline orchestrator
```

### Execution Flow

```
1. Node.js Phase (1_index.js)
   ├── Launch Puppeteer browser
   ├── Navigate to provider directory
   ├── Export search results to CSV
   └── Save raw HTML pages

2. Python Phase (5_map_html_to_json.py)
   ├── Parse HTML content
   └── Extract structured data to JSON

3. Normalization (6_map_json_to_ideon_format.py)
   ├── Map to standard schema
   └── Deduplicate by NPI
```

### Projects
- `audiobee_jefferson_health` (PA)
- `audiobee_physicians_health_plan_mi` (MI)

---

## 6. Werally Type (2 Projects)

### Overview
UHC platform using geographic grid search for comprehensive coverage.

### Characteristics
- **API Type**: REST
- **Authentication**: None (public API)
- **Rate Limiting**: Low
- **Browser Required**: No

### Geographic Grid Configuration

```python
# audiobee_uhc_medicaid/config.py

BASE_URLS = {
    "search": "https://connect.werally.com/rest/provider/v4/search/filtered",
    "details": "https://connect.werally.com/rest/provider/v3/partners/{partner_id}/providers/{provider_id}",
}

# State-specific coordinate grids
POINTS = {
    "AZ": [
        {"lat": 33.4484, "lng": -112.0740, "radius": 150},  # Phoenix area
        {"lat": 32.2226, "lng": -110.9747, "radius": 100},  # Tucson area
        {"lat": 35.1894, "lng": -111.6513, "radius": 120},  # Northern AZ
    ],
    "TX": [
        {"lat": 29.7604, "lng": -95.3698, "radius": 200},   # Houston
        {"lat": 32.7767, "lng": -96.7970, "radius": 200},   # Dallas
        {"lat": 29.4241, "lng": -98.4936, "radius": 150},   # San Antonio
        {"lat": 31.7619, "lng": -106.4850, "radius": 100},  # El Paso
    ],
    # ... more states
}

# Plan mappings per state
PLANS = {
    "AZ": [
        {"partner_id": "AHCCCS", "plan_name": "Arizona Medicaid"},
    ],
    "TX": [
        {"partner_id": "CHIP", "plan_name": "Texas CHIP"},
        {"partner_id": "STAR", "plan_name": "Texas STAR"},
    ],
}
```

### Search Strategy

```
1. For each state in REQ_STATES:
   ├── Load coordinate grid points
   └── For each point:
       ├── Search with radius
       ├── Paginate through results
       └── Cache to disk

2. Deduplicate across overlapping grids
   └── NPI-based deduplication
```

### Projects
- `audiobee_uhc_medicaid` (All states)
- `audiobee_uhc_individual` (All states)

---

## 7. Provider Lenz Type (1 Project)

### Overview
Anti-bot protected site requiring CAPTCHA solving and advanced evasion techniques.

### Characteristics
- **API Type**: Protected REST
- **Authentication**: CAPTCHA token + session
- **Rate Limiting**: Very strict
- **Browser Required**: Yes (Camoufox stealth)

### Anti-Detection Stack

```python
# Required components
import execjs                    # JavaScript execution
from camoufox import Camoufox   # Stealth Firefox
from capsolver_local import capsolver_fn  # CAPTCHA solving

# Stealth browser configuration
browser_config = {
    "headless": True,
    "proxy": {
        "server": "socks5://proxy.dataimpulse.com:824",
        "username": "user",
        "password": "pass",
    },
    "fingerprint_options": {
        "randomize": True,
    },
}
```

### CAPTCHA Solving Flow

```python
async def solve_captcha(page):
    """Solve CAPTCHA using external service."""

    # Detect CAPTCHA presence
    captcha_element = await page.query_selector(".captcha-container")
    if not captcha_element:
        return True  # No CAPTCHA needed

    # Get CAPTCHA image/challenge
    captcha_data = await captcha_element.screenshot()

    # Send to solver service
    solution = await capsolver_fn(captcha_data)

    # Enter solution
    await page.fill("#captcha-input", solution)
    await page.click("#submit-captcha")

    # Wait for validation
    await page.wait_for_selector(".captcha-success", timeout=10000)

    return True
```

### Error Handling

```python
# Special 418 (I'm a teapot) handling
MAX_418_RETRIES = 10
SLEEP_AFTER_418 = 300  # 5 minutes

async def fetch_with_418_handling(url):
    retries = 0

    while retries < MAX_418_RETRIES:
        response = await browser.fetch(url)

        if response.status == 418:
            retries += 1
            print(f"418 error, sleeping {SLEEP_AFTER_418}s...")
            await asyncio.sleep(SLEEP_AFTER_418)
            continue

        return response

    raise Exception("Max 418 retries exceeded")
```

### Projects
- `audiobee_elderplan` (NY)

---

## Configuration Templates

### Standard config.py Template

```python
#!/usr/bin/env python3
"""
Configuration for {PROJECT_NAME}

Site Type: {SITE_TYPE}
Coverage: {STATES}
Coverage Types: {COVERAGE_TYPES}
"""

import os
from pathlib import Path
from uuid import uuid4

# ============================================================
# DATE CONFIGURATION
# ============================================================
PREV_DATE = "20251010"
CURR_DATE = "20251110"
PROJECT_NAME = "audiobee_{project_name}"

# ============================================================
# DIRECTORY STRUCTURE
# ============================================================
BASE_DIR = Path(__file__).parent

DIRS = {
    "raw": os.path.join(CURR_DATE, "raw"),
    "search_results": os.path.join(CURR_DATE, "raw", "search_results"),
    "provider_details": os.path.join(CURR_DATE, "raw", "provider_details"),
    "processed": os.path.join(CURR_DATE, "processed"),
}

PREV_DIRS = {
    "raw": os.path.join(PREV_DATE, "raw"),
    "search_results": os.path.join(PREV_DATE, "raw", "search_results"),
    "provider_details": os.path.join(PREV_DATE, "raw", "provider_details"),
    "processed": os.path.join(PREV_DATE, "processed"),
}

# Create directories
for dir_path in DIRS.values():
    os.makedirs(dir_path, exist_ok=True)

# ============================================================
# API CONFIGURATION
# ============================================================
BASE_URLS = {
    "search": "https://api.example.com/v1/providers/search",
    "details": "https://api.example.com/v1/providers/{provider_id}",
}

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "X-API-Key": os.environ.get("API_KEY", "your-api-key"),
}

# ============================================================
# SEARCH PARAMETERS
# ============================================================
BASE_PARAMS = {
    "network_id": "1",
    "page": "1",
    "limit": "100",
}

# ============================================================
# GEOGRAPHIC CONFIGURATION
# ============================================================
REQ_STATES = ["IL"]
REQ_STATES_ONLY = ["IL", "IN", "WI"]

GEO_COORDS = "39.883875,-88.834467"
RADIUS = "210"

# ============================================================
# REFERENCE DATA
# ============================================================
with open(BASE_DIR / "data" / "specialties.json", "r") as f:
    SPECIALTIES = json.load(f)["search_specialties"]

with open(BASE_DIR / "data" / "networks.json", "r") as f:
    NETWORKS = json.load(f)["networks"]
```

---

## Adding a New Scraper

### Step 1: Identify Site Type

Analyze the target website to determine which pattern it follows:
1. Check network requests for API patterns
2. Identify authentication requirements
3. Test for bot detection

### Step 2: Create Project Structure

```bash
mkdir audiobee_new_carrier
cd audiobee_new_carrier

# Create standard files
touch config.py
touch index_1.py
touch index_2.py
touch index_3.py
touch run_all.py
touch CLAUDE.md

# Create data directories
mkdir -p data
mkdir -p $(date +%Y%m%d)/raw/search_results
mkdir -p $(date +%Y%m%d)/raw/provider_details
mkdir -p $(date +%Y%m%d)/processed
```

### Step 3: Configure Project

Edit `config.py` with appropriate URLs, headers, and parameters.

### Step 4: Implement Phases

Copy patterns from a similar project and adapt to the new API.

### Step 5: Test Pipeline

```bash
python run_all.py
```

---

## References

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [PIPELINE.md](./PIPELINE.md) - Pipeline phase details
- [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) - Development guide

---

*Last Updated: December 2024*

# Developer Onboarding Guide

> **Complete Guide for New Developers Working on the Ideon Scraping Infrastructure**

## Welcome

This guide will help you understand, run, modify, and create new scrapers in the Ideon scraping infrastructure. By the end, you'll be able to:

- Run existing scrapers successfully
- Debug common issues
- Modify scrapers for changed APIs
- Create new scrapers from templates
- Understand the QA validation process

---

## Prerequisites

### Required Software

```bash
# Python 3.10+ (recommended 3.12)
python3 --version

# Node.js 18+ (for healthsparq-server)
node --version
npm --version

# Git
git --version
```

### Python Dependencies

```bash
# Core dependencies (install in each project's venv or globally)
pip install httpx aiofiles orjson pydantic tqdm
pip install tenacity  # Retry logic
pip install browserforge  # Header generation
pip install camoufox  # Stealth browser (optional)

# QA utilities
pip install jsonschema py7zr pandas openpyxl fuzzywuzzy
```

### Node.js Dependencies (for Healthsparq projects)

```bash
cd healthsparq-server
npm install
```

---

## Quick Start

### Running Your First Scraper

```bash
# 1. Navigate to a project
cd /Users/dikson/Work/ideon_scraping/scraping/audiobee_bcbs_il

# 2. Check the current dates in config.py
cat config.py | grep -E "PREV_DATE|CURR_DATE"
# Output:
# PREV_DATE = "20251010"
# CURR_DATE = "20251110"

# 3. Update dates if needed (edit config.py)
# PREV_DATE = "20251110"
# CURR_DATE = "20251210"

# 4. Run the full pipeline
python run_all.py

# Or run individual phases
python index_1.py  # Discovery
python index_2.py  # Extraction
python index_3.py  # Normalization
```

### Running a Healthsparq Project

```bash
# Terminal 1: Start the browser server
cd /Users/dikson/Work/ideon_scraping/scraping/healthsparq-server
PORT=1018 npm start

# Terminal 2: Run the scraper
cd /Users/dikson/Work/ideon_scraping/scraping/audiobee_mvp_health
python run_all.py
```

### Validating Output

```bash
# Run QA validation
cd /Users/dikson/Work/ideon_scraping/scraping
python output_generator/type_check.py audiobee_bcbs_il/

# Generate comparison with previous run
python output_generator/comparison_creator.py audiobee_bcbs_il/
```

---

## Project Structure Deep Dive

### Understanding a Scraper Project

```
audiobee_project_name/
│
├── config.py           # Configuration (URLs, dates, parameters)
│   ├── PREV_DATE       # Previous run date (YYYYMMDD)
│   ├── CURR_DATE       # Current run date (YYYYMMDD)
│   ├── PROJECT_NAME    # Project identifier
│   ├── DIRS            # Output directory paths
│   ├── BASE_URLS       # API endpoints
│   ├── HEADERS         # Request headers
│   ├── BASE_PARAMS     # Default request parameters
│   └── REQ_STATES      # Target states
│
├── index_1.py          # Phase 1: Discovery/Search
│   └── Discovers all provider IDs
│
├── index_2.py          # Phase 2: Detail Extraction
│   └── Fetches detailed info for each provider
│
├── index_3.py          # Phase 3: Normalization
│   └── Transforms to standard output schema
│
├── run_all.py          # Pipeline Orchestrator
│   └── Runs all phases sequentially with error handling
│
├── CLAUDE.md           # Project metadata
│   ├── Site Type       # Platform category
│   ├── Coverage        # States covered
│   └── Approval Date   # When approved
│
├── data/               # Reference data
│   ├── specialties.json
│   ├── networks.json
│   └── allowable_networks.json
│
└── YYYYMMDD/           # Date-versioned output
    ├── raw/
    │   ├── search_results/
    │   └── provider_details/
    └── processed/
        └── project-YYYYMMDD.jsonl
```

### Understanding config.py

```python
# Essential configuration elements

import os
from pathlib import Path

# ======================================
# DATES - Update before each run
# ======================================
PREV_DATE = "20251010"  # Last successful run
CURR_DATE = "20251110"  # Current run

# ======================================
# PROJECT IDENTITY
# ======================================
PROJECT_NAME = "audiobee_bcbs_il"

# ======================================
# DIRECTORIES - Auto-created
# ======================================
DIRS = {
    "raw": os.path.join(CURR_DATE, "raw"),
    "search_results": os.path.join(CURR_DATE, "raw", "search_results"),
    "provider_details": os.path.join(CURR_DATE, "raw", "provider_details"),
    "processed": os.path.join(CURR_DATE, "processed"),
}

# Create directories on import
for d in DIRS.values():
    os.makedirs(d, exist_ok=True)

# ======================================
# API CONFIGURATION
# ======================================
BASE_URLS = {
    "search": "https://api.example.com/providers/search",
    "details": "https://api.example.com/providers/{id}",
}

HEADERS = {
    "Accept": "application/json",
    "X-API-Key": "your-api-key",
}

# ======================================
# SEARCH PARAMETERS
# ======================================
BASE_PARAMS = {
    "network_id": "1",
    "limit": "100",
}

# ======================================
# GEOGRAPHIC SCOPE
# ======================================
REQ_STATES = ["IL"]  # Required states
REQ_STATES_ONLY = ["IL", "IN", "WI"]  # Extended scope
```

---

## Common Tasks

### Task 1: Update Dates for New Run

```python
# In config.py, update:
PREV_DATE = "20251010"  # Previous CURR_DATE
CURR_DATE = "20251210"  # New date (YYYYMMDD)
```

### Task 2: Add a New Network

```python
# 1. Add to networks.json
{
  "networks": [
    {"id": "1", "name": "PPO Network"},
    {"id": "2", "name": "HMO Network"},
    {"id": "3", "name": "NEW Network"}  # Add here
  ]
}

# 2. Update allowable_networks.json if needed
```

### Task 3: Modify API Endpoint

```python
# In config.py, update BASE_URLS:
BASE_URLS = {
    "search": "https://api.example.com/v2/providers/search",  # v1 → v2
    "details": "https://api.example.com/v2/providers/{id}",
}
```

### Task 4: Add New Field to Output

```python
# In index_3.py, modify the mapping function:
def map_provider(raw: dict) -> dict:
    return {
        # Existing fields...
        "provider": {
            "npi": raw.get("npi"),
            "first_name": raw.get("firstName"),
            # Add new field:
            "board_certified": raw.get("boardCertified", False),
        },
        # ...
    }
```

### Task 5: Handle Rate Limiting

```python
import time
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60)
)
def fetch_with_retry(url):
    response = httpx.get(url)

    if response.status_code == 429:  # Too Many Requests
        retry_after = int(response.headers.get("Retry-After", 60))
        time.sleep(retry_after)
        raise Exception("Rate limited, retrying...")

    return response.json()
```

---

## Creating a New Scraper

### Step 1: Analyze the Target Site

```
1. Open browser DevTools (F12)
2. Navigate to provider search
3. Monitor Network tab for API calls
4. Identify:
   - Base URL
   - Authentication method
   - Request/Response format
   - Pagination pattern
```

### Step 2: Choose Template

| Site Behavior | Template |
|---------------|----------|
| REST API, no auth | Carrier template |
| REST API, API key | Carrier template |
| Browser session needed | Healthsparq template |
| CAPTCHA protected | Provider Lenz template |

### Step 3: Create Project Structure

```bash
# Create project directory
PROJECT="audiobee_new_carrier"
mkdir $PROJECT
cd $PROJECT

# Copy template files
cp ../audiobee_multiplan/config.py .
cp ../audiobee_multiplan/index_1.py .
cp ../audiobee_multiplan/index_2.py .
cp ../audiobee_multiplan/index_3.py .
cp ../audiobee_multiplan/run_all.py .

# Create directories
mkdir -p data
mkdir -p $(date +%Y%m%d)/raw/search_results
mkdir -p $(date +%Y%m%d)/raw/provider_details
mkdir -p $(date +%Y%m%d)/processed
```

### Step 4: Configure Project

```python
# Edit config.py with actual values

PROJECT_NAME = "audiobee_new_carrier"

BASE_URLS = {
    "search": "https://actual-api.com/search",
    "details": "https://actual-api.com/details/{id}",
}

HEADERS = {
    "Authorization": "Bearer actual-token",
}

REQ_STATES = ["CA", "TX"]
```

### Step 5: Implement Phases

```python
# index_1.py - Customize search logic
def search_providers():
    # Adapt to actual API structure
    for state in config.REQ_STATES:
        params = {**config.BASE_PARAMS, "state": state}
        response = httpx.get(config.BASE_URLS["search"], params=params)
        # ... process results
```

### Step 6: Create CLAUDE.md

```markdown
# audiobee_new_carrier

## Metadata
- **Site Type**: Carrier
- **Coverage**: CA, TX
- **Coverage Types**: ACA, Medicare Advantage
- **Approval Date**: 2025-01-15

## Notes
- API requires Bearer token authentication
- Rate limit: 100 requests/minute
- Pagination via offset parameter
```

### Step 7: Test and Validate

```bash
# Test individual phases
python index_1.py
python index_2.py
python index_3.py

# Validate output
python ../output_generator/type_check.py .

# Run full pipeline
python run_all.py
```

---

## Debugging Guide

### Problem: "Connection refused" on Healthsparq project

```bash
# Check if server is running
curl http://localhost:1018/health

# Start the server
cd /healthsparq-server && npm start

# Check configured port in config.py
grep HEALTHSPARK_PUPPETEER_PORT config.py
```

### Problem: 403 Forbidden errors

```python
# Possible causes:
# 1. API key expired → Update in config.py
# 2. IP blocked → Use proxy rotation
# 3. Missing headers → Check request headers

# Debug approach:
import httpx
response = httpx.get(url, headers=config.HEADERS)
print(f"Status: {response.status_code}")
print(f"Headers: {response.headers}")
print(f"Body: {response.text[:500]}")
```

### Problem: Empty output file

```bash
# Check Phase 1 output
ls -la 20251110/raw/search_results/

# Check Phase 2 output
ls -la 20251110/raw/provider_details/

# If empty, check index_1.py for errors
python index_1.py 2>&1 | head -50
```

### Problem: Schema validation failed

```bash
# Check specific errors
python output_generator/type_check.py audiobee_project/ 2>&1 | grep "Error"

# Common fixes:
# - Missing required field (npi, unparsed_name)
# - Wrong data type (string vs number)
# - Invalid state code (lowercase vs uppercase)
```

### Problem: Duplicate providers in output

```python
# Check deduplication logic in index_3.py
# Ensure NPI-based deduplication is working

def check_duplicates(filepath):
    seen_npis = set()
    duplicates = []

    with open(filepath, 'r') as f:
        for line in f:
            data = orjson.loads(line)
            npi = data['provider']['npi']
            if npi and npi in seen_npis:
                duplicates.append(npi)
            seen_npis.add(npi)

    print(f"Found {len(duplicates)} duplicate NPIs")
```

---

## Best Practices

### Code Style

```python
# Use type hints
def fetch_provider(provider_id: str) -> dict:
    ...

# Use pathlib for file operations
from pathlib import Path
output_path = Path(config.DIRS["processed"]) / f"{config.PROJECT_NAME}.jsonl"

# Use context managers
with open(filepath, "rb") as f:
    data = orjson.loads(f.read())

# Use tqdm for progress bars
from tqdm import tqdm
for item in tqdm(items, desc="Processing"):
    ...
```

### Error Handling

```python
# Always handle expected errors
try:
    response = httpx.get(url, timeout=30)
    response.raise_for_status()
except httpx.TimeoutException:
    print(f"Timeout fetching {url}")
    # Retry or skip
except httpx.HTTPStatusError as e:
    print(f"HTTP error {e.response.status_code}")
    # Log and continue
```

### Caching

```python
# Always check for existing files before fetching
output_path = f"{config.DIRS['provider_details']}/{provider_id}.json"
if os.path.exists(output_path):
    print(f"Skipping {provider_id} (cached)")
    return

# Then fetch and save
response = httpx.get(url)
with open(output_path, "wb") as f:
    f.write(orjson.dumps(response.json()))
```

### Logging

```python
# Use structured logging
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

logger.info(f"Starting Phase 1 for {config.PROJECT_NAME}")
logger.warning(f"Rate limited, sleeping 60s")
logger.error(f"Failed to fetch {provider_id}: {e}")
```

---

## Testing Checklist

Before submitting a new or modified scraper:

- [ ] `python index_1.py` completes without errors
- [ ] `python index_2.py` completes without errors
- [ ] `python index_3.py` completes without errors
- [ ] Output file exists in `YYYYMMDD/processed/`
- [ ] `python output_generator/type_check.py .` passes
- [ ] Sample records look correct (check 5-10 manually)
- [ ] NPI deduplication is working (no duplicate NPIs)
- [ ] State filtering is correct (only requested states)
- [ ] All required fields are populated

---

## Getting Help

### Documentation
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System overview
- [PIPELINE.md](./PIPELINE.md) - Pipeline details
- [SITE_TYPES_REFERENCE.md](./SITE_TYPES_REFERENCE.md) - Platform specifics
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Common issues

### Existing Examples
- `audiobee_multiplan` - Good Carrier template
- `audiobee_mvp_health` - Good Healthsparq template
- `audiobee_bcbs_il` - Good Sapphire template

### Key Files
- `/docs/site-type-mapping.md` - All projects by type
- `/docs/project-links.md` - Project index
- `/PLAN.md` - Infrastructure scaling plan

---

*Last Updated: December 2024*

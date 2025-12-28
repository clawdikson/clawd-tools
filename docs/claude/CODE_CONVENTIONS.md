# Code Conventions

This document covers the standardized patterns used across all scraper projects.

## Pipeline Architecture (3-4 Phases)

All scrapers follow a consistent multi-phase architecture:

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

## Configuration Pattern (config.py)

Every project includes a `config.py` with a standardized structure:

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

See `core/data/output_json_schema.json` for the complete schema definition.

## Shared Package Pattern (Local vs Root)

### Root-Level Shared Package

The `core/` submodule (formerly `shared_package`) provides v3.0 utilities:

- Config management (Pydantic Settings)
- SQLiteFS and JSONL I/O with async support
- Loguru-based logging
- Validation models
- Proxy orchestration
- Browser/HTTP session management

### Project-Level Shared Package

Some individual scrapers include local `shared_package/` directories for project-specific session management:

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

### Migration Note

Root `shared_package/` submodule was renamed to `core/` (Dec 2025) to clarify it as the central shared utilities package. Use backwards-compatible imports:

```python
try:
    from core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
```

## Key Files Reference

| File         | Purpose                                          |
| ------------ | ------------------------------------------------ |
| `config.py`  | Project configuration (URLs, params, dates)      |
| `index_1.py` | Phase 1: Search/discovery                        |
| `index_2.py` | Phase 2: Detail extraction                       |
| `index_3.py` | Phase 3: Data normalization                      |
| `run_all.py` | Pipeline orchestrator                            |
| `CLAUDE.md`  | Project metadata (site type, coverage, approval) |

## Coverage Types

| Type                   | Description           | Example Projects                           |
| ---------------------- | --------------------- | ------------------------------------------ |
| **Medicare Advantage** | Senior plans (65+)    | audiobee_anthem, audiobee_humana           |
| **Medicaid**           | State-funded programs | audiobee_uhc_medicaid, audiobee_amerigroup |
| **ACA**                | Marketplace plans     | audiobee_florida_blue, audiobee_bcbs_il    |
| **Large Group**        | Employer plans        | audiobee_multiplan                         |

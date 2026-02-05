# Coding Framework Architecture

**Purpose**: Define what goes where, how code will be written, and architectural-level patterns across all 95+ scraper projects.

---

## Directory Structure Standard

### Project Layout

Every scraper project MUST follow this structure:

```
audiobee_{project_name}/
├── config.py              # Configuration (dates, URLs, params)
├── index_1.py             # Phase 1: Discovery/Search
├── index_2.py             # Phase 2: Detail extraction
├── index_3.py             # Phase 3: Data mapping/normalization
├── run_all.py             # Pipeline orchestrator
├── utils.py               # Project-specific utilities (optional)
├── CLAUDE.md              # Project metadata (optional)
├── .env                   # Local secrets (gitignored)
├── {YYYYMMDD}/            # Date-versioned output
│   ├── raw/               # Raw API responses
│   │   ├── search_results/
│   │   └── provider_details/
│   └── processed/         # Normalized output
└── old_code/              # Deprecated scripts (optional)
```

### Shared Package Layout

```
shared/
├── __init__.py
├── config/                # Configuration management
│   ├── __init__.py
│   ├── base.py           # BaseConfig class
│   ├── sapphire.py       # SapphireConfig
│   ├── healthsparq.py    # HealthsparqConfig
│   ├── carrier.py        # CarrierConfig
│   ├── anthem.py         # AnthemConfig
│   └── factory.py        # load_config() factory
├── io/                    # File I/O utilities
│   ├── __init__.py
│   ├── jsonl.py          # JSONLReader, JSONLWriter
│   ├── file_manager.py   # AtomicWriter, ensure_dir
│   └── cache.py          # CachedJSONLoader
├── logging/               # Logging infrastructure
│   ├── __init__.py
│   └── logger.py         # ScraperLogger
├── validation/            # Data validation
│   ├── __init__.py
│   ├── raw_file.py       # RawFileValidator
│   ├── schema.py         # Pydantic models
│   └── report.py         # ValidationReport
├── retry/                 # Resilience patterns
│   ├── __init__.py
│   └── decorators.py     # @with_retry, circuit breaker
└── pyproject.toml
```

---

## Module Responsibilities

### config.py

**Responsibility**: ALL configuration values

```python
# GOOD: All config in config.py
from shared.config import load_config

config = load_config("sapphire", "audiobee_bcbs_il")

# Backward compat exports
PREV_DATE = config.prev_date
CURR_DATE = config.curr_date
DIRS = config.dirs

# BAD: Hardcoded values in index_*.py files
```

### index_1.py (Discovery Phase)

**Responsibility**: Find all providers/locations to scrape

```python
"""
Phase 1: Discovery
- Execute paginated search queries
- Cache raw responses to {date}/raw/search_results/
- Extract unique IDs for Phase 2
- NO data transformation
"""

# Standard imports
import asyncio
from config import DIRS, REQ_STATES
from shared.io import JSONLWriter
from shared.logging import get_logger

logger = get_logger(__name__)

async def main():
    writer = JSONLWriter(DIRS["search_results"])
    # ... search logic
```

### index_2.py (Detail Phase)

**Responsibility**: Fetch detailed data for each ID

```python
"""
Phase 2: Detail Extraction
- Load IDs from Phase 1
- Fetch individual provider details
- Cache to {date}/raw/provider_details/
- Handle rate limiting/retries
- NO data transformation
"""
```

### index_3.py (Mapping Phase)

**Responsibility**: Transform raw data to output schema

```python
"""
Phase 3: Data Normalization
- Load raw data from Phases 1-2
- Map to standard ProviderRecord schema
- Deduplicate by NPI
- Write to {date}/processed/
- NO API calls
"""
```

### run_all.py

**Responsibility**: Orchestrate pipeline execution

```python
"""
Pipeline Orchestrator
- Execute phases sequentially
- Track progress
- Aggregate errors
- Optional: validation and reporting
"""
```

---

## Code Patterns

### Import Order

```python
# 1. Standard library
import os
import asyncio
from pathlib import Path
from typing import Dict, List, Optional

# 2. Third-party
import httpx
import orjson
from tqdm import tqdm

# 3. Shared utilities
from shared.config import load_config
from shared.io import JSONLWriter, JSONLReader
from shared.logging import get_logger

# 4. Local imports
from config import DIRS, REQ_STATES
```

### Function Naming

```python
# Phase 1 functions
def search_providers()
def fetch_search_page()
def extract_provider_ids()

# Phase 2 functions
def fetch_provider_detail()
def fetch_location_detail()
def fetch_affiliations()

# Phase 3 functions
def map_provider()
def map_address()
def deduplicate_by_npi()
```

### Error Handling Pattern

```python
from shared.retry import with_retry
from shared.logging import get_logger

logger = get_logger(__name__)

@with_retry(max_attempts=3, backoff=2.0)
async def fetch_provider(provider_id: str) -> Optional[dict]:
    """Fetch single provider with retry."""
    try:
        response = await client.get(f"/providers/{provider_id}")
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP error for {provider_id}: {e.response.status_code}")
        if e.response.status_code == 404:
            return None  # Expected - provider not found
        raise  # Will trigger retry
    except httpx.RequestError as e:
        logger.error(f"Request failed for {provider_id}: {e}")
        raise  # Will trigger retry
```

### Progress Tracking Pattern

```python
from tqdm import tqdm
from shared.logging import get_logger

logger = get_logger(__name__)

async def process_all(items: list):
    total = len(items)
    success = 0
    failed = 0

    for item in tqdm(items, desc="Processing"):
        try:
            await process_item(item)
            success += 1
        except Exception as e:
            failed += 1
            logger.error(f"Failed {item}: {e}")

    logger.info(f"Complete: {success}/{total} success, {failed} failed")
```

### File I/O Pattern

```python
from shared.io import JSONLWriter, JSONLReader

# Writing
async def save_results(results: list, output_dir: str):
    writer = JSONLWriter(output_dir)
    for result in results:
        await writer.write(result, filename="providers.jsonl")
    await writer.close()

# Reading
def load_results(input_dir: str) -> list:
    reader = JSONLReader(input_dir)
    return list(reader.read_all("providers.jsonl"))
```

---

## Concurrency Patterns

### Async HTTP Client

```python
import httpx
from config import BATCH_SIZE, SEMAPHORE

async def create_client() -> httpx.AsyncClient:
    """Create configured HTTP client."""
    return httpx.AsyncClient(
        timeout=httpx.Timeout(30.0),
        limits=httpx.Limits(
            max_connections=SEMAPHORE,
            max_keepalive_connections=SEMAPHORE // 2,
        ),
    )
```

### Semaphore-Based Rate Limiting

```python
import asyncio
from config import SEMAPHORE

semaphore = asyncio.Semaphore(SEMAPHORE)

async def fetch_with_limit(url: str) -> dict:
    async with semaphore:
        return await fetch(url)

async def fetch_all(urls: list) -> list:
    tasks = [fetch_with_limit(url) for url in urls]
    return await asyncio.gather(*tasks, return_exceptions=True)
```

### Batch Processing

```python
from itertools import islice

def batched(iterable, n):
    """Yield successive n-sized batches."""
    it = iter(iterable)
    while batch := list(islice(it, n)):
        yield batch

async def process_in_batches(items: list, batch_size: int = 100):
    for batch in batched(items, batch_size):
        results = await asyncio.gather(*[process(item) for item in batch])
        yield from results
```

---

## Data Flow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  index_1.py │───>│  index_2.py │───>│  index_3.py │
└─────────────┘    └─────────────┘    └─────────────┘
      │                  │                  │
      v                  v                  v
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   raw/      │    │   raw/      │    │ processed/  │
│ search_     │    │ provider_   │    │ {proj}-     │
│ results/    │    │ details/    │    │ {date}.jsonl│
└─────────────┘    └─────────────┘    └─────────────┘
```

---

## Type Annotations

### Required for All New Code

```python
from typing import Dict, List, Optional, Any, Iterator

def map_provider(
    raw_data: Dict[str, Any],
    network_id: str
) -> Optional[Dict[str, Any]]:
    """
    Map raw provider data to output schema.

    Args:
        raw_data: Raw provider data from API
        network_id: Network identifier

    Returns:
        Mapped provider record or None if invalid
    """
    ...
```

### Common Type Patterns

```python
from typing import TypedDict, Literal

class ProviderDict(TypedDict):
    npi: Optional[str]
    unparsed_name: str
    provider_type: Literal["individual", "organization"]
    gender: Optional[Literal["M", "F", "O", "U"]]

class AddressDict(TypedDict):
    street_line_1: str
    city: str
    state: str
    zip: str
```

---

## Testing Guidelines

### Test File Location

```
audiobee_project/
├── tests/                 # Project-specific tests
│   ├── test_mapping.py
│   └── fixtures/
│       └── sample_data.json
```

### Test Patterns

```python
import pytest
from index_3 import map_provider

@pytest.fixture
def sample_raw_data():
    return {
        "npi": "1234567890",
        "name": "John Smith MD",
        ...
    }

def test_map_provider_valid(sample_raw_data):
    result = map_provider(sample_raw_data, "network_123")
    assert result is not None
    assert result["provider"]["npi"] == "1234567890"

def test_map_provider_invalid_npi():
    result = map_provider({"npi": "invalid"}, "network_123")
    assert result is None
```

---

## Code Quality Checks

### Pre-commit Hooks (Recommended)

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

### Type Checking

```bash
# Run mypy on shared utilities
mypy shared/ --ignore-missing-imports
```

---

## What NOT To Do

### Anti-Patterns to Avoid

```python
# BAD: Hardcoded values in code
API_KEY = "abc123"  # Should be in .env

# BAD: Global mutable state
results = []  # Use function parameters instead

# BAD: Mixed responsibilities
def search_and_map():  # Split into separate functions
    ...

# BAD: Suppressed exceptions
except Exception:
    pass  # Always log or handle

# BAD: String concatenation for paths
path = "raw/" + "data.json"  # Use os.path.join()
```

---

## Summary

| Layer | Location | Responsibility |
|-------|----------|----------------|
| Config | `config.py` | All configuration |
| Discovery | `index_1.py` | Search, find IDs |
| Details | `index_2.py` | Fetch details |
| Mapping | `index_3.py` | Transform data |
| Orchestration | `run_all.py` | Pipeline control |
| Utilities | `shared/` | Reusable components |

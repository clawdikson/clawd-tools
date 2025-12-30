# Code Style Guide

## Naming Conventions

### Files

| Type | Convention | Examples |
|------|------------|----------|
| Pipeline phases | `index_N.py` | `index_1.py`, `index_2.py`, `index_3.py` |
| Configuration | `config.py` | - |
| Orchestrator | `run_all.py` | - |
| Utilities | `snake_case.py` | `file_writer.py`, `browser_session.py` |
| Tests | `test_*.py` | `test_config.py`, `test_io.py` |
| Version iterations | `*_vN.py` | `index_1_v3.py` |

### Functions & Variables

| Type | Convention | Examples |
|------|------------|----------|
| Functions | `snake_case` | `fetch_search_results()`, `get_provider_details()` |
| Private functions | `_snake_case` | `_process_summary()`, `_get_headers()` |
| Variables | `snake_case` | `provider_data`, `search_results` |
| Constants | `UPPER_SNAKE_CASE` | `PREV_DATE`, `CURR_DATE`, `MAX_WORKERS` |
| Classes | `PascalCase` | `BrowserSession`, `HealthSpark`, `JSONLWriter` |

### Directories

| Type | Convention | Examples |
|------|------------|----------|
| Projects | `audiobee_*` | `audiobee_bcbs_il`, `audiobee_florida_blue` |
| Date outputs | `YYYYMMDD` | `20251227/raw/`, `20251227/processed/` |
| Raw data | `raw/` subdirs | `raw/search_results/`, `raw/provider_details/` |
| Processed data | `processed/` | `processed/providers.jsonl` |

## File Organization

### Standard Project Structure

```
audiobee_project/
├── config.py           # Configuration constants
├── index_1.py          # Phase 1: Search
├── index_2.py          # Phase 2: Details
├── index_3.py          # Phase 3: Normalize
├── run_all.py          # Orchestrator
├── CLAUDE.md           # AI context (optional)
├── pyproject.toml      # Dependencies
└── YYYYMMDD/           # Output directory
    ├── raw/
    │   ├── search_results/
    │   └── provider_details/
    └── processed/
```

### config.py Pattern

```python
import os

# Date configuration
PREV_DATE = "20251010"
CURR_DATE = "20251110"
PROJECT_NAME = "audiobee_*"

# Execution parameters
MAX_WORKERS = 10
BATCH_SIZE = 1000

# Directory structure
DIRS = {
    "raw": os.path.join(CURR_DATE, "raw"),
    "search_results": os.path.join(CURR_DATE, "raw", "search_results"),
    "provider_details": os.path.join(CURR_DATE, "raw", "provider_details"),
    "processed": os.path.join(CURR_DATE, "processed"),
}

# Create directories
for dir_path in DIRS.values():
    os.makedirs(dir_path, exist_ok=True)

# API configuration
BASE_URLS = {
    "search": "https://api.example.com/search",
    "details": "https://api.example.com/details",
}

BASE_PARAMS = {
    "network_id": "...",
    "page": "1",
    "limit": "100",
}

# Geographic scope
REQ_STATES = ["IL", "IN", "WI", "MI"]
```

## Import Style

### Import Order

```python
# 1. Standard library
import os
import sys
import json
from pathlib import Path
from typing import Any, Optional

# 2. Third-party packages
import httpx
import orjson
import pandas as pd
from tqdm import tqdm
from pydantic import BaseModel

# 3. Local imports
from config import DIRS, BASE_URLS, CURR_DATE
from shared_package.session import BrowserSession
```

### Backwards-Compatible Imports

```python
# For core package utilities
try:
    from core.logging import logger
    from core.io import JSONLWriter
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
```

### Path Manipulation for Cross-Project Imports

```python
import sys
from pathlib import Path

workspace_root = Path(__file__).parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from output_generator import type_checker, sample_generator
```

## Code Patterns

### Async HTTP Requests

```python
import asyncio
import httpx

async def fetch_data(url: str, params: dict) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()

# With semaphore for rate limiting
semaphore = asyncio.Semaphore(10)

async def fetch_with_limit(url: str) -> dict:
    async with semaphore:
        return await fetch_data(url, {})
```

### JSONL File Operations

```python
import orjson

# Writing JSONL
def write_jsonl(file_path: str, records: list[dict]) -> None:
    with open(file_path, "wb") as f:
        for record in records:
            f.write(orjson.dumps(record) + b"\n")

# Reading JSONL
def read_jsonl(file_path: str) -> list[dict]:
    records = []
    with open(file_path, "rb") as f:
        for line in f:
            if line.strip():
                records.append(orjson.loads(line))
    return records

# Using core package (preferred)
from core.io import JSONLWriter, JSONLReader

with JSONLWriter("output.jsonl", dedup_key="npi") as writer:
    for record in records:
        writer.write(record)  # Auto-deduplicates

with JSONLReader("output.jsonl", skip_invalid_lines=True) as reader:
    for record in reader:
        process(record)
```

### Context Managers

```python
# Browser session
async with ResilientBrowserSession(proxy_types=[ProxyType.SMARTPROXY_SESSION]) as session:
    await session.login(url)
    response = await session.get("/api/data")

# File I/O
with JSONLWriter("output.jsonl") as writer:
    writer.write(record)

# DataStore
with create_store("data.db") as store:
    store.put("key.json", data)
```

### Dataclasses for Results

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class PhaseResult:
    phase: int
    success: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)

@dataclass
class ScraperResult:
    success: bool
    providers_count: int
    error: str | None = None
    phase_results: dict[int, PhaseResult] = field(default_factory=dict)
```

### Pydantic Models

```python
from pydantic import BaseModel, Field, field_validator

class Provider(BaseModel):
    npi: str = Field(..., min_length=10, max_length=10)
    first_name: str | None = None
    last_name: str | None = None
    state: str = Field(..., min_length=2, max_length=2)

    @field_validator("state")
    @classmethod
    def uppercase_state(cls, v: str) -> str:
        return v.upper()
```

## Error Handling

### Try/Except Pattern

```python
import traceback

def process_provider(provider_id: str) -> dict | None:
    try:
        response = fetch_details(provider_id)
        return response.json()
    except httpx.HTTPStatusError as e:
        print(f"HTTP error for {provider_id}: {e.response.status_code}")
        return None
    except Exception as e:
        print(f"Error processing {provider_id}: {e}")
        traceback.print_exc()
        return None
```

### Batch Processing with Continue

```python
from tqdm import tqdm

results = []
errors = []

for provider_id in tqdm(provider_ids, desc="Processing"):
    try:
        result = process_provider(provider_id)
        if result:
            results.append(result)
    except Exception as e:
        errors.append({"id": provider_id, "error": str(e)})
        continue  # Continue on individual failures

print(f"Processed: {len(results)}, Errors: {len(errors)}")
```

### Retry with Tenacity

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def fetch_with_retry(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
```

## Logging

### Using Core Logger (Preferred)

```python
try:
    from core.logging import logger, setup_logging, set_trace_id
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# Setup at startup
setup_logging(
    project_name="audiobee_bcbs_il",
    run_id="20251227",
    log_dir="logs",
    level="INFO",
)

# Structured logging
set_trace_id(f"provider_{npi}")
logger.info("Processing provider", npi=npi, phase=2)
logger.warning("Rate limited", retry_after=60, status_code=429)
logger.error("API failure", endpoint="/search", error=str(e))
```

### Print Statements (Legacy)

```python
# Simple progress (legacy pattern, still common)
print(f"Processing {len(providers)} providers...")
print(f"✅ Phase 1 complete: {total_found} providers found")
print(f"❌ Error: {e}")
```

## Testing

### Test File Structure

```python
"""Unit tests for file I/O utilities."""
from pathlib import Path

import pytest
import orjson

from shared_package.io import BoundedSet, JSONLWriter, JSONLReader


def test_bounded_set_basic_operations():
    """Test BoundedSet add, contains, len operations."""
    bset = BoundedSet(max_size=3)
    bset.add("a")
    bset.add("b")
    
    assert "a" in bset
    assert "b" in bset
    assert len(bset) == 2


def test_jsonl_writer_context_manager(temp_dir):
    """Test JSONLWriter as context manager."""
    file_path = temp_dir / "output.jsonl"
    
    with JSONLWriter(file_path) as writer:
        writer.write({"npi": "1234567890"})
    
    assert file_path.exists()


@pytest.fixture
def temp_dir(tmp_path):
    """Provide temporary directory for tests."""
    return tmp_path
```

### Test Markers

```python
import pytest

@pytest.mark.unit
def test_fast_operation():
    pass

@pytest.mark.integration
def test_api_call():
    pass

@pytest.mark.slow
def test_large_dataset():
    pass
```

## Git Commits

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting (no code change) |
| `refactor` | Code restructuring (no feature/fix) |
| `perf` | Performance improvement |
| `test` | Adding/fixing tests |
| `build` | Build system or dependencies |
| `ci` | CI configuration |
| `chore` | Maintenance (no src/test change) |

### Examples

```bash
feat(scraper): add retry logic for rate-limited requests
fix(index_2): handle missing NPI in provider response
docs: update CLAUDE.md with conventional commits guide
refactor(config): extract URL building to helper function
perf(sqlite): implement buffered writes for 15x speedup
```

## Do's and Don'ts

### Do

- Use `orjson` instead of `json` for performance
- Use JSONL format for large datasets
- Use date-versioned output directories (`YYYYMMDD/`)
- Use NPI-based deduplication
- Use context managers for file/session handling
- Use `tqdm` for progress bars
- Prefer `core/` implementations over reinventing
- Use async/await for concurrent HTTP requests
- Use `asyncio.Semaphore` for rate limiting

### Don't

- Don't use `print()` for logging in new code (use `logger`)
- Don't hardcode credentials (use environment variables)
- Don't commit `.env` files or credentials
- Don't use `json` module (use `orjson`)
- Don't create empty `__init__.py` files without exports
- Don't use `cd && command` in scripts (use `workdir` parameter)
- Don't use interactive git commands (`-i` flag)
- Don't skip type hints in new `core/` code

## Type Hints

### New Code (core/, healthsparq/)

```python
from typing import Any, Optional
from pathlib import Path

def process_provider(
    provider_id: str,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Process a single provider."""
    ...

async def fetch_data(url: str) -> list[dict[str, Any]]:
    """Fetch data from API."""
    ...
```

### Legacy Code (audiobee_*)

Type hints are optional in individual scraper projects. Pragmatic approach - scripts are short and task-specific.

## Documentation

### Docstrings (Optional in Scrapers)

```python
# Core package - use docstrings
def setup_logging(
    project_name: str,
    run_id: str,
    log_dir: str | Path = "logs",
    level: str = "INFO",
) -> None:
    """Setup loguru logging with rich context format.

    Args:
        project_name: Project identifier (e.g., 'audiobee_bcbs_il')
        run_id: Unique run identifier for correlation
        log_dir: Directory for log files (default: 'logs')
        level: Log level (default: 'INFO')
    """
    ...

# Scraper projects - docstrings optional
def fetch_search_results(healthspark, plan, state, county, filters, page):
    # Implementation
    ...
```

### CLAUDE.md Files

Each major component should have a `CLAUDE.md` file providing AI context:

- Project overview
- Build/run commands
- Architecture notes
- Key patterns
- Dependencies

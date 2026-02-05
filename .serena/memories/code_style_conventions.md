# Code Style and Conventions

## General Style
- **No docstrings** typically (scripts are short and task-specific)
- **No type hints** in most existing code (pragmatic approach)
- **Underscored private functions**: `_process_summary()`, `_get_headers()`
- **UPPERCASE for constants**: `PREV_DATE`, `CURR_DATE`, `DIRS`, `BASE_URLS`

## File Naming
- `index_N.py` - Pipeline phases (index_1, index_2, index_3)
- `config.py` - Configuration constants
- `run_all.py` - Orchestrator
- `utils.py` - Helper functions
- Version suffixes: `index_1_v3.py` (for iterations)

## Config.py Pattern
```python
import os

PREV_DATE = "20251010"
CURR_DATE = "20251110"
PROJECT_NAME = "audiobee_*"
BATCH_SIZE = 1000

DIRS = {
    "raw": os.path.join(CURR_DATE, "raw"),
    "search_results": os.path.join(CURR_DATE, "raw", "search_results"),
    "processed": os.path.join(CURR_DATE, "processed"),
}

BASE_URLS = {
    "search": "https://...",
    "details": "https://...",
}

BASE_PARAMS = {
    "network_id": "...",
    "page": "1",
    "limit": "100",
}

REQ_STATES = ["IL", "IN", ...]
```

## Data Handling
- Use `orjson` not `json` for performance
- JSONL format for large datasets (line-delimited JSON)
- Date-versioned output: `{YYYYMMDD}/raw/`, `{YYYYMMDD}/processed/`
- NPI-based deduplication is standard

## Async Patterns
- `async def` functions with `await`
- `asyncio.gather()` for concurrent operations
- `asyncio.Semaphore()` for rate limiting
- `aiofiles` for async file I/O

## Imports Organization
```python
# Standard library
import os
import sys

# Third-party
from tqdm import tqdm
import orjson

# Local
from config import DIRS, BASE_URLS, _get_headers
```

## Error Handling
- `try/except` blocks around HTTP calls
- Retry logic via `tenacity` library
- Print statements for logging (not logging module)
- Continue on individual failures in batch processing

## Output Generator Imports
```python
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_root not in sys.path: sys.path.insert(0, workspace_root)

from output_generator import type_checker, sample_generator, comparison_creator
```

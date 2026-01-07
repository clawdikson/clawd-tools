# Migration Plan: output_generator → core/qa

**Version**: 1.1 (P0 Fixes Applied)
**Date**: 2025-12-28
**Status**: Draft - Expert Panel Reviewed
**Author**: AI Assistant

---

## Overview

Migrate QA utilities from `output_generator/` to `core/qa/` module, consolidating schema validation, cross-run comparison, sampling, and reporting capabilities into the shared package. This migration includes performance optimizations, improved error handling, and alignment with core/ design patterns.

### Scope

| Current Location                            | Target Location                        | Status     |
| ------------------------------------------- | -------------------------------------- | ---------- |
| `output_generator/type_check.py`            | `core/qa/validator.py`                 | To migrate |
| `output_generator/comparison_creator.py`    | `core/qa/comparison.py`                | To migrate |
| `output_generator/sample_generator.py`      | `core/qa/sampler.py`                   | To migrate |
| `output_generator/report_generator.py`      | `core/qa/reporter.py`                  | To migrate |
| `output_generator/get_per_STATE_counts.py`  | `core/qa/statistics.py`                | To migrate |
| `output_generator/get_per_state_scraped.py` | (merged into statistics.py)            | To migrate |
| `output_generator/states_coordinates.json`  | `core/data/us_states_coordinates.json` | To copy    |
| `output_generator/States_Coordinates.xlsx`  | (deprecated - use JSON only)           | Archive    |

### Goals

1. **Consolidation**: Single source of QA utilities for 86 scraper projects
2. **Performance**: Optimize memory-intensive operations (streaming, chunked processing)
3. **Reliability**: Improved error handling, graceful degradation for missing data
4. **Consistency**: Align with core/ design patterns (Protocols, logging, configuration)
5. **Testability**: Full test coverage with parametrized backend tests

### Non-Goals

- API-based coverage verification (get_per_STATE_counts.py external dependencies)
- Real-time QA dashboards
- GUI tools

---

## Technical Analysis

### Current Architecture Issues

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Current State (output_generator/)                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐       │
│  │  type_check.py   │    │comparison_creator│    │ report_generator │       │
│  │  (666 lines)     │    │   (740 lines)    │    │   (241 lines)    │       │
│  ├──────────────────┤    ├──────────────────┤    ├──────────────────┤       │
│  │ ❌ Embedded       │    │ ❌ Double file    │    │ ❌ Triple file   │       │
│  │    schema (164L)  │    │    reads         │    │    reads         │       │
│  │ ❌ Full file in   │    │ ❌ iterrows()    │    │ ❌ Excel in loop │       │
│  │    memory         │    │ ❌ gc.collect()  │    │                  │       │
│  │ ❌ O(n×m×k) loop │    │    in loop       │    │                  │       │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘       │
│           │                       │                       │                  │
│           ▼                       ▼                       ▼                  │
│  ┌───────────────────────────────────────────────────────────────────┐      │
│  │                     Shared Issues                                  │      │
│  │  • Mix of print() and logging                                     │      │
│  │  • Inconsistent error handling                                    │      │
│  │  • Hardcoded paths and file structures                            │      │
│  │  • No test coverage                                               │      │
│  │  • Schema duplication with core/data/output_json_schema.json      │      │
│  └───────────────────────────────────────────────────────────────────┘      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Performance Issues Identified

| File                       | Issue                            | Line(s) | Severity | Solution                     |
| -------------------------- | -------------------------------- | ------- | -------- | ---------------------------- |
| `type_check.py`            | Full file in memory for dedup    | 582-594 | **High** | Use core/io BoundedSet       |
| `type_check.py`            | O(n×m×k) nested loop             | 247-262 | Medium   | Vectorize with Polars        |
| `comparison_creator.py`    | Double file read                 | 303-318 | **High** | Single-pass processing       |
| `comparison_creator.py`    | `iterrows()` on large DataFrames | 91-106  | Medium   | Use `DataFrame.apply()`      |
| `comparison_creator.py`    | `gc.collect()` in loop           | 540     | Medium   | Fix memory management        |
| `report_generator.py`      | Triple JSONL file read           | 129-166 | **High** | Single-pass with aggregation |
| `sample_generator.py`      | Full file for `random.sample()`  | 22-23   | Medium   | Reservoir sampling           |
| `get_per_state_scraped.py` | Excel in loop                    | 20      | **High** | Cache at module level        |

### Dependency Analysis

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Dependencies to Add to core/                                              │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  Already in core/:           Need to Add:          Optional (P2):        │
│  ├─ orjson                   ├─ pandas            ├─ polars              │
│  ├─ jsonschema               ├─ openpyxl          ├─ rapidfuzz           │
│  ├─ loguru                   ├─ xlsxwriter        │   (replaces          │
│  └─ pydantic                 ├─ fuzzywuzzy*       │    fuzzywuzzy)       │
│                              ├─ python-levenshtein│                       │
│                              ├─ py7zr             │                       │
│                              └─ tqdm              │                       │
│                                                                           │
│  * fuzzywuzzy has GPL-licensed C extension; consider rapidfuzz (MIT)     │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Target Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Target State (core/qa/)                                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  core/                                                                       │
│  ├── data/                          # REFERENCE DATA MODULE                  │
│  │   ├── __init__.py                # NEW: Public API for data loading       │
│  │   ├── loader.py                  # NEW: Cached reference data loading     │
│  │   ├── output_json_schema.json    # ✓ Already exists                      │
│  │   ├── uszips.xlsx                # ✓ Already exists                      │
│  │   ├── us_states_coordinates.json # NEW: From output_generator            │
│  │   └── us_specialties.json        # NEW: Specialty code mappings          │
│  │                                                                           │
│  └── qa/                            # NEW MODULE                             │
│      ├── __init__.py                # Public API exports                     │
│      ├── base.py                    # QAResult Protocol, QAError hierarchy   │
│      ├── config.py                  # QASettings (Pydantic Settings)         │
│      ├── validator.py               # Schema validation + data collection    │
│      ├── comparison.py              # Cross-run diff analysis                │
│      ├── sampler.py                 # Random sampling + archive creation     │
│      ├── reporter.py                # Excel report generation                │
│      ├── statistics.py              # State-level statistics                 │
│      └── cli.py                     # Typer CLI (python -m core.qa)          │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────┐      │
│  │                    Design Improvements                             │      │
│  │  ✅ Single schema source (core/data/output_json_schema.json)      │      │
│  │  ✅ Protocol-based abstractions for testability                   │      │
│  │  ✅ Streaming/chunked processing for large files                  │      │
│  │  ✅ Integrated with core/logging                                  │      │
│  │  ✅ Pydantic Settings configuration                               │      │
│  │  ✅ Full test coverage with parametrized tests                    │      │
│  │  ✅ Graceful degradation for missing prev_date                    │      │
│  └───────────────────────────────────────────────────────────────────┘      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Foundation (Day 1-2)

#### 1.1 Create Module Structures

**core/data/ (Reference Data Service)**

```
core/data/
├── __init__.py                # Public API: get_schema, get_state_coordinates, get_zip_to_state
├── loader.py                  # Cached reference data loading with @cache decorators
├── output_json_schema.json    # ✓ Already exists
├── uszips.xlsx                # ✓ Already exists
├── us_states_coordinates.json # NEW: From output_generator/states_coordinates.json
└── us_specialties.json        # NEW: Optional specialty code mappings
```

**core/qa/ (QA Utilities)**

```
core/qa/
├── __init__.py           # Public API: validate, compare, sample, report, statistics
├── base.py               # QAResult, QAError, QAToolProtocol
├── config.py             # QASettings (Pydantic BaseSettings)
└── README.md             # Module documentation
```

**Files to Create:**

##### core/qa/**init**.py

```python
"""
QA utilities for provider data validation and reporting.

Usage:
    from core.qa import validate, compare, sample, report

    # Validate output schema
    result = validate(jsonl_path, schema_path=None)
    if result.is_success:
        print(f"Valid: {result.metrics.valid_records}")

    # Compare runs
    result = compare(curr_path, prev_path, output_path)
    print(f"Added: {result.metrics.added}, Removed: {result.metrics.removed}")

    # Generate samples
    result = sample(jsonl_path, output_dir, count=10)

    # Generate report
    result = report(project_name, curr_date, prev_date, states)

    # Access outcome details (P0: new structure)
    print(f"Status: {result.outcome.status}")
    print(f"Elapsed: {result.outcome.elapsed_seconds:.1f}s")
"""

__version__ = "1.0.0"

from .base import (
    QAResult,
    QAOutcome,
    QAStatus,
    QAError,
    ValidationError,
    ComparisonError,
    ConfigurationError,
    QATimeoutError,
    QAToolProtocol,
    DEFAULT_TIMEOUT_SECONDS,
    run_with_timeout,
)
from .config import QASettings, load_qa_config
from .validator import validate, Validator, ValidationMetrics
from .comparison import compare, Comparator, ComparisonMetrics
from .sampler import sample, Sampler, SamplingMetrics
from .reporter import report, Reporter, ReportMetrics
from .statistics import get_state_counts, get_coverage

__all__ = [
    # Core functions
    "validate",
    "compare",
    "sample",
    "report",
    "get_state_counts",
    "get_coverage",
    # Classes
    "Validator",
    "Comparator",
    "Sampler",
    "Reporter",
    # Result types (P0: new structure)
    "QAResult",
    "QAOutcome",
    "QAStatus",
    # Metrics types
    "ValidationMetrics",
    "ComparisonMetrics",
    "SamplingMetrics",
    "ReportMetrics",
    # Exceptions
    "QAError",
    "ValidationError",
    "ComparisonError",
    "ConfigurationError",
    "QATimeoutError",
    # Protocols and utilities
    "QAToolProtocol",
    "DEFAULT_TIMEOUT_SECONDS",
    "run_with_timeout",
    # Configuration
    "QASettings",
    "load_qa_config",
]
```

##### core/qa/base.py

```python
"""Base types and protocols for QA utilities.

Design improvements based on expert panel review:
- Split QAResult into QAOutcome + type-specific metrics (Martin Fowler)
- Added timeout support to Protocol (Michael Nygard)
- Added TimeoutError for operation timeout handling
"""

from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable, TypeVar, Generic

# Default timeout for QA operations (5 minutes)
DEFAULT_TIMEOUT_SECONDS = 300

class QAStatus(Enum):
    """Status of QA operation."""
    SUCCESS = "success"
    WARNING = "warning"  # Completed with warnings
    ERROR = "error"
    TIMEOUT = "timeout"  # Operation timed out (P0 fix)
    SKIPPED = "skipped"  # e.g., no prev_date for comparison

@dataclass
class QAOutcome:
    """Outcome of a QA operation (success/failure semantics).

    Separated from metrics per Martin Fowler's recommendation
    to avoid God Object anti-pattern.
    """
    status: QAStatus
    message: str
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0

    @property
    def is_success(self) -> bool:
        return self.status in (QAStatus.SUCCESS, QAStatus.WARNING)

    @property
    def is_timeout(self) -> bool:
        return self.status == QAStatus.TIMEOUT

# Generic type for metrics
T = TypeVar('T')

@dataclass
class QAResult(Generic[T]):
    """Generic result combining outcome with type-specific metrics.

    Usage:
        result: QAResult[ValidationMetrics] = validator.run()
        if result.outcome.is_success:
            print(f"Valid: {result.metrics.valid_records}")
    """
    outcome: QAOutcome
    metrics: T | None = None
    output_files: list[Path] = field(default_factory=list)

    @property
    def is_success(self) -> bool:
        """Convenience accessor for outcome.is_success."""
        return self.outcome.is_success

    @property
    def status(self) -> QAStatus:
        """Convenience accessor for outcome.status."""
        return self.outcome.status

    @property
    def message(self) -> str:
        """Convenience accessor for outcome.message."""
        return self.outcome.message

    @property
    def warnings(self) -> list[str]:
        """Convenience accessor for outcome.warnings."""
        return self.outcome.warnings

    @property
    def errors(self) -> list[str]:
        """Convenience accessor for outcome.errors."""
        return self.outcome.errors

# Backward compatibility: simple result without generic metrics
SimpleQAResult = QAResult[dict[str, Any]]

class QAError(Exception):
    """Base exception for QA operations."""
    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message)
        self.context = context or {}

class ValidationError(QAError):
    """Schema validation failed."""
    def __init__(self, message: str, record_path: str | None = None,
                 errors: list[str] | None = None, **kwargs):
        super().__init__(message, kwargs)
        self.record_path = record_path
        self.errors = errors or []

class ComparisonError(QAError):
    """Comparison operation failed."""
    pass

class ConfigurationError(QAError):
    """Configuration is invalid or missing."""
    pass

class QATimeoutError(QAError):
    """Operation timed out (P0 fix per Michael Nygard)."""
    def __init__(self, message: str, elapsed_seconds: float, **kwargs):
        super().__init__(message, kwargs)
        self.elapsed_seconds = elapsed_seconds

@runtime_checkable
class QAToolProtocol(Protocol):
    """Protocol for QA tools - ensures testability.

    Updated to include timeout support per expert panel review.
    """

    def run(self, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS, **kwargs) -> QAResult:
        """Execute the QA tool with timeout protection.

        Args:
            timeout_seconds: Maximum execution time (default: 300s/5min)
            **kwargs: Tool-specific options

        Returns:
            QAResult with outcome and metrics

        Raises:
            QATimeoutError: If operation exceeds timeout
        """
        ...

    def validate_inputs(self) -> list[str]:
        """Validate inputs before execution. Returns list of errors."""
        ...

# Helper for implementing timeout in sync code
def run_with_timeout(func, timeout_seconds: int, *args, **kwargs) -> Any:
    """Run a synchronous function with timeout protection.

    Uses threading.Timer for sync code, asyncio.timeout for async.

    Example:
        def _execute():
            # Long-running operation
            return process_large_file()

        result = run_with_timeout(_execute, timeout_seconds=300)
    """
    import threading
    import time

    result = [None]
    exception = [None]
    start_time = time.monotonic()

    def target():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e

    thread = threading.Thread(target=target)
    thread.start()
    thread.join(timeout=timeout_seconds)

    if thread.is_alive():
        # Thread still running - timeout occurred
        elapsed = time.monotonic() - start_time
        raise QATimeoutError(
            f"Operation timed out after {elapsed:.1f}s (limit: {timeout_seconds}s)",
            elapsed_seconds=elapsed
        )

    if exception[0]:
        raise exception[0]

    return result[0]
```

##### core/qa/config.py

```python
"""QA Configuration using Pydantic Settings."""

from __future__ import annotations
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

class QASettings(BaseSettings):
    """Configuration for QA utilities."""

    # Project identification
    project_name: str = Field(..., description="Project identifier (e.g., 'audiobee_bcbs_il')")
    curr_date: str = Field(..., pattern=r"^\d{8}$", description="Current date YYYYMMDD")
    prev_date: str | None = Field(None, pattern=r"^\d{8}$", description="Previous date YYYYMMDD")

    # Paths
    base_dir: Path = Field(Path("."), description="Base directory for project")
    processed_dir: Path | None = Field(None, description="Processed data directory")
    raw_dir: Path | None = Field(None, description="Raw data directory")
    output_dir: Path | None = Field(None, description="QA output directory")

    # Validation settings
    validate_schema: bool = Field(True, description="Enable schema validation")
    schema_path: Path | None = Field(None, description="Custom schema path")

    # Sampling settings
    sample_count: int = Field(10, ge=1, le=100, description="Number of samples")
    archive_format: Literal["7z", "zip", "tar.gz"] = Field("7z", description="Archive format")

    # Comparison settings
    fuzzy_threshold: int = Field(80, ge=0, le=100, description="Fuzzy match threshold")

    # State filtering
    req_states: list[str] = Field(default_factory=list, description="Required states")
    req_states_only: list[str] = Field(default_factory=list, description="States-only mode")

    # Anthem-specific multi-state processing
    anthem_state: str | None = Field(None, description="Anthem state subdirectory")

    # Memory management
    chunk_size: int = Field(10000, ge=100, description="Chunk size for large files")
    max_memory_mb: int = Field(500, ge=100, description="Max memory budget (MB)")

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field("INFO")

    class Config:
        env_prefix = "QA_"
        extra = "ignore"

    @field_validator("curr_date", "prev_date", mode="before")
    @classmethod
    def normalize_date(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return str(v).replace("-", "").replace("/", "")[:8]

    @property
    def curr_processed_dir(self) -> Path:
        """Current date processed directory."""
        if self.processed_dir:
            return self.processed_dir
        return self.base_dir / self.curr_date / "processed"

    @property
    def prev_processed_dir(self) -> Path | None:
        """Previous date processed directory."""
        if self.prev_date is None:
            return None
        if self.processed_dir:
            return self.processed_dir.parent / self.prev_date / "processed"
        return self.base_dir / self.prev_date / "processed"

def load_qa_config(
    project_name: str,
    curr_date: str,
    prev_date: str | None = None,
    **overrides
) -> QASettings:
    """Factory function to create QASettings."""
    return QASettings(
        project_name=project_name,
        curr_date=curr_date,
        prev_date=prev_date,
        **overrides
    )

# Backward compatibility adapter
def load_from_legacy_config(config_module) -> QASettings:
    """Convert legacy config.py module to QASettings."""
    return QASettings(
        project_name=getattr(config_module, "PROJECT_NAME", "unknown"),
        curr_date=getattr(config_module, "CURR_DATE", ""),
        prev_date=getattr(config_module, "PREV_DATE", None),
        base_dir=Path(getattr(config_module, "BASE_DIR", ".")),
        req_states=getattr(config_module, "REQ_STATES", []),
        req_states_only=getattr(config_module, "REQ_STATES_ONLY", []),
        anthem_state=getattr(config_module, "ANTHEM_STATE", None),
    )
```

##### core/data/**init**.py

```python
"""
Reference data loading service for the scraping project.

Provides cached access to shared reference data:
- Output JSON schema for validation
- US state coordinates for geographic coverage
- ZIP to state mappings for address normalization
- Specialty code mappings

Usage:
    from core.data import get_schema, get_state_coordinates, get_zip_to_state

    schema = get_schema()
    coords = get_state_coordinates()
    zip_map = get_zip_to_state()
"""

from .loader import (
    get_schema,
    get_state_coordinates,
    get_zip_to_state,
    get_specialties,
    clear_caches,
)

__all__ = [
    "get_schema",
    "get_state_coordinates",
    "get_zip_to_state",
    "get_specialties",
    "clear_caches",
]
```

##### core/data/loader.py

```python
"""
Cached reference data loading for the scraping project.

This module provides lazy-loaded, cached access to shared reference data.
All data is loaded once on first access and cached for the process lifetime.

Design Decisions:
- @cache decorator for unbounded caching (data is small, ~10MB total)
- Lazy loading to avoid startup cost if data isn't needed
- Separate from qa/ module since data is used by mappers, validators, scrapers
"""

from __future__ import annotations
from functools import cache
from pathlib import Path
from typing import Any

import orjson

try:
    from core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# Reference data directory (same directory as this module)
_DATA_DIR = Path(__file__).parent

@cache
def get_schema() -> dict[str, Any]:
    """Load and cache output JSON schema.

    Returns:
        Parsed JSON Schema for provider output validation.

    Raises:
        FileNotFoundError: If output_json_schema.json doesn't exist.

    Example:
        from core.data import get_schema
        schema = get_schema()
        # Use with fastjsonschema or jsonschema
    """
    schema_path = _DATA_DIR / "output_json_schema.json"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")

    with open(schema_path, "rb") as f:
        schema = orjson.loads(f.read())

    logger.debug("Loaded output schema", path=str(schema_path), size=len(schema))
    return schema

@cache
def get_state_coordinates() -> dict[str, dict]:
    """Load and cache US state coordinates for geographic coverage.

    Returns:
        Dict mapping state codes to coordinate data:
        {"TX": {"lat": [...], "lon": [...], "radius": ...}, ...}

    Raises:
        FileNotFoundError: If us_states_coordinates.json doesn't exist.

    Example:
        from core.data import get_state_coordinates
        coords = get_state_coordinates()
        texas_coords = coords["TX"]
    """
    coord_path = _DATA_DIR / "us_states_coordinates.json"
    if not coord_path.exists():
        raise FileNotFoundError(f"State coordinates not found: {coord_path}")

    with open(coord_path, "rb") as f:
        coords = orjson.loads(f.read())

    logger.debug("Loaded state coordinates", states=len(coords))
    return coords

@cache
def get_zip_to_state() -> dict[str, str]:
    """Load and cache ZIP code to state mapping.

    Returns:
        Dict mapping 5-digit ZIP codes to state abbreviations:
        {"60601": "IL", "75001": "TX", ...}

    Raises:
        FileNotFoundError: If uszips.xlsx doesn't exist.

    Note:
        Uses pandas for Excel reading. Consider migrating to
        parquet format for faster loading if this becomes a bottleneck.

    Example:
        from core.data import get_zip_to_state
        zip_map = get_zip_to_state()
        state = zip_map.get("60601")  # "IL"
    """
    import pandas as pd

    zip_path = _DATA_DIR / "uszips.xlsx"
    if not zip_path.exists():
        raise FileNotFoundError(f"ZIP data not found: {zip_path}")

    df = pd.read_excel(zip_path, dtype={"ZIP": str})
    mapping = dict(zip(df["ZIP"].str.zfill(5), df["STUSPS"]))

    logger.debug("Loaded ZIP mapping", count=len(mapping))
    return mapping

@cache
def get_specialties() -> dict[str, dict]:
    """Load and cache specialty code mappings.

    Returns:
        Dict mapping specialty codes to specialty data:
        {"207Q00000X": {"name": "Family Medicine", ...}, ...}

    Raises:
        FileNotFoundError: If us_specialties.json doesn't exist.
    """
    specialty_path = _DATA_DIR / "us_specialties.json"
    if not specialty_path.exists():
        # Optional file - return empty dict if not present
        logger.debug("Specialties file not found, returning empty mapping")
        return {}

    with open(specialty_path, "rb") as f:
        specialties = orjson.loads(f.read())

    logger.debug("Loaded specialties", count=len(specialties))
    return specialties

def clear_caches() -> None:
    """Clear all cached reference data.

    Use this for testing or when reference data files are updated.
    """
    get_schema.cache_clear()
    get_state_coordinates.cache_clear()
    get_zip_to_state.cache_clear()
    get_specialties.cache_clear()
    logger.info("Cleared all data caches")
```

#### 1.2 Copy Reference Data

```bash
# Copy states_coordinates.json to core/data/
cp output_generator/states_coordinates.json core/data/us_states_coordinates.json
```

### Phase 2: Validator Module (Day 3-4)

#### 2.1 Create core/qa/validator.py

Migrate from `type_check.py` with these improvements:

```python
"""
Schema validation and data collection for provider JSONL files.

Improvements over output_generator/type_check.py:
- Uses core/data/output_json_schema.json (no embedded schema)
- Streaming deduplication with BoundedSet (memory-bounded)
- fastjsonschema for 100x faster validation
- Integrated with core/logging
- Graceful error handling with QAResult
- Timeout protection for long-running operations (P0 fix)
- BoundedSet capacity warnings (P0 fix)
"""

from __future__ import annotations
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import fastjsonschema
import orjson
from tqdm import tqdm

from .base import (
    QAResult, QAOutcome, QAStatus, ValidationError,
    QATimeoutError, run_with_timeout, DEFAULT_TIMEOUT_SECONDS
)
from .config import QASettings
from core.data import get_schema  # Reference data from core/data/

try:
    from core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

try:
    from core.io import BoundedSet
except ImportError:
    # Fallback for standalone use
    BoundedSet = set

# BoundedSet capacity threshold for warnings (P0 fix)
BOUNDEDSET_CAPACITY = 100_000
BOUNDEDSET_WARNING_THRESHOLD = 0.9  # Warn at 90% capacity

@dataclass
class ValidationMetrics:
    """Metrics collected during validation."""
    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    duplicate_records: int = 0
    unique_npis: int = 0
    unique_networks: int = 0
    unique_specialties: int = 0
    unique_states: int = 0
    unique_zips: int = 0

    # Detailed breakdowns
    networks: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    specialties: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    states: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    zips: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # Errors
    validation_errors: list[dict] = field(default_factory=list)

    # P0: Capacity tracking for BoundedSet
    dedup_capacity_reached: bool = False

class Validator:
    """Schema validator with data collection."""

    def __init__(self, settings: QASettings):
        self.settings = settings
        self._schema = get_schema() if settings.validate_schema else None
        self._compiled_validator = None

        if self._schema:
            # Compile schema for 100x faster validation
            try:
                self._compiled_validator = fastjsonschema.compile(self._schema)
                logger.debug("Schema compiled with fastjsonschema")
            except Exception as e:
                logger.warning(f"Failed to compile schema: {e}, falling back to jsonschema")

    def validate_inputs(self) -> list[str]:
        """Validate inputs before execution."""
        errors = []

        jsonl_path = self._get_jsonl_path()
        if not jsonl_path.exists():
            errors.append(f"JSONL file not found: {jsonl_path}")

        return errors

    def run(
        self,
        deduplicate: bool = True,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        **kwargs
    ) -> QAResult[ValidationMetrics]:
        """Execute validation and data collection with timeout protection.

        Args:
            deduplicate: Remove duplicate NPIs (default: True)
            timeout_seconds: Maximum execution time (default: 300s/5min)
            **kwargs: Additional options

        Returns:
            QAResult[ValidationMetrics] with outcome and metrics

        Raises:
            QATimeoutError: If operation exceeds timeout
        """
        start_time = time.monotonic()
        input_errors = self.validate_inputs()

        if input_errors:
            outcome = QAOutcome(
                status=QAStatus.ERROR,
                message="Validation failed: input errors",
                errors=input_errors,
                elapsed_seconds=time.monotonic() - start_time
            )
            return QAResult(outcome=outcome, metrics=None)

        try:
            # P0: Run with timeout protection
            metrics = run_with_timeout(
                self._process_file,
                timeout_seconds,
                deduplicate=deduplicate
            )
            return self._generate_result(metrics, start_time)

        except QATimeoutError as e:
            logger.error(f"Validation timed out after {e.elapsed_seconds:.1f}s")
            outcome = QAOutcome(
                status=QAStatus.TIMEOUT,
                message=f"Validation timed out after {e.elapsed_seconds:.1f}s",
                errors=[str(e)],
                elapsed_seconds=e.elapsed_seconds
            )
            return QAResult(outcome=outcome, metrics=None)

        except Exception as e:
            logger.exception("Validation failed")
            outcome = QAOutcome(
                status=QAStatus.ERROR,
                message=f"Validation failed: {e}",
                errors=[str(e)],
                elapsed_seconds=time.monotonic() - start_time
            )
            return QAResult(outcome=outcome, metrics=None)

    def _get_jsonl_path(self) -> Path:
        """Get path to JSONL file."""
        processed_dir = self.settings.curr_processed_dir
        pattern = f"{self.settings.project_name}-{self.settings.curr_date}.jsonl"

        matches = list(processed_dir.glob(pattern))
        if matches:
            return matches[0]

        # Fallback: any .jsonl file
        matches = list(processed_dir.glob("*.jsonl"))
        return matches[0] if matches else processed_dir / pattern

    def _process_file(self, deduplicate: bool) -> ValidationMetrics:
        """Process JSONL file with streaming."""
        jsonl_path = self._get_jsonl_path()
        metrics = ValidationMetrics()

        # Memory-bounded deduplication with capacity tracking (P0 fix)
        seen_npis = BoundedSet(max_size=BOUNDEDSET_CAPACITY) if deduplicate else None
        capacity_warning_logged = False

        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(tqdm(f, desc="Validating"), 1):
                if not line.strip():
                    continue

                try:
                    record = orjson.loads(line)
                except orjson.JSONDecodeError as e:
                    metrics.invalid_records += 1
                    metrics.validation_errors.append({
                        "line": line_num,
                        "error": f"JSON parse error: {e}"
                    })
                    continue

                metrics.total_records += 1

                # Check for duplicate NPI
                npi = record.get("provider", {}).get("npi")
                if deduplicate and npi:
                    if npi in seen_npis:
                        metrics.duplicate_records += 1
                        continue
                    seen_npis.add(npi)

                    # P0: Log warning when approaching capacity
                    if not capacity_warning_logged and hasattr(seen_npis, '__len__'):
                        current_size = len(seen_npis)
                        if current_size >= BOUNDEDSET_CAPACITY * BOUNDEDSET_WARNING_THRESHOLD:
                            logger.warning(
                                f"BoundedSet at {current_size}/{BOUNDEDSET_CAPACITY} capacity "
                                f"({current_size/BOUNDEDSET_CAPACITY*100:.1f}%). "
                                "LRU eviction may cause false negatives for duplicates."
                            )
                            capacity_warning_logged = True
                            metrics.dedup_capacity_reached = True

                # Schema validation
                if self.settings.validate_schema and self._compiled_validator:
                    try:
                        self._compiled_validator(record)
                        metrics.valid_records += 1
                    except fastjsonschema.JsonSchemaValueException as e:
                        metrics.invalid_records += 1
                        if len(metrics.validation_errors) < 100:  # Limit error collection
                            metrics.validation_errors.append({
                                "line": line_num,
                                "npi": npi,
                                "error": str(e.message)
                            })
                else:
                    metrics.valid_records += 1

                # Collect statistics
                self._collect_stats(record, metrics)

        # Finalize counts
        metrics.unique_npis = len(seen_npis) if seen_npis else metrics.valid_records
        metrics.unique_networks = len(metrics.networks)
        metrics.unique_specialties = len(metrics.specialties)
        metrics.unique_states = len(metrics.states)
        metrics.unique_zips = len(metrics.zips)

        return metrics

    def _collect_stats(self, record: dict, metrics: ValidationMetrics) -> None:
        """Collect statistics from a record."""
        # Networks
        for network in record.get("networks", []):
            network_name = network.get("network_name", "Unknown")
            metrics.networks[network_name] += 1

        # Specialties
        for specialty in record.get("specialties", []):
            spec_name = specialty.get("specialty_name", "Unknown")
            metrics.specialties[spec_name] += 1

        # Addresses (states and zips)
        for address in record.get("addresses", []):
            state = address.get("state")
            zip_code = address.get("zip", "")[:5]

            if state:
                metrics.states[state] += 1
            if zip_code:
                metrics.zips[zip_code] += 1

    def _generate_result(
        self,
        metrics: ValidationMetrics,
        start_time: float
    ) -> QAResult[ValidationMetrics]:
        """Generate QAResult from metrics (P0: uses new structure)."""
        status = QAStatus.SUCCESS
        warnings = []

        if metrics.invalid_records > 0:
            status = QAStatus.WARNING
            warnings.append(f"{metrics.invalid_records} records failed validation")

        if metrics.duplicate_records > 0:
            warnings.append(f"{metrics.duplicate_records} duplicate NPIs removed")

        # P0: Warn about BoundedSet capacity
        if metrics.dedup_capacity_reached:
            warnings.append(
                f"Deduplication capacity ({BOUNDEDSET_CAPACITY}) reached. "
                "Some duplicates may not have been detected."
            )

        outcome = QAOutcome(
            status=status,
            message=f"Validated {metrics.valid_records}/{metrics.total_records} records",
            warnings=warnings,
            errors=[e["error"] for e in metrics.validation_errors[:10]],
            elapsed_seconds=time.monotonic() - start_time
        )

        return QAResult(outcome=outcome, metrics=metrics)

# Convenience function
def validate(
    jsonl_path: Path | str,
    schema_path: Path | str | None = None,
    deduplicate: bool = True,
    **kwargs
) -> QAResult:
    """Validate a JSONL file against the output schema.

    Args:
        jsonl_path: Path to JSONL file
        schema_path: Optional custom schema path
        deduplicate: Remove duplicate NPIs (default: True)
        **kwargs: Additional settings passed to QASettings

    Returns:
        QAResult with validation metrics

    Example:
        result = validate("providers.jsonl")
        if result.is_success:
            print(f"Valid: {result.metrics['valid_records']}")
        else:
            for error in result.errors:
                print(f"Error: {error}")
    """
    jsonl_path = Path(jsonl_path)

    settings = QASettings(
        project_name=jsonl_path.stem,
        curr_date="00000000",  # Will be ignored
        validate_schema=schema_path is not None or True,
        schema_path=Path(schema_path) if schema_path else None,
        **kwargs
    )

    validator = Validator(settings)
    return validator.run(deduplicate=deduplicate)
```

### Phase 3: Comparison Module (Day 5-6)

#### 3.1 Create core/qa/comparison.py

```python
"""
Cross-run comparison analysis for detecting changes between scraper runs.

Improvements over output_generator/comparison_creator.py:
- Single-pass file reading (no double reads)
- Polars for 10x faster DataFrame operations
- Graceful handling of missing prev_date (first run mode)
- Memory-efficient chunked processing
- Integrated with core/logging
- Timeout protection for long-running operations (P0 fix)
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import polars as pl
from tqdm import tqdm

from .base import (
    QAResult, QAOutcome, QAStatus, ComparisonError,
    QATimeoutError, run_with_timeout, DEFAULT_TIMEOUT_SECONDS
)
from .config import QASettings

try:
    from core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

@dataclass
class ComparisonMetrics:
    """Metrics from comparison analysis."""
    curr_total: int = 0
    prev_total: int = 0
    added: int = 0
    removed: int = 0
    unchanged: int = 0
    changed: int = 0

    # Per-network/specialty breakdowns
    network_changes: dict[str, dict] = field(default_factory=dict)
    specialty_changes: dict[str, dict] = field(default_factory=dict)

class Comparator:
    """Cross-run comparison with memory-efficient processing."""

    def __init__(self, settings: QASettings):
        self.settings = settings

    def validate_inputs(self) -> list[str]:
        """Validate inputs before execution."""
        errors = []

        curr_path = self._get_comparison_file(is_current=True)
        if curr_path and not curr_path.exists():
            errors.append(f"Current comparison file not found: {curr_path}")

        # Previous is optional - first run mode
        prev_path = self._get_comparison_file(is_current=False)
        if prev_path is None:
            logger.info("No previous date specified - running in first-run mode")
        elif not prev_path.exists():
            logger.warning(f"Previous comparison file not found: {prev_path}")

        return errors

    def run(
        self,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        **kwargs
    ) -> QAResult[ComparisonMetrics]:
        """Execute comparison analysis with timeout protection.

        Args:
            timeout_seconds: Maximum execution time (default: 300s/5min)
            **kwargs: Additional options

        Returns:
            QAResult[ComparisonMetrics] with outcome and metrics
        """
        start_time = time.monotonic()
        input_errors = self.validate_inputs()

        if input_errors:
            outcome = QAOutcome(
                status=QAStatus.ERROR,
                message="Comparison failed: input errors",
                errors=input_errors,
                elapsed_seconds=time.monotonic() - start_time
            )
            return QAResult(outcome=outcome, metrics=None)

        try:
            prev_path = self._get_comparison_file(is_current=False)

            if prev_path is None or not prev_path.exists():
                return self._first_run_result(start_time)

            # P0: Run with timeout protection
            metrics = run_with_timeout(
                self._compare_files,
                timeout_seconds
            )
            return self._generate_result(metrics, start_time)

        except QATimeoutError as e:
            logger.error(f"Comparison timed out after {e.elapsed_seconds:.1f}s")
            outcome = QAOutcome(
                status=QAStatus.TIMEOUT,
                message=f"Comparison timed out after {e.elapsed_seconds:.1f}s",
                errors=[str(e)],
                elapsed_seconds=e.elapsed_seconds
            )
            return QAResult(outcome=outcome, metrics=None)

        except Exception as e:
            logger.exception("Comparison failed")
            outcome = QAOutcome(
                status=QAStatus.ERROR,
                message=f"Comparison failed: {e}",
                errors=[str(e)],
                elapsed_seconds=time.monotonic() - start_time
            )
            return QAResult(outcome=outcome, metrics=None)

    def _get_comparison_file(self, is_current: bool) -> Path | None:
        """Get path to comparison Excel file."""
        if is_current:
            base_dir = self.settings.curr_processed_dir
        else:
            base_dir = self.settings.prev_processed_dir
            if base_dir is None:
                return None

        return base_dir / "debug_specialty_network.xlsx"

    def _first_run_result(self, start_time: float) -> QAResult[ComparisonMetrics]:
        """Generate result for first run (no previous data)."""
        outcome = QAOutcome(
            status=QAStatus.SKIPPED,
            message="First run - no previous data for comparison",
            warnings=["Comparison skipped: no previous date data"],
            elapsed_seconds=time.monotonic() - start_time
        )
        # Return empty metrics for first run
        metrics = ComparisonMetrics()
        return QAResult(outcome=outcome, metrics=metrics)

    def _compare_files(self) -> ComparisonMetrics:
        """Compare current and previous Excel files using Polars."""
        curr_path = self._get_comparison_file(is_current=True)
        prev_path = self._get_comparison_file(is_current=False)

        logger.info(f"Comparing {prev_path} → {curr_path}")

        # Read with Polars for speed
        curr_df = pl.read_excel(curr_path, sheet_name="Specialty Zip Code Network")
        prev_df = pl.read_excel(prev_path, sheet_name="Specialty Zip Code Network")

        metrics = ComparisonMetrics()
        metrics.curr_total = len(curr_df)
        metrics.prev_total = len(prev_df)

        # Merge on key columns
        merged = curr_df.join(
            prev_df,
            on=["Specialty", "Zip Code"],
            how="outer",
            suffix="_prev"
        )

        # Calculate changes per network
        network_cols = [c for c in curr_df.columns if c not in ["Specialty", "Zip Code"]]

        for network in network_cols:
            curr_col = network
            prev_col = f"{network}_prev"

            if prev_col not in merged.columns:
                continue

            changes = merged.select([
                curr_col,
                prev_col,
                (pl.col(curr_col).fill_null(0) - pl.col(prev_col).fill_null(0)).alias("diff")
            ])

            added = changes.filter(pl.col("diff") > 0)["diff"].sum()
            removed = abs(changes.filter(pl.col("diff") < 0)["diff"].sum())

            metrics.network_changes[network] = {
                "added": int(added or 0),
                "removed": int(removed or 0),
                "net_change": int((added or 0) - (removed or 0))
            }

            metrics.added += int(added or 0)
            metrics.removed += int(removed or 0)

        return metrics

    def _generate_result(
        self,
        metrics: ComparisonMetrics,
        start_time: float
    ) -> QAResult[ComparisonMetrics]:
        """Generate QAResult from comparison metrics (P0: uses new structure)."""
        status = QAStatus.SUCCESS
        warnings = []

        # Check for significant drops (>10% decrease)
        for network, changes in metrics.network_changes.items():
            if changes["removed"] > metrics.prev_total * 0.1:
                status = QAStatus.WARNING
                warnings.append(f"Large drop in {network}: {changes['removed']} removed")

        outcome = QAOutcome(
            status=status,
            message=f"Compared {metrics.curr_total} current vs {metrics.prev_total} previous records",
            warnings=warnings,
            elapsed_seconds=time.monotonic() - start_time
        )

        return QAResult(outcome=outcome, metrics=metrics)

# Convenience function
def compare(
    curr_path: Path | str,
    prev_path: Path | str | None = None,
    output_path: Path | str | None = None,
    **kwargs
) -> QAResult:
    """Compare two scraper runs for changes.

    Args:
        curr_path: Path to current run's debug_specialty_network.xlsx
        prev_path: Path to previous run's debug_specialty_network.xlsx
        output_path: Path for comparison output Excel
        **kwargs: Additional settings

    Returns:
        QAResult with comparison metrics
    """
    curr_path = Path(curr_path)

    settings = QASettings(
        project_name=curr_path.stem,
        curr_date="00000000",
        prev_date="00000000" if prev_path else None,
        **kwargs
    )

    comparator = Comparator(settings)
    return comparator.run()
```

### Phase 4: Sampler & Reporter (Day 7-8)

#### 4.1 Create core/qa/sampler.py

```python
"""
Random sampling with reservoir algorithm for memory efficiency.

Improvements over output_generator/sample_generator.py:
- Reservoir sampling (no full file load)
- Configurable sample size
- Multiple archive format support
- Timeout protection for long-running operations (P0 fix)
"""

from __future__ import annotations
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import orjson

from .base import (
    QAResult, QAOutcome, QAStatus,
    QATimeoutError, run_with_timeout, DEFAULT_TIMEOUT_SECONDS
)
from .config import QASettings

try:
    from core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

@dataclass
class SamplingMetrics:
    """Metrics from sampling operation."""
    sample_count: int = 0
    total_records: int = 0
    archive_size_bytes: int = 0
    archive_format: str = ""

class Sampler:
    """Random sampling with reservoir algorithm."""

    def __init__(self, settings: QASettings):
        self.settings = settings

    def run(
        self,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        **kwargs
    ) -> QAResult[SamplingMetrics]:
        """Generate random samples with timeout protection.

        Args:
            timeout_seconds: Maximum execution time (default: 300s/5min)
            **kwargs: Additional options

        Returns:
            QAResult[SamplingMetrics] with outcome and metrics
        """
        start_time = time.monotonic()

        try:
            # P0: Run with timeout protection
            samples, total_records = run_with_timeout(
                self._reservoir_sample,
                timeout_seconds
            )
            output_files = self._write_samples(samples)
            archive_path = self._create_archive(output_files)

            metrics = SamplingMetrics(
                sample_count=len(samples),
                total_records=total_records,
                archive_size_bytes=archive_path.stat().st_size if archive_path.exists() else 0,
                archive_format=self.settings.archive_format
            )

            outcome = QAOutcome(
                status=QAStatus.SUCCESS,
                message=f"Generated {len(samples)} samples from {total_records} records",
                elapsed_seconds=time.monotonic() - start_time
            )

            return QAResult(
                outcome=outcome,
                metrics=metrics,
                output_files=output_files + [archive_path]
            )

        except QATimeoutError as e:
            logger.error(f"Sampling timed out after {e.elapsed_seconds:.1f}s")
            outcome = QAOutcome(
                status=QAStatus.TIMEOUT,
                message=f"Sampling timed out after {e.elapsed_seconds:.1f}s",
                errors=[str(e)],
                elapsed_seconds=e.elapsed_seconds
            )
            return QAResult(outcome=outcome, metrics=None)

        except Exception as e:
            logger.exception("Sampling failed")
            outcome = QAOutcome(
                status=QAStatus.ERROR,
                message=f"Sampling failed: {e}",
                errors=[str(e)],
                elapsed_seconds=time.monotonic() - start_time
            )
            return QAResult(outcome=outcome, metrics=None)

    def _reservoir_sample(self) -> tuple[list[dict], int]:
        """Reservoir sampling - O(n) time, O(k) space.

        Returns:
            Tuple of (sampled records, total records count)
        """
        k = self.settings.sample_count
        reservoir = []
        total_records = 0

        jsonl_path = self._get_jsonl_path()

        with open(jsonl_path, "r") as f:
            for i, line in enumerate(f):
                if not line.strip():
                    continue

                total_records += 1
                record = orjson.loads(line)

                if i < k:
                    reservoir.append(record)
                else:
                    j = random.randint(0, i)
                    if j < k:
                        reservoir[j] = record

        return reservoir, total_records

    def _get_jsonl_path(self) -> Path:
        """Get JSONL file path."""
        processed_dir = self.settings.curr_processed_dir
        pattern = f"{self.settings.project_name}*.jsonl"
        matches = list(processed_dir.glob(pattern))
        return matches[0] if matches else processed_dir / "providers.jsonl"

    def _write_samples(self, samples: list[dict]) -> list[Path]:
        """Write individual sample files."""
        output_dir = self.settings.curr_processed_dir
        output_files = []

        for i, record in enumerate(samples):
            output_path = output_dir / f"{self.settings.project_name}-sample-{self.settings.curr_date}-{i}.json"
            with open(output_path, "wb") as f:
                f.write(orjson.dumps(record, option=orjson.OPT_INDENT_2))
            output_files.append(output_path)

        return output_files

    def _create_archive(self, files: list[Path]) -> Path:
        """Create archive from sample files."""
        output_dir = self.settings.curr_processed_dir
        archive_name = f"{self.settings.curr_date}.{self.settings.archive_format}"
        archive_path = output_dir / archive_name

        if self.settings.archive_format == "7z":
            import py7zr
            with py7zr.SevenZipFile(archive_path, "w") as archive:
                for f in files:
                    archive.write(f, f.name)
        elif self.settings.archive_format == "zip":
            import zipfile
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
                for f in files:
                    archive.write(f, f.name)
        elif self.settings.archive_format == "tar.gz":
            import tarfile
            with tarfile.open(archive_path, "w:gz") as archive:
                for f in files:
                    archive.add(f, f.name)

        logger.info(f"Created archive: {archive_path}")
        return archive_path

# Convenience function
def sample(
    jsonl_path: Path | str,
    output_dir: Path | str | None = None,
    count: int = 10,
    archive_format: str = "7z",
    **kwargs
) -> QAResult:
    """Generate random samples from a JSONL file."""
    jsonl_path = Path(jsonl_path)

    settings = QASettings(
        project_name=jsonl_path.stem,
        curr_date="00000000",
        sample_count=count,
        archive_format=archive_format,
        **kwargs
    )

    sampler = Sampler(settings)
    return sampler.run()
```

#### 4.2 Create core/qa/reporter.py

```python
"""
Excel report generation for state-level statistics.

Improvements over output_generator/report_generator.py:
- Single-pass JSONL processing
- xlsxwriter streaming mode for large files
- Cached reference data loading
- Timeout protection for long-running operations (P0 fix)
"""

from __future__ import annotations
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import orjson
import xlsxwriter
from tqdm import tqdm

from .base import (
    QAResult, QAOutcome, QAStatus,
    QATimeoutError, run_with_timeout, DEFAULT_TIMEOUT_SECONDS
)
from .config import QASettings
from core.data import get_zip_to_state  # Reference data from core/data/

try:
    from core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

@dataclass
class StateStats:
    """Statistics per state."""
    curr_count: int = 0
    prev_count: int = 0
    in_scope: bool = False
    npis: set = field(default_factory=set)
    prev_npis: set = field(default_factory=set)

@dataclass
class ReportMetrics:
    """Metrics from report generation."""
    states_count: int = 0
    total_providers: int = 0
    in_scope_states: int = 0
    total_change: int = 0
    report_size_bytes: int = 0

class Reporter:
    """State-level statistics report generator."""

    def __init__(self, settings: QASettings):
        self.settings = settings
        self._zip_to_state = get_zip_to_state()

    def run(
        self,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        **kwargs
    ) -> QAResult[ReportMetrics]:
        """Generate state-level report with timeout protection.

        Args:
            timeout_seconds: Maximum execution time (default: 300s/5min)
            **kwargs: Additional options

        Returns:
            QAResult[ReportMetrics] with outcome and metrics
        """
        start_time = time.monotonic()

        try:
            # P0: Run with timeout protection
            stats = run_with_timeout(
                self._collect_stats,
                timeout_seconds
            )
            output_path = self._write_excel(stats)

            metrics = ReportMetrics(
                states_count=len(stats),
                total_providers=sum(s.curr_count for s in stats.values()),
                in_scope_states=sum(1 for s in stats.values() if s.in_scope),
                total_change=sum(s.curr_count - s.prev_count for s in stats.values()),
                report_size_bytes=output_path.stat().st_size if output_path.exists() else 0
            )

            outcome = QAOutcome(
                status=QAStatus.SUCCESS,
                message=f"Generated report with {len(stats)} states",
                elapsed_seconds=time.monotonic() - start_time
            )

            return QAResult(
                outcome=outcome,
                metrics=metrics,
                output_files=[output_path]
            )

        except QATimeoutError as e:
            logger.error(f"Report generation timed out after {e.elapsed_seconds:.1f}s")
            outcome = QAOutcome(
                status=QAStatus.TIMEOUT,
                message=f"Report generation timed out after {e.elapsed_seconds:.1f}s",
                errors=[str(e)],
                elapsed_seconds=e.elapsed_seconds
            )
            return QAResult(outcome=outcome, metrics=None)

        except Exception as e:
            logger.exception("Report generation failed")
            outcome = QAOutcome(
                status=QAStatus.ERROR,
                message=f"Report failed: {e}",
                errors=[str(e)],
                elapsed_seconds=time.monotonic() - start_time
            )
            return QAResult(outcome=outcome, metrics=None)

    def _collect_stats(self) -> dict[str, StateStats]:
        """Collect statistics from JSONL files."""
        stats: dict[str, StateStats] = defaultdict(StateStats)

        # Mark in-scope states
        for state in self.settings.req_states:
            stats[state].in_scope = True

        # Process current file
        curr_path = self._get_jsonl_path(is_current=True)
        if curr_path.exists():
            self._process_jsonl(curr_path, stats, is_current=True)

        # Process previous file
        prev_path = self._get_jsonl_path(is_current=False)
        if prev_path and prev_path.exists():
            self._process_jsonl(prev_path, stats, is_current=False)

        return stats

    def _process_jsonl(self, path: Path, stats: dict[str, StateStats], is_current: bool):
        """Process a JSONL file in single pass."""
        with open(path, "r") as f:
            for line in tqdm(f, desc=f"Processing {path.name}"):
                if not line.strip():
                    continue

                record = orjson.loads(line)
                npi = record.get("provider", {}).get("npi")

                # Extract states from addresses
                for address in record.get("addresses", []):
                    state = address.get("state")
                    if not state:
                        # Try ZIP lookup
                        zip_code = address.get("zip", "")[:5]
                        state = self._zip_to_state.get(zip_code)

                    if state:
                        if is_current:
                            stats[state].curr_count += 1
                            if npi:
                                stats[state].npis.add(npi)
                        else:
                            stats[state].prev_count += 1
                            if npi:
                                stats[state].prev_npis.add(npi)

    def _get_jsonl_path(self, is_current: bool) -> Path | None:
        """Get JSONL file path."""
        if is_current:
            base_dir = self.settings.curr_processed_dir
        else:
            base_dir = self.settings.prev_processed_dir
            if base_dir is None:
                return None

        pattern = f"{self.settings.project_name}*.jsonl"
        matches = list(base_dir.glob(pattern))
        return matches[0] if matches else None

    def _write_excel(self, stats: dict[str, StateStats]) -> Path:
        """Write statistics to Excel using streaming mode."""
        output_dir = self.settings.curr_processed_dir
        output_path = output_dir / f"{self.settings.project_name}-{self.settings.curr_date}-state_counts.xlsx"

        workbook = xlsxwriter.Workbook(str(output_path), {'constant_memory': True})
        worksheet = workbook.add_worksheet("State Counts")

        # Header
        headers = ["State", "In Scope", "Current Count", "Previous Count",
                   "Change", "True Drops (NPIs)", "True Adds (NPIs)"]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)

        # Data rows
        row = 1
        for state, state_stats in sorted(stats.items()):
            true_drops = len(state_stats.prev_npis - state_stats.npis)
            true_adds = len(state_stats.npis - state_stats.prev_npis)

            worksheet.write(row, 0, state)
            worksheet.write(row, 1, "Yes" if state_stats.in_scope else "No")
            worksheet.write(row, 2, state_stats.curr_count)
            worksheet.write(row, 3, state_stats.prev_count)
            worksheet.write(row, 4, state_stats.curr_count - state_stats.prev_count)
            worksheet.write(row, 5, true_drops)
            worksheet.write(row, 6, true_adds)
            row += 1

        workbook.close()
        logger.info(f"Wrote report: {output_path}")
        return output_path

# Convenience function
def report(
    project_name: str,
    curr_date: str,
    prev_date: str | None = None,
    states: list[str] | None = None,
    **kwargs
) -> QAResult:
    """Generate state-level report."""
    settings = QASettings(
        project_name=project_name,
        curr_date=curr_date,
        prev_date=prev_date,
        req_states=states or [],
        **kwargs
    )

    reporter = Reporter(settings)
    return reporter.run()
```

### Phase 5: Statistics & CLI (Day 9-10)

#### 5.1 Create core/qa/statistics.py

Merge `get_per_STATE_counts.py` and `get_per_state_scraped.py`.

#### 5.2 Create core/qa/cli.py

```python
"""
CLI for QA utilities.

Usage:
    python -m core.qa validate providers.jsonl
    python -m core.qa compare --curr 20251227 --prev 20251126
    python -m core.qa sample providers.jsonl --count 20
    python -m core.qa report project_name --curr 20251227
"""

import typer
from pathlib import Path

app = typer.Typer(help="QA utilities for provider data validation")

@app.command()
def validate(
    jsonl_path: Path = typer.Argument(..., help="Path to JSONL file"),
    schema: Path = typer.Option(None, help="Custom schema path"),
    no_dedup: bool = typer.Option(False, help="Skip deduplication"),
):
    """Validate JSONL file against output schema."""
    from .validator import validate as run_validate

    result = run_validate(jsonl_path, schema_path=schema, deduplicate=not no_dedup)

    if result.is_success:
        typer.secho(f"✓ {result.message}", fg="green")
        typer.echo(f"  Valid: {result.metrics['valid_records']}")
        typer.echo(f"  States: {result.metrics['unique_states']}")
    else:
        typer.secho(f"✗ {result.message}", fg="red")
        for error in result.errors[:5]:
            typer.echo(f"  - {error}")

    raise typer.Exit(0 if result.is_success else 1)

@app.command()
def compare(
    curr: str = typer.Option(..., help="Current date YYYYMMDD"),
    prev: str = typer.Option(None, help="Previous date YYYYMMDD"),
    project: str = typer.Option(".", help="Project directory"),
):
    """Compare runs for changes."""
    from .comparison import Comparator
    from .config import QASettings

    settings = QASettings(
        project_name=Path(project).name,
        curr_date=curr,
        prev_date=prev,
        base_dir=Path(project)
    )

    result = Comparator(settings).run()

    if result.status.value == "skipped":
        typer.secho(f"⊘ {result.message}", fg="yellow")
    elif result.is_success:
        typer.secho(f"✓ {result.message}", fg="green")
        typer.echo(f"  Added: {result.metrics.get('added', 0)}")
        typer.echo(f"  Removed: {result.metrics.get('removed', 0)}")
    else:
        typer.secho(f"✗ {result.message}", fg="red")

    raise typer.Exit(0 if result.is_success else 1)

@app.command()
def sample(
    jsonl_path: Path = typer.Argument(..., help="Path to JSONL file"),
    count: int = typer.Option(10, help="Number of samples"),
    format: str = typer.Option("7z", help="Archive format (7z, zip, tar.gz)"),
):
    """Generate random samples."""
    from .sampler import sample as run_sample

    result = run_sample(jsonl_path, count=count, archive_format=format)

    if result.is_success:
        typer.secho(f"✓ {result.message}", fg="green")
        for path in result.output_files:
            typer.echo(f"  Created: {path}")
    else:
        typer.secho(f"✗ {result.message}", fg="red")

    raise typer.Exit(0 if result.is_success else 1)

@app.command()
def report(
    project: str = typer.Argument(..., help="Project name"),
    curr: str = typer.Option(..., help="Current date YYYYMMDD"),
    prev: str = typer.Option(None, help="Previous date YYYYMMDD"),
    states: str = typer.Option(None, help="Comma-separated state codes"),
):
    """Generate state-level report."""
    from .reporter import report as run_report

    state_list = states.split(",") if states else []
    result = run_report(project, curr, prev, state_list)

    if result.is_success:
        typer.secho(f"✓ {result.message}", fg="green")
        for path in result.output_files:
            typer.echo(f"  Created: {path}")
    else:
        typer.secho(f"✗ {result.message}", fg="red")

    raise typer.Exit(0 if result.is_success else 1)

if __name__ == "__main__":
    app()
```

### Phase 6: Backward Compatibility & Testing (Day 11-12)

#### 6.1 Create Backward Compatibility Wrapper

Update `output_generator/__init__.py`:

```python
"""
DEPRECATED: Use core.qa instead.

This module provides backward compatibility for existing code.
All functionality has been migrated to core/qa/.

Migration guide:
    # Old
    from output_generator import type_checker
    type_checker(project_name, curr_date, processed_dir)

    # New
    from core.qa import validate
    result = validate(processed_dir / f"{project_name}-{curr_date}.jsonl")
"""

import warnings
from pathlib import Path

def _deprecated(old_name: str, new_import: str):
    warnings.warn(
        f"'{old_name}' is deprecated and will be removed in v4.0. "
        f"Use '{new_import}' instead.",
        DeprecationWarning,
        stacklevel=3
    )

def type_checker(project_name: str, curr_date: str, processed_dir: str, **kwargs):
    """DEPRECATED: Use core.qa.validate instead."""
    _deprecated("type_checker", "from core.qa import validate")

    from core.qa import validate
    from core.qa.config import QASettings

    jsonl_path = Path(processed_dir) / f"{project_name}-{curr_date}.jsonl"
    result = validate(jsonl_path, **kwargs)

    # Return in legacy format for compatibility
    return result.is_success

def sample_generator(project_name: str, curr_date: str, processed_dir: str, **kwargs):
    """DEPRECATED: Use core.qa.sample instead."""
    _deprecated("sample_generator", "from core.qa import sample")

    from core.qa import sample

    jsonl_path = Path(processed_dir) / f"{project_name}-{curr_date}.jsonl"
    result = sample(jsonl_path, **kwargs)
    return result.is_success

def comparison_creator(project_name: str, curr_date: str, processed_dir: str,
                       prev_date: str, prev_processed_dir: str, **kwargs):
    """DEPRECATED: Use core.qa.compare instead."""
    _deprecated("comparison_creator", "from core.qa import compare")

    from core.qa import compare

    curr_path = Path(processed_dir) / "debug_specialty_network.xlsx"
    prev_path = Path(prev_processed_dir) / "debug_specialty_network.xlsx"
    result = compare(curr_path, prev_path, **kwargs)
    return result.is_success

def report_generator(project_name: str, curr_date: str, prev_date: str,
                     req_states: list, req_states_only: list, **kwargs):
    """DEPRECATED: Use core.qa.report instead."""
    _deprecated("report_generator", "from core.qa import report")

    from core.qa import report

    result = report(project_name, curr_date, prev_date, req_states, **kwargs)
    return result.is_success

def compress_folder_to_7z(input_dir: str, output_path: str):
    """DEPRECATED: Use core.qa.sampler archive functionality."""
    _deprecated("compress_folder_to_7z", "core.qa.sampler")

    import py7zr
    with py7zr.SevenZipFile(output_path, "w") as archive:
        archive.writeall(input_dir)
    return True

# Export all for backward compatibility
__all__ = [
    "type_checker",
    "sample_generator",
    "comparison_creator",
    "report_generator",
    "compress_folder_to_7z",
]
```

#### 6.2 Create Test Suite

Create `core/tests/test_qa/`:

```
core/tests/test_qa/
├── __init__.py
├── conftest.py           # Shared fixtures
├── test_validator.py     # Validator tests
├── test_comparison.py    # Comparison tests
├── test_sampler.py       # Sampler tests
├── test_reporter.py      # Reporter tests
└── fixtures/
    ├── sample_providers.jsonl
    ├── sample_schema.json
    └── sample_specialty_network.xlsx
```

---

## Dependencies Update

Add to `core/pyproject.toml`:

```toml
[project]
dependencies = [
    # Existing
    "orjson>=3.9.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "loguru>=0.7.0",

    # New for QA module
    "pandas>=2.0.0",
    "polars>=0.20.0",
    "openpyxl>=3.1.0",
    "xlsxwriter>=3.1.0",
    "fastjsonschema>=2.19.0",
    "py7zr>=0.21.0",
    "rapidfuzz>=3.5.0",  # MIT replacement for fuzzywuzzy
    "tqdm>=4.66.0",
    "typer>=0.9.0",
]

[project.optional-dependencies]
qa = [
    "pandas>=2.0.0",
    "polars>=0.20.0",
    "openpyxl>=3.1.0",
    "xlsxwriter>=3.1.0",
    "fastjsonschema>=2.19.0",
    "py7zr>=0.21.0",
    "rapidfuzz>=3.5.0",
    "tqdm>=4.66.0",
    "typer>=0.9.0",
]

[project.scripts]
core-qa = "core.qa.cli:app"
```

---

## Rollout Timeline

| Phase                   | Duration  | Deliverables                                           |
| ----------------------- | --------- | ------------------------------------------------------ |
| **1: Foundation**       | Day 1-2   | Module structure, base types, config, data loader      |
| **2: Validator**        | Day 3-4   | Schema validation with fastjsonschema, streaming dedup |
| **3: Comparison**       | Day 5-6   | Cross-run diff with Polars, first-run mode             |
| **4: Sampler/Reporter** | Day 7-8   | Reservoir sampling, streaming Excel                    |
| **5: Statistics/CLI**   | Day 9-10  | State statistics, Typer CLI                            |
| **6: Compat/Testing**   | Day 11-12 | Backward compat wrapper, test suite                    |
| **7: Pilot**            | Day 13-14 | Test with 3 projects, validate outputs                 |
| **8: Documentation**    | Day 15    | Update CLAUDE.md, README, migration guide              |

---

## Success Criteria

- [ ] All 6 utilities migrated to core/qa/
- [ ] Performance: Validation 10x faster (fastjsonschema vs jsonschema)
- [ ] Performance: Comparison 5x faster (Polars vs pandas)
- [ ] Memory: Handle 500MB JSONL files without OOM
- [ ] Test coverage: >80% for core logic
- [ ] Backward compatibility: All 86 projects work with wrapper
- [ ] Documentation: Complete usage guide and migration instructions

---

## Risks & Mitigations

| Risk                                | Impact | Mitigation                                        |
| ----------------------------------- | ------ | ------------------------------------------------- |
| Breaking changes in 86 projects     | High   | Backward compat wrapper with deprecation warnings |
| Performance regression              | Medium | Benchmark before/after with real data             |
| Schema drift                        | Medium | Single source of truth in core/data/              |
| External dependencies (healthsparq) | Low    | Keep API coverage tools separate                  |

---

## Expert Panel Review - P0 Fixes Applied

Based on review by 5 domain experts, the following P0 (critical) fixes have been applied to this plan:

### 1. Split QAResult into QAOutcome + QAResult[T] (Martin Fowler)

**Issue**: QAResult was a "God Object" combining success/failure semantics with metrics collection.

**Fix**:

- Created `QAOutcome` for status, message, warnings, errors, elapsed_seconds
- Made `QAResult[T]` generic with `outcome: QAOutcome` and `metrics: T | None`
- Each module has typed metrics: `ValidationMetrics`, `ComparisonMetrics`, `SamplingMetrics`, `ReportMetrics`

**Impact**: Better separation of concerns, clearer API, type-safe metrics access.

### 2. Added Timeout Mechanism (Michael Nygard)

**Issue**: No timeout protection for long-running operations could cause indefinite hangs.

**Fix**:

- Added `DEFAULT_TIMEOUT_SECONDS = 300` (5 minutes)
- Added `run_with_timeout()` helper using threading for sync code
- Added `QATimeoutError` exception
- Added `QAStatus.TIMEOUT` enum value
- All `.run()` methods now accept `timeout_seconds` parameter

**Impact**: Operations fail gracefully with clear error messages after timeout.

### 3. BoundedSet Capacity Warning (Michael Nygard)

**Issue**: BoundedSet with 100k capacity uses LRU eviction which could cause false negatives for duplicates without any warning.

**Fix**:

- Added `BOUNDEDSET_WARNING_THRESHOLD = 0.9` (warn at 90% capacity)
- Added `dedup_capacity_reached: bool` to `ValidationMetrics`
- Log warning when approaching capacity limit
- Include capacity warning in result warnings

**Impact**: Users are alerted when deduplication accuracy may be compromised.

### P1 Issues (Pending for Future Work)

| Issue                                | Owner          | Status  |
| ------------------------------------ | -------------- | ------- |
| No concrete test cases with fixtures | Lisa Crispin   | Pending |
| Missing BDD scenarios for edge cases | Gojko Adzic    | Pending |
| No checkpoint/resume for large files | Michael Nygard | Pending |
| Excel 1M row limit handling          | Lisa Crispin   | Pending |

---

## References

- Current files: `output_generator/type_check.py:1-666`, `comparison_creator.py:1-740`
- Target location: `core/qa/`
- Schema: `core/data/output_json_schema.json`
- Design patterns: `core/io/base.py` (Protocol), `core/config/base.py` (Settings)
- Expert panel review: Karl Wiegers, Martin Fowler, Michael Nygard, Lisa Crispin, Gojko Adzic

# Shared Utilities Implementation Plan

## Objective
Implement centralized shared utilities for the 95+ scraper projects based on recommendations from `docs/IMPROVEMENTS.md`.

## Current State
- **No `shared/` directory exists** - utilities scattered across projects
- **No `tools/` directory** - mentioned in CLAUDE.md but doesn't exist
- **Existing patterns**: `print()` logging, `tenacity` retries (inconsistent), manual metrics
- **Existing shared code**: `output_generator/` has validation/reporting utilities

## Target Shared Utilities (from IMPROVEMENTS.md)

| Priority | Utility | File | Purpose |
|----------|---------|------|---------|
| P0 | Logging | `shared/logging_config.py` | JSON-formatted structured logging |
| P0 | Checkpoint | `shared/checkpoint.py` | Resume failed runs |
| P1 | Base Config | `shared/base_config.py` | Config inheritance (BaseConfig, SapphireConfig, etc.) |
| P1 | Resilience | `shared/resilience.py` | Retry + circuit breaker patterns |
| P2 | Metrics | `shared/metrics.py` | Run metrics collection |
| P2 | Validation | `shared/validation.py` | Pydantic-based data validation |

## Design Considerations

### Integration Strategy
- **Opt-in adoption** - Don't require refactoring all 95+ scrapers
- **Backward compatible** - Existing scrapers continue working
- **Gradual migration** - New scrapers use shared utils, migrate old ones incrementally

### Current Patterns to Support
1. **Config**: Dict-based `DIRS`, `BASE_URLS`, `BASE_PARAMS`, `HEADERS`
2. **Logging**: Replace `print()` with drop-in logger
3. **Retries**: Standardize on `tenacity` patterns already used by some projects
4. **Progress**: Thread-safe `ProgressCounter` class pattern
5. **File I/O**: `orjson` for JSON, date-versioned directories

---

## Implementation Plan

### Directory Structure

```
scraping/
├── shared/                      # NEW: Shared utilities package
│   ├── __init__.py              # Package exports
│   ├── logging_config.py        # P0: JSON logging (replaces print)
│   ├── checkpoint.py            # P0: Resume failed runs
│   ├── base_config.py           # P1: Config inheritance
│   ├── resilience.py            # P1: Retry + circuit breaker
│   ├── metrics.py               # P2: Run metrics
│   ├── validation.py            # P2: Pydantic validation
│   └── tests/                   # Unit tests
│       ├── test_logging.py
│       ├── test_checkpoint.py
│       └── ...
```

### Implementation Order

```
Week 1-2 (P0 Critical)
├── 1. logging_config.py  [foundational, no deps]
└── 2. checkpoint.py      [depends on logging]

Week 3-4 (P1 High)
├── 3. base_config.py     [standalone]
└── 4. resilience.py      [wraps tenacity]

Week 5-6 (P2 Medium)
├── 5. metrics.py         [depends on logging]
└── 6. validation.py      [uses pydantic]
```

### Key Design Decisions

1. **Opt-in adoption** - No changes required to existing 95+ scrapers
2. **Drop-in replacements** - Logger works like `print()`, configs wrap existing dicts
3. **Minimal deps** - Uses stdlib + existing deps (tenacity, pydantic, orjson)
4. **Backward compatible** - Export individual values for legacy imports

### File Summaries

#### 1. `logging_config.py` (P0)
- `Logger` class with print-like interface: `log("message")` or `log.info("message")`
- JSON lines output to `{date}/logs/{project}.jsonl`
- Console output with colors for human readability
- Extra context via kwargs: `log.info("Found", count=1000, phase="discovery")`

#### 2. `checkpoint.py` (P0)
- Stores state in `{date}/.checkpoint.json`
- Phase-level: `is_phase_complete()`, `mark_phase_start/complete()`
- Item-level: `get_processed_ids()`, `add_processed_id()`
- Auto-save every 100 items

#### 3. `base_config.py` (P1)
- `BaseConfig` dataclass with computed `dirs`, `prev_dirs` properties
- Site-type subclasses: `SapphireConfig`, `HealthsparqConfig`, `CarrierConfig`, `AnthemConfig`
- Environment variable support via `os.environ.get()`
- `setup_directories()` method

#### 4. `resilience.py` (P1)
- `@retry_with_backoff()` decorator wrapping tenacity
- `CircuitBreaker` class with CLOSED/OPEN/HALF_OPEN states
- Both sync and async support
- Composable `@with_resilience()` decorator

#### 5. `metrics.py` (P2)
- `RunMetrics` dataclass for collecting run statistics
- Phase timing via context manager: `with metrics.time_phase("discovery")`
- Saves to `{date}/metrics.json`

#### 6. `validation.py` (P2)
- Pydantic models matching output schema: `ProviderRecord`, `Address`, `Phone`, etc.
- `validate_record(data)` returns `(bool, error_string)`
- `validate_batch()` for bulk validation

---

## Migration Strategy

### Zero-Change Adoption
Existing scrapers continue working unchanged - `shared/` is additive.

### Incremental Adoption (per scraper)

**Step 1: Add logging (2 lines)**
```python
import sys; sys.path.insert(0, "..")
from shared import Logger
log = Logger(config.PROJECT_NAME, config.DIRS.get("logs"))
# Replace print() with log.info()
```

**Step 2: Add checkpointing (in run_all.py)**
```python
from shared import Checkpoint
checkpoint = Checkpoint(config.PROJECT_NAME, config.CURR_DATE)

for task in TASKS:
    if checkpoint.is_phase_complete(task):
        continue
    checkpoint.mark_phase_start(task)
    run_task(task)
    checkpoint.mark_phase_complete(task)
```

**Step 3: Config inheritance (optional)**
```python
from shared import SapphireConfig
config = SapphireConfig(project_name="...", ...)
# Backward compat exports
DIRS = config.dirs
```

### Pilot Projects
1. `audiobee_bcbs_il` (Sapphire)
2. `audiobee_mvp_health` (Healthsparq)
3. `audiobee_multiplan` (Carrier)

---

## Critical Files

| File | Action |
|------|--------|
| `shared/__init__.py` | Create - package exports |
| `shared/logging_config.py` | Create - P0 logging |
| `shared/checkpoint.py` | Create - P0 resume |
| `shared/base_config.py` | Create - P1 config |
| `shared/resilience.py` | Create - P1 retry |
| `shared/metrics.py` | Create - P2 metrics |
| `shared/validation.py` | Create - P2 validation |

---

## Dependencies

```toml
# shared/pyproject.toml
dependencies = [
    "orjson>=3.9.0",      # Fast JSON (optional)
    "pydantic>=2.0.0",    # Validation
    "tenacity>=8.0.0",    # Retries
]
```

All deps already used by existing scrapers.

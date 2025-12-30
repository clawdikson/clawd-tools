# feat: Comprehensive Logging Enhancement for healthsparq and core packages

## Overview

Add comprehensive logging to the healthsparq and core packages to enable proper debugging, monitoring, and troubleshooting of scraper operations. Currently, only **6.25%** of healthsparq files have logging, and critical core modules use `print()` instead of structured logging.

## Problem Statement

### Current State

**healthsparq package** (16 Python files, 9,048 LOC):

- **1 file** has logging (normalize.py - 24 logger calls)
- **5 files** use print() for errors (should be logger)
- **10 files** have no logging at all

**core package** (~35 modules):

- Excellent logging infrastructure in `core/logging/logger.py`
- **I/O utilities** (jsonl.py, sqlite_fs.py): Zero logging
- **Session modules**: Use print() instead of logger
- **Config/Proxy modules**: Minimal or no logging

### Critical Gaps

| Module                            | Status       | Impact                                      |
| --------------------------------- | ------------ | ------------------------------------------- |
| `healthsparq/core/healthspark.py` | No logging   | No visibility into API calls, retries, auth |
| `healthsparq/core/session.py`     | No logging   | No visibility into login, session reuse     |
| `healthsparq/phases/search.py`    | print() only | Errors not structured                       |
| `healthsparq/phases/details.py`   | print() only | Errors not structured                       |
| `core/io/jsonl.py`                | No logging   | Silent I/O failures                         |
| `core/io/sqlite_fs.py`            | No logging   | Silent DB operations                        |
| `core/session/browser_session.py` | print() only | Browser lifecycle invisible                 |

## Proposed Solution

### Phase 1: Core Package Logging Enhancement

Add structured logging to all core modules following the existing `core/logging/logger.py` infrastructure.

### Phase 2: healthsparq Package Logging

Convert all print() statements to logger calls and add logging to critical paths.

### Phase 3: Enhanced Logging Features

- Add JSON structured output for machine parsing
- Add error-only log file with separate rotation
- Add log context manager for async context propagation

---

## Technical Approach

### Import Pattern (All Files)

```python
# Use core.logging if available, fallback to stdlib
try:
    from core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
```

### Logging Levels Guide

| Level    | Usage                                                                         |
| -------- | ----------------------------------------------------------------------------- |
| DEBUG    | Pagination decisions, filter drilling, retry details, request/response bodies |
| INFO     | Phase start/completion, record counts, file writes, session lifecycle         |
| WARNING  | Corrupted files, invalid responses, skipped records, rate limits              |
| ERROR    | API failures, file I/O errors, mapping failures                               |
| CRITICAL | Session failures, fatal configuration errors                                  |

---

## Implementation Phases

### Phase 1: Core Package (Priority: CRITICAL)

**Effort**: 3-4 hours

#### 1.1 I/O Utilities - `core/io/jsonl.py`

**File**: `/Users/dikson/Work/ideon_scraping/scraping/core/io/jsonl.py`

Add logging for:

- File open/close operations (DEBUG)
- Deduplication skips (DEBUG)
- Batch write stats (INFO)
- Invalid JSON line skips (WARNING)
- I/O errors (ERROR)

```python
# Example additions
logger.debug(f"JSONLWriter: opened {file_path} (mode={mode}, dedup_key={dedup_key})")
logger.debug(f"JSONLWriter: skipped duplicate key={key}")
logger.info(f"JSONLWriter: wrote {written}/{total} records ({skipped} duplicates)")
logger.warning(f"JSONLReader: skipped invalid JSON on line {line_num}: {e}")
```

#### 1.2 SQLite Filesystem - `core/io/sqlite_fs.py`

**File**: `/Users/dikson/Work/ideon_scraping/scraping/core/io/sqlite_fs.py`

Add logging for:

- DB initialization (INFO)
- Buffer flush operations with stats (DEBUG)
- Export operations (INFO)
- Database size warnings (WARNING)

```python
logger.info(f"SQLiteFS: initialized {db_path} (buffer_size={buffer_size})")
logger.debug(f"SQLiteFS: flushed {count} writes in {elapsed:.3f}s")
logger.info(f"SQLiteFS: exported {count} files to {output_path}")
```

#### 1.3 Session Modules - Replace print() with logger

**Files**:

- `/Users/dikson/Work/ideon_scraping/scraping/core/session/browser_session.py` (lines 180, 189)
- `/Users/dikson/Work/ideon_scraping/scraping/core/session/http_session.py` (lines 110, 158)
- `/Users/dikson/Work/ideon_scraping/scraping/core/session/resilient_session.py`

Add logging for:

- Browser launch (INFO)
- Login attempts and results (INFO/ERROR)
- Request/response cycle (DEBUG)
- Rate limiting and backoff (WARNING)
- Session recreation (INFO)

```python
logger.info(f"BrowserSession: launching (proxy={proxy_type}, browser_id={browser_id})")
logger.debug(f"BrowserSession: {method} {url}")
logger.warning(f"BrowserSession: rate limited (429), waiting {backoff}s")
logger.info(f"ResilientSession: recreating (generation={gen})")
```

#### 1.4 Config Modules - Add validation logging

**Files**:

- `/Users/dikson/Work/ideon_scraping/scraping/core/config/base.py`
- `/Users/dikson/Work/ideon_scraping/scraping/core/config/factory.py`

Add logging for:

- Config loading (DEBUG)
- Environment variable resolution (DEBUG)
- Missing required variables (WARNING)

---

### Phase 2: healthsparq Package (Priority: HIGH)

**Effort**: 2-3 hours

#### 2.1 Convert print() to logger

**Files to update**:

| File                  | print() Count | Changes Needed           |
| --------------------- | ------------- | ------------------------ |
| `phases/search.py`    | 4             | lines 159, 163, 302, 306 |
| `phases/details.py`   | 3             | lines 78, 82, 86         |
| `core/file_writer.py` | 2             | lines 123, 130           |

#### 2.2 Add logging to healthspark.py

**File**: `/Users/dikson/Work/ideon_scraping/scraping/healthsparq/core/healthspark.py` (371 LOC)

Add logging for:

- Session initialization (INFO)
- Search operations with params (DEBUG)
- Provider detail fetches (DEBUG)
- Retry attempts (WARNING)
- API errors with status codes (ERROR)

```python
logger.info(f"HealthSpark: session initialized for {domain}")
logger.debug(f"HealthSpark: search location={location}, page={page}")
logger.warning(f"HealthSpark: retry {attempt}/{max_retries} for {url}")
logger.error(f"HealthSpark: API error {status_code}: {error_message}")
```

#### 2.3 Add logging to session.py

**File**: `/Users/dikson/Work/ideon_scraping/scraping/healthsparq/core/session.py` (198 LOC)

Add logging for:

- Login start/completion (INFO)
- Cookie extraction (DEBUG)
- HTTP session creation from browser (INFO)

#### 2.4 Enhance normalize.py logging

Already has logging but add:

- Per-record mapping progress (DEBUG with progress %)
- NPI merge details (DEBUG)

---

### Phase 3: Enhanced Logging Features (Priority: MEDIUM)

**Effort**: 1-2 hours

#### 3.1 Add JSON structured output

**File**: `/Users/dikson/Work/ideon_scraping/scraping/core/logging/logger.py`

```python
def setup_logging(
    project_name: str,
    run_id: str,
    log_dir: str | Path = "logs",
    level: str = "INFO",
    enable_json_output: bool = True,  # NEW
) -> None:
    # ... existing console handler ...

    if enable_json_output:
        logger.add(
            log_path / f"{project_name}.jsonl",
            format="{message}",
            level=level,
            rotation="50 MB",
            retention="7 days",
            compression="gz",
            serialize=True,  # JSON output
            enqueue=True,
        )
```

#### 3.2 Add error-only log file

```python
# Separate file for errors (quick debugging)
logger.add(
    log_path / f"{project_name}_errors.log",
    format=log_format,
    level="ERROR",
    rotation="10 MB",
    retention="30 days",
    compression="gz",
    enqueue=True,
)
```

#### 3.3 Add async context manager

**File**: `/Users/dikson/Work/ideon_scraping/scraping/core/logging/logger.py`

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def log_context(
    trace_id: str | None = None,
    phase: str | None = None,
    **extra: Any,
):
    """Async context manager for scoped logging context."""
    tokens = []
    if trace_id:
        tokens.append(trace_id_var.set(trace_id))
    # ... bind extra context ...
    try:
        yield
    finally:
        for token in reversed(tokens):
            token.var.reset(token)
```

---

## Acceptance Criteria

### Functional Requirements

- [ ] All `print()` statements in core/ and healthsparq/ converted to logger calls
- [ ] `core/io/jsonl.py` has DEBUG/INFO/WARNING/ERROR logging
- [ ] `core/io/sqlite_fs.py` has DEBUG/INFO/WARNING logging
- [ ] `core/session/*.py` modules have full lifecycle logging
- [ ] `healthsparq/core/healthspark.py` has API call logging
- [ ] `healthsparq/phases/*.py` have phase progress logging
- [ ] JSON structured log output available via `enable_json_output=True`
- [ ] Error-only log file created with separate rotation

### Non-Functional Requirements

- [ ] No performance degradation (use `opt(lazy=True)` for expensive debug logs)
- [ ] Backwards compatible (existing log setups continue working)
- [ ] Log levels appropriate (DEBUG for verbose, INFO for operations)

### Quality Gates

- [ ] All existing tests pass
- [ ] Log output verified in manual testing
- [ ] No `print()` statements remain in production code

---

## Success Metrics

- **Logging coverage**: 6.25% → 90%+ of files
- **print() statements**: 15+ → 0 in production code
- **Debug capability**: Can trace any request from CLI to API response

---

## Files to Modify

### core/ package

| File                                | Action                       | Priority |
| ----------------------------------- | ---------------------------- | -------- |
| `core/io/jsonl.py`                  | Add logging                  | P1       |
| `core/io/sqlite_fs.py`              | Add logging                  | P1       |
| `core/session/browser_session.py`   | Replace print(), add logging | P1       |
| `core/session/http_session.py`      | Replace print(), add logging | P1       |
| `core/session/resilient_session.py` | Add logging                  | P1       |
| `core/config/base.py`               | Add logging                  | P2       |
| `core/config/factory.py`            | Add logging                  | P2       |
| `core/logging/logger.py`            | Add JSON output, error file  | P3       |

### healthsparq/ package

| File                              | Action                            | Priority |
| --------------------------------- | --------------------------------- | -------- |
| `healthsparq/core/healthspark.py` | Add logging                       | P1       |
| `healthsparq/core/session.py`     | Add logging                       | P1       |
| `healthsparq/phases/search.py`    | Replace print(), add logging      | P1       |
| `healthsparq/phases/details.py`   | Replace print(), add logging      | P1       |
| `healthsparq/core/file_writer.py` | Replace print()                   | P2       |
| `healthsparq/cli.py`              | Add structured logging (optional) | P3       |

---

## Dependencies & Prerequisites

- `core/logging/logger.py` must be available (already exists)
- All modules use the try/except import pattern for backwards compatibility

---

## Risk Analysis

| Risk                              | Likelihood | Impact | Mitigation                                    |
| --------------------------------- | ---------- | ------ | --------------------------------------------- |
| Performance overhead from logging | Low        | Medium | Use `opt(lazy=True)` for expensive operations |
| Log file disk space               | Low        | Low    | Rotation already configured                   |
| Breaking changes                  | Low        | Low    | All changes are additive                      |

---

## References

### Internal References

- Logging infrastructure: `core/logging/logger.py`
- Logging design doc: `docs/implementation_research/04_LOGGING.md`
- Current normalize.py logging: `healthsparq/phases/normalize.py:20-24`

### External References

- [Loguru documentation](https://loguru.readthedocs.io/)
- [Python logging best practices 2025](https://signoz.io/guides/python-logging-best-practices/)

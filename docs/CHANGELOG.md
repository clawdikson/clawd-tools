# Changelog

Recent enhancements and implementation details for the Ideon Scraping project.

## Dec 2025

### Browser Backend Selection (Completed)

**From commit de79ce4**: Added selectable browser backend to BrowserSession enabling choice between Patchright, Playwright, and Camoufox.

**What Changed**:

- **core/session/backend.py**: New BrowserType enum (PATCHRIGHT, PLAYWRIGHT, CAMOUFOX)
- **core/session/browser_session.py**: Added browser_type parameter with lazy imports for optional backends
- **core/session/resilient_session.py**: Pass-through browser_type parameter to BrowserSession
- **healthsparq/core/session.py**: Added browser_type to SessionConfig and create_session()
- **core/tests/test_browser_backend.py**: Comprehensive test suite for backend selection
- **Dependencies**: Added playwright>=1.55.0 and camoufox[geoip]>=0.4.11 to core/pyproject.toml

**Backend Types**:

| Backend    | Engine   | Anti-Detection | Use Case                 |
| ---------- | -------- | -------------- | ------------------------ |
| PATCHRIGHT | Chromium | Medium         | Default, most sites      |
| PLAYWRIGHT | Chromium | Low            | Sites without detection  |
| CAMOUFOX   | Firefox  | High           | Anti-bot protected sites |

**Key Benefits**:

- Flexible backend selection for different anti-detection requirements
- Enum-based type safety with string fallback for convenience
- Lazy imports prevent unnecessary dependencies (only load backend when used)
- Backward compatible - defaults to PATCHRIGHT (existing behavior)
- Camoufox cleanup handled automatically via context manager pattern

**Usage Pattern**:

```python
from core.session import BrowserSession, ResilientBrowserSession, BrowserType

# Default: Patchright (existing behavior)
session = BrowserSession()

# Standard Playwright
session = BrowserSession(browser_type=BrowserType.PLAYWRIGHT)

# Camoufox for anti-bot sites
session = BrowserSession(browser_type=BrowserType.CAMOUFOX)

# String also accepted (case-insensitive)
session = BrowserSession(browser_type="camoufox")

# ResilientBrowserSession passes through
resilient = ResilientBrowserSession(
    login_url="https://example.com",
    browser_type=BrowserType.CAMOUFOX,
)
```

**See**: `plans/feat-browser-session-camoufox.md` for complete implementation plan.

---

### DataStore Abstraction Layer (Completed)

**From commit e4e4250**: Added unified DataStore abstraction to core/io module for consistent interface across storage backends.

**What Changed**:

- **core/io/base.py**: DataStore Protocol with put/get/exists/keys/iter operations
- **core/io/factory.py**: create_store() factory function with auto-detection from file extension
- **core/io/json_files.py**: JSONFileStore implementation for individual JSON files
- **core/io/jsonl.py**: JSONLStore wrapper around existing JSONLWriter/JSONLReader
- **core/io/sqlite_fs.py**: SQLiteStore wrapper around existing SQLiteFS
- **Filepath-keyed storage**: Keys are logical paths like "provider_details/1234567890.json"
- **Backend selection**: Auto-detects from extension (.jsonl, .db) or path (directory → JSON files)

**Backend Types**:

| Backend    | Best For                        | Extension | Pros                                  | Cons                     |
| ---------- | ------------------------------- | --------- | ------------------------------------- | ------------------------ |
| JSONL      | Streaming, append-only          | .jsonl    | Fast writes, human-readable           | No random access by path |
| JSON Files | Debugging, small datasets       | /         | Easy inspection, no DB overhead       | Slow with 100k+ files    |
| SQLite     | Large datasets, exists() checks | .db       | 15x faster writes, ACID, no FS limits | Binary format            |

**Key Benefits**:

- Unified API across JSONL, SQLite, and JSON files (no more switching between different APIs)
- Configuration-driven backend selection via create_store()
- Filepath-keyed interface matches existing scraper organization patterns
- Protocol-based design allows easy addition of new backends
- Backward compatibility: legacy JSONLWriter/SQLiteFS still work directly

**Usage Pattern**:

```python
from core.io import create_store, BackendType

# Auto-detect backend from extension
store = create_store("raw_data.jsonl")  # JSONL backend
store = create_store("raw_data.db")     # SQLite backend
store = create_store("raw_data/")       # JSON Files backend

# Explicit backend selection
store = create_store("raw_data", backend=BackendType.SQLITE)

# Unified API across all backends
store.put("provider_details/1234567890.json", provider_data)
data = store.get("provider_details/1234567890.json")
if store.exists("provider_details/1234567890.json"):
    print("Found provider")

# Iterate all records
for path, record in store:
    process(record)
```

**See**: `plans/feat-datastore-abstraction.md` for complete implementation details.

---

### Provider Data Mapper Module (Completed)

**From commit bddc142**: Added unified mapper module to core package for provider data normalization.

**What Changed**:

- **core/mapper/**: New module for converting raw scraper output to schema-compliant JSONL
- **HealthSparqMapper**: Handles v2 format for 23 HealthSparq projects with network/address extraction
- **CarrierMapper**: Abstract base class for custom carrier API structures (subclass per carrier)
- **Normalization utilities**: ZIP code (5 digits), phone, gender, address string building
- **NPI deduplication**: Merges duplicate records across networks with network/address/specialty merging
- **Schema validation**: Against `core/data/output_json_schema.json` using jsonschema library
- **healthsparq/phases/normalize.py**: Fixed ZIP code format (5 digits) and uszips.xlsx path (commit 45566dc)

**Mapper Types**:

| Mapper Type         | Use Case                                | Projects |
| ------------------- | --------------------------------------- | -------- |
| `HealthSparqMapper` | HealthSparq platform scrapers           | 23       |
| `CarrierMapper`     | Direct API scrapers (custom structures) | 35+      |
| `HTMLCarrierMapper` | Legacy HTML scrapers (BeautifulSoup)    | TBD      |

**Key Benefits**:

- Consistent normalization across all projects (ZIP always 5 digits, phone/address format)
- Reusable base classes reduce code duplication in individual scrapers
- Schema validation catches format issues before output generation
- Proper NPI-based deduplication with record merging logic
- HealthSparq projects now output correct format matching schema requirements

**Usage Pattern**:

```python
# HealthSparq projects (automatic)
from core.mapper import run_normalize

result = run_normalize(
    raw_dir=Path("20251227/raw/provider_details"),
    output_file=Path("20251227/processed/providers.jsonl"),
    validate=True,
)

# Carrier projects (custom mapper)
class MyCarrierMapper(CarrierMapper):
    def extract_provider(self, data: dict) -> dict:
        # Map carrier-specific fields
        ...

result = run_carrier_normalize(raw_dir, output_file, mapper=MyCarrierMapper("MyCarrier"))
```

**See**: `core/mapper/README.md` for implementation guide and examples.

---

### Comprehensive Logging Enhancement (Completed)

**From commit 8193314**: Added structured logging to core and healthsparq packages to enable proper debugging and monitoring.

**What Changed**:

- **core/logging/logger.py**: Enhanced loguru-based logging with JSON output support and error-only log files
- **core session modules**: Replaced all `print()` statements with `logger` calls (browser_session.py, http_session.py, resilient_session.py)
- **core I/O modules**: Added logging to sqlite_fs.py and jsonl.py for I/O visibility
- **core config modules**: Added logging to factory.py and base.py for configuration debugging
- **healthsparq modules**: Added comprehensive logging to session.py, healthspark.py, file_writer.py, search.py, and details.py

**Logging Features**:

- Structured logging with project_name, run_id, trace_id correlation
- JSON structured output for machine parsing (`.jsonl` log files)
- Error-only log files for quick debugging (`logs/{date}/{project}_error.log`)
- Async-safe context propagation via ContextVar
- InterceptHandler for third-party library integration
- Automatic log rotation (100 MB files, 30 day retention)

**Import Pattern** (all modules use this for backwards compatibility):

```python
try:
    from core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
```

**Key Benefits**:

- Visibility into browser lifecycle, session management, and API operations
- Structured error tracking with context preservation
- Performance monitoring via elapsed time tracking
- Request/response debugging with trace_id correlation
- Silent I/O operations now logged (SQLiteFS writes, JSONL deduplication)

**See**: `plans/feat-comprehensive-logging-enhancement.md` for full implementation details.

---

### HealthSparq Library Transformation (v2.0.0 - Completed)

The `healthsparq/` package has been transformed from a CLI-only tool into an importable library with custom mapper injection support.

**What Changed**:

- **v2.0.0 release**: Dual interface (CLI + importable library)
- **Public API**: `run_scraper_sync()`, `default_mapper()`, `load_config()`, `MapperFunc`
- **Custom mappers**: Projects can inject custom normalization logic via `MapperFunc` parameter
- **Project templates**: `healthsparq/templates/` for scaffolding library-based projects
- **Pilot project**: `audiobee_christus_health_plan/` demonstrates library usage pattern

**Key Benefits Achieved**:

- Projects can customize normalization logic without forking the library
- Clean imports: `from healthsparq import run_scraper_sync, default_mapper`
- No more `sys.path.insert()` hacks in library-based projects
- Better IDE support and type checking
- Single dependency in project requirements: `healthsparq`

**Migration Path**:

- Existing CLI workflow unchanged: `python -m healthsparq run <project> --curr YYYYMMDD`
- New projects can use library pattern with templates from `healthsparq/templates/`
- Pilot: `audiobee_christus_health_plan/` shows library-based approach
- Gradual migration: Projects can adopt library pattern as needed

---

### HealthSparq-Core Consolidation (Completed)

**From commit 03bd525**: Successfully consolidated duplicate normalization utilities from healthsparq to core package.

**Problem Solved**: The `healthsparq/` package was duplicating ~75 lines of normalization/deduplication utilities from `core/` package, including `normalize_zip_code`, `deduplicate_by_npi`, `merge_provider_data`, and the `MapperFunc` type alias. This created maintenance burden (bug fixes in two places) and drift risk.

**Changes Implemented** (Phase 1 - Dec 28, 2025):

- **Import normalization utilities from core** (~75 LOC reduction)
    - `MapperFunc` type from `core/mapper/base.py`
    - `normalize_zip_code` from `core/mapper/normalize.py`
    - `deduplicate_by_npi`, `merge_provider_records` from `core/mapper/dedup.py`
    - **Kept local**: `clean_network_name()` (7 LOC, project-specific "medica_sg" → "medica" replacement)
    - **File modified**: `healthsparq/phases/normalize.py` only

**Impact**: All 23 HealthSparq projects now use single source of truth from core package. Output remains byte-identical. No API changes for library users.

**Rejected Phases** (Reviewer consensus - DHH & Kieran):

- **Phase 2**: Exception hierarchy unification (no practical value - "inheritance for inheritance's sake")
- **Phase 3**: Retry logic consolidation (intentionally different - HTTP vs browser session levels)
- **Phase 4**: Deprecation warnings (unnecessary for internal code)

**See**:

- `plans/feat-healthsparq-core-consolidation.md` - Master plan
- `plans/context/healthsparq-core-consolidation-phase*.md` - Detailed phase documentation with reviewer rationale

---

### HTTP Retry Logic Consolidation (Completed)

**From commits f1d0dea, cabeb5d**: Consolidated duplicate HTTP retry logic from healthsparq to core package.

**Problem Solved**: The `healthsparq/core/session.py` contained ~40 lines of duplicate HTTP retry logic (exponential backoff, auth error handling) that should have been in `core/session/http_session.py`. This created:

- Code duplication (retry logic in two places)
- Inconsistent retry behavior across projects
- Maintenance burden (bug fixes needed in multiple locations)

**Changes Implemented** (3 phases - Dec 28, 2025):

**Phase 1** - Add Retry Logic to `core/session/http_session.py`:

- Added `RetryConfig` dataclass with configurable parameters (max_retries, backoff_factor, retry_on_status)
- Added `_request_with_retry()` method with exponential backoff
- Added `on_auth_error` callback hook for session invalidation on 401/403
- Updated `get()` and `post()` to use retry wrapper
- Exported `RetryConfig` from `core/session/__init__.py`

**Phase 2** - Simplify `healthsparq/core/session.py`:

- Removed duplicate `_request_with_retry()` method (~40 LOC)
- Added `_invalidate_session()` callback for auth error handling
- Updated `login()` to pass `RetryConfig` and `on_auth_error` to HttpSession
- Simplified `get()` and `post()` to delegate directly to HttpSession
- Added fallback handling for legacy environments without RetryConfig

**Phase 3** - Testing (Pending):

- Test coverage for retry logic in core/tests/test_session.py
- Updated healthsparq tests for simplified session

**Key Features**:

- **Exponential backoff**: Configurable backoff_factor (default 2.0) with max_backoff cap (30s)
- **Configurable retries**: Default 5 retries for 429/500-504 status codes
- **Auth error callbacks**: Session invalidation on 401/403 via `on_auth_error` hook
- **Backward compatible**: All parameters optional with sensible defaults

**Impact**:

- All projects using `HttpSession` now get retry logic automatically
- ~40 LOC removed from healthsparq (single source of truth in core)
- No behavior changes for existing scrapers
- Consistent retry configuration across all projects

**See**:

- `plans/refactor-healthsparq-retry-consolidation.md` - Master plan
- `plans/context/http-retry-consolidation-phase*.md` - Detailed phase documentation

---

### BrowserSession Backend Selection (Planned)

**Implementation plan**: `plans/feat-browser-session-camoufox.md` - Add selectable browser backend to `core/session/BrowserSession` enabling choice between Patchright, Playwright, and Camoufox.

**Planned Architecture**:

- **BrowserType enum**: `PATCHRIGHT` (default), `PLAYWRIGHT`, `CAMOUFOX`
- **Backend selection**: Via `browser_type` parameter (enum or string)
- **Lazy imports**: Backend libraries loaded only when selected
- **Concurrency preservation**: Existing patterns unchanged (\_init_lock, \_request_semaphore, \_active_cond)
- **Backward compatibility**: Default to PATCHRIGHT (current behavior)

**New Dependencies** (when implemented):

- `playwright>=1.55.0` - Standard Playwright library
- `camoufox[geoip]>=0.4.11` - Firefox-based anti-detection browser

**Backend Comparison**:

| Backend    | Engine   | Anti-Detection | Use Case                 |
| ---------- | -------- | -------------- | ------------------------ |
| PATCHRIGHT | Chromium | Medium         | Default, most sites      |
| PLAYWRIGHT | Chromium | Low            | Sites without detection  |
| CAMOUFOX   | Firefox  | High           | Anti-bot protected sites |

**Implementation Tasks** (8 total):

1. Add BrowserType enum and dependencies to `core/session/backend.py`
2. Add browser_type parameter to BrowserSession `__init__`
3. Implement backend-specific initialization (\_init_playwright, \_init_camoufox)
4. Implement backend-specific cleanup (Camoufox uses `__aexit__` pattern)
5. Update ResilientBrowserSession to pass through browser_type
6. Update HealthSparqSession with browser_type support (optional)
7. Write unit tests for backend selection and initialization
8. Update `core/CLAUDE.md` documentation

**Key Features**:

- Unified async interface across all backends
- Camoufox uses AsyncCamoufox context manager (different from Playwright/Patchright)
- Backend-specific proxy configuration handling
- Preserves existing session lifecycle and error handling

**See**: `plans/feat-browser-session-camoufox.md` for complete 8-task implementation plan with code snippets.

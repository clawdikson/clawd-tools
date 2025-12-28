# Recent Enhancements

This document tracks significant infrastructure and tooling changes to the scraping project.

---

## DataStore Abstraction Layer (Completed - Dec 2025)

**From commit e4e4250**: Added unified DataStore abstraction to core/io module for consistent interface across storage backends.

### What Changed

- **core/io/base.py**: DataStore Protocol with put/get/exists/keys/iter operations
- **core/io/factory.py**: create_store() factory function with auto-detection from file extension
- **core/io/json_files.py**: JSONFileStore implementation for individual JSON files
- **core/io/jsonl.py**: JSONLStore wrapper around existing JSONLWriter/JSONLReader
- **core/io/sqlite_fs.py**: SQLiteStore wrapper around existing SQLiteFS
- **Filepath-keyed storage**: Keys are logical paths like "provider_details/1234567890.json"
- **Backend selection**: Auto-detects from extension (.jsonl, .db) or path (directory -> JSON files)

### Backend Types

| Backend    | Best For                        | Extension | Pros                                  | Cons                     |
| ---------- | ------------------------------- | --------- | ------------------------------------- | ------------------------ |
| JSONL      | Streaming, append-only          | .jsonl    | Fast writes, human-readable           | No random access by path |
| JSON Files | Debugging, small datasets       | /         | Easy inspection, no DB overhead       | Slow with 100k+ files    |
| SQLite     | Large datasets, exists() checks | .db       | 15x faster writes, ACID, no FS limits | Binary format            |

### Key Benefits

- Unified API across JSONL, SQLite, and JSON files (no more switching between different APIs)
- Configuration-driven backend selection via create_store()
- Filepath-keyed interface matches existing scraper organization patterns
- Protocol-based design allows easy addition of new backends
- Backward compatibility: legacy JSONLWriter/SQLiteFS still work directly

### Usage Pattern

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

## Provider Data Mapper Module (Completed - Dec 2025)

**From commit bddc142**: Added unified mapper module to core package for provider data normalization.

### What Changed

- **core/mapper/**: New module for converting raw scraper output to schema-compliant JSONL
- **HealthSparqMapper**: Handles v2 format for 23 HealthSparq projects with network/address extraction
- **CarrierMapper**: Abstract base class for custom carrier API structures (subclass per carrier)
- **Normalization utilities**: ZIP code (5 digits), phone, gender, address string building
- **NPI deduplication**: Merges duplicate records across networks with network/address/specialty merging
- **Schema validation**: Against `core/data/output_json_schema.json` using jsonschema library
- **healthsparq/phases/normalize.py**: Fixed ZIP code format (5 digits) and uszips.xlsx path (commit 45566dc)

### Mapper Types

| Mapper Type         | Use Case                                | Projects |
| ------------------- | --------------------------------------- | -------- |
| `HealthSparqMapper` | HealthSparq platform scrapers           | 23       |
| `CarrierMapper`     | Direct API scrapers (custom structures) | 35+      |
| `HTMLCarrierMapper` | Legacy HTML scrapers (BeautifulSoup)    | TBD      |

### Key Benefits

- Consistent normalization across all projects (ZIP always 5 digits, phone/address format)
- Reusable base classes reduce code duplication in individual scrapers
- Schema validation catches format issues before output generation
- Proper NPI-based deduplication with record merging logic
- HealthSparq projects now output correct format matching schema requirements

### Usage Pattern

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

## Comprehensive Logging Enhancement (Completed - Dec 2025)

**From commit 8193314**: Added structured logging to core and healthsparq packages to enable proper debugging and monitoring.

### What Changed

- **core/logging/logger.py**: Enhanced loguru-based logging with JSON output support and error-only log files
- **core session modules**: Replaced all `print()` statements with `logger` calls (browser_session.py, http_session.py, resilient_session.py)
- **core I/O modules**: Added logging to sqlite_fs.py and jsonl.py for I/O visibility
- **core config modules**: Added logging to factory.py and base.py for configuration debugging
- **healthsparq modules**: Added comprehensive logging to session.py, healthspark.py, file_writer.py, search.py, and details.py

### Logging Features

- Structured logging with project_name, run_id, trace_id correlation
- JSON structured output for machine parsing (`.jsonl` log files)
- Error-only log files for quick debugging (`logs/{date}/{project}_error.log`)
- Async-safe context propagation via ContextVar
- InterceptHandler for third-party library integration
- Automatic log rotation (100 MB files, 30 day retention)

### Import Pattern

All modules use this for backwards compatibility:

```python
try:
    from core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
```

### Key Benefits

- Visibility into browser lifecycle, session management, and API operations
- Structured error tracking with context preservation
- Performance monitoring via elapsed time tracking
- Request/response debugging with trace_id correlation
- Silent I/O operations now logged (SQLiteFS writes, JSONL deduplication)

**See**: `plans/feat-comprehensive-logging-enhancement.md` for full implementation details.

---

## HealthSparq Library Transformation (v2.0.0 - Completed)

The `healthsparq/` package has been transformed from a CLI-only tool into an importable library with custom mapper injection support.

### What Changed

- **v2.0.0 release**: Dual interface (CLI + importable library)
- **Public API**: `run_scraper_sync()`, `default_mapper()`, `load_config()`, `MapperFunc`
- **Custom mappers**: Projects can inject custom normalization logic via `MapperFunc` parameter
- **Project templates**: `healthsparq/templates/` for scaffolding library-based projects
- **Pilot project**: `audiobee_christus_health_plan/` demonstrates library usage pattern

### Key Benefits Achieved

- Projects can customize normalization logic without forking the library
- Clean imports: `from healthsparq import run_scraper_sync, default_mapper`
- No more `sys.path.insert()` hacks in library-based projects
- Better IDE support and type checking
- Single dependency in project requirements: `healthsparq`

### Migration Path

- Existing CLI workflow unchanged: `python -m healthsparq run <project> --curr YYYYMMDD`
- New projects can use library pattern with templates from `healthsparq/templates/`
- Pilot: `audiobee_christus_health_plan/` shows library-based approach
- Gradual migration: Projects can adopt library pattern as needed

### Next Steps

- Migrate additional projects to library pattern using templates
- Document custom mapper patterns for common use cases
- Evaluate subclassing support for deeper phase customization

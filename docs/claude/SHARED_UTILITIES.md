# Shared Utilities

Common utilities and packages used across all scraper projects.

## healthsparq/ - Importable Library v2.0

Unified package for 23 HealthSparq projects with dual CLI + library interface.

### CLI Usage

```bash
# List available projects
python -m healthsparq list

# Validate configuration
python -m healthsparq validate christus_health_plan

# Run scraper (standalone - uses core/session for browser automation)
python -m healthsparq run christus_health_plan --curr 20251226 --prev 20251126

# Run specific phase only
python -m healthsparq run medica_sg --curr 20251226 --phase 1 # Search
python -m healthsparq run medica_sg --curr 20251226 --phase 2 # Details
python -m healthsparq run medica_sg --curr 20251226 --phase 3 # Normalize

# Health checks
python -m healthsparq doctor
```

### Library Usage

```python
from healthsparq import load_config, run_scraper_sync, default_mapper

# Basic usage
config = load_config("christus_health_plan")
result = run_scraper_sync(config, "20251227")
print(f"Found {result.providers_count} providers")

# Custom mapper injection
def my_mapper(raw: dict) -> dict:
    result = default_mapper(raw)
    # Add custom logic here
    return result

result = run_scraper_sync(config, "20251227", mapper=my_mapper)

# Enable JSON schema validation
result = run_scraper_sync(config, "20251227", validate=True)
```

### Project Scaffolding

Use templates in `healthsparq/templates/` to create library-based projects:

- `run.py.template`: Typer CLI importing from healthsparq library
- `mapper.py.template`: Custom mapper extending `default_mapper()`
- `.env.example`: Environment config (proxy, browser settings)
- `requirements.txt.template`: Single dependency: `healthsparq`
- `README.md.template`: Usage instructions
- `.gitignore.template`: Output directory ignores

### Key Features

- **Dual interface**: CLI tool + importable library with custom mapper injection
- **Configuration-driven**: YAML configs in `healthsparq/configs/` (no hardcoded domains/plans)
- **Custom mapping**: Projects can inject custom mapper functions via `MapperFunc` type
- **Async session management**: Browser login -> cookie extraction -> fast HTTP requests
- **Structured exceptions**: Custom hierarchy (AuthenticationError, APIError, SearchError, etc.)
- **Context managers**: Proper resource cleanup with `async with` pattern
- **99+ tests**: Comprehensive test suite with fixtures and integration tests

### Architecture

| Component                         | Purpose                                                             |
| --------------------------------- | ------------------------------------------------------------------- |
| `healthsparq/api.py`              | High-level API (`run_scraper_sync`, `ScraperResult`, `PhaseResult`) |
| `healthsparq/core/healthspark.py` | HealthSpark API wrapper (search, profile, geocode endpoints)        |
| `healthsparq/core/session.py`     | HealthSparqSession with ResilientBrowserSession for auth            |
| `healthsparq/config/schema.py`    | Pydantic models for configuration validation                        |
| `healthsparq/phases/normalize.py` | Supports custom mapper injection via `MapperFunc` type              |
| `healthsparq/templates/`          | Project scaffolding templates for library-based projects            |

---

## healthsparq-server (Port 1018) - Legacy Only

**Deprecated**: Browser automation server for legacy `audiobee_*` HealthSparq projects only. NOT needed for the unified `healthsparq/` package.

```bash
# Start server (only for legacy audiobee_* projects)
cd healthsparq-server && PORT=1018 npm start
```

**Note**: The unified `healthsparq/` package is standalone Python and uses `core/session/` (ResilientBrowserSession) for browser automation.

---

## output_generator

QA and reporting utilities for validating scraper output.

```bash
# Validate output schema
python output_generator/type_check.py audiobee_*/

# Generate samples
python output_generator/sample_generator.py audiobee_*/

# Compare runs
python output_generator/comparison_creator.py audiobee_*/ --prev 20251010 --curr 20251110

# Create Excel report
python output_generator/report_generator.py audiobee_*/
```

---

## core/ - Shared Package v3.0

The `core/` submodule (formerly `shared_package/`) provides common utilities for all scrapers. **Always prefer core implementations over reinventing**.

### Mapper Module (`core/mapper/`)

Unified provider data normalization for all scraper types:

```python
from core.mapper import run_normalize, HealthSparqMapper, CarrierMapper
from pathlib import Path

# HealthSparq projects (23 projects)
result = run_normalize(
    raw_dir=Path("20251227/raw/provider_details"),
    output_file=Path("20251227/processed/providers.jsonl"),
    validate=True,  # JSON schema validation
)
print(f"Mapped {result.total_raw} -> {result.total_deduplicated} providers")

# Carrier projects (custom subclass)
class FloridaBlueMapper(CarrierMapper):
    def extract_provider(self, data: dict) -> dict:
        return {
            "npi": data.get("nationalProviderId"),
            "first_name": data.get("firstName"),
            # ... map carrier-specific fields
        }

mapper = FloridaBlueMapper(carrier_name="FloridaBlue")
result = run_carrier_normalize(
    raw_dir=Path("audiobee_florida_blue/20251227/raw"),
    output_file=Path("audiobee_florida_blue/20251227/processed/providers.jsonl"),
    mapper=mapper,
)
```

**Features**:

- HealthSparqMapper: v2 format for 23 HealthSparq projects
- CarrierMapper: Base class for custom API structures (subclass per carrier)
- Normalization: ZIP code (5 digits), phone, gender, address strings
- Deduplication: NPI-based with network/address/specialty merging
- Schema validation: Against `core/data/output_json_schema.json`
- Record merging: Combines duplicate NPIs across networks

### Logging (`core/logging/`)

```python
from core.logging import logger, setup_logging, set_trace_id

# Setup at startup with enhanced features
setup_logging(
    project_name="audiobee_bcbs_il",
    run_id="20251227",
    log_dir="logs",
    level="INFO",
    enable_json_output=True,   # JSON .jsonl file for machine parsing
    enable_error_file=True,    # Separate error-only log for debugging
)

# Structured logging with trace_id correlation
set_trace_id(f"provider_{npi}")
logger.bind(npi=npi, phase=3).info("Processing provider")

# Log levels guide
logger.debug("Pagination details", page=5, total=100)
logger.info("Phase completed", providers=1234, elapsed="5.2s")
logger.warning("Rate limited", retry_after=60, status_code=429)
logger.error("API failure", endpoint="/search", error=str(e))
logger.critical("Session failure", reason="browser crashed")
```

### File I/O (`core/io/`)

```python
from core.io import create_store, BackendType, JSONLWriter, JSONLReader, SQLiteFS, BoundedSet

# DataStore abstraction (unified interface for JSONL, SQLite, JSON files)
# Auto-detect backend from file extension
store = create_store("raw_data.jsonl")  # JSONL backend
store = create_store("raw_data.db")     # SQLite backend
store = create_store("raw_data/")       # JSON Files backend

# Unified API across all backends (filepath-keyed storage)
store.put("provider_details/1234567890.json", {"npi": "1234567890", ...})
store.put("search_results/TX/Dallas/page_1.json", {"results": [...]})
data = store.get("provider_details/1234567890.json")

# Check existence (optimized per backend)
if store.exists("provider_details/1234567890.json"):
    print("Provider exists")

# Iterate all records
for path, record in store:
    print(f"{path}: {record}")

# Pattern matching (glob-style)
for path in store.keys("provider_details/*.json"):
    print(path)
```

**Legacy Direct Usage** (still supported):

```python
# JSONL with auto-deduplication
with JSONLWriter("providers.jsonl", dedup_key="npi") as writer:
    writer.write(provider)  # Skips duplicates

# SQLite virtual filesystem (15x faster writes)
fs = SQLiteFS("scraper.db", buffer_size=100)
fs.write("raw/search/IL_60601.json", data)

# Memory-safe deduplication (LRU at 100k items)
seen = BoundedSet(max_size=100_000)
```

**Backend Comparison**:

| Backend    | Best For                        | Extension | Pros                                  | Cons                     |
| ---------- | ------------------------------- | --------- | ------------------------------------- | ------------------------ |
| JSONL      | Streaming, append-only          | `.jsonl`  | Fast writes, human-readable           | No random access by path |
| JSON Files | Debugging, small datasets       | `/`       | Easy inspection, no DB overhead       | Slow with 100k+ files    |
| SQLite     | Large datasets, exists() checks | `.db`     | 15x faster writes, ACID, no FS limits | Binary format            |

### Session Management (`core/session/`)

```python
from core.session import ResilientBrowserSession, HttpSession
from core.proxy import ProxyType

# Browser with proxy and auto-recovery
async with ResilientBrowserSession(proxy_types=[ProxyType.SMARTPROXY_SESSION]) as session:
    await session.login(url)
    response = await session.get("/api/data")
```

### Configuration (`core/config/`)

```python
from core.config import load_config, ProxySettings

config = load_config("sapphire", project_name="audiobee_bcbs_il")
proxy = ProxySettings()  # Auto-loads from .env
```

### Import Pattern (Backwards Compatibility)

```python
try:
    from core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
```

See `core/CLAUDE.md` for complete documentation.

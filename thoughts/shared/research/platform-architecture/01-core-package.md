---
date: 2026-01-11
type: research
scope: core-package
commit: 4b76867
parent: INDEX.md
---

# Core Package Deep Dive

Shared utilities package (v3.0) providing foundation for all 95+ scraper projects.

## Overview

```
core/
├── __init__.py              # Public API (v3.0.0)
├── exceptions.py            # 4-class hierarchy
├── config/                  # Pydantic Settings
├── io/                      # DataStore abstraction
├── logging/                 # Loguru-based
├── proxy/                   # Multi-provider orchestration
├── session/                 # Browser/HTTP management
├── mapper/                  # Normalization utilities
├── qa/                      # Validation, comparison
└── validation/              # Pydantic models
```

## Public API Exports

From `core/__init__.py:23-110`:

```python
# Configuration
from .config import (
    load_config,          # Factory function
    BaseConfig,           # Base class with SCRAPER_* prefix
    ProxySettings,        # SecretStr credentials
    SapphireConfig,       # ProviderFinderOnline
    HealthsparqConfig,    # Browser automation
    CarrierConfig,        # API-based
    AnthemConfig,         # Wellpoint
    CONFIG_TYPES,         # Registry mapping
)

# Exceptions
from .exceptions import (
    SharedPackageError,   # Base exception
    SessionError,         # Session issues
    ProxyError,           # Proxy issues
    ConfigError,          # Configuration issues
)

# Mapper utilities (optional import)
from .mapper import (
    MapperFunc,                    # Type alias
    BaseMapper,                    # Abstract base
    HealthSparqMapper,             # Default implementation
    normalize_zip_code,            # 5-digit ZIP
    normalize_phone,               # Digits only
    normalize_gender,              # M/F/O
    build_address_string,          # Deterministic format
    clean_network_name,            # Remove quotes/backslashes
    deduplicate_by_npi,            # NPI-based grouping
    merge_provider_records,        # Union merging
    merge_provider_records_inplace,
    validate_record,               # Schema validation
    validate_batch,                # Batch validation
    load_schema,                   # Load JSON schema
)
```

---

## Configuration System (`config/`)

### Architecture

```
BaseConfig (SCRAPER_* env prefix, .env hierarchy)
    ├── SapphireConfig (network_id, search_radius, geo_strategy)
    ├── HealthsparqConfig (server_host/port, timeouts, v2_enabled)
    ├── CarrierConfig (api_base_url, max_concurrent)
    └── AnthemConfig (brand, camoufox, max_workers)
```

### Key Files

| File | Purpose | Key Exports |
|------|---------|-------------|
| `base.py:42-161` | Base configuration | `BaseConfig` |
| `factory.py:18-50` | Factory function | `load_config()` |
| `registry.py` | Site-type mapping | `CONFIG_TYPES` |
| `proxy.py` | Proxy credentials | `ProxySettings` |

### Usage Pattern

```python
from core.config import load_config, BaseConfig

# Factory function (recommended)
config = load_config("sapphire", project_name="audiobee_bcbs_il")

# Direct instantiation
config = SapphireConfig()  # Loads from SCRAPER_* env vars

# Access fields
print(config.project_name)     # From SCRAPER_PROJECT_NAME
print(config.output_dir)       # Path(curr_date)
print(config.proxy.proxy_types) # From PROXY_TYPES
```

### Environment Hierarchy

Precedence (highest to lowest):
1. Explicit constructor values
2. Environment variables (`SCRAPER_*`)
3. Project-level `.env` file
4. Parent directory `.env` files (walks up tree)
5. Pydantic Field defaults

From `base.py:22-39`:
```python
def find_env_files_hierarchy(start_path: Path | None = None) -> list[Path]:
    """Walk up directory tree to find all .env files."""
    env_files = []
    current = (start_path or Path.cwd()).resolve()
    while current != current.parent:
        env_file = current / ".env"
        if env_file.exists():
            env_files.append(env_file)
        current = current.parent
    return env_files
```

---

## DataStore Abstraction (`io/`)

### Protocol

From `io/base.py`:

```python
class DataStore(Protocol):
    def put(path: str, record: dict) -> None     # Store
    def get(path: str) -> dict | None            # Retrieve
    def exists(path: str) -> bool                # Check (optimized)
    def keys(pattern: str) -> Iterator[str]      # Glob matching
    def __iter__() -> Iterator[tuple[str, dict]] # All records
    def __len__() -> int                         # Count
    def flush() -> None                          # Force persist
    def close() -> None                          # Release resources
```

### Backend Types

| Backend | Extension | Best For | exists() | Writes |
|---------|-----------|----------|----------|--------|
| SQLite | `.db` | Large datasets (100k+) | O(log n) | 15x faster |
| JSON Files | `/` directory | Debugging | O(1) fs | Individual |
| JSONL | `.jsonl` | Streaming | O(1) set | Sequential |

### Factory Function

From `io/factory.py:24-86`:

```python
from core.io import create_store, BackendType

# Auto-detect from extension
store = create_store("data.jsonl")   # JSONL
store = create_store("data.db")      # SQLite
store = create_store("data/")        # JSON Files

# Explicit backend
store = create_store("data", backend=BackendType.SQLITE)

# Context manager (auto-flush/close)
with create_store("data.db") as store:
    store.put("providers/123.json", {"npi": "123"})
```

### Implementation Details

**SQLiteStore** (`io/sqlite_fs.py:50-100`):
- Buffered writes (100 record batches)
- 15x faster than per-write commits
- ACID transactions

**JSONLStore** (`io/jsonl.py`):
- BoundedSet deduplication (100k LRU)
- Append-only writes
- Skip duplicates by path

**JSONFileStore** (`io/json_files.py`):
- Individual JSON files
- Direct filesystem mapping
- Human-readable output

---

## Session Management (`session/`)

### Architecture

```
ResilientBrowserSession (auto-recovery, generation tracking)
         │
         └─► BrowserSession (Patchright/Playwright/Camoufox)
                    │
                    └─► HttpSession (curl_cffi, browser impersonation)
```

### Key Files

| File | Purpose | Key Class |
|------|---------|-----------|
| `browser_session.py:100-150` | Browser automation | `BrowserSession` |
| `http_session.py:150-200` | HTTP client | `HttpSession` |
| `resilient_session.py:100-150` | Auto-recovery | `ResilientBrowserSession` |
| `backend.py` | Backend enum | `BrowserType` |

### Browser Backends

```python
from core.session import BrowserSession, BrowserType

# Patchright (default) - anti-detection Chromium
session = BrowserSession()

# Playwright - standard Chromium
session = BrowserSession(browser_type=BrowserType.PLAYWRIGHT)

# Camoufox - Firefox-based, highest anti-detection
session = BrowserSession(browser_type=BrowserType.CAMOUFOX)
```

| Backend | Engine | Anti-Detection | Use Case |
|---------|--------|----------------|----------|
| PATCHRIGHT | Chromium | Medium | Default, most sites |
| PLAYWRIGHT | Chromium | Low | Sites without detection |
| CAMOUFOX | Firefox | High | Anti-bot protected |

### Cookie Transfer Pattern

From `http_session.py:150-200`:

```python
# 1. Login via browser
browser = BrowserSession(proxy_types=[ProxyType.SMARTPROXY_SESSION])
await browser.login("https://example.com")

# 2. Transfer to HTTP (10x faster API calls)
http = HttpSession()
await http.initialize_from_browser(
    browser_cookies=await browser.get_cookies(),
    user_agent=await browser.get_user_agent(),
    proxy_config=browser.proxy_config
)

# 3. Use HTTP for subsequent requests
response = await http.get("/api/data")
```

### Auto-Recovery (Resilient Session)

From `resilient_session.py:100-150`:

```python
SESSION_DEATH_PATTERNS = [
    "target page, context or browser has been closed",
    "browser has disconnected",
    "protocol error",
    "target crashed",
]

RECREATION_STATUS_CODES = {401, 403, 429, 202}
```

Features:
- Auto-recreates on session death
- Rotates proxy on blocks
- Tracks session generations for cleanup

---

## Proxy Orchestration (`proxy/`)

### Structure

```
proxy/
├── base.py              # ProxyType enum, ProxyConfig, BaseProxyProvider
├── manager.py           # ProxyManager (round-robin)
├── session_manager.py   # Sticky session pool
└── providers/
    ├── decodo_datacenter.py  # Static IPs (ports 10001-63000)
    ├── smartproxy.py         # Rotating & session residential
    ├── dataimpulse.py        # Rotating & session residential
    ├── surfshark.py          # VPN-based
    └── nordvpn.py            # VPN-based
```

### Proxy Types

| Tier | Type | Provider | Description |
|------|------|----------|-------------|
| 1 | `NONE` | - | No proxy |
| 2 | `DECODO_DC_STATIC` | DecodoDCProvider | Datacenter static IPs |
| 3 | `SURFSHARK` | SurfsharkProvider | VPN-based |
| 4 | `NORDVPN` | NordVPNProvider | VPN-based |
| 5 | `DATAIMPULSE_ROTATING` | DataImpulseRotatingProvider | New IP each request |
| 6 | `DATAIMPULSE_SESSION` | DataImpulseSessionProvider | Sticky IP |
| 7 | `SMARTPROXY_ROTATING` | SmartProxyRotatingProvider | New IP each request |
| 8 | `SMARTPROXY_SESSION` | SmartProxySessionProvider | Sticky IP |

### Distribution Pattern

From `manager.py`:
```python
# Round-robin by browser_id
proxy_type = types[browser_id % len(types)]
```

### Environment Variables

```bash
PROXY_TYPES=smartproxy_session,dataimpulse_rotating

# SmartProxy
SMARTPROXY_USERNAME=
SMARTPROXY_PASSWORD=
SMARTPROXY_HOST=gate.decodo.com

# DataImpulse
DATAIMPULSE_PROXY_HOST=gw.dataimpulse.com
DATAIMPULSE_PROXY_USERNAME=
DATAIMPULSE_PROXY_PASSWORD=

# Datacenter
DECODO_DC_USERNAME=
DECODO_DC_PASSWORD=
DECODO_DC_HOST=dc.decodo.com
```

---

## Mapper Utilities (`mapper/`)

### Type Definitions

From `mapper/base.py`:

```python
MapperFunc = Callable[[dict], dict]  # Raw → Normalized

@dataclass
class MapperResult:
    success: bool
    record: dict | None
    errors: list[str]
```

### Normalization Functions

From `mapper/normalize.py`:

| Function | Input | Output | Notes |
|----------|-------|--------|-------|
| `normalize_zip_code("12345-6789")` | 9-digit | "12345" | 5-digit only |
| `normalize_phone("(123) 456-7890")` | Formatted | "1234567890" | Digits only |
| `normalize_gender("Male")` | Various | "M" | M/F/O |
| `clean_network_name("\"Net\\work\"")` | Escaped | "Network" | Strip quotes |

### Deduplication

From `mapper/dedup.py`:

```python
# NPI-based grouping
records = deduplicate_by_npi(raw_records)

# Union merge (addresses, networks, etc.)
merge_provider_records_inplace(existing, new)
```

### Schema Validation

From `mapper/schema.py`:

```python
from core.mapper import validate_record, load_schema

schema = load_schema()  # core/data/output_json_schema.json
is_valid, errors = validate_record(record, schema)
```

---

## QA System (`qa/`)

### Operations

| Operation | Description | Performance |
|-----------|-------------|-------------|
| `validate` | Schema validation | fastjsonschema (100x) |
| `compare` | Cross-run diff | Polars (10x) |
| `sample` | Reservoir sampling | Memory-efficient |
| `report` | Excel state reports | xlsxwriter streaming |
| `debug` | Debug Excel reports | 12 detail sheets |

### CLI Usage

```bash
# Validation
python -m core.qa validate providers.jsonl

# Comparison
python -m core.qa compare --curr 20251227 --prev 20251126

# Sampling
python -m core.qa sample providers.jsonl --count 20

# Reports
python -m core.qa report audiobee_bcbs_il --curr 20251227

# Debug
python -m core.qa debug providers.jsonl --curr 20251227
```

### Library Usage

```python
from core.qa import validate, compare, sample, report

# Validate
result = validate("providers.jsonl", deduplicate=True)
print(f"Valid: {result.metrics.valid_records}")

# Compare
result = compare(curr_path="20251227/processed", prev_path="20251126/processed")
print(f"Added: {result.metrics.added}, Removed: {result.metrics.removed}")
```

---

## Logging System (`logging/`)

### Setup

From `logging/logger.py`:

```python
from core.logging import logger, setup_logging, set_trace_id

# Setup at startup
setup_logging(
    project_name="audiobee_bcbs_il",
    run_id="20251226",
    log_dir="logs",
    level="INFO",
)

# Request tracking
set_trace_id("provider_123")
logger.info("Fetching details")
logger.bind(npi="1234567890").info("Found")
```

### Log Format

```
2025-12-26 21:00:00.123 | INFO | audiobee_bcbs_il | 20251226 | provider_123 | module:func:45 | Message | 2.3s
```

### Features

- ContextVar for async-safe trace_id
- InterceptHandler routes stdlib to loguru
- Auto rotation (100 MB, 30 day retention)
- Rich context binding

---

## Exception Hierarchy

From `exceptions.py`:

```python
SharedPackageError         # Base
    ├── SessionError       # Session issues
    ├── ProxyError         # Proxy issues
    └── ConfigError        # Configuration issues
```

### Usage

```python
from core.exceptions import ConfigError

raise ConfigError(
    "Invalid site_type",
    field="site_type",
    context={"attempted_value": "unknown"}
)
```

---

## Related Documents

- [INDEX.md](./INDEX.md) - Navigation
- [04-patterns.md](./04-patterns.md) - Cross-cutting patterns
- [05-performance.md](./05-performance.md) - Performance optimizations

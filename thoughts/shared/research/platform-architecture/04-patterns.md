---
date: 2026-01-11
type: research
scope: patterns
commit: 4b76867
parent: INDEX.md
---

# Cross-Cutting Architecture Patterns

Design patterns shared across core, healthsparq, and sapphire.

## 1. Zero Global State

**Pattern**: All configuration injected via Pydantic Settings. No globals.

**Implementation**:
```python
# core/config/base.py
class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SCRAPER_",
        env_file=".env",
    )

    project_name: str
    site_type: str
    curr_date: str
```

**Benefits**:
- Testability: Easy to mock configuration
- Composability: Multiple configs in same process
- No hidden dependencies

**Where Used**:
- `core/__init__.py:23-32` - Config exports
- `healthsparq/api.py:57-76` - Config injection
- `sapphire/api.py:59-81` - Config injection

---

## 2. Protocol-Based Abstractions

**Pattern**: Define interfaces via Protocol, enable swappable implementations.

**Key Example - DataStore**:
```python
# core/io/base.py:36-50
class DataStore(Protocol):
    def put(path: str, record: dict) -> None
    def get(path: str) -> dict | None
    def exists(path: str) -> bool
    def keys(pattern: str) -> Iterator[str]
    def __iter__() -> Iterator[tuple[str, dict]]
```

**Implementations**:
- `JSONFileStore` - Individual JSON files
- `JSONLStore` - Line-delimited JSON
- `SQLiteStore` - SQLite database

**Benefits**:
- Switch storage without code changes (`--storage sqlite`)
- Test with mock implementations
- Performance optimization per use case

**Where Used**:
- `core/io/` - Storage abstraction
- `core/mapper/base.py` - MapperFunc type

---

## 3. Factory Pattern with Registry

**Pattern**: Factory function with type registry for extensibility.

**Configuration Factory**:
```python
# core/config/registry.py
CONFIG_TYPES = {
    "sapphire": SapphireConfig,
    "healthsparq": HealthsparqConfig,
    "carrier": CarrierConfig,
    "anthem": AnthemConfig,
}

# core/config/factory.py
def load_config(site_type: str, project_name: str) -> BaseConfig:
    config_class = CONFIG_TYPES[site_type]
    return config_class(site_type=site_type, project_name=project_name)
```

**Storage Factory**:
```python
# core/io/factory.py
def create_store(path: str, backend: BackendType = BackendType.AUTO) -> DataStore:
    if backend == BackendType.AUTO:
        backend = _detect_backend(path)
    return BACKENDS[backend](path)
```

**Benefits**:
- New types without modifying factory
- Type-safe via registry
- Auto-detection from conventions

**Where Used**:
- `core/config/factory.py:18-50` - Config factory
- `core/io/factory.py:24-86` - Storage factory

---

## 4. Mapper Injection

**Pattern**: Injectable transformation functions for data normalization.

**Type Definition**:
```python
MapperFunc = Callable[[dict], dict]  # Raw → Normalized
```

**HealthSparq - Factory Pattern**:
```python
# healthsparq/phases/normalize.py:450-500
def make_mapper(custom_logic: Callable | None = None) -> MapperFunc:
    def mapper(raw: dict) -> dict:
        result = default_mapper(raw)
        if custom_logic:
            result = custom_logic(result)
        return result
    return mapper
```

**Sapphire - Registry Pattern**:
```python
# sapphire/mappers/registry.py
_MAPPERS: dict[str, MapperFunc] = {}

def register_mapper(slug: str, mapper: MapperFunc) -> None:
    _MAPPERS[slug] = mapper

def get_mapper(slug: str) -> MapperFunc:
    return _MAPPERS.get(slug, default_sapphire_mapper)
```

**Benefits**:
- Project-specific normalization
- Extend default behavior
- No platform code changes needed

**Open Question**: Should these converge to a single pattern?

---

## 5. Graceful Degradation

**Pattern**: Optional imports with fallback implementations.

**Implementation**:
```python
# core/__init__.py:41-63
try:
    from .mapper import (
        MapperFunc, deduplicate_by_npi, ...
    )
    _MAPPER_AVAILABLE = True
except ImportError:
    _MAPPER_AVAILABLE = False
```

```python
# healthsparq/core/session.py
try:
    from core.session import HttpSession, ResilientBrowserSession, BrowserType
except ImportError:
    from shared_package.session import HttpSession, ResilientBrowserSession
    BrowserType = None  # Not available in legacy
```

**Benefits**:
- Works in partial environments
- Backward compatibility with legacy paths
- Clear import errors

**Where Used**:
- `core/__init__.py:41-63` - Mapper imports
- `healthsparq/core/session.py` - Session imports

---

## 6. Dual CLI + Library Interface

**Pattern**: Same code usable as CLI tool and importable library.

**CLI Entry**:
```bash
python -m healthsparq run christus_health_plan --curr 20251230
```

**Library Entry**:
```python
from healthsparq import run_scraper_sync, load_config

config = load_config("christus_health_plan")
result = run_scraper_sync(config, curr_date="20251230")
```

**Thin Wrapper Factory**:
```python
# healthsparq/cli.py
def create_project_cli(
    project_dir: Path,
    mapper: MapperFunc | None = None,
) -> typer.Typer:
    """Factory for project-specific CLI."""
    app = typer.Typer()
    # Register standard commands
    return app
```

**Benefits**:
- Flexible usage patterns
- Programmatic control for automation
- REPL-friendly for debugging

**Where Used**:
- `healthsparq/cli.py` - CLI + factory
- `healthsparq/api.py` - Library API
- `sapphire/cli.py` - CLI
- `sapphire/api.py` - Library API

---

## 7. Browser → HTTP Transfer

**Pattern**: Login via browser for anti-bot, transfer to HTTP for performance.

**Flow**:
```python
# 1. Browser login (anti-bot handled)
browser = BrowserSession(proxy_types=[ProxyType.SMARTPROXY_SESSION])
await browser.login("https://example.com")

# 2. Extract session state
cookies = await browser.get_cookies()
user_agent = await browser.get_user_agent()

# 3. Transfer to lightweight HTTP
http = HttpSession()
await http.initialize_from_browser(
    browser_cookies=cookies,
    user_agent=user_agent,
    proxy_config=browser.proxy_config
)

# 4. Fast API calls (10x speedup)
response = await http.get("/api/data")
```

**Benefits**:
- Anti-bot protection via browser
- 10x API call performance via HTTP
- Same proxy configuration

**Where Used**:
- `core/session/http_session.py:150-200` - Cookie transfer
- `healthsparq/core/session.py` - Two-step pattern

---

## 8. Phase Pipeline Architecture

**Pattern**: Sequential phases with typed results and granular control.

**Phase Structure**:
```python
# Each phase returns typed result
@dataclass
class PhaseResult:
    phase: int
    success: bool
    message: str
    data: dict[str, Any]
    duration_seconds: float

# Pipeline orchestration
def run_scraper_sync(
    config: Config,
    phases: set[int] | None = None,  # e.g., {1, 2, 3}
) -> ScraperResult:
    for phase_num in sorted(phases):
        result = run_phase(phase_num, config)
        results[phase_num] = result
```

**Granular Control**:
```bash
--phase 2           # Single phase
-p 2,3,5            # Multiple phases
-p 2-5              # Range
--from-phase 2      # From phase onwards
--skip-phase 1      # Skip phase
```

**Benefits**:
- Resume from any phase
- Skip expensive phases during debugging
- Compose pipelines programmatically

**Where Used**:
- `healthsparq/api.py:57-174` - 6-phase pipeline
- `sapphire/api.py:59-103` - 5-phase pipeline

---

## 9. YAML + Pydantic Configuration

**Pattern**: YAML files validated by Pydantic models with base inheritance.

**YAML with Inheritance (Sapphire)**:
```yaml
# configs/_base.yaml
geo:
  strategy: dual
  radii_miles:
    small: [25, 50]

# configs/molina.yaml (inherits from _base)
project:
  name: "Molina"
  slug: molina
```

**Pydantic Validation**:
```python
class ProjectConfig(BaseModel):
    project: ProjectInfo
    site: SiteConfig
    coverage: CoverageConfig

# Load and validate
def load_config(slug: str) -> ProjectConfig:
    data = yaml.safe_load(config_file.read_text())
    return ProjectConfig(**data)  # Validates on instantiation
```

**Benefits**:
- Type-safe configuration
- Clear error messages on invalid config
- IDE autocomplete via Pydantic

**Where Used**:
- `healthsparq/config/schema.py` - HealthSparqProjectConfig
- `sapphire/config/schema.py` - SapphireProjectConfig

---

## 10. Memory-Safe Collections

**Pattern**: Bounded data structures to prevent memory exhaustion.

**BoundedSet**:
```python
# core/io/jsonl.py:150-200
class BoundedSet:
    """OrderedDict-based LRU set with max_size eviction."""
    def __init__(self, max_size: int = 100_000):
        self._data = OrderedDict()
        self._max_size = max_size

    def add(self, item):
        if item in self._data:
            self._data.move_to_end(item)  # Update LRU
        else:
            self._data[item] = None
            if len(self._data) > self._max_size:
                self._data.popitem(last=False)  # Evict oldest
```

**SQLite Staging**:
```python
# For very large datasets, use SQLite instead of in-memory
store = create_store("data.db", backend=BackendType.SQLITE)
# Disk-based, no memory limits
```

**Benefits**:
- Predictable memory usage
- No OOM on large datasets
- LRU eviction preserves recent items

**Where Used**:
- `core/io/jsonl.py:150-200` - BoundedSet
- `healthsparq/phases/normalize.py:80-120` - SQLite NPI map

---

## Pattern Summary

| # | Pattern | Purpose | Location |
|---|---------|---------|----------|
| 1 | Zero Global State | Testability | core/config/ |
| 2 | Protocol Abstractions | Swappable implementations | core/io/base.py |
| 3 | Factory + Registry | Extensibility | core/config/factory.py |
| 4 | Mapper Injection | Custom normalization | phases/normalize.py |
| 5 | Graceful Degradation | Partial environments | core/__init__.py |
| 6 | Dual Interface | CLI + Library | api.py, cli.py |
| 7 | Browser → HTTP | Performance | core/session/ |
| 8 | Phase Pipeline | Granular control | api.py |
| 9 | YAML + Pydantic | Type-safe config | config/schema.py |
| 10 | Bounded Collections | Memory safety | core/io/jsonl.py |

---

## Related Documents

- [INDEX.md](./INDEX.md) - Navigation
- [01-core-package.md](./01-core-package.md) - Core implementation
- [05-performance.md](./05-performance.md) - Performance patterns

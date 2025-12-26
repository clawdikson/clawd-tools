# Shared Package Architecture Specification

**Version**: 1.0
**Status**: Draft
**Based on**: `audiobee_bluecard_national/shared_package/` (most complete implementation)

---

## Overview

The `shared_package` is a Python package providing common utilities for all 95+ scraper projects. It will be installed as a workspace dependency via UV.

---

## Package Structure

```
shared_package/
├── pyproject.toml              # Package configuration
├── src/
│   └── shared_package/
│       ├── __init__.py         # Package exports
│       │
│       ├── config/             # Configuration management
│       │   ├── __init__.py     # Exports: BaseConfig, load_config
│       │   ├── base.py         # BaseConfig (Pydantic Settings)
│       │   ├── proxy.py        # ProxyConfig
│       │   ├── sapphire.py     # SapphireConfig
│       │   ├── healthsparq.py  # HealthsparqConfig
│       │   ├── carrier.py      # CarrierConfig
│       │   ├── anthem.py       # AnthemConfig
│       │   └── factory.py      # load_config() factory function
│       │
│       ├── session/            # HTTP/Browser sessions
│       │   ├── __init__.py     # Exports: BrowserSession, HttpSession, ResilientBrowserSession
│       │   ├── browser_session.py    # Patchright-based browser
│       │   ├── http_session.py       # curl_cffi HTTP client
│       │   └── resilient_session.py  # Auto-recovery wrapper
│       │
│       ├── proxy/              # Proxy management
│       │   ├── __init__.py     # Exports: ProxyManager, ProxyType, ProxyConfig
│       │   ├── base.py         # ProxyType enum, ProxyConfig dataclass
│       │   ├── manager.py      # ProxyManager (round-robin, tier selection)
│       │   ├── session_manager.py    # Sticky session pool
│       │   └── providers/      # Provider implementations
│       │       ├── __init__.py
│       │       ├── dataimpulse.py
│       │       ├── smartproxy.py
│       │       ├── surfshark.py
│       │       ├── nordvpn.py
│       │       └── decodo_datacenter.py
│       │
│       ├── io/                 # File I/O utilities
│       │   ├── __init__.py     # Exports: JSONLReader, JSONLWriter
│       │   ├── jsonl.py        # JSONL read/write with orjson
│       │   └── file_manager.py # AtomicWriter, directory utils
│       │
│       ├── logging/            # Centralized logging
│       │   ├── __init__.py     # Exports: setup_logging, get_logger
│       │   └── logger.py       # Loguru configuration
│       │
│       ├── queue/              # Task queue management
│       │   ├── __init__.py     # Exports: TaskQueue, Task
│       │   └── task_queue.py   # asyncio.Queue implementation
│       │
│       ├── validation/         # Data validation
│       │   ├── __init__.py
│       │   └── schema.py       # Pydantic models for provider data
│       │
│       └── localdataclass/     # Response objects (backward compat)
│           ├── __init__.py
│           └── response.py     # Response dataclass
```

---

## Module Specifications

### 1. config/ - Configuration Management

#### base.py

```python
"""Base configuration using Pydantic Settings v2."""

from datetime import datetime
from pathlib import Path
from typing import ClassVar, Dict, List, Literal, Optional

from pydantic import Field, SecretStr, computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    """
    Base configuration for all scraper projects.

    Features:
    - Multi-file .env loading (project → parent → root)
    - Environment variable override with SCRAPER_ prefix
    - Automatic validation of dates, states
    - Computed DIRS from curr_date
    - SecretStr for sensitive values

    Environment Variable Precedence:
    1. Explicit constructor arguments
    2. Environment variables (SCRAPER_*)
    3. .env in current directory
    4. .env in parent directories
    5. Field defaults

    Usage:
        # Direct instantiation
        config = BaseConfig(
            project_name="audiobee_bcbs_il",
            prev_date="20251110",
            curr_date="20251210",
        )

        # From environment
        # SCRAPER_PREV_DATE=20251110 SCRAPER_CURR_DATE=20251210 python main.py

        # Via factory (recommended)
        from shared_package.config import load_config
        config = load_config("sapphire", "audiobee_bcbs_il")
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        env_prefix="SCRAPER_",
        case_sensitive=False,
        extra="ignore",
    )

    # Class-level constants (override in subclass)
    site_type: ClassVar[str] = "base"

    # Project identification
    project_name: str = Field(description="Project identifier (e.g., audiobee_bcbs_il)")

    # Date management
    prev_date: str = Field(description="Previous run date (YYYYMMDD)")
    curr_date: str = Field(description="Current run date (YYYYMMDD)")

    # Geographic configuration
    req_states: List[str] = Field(default_factory=list, description="Target states")
    req_states_only: List[str] = Field(default_factory=list, description="Strict state filter")

    # Concurrency
    batch_size: int = Field(default=100, ge=1, le=10000)
    max_concurrent: int = Field(default=10, ge=1, le=100)
    max_retries: int = Field(default=3, ge=0, le=10)

    # Rate limiting
    request_delay_min: float = Field(default=0.5, ge=0)
    request_delay_max: float = Field(default=2.0, ge=0)

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    log_to_file: bool = Field(default=True)

    # Debug
    debug: bool = Field(default=False)

    @field_validator("prev_date", "curr_date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Validate YYYYMMDD format."""
        if len(v) != 8 or not v.isdigit():
            raise ValueError(f"Date must be YYYYMMDD format, got: {v}")
        try:
            datetime.strptime(v, "%Y%m%d")
        except ValueError:
            raise ValueError(f"Invalid date: {v}")
        return v

    @field_validator("req_states", "req_states_only", mode="before")
    @classmethod
    def parse_states(cls, v):
        """Accept comma-separated string or list."""
        if isinstance(v, str):
            return [s.strip().upper() for s in v.split(",") if s.strip()]
        return [s.upper() for s in v] if v else []

    @model_validator(mode="after")
    def validate_date_order(self) -> "BaseConfig":
        """Ensure prev_date <= curr_date."""
        if self.prev_date > self.curr_date:
            raise ValueError(
                f"prev_date ({self.prev_date}) must be <= curr_date ({self.curr_date})"
            )
        return self

    @computed_field
    @property
    def dirs(self) -> Dict[str, Path]:
        """Compute directory structure from curr_date."""
        base = Path(self.curr_date)
        return {
            "raw": base / "raw",
            "search_results": base / "raw" / "search_results",
            "provider_details": base / "raw" / "provider_details",
            "locations": base / "raw" / "locations",
            "affiliations": base / "raw" / "affiliations",
            "networks": base / "raw" / "networks",
            "processed": base / "processed",
            "logs": Path("logs"),
        }

    @computed_field
    @property
    def prev_dirs(self) -> Dict[str, Path]:
        """Compute directory structure from prev_date."""
        base = Path(self.prev_date)
        return {
            "raw": base / "raw",
            "search_results": base / "raw" / "search_results",
            "provider_details": base / "raw" / "provider_details",
            "processed": base / "processed",
        }

    def ensure_dirs(self) -> None:
        """Create all required directories."""
        for dir_path in self.dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)

    def get_output_path(self, filename: str) -> Path:
        """Get full path for output file in processed directory."""
        return self.dirs["processed"] / filename
```

#### proxy.py

```python
"""Proxy configuration with Pydantic validation."""

from typing import Optional
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProxySettings(BaseSettings):
    """
    Proxy credentials configuration.

    Loads from environment variables with PROXY_ prefix.
    Uses SecretStr to prevent credential logging.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_prefix="PROXY_",
        extra="ignore",
    )

    # NordVPN
    nord_username: SecretStr = Field(default=SecretStr(""))
    nord_password: SecretStr = Field(default=SecretStr(""))

    # Surfshark
    surfshark_username: SecretStr = Field(default=SecretStr(""))
    surfshark_password: SecretStr = Field(default=SecretStr(""))

    # DataImpulse
    dataimpulse_server: str = Field(default="http://gw.dataimpulse.com:823")
    dataimpulse_username: SecretStr = Field(default=SecretStr(""))
    dataimpulse_password: SecretStr = Field(default=SecretStr(""))
    dataimpulse_port_min: int = Field(default=823)
    dataimpulse_port_max: int = Field(default=9999)

    # SmartProxy
    smartproxy_host: str = Field(default="us.smartproxy.net")
    smartproxy_port: int = Field(default=3120)
    smartproxy_username: SecretStr = Field(default=SecretStr(""))
    smartproxy_password: SecretStr = Field(default=SecretStr(""))
    smartproxy_session_lifetime: int = Field(default=10)
    smartproxy_pool_size: int = Field(default=10)

    # Decodo Datacenter
    decodo_dc_host: str = Field(default="")
    decodo_dc_username: SecretStr = Field(default=SecretStr(""))
    decodo_dc_password: SecretStr = Field(default=SecretStr(""))

    def has_nord(self) -> bool:
        return bool(self.nord_username.get_secret_value())

    def has_surfshark(self) -> bool:
        return bool(self.surfshark_username.get_secret_value())

    def has_dataimpulse(self) -> bool:
        return bool(self.dataimpulse_username.get_secret_value())

    def has_smartproxy(self) -> bool:
        return bool(self.smartproxy_username.get_secret_value())

    def get_available_types(self) -> list[str]:
        """Get list of configured proxy types."""
        available = []
        if self.has_nord():
            available.append("nordvpn")
        if self.has_surfshark():
            available.append("surfshark")
        if self.has_dataimpulse():
            available.extend(["dataimpulse_rotating", "dataimpulse_session"])
        if self.has_smartproxy():
            available.extend(["smartproxy_rotating", "smartproxy_session"])
        return available


# Singleton instance
_proxy_settings: Optional[ProxySettings] = None


def get_proxy_settings() -> ProxySettings:
    """Get cached proxy settings instance."""
    global _proxy_settings
    if _proxy_settings is None:
        _proxy_settings = ProxySettings()
    return _proxy_settings
```

#### factory.py

```python
"""Configuration factory function."""

from typing import Any, Dict, Optional, Type

from .base import BaseConfig
from .sapphire import SapphireConfig
from .healthsparq import HealthsparqConfig
from .carrier import CarrierConfig
from .anthem import AnthemConfig


CONFIG_REGISTRY: Dict[str, Type[BaseConfig]] = {
    "base": BaseConfig,
    "sapphire": SapphireConfig,
    "healthsparq": HealthsparqConfig,
    "carrier": CarrierConfig,
    "anthem": AnthemConfig,
}


def load_config(
    site_type: str,
    project_name: str,
    *,
    curr_date: Optional[str] = None,
    prev_date: Optional[str] = None,
    **overrides: Any,
) -> BaseConfig:
    """
    Factory function to load configuration.

    Args:
        site_type: "sapphire", "healthsparq", "carrier", "anthem", or "base"
        project_name: Project identifier (e.g., "audiobee_bcbs_il")
        curr_date: Override current date (optional)
        prev_date: Override previous date (optional)
        **overrides: Additional config values

    Returns:
        Configured BaseConfig subclass instance

    Example:
        config = load_config(
            "sapphire",
            "audiobee_bcbs_il",
            curr_date="20251210",
            network_id="210002020",
        )
    """
    config_class = CONFIG_REGISTRY.get(site_type.lower())
    if not config_class:
        raise ValueError(
            f"Unknown site_type: {site_type}. "
            f"Available: {list(CONFIG_REGISTRY.keys())}"
        )

    values = {"project_name": project_name}

    if curr_date:
        values["curr_date"] = curr_date
    if prev_date:
        values["prev_date"] = prev_date

    values.update(overrides)

    return config_class(**values)
```

---

### 2. session/ - HTTP/Browser Sessions

#### browser_session.py

Key features (from `audiobee_bluecard_national/shared_package/session/browser_session.py`):

- Patchright (Playwright fork) for anti-detection
- Proxy integration via ProxyManager
- Semaphore for concurrent request limiting
- Lazy initialization with `_ensure_initialized()`
- Thread-safe state management with locks
- Graceful close with in-flight operation tracking
- HTTP methods: `login()`, `get()`, `post()`
- Cookie/UA extraction for HttpSession transfer

#### resilient_session.py

Key features:

- Drop-in replacement for BrowserSession
- Auto-recreation on:
    - HTTP 202, 401, 403, 429 responses
    - Browser crashes
    - Session timeouts
- Concurrency-safe with `asyncio.Lock`
- Session versioning for tracking
- Exponential backoff on failures

---

### 3. proxy/ - Proxy Management

#### base.py - ProxyType Enum

```python
class ProxyType(Enum):
    """
    Supported proxy types organized by tier.

    Tier Selection Guide:
    - Tier 1 (NONE): Testing only
    - Tier 2 (DECODO_DC_STATIC): Basic API scraping, low detection risk
    - Tier 3-4 (VPN): Medium protection, good for healthsparq
    - Tier 5-6 (DATAIMPULSE): High protection, rotating/session
    - Tier 7-8 (SMARTPROXY): Premium protection, anti-bot sites
    """
    NONE = "none"
    DECODO_DC_STATIC = "decodo_dc_static"
    SURFSHARK = "surfshark"
    NORDVPN = "nordvpn"
    DATAIMPULSE_ROTATING = "dataimpulse_rotating"
    DATAIMPULSE_SESSION = "dataimpulse_session"
    SMARTPROXY_ROTATING = "smartproxy_rotating"
    SMARTPROXY_SESSION = "smartproxy_session"
```

#### manager.py - ProxyManager

Key features:

- Multi-tier proxy selection
- Round-robin within tier
- Blocked proxy tracking
- Browser ID → proxy mapping
- Automatic failover

---

### 4. io/ - File I/O

#### jsonl.py

```python
"""Thread-safe JSONL utilities using orjson."""

from pathlib import Path
from typing import Any, Iterator
import orjson


class JSONLWriter:
    """
    Thread-safe JSONL writer with atomic operations.

    Usage:
        with JSONLWriter("output.jsonl") as writer:
            writer.write({"npi": "123", "name": "John"})
            writer.write_many(records)
    """

    def __init__(self, path: Path | str, append: bool = False):
        self.path = Path(path)
        self.mode = "ab" if append else "wb"
        self._file = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self.path, self.mode)
        return self

    def __exit__(self, *args):
        if self._file:
            self._file.close()

    def write(self, record: dict[str, Any]) -> None:
        """Write a single record."""
        self._file.write(orjson.dumps(record) + b"\n")

    def write_many(self, records: list[dict[str, Any]]) -> None:
        """Write multiple records."""
        for record in records:
            self.write(record)


class JSONLReader:
    """
    Memory-efficient JSONL reader with streaming.

    Usage:
        for record in JSONLReader("input.jsonl"):
            process(record)
    """

    def __init__(self, path: Path | str):
        self.path = Path(path)

    def __iter__(self) -> Iterator[dict[str, Any]]:
        with open(self.path, "rb") as f:
            for line in f:
                if line.strip():
                    yield orjson.loads(line)

    def read_all(self) -> list[dict[str, Any]]:
        """Read all records into memory."""
        return list(self)

    def count(self) -> int:
        """Count records without loading all into memory."""
        return sum(1 for _ in self)
```

---

### 5. logging/ - Centralized Logging

#### logger.py

```python
"""Loguru-based logging configuration."""

import sys
from pathlib import Path
from loguru import logger


def setup_logging(
    project_name: str,
    log_level: str = "INFO",
    log_dir: Path | str = "logs",
    log_to_file: bool = True,
) -> None:
    """
    Configure loguru for a scraper project.

    Args:
        project_name: Project identifier for log files
        log_level: Minimum log level
        log_dir: Directory for log files
        log_to_file: Whether to write to files
    """
    # Remove default handler
    logger.remove()

    # Console handler (colored)
    logger.add(
        sys.stderr,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[phase]:-^10}</cyan> | "
            "{message}"
        ),
        level=log_level,
        colorize=True,
    )

    if log_to_file:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # Daily log file
        logger.add(
            log_path / f"{project_name}_{{time:YYYYMMDD}}.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
            level="DEBUG",
            rotation="00:00",
            retention="30 days",
            compression="gz",
            enqueue=True,
        )

        # Error-only file
        logger.add(
            log_path / f"{project_name}_errors.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}\n{exception}",
            level="ERROR",
            rotation="1 week",
            retention="3 months",
        )


def get_logger(phase: str = "main"):
    """Get logger with phase context."""
    return logger.bind(phase=phase)
```

---

## pyproject.toml

```toml
[project]
name = "shared-package"
version = "0.1.0"
description = "Shared utilities for Ideon scraping projects"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "python-dotenv>=1.0.0",
    "loguru>=0.7.0",
    "orjson>=3.9.0",
    "httpx>=0.27.0",
    "curl-cffi>=0.7.0",
    "patchright>=1.0.0",
    "tenacity>=8.0.0",
    "tqdm>=4.66.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/shared_package"]
```

---

## Usage Examples

### Basic Configuration

```python
# audiobee_bcbs_il/config.py
from shared_package.config import load_config

config = load_config(
    "sapphire",
    "audiobee_bcbs_il",
    network_id="210002020",
    geo_coords="39.883875,-88.834467",
    radius=210,
    req_states=["IL"],
)

# Backward compatibility exports
PREV_DATE = config.prev_date
CURR_DATE = config.curr_date
PROJECT_NAME = config.project_name
DIRS = {k: str(v) for k, v in config.dirs.items()}

# Setup directories
config.ensure_dirs()
```

### Browser Session with Proxy

```python
from shared_package.session import ResilientBrowserSession
from shared_package.proxy import ProxyType

async def scrape():
    async with ResilientBrowserSession(
        proxy_types=[ProxyType.DATAIMPULSE_SESSION],
        max_concurrent_requests=5,
    ) as session:
        response = await session.get(url, params=params)
        return response.json()
```

### Logging

```python
from shared_package.logging import setup_logging, get_logger

setup_logging("audiobee_bcbs_il", log_level="DEBUG")
logger = get_logger("search")

logger.info("Starting search phase", total_zips=1000)
```

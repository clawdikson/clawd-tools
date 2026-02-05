# Project Migration Guide

**Purpose**: Step-by-step instructions for migrating existing scrapers to the new architecture
**Audience**: Developers migrating `audiobee_*` projects
**Prerequisites**: Read [RESTRUCTURING_PLAN.md](./RESTRUCTURING_PLAN.md) and [SHARED_PACKAGE_SPEC.md](./SHARED_PACKAGE_SPEC.md)

---

## Migration Overview

### Before Migration

```
audiobee_bcbs_il/
├── config.py              # Hardcoded dates, raw os.getenv()
├── index_1.py             # Search logic
├── index_2.py             # Detail extraction
├── index_3.py             # Normalization
├── run_all.py             # Simple orchestrator
├── 20251210/              # Date-versioned output
│   ├── raw/
│   └── processed/
└── (no .env)              # Uses root .env via CWD
```

### After Migration

```
audiobee_bcbs_il/
├── config.py              # Inherits from BaseConfig, typed, validated
├── .env                   # Project-specific overrides (optional)
├── logs/                  # Centralized logs
├── scraper/
│   ├── __init__.py
│   ├── main.py            # Entry point
│   ├── service/
│   │   ├── __init__.py
│   │   ├── search.py      # Phase 1 logic
│   │   ├── details.py     # Phase 2 logic
│   │   └── normalize.py   # Phase 3 logic
│   └── infrastructure/
│       ├── __init__.py
│       └── api_client.py  # Project-specific HTTP client
├── pipeline/              # Optional task queue
│   ├── __init__.py
│   └── task_queue.py
├── run_all.py             # Typer CLI with progress tracking
├── mapper.py              # Data normalization mappings
└── 20251210/
    ├── raw/
    └── processed/
```

---

## Migration Levels

Choose your migration level based on project needs:

| Level       | Scope            | Effort    | Benefits                              |
| ----------- | ---------------- | --------- | ------------------------------------- |
| **Level 1** | Config only      | 15 min    | Validated config, proper .env loading |
| **Level 2** | + Logging        | 30 min    | Centralized logs, no more print()     |
| **Level 3** | + Sessions       | 1 hour    | Shared proxy/session management       |
| **Level 4** | Full restructure | 2-4 hours | Complete new architecture             |

**Recommendation**: Start with Level 1 for all projects, then Level 2-3 as needed.

---

## Level 1: Configuration Migration

### Step 1.1: Ensure Root .env Exists

```bash
# From scraping/ root
cp .env.example .env

# Edit with your credentials
nano .env
```

Verify required variables are set:

```bash
grep -E "^PROXY_NORD|^PROXY_SURFSHARK|^SCRAPER_" .env
```

### Step 1.2: Update config.py

**Before (Legacy):**

```python
# audiobee_bcbs_il/config.py
import os

PREV_DATE = "20251110"
CURR_DATE = "20251210"
PROJECT_NAME = "audiobee_bcbs_il"

DIRS = {
    "raw": os.path.join(CURR_DATE, "raw"),
    "search_results": os.path.join(CURR_DATE, "raw", "search_results"),
    "provider_details": os.path.join(CURR_DATE, "raw", "provider_details"),
    "processed": os.path.join(CURR_DATE, "processed"),
}

BASE_URLS = {
    "search": "https://providerfinderonline.com/api/search",
    "details": "https://providerfinderonline.com/api/provider",
}

HEADERS = {
    "x-api-key": "03220e47-16eb-44d3-b1ca-4e3641973a97",  # HARDCODED!
}

NETWORK_ID = "210002020"
REQ_STATES = ["IL", "IN", "WI"]
```

**After (Migrated):**

```python
# audiobee_bcbs_il/config.py
"""
Configuration for audiobee_bcbs_il scraper.

Uses shared_package for validated configuration loading.
Environment variables override defaults (see .env.example).
"""
from shared_package.config import load_config
from shared_package.config.sapphire import SapphireConfig

# Load validated configuration
config = load_config(
    site_type="sapphire",
    project_name="audiobee_bcbs_il",
    network_id="210002020",
)

# Backward compatibility exports (for existing index_*.py files)
PREV_DATE = config.prev_date
CURR_DATE = config.curr_date
PROJECT_NAME = config.project_name
DIRS = config.dirs
BASE_URLS = config.urls
HEADERS = config.headers
NETWORK_ID = config.network_id
REQ_STATES = config.req_states or ["IL", "IN", "WI"]

# Ensure directories exist
config.ensure_dirs()
```

### Step 1.3: Create Project .env (Optional)

Only needed if overriding root values:

```bash
# audiobee_bcbs_il/.env
SCRAPER_PROJECT_NAME=audiobee_bcbs_il
SCRAPER_PREV_DATE=20251125
SCRAPER_CURR_DATE=20251226

# Project-specific API key (if different from root)
SAPPHIRE_API_KEY=bcbs_il_specific_api_key

# State restrictions
SCRAPER_REQ_STATES=IL,IN,WI
```

### Step 1.4: Verify Migration

```bash
cd audiobee_bcbs_il

# Test config loading
python -c "
from config import config, PREV_DATE, CURR_DATE, DIRS
print(f'Project: {config.project_name}')
print(f'Dates: {PREV_DATE} -> {CURR_DATE}')
print(f'Dirs: {list(DIRS.keys())}')
print(f'API Key: {config.api_key[:8]}...' if config.api_key else 'No API key')
"
```

Expected output:

```
Project: audiobee_bcbs_il
Dates: 20251125 -> 20251226
Dirs: ['raw', 'search_results', 'provider_details', 'processed']
API Key: bcbs_il_...
```

---

## Level 2: Logging Migration

### Step 2.1: Update Imports

**Before:**

```python
# index_1.py
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Or worse...
print(f"Processing {len(items)} items")
```

**After:**

```python
# index_1.py
from shared_package.logging import get_logger

logger = get_logger(__name__)

# All print() replaced with logger calls
logger.info(f"Processing {len(items)} items")
logger.debug(f"Item details: {item}")
logger.error(f"Failed to fetch: {e}")
```

### Step 2.2: Search and Replace

```bash
# Find all print statements in project
grep -rn "print(" *.py

# Common replacements:
# print(f"...")  →  logger.info(f"...")
# print("Error: ...")  →  logger.error(f"...")
# print("Debug: ...")  →  logger.debug(f"...")
```

### Step 2.3: Create logs/ Directory

```bash
mkdir -p logs
echo "*.log" >> .gitignore
```

### Step 2.4: Update run_all.py

```python
# run_all.py
from shared_package.logging import setup_logging, get_logger
from config import config

# Setup logging (call once at startup)
setup_logging(
    project_name=config.project_name,
    log_dir="logs",
    level=config.log_level,
    log_to_file=config.log_to_file,
)

logger = get_logger(__name__)
logger.info(f"Starting {config.project_name} run")
```

---

## Level 3: Session Migration

### Step 3.1: Remove Local shared_package

If the project has a local `shared_package/` directory:

```bash
# Backup first
mv shared_package shared_package_backup

# Update imports to use root shared_package
# The root package is installed as editable via UV
```

### Step 3.2: Update Session Imports

**Before:**

```python
# Using local shared_package
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared_package.session.browser_session import BrowserSession
```

**After:**

```python
# Using installed shared_package
from shared_package.session import BrowserSession, ResilientBrowserSession
from shared_package.proxy import ProxyManager, ProxyType
```

### Step 3.3: Update Proxy Configuration

**Before:**

```python
# Manual proxy string construction
import os
from dotenv import load_dotenv
load_dotenv()

username = os.getenv("NORD_USERNAME")
password = os.getenv("NORD_PASSWORD")
proxy_url = f"http://{username}:{password}@us.nordvpn.com:80"
```

**After:**

```python
# Using ProxyManager
from shared_package.proxy import get_proxy_settings, ProxyType

proxy_settings = get_proxy_settings()
proxy_config = proxy_settings.get_config(ProxyType.NORD)

# Or let session handle it automatically
async with BrowserSession(proxy_type=ProxyType.NORD) as session:
    response = await session.get(url)
```

### Step 3.4: Update Browser Sessions

**Before:**

```python
async def fetch_data():
    browser = await async_playwright().chromium.launch(
        headless=True,
        proxy={"server": proxy_url}
    )
    page = await browser.new_page()
    # ... manual error handling
```

**After:**

```python
from shared_package.session import ResilientBrowserSession
from shared_package.proxy import ProxyType

async def fetch_data():
    async with ResilientBrowserSession(
        proxy_type=ProxyType.DATAIMPULSE,
        max_retries=3,
    ) as session:
        # Automatic retry on 429, 401, browser crashes
        response = await session.get(url)
        return response.json()
```

---

## Level 4: Full Restructure

### Step 4.1: Create Directory Structure

```bash
cd audiobee_bcbs_il

# Create new structure
mkdir -p scraper/service scraper/infrastructure pipeline logs

# Create __init__.py files
touch scraper/__init__.py
touch scraper/service/__init__.py
touch scraper/infrastructure/__init__.py
touch pipeline/__init__.py
```

### Step 4.2: Extract Service Classes

**Move index_1.py logic to scraper/service/search.py:**

```python
# scraper/service/search.py
"""Search service for provider discovery."""
from typing import AsyncIterator
from shared_package.logging import get_logger
from shared_package.session import HttpSession

logger = get_logger(__name__)


class SearchService:
    """Handles Phase 1: Provider search/discovery."""

    def __init__(self, config, session: HttpSession):
        self.config = config
        self.session = session

    async def search_by_specialty(
        self,
        specialty_code: str,
        state: str,
    ) -> AsyncIterator[dict]:
        """Search providers by specialty and state."""
        logger.info(f"Searching {specialty_code} in {state}")

        params = {
            "specialty": specialty_code,
            "state": state,
            "network_id": self.config.network_id,
            "page": 1,
            "limit": 100,
        }

        while True:
            response = await self.session.get(
                self.config.urls["search"],
                params=params,
                headers=self.config.headers,
            )
            data = response.json()

            for provider in data.get("providers", []):
                yield provider

            if not data.get("has_more"):
                break

            params["page"] += 1

    async def search_all_states(self) -> AsyncIterator[dict]:
        """Search all configured states."""
        for state in self.config.req_states:
            async for provider in self.search_by_specialty("*", state):
                yield provider
```

**Move index_2.py logic to scraper/service/details.py:**

```python
# scraper/service/details.py
"""Detail fetching service."""
from typing import List
from shared_package.logging import get_logger
from shared_package.session import HttpSession

logger = get_logger(__name__)


class DetailsService:
    """Handles Phase 2: Provider detail extraction."""

    def __init__(self, config, session: HttpSession):
        self.config = config
        self.session = session

    async def get_provider_details(self, provider_id: str) -> dict:
        """Fetch detailed provider information."""
        response = await self.session.get(
            f"{self.config.urls['details']}/{provider_id}",
            headers=self.config.headers,
        )
        return response.json()

    async def get_batch_details(
        self,
        provider_ids: List[str],
        batch_size: int = 10,
    ) -> List[dict]:
        """Fetch details for multiple providers with batching."""
        import asyncio

        results = []
        for i in range(0, len(provider_ids), batch_size):
            batch = provider_ids[i:i + batch_size]
            logger.info(f"Fetching batch {i // batch_size + 1}")

            tasks = [self.get_provider_details(pid) for pid in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for pid, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to fetch {pid}: {result}")
                else:
                    results.append(result)

        return results
```

### Step 4.3: Create Main Entry Point

```python
# scraper/main.py
"""Main entry point for audiobee_bcbs_il scraper."""
import asyncio
from pathlib import Path
from shared_package.logging import setup_logging, get_logger
from shared_package.session import HttpSession
from shared_package.io import JSONLWriter

from config import config
from scraper.service.search import SearchService
from scraper.service.details import DetailsService
from scraper.service.normalize import NormalizeService

logger = get_logger(__name__)


async def run_phase_1():
    """Phase 1: Discovery."""
    logger.info("Starting Phase 1: Discovery")

    output_path = Path(config.dirs["search_results"]) / "providers.jsonl"

    async with HttpSession() as session:
        search_service = SearchService(config, session)

        with JSONLWriter(output_path) as writer:
            async for provider in search_service.search_all_states():
                writer.write(provider)

    logger.info(f"Phase 1 complete: {output_path}")


async def run_phase_2():
    """Phase 2: Detail extraction."""
    logger.info("Starting Phase 2: Details")

    # Load provider IDs from Phase 1
    from shared_package.io import JSONLReader

    input_path = Path(config.dirs["search_results"]) / "providers.jsonl"
    provider_ids = [p["id"] for p in JSONLReader(input_path)]

    output_path = Path(config.dirs["provider_details"]) / "details.jsonl"

    async with HttpSession() as session:
        details_service = DetailsService(config, session)
        results = await details_service.get_batch_details(provider_ids)

        with JSONLWriter(output_path) as writer:
            for result in results:
                writer.write(result)

    logger.info(f"Phase 2 complete: {output_path}")


async def run_phase_3():
    """Phase 3: Normalization."""
    logger.info("Starting Phase 3: Normalization")

    normalize_service = NormalizeService(config)
    normalize_service.run()

    logger.info("Phase 3 complete")


async def main():
    """Run all phases."""
    setup_logging(
        project_name=config.project_name,
        log_dir="logs",
    )

    config.ensure_dirs()

    await run_phase_1()
    await run_phase_2()
    await run_phase_3()

    logger.info("All phases complete")


if __name__ == "__main__":
    asyncio.run(main())
```

### Step 4.4: Update run_all.py with Typer CLI

```python
#!/usr/bin/env python3
# run_all.py
"""CLI orchestrator for audiobee_bcbs_il scraper."""
import asyncio
from typing import Optional
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from shared_package.logging import setup_logging, get_logger
from config import config

app = typer.Typer(help="audiobee_bcbs_il scraper CLI")
console = Console()
logger = get_logger(__name__)


@app.command()
def run(
    phase: Optional[int] = typer.Option(
        None, "--phase", "-p",
        help="Run specific phase (1, 2, or 3). Omit to run all.",
    ),
    curr_date: Optional[str] = typer.Option(
        None, "--curr",
        help="Override current date (YYYYMMDD)",
    ),
    prev_date: Optional[str] = typer.Option(
        None, "--prev",
        help="Override previous date (YYYYMMDD)",
    ),
    debug: bool = typer.Option(
        False, "--debug", "-d",
        help="Enable debug logging",
    ),
):
    """Run the scraper pipeline."""
    # Setup logging
    setup_logging(
        project_name=config.project_name,
        log_dir="logs",
        level="DEBUG" if debug else config.log_level,
    )

    # Override dates if provided
    if curr_date:
        config.curr_date = curr_date
    if prev_date:
        config.prev_date = prev_date

    config.ensure_dirs()

    console.print(f"[bold blue]Starting {config.project_name}[/]")
    console.print(f"  Dates: {config.prev_date} → {config.curr_date}")

    from scraper.main import run_phase_1, run_phase_2, run_phase_3

    phases = {
        1: ("Discovery", run_phase_1),
        2: ("Details", run_phase_2),
        3: ("Normalization", run_phase_3),
    }

    if phase:
        name, func = phases[phase]
        console.print(f"[yellow]Running Phase {phase}: {name}[/]")
        asyncio.run(func())
    else:
        for num, (name, func) in phases.items():
            console.print(f"[yellow]Running Phase {num}: {name}[/]")
            asyncio.run(func())

    console.print("[bold green]Complete![/]")


@app.command()
def validate():
    """Validate output files."""
    import subprocess
    result = subprocess.run(
        ["python", "../output_generator/type_check.py", "."],
        capture_output=True,
        text=True,
    )
    console.print(result.stdout)
    if result.returncode != 0:
        console.print(f"[red]{result.stderr}[/]")
        raise typer.Exit(1)


@app.command()
def info():
    """Show project configuration."""
    console.print(f"[bold]Project:[/] {config.project_name}")
    console.print(f"[bold]Site Type:[/] {config.site_type}")
    console.print(f"[bold]Dates:[/] {config.prev_date} → {config.curr_date}")
    console.print(f"[bold]States:[/] {', '.join(config.req_states or [])}")
    console.print(f"[bold]Network ID:[/] {config.network_id}")
    console.print(f"\n[bold]Directories:[/]")
    for name, path in config.dirs.items():
        console.print(f"  {name}: {path}")


if __name__ == "__main__":
    app()
```

---

## Migration Checklist

### Pre-Migration

- [ ] Backup current project: `cp -r audiobee_project audiobee_project_backup`
- [ ] Verify shared_package is installed: `python -c "import shared_package"`
- [ ] Create root `.env` if not exists
- [ ] Document current behavior (run once, save output)

### Level 1 (Config)

- [ ] Update `config.py` to use `load_config()`
- [ ] Add backward compatibility exports
- [ ] Create project `.env` if needed
- [ ] Test: `python -c "from config import PREV_DATE; print(PREV_DATE)"`
- [ ] Run scraper, verify same output as before

### Level 2 (Logging)

- [ ] Replace all `print()` with logger calls
- [ ] Add `setup_logging()` to entry point
- [ ] Create `logs/` directory
- [ ] Add `*.log` to `.gitignore`
- [ ] Run scraper, check logs created

### Level 3 (Sessions)

- [ ] Remove local `shared_package/` if exists
- [ ] Update imports to use root package
- [ ] Replace manual proxy config with ProxyManager
- [ ] Use BrowserSession or HttpSession classes
- [ ] Test with different proxy types

### Level 4 (Full Restructure)

- [ ] Create `scraper/service/` directory structure
- [ ] Extract search logic to `SearchService`
- [ ] Extract details logic to `DetailsService`
- [ ] Create `scraper/main.py` entry point
- [ ] Update `run_all.py` with Typer CLI
- [ ] Run full pipeline, verify output matches

### Post-Migration

- [ ] Run `output_generator/type_check.py`
- [ ] Compare output with pre-migration backup
- [ ] Delete backup after verification
- [ ] Update project CLAUDE.md if exists

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'shared_package'"

```bash
# Ensure you're in the right virtual environment
source .venv/bin/activate

# Install shared_package in editable mode
cd /path/to/scraping
uv pip install -e shared_package/
```

### "ValidationError: Date must be YYYYMMDD format"

```bash
# Check .env file format
cat .env | grep DATE

# Dates should NOT have quotes
# Wrong: SCRAPER_CURR_DATE="20251226"
# Right: SCRAPER_CURR_DATE=20251226
```

### "Config loading from wrong .env"

```python
# Debug which .env files are loaded
from shared_package.config import BaseConfig
print(BaseConfig.model_config.get("env_file"))

# Should show: ('.env', '../.env', '../../.env')

# Check current working directory
import os
print(os.getcwd())  # Must be in project directory
```

### Legacy imports still work

If you see warnings about deprecated imports, update gradually:

```python
# Old (deprecated but still works)
from config import PREV_DATE, CURR_DATE

# New (preferred)
from config import config
print(config.prev_date, config.curr_date)
```

### Browser session crashes

```python
# Use ResilientBrowserSession for automatic recovery
from shared_package.session import ResilientBrowserSession

async with ResilientBrowserSession(max_retries=3) as session:
    # Automatic retry on browser crash, 429, 401, 403
    response = await session.get(url)
```

---

## Quick Reference

### Common Config Patterns

```python
# Sapphire projects
config = load_config("sapphire", "audiobee_bcbs_il", network_id="210002020")

# Carrier projects
config = load_config("carrier", "audiobee_florida_blue")

# Healthsparq projects
config = load_config("healthsparq", "audiobee_mvp_health")

# Anthem projects
config = load_config("anthem", "audiobee_anthem", brand="anthem")
```

### Common Session Patterns

```python
# Simple HTTP requests
async with HttpSession() as session:
    response = await session.get(url)

# Browser automation (stealth)
async with BrowserSession(proxy_type=ProxyType.NORD) as session:
    page = await session.new_page()
    await page.goto(url)

# Resilient browser (auto-retry)
async with ResilientBrowserSession(max_retries=3) as session:
    response = await session.get(url)
```

### Common Logging Patterns

```python
from shared_package.logging import get_logger
logger = get_logger(__name__)

logger.info(f"Processing {count} items")
logger.debug(f"Item details: {item}")
logger.warning(f"Rate limit approaching")
logger.error(f"Failed: {e}", exc_info=True)
```

---

## Related Documents

- [RESTRUCTURING_PLAN.md](./RESTRUCTURING_PLAN.md) - Overall architecture plan
- [SHARED_PACKAGE_SPEC.md](./SHARED_PACKAGE_SPEC.md) - Shared package specification
- [ENV_MANAGEMENT_GUIDE.md](./ENV_MANAGEMENT_GUIDE.md) - Environment variable best practices

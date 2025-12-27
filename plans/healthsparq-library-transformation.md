# feat: Transform healthsparq into importable library package

## Overview

Transform the unified `healthsparq/` package from a standalone CLI tool into an installable library that individual project folders can import. Each of the 23 HealthSparq projects will have its own folder with project-specific implementation while sharing core functionality from the `healthsparq` library.

**Type**: enhancement / refactor
**Priority**: P1
**Complexity**: High
**Estimated Effort**: 4-6 weeks

---

## Problem Statement / Motivation

### Current State

- `healthsparq/` is a monolithic package with 23 projects defined as YAML configs in `configs/`
- CLI-first design: `python -m healthsparq run project_name --curr YYYYMMDD`
- All projects share identical pipeline logic with no project-specific customization
- Session imports from external `core/` package via `sys.path.insert()` hack
- Configuration loading expects YAML files in package's internal `configs/` directory

### Problems with Current Approach

1. **No customization**: Projects can't override search logic, mapping, or normalization
2. **Fragile imports**: `sys.path.insert()` is fragile and breaks IDE tooling
3. **Testing limitations**: Can't run project-specific tests independently
4. **Deployment inflexibility**: Must deploy entire package for any project change
5. **Configuration sprawl**: 23 YAML configs embedded in library, not with projects

### Desired State

- `healthsparq` is an installable library (`pip install healthsparq`)
- Each project has its own folder (e.g., `audiobee_christus_health_plan/`)
- Projects import library and implement/override specific phases
- Project-specific configs, tests, and CLI in each folder
- Clean dependency management via `pyproject.toml`

---

## Proposed Solution

### Architecture Overview

```
scraping/
├── healthsparq/                    # LIBRARY PACKAGE
│   ├── pyproject.toml              # Package metadata (installable)
│   ├── src/healthsparq/            # Src layout for safety
│   │   ├── __init__.py             # Public API exports
│   │   ├── api.py                  # High-level scraping API
│   │   ├── config/                 # Configuration system
│   │   │   ├── __init__.py
│   │   │   ├── schema.py           # Pydantic models
│   │   │   ├── loader.py           # Config loading utilities
│   │   │   └── env.py              # pydantic-settings for .env
│   │   ├── core/                   # Core functionality
│   │   │   ├── __init__.py
│   │   │   ├── healthspark.py      # HealthSpark API wrapper
│   │   │   ├── session.py          # Session management
│   │   │   └── exceptions.py       # Exception hierarchy
│   │   ├── phases/                 # Pipeline phases (extensible)
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # Base phase classes
│   │   │   ├── search.py           # Search phase
│   │   │   ├── details.py          # Details phase
│   │   │   └── normalize.py        # Normalize phase
│   │   ├── io/                     # I/O utilities
│   │   │   ├── __init__.py
│   │   │   └── file_writer.py
│   │   └── cli/                    # CLI utilities for projects
│   │       ├── __init__.py
│   │       └── base.py             # Base CLI app
│   └── tests/                      # Library tests
│
├── audiobee_christus_health_plan/  # PROJECT FOLDER (example)
│   ├── pyproject.toml              # Project dependencies
│   ├── config.yaml                 # Project configuration
│   ├── .env                        # Secrets (gitignored)
│   ├── .env.example                # Secrets template
│   ├── run.py                      # CLI entry point
│   ├── scraper.py                  # Project-specific scraper (optional)
│   ├── mapper.py                   # Custom mapping logic (optional)
│   ├── tests/                      # Project-specific tests
│   │   └── test_scraper.py
│   └── YYYYMMDD/                   # Output directories
│       ├── raw/
│       └── processed/
│
├── audiobee_medica_sg/             # Another project
│   └── ...
│
└── core/                           # Shared utilities (git submodule)
```

### Public API Surface

```python
# healthsparq/__init__.py - Public API

# High-level API
from healthsparq.api import (
    HealthSparqScraper,      # Main scraper class
    run_scraper,             # Function to run full pipeline
    run_scraper_sync,        # Sync wrapper
)

# Configuration
from healthsparq.config import (
    ProjectConfig,           # Project configuration model
    EnvironmentSettings,     # .env settings model
    load_config,             # Load config from YAML
    get_env_settings,        # Get cached env settings
)

# Core components (for customization)
from healthsparq.core import (
    HealthSpark,             # Low-level API wrapper
    HealthSparkConfig,       # API configuration
    HealthSparqSession,      # Session management
)

# Phases (for extension)
from healthsparq.phases import (
    BasePhase,               # Base class for custom phases
    SearchPhase,             # Search phase implementation
    DetailsPhase,            # Details phase implementation
    NormalizePhase,          # Normalize phase implementation
)

# Exceptions
from healthsparq.exceptions import (
    HealthSparqError,
    AuthenticationError,
    APIError,
    SearchError,
    ConfigurationError,
)

# CLI utilities
from healthsparq.cli import (
    create_cli_app,          # Factory to create project CLI
    CommonOptions,           # Shared CLI options
)

# Version
__version__ = "2.0.0"
```

### Configuration Architecture

**Layer Precedence** (highest to lowest):

1. CLI arguments
2. Environment variables (`.env`)
3. Project YAML (`config.yaml`)
4. Library defaults

**Project config.yaml**:

```yaml
# audiobee_christus_health_plan/config.yaml
project:
  name: "Christus Health Plan"
  slug: christus_health_plan
  site_type: healthsparq

site:
  domain: providersearch.christushealth.org
  brand_code: CHRISTUS
  insurer_code: CHRISTUS
  api_version: "2"

plans:
  - product_code: HMO
    name: "Christus HMO"
    states: [TX, LA]
  - product_code: PPO
    name: "Christus PPO"
    states: [TX]

coverage:
  states: [TX, LA]

# Optional overrides (can also be in .env)
concurrency:
  max_workers: 5
  rate_limit_delay: 1.0
```

**Environment settings (.env)**:

```bash
# audiobee_christus_health_plan/.env
# Proxy configuration
HEALTHSPARQ_PROXY_URL=http://proxy.example.com:8080
HEALTHSPARQ_PROXY_USERNAME=user
HEALTHSPARQ_PROXY_PASSWORD=secret

# Browser automation
HEALTHSPARQ_HEADLESS=true
HEALTHSPARQ_BROWSER_TIMEOUT=30

# Debugging
HEALTHSPARQ_DEBUG=false
HEALTHSPARQ_LOG_LEVEL=INFO
```

### Project CLI Pattern

```python
# audiobee_christus_health_plan/run.py
#!/usr/bin/env python
"""CLI entry point for Christus Health Plan scraper."""

from pathlib import Path

import typer
from healthsparq import (
    ProjectConfig,
    run_scraper_sync,
    create_cli_app,
)

# Create CLI app with standard commands
app = create_cli_app(
    name="christus-health-plan",
    help="Christus Health Plan provider directory scraper",
)

# Project root directory
PROJECT_DIR = Path(__file__).parent


@app.command()
def run(
    curr: str = typer.Option(..., "--curr", "-c", help="Current date (YYYYMMDD)"),
    prev: str = typer.Option(None, "--prev", "-p", help="Previous date"),
    phase: int = typer.Option(None, "--phase", help="Run specific phase (1, 2, or 3)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate without scraping"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Run the scraper for specified dates."""
    config = ProjectConfig.load(PROJECT_DIR / "config.yaml")

    result = run_scraper_sync(
        config=config,
        curr_date=curr,
        prev_date=prev,
        phase=phase,
        dry_run=dry_run,
        output_dir=PROJECT_DIR,
    )

    if result.success:
        typer.echo(f"[green]Completed: {result.providers_count} providers[/green]")
    else:
        typer.echo(f"[red]Failed: {result.error}[/red]", err=True)
        raise typer.Exit(1)


@app.command()
def validate():
    """Validate project configuration."""
    config = ProjectConfig.load(PROJECT_DIR / "config.yaml")
    typer.echo(f"[green]Configuration valid: {config.project.name}[/green]")


if __name__ == "__main__":
    app()
```

### Customization Pattern

```python
# audiobee_medica_sg/scraper.py
"""Custom scraper with extended mapping logic."""

from healthsparq import HealthSparqScraper, NormalizePhase
from healthsparq.phases import BasePhase


class MedicaSGNormalizePhase(NormalizePhase):
    """Custom normalization for Medica SG with special network handling."""

    def map_provider(self, raw_provider: dict) -> dict:
        """Override mapping for Medica-specific fields."""
        mapped = super().map_provider(raw_provider)

        # Custom network name mapping
        if "medica_sg_network" in raw_provider:
            mapped["network_name"] = self._map_medica_network(
                raw_provider["medica_sg_network"]
            )

        return mapped

    def _map_medica_network(self, network_code: str) -> str:
        """Map Medica-specific network codes."""
        network_map = {
            "MSG_HMO": "Medica SG HMO Network",
            "MSG_PPO": "Medica SG PPO Network",
        }
        return network_map.get(network_code, network_code)


# In run.py, use custom phase:
from scraper import MedicaSGNormalizePhase

result = run_scraper_sync(
    config=config,
    curr_date=curr,
    normalize_phase_class=MedicaSGNormalizePhase,  # Custom phase
)
```

---

## Technical Approach

### Phase 1: Library Refactoring (Week 1-2)

#### 1.1 Restructure to src/ layout

```
healthsparq/
├── pyproject.toml
├── src/
│   └── healthsparq/
│       ├── __init__.py      # Public API
│       └── ...
└── tests/
```

#### 1.2 Update pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "healthsparq"
version = "2.0.0"
description = "Library for scraping HealthSparq provider directories"
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
dependencies = [
    "pydantic>=2.0.0,<3.0.0",
    "pydantic-settings>=2.0.0,<3.0.0",
    "typer>=0.9.0,<1.0.0",
    "pyyaml>=6.0.0,<7.0.0",
    "httpx>=0.24.0,<1.0.0",
    "orjson>=3.9.0,<4.0.0",
    "ideon-scraping-core>=3.0.0",  # core/ as proper dependency
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "mypy>=1.0.0",
    "ruff>=0.1.0",
]

[tool.hatch.build.targets.wheel]
packages = ["src/healthsparq"]
```

#### 1.3 Create EnvironmentSettings class

```python
# src/healthsparq/config/env.py
from functools import lru_cache
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvironmentSettings(BaseSettings):
    """Runtime environment configuration from .env files."""

    model_config = SettingsConfigDict(
        env_prefix="HEALTHSPARQ_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Proxy settings
    proxy_url: str | None = None
    proxy_username: str | None = None
    proxy_password: SecretStr | None = None

    # Browser automation
    headless: bool = True
    browser_timeout: int = 30

    # Debugging
    debug: bool = False
    log_level: str = "INFO"


@lru_cache
def get_env_settings() -> EnvironmentSettings:
    """Get cached environment settings."""
    return EnvironmentSettings()
```

#### 1.4 Create high-level API

```python
# src/healthsparq/api.py
from pathlib import Path
from typing import Type
import asyncio

from .config import ProjectConfig, get_env_settings
from .core import HealthSpark, HealthSparkConfig
from .phases import SearchPhase, DetailsPhase, NormalizePhase, BasePhase


class HealthSparqScraper:
    """High-level scraper that orchestrates all phases."""

    def __init__(
        self,
        config: ProjectConfig,
        output_dir: Path,
        search_phase_class: Type[SearchPhase] = SearchPhase,
        details_phase_class: Type[DetailsPhase] = DetailsPhase,
        normalize_phase_class: Type[NormalizePhase] = NormalizePhase,
    ):
        self.config = config
        self.output_dir = output_dir
        self.env = get_env_settings()
        self._search_phase = search_phase_class(config, output_dir)
        self._details_phase = details_phase_class(config, output_dir)
        self._normalize_phase = normalize_phase_class(config, output_dir)

    async def run(
        self,
        curr_date: str,
        prev_date: str | None = None,
        phase: int | None = None,
    ) -> "ScraperResult":
        """Run the scraper pipeline."""
        # Implementation
        pass


async def run_scraper(
    config: ProjectConfig,
    curr_date: str,
    prev_date: str | None = None,
    phase: int | None = None,
    output_dir: Path | None = None,
    **kwargs,
) -> "ScraperResult":
    """Async function to run a scraper."""
    scraper = HealthSparqScraper(config, output_dir or Path.cwd(), **kwargs)
    return await scraper.run(curr_date, prev_date, phase)


def run_scraper_sync(
    config: ProjectConfig,
    curr_date: str,
    prev_date: str | None = None,
    phase: int | None = None,
    output_dir: Path | None = None,
    **kwargs,
) -> "ScraperResult":
    """Sync wrapper for CLI usage."""
    return asyncio.run(
        run_scraper(config, curr_date, prev_date, phase, output_dir, **kwargs)
    )
```

#### 1.5 Create CLI factory

```python
# src/healthsparq/cli/base.py
import typer
from rich.console import Console

console = Console()


def create_cli_app(
    name: str,
    help: str,
    version: str = "1.0.0",
) -> typer.Typer:
    """Factory to create a CLI app for a project."""
    app = typer.Typer(
        name=name,
        help=help,
        add_completion=True,
    )

    @app.callback()
    def main(
        version: bool = typer.Option(
            False, "--version", "-V", help="Show version"
        ),
    ):
        if version:
            console.print(f"{name} v{version}")
            raise typer.Exit()

    return app
```

### Phase 2: Migration Tooling (Week 2-3)

#### 2.1 Create project scaffold command

```python
# src/healthsparq/cli/scaffold.py
import typer
from pathlib import Path
import shutil

scaffold_app = typer.Typer()


@scaffold_app.command()
def create_project(
    name: str = typer.Argument(..., help="Project slug (e.g., christus_health_plan)"),
    output_dir: Path = typer.Option(
        Path.cwd(), "--output", "-o", help="Output directory"
    ),
):
    """Create a new HealthSparq project from template."""
    project_dir = output_dir / f"audiobee_{name}"

    # Create directory structure
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "tests").mkdir(exist_ok=True)

    # Create files from templates
    _create_config_yaml(project_dir, name)
    _create_run_py(project_dir, name)
    _create_env_example(project_dir)
    _create_pyproject_toml(project_dir, name)
    _create_gitignore(project_dir)

    console.print(f"[green]Created project: {project_dir}[/green]")
```

#### 2.2 Create migration script

```python
# scripts/migrate_project.py
"""Migrate a project from unified configs/ to standalone folder."""

import argparse
from pathlib import Path
import yaml
import shutil


def migrate_project(
    project_slug: str,
    source_dir: Path,  # healthsparq/configs/
    target_dir: Path,  # scraping/
):
    """Migrate a single project from unified to standalone."""
    # Read existing config
    config_path = source_dir / f"{project_slug}.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Create project directory
    project_dir = target_dir / f"audiobee_{project_slug}"
    project_dir.mkdir(parents=True, exist_ok=True)

    # Write new config.yaml
    with open(project_dir / "config.yaml", "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    # Create other files
    _create_run_py(project_dir, project_slug)
    _create_env_example(project_dir)
    _create_pyproject_toml(project_dir, project_slug)

    print(f"Migrated: {project_slug} -> {project_dir}")
```

### Phase 3: Pilot Migration (Week 3-4)

1. Migrate 3 pilot projects:
   - `christus_health_plan` (simple)
   - `medica_sg` (complex with 27 plans)
   - `excellus` (medium complexity)

2. Validation checklist:
   - [ ] Config loads correctly
   - [ ] CLI commands work (`run`, `validate`)
   - [ ] Output matches unified package exactly
   - [ ] Project-specific tests pass
   - [ ] QA tools can find outputs

### Phase 4: Full Migration (Week 4-6)

1. Migrate remaining 20 projects
2. Update tooling:
   - `tools/run_parallel.py` - discover projects by convention
   - `output_generator/` - find outputs in project folders
3. Deprecate unified `healthsparq/configs/` directory
4. Update documentation

---

## Acceptance Criteria

### Functional Requirements

- [ ] `healthsparq` is installable via `pip install healthsparq` (or `pip install -e .` for dev)
- [ ] Each project has its own folder with `config.yaml`, `run.py`, `.env.example`
- [ ] Projects can run independently: `cd audiobee_christus_health_plan && python run.py --curr 20251226`
- [ ] Projects can customize phases by subclassing
- [ ] `.env` files are properly loaded with pydantic-settings
- [ ] CLI provides `--curr`, `--prev`, `--phase`, `--dry-run`, `--verbose` options

### Non-Functional Requirements

- [ ] No `sys.path.insert()` hacks - clean imports only
- [ ] All 23 projects migrated and functional
- [ ] Output matches unified package exactly (validated by comparison)
- [ ] `tools/run_parallel.py` works with new structure
- [ ] `output_generator/` tools work with new structure
- [ ] Library tests pass: `pytest healthsparq/tests/`
- [ ] Project tests pass: `pytest audiobee_*/tests/`

### Quality Gates

- [ ] Type checking passes: `mypy healthsparq/`
- [ ] Linting passes: `ruff check healthsparq/`
- [ ] Test coverage >80% for library code
- [ ] Documentation updated in `healthsparq/README.md`
- [ ] Migration runbook documented

---

## Success Metrics

1. **Migration completeness**: All 23 projects migrated and functional
2. **Output equivalence**: 100% match with unified package outputs
3. **Developer velocity**: New project setup <10 minutes (with scaffold)
4. **Independence**: Projects can be versioned/deployed independently
5. **Test isolation**: Project tests run without full library

---

## Dependencies & Prerequisites

### Technical Dependencies

- `core/` submodule published as installable package (`ideon-scraping-core`)
- Python 3.10+ on all execution environments
- `pydantic-settings>=2.0.0` for .env handling

### Human Dependencies

- Team training on new project structure
- Documentation review before migration
- Validation of pilot projects before full migration

### Blocked By

- Nothing (can start immediately)

### Blocks

- Individual project feature development (should wait for migration)

---

## Risk Analysis & Mitigation

| Risk                            | Impact | Probability | Mitigation                             |
| ------------------------------- | ------ | ----------- | -------------------------------------- |
| Output mismatch after migration | High   | Medium      | Automated comparison tests             |
| `core/` dependency conflicts    | High   | Low         | Pin versions during transition         |
| Parallel execution breaks       | Medium | Medium      | Update `run_parallel.py` early         |
| Developer confusion             | Medium | High        | Comprehensive documentation            |
| Secrets accidentally committed  | High   | Low         | .gitignore templates, pre-commit hooks |

---

## Implementation Phases

### Phase 1: Library Refactoring (Week 1-2)

- [ ] Restructure to src/ layout
- [ ] Update pyproject.toml with proper metadata
- [ ] Create EnvironmentSettings class (pydantic-settings)
- [ ] Create high-level API (`HealthSparqScraper`, `run_scraper`)
- [ ] Create CLI factory (`create_cli_app`)
- [ ] Make phases extensible (base classes)
- [ ] Update `__init__.py` with public API
- [ ] Add library tests

### Phase 2: Migration Tooling (Week 2-3)

- [ ] Create project scaffold command
- [ ] Create migration script
- [ ] Create project template files
- [ ] Update `run_parallel.py` for project discovery
- [ ] Update `output_generator/` for new structure

### Phase 3: Pilot Migration (Week 3-4)

- [ ] Migrate `christus_health_plan`
- [ ] Migrate `medica_sg`
- [ ] Migrate `excellus`
- [ ] Run validation suite
- [ ] Document lessons learned

### Phase 4: Full Migration (Week 4-6)

- [ ] Migrate remaining 20 projects
- [ ] Run full validation suite
- [ ] Update all documentation
- [ ] Deprecate unified configs
- [ ] Deploy to production

---

## File Structure for MVP

### healthsparq/pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "healthsparq"
version = "2.0.0"
description = "Library for scraping HealthSparq provider directories"
requires-python = ">=3.10"
dependencies = [
    "pydantic>=2.0.0,<3.0.0",
    "pydantic-settings>=2.0.0,<3.0.0",
    "typer>=0.9.0,<1.0.0",
    "pyyaml>=6.0.0,<7.0.0",
    "httpx>=0.24.0,<1.0.0",
    "orjson>=3.9.0,<4.0.0",
]

[tool.hatch.build.targets.wheel]
packages = ["src/healthsparq"]
```

### audiobee_christus_health_plan/run.py

```python
#!/usr/bin/env python
from pathlib import Path
import typer
from healthsparq import ProjectConfig, run_scraper_sync, create_cli_app

app = create_cli_app("christus-health-plan", "Christus Health Plan scraper")
PROJECT_DIR = Path(__file__).parent

@app.command()
def run(
    curr: str = typer.Option(..., "--curr", "-c"),
    prev: str = typer.Option(None, "--prev", "-p"),
    phase: int = typer.Option(None, "--phase"),
):
    config = ProjectConfig.load(PROJECT_DIR / "config.yaml")
    result = run_scraper_sync(config, curr, prev, phase, PROJECT_DIR)
    typer.echo(f"Completed: {result.providers_count} providers")

if __name__ == "__main__":
    app()
```

### audiobee_christus_health_plan/.env.example

```bash
# Proxy configuration
HEALTHSPARQ_PROXY_URL=
HEALTHSPARQ_PROXY_USERNAME=
HEALTHSPARQ_PROXY_PASSWORD=

# Browser automation
HEALTHSPARQ_HEADLESS=true
HEALTHSPARQ_BROWSER_TIMEOUT=30

# Debugging
HEALTHSPARQ_DEBUG=false
HEALTHSPARQ_LOG_LEVEL=INFO
```

---

## References & Research

### Internal References

- Current healthsparq structure: `healthsparq/` (86 files)
- CLI implementation: `healthsparq/cli.py:1-150`
- Config schema: `healthsparq/config/schema.py:1-212`
- Core API: `healthsparq/core/healthspark.py:1-372`
- Session management: `healthsparq/core/session.py:1-199`

### External References

- [Python Packaging User Guide - src layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)
- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Typer Documentation](https://typer.tiangolo.com/)
- [pyOpenSci Python Package Guide](https://www.pyopensci.org/python-package-guide/)

### Related Work

- Similar transformation: Scrapy's project structure (library + per-project folders)
- Configuration pattern: FastAPI settings with pydantic-settings

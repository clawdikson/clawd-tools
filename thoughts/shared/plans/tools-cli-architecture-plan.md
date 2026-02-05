# Feature Plan: Unified Tools CLI Architecture
Created: 2026-01-24
Author: architect-agent

## Overview

Consolidate 13+ disparate tools into a unified CLI (`scraper-tools`) with plugin discovery, shared abstractions, and consistent UX patterns. This plan addresses code duplication, inconsistent interfaces, and poor discoverability in the current tools/ directory.

## Current State Analysis

### Tool Inventory (13 tools, 6 categories)

| Category | Tool | CLI Type | UX Quality | Issues |
|----------|------|----------|------------|--------|
| **Cloud Upload** | drive_uploader.py | Typer | Excellent | OAuth code duplicated with xlsx_to_clickup |
| | s3_uploader.py | Library only | Good | No CLI, only library API |
| **Reporting** | xlsx_to_clickup.py | Typer | Excellent | Gmail OAuth duplicated with drive_uploader |
| **Validation** | validate_env.py | argparse | Basic | No progress, bare-bones output |
| | validate_migration.py | argparse | Basic | Legacy argparse |
| **Project Mgmt** | project_config.py | Library only | N/A | Utility, no CLI |
| | project_registry.py | Typer | Good | Standalone, not discoverable |
| **Migration** | migrate_datastore/ | Typer | Excellent | Best-in-class UX with Rich |
| | rollback_migration.py | argparse | Basic | Legacy, minimal feedback |
| **TUI Apps** | dashboard/ | Textual | Good | Standalone app |
| | sqlitefs_explorer/ | Textual | Excellent | Standalone app |
| **Security** | find_hardcoded_credentials.py | argparse | Basic | Legacy, no color output |

### Pain Points Identified

1. **No unified entry point** - Users must memorize 13+ tool names
2. **Inconsistent CLI patterns** - Mix of argparse (5), Typer (5), library-only (3)
3. **Code duplication**:
   - OAuth flow: `drive_uploader.py` and `xlsx_to_clickup.py` both implement `_load_google_libs()`, `_get_oauth_credentials()`
   - Lazy loading: 3 tools implement identical `_load_*_libs()` pattern
   - Config loading: `project_config.py` duplicated in multiple tools
4. **Inconsistent logging**: Some use `core.logging`, others use `print()`
5. **No shared progress/output abstractions**: Each tool reinvents progress bars

## Requirements

- [ ] Single entry point: `scraper-tools <command>` or `python -m tools <command>`
- [ ] Plugin discovery: Auto-discover tools without hardcoded registration
- [ ] Consistent UX: Rich console output, progress bars, error handling
- [ ] Shared abstractions: OAuth, credentials, progress, config loading
- [ ] Backwards compatibility: Existing CLI invocations continue to work
- [ ] TUI apps accessible: Dashboard and Explorer via subcommands

## Design

### Architecture

```
tools/
├── __init__.py                 # Package marker
├── __main__.py                 # Entry: python -m tools
├── cli.py                      # Main Typer app with plugin discovery
│
├── core/                       # NEW: Shared abstractions
│   ├── __init__.py
│   ├── oauth.py                # Consolidated OAuth (Google, AWS)
│   ├── credentials.py          # Credential loading from secrets/
│   ├── progress.py             # Rich progress/console utilities
│   ├── lazy_imports.py         # Generic lazy import pattern
│   └── config.py               # Project config loading (from project_config.py)
│
├── commands/                   # NEW: Plugin-based command modules
│   ├── __init__.py             # Plugin discovery logic
│   ├── upload.py               # drive, s3 subcommands
│   ├── report.py               # xlsx-to-clickup, email subcommands
│   ├── validate.py             # env, migration, schema subcommands
│   ├── project.py              # registry, config subcommands
│   ├── migrate.py              # datastore migration commands
│   └── tui.py                  # dashboard, explorer launchers
│
├── secrets/                    # Credentials directory (gitignored)
│   ├── oauth_credentials.json
│   ├── google_drive_credentials.json
│   └── aws_credentials.json
│
└── [existing files...]         # Legacy tools (deprecated, still work)
```

### Unified CLI Structure

```bash
# Main entry point
scraper-tools --help
python -m tools --help

# Command groups (5 categories)
scraper-tools upload drive <project> --date 20260115
scraper-tools upload s3 <file> --project <name>

scraper-tools report excel <project> --to email@example.com
scraper-tools report clickup <project> --task CU12345

scraper-tools validate env --project <name>
scraper-tools validate migration <project> --prev 20251210 --curr 20260115

scraper-tools project list --site-type sapphire
scraper-tools project show <name>

scraper-tools migrate run <source> --to sqlite
scraper-tools migrate sapphire <project> <date>
scraper-tools migrate rollback --list-commits

scraper-tools tui dashboard
scraper-tools tui explorer <db_path>
```

### Plugin Discovery Pattern

```python
# tools/commands/__init__.py
from pathlib import Path
import importlib

def discover_commands() -> list[typer.Typer]:
    """Auto-discover command modules in commands/ directory."""
    commands_dir = Path(__file__).parent
    apps = []
    
    for module_path in commands_dir.glob("*.py"):
        if module_path.name.startswith("_"):
            continue
        module_name = f"tools.commands.{module_path.stem}"
        module = importlib.import_module(module_name)
        
        # Each module exports `app: typer.Typer` and `name: str`
        if hasattr(module, "app") and hasattr(module, "name"):
            apps.append((module.name, module.app))
    
    return apps

# tools/cli.py
import typer
from tools.commands import discover_commands

main_app = typer.Typer(
    name="scraper-tools",
    help="Unified CLI for scraping toolkit utilities",
)

# Auto-register discovered command groups
for name, app in discover_commands():
    main_app.add_typer(app, name=name)
```

### Shared OAuth Abstraction

```python
# tools/core/oauth.py
from pathlib import Path
from typing import Literal

class OAuthManager:
    """Unified OAuth credential management for Google and AWS."""
    
    SECRETS_DIR = Path(__file__).parent.parent / "secrets"
    
    def __init__(self, provider: Literal["google", "aws"]):
        self.provider = provider
        self._credentials = None
        self._service = None
    
    def get_google_credentials(
        self,
        scopes: list[str],
        service_account: bool = False,
    ):
        """Get Google OAuth credentials (lazily loaded)."""
        # Consolidated logic from drive_uploader and xlsx_to_clickup
        ...
    
    def get_aws_credentials(self) -> dict:
        """Get AWS credentials from secrets or environment."""
        # Logic from s3_uploader
        ...
```

### Shared Progress Utilities

```python
# tools/core/progress.py
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

def create_progress() -> Progress:
    """Create standardized progress bar."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    )

def success(message: str) -> None:
    """Print success message."""
    console.print(f"[green]✓[/] {message}")

def error(message: str) -> None:
    """Print error message."""
    console.print(f"[red]✗[/] {message}", style="red")

def warning(message: str) -> None:
    """Print warning message."""
    console.print(f"[yellow]⚠[/] {message}")
```

## Dependencies

| Dependency | Type | Reason |
|------------|------|--------|
| typer | External | CLI framework (already used by 5+ tools) |
| rich | External | Console output, progress bars |
| google-api-python-client | External | Google Drive/Gmail (lazy loaded) |
| boto3 | External | AWS S3 (lazy loaded) |
| textual | External | TUI apps (lazy loaded) |

## Implementation Phases

### Phase 1: Foundation (core/ abstractions)
**Files to create:**
- `tools/core/__init__.py`
- `tools/core/oauth.py` - Consolidated OAuth from drive_uploader + xlsx_to_clickup
- `tools/core/credentials.py` - Credential loading patterns
- `tools/core/progress.py` - Rich progress utilities
- `tools/core/lazy_imports.py` - Generic lazy import decorator

**Acceptance:**
- [ ] OAuth works for both Drive and Gmail
- [ ] Progress utilities match migrate_datastore quality
- [ ] Lazy imports work without dependencies installed

**Estimated effort:** Medium (2-3 hours)

### Phase 2: Plugin Discovery System
**Files to create:**
- `tools/commands/__init__.py` - Plugin discovery
- `tools/cli.py` - Main Typer app
- `tools/__main__.py` - Entry point

**Acceptance:**
- [ ] `python -m tools --help` shows all commands
- [ ] Commands auto-discovered from commands/
- [ ] No hardcoded command registration

**Estimated effort:** Small (1-2 hours)

### Phase 3: Command Migration - Upload Group
**Files to create:**
- `tools/commands/upload.py` - drive, s3 subcommands

**Refactor:**
- Extract core logic from `drive_uploader.py`
- Extract core logic from `s3_uploader.py`

**Acceptance:**
- [ ] `scraper-tools upload drive` works
- [ ] `scraper-tools upload s3` works
- [ ] OAuth shared between commands

**Estimated effort:** Medium (2 hours)

### Phase 4: Command Migration - Report Group
**Files to create:**
- `tools/commands/report.py` - excel, email, clickup subcommands

**Refactor:**
- Extract core logic from `xlsx_to_clickup.py`
- Share Gmail OAuth with upload commands

**Acceptance:**
- [ ] `scraper-tools report email` works
- [ ] `scraper-tools report clickup` works
- [ ] OAuth reused from core/

**Estimated effort:** Medium (2 hours)

### Phase 5: Command Migration - Validate Group
**Files to create:**
- `tools/commands/validate.py` - env, migration subcommands

**Refactor:**
- Modernize `validate_env.py` (argparse -> Typer)
- Modernize `validate_migration.py` (argparse -> Typer)

**Acceptance:**
- [ ] `scraper-tools validate env` works
- [ ] `scraper-tools validate migration` works
- [ ] Rich output for validation results

**Estimated effort:** Small (1-2 hours)

### Phase 6: Command Migration - Project Group
**Files to create:**
- `tools/commands/project.py` - list, show, stats subcommands

**Refactor:**
- Integrate `project_registry.py` commands
- Integrate `project_config.py` utilities

**Acceptance:**
- [ ] `scraper-tools project list` works
- [ ] `scraper-tools project show` works

**Estimated effort:** Small (1 hour)

### Phase 7: Command Migration - Migrate Group
**Files to create:**
- `tools/commands/migrate.py` - run, sapphire, rollback subcommands

**Refactor:**
- Wrap `migrate_datastore/` module
- Modernize `rollback_migration.py`

**Acceptance:**
- [ ] `scraper-tools migrate run` works
- [ ] `scraper-tools migrate sapphire` works
- [ ] `scraper-tools migrate rollback` works

**Estimated effort:** Medium (2 hours)

### Phase 8: Command Migration - TUI Group
**Files to create:**
- `tools/commands/tui.py` - dashboard, explorer launchers

**Acceptance:**
- [ ] `scraper-tools tui dashboard` launches dashboard
- [ ] `scraper-tools tui explorer <path>` launches explorer

**Estimated effort:** Small (30 minutes)

### Phase 9: Documentation & Deprecation
**Files to modify:**
- `tools/README.md` - Document new CLI
- Legacy tools - Add deprecation warnings

**Acceptance:**
- [ ] README documents all commands
- [ ] Legacy tools print deprecation notice
- [ ] Migration guide for users

**Estimated effort:** Small (1 hour)

### Phase 10: Testing
**Files to create:**
- `tools/tests/test_cli.py`
- `tools/tests/test_oauth.py`
- `tools/tests/test_commands.py`

**Coverage target:** 80%

**Estimated effort:** Medium (2-3 hours)

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing scripts | High | Keep legacy entry points working with deprecation warnings |
| OAuth refactor breaks auth | High | Test with real credentials before merging |
| Plugin discovery performance | Low | Cache discovered modules at startup |
| Dependency conflicts | Medium | Lazy imports for optional deps (textual, boto3) |

## Open Questions

- [ ] Should we use `uv run scraper-tools` or add entry point to pyproject.toml?
- [ ] Should TUI apps be lazy-loaded or always available?
- [ ] Do we need a config file for default settings (e.g., default recipients)?

## Success Criteria

1. Single command to discover all tools: `scraper-tools --help`
2. All tools use consistent Rich output (colors, progress bars)
3. OAuth flow shared between Drive, Gmail, ClickUp commands
4. 0 code duplication for lazy imports, credentials, progress
5. Legacy tools still work with deprecation warnings
6. Test coverage >= 80%

## Integration with Platform Libraries

This tools CLI complements the platform-specific CLIs:

| CLI | Purpose | Entry Point |
|-----|---------|-------------|
| `python -m healthsparq` | Run HealthSparq scrapers | healthsparq/cli.py |
| `python -m sapphire` | Run Sapphire scrapers | sapphire/cli.py |
| `scraper-tools` | Utilities (upload, validate, etc.) | tools/cli.py |

The platform CLIs remain separate (they run scrapers), while `scraper-tools` handles auxiliary operations.

## Appendix: Example Command Module

```python
# tools/commands/upload.py
"""Upload commands: Google Drive and S3."""

import typer
from pathlib import Path
from tools.core.oauth import OAuthManager
from tools.core.progress import console, success, error

name = "upload"  # Command group name for discovery
app = typer.Typer(help="Upload files to cloud storage")


@app.command()
def drive(
    project: str = typer.Argument(..., help="Project name"),
    date: str = typer.Option(None, "--date", "-d", help="Date (YYYYMMDD)"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Validate only"),
):
    """Upload 7z archive to Google Drive."""
    from tools.core.config import load_project_config
    from tools.drive_uploader import DriveUploader
    
    # Load config
    config = load_project_config(project, date_override=date)
    console.print(f"Project: {config.name} ({config.project_type})")
    console.print(f"Date: {config.curr_date}")
    
    # Validate and upload
    uploader = DriveUploader(use_oauth=True)
    folder_id = uploader.get_folder_id(config.name)
    
    if dry_run:
        success(f"Would upload to folder {folder_id}")
        return
    
    # ... actual upload logic with progress bar
    success("Upload complete!")


@app.command()
def s3(
    file: Path = typer.Argument(..., help="File to upload"),
    project: str = typer.Option(..., "--project", "-p", help="Project name"),
):
    """Upload file to S3 with presigned URL."""
    from tools.s3_uploader import S3Uploader, S3Config
    
    config = S3Config.from_env()
    uploader = S3Uploader(config)
    
    # ... upload logic
    success(f"Uploaded to s3://{config.bucket_name}/...")
```

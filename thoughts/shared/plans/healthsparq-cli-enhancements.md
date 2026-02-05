# HealthSparq CLI Enhancements Plan

**Created**: 2026-01-08
**Status**: Draft
**Author**: Claude Code (Sisyphus)

## Overview

This plan consolidates multiple CLI improvements for the HealthSparq scraper package:

1. Report generator fix (migrate from `output_generator`)
2. Include recovered providers as default
3. Multiple phase run support (ranges, arrays, skip/from)
4. Sticky tqdm progress view
5. Thin wrapper pattern for per-project `run.py`

---

## 1. Report Generator Migration

### Problem

The `core/qa/reporter.py` is missing critical metrics that `output_generator/report_generator.py` provides. The `output_generator` package is being deprecated, so this logic needs to move to `core/qa`.

### Missing Metrics in `core/qa/reporter.py`

| Metric | Description | Source |
|--------|-------------|--------|
| `first_file_date` | Timestamp of earliest raw file | `raw/` directory `ctime`/`mtime` |
| `last_file_date` | Timestamp of latest raw file | `raw/` directory `ctime`/`mtime` |
| `scraped_npis` | Count of directly scraped NPIs | `raw/provider_details/*.json` (non-missing) |
| `original_dropped_npis` | Missing + true drops count | `missing_*.json` count + true drops |
| `recovered_npis` | NPIs found via checker/recovery | `raw/provider_details/missing_*.json` |
| `true_drops` | NPIs in prev but not in curr | `prev_npis - curr_npis` |
| `raw_direct_files` | Count of direct scrape files | `*.json` without "missing" prefix |
| `raw_missing_files` | Count of recovery files | `missing_*.json` files |
| `in_scope_unique` | Unique providers in req_states | Per-provider state check |
| `out_scope_unique` | Unique providers outside req_states | Per-provider state check |
| `in_scope_non_unique` | Address count in req_states | Per-address state count |
| `out_scope_non_unique` | Address count outside req_states | Per-address state count |

### Output Format

Two Excel sheets matching `output_generator` format:

**Sheet 1: Summary Counts**
```
Description                                    | Data
-----------------------------------------------|----------------------------------
In-scope States:                               | IL, IN, WI
In-Scope Providers (Unique):                   | 12,345 (85.2%)
Out-of-Scope Provider (Unique):                | 2,145 (14.8%)
In-Scope Providers (Non-Unique):               | 18,234 (78.3%)
Out-of-Scope Providers (Non-Unique):           | 5,043 (21.7%)
                                               |
First File Created = 01/15/2026 10:30:45       |
Last File Created = 01/15/2026 18:45:12        |
                                               |
Scraped NPIs = 14,234                          |
Original dropped NPIs = 456                    |
Found and scraped using checker tool = 389    |
True Drops = 67                                |
                                               |
Provider Data Statistics:                      |
Raw Direct Files: 14,234                       |
Raw Missing Files: 389                         |
Unique Direct NPIs: 14,234                     |
Unique Missing NPIs: 389                       |
```

**Sheet 2: State Level Counts**
```
State | Count
------|-------
IL    | 8,234
IN    | 3,456
WI    | 2,100
OH    | 1,234
...   | ...
```

### Implementation Tasks

#### Task 1.1: Update `core/qa/reporter.py`

**File**: `core/qa/reporter.py`

Add new dataclass for extended metrics:
```python
@dataclass
class ExtendedReportMetrics:
    """Extended metrics matching output_generator format."""
    # Existing
    states_count: int = 0
    total_providers: int = 0
    in_scope_states: int = 0
    total_change: int = 0
    report_size_bytes: int = 0
    
    # New: File timestamps
    first_file_date: str | None = None
    last_file_date: str | None = None
    
    # New: NPI statistics
    scraped_npis: int = 0
    original_dropped_npis: int = 0
    recovered_npis: int = 0
    true_drops: int = 0
    
    # New: Raw file counts
    raw_direct_files: int = 0
    raw_missing_files: int = 0
    
    # New: Scope breakdown
    in_scope_unique: int = 0
    out_scope_unique: int = 0
    in_scope_non_unique: int = 0
    out_scope_non_unique: int = 0
    
    # New: State counts
    state_counts: dict[str, int] = field(default_factory=dict)
```

Add methods:
- `_analyze_provider_data()` - Scan `raw/provider_details/` for direct vs missing files
- `_get_file_timestamps()` - Get first/last file dates from `raw/` directory
- `_calculate_scope_breakdown()` - Calculate in-scope vs out-of-scope counts
- `_write_extended_excel()` - Write two-sheet Excel with full metrics

#### Task 1.2: Update `healthsparq/phases/report.py`

Pass additional parameters to `core.qa.report()`:
- `raw_dir` - Path to raw provider details
- `hsparq=True` - Enable HealthSparq-specific analysis

#### Task 1.3: Add CLI option for report type

```python
@app.command()
def run(
    # ... existing options ...
    report_type: str = typer.Option(
        "extended", "--report-type",
        help="Report type: basic (state counts only) or extended (full metrics)"
    ),
):
```

---

## 2. Include Recovered as Default

### Problem

Currently `--include-recovered` is opt-in for Phase 3 (normalize). Since Phase 3 without Phase 6 has no recovered data anyway, this should be the default.

### Implementation Tasks

#### Task 2.1: Update `healthsparq/cli.py`

Change default and add opt-out flag:
```python
# Before
include_recovered: bool = typer.Option(
    False, "--include-recovered",
    help="Include recovered providers from Phase 6 in normalization (Phase 3)"
)

# After
exclude_recovered: bool = typer.Option(
    False, "--exclude-recovered", "--no-recovered",
    help="Exclude recovered providers from Phase 6 in normalization (Phase 3)"
)
```

Update Phase 3 call:
```python
results = run_normalize_sync(
    config, curr,
    storage_backend=storage_backend,
    include_recovered=not exclude_recovered,  # Default True
)
```

#### Task 2.2: Update `healthsparq/api.py`

Change `run_scraper_sync` signature:
```python
def run_scraper_sync(
    # ... existing params ...
    include_recovered: bool = True,  # Changed from False
):
```

#### Task 2.3: Update documentation

- `healthsparq/CLAUDE.md` - Update CLI examples
- `healthsparq/README.md` - Update usage docs

---

## 3. Multiple Phase Run Support

### Problem

Currently only single phase (`--phase N`) or all phases (no flag) are supported. Users need more flexibility.

### Proposed Syntax

| Syntax | Meaning | Example |
|--------|---------|---------|
| `--phase 2,3,5` | Run specific phases | Phases 2, 3, and 5 |
| `--phase 2-5` | Run phase range | Phases 2, 3, 4, 5 |
| `--from-phase 2` | Run from phase N onwards | Phases 2, 3, 4, 5, 6 |
| `--skip-phase 1` | Skip specific phase(s) | Phases 2, 3, 4, 5, 6 |
| `--phase 1-3,5` | Combined syntax | Phases 1, 2, 3, 5 |

### Implementation Tasks

#### Task 3.1: Create phase parser utility

**File**: `healthsparq/utils/phase_parser.py` (new file)

```python
"""Phase specification parser for CLI."""
from __future__ import annotations

import re
from typing import Set

ALL_PHASES = {1, 2, 3, 4, 5, 6}
DEFAULT_PHASES = {1, 2, 3}  # Default when no flags specified


def parse_phase_spec(spec: str) -> Set[int]:
    """Parse phase specification string.
    
    Supports:
    - Single: "2" -> {2}
    - List: "2,3,5" -> {2, 3, 5}
    - Range: "2-5" -> {2, 3, 4, 5}
    - Combined: "1-3,5" -> {1, 2, 3, 5}
    
    Args:
        spec: Phase specification string
        
    Returns:
        Set of phase numbers
        
    Raises:
        ValueError: If spec is invalid or contains invalid phase numbers
    """
    phases: Set[int] = set()
    
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
            
        if "-" in part:
            # Range: "2-5"
            match = re.match(r"^(\d+)-(\d+)$", part)
            if not match:
                raise ValueError(f"Invalid range format: {part}")
            start, end = int(match.group(1)), int(match.group(2))
            if start > end:
                raise ValueError(f"Invalid range: {start} > {end}")
            phases.update(range(start, end + 1))
        else:
            # Single: "2"
            if not part.isdigit():
                raise ValueError(f"Invalid phase number: {part}")
            phases.add(int(part))
    
    # Validate all phases are in valid range
    invalid = phases - ALL_PHASES
    if invalid:
        raise ValueError(f"Invalid phase numbers: {invalid}. Valid: 1-6")
    
    return phases


def resolve_phases(
    phase_spec: str | None = None,
    from_phase: int | None = None,
    skip_phases: str | None = None,
) -> Set[int]:
    """Resolve final set of phases to run.
    
    Priority: phase_spec > from_phase > skip_phases > default
    
    Args:
        phase_spec: Explicit phase specification (e.g., "2,3,5" or "2-5")
        from_phase: Run from this phase onwards
        skip_phases: Phases to skip (e.g., "1" or "1,2")
        
    Returns:
        Set of phases to run
    """
    if phase_spec:
        return parse_phase_spec(phase_spec)
    
    if from_phase is not None:
        if from_phase not in ALL_PHASES:
            raise ValueError(f"Invalid from_phase: {from_phase}. Valid: 1-6")
        return {p for p in ALL_PHASES if p >= from_phase}
    
    if skip_phases:
        to_skip = parse_phase_spec(skip_phases)
        return ALL_PHASES - to_skip
    
    return DEFAULT_PHASES
```

#### Task 3.2: Update `healthsparq/cli.py`

Replace single `--phase` with new options:
```python
from healthsparq.utils.phase_parser import resolve_phases, parse_phase_spec

@app.command()
def run(
    # ... existing options ...
    phase: str | None = typer.Option(
        None, "--phase", "-p",
        help="Phase(s) to run: single (2), list (2,3,5), or range (2-5)"
    ),
    from_phase: int | None = typer.Option(
        None, "--from-phase", "-f",
        help="Run from this phase onwards (e.g., 2 runs phases 2-6)"
    ),
    skip_phase: str | None = typer.Option(
        None, "--skip-phase", "-S",
        help="Skip specific phase(s): single (1) or list (1,2)"
    ),
):
    # Resolve phases
    try:
        phases_to_run = resolve_phases(phase, from_phase, skip_phase)
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    
    typer.echo(f"  Phases: {sorted(phases_to_run)}")
    
    # Run each phase in order
    for phase_num in sorted(phases_to_run):
        # ... run phase logic ...
```

#### Task 3.3: Update `healthsparq/api.py`

Change `phase: int | None` to `phases: Set[int] | None`:
```python
def run_scraper_sync(
    # ... existing params ...
    phases: Set[int] | None = None,  # None = default phases (1-3)
):
    """Run the scraper pipeline synchronously.
    
    Args:
        phases: Set of phases to run. If None, runs default phases (1-3).
                Valid phases: 1 (search), 2 (details), 3 (normalize),
                4 (qa), 5 (report), 6 (recovery)
    """
    phases_to_run = phases or {1, 2, 3}
    
    for phase_num in sorted(phases_to_run):
        if phase_num == 1:
            # Phase 1: Search
            ...
```

#### Task 3.4: Add phase dependency validation (optional warning)

```python
def validate_phase_dependencies(phases: Set[int], output_dir: Path, curr_date: str) -> list[str]:
    """Check if required outputs exist for phases.
    
    Returns list of warnings (not errors - allows user to proceed).
    """
    warnings = []
    
    # Phase 2 requires Phase 1 output
    if 2 in phases and 1 not in phases:
        search_dir = output_dir / curr_date / "raw" / "search_results"
        if not search_dir.exists() or not list(search_dir.glob("*.jsonl")):
            warnings.append("Phase 2 requires Phase 1 output (search_results not found)")
    
    # Phase 3 requires Phase 2 output
    if 3 in phases and 2 not in phases:
        details_dir = output_dir / curr_date / "raw" / "provider_details"
        if not details_dir.exists() or not list(details_dir.glob("*.json")):
            warnings.append("Phase 3 requires Phase 2 output (provider_details not found)")
    
    # Phase 4-6 require Phase 3 output
    if phases & {4, 5, 6} and 3 not in phases:
        processed_dir = output_dir / curr_date / "processed"
        if not list(processed_dir.glob("*.jsonl")):
            warnings.append("Phases 4-6 require Phase 3 output (JSONL not found)")
    
    return warnings
```

---

## 4. Sticky tqdm Progress View

### Problem

Current tqdm progress bars are created per-phase and scroll away with logs. Users want a persistent progress view at the bottom while logs scroll above.

### Solution

Use `rich` library for persistent progress panel with scrolling logs.

### Implementation Tasks

#### Task 4.1: Add `rich` dependency

**File**: `pyproject.toml`
```toml
dependencies = [
    # ... existing ...
    "rich>=13.0.0",
]
```

#### Task 4.2: Create progress manager

**File**: `healthsparq/utils/progress.py` (new file)

```python
"""Rich-based progress display with sticky footer."""
from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import Generator

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    MofNCompleteColumn,
)
from rich.table import Table


class PipelineProgress:
    """Manages progress display for multi-phase pipeline."""
    
    PHASE_NAMES = {
        1: "Search",
        2: "Details", 
        3: "Normalize",
        4: "QA",
        5: "Report",
        6: "Recovery",
    }
    
    def __init__(self, phases: set[int], console: Console | None = None):
        self.phases = sorted(phases)
        self.console = console or Console()
        self.current_phase: int | None = None
        self.phase_tasks: dict[int, int] = {}  # phase -> task_id
        
        # Overall progress
        self.overall_progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Overall"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
        )
        self.overall_task = self.overall_progress.add_task(
            "Pipeline", total=len(phases)
        )
        
        # Phase progress
        self.phase_progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeRemainingColumn(),
            console=self.console,
        )
        
        self._live: Live | None = None
    
    def _make_panel(self) -> Panel:
        """Create the progress panel."""
        table = Table.grid(padding=1)
        table.add_row(self.phase_progress)
        table.add_row(self.overall_progress)
        return Panel(
            table,
            title="[bold]Pipeline Progress",
            border_style="blue",
        )
    
    @contextmanager
    def live_display(self) -> Generator[None, None, None]:
        """Context manager for live progress display."""
        with Live(
            self._make_panel(),
            console=self.console,
            refresh_per_second=10,
            vertical_overflow="visible",
        ) as live:
            self._live = live
            try:
                yield
            finally:
                self._live = None
    
    def start_phase(self, phase: int, total: int, description: str | None = None) -> int:
        """Start a new phase progress bar.
        
        Returns task_id for updating progress.
        """
        self.current_phase = phase
        phase_name = description or self.PHASE_NAMES.get(phase, f"Phase {phase}")
        
        task_id = self.phase_progress.add_task(
            f"[Phase {phase}] {phase_name}",
            total=total,
        )
        self.phase_tasks[phase] = task_id
        
        if self._live:
            self._live.update(self._make_panel())
        
        return task_id
    
    def update_phase(self, advance: int = 1, **kwargs):
        """Update current phase progress."""
        if self.current_phase and self.current_phase in self.phase_tasks:
            task_id = self.phase_tasks[self.current_phase]
            self.phase_progress.update(task_id, advance=advance, **kwargs)
            
            if self._live:
                self._live.update(self._make_panel())
    
    def complete_phase(self, phase: int | None = None):
        """Mark a phase as complete."""
        phase = phase or self.current_phase
        if phase and phase in self.phase_tasks:
            task_id = self.phase_tasks[phase]
            self.phase_progress.update(task_id, completed=self.phase_progress.tasks[task_id].total)
        
        self.overall_progress.update(self.overall_task, advance=1)
        
        if self._live:
            self._live.update(self._make_panel())
    
    def log(self, message: str, style: str = ""):
        """Log a message above the progress panel."""
        if self._live:
            self.console.print(message, style=style)


# Global progress instance for CLI
_progress: PipelineProgress | None = None


def get_progress() -> PipelineProgress | None:
    """Get the global progress instance."""
    return _progress


@contextmanager
def pipeline_progress(phases: set[int]) -> Generator[PipelineProgress, None, None]:
    """Context manager for pipeline progress display.
    
    Usage:
        with pipeline_progress({1, 2, 3}) as progress:
            progress.start_phase(1, total=100)
            for item in items:
                process(item)
                progress.update_phase()
            progress.complete_phase()
    """
    global _progress
    
    # Disable if not a TTY
    if not sys.stdout.isatty():
        yield None  # type: ignore
        return
    
    progress = PipelineProgress(phases)
    _progress = progress
    
    try:
        with progress.live_display():
            yield progress
    finally:
        _progress = None
```

#### Task 4.3: Integrate into CLI

**File**: `healthsparq/cli.py`

```python
from healthsparq.utils.progress import pipeline_progress

@app.command()
def run(...):
    # ... setup ...
    
    with pipeline_progress(phases_to_run) as progress:
        for phase_num in sorted(phases_to_run):
            if phase_num == 1:
                if progress:
                    progress.start_phase(1, total=len(counties), description="County search")
                results = run_search_sync(config, curr, progress_callback=progress.update_phase if progress else None)
                if progress:
                    progress.complete_phase()
            # ... other phases ...
```

#### Task 4.4: Add progress callback to phase functions

Update each phase to accept optional progress callback:
```python
def run_search_sync(
    config: HealthSparqProjectConfig,
    curr_date: str,
    # ... existing params ...
    progress_callback: Callable[[], None] | None = None,
) -> dict[str, list[SearchResult]]:
    """Run search phase.
    
    Args:
        progress_callback: Optional callback to update progress bar
    """
    for county in counties:
        result = search_county(county)
        if progress_callback:
            progress_callback()
```

---

## 5. Thin Wrapper Pattern for Per-Project `run.py`

### Problem

Per-project `run.py` files duplicate CLI logic from `healthsparq/cli.py`. Need a thin wrapper that:
- Loads project-specific config from local `config.yaml`
- Supports custom mappers from local `mapper.py`
- Delegates all CLI logic to central implementation

### Implementation Tasks

#### Task 5.1: Create project app factory

**File**: `healthsparq/cli.py` (add to existing)

```python
from pathlib import Path
from typing import Callable

from healthsparq.phases import MapperFunc


def create_project_cli(
    project_dir: Path,
    mapper: MapperFunc | None = None,
    custom_commands: dict[str, Callable] | None = None,
) -> typer.Typer:
    """Create a Typer CLI app for a project directory.
    
    This is the thin wrapper factory for per-project run.py files.
    
    Args:
        project_dir: Path to project directory (contains config.yaml)
        mapper: Optional custom mapper function for Phase 3 normalization
        custom_commands: Optional dict of additional commands to register
        
    Returns:
        Configured Typer app
        
    Example:
        # In audiobee_my_project/run.py
        from pathlib import Path
        from healthsparq.cli import create_project_cli
        from mapper import my_mapper
        
        app = create_project_cli(
            project_dir=Path(__file__).parent,
            mapper=my_mapper,
        )
        
        if __name__ == "__main__":
            app()
    """
    from healthsparq.config import load_config
    
    # Load config once
    config_path = project_dir / "config.yaml"
    if not config_path.exists():
        # Fall back to looking up in healthsparq/configs/
        config = None
    else:
        config = load_config(config_path)
    
    project_name = config.project.name if config else project_dir.name
    
    app = typer.Typer(
        name=project_name,
        help=f"{project_name} provider directory scraper",
        add_completion=False,
    )
    
    @app.command()
    def run(
        curr: str = typer.Option(..., "--curr", "-c", help="Current date (YYYYMMDD)"),
        prev: str | None = typer.Option(None, "--prev", help="Previous date (YYYYMMDD)"),
        phase: str | None = typer.Option(None, "--phase", "-p", help="Phase(s) to run"),
        from_phase: int | None = typer.Option(None, "--from-phase", "-f", help="Run from phase N onwards"),
        skip_phase: str | None = typer.Option(None, "--skip-phase", "-S", help="Skip phase(s)"),
        storage: str = typer.Option("sqlite", "--storage", "-s", help="Storage backend"),
        exclude_recovered: bool = typer.Option(False, "--no-recovered", help="Exclude recovered providers"),
        qa: bool = typer.Option(False, "--qa", help="Run QA phase"),
        report: bool = typer.Option(False, "--report", help="Run Report phase"),
        recover: bool = typer.Option(False, "--recover", help="Run Recovery phase"),
        strict: bool = typer.Option(False, "--strict", help="Exit on failures"),
        dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would run"),
    ):
        """Run the scraper pipeline."""
        from healthsparq.utils.phase_parser import resolve_phases
        from healthsparq.config.schema import StorageBackend
        
        # Use project-local config if available
        cfg = config or load_config(project_dir / "config.yaml")
        
        # Resolve phases
        phases_to_run = resolve_phases(phase, from_phase, skip_phase)
        
        # Add optional phases
        if qa:
            phases_to_run.add(4)
        if report:
            phases_to_run.add(5)
        if recover and prev:
            phases_to_run.add(6)
        
        if dry_run:
            typer.echo(f"Would run phases: {sorted(phases_to_run)}")
            typer.echo(f"  Config: {cfg.project.name}")
            typer.echo(f"  Mapper: {'custom' if mapper else 'default'}")
            return
        
        # Map storage string to enum
        storage_backend = StorageBackend(storage.lower())
        
        # Run with project-specific mapper
        from healthsparq import run_scraper_sync
        
        result = run_scraper_sync(
            config=cfg,
            curr_date=curr,
            prev_date=prev,
            phases=phases_to_run,
            output_dir=project_dir,
            mapper=mapper,  # Project-specific mapper
            storage_backend=storage_backend,
            include_recovered=not exclude_recovered,
        )
        
        if result.success:
            typer.echo(f"Completed: {result.providers_count} providers")
        else:
            typer.echo(f"Failed: {result.error}", err=True)
            raise typer.Exit(1)
    
    @app.command()
    def validate():
        """Validate project configuration."""
        cfg = config or load_config(project_dir / "config.yaml")
        typer.echo(f"Configuration valid: {cfg.project.name}")
        typer.echo(f"  Domain: {cfg.site.domain}")
        typer.echo(f"  Plans: {len(cfg.plans)}")
        typer.echo(f"  States: {', '.join(cfg.coverage.states)}")
        if mapper:
            typer.echo(f"  Custom mapper: yes")
    
    # Register custom commands
    if custom_commands:
        for name, func in custom_commands.items():
            app.command(name)(func)
    
    return app
```

#### Task 5.2: Update template

**File**: `healthsparq/templates/run.py.template`

```python
#!/usr/bin/env python
"""{{PROJECT_NAME}} scraper CLI.

Thin wrapper using healthsparq.cli.create_project_cli().
"""
from pathlib import Path

from healthsparq.cli import create_project_cli

# Optional: import custom mapper
# from mapper import my_custom_mapper
# mapper = my_custom_mapper

# Use None for default mapper
mapper = None

# Create CLI app with project-specific settings
app = create_project_cli(
    project_dir=Path(__file__).parent,
    mapper=mapper,
)

if __name__ == "__main__":
    app()
```

This reduces the template from 164 lines to ~20 lines while preserving all functionality.

---

## Summary of Files to Modify/Create

### New Files
| File | Purpose |
|------|---------|
| `healthsparq/utils/phase_parser.py` | Phase specification parser |
| `healthsparq/utils/progress.py` | Rich-based progress manager |

### Modified Files
| File | Changes |
|------|---------|
| `core/qa/reporter.py` | Add extended metrics from output_generator |
| `healthsparq/cli.py` | Add phase parser, progress, create_project_cli |
| `healthsparq/api.py` | Change phase param to phases Set, include_recovered default |
| `healthsparq/phases/report.py` | Pass hsparq flag and raw_dir to reporter |
| `healthsparq/templates/run.py.template` | Thin wrapper pattern |
| `pyproject.toml` | Add rich dependency |

### Documentation Updates
| File | Changes |
|------|---------|
| `healthsparq/CLAUDE.md` | Update CLI examples, phase syntax |
| `healthsparq/README.md` | Update usage docs |

---

## Implementation Order

1. **Phase Parser** (Task 3.1) - Foundation for other features
2. **Include Recovered Default** (Task 2.1-2.3) - Simple change
3. **Multiple Phase Run** (Task 3.2-3.4) - Depends on parser
4. **Report Generator** (Task 1.1-1.3) - Independent, can parallel
5. **Progress Display** (Task 4.1-4.4) - Depends on phase runner changes
6. **Thin Wrapper** (Task 5.1-5.2) - Depends on all CLI changes

---

## Testing Plan

1. **Unit tests for phase parser**
   - Valid specs: "2", "2,3,5", "2-5", "1-3,5"
   - Invalid specs: "7", "a", "3-1", ""
   
2. **Integration tests for CLI**
   - `--phase 2-5` runs correct phases
   - `--from-phase 3` skips 1-2
   - `--skip-phase 1` runs 2-6
   - Default includes recovered
   
3. **Report generation tests**
   - Extended metrics match output_generator format
   - File timestamps extracted correctly
   - In-scope/out-of-scope counts correct

4. **Progress display tests**
   - Disabled when not TTY
   - Updates correctly during pipeline
   - Handles errors gracefully

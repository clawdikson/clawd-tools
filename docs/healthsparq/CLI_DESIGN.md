# HealthSparq CLI Design

## Overview

The HealthSparq CLI uses [Typer](https://typer.tiangolo.com/) for command-line interface with rich help text, argument validation, and shell completion support.

---

## Command Structure

```
healthsparq
├── run          # Run scraper for a project
├── list         # List available projects
├── validate     # Validate project configuration
├── init         # Initialize new project config
├── compare      # Compare outputs between runs
└── status       # Show running/completed jobs
```

---

## CLI Implementation

### Main Entry Point

```python
# healthsparq/cli.py
import typer
from typing import Optional, Annotated
from pathlib import Path
from enum import Enum

app = typer.Typer(
    name="healthsparq",
    help="Unified HealthSparq provider directory scraper",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

class Phase(str, Enum):
    """Pipeline phases."""
    ALL = "all"
    SEARCH = "1"
    DETAILS = "2"
    NORMALIZE = "3"


@app.command()
def run(
    project: Annotated[str, typer.Argument(
        help="Project slug (e.g., christus_health_plan, excellus)"
    )],
    curr_date: Annotated[str, typer.Option(
        "--curr", "-c",
        help="Current run date [bold](YYYYMMDD)[/bold]"
    )],
    prev_date: Annotated[Optional[str], typer.Option(
        "--prev", "-p",
        help="Previous run date for comparison"
    )] = None,
    phase: Annotated[Phase, typer.Option(
        "--phase",
        help="Run specific phase only"
    )] = Phase.ALL,
    workers: Annotated[Optional[int], typer.Option(
        "--workers", "-w",
        min=1, max=500,
        help="Override max concurrent workers"
    )] = None,
    plans: Annotated[Optional[str], typer.Option(
        "--plans",
        help="Comma-separated plan codes to run (default: all)"
    )] = None,
    states: Annotated[Optional[str], typer.Option(
        "--states",
        help="Comma-separated state codes to run (default: all)"
    )] = None,
    dry_run: Annotated[bool, typer.Option(
        "--dry-run",
        help="Validate config and show plan without executing"
    )] = False,
    verbose: Annotated[bool, typer.Option(
        "--verbose", "-v",
        help="Enable verbose logging"
    )] = False,
):
    """
    Run the scraper pipeline for a project.

    [bold]Examples:[/bold]

        # Run full pipeline
        healthsparq run christus_health_plan --curr 20251214

        # Run with comparison
        healthsparq run excellus --curr 20251214 --prev 20251114

        # Run only search phase
        healthsparq run bluecard_national --curr 20251214 --phase 1

        # Run specific plans only
        healthsparq run christus_health_plan --curr 20251214 --plans MA,HIX

        # Run specific states only
        healthsparq run bluecard_national --curr 20251214 --states TX,CA,NY

        # Dry run to validate config
        healthsparq run excellus --curr 20251214 --dry-run
    """
    from .runner import PipelineRunner
    from .config import load_config

    # Load and validate config
    config = load_config(project)

    # Apply CLI overrides
    if workers:
        config.concurrency.max_workers = workers
    if plans:
        plan_codes = [p.strip() for p in plans.split(",")]
        config.plans = [p for p in config.plans if p.product_code in plan_codes]
    if states:
        state_codes = [s.strip().upper() for s in states.split(",")]
        config.coverage.states = state_codes

    if dry_run:
        _show_dry_run(config, curr_date, prev_date, phase)
        return

    # Execute pipeline
    runner = PipelineRunner(config, curr_date, prev_date, verbose)
    runner.run(phase)


@app.command("list")
def list_projects(
    verbose: Annotated[bool, typer.Option(
        "--verbose", "-v",
        help="Show detailed project info"
    )] = False,
):
    """
    List all available project configurations.

    [bold]Examples:[/bold]

        healthsparq list
        healthsparq list --verbose
    """
    from .config import list_projects, load_config
    from rich.console import Console
    from rich.table import Table

    console = Console()
    projects = list_projects()

    if verbose:
        table = Table(title="HealthSparq Projects")
        table.add_column("Slug", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("States", style="yellow")
        table.add_column("Plans", style="magenta")

        for slug in sorted(projects):
            try:
                config = load_config(slug)
                table.add_row(
                    slug,
                    config.project.name,
                    ", ".join(config.coverage.states[:3]) + ("..." if len(config.coverage.states) > 3 else ""),
                    str(len(config.plans)),
                )
            except Exception as e:
                table.add_row(slug, f"[red]Error: {e}[/red]", "-", "-")

        console.print(table)
    else:
        console.print("[bold]Available projects:[/bold]")
        for slug in sorted(projects):
            console.print(f"  - {slug}")


@app.command()
def validate(
    project: Annotated[str, typer.Argument(
        help="Project slug to validate"
    )],
):
    """
    Validate project configuration.

    [bold]Examples:[/bold]

        healthsparq validate christus_health_plan
    """
    from .config import load_config
    from rich.console import Console
    from rich.panel import Panel

    console = Console()

    try:
        config = load_config(project)
        console.print(Panel(
            f"[green]Configuration valid![/green]\n\n"
            f"[bold]Project:[/bold] {config.project.name}\n"
            f"[bold]Domain:[/bold] {config.site.domain}\n"
            f"[bold]States:[/bold] {', '.join(config.coverage.states)}\n"
            f"[bold]Plans:[/bold] {len(config.plans)}\n"
            f"[bold]Max Workers:[/bold] {config.concurrency.max_workers}",
            title=f"[cyan]{project}[/cyan]"
        ))
    except Exception as e:
        console.print(f"[red]Validation failed:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def init(
    slug: Annotated[str, typer.Argument(
        help="Project slug (e.g., new_carrier)"
    )],
    domain: Annotated[str, typer.Option(
        "--domain", "-d",
        help="HealthSparq domain"
    )],
    states: Annotated[str, typer.Option(
        "--states", "-s",
        help="Comma-separated state codes"
    )],
    brand_code: Annotated[Optional[str], typer.Option(
        "--brand",
        help="Brand code (defaults to uppercase slug)"
    )] = None,
    insurer_code: Annotated[Optional[str], typer.Option(
        "--insurer",
        help="Insurer code (defaults to uppercase slug)"
    )] = None,
):
    """
    Initialize a new project configuration.

    [bold]Examples:[/bold]

        healthsparq init new_carrier --domain newcarrier.healthsparq.com --states NY,NJ

        healthsparq init my_plan --domain myplan.healthsparq.com --states TX --brand MYPLAN
    """
    from pathlib import Path
    import yaml

    config_dir = Path(__file__).parent / "configs"
    config_path = config_dir / f"{slug}.yaml"

    if config_path.exists():
        typer.confirm(f"Config {slug}.yaml already exists. Overwrite?", abort=True)

    state_list = [s.strip().upper() for s in states.split(",")]

    config = {
        "project": {
            "name": f"audiobee_{slug}",
            "slug": slug,
            "description": f"TODO: Add description",
            "version": "1.0",
        },
        "site": {
            "domain": domain,
            "brand_code": brand_code or slug.upper(),
            "insurer_code": insurer_code or slug.upper(),
            "api_version": "v4",
        },
        "plans": [
            {"product_code": "TODO", "name": "TODO: Add plans"},
        ],
        "coverage": {
            "states": state_list,
        },
    }

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    typer.echo(f"Created config: {config_path}")
    typer.echo("Edit the file to add plans and customize settings.")


@app.command()
def compare(
    project: Annotated[str, typer.Argument(
        help="Project slug"
    )],
    curr_date: Annotated[str, typer.Option(
        "--curr", "-c",
        help="Current run date"
    )],
    prev_date: Annotated[str, typer.Option(
        "--prev", "-p",
        help="Previous run date"
    )],
    output: Annotated[Optional[Path], typer.Option(
        "--output", "-o",
        help="Output path for comparison report"
    )] = None,
):
    """
    Compare outputs between two runs.

    [bold]Examples:[/bold]

        healthsparq compare christus_health_plan --curr 20251214 --prev 20251114

        healthsparq compare excellus --curr 20251214 --prev 20251114 -o report.xlsx
    """
    from .comparison import run_comparison
    from rich.console import Console

    console = Console()
    result = run_comparison(project, curr_date, prev_date, output)

    console.print(f"\n[bold]Comparison Results:[/bold]")
    console.print(f"  Previous: {result['prev_count']:,} providers")
    console.print(f"  Current:  {result['curr_count']:,} providers")
    console.print(f"  Added:    [green]+{result['added']:,}[/green]")
    console.print(f"  Removed:  [red]-{result['removed']:,}[/red]")
    console.print(f"  Changed:  [yellow]{result['changed']:,}[/yellow]")


@app.command()
def status():
    """
    Show status of running and recent jobs.
    """
    from .status import get_job_status
    from rich.console import Console
    from rich.table import Table

    console = Console()
    jobs = get_job_status()

    if not jobs:
        console.print("[dim]No recent jobs found.[/dim]")
        return

    table = Table(title="Recent Jobs")
    table.add_column("Project", style="cyan")
    table.add_column("Date", style="green")
    table.add_column("Phase", style="yellow")
    table.add_column("Status", style="magenta")
    table.add_column("Progress")

    for job in jobs:
        status_color = {
            "running": "blue",
            "completed": "green",
            "failed": "red",
        }.get(job["status"], "white")

        table.add_row(
            job["project"],
            job["date"],
            job["phase"],
            f"[{status_color}]{job['status']}[/{status_color}]",
            job.get("progress", "-"),
        )

    console.print(table)


def _show_dry_run(config, curr_date, prev_date, phase):
    """Display dry run information."""
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    console.print(Panel(
        f"[bold]Project:[/bold] {config.project.name}\n"
        f"[bold]Domain:[/bold] {config.site.domain}\n"
        f"[bold]Current Date:[/bold] {curr_date}\n"
        f"[bold]Previous Date:[/bold] {prev_date or 'None'}\n"
        f"[bold]Phase:[/bold] {phase.value}\n"
        f"[bold]States:[/bold] {', '.join(config.coverage.states)}\n"
        f"[bold]Plans:[/bold] {len(config.plans)}\n"
        f"[bold]Max Workers:[/bold] {config.concurrency.max_workers}\n\n"
        f"[yellow]Dry run mode - no actions taken[/yellow]",
        title="[cyan]Execution Plan[/cyan]"
    ))


if __name__ == "__main__":
    app()
```

---

## Usage Examples

### Basic Usage

```bash
# Run full pipeline for a project
healthsparq run christus_health_plan --curr 20251214

# Run with previous date comparison
healthsparq run excellus --curr 20251214 --prev 20251114

# Run specific phase only
healthsparq run bluecard_national --curr 20251214 --phase 1

# List available projects
healthsparq list
healthsparq list --verbose
```

### Advanced Usage

```bash
# Override concurrency
healthsparq run christus_health_plan --curr 20251214 --workers 50

# Run specific plans only
healthsparq run christus_health_plan --curr 20251214 --plans MA,HIX

# Run specific states only (useful for bluecard_national)
healthsparq run bluecard_national --curr 20251214 --states TX,CA,NY

# Dry run to validate
healthsparq run excellus --curr 20251214 --dry-run --verbose

# Compare runs
healthsparq compare christus_health_plan --curr 20251214 --prev 20251114
```

### Project Management

```bash
# Validate configuration
healthsparq validate christus_health_plan

# Initialize new project
healthsparq init new_carrier --domain newcarrier.healthsparq.com --states NY,NJ

# Check job status
healthsparq status
```

---

## Shell Completion

```bash
# Install shell completion (bash)
healthsparq --install-completion bash

# Install shell completion (zsh)
healthsparq --install-completion zsh

# Show completion script
healthsparq --show-completion
```

---

## Environment Variables

| Variable                 | Description                               | Default               |
| ------------------------ | ----------------------------------------- | --------------------- |
| `HEALTHSPARQ_CONFIG_DIR` | Config directory path                     | `healthsparq/configs` |
| `HEALTHSPARQ_OUTPUT_DIR` | Output directory path                     | Current directory     |
| `HEALTHSPARQ_LOG_LEVEL`  | Log level (DEBUG, INFO, WARNING, ERROR)   | `INFO`                |
| `HEALTHSPARQ_PROXY_TYPE` | Proxy type (DATAIMPULSE, SURFSHARK, NONE) | `DATAIMPULSE`         |

---

## Exit Codes

| Code | Meaning             |
| ---- | ------------------- |
| 0    | Success             |
| 1    | Configuration error |
| 2    | Runtime error       |
| 3    | Network/API error   |
| 4    | Validation failure  |

---

## Integration with run_parallel.py

The CLI can be used with `tools/run_parallel.py` for batch execution:

```bash
# Create project list
cat > projects/healthsparq.txt << EOF
christus_health_plan
excellus
ibx
mvp_health
bluecard_national
EOF

# Run in parallel (uses python -m healthsparq internally)
python tools/run_parallel.py \
  --list projects/healthsparq.txt \
  --workers 3 \
  --curr 20251214 \
  --prev 20251114 \
  --module healthsparq
```

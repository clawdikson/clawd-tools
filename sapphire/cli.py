"""
Sapphire CLI - Command Line Interface for Sapphire scrapers.

Usage:
    python -m sapphire run molina --curr 20251230
    python -m sapphire list
    python -m sapphire validate molina
    python -m sapphire doctor
"""

from pathlib import Path
from typing import Optional

import typer

from sapphire.config.loader import list_projects, load_config
from sapphire.config.schema import StorageBackend

app = typer.Typer(
    name="sapphire",
    help="Sapphire provider directory scraper for ProviderFinderOnline sites.",
    add_completion=False,
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        from sapphire import __version__
        typer.echo(f"sapphire {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Sapphire provider directory scraper."""
    pass


@app.command()
def list_cmd() -> None:
    """List all available Sapphire projects."""
    projects = list_projects()
    typer.echo(f"Available projects ({len(projects)}):\n")
    for project in projects:
        try:
            config = load_config(project)
            typer.echo(f"  {project}: {config.project.name}")
        except Exception as e:
            typer.echo(f"  {project}: (error: {e})")


# Rename to avoid conflict with built-in list
app.command(name="list")(list_cmd)


@app.command()
def validate(
    project: str = typer.Argument(..., help="Project slug to validate"),
) -> None:
    """Validate a project configuration."""
    try:
        config = load_config(project)
        typer.echo(f"[OK] {project}: {config.project.name}")
        typer.echo(f"     Site: {config.site.domain}")
        typer.echo(f"     States: {', '.join(config.coverage.states)}")
        typer.echo(f"     Networks: {len(config.networks)}")
        typer.echo(f"     Storage: {config.output.storage_backend.value}")
    except FileNotFoundError:
        typer.echo(f"[ERROR] Config not found: {project}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"[ERROR] {project}: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def doctor() -> None:
    """Validate all project configurations."""
    projects = list_projects()
    errors = []

    typer.echo(f"Validating {len(projects)} projects...\n")

    for project in projects:
        try:
            config = load_config(project)
            typer.echo(f"  [OK] {project}")
        except Exception as e:
            typer.echo(f"  [ERROR] {project}: {e}")
            errors.append((project, str(e)))

    typer.echo("")
    if errors:
        typer.echo(f"Found {len(errors)} invalid configs.", err=True)
        raise typer.Exit(1)
    else:
        typer.echo(f"All {len(projects)} configs valid.")


@app.command()
def run(
    project: str = typer.Argument(..., help="Project slug (e.g., molina, bcbs_il)"),
    curr: str = typer.Option(..., "--curr", help="Current date (YYYYMMDD)"),
    prev: Optional[str] = typer.Option(None, "--prev", help="Previous date for comparison"),
    phase: Optional[int] = typer.Option(
        None, "--phase", help="Run specific phase (1-5), or all if not specified"
    ),
    storage: Optional[str] = typer.Option(
        None, "--storage", help="Storage backend: sqlite, json_files, jsonl"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate without executing"),
    # Phase 4 (QA) flags
    qa: bool = typer.Option(False, "--qa", help="Run full QA phase (validation + comparison)"),
    validate_only: bool = typer.Option(
        False, "--validate", help="Run schema validation only (Phase 4a)"
    ),
    compare: bool = typer.Option(
        False, "--compare", help="Run comparison only (Phase 4b, requires --prev)"
    ),
    # Phase 5 (Report) flags
    report: bool = typer.Option(False, "--report", help="Generate Excel reports and samples"),
    excel: bool = typer.Option(False, "--excel", help="Generate Excel report only (Phase 5a)"),
    samples_only: bool = typer.Option(
        False, "--samples-only", help="Generate samples only (Phase 5b)"
    ),
    sample_count: int = typer.Option(10, "--sample-count", help="Number of samples to generate"),
) -> None:
    """Run Sapphire scraper for a project."""
    from sapphire.api import run_scraper_sync

    # Validate date format
    if len(curr) != 8 or not curr.isdigit():
        typer.echo("Error: --curr must be YYYYMMDD format", err=True)
        raise typer.Exit(2)

    if prev and (len(prev) != 8 or not prev.isdigit()):
        typer.echo("Error: --prev must be YYYYMMDD format", err=True)
        raise typer.Exit(2)

    # Load config
    try:
        config = load_config(project)
    except FileNotFoundError:
        typer.echo(f"Error: Project not found: {project}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Error loading config: {e}", err=True)
        raise typer.Exit(1)

    # Override storage backend if specified
    storage_backend = None
    if storage:
        try:
            storage_backend = StorageBackend(storage.lower())
        except ValueError:
            typer.echo(f"Error: Invalid storage backend: {storage}", err=True)
            typer.echo("Valid options: sqlite, json_files, jsonl")
            raise typer.Exit(2)

    if dry_run:
        typer.echo(f"[DRY RUN] Would run {project} for {curr}")
        typer.echo(f"  Config: {config.project.name}")
        typer.echo(f"  States: {', '.join(config.coverage.states)}")
        typer.echo(f"  Networks: {len(config.networks)}")
        if phase:
            typer.echo(f"  Phase: {phase}")
        else:
            typer.echo("  Phases: 1-3 (all)")
        if storage_backend:
            typer.echo(f"  Storage: {storage_backend.value}")
        return

    typer.echo(f"Running {project} for {curr}...")

    try:
        result = run_scraper_sync(
            config=config,
            curr_date=curr,
            prev_date=prev,
            phase=phase,
            storage_backend=storage_backend,
            run_qa=qa,
            run_validate=validate_only,
            run_compare=compare,
            run_report=report,
            run_excel=excel,
            run_samples=samples_only,
            sample_count=sample_count,
        )

        if result.success:
            typer.echo(f"\n[SUCCESS] {project}")
            typer.echo(f"  Providers: {result.providers_count}")
            for phase_num, phase_result in result.phase_results.items():
                status = "OK" if phase_result.success else "FAILED"
                typer.echo(f"  Phase {phase_num}: {status} - {phase_result.message}")
        else:
            typer.echo(f"\n[FAILED] {project}: {result.error}", err=True)
            raise typer.Exit(1)

    except Exception as e:
        typer.echo(f"\n[ERROR] {project}: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()

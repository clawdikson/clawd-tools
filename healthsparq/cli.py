"""HealthSparq CLI.

Provides command-line interface for running scrapers and managing configurations.
"""

from pathlib import Path
from typing import Optional

import typer

from healthsparq import __version__
from healthsparq.config import HealthSparqProjectConfig, list_projects, load_config

app = typer.Typer(
    name="healthsparq",
    help="Unified HealthSparq scraper CLI",
    add_completion=False,
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"healthsparq {__version__}")
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
    """HealthSparq unified scraper CLI."""
    pass


@app.command("list")
def list_cmd(
    count: bool = typer.Option(False, "--count", "-c", help="Show project count only"),
) -> None:
    """List available project configurations."""
    projects = list_projects()
    if count:
        typer.echo(len(projects))
    else:
        typer.echo("Available projects:")
        for proj in projects:
            typer.echo(f"  - {proj}")
        typer.echo(f"\nTotal: {len(projects)} projects")


@app.command()
def validate(
    project: str = typer.Argument(..., help="Project slug to validate"),
) -> None:
    """Validate a project configuration."""
    try:
        config = load_config(project)
        typer.echo(f"Configuration valid: {project}")
        typer.echo(f"  Name: {config.project.name}")
        typer.echo(f"  Domain: {config.site.domain}")
        typer.echo(f"  Plans: {len(config.plans)}")
        typer.echo(f"  States: {', '.join(config.coverage.states)}")
    except FileNotFoundError:
        typer.echo(f"Error: Project '{project}' not found", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Error validating '{project}': {e}", err=True)
        raise typer.Exit(1)


@app.command()
def run(
    project: str = typer.Argument(..., help="Project slug to run"),
    curr: str = typer.Option(..., "--curr", help="Current date (YYYYMMDD)"),
    prev: Optional[str] = typer.Option(None, "--prev", help="Previous date (YYYYMMDD)"),
    phase: Optional[int] = typer.Option(
        None, "--phase", "-p", help="Run specific phase only (1, 2, or 3)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be done without executing"
    ),
) -> None:
    """Run a scraper for a specific project."""
    try:
        config = load_config(project)
    except FileNotFoundError:
        typer.echo(f"Error: Project '{project}' not found", err=True)
        raise typer.Exit(1)

    if dry_run:
        typer.echo("Dry run mode - no changes will be made")
        typer.echo(f"\nWould run scraper for: {project}")
        typer.echo(f"  Current date: {curr}")
        typer.echo(f"  Previous date: {prev or 'not specified'}")
        typer.echo(f"  Phase: {phase or 'all'}")
        typer.echo(f"  Domain: {config.site.domain}")
        typer.echo(f"  Plans: {len(config.plans)}")
        for plan in config.plans:
            typer.echo(f"    - {plan.product_code}: {plan.name}")
        typer.echo(f"  States: {', '.join(config.coverage.states)}")
        typer.echo(f"  Max workers: {config.concurrency.max_workers}")
        return

    # Execute the scraper phases
    typer.echo(f"Running scraper for: {project}")
    typer.echo(f"  Current date: {curr}")
    typer.echo(f"  Previous date: {prev or 'not specified'}")
    typer.echo(f"  Phase: {phase or 'all'}")

    from healthsparq.phases import run_search_sync, run_details_sync, run_normalize_sync

    # Phase 1: Search
    if phase is None or phase == 1:
        typer.echo("\n[Phase 1] Running search phase...")
        try:
            results = run_search_sync(config, curr)
            total_providers = sum(
                sum(r.total_providers_found for r in plan_results)
                for plan_results in results.values()
            )
            typer.echo(f"  Search complete: {total_providers} providers found")
        except Exception as e:
            typer.echo(f"  Error in search phase: {e}", err=True)
            raise typer.Exit(1)

    # Phase 2: Details
    if phase is None or phase == 2:
        typer.echo("\n[Phase 2] Running details phase...")
        try:
            results = run_details_sync(config, curr)
            typer.echo(f"  Details complete: {results.providers_processed} providers processed")
        except Exception as e:
            typer.echo(f"  Error in details phase: {e}", err=True)
            raise typer.Exit(1)

    # Phase 3: Normalize
    if phase is None or phase == 3:
        typer.echo("\n[Phase 3] Running normalize phase...")
        try:
            results = run_normalize_sync(config, curr)
            typer.echo(f"  Normalize complete: {results.total_output} records written")
        except Exception as e:
            typer.echo(f"  Error in normalize phase: {e}", err=True)
            raise typer.Exit(1)

    typer.echo("\nScraper completed successfully!")


@app.command()
def doctor() -> None:
    """Run health checks on the configuration system."""
    typer.echo("Running health checks...\n")

    # Check all configs are valid
    projects = list_projects()
    valid_count = 0
    errors = []

    for proj in projects:
        try:
            load_config(proj)
            valid_count += 1
        except Exception as e:
            errors.append((proj, str(e)))

    typer.echo(f"Projects found: {len(projects)}")
    typer.echo(f"Valid configs: {valid_count}")

    if errors:
        typer.echo(f"\nErrors ({len(errors)}):")
        for proj, err in errors:
            typer.echo(f"  - {proj}: {err}")
        raise typer.Exit(1)
    else:
        typer.echo("\nAll health checks passed!")


if __name__ == "__main__":
    app()

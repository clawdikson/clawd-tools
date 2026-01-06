#!/usr/bin/env python
"""
Project Registry - Query and manage project metadata from projects.yaml.

Usage:
    python tools/project_registry.py list                      # List all projects
    python tools/project_registry.py list --site-type sapphire # Filter by site type
    python tools/project_registry.py list --state TX           # Filter by state
    python tools/project_registry.py list --coverage medicaid  # Filter by coverage
    python tools/project_registry.py show audiobee_bcbs_il     # Show project details
    python tools/project_registry.py stats                     # Show statistics
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
import yaml

app = typer.Typer(help="Query project metadata from projects.yaml manifest")

# Resolve manifest path relative to this file
MANIFEST_PATH = Path(__file__).parent.parent / "projects.yaml"


def load_manifest() -> dict:
    """Load the projects.yaml manifest."""
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Manifest not found: {MANIFEST_PATH}")
    with open(MANIFEST_PATH) as f:
        return yaml.safe_load(f)


def get_projects() -> dict:
    """Get all projects from manifest."""
    return load_manifest().get("projects", {})


def get_site_types() -> dict:
    """Get site type definitions."""
    return load_manifest().get("site_types", {})


def get_coverage_types() -> dict:
    """Get coverage type definitions."""
    return load_manifest().get("coverage_types", {})


def get_projects_by_site_type(site_type: str) -> list[str]:
    """Get all projects of a specific site type."""
    projects = get_projects()
    return [
        name
        for name, config in projects.items()
        if config.get("site_type") == site_type
    ]


def get_projects_by_state(state: str) -> list[str]:
    """Get all projects covering a specific state."""
    state = state.upper()
    projects = get_projects()
    return [
        name
        for name, config in projects.items()
        if state in config.get("states", []) or "ALL" in config.get("states", [])
    ]


def get_projects_by_coverage(coverage: str) -> list[str]:
    """Get all projects with a specific coverage type."""
    coverage = coverage.lower()
    projects = get_projects()
    return [
        name
        for name, config in projects.items()
        if coverage in config.get("coverage", [])
    ]


def get_project_info(project_name: str) -> Optional[dict]:
    """Get detailed info for a specific project."""
    projects = get_projects()
    return projects.get(project_name)


def get_projects_by_status(status: str) -> list[str]:
    """Get all projects with a specific status."""
    status = status.lower()
    projects = get_projects()
    return [
        name
        for name, config in projects.items()
        if config.get("status", "active") == status
    ]


def get_project_dir(project_name: str) -> str:
    """Get the actual directory name for a project (handles dir_name override)."""
    info = get_project_info(project_name)
    if info and info.get("dir_name"):
        return info["dir_name"]
    return project_name


@app.command()
def list(
    site_type: Optional[str] = typer.Option(
        None, "--site-type", "-t", help="Filter by site type (carrier, healthsparq, sapphire, anthem, etc.)"
    ),
    state: Optional[str] = typer.Option(
        None, "--state", "-s", help="Filter by state (e.g., TX, CA, NY)"
    ),
    coverage: Optional[str] = typer.Option(
        None, "--coverage", "-c", help="Filter by coverage type (medicare_advantage, medicaid, aca, large_group)"
    ),
    status: Optional[str] = typer.Option(
        None, "--status", help="Filter by status (active, not_implemented, archived)"
    ),
    names_only: bool = typer.Option(
        False, "--names-only", "-n", help="Output project names only (for scripting)"
    ),
    dirs_only: bool = typer.Option(
        False, "--dirs-only", "-d", help="Output directory names only (handles dir_name overrides)"
    ),
):
    """List projects with optional filters."""
    projects = get_projects()

    # Apply filters
    if site_type:
        matching = set(get_projects_by_site_type(site_type))
        projects = {k: v for k, v in projects.items() if k in matching}

    if state:
        matching = set(get_projects_by_state(state))
        projects = {k: v for k, v in projects.items() if k in matching}

    if coverage:
        matching = set(get_projects_by_coverage(coverage))
        projects = {k: v for k, v in projects.items() if k in matching}

    if status:
        matching = set(get_projects_by_status(status))
        projects = {k: v for k, v in projects.items() if k in matching}

    if not projects:
        typer.echo("No projects match the specified filters.")
        raise typer.Exit(1)

    if names_only:
        for name in sorted(projects.keys()):
            typer.echo(name)
    elif dirs_only:
        for name in sorted(projects.keys()):
            typer.echo(get_project_dir(name))
    else:
        typer.echo(f"\nFound {len(projects)} project(s):\n")
        for name in sorted(projects.keys()):
            config = projects[name]
            site = config.get("site_type", "unknown")
            states = ", ".join(config.get("states", []))
            proj_status = config.get("status", "active")
            status_marker = "" if proj_status == "active" else f" [{proj_status.upper()}]"
            typer.echo(f"  {name}{status_marker}")
            typer.echo(f"    Site: {site} | States: {states}")


@app.command()
def show(project_name: str = typer.Argument(..., help="Project name (e.g., audiobee_bcbs_il)")):
    """Show detailed information for a specific project."""
    info = get_project_info(project_name)
    
    if not info:
        typer.echo(f"Project '{project_name}' not found in manifest.")
        raise typer.Exit(1)

    site_types = get_site_types()
    coverage_types = get_coverage_types()

    typer.echo(f"\n{project_name}")
    typer.echo("=" * len(project_name))
    typer.echo(f"Site Type:  {info.get('site_type', 'N/A')}")
    
    site_desc = site_types.get(info.get("site_type", ""), "")
    if site_desc:
        typer.echo(f"            {site_desc}")
    
    typer.echo(f"States:     {', '.join(info.get('states', []))}")
    
    coverage = info.get("coverage", [])
    if coverage:
        typer.echo(f"Coverage:   {', '.join(coverage)}")
        for c in coverage:
            desc = coverage_types.get(c, "")
            if desc:
                typer.echo(f"            - {c}: {desc}")
    else:
        typer.echo("Coverage:   Not specified")
    
    typer.echo(f"Status:     {info.get('status', 'unknown')}")
    
    if info.get("config_ref"):
        typer.echo(f"Config:     {info['config_ref']}")
    
    if info.get("notes"):
        typer.echo(f"Notes:      {info['notes']}")
    
    typer.echo()


@app.command()
def stats():
    """Show project statistics by site type and coverage."""
    projects = get_projects()
    site_types = get_site_types()
    coverage_types = get_coverage_types()

    typer.echo(f"\n{'=' * 50}")
    typer.echo("PROJECT STATISTICS")
    typer.echo(f"{'=' * 50}\n")
    typer.echo(f"Total Projects: {len(projects)}\n")

    # Count by site type
    typer.echo("By Site Type:")
    typer.echo("-" * 40)
    site_counts: dict[str, int] = {}
    for config in projects.values():
        site = config.get("site_type", "unknown")
        site_counts[site] = site_counts.get(site, 0) + 1
    
    for site, count in sorted(site_counts.items(), key=lambda x: -x[1]):
        desc = site_types.get(site, "")[:40]
        typer.echo(f"  {site:20} {count:3}  {desc}")

    typer.echo()

    # Count by coverage
    typer.echo("By Coverage Type:")
    typer.echo("-" * 40)
    coverage_counts: dict[str, int] = {}
    for config in projects.values():
        for cov in config.get("coverage", []):
            coverage_counts[cov] = coverage_counts.get(cov, 0) + 1
    
    for cov, count in sorted(coverage_counts.items(), key=lambda x: -x[1]):
        desc = coverage_types.get(cov, "")
        typer.echo(f"  {cov:20} {count:3}  {desc}")

    typer.echo()

    # Count by state
    typer.echo("Top States (by project count):")
    typer.echo("-" * 40)
    state_counts: dict[str, int] = {}
    for config in projects.values():
        for state in config.get("states", []):
            if state != "ALL":
                state_counts[state] = state_counts.get(state, 0) + 1
    
    for state, count in sorted(state_counts.items(), key=lambda x: -x[1])[:15]:
        typer.echo(f"  {state:5} {count:3}")

    typer.echo()


@app.command()
def types():
    """List all site types and coverage types."""
    site_types = get_site_types()
    coverage_types = get_coverage_types()

    typer.echo("\nSite Types:")
    typer.echo("-" * 60)
    for name, desc in site_types.items():
        typer.echo(f"  {name:20} {desc}")

    typer.echo("\nCoverage Types:")
    typer.echo("-" * 60)
    for name, desc in coverage_types.items():
        typer.echo(f"  {name:20} {desc}")
    
    typer.echo()


if __name__ == "__main__":
    app()

#!/usr/bin/env python
"""Project scaffolding CLI for creating new scraper projects.

Usage:
    python scripts/scaffold_project.py new my_project --platform healthsparq --states TX,LA
    python scripts/scaffold_project.py new bcbs_ca --platform sapphire --states CA
    python scripts/scaffold_project.py list-templates
"""

from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
import yaml

app = typer.Typer(
    name="scaffold",
    help="Project scaffolding CLI for creating new scraper projects.",
    no_args_is_help=True,
)

REPO_ROOT = Path(__file__).parent.parent
PLATFORMS = ["healthsparq", "sapphire"]

# US state codes
US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "PR",
]


def validate_project_name(name: str) -> str:
    """Validate and normalize project name to slug format."""
    # Convert to lowercase and replace spaces/hyphens with underscores
    slug = re.sub(r"[-\s]+", "_", name.lower())
    # Remove non-alphanumeric characters except underscores
    slug = re.sub(r"[^a-z0-9_]", "", slug)
    # Remove leading/trailing underscores
    slug = slug.strip("_")

    if not slug:
        raise typer.BadParameter("Project name must contain alphanumeric characters")

    if not re.match(r"^[a-z][a-z0-9_]*$", slug):
        raise typer.BadParameter("Project slug must start with a letter")

    return slug


def validate_states(states_str: str) -> list[str]:
    """Validate and parse state codes."""
    if not states_str:
        return []

    states = [s.strip().upper() for s in states_str.split(",")]
    invalid = [s for s in states if s not in US_STATES]

    if invalid:
        raise typer.BadParameter(f"Invalid state codes: {', '.join(invalid)}")

    return states


def slug_to_human_name(slug: str) -> str:
    """Convert slug to human-readable name."""
    # Replace underscores with spaces and title case
    words = slug.replace("_", " ").split()
    # Handle common abbreviations
    abbreviations = {"bcbs", "uhc", "hmo", "ppo", "ca", "tx", "ny", "il", "fl"}
    return " ".join(
        word.upper() if word.lower() in abbreviations else word.title()
        for word in words
    )


def copy_and_replace_template(
    src: Path,
    dst: Path,
    replacements: dict[str, str],
) -> None:
    """Copy template file and replace placeholders."""
    content = src.read_text()

    for placeholder, value in replacements.items():
        content = content.replace(placeholder, value)

    dst.write_text(content)


def generate_config_yaml(
    platform: str,
    project_slug: str,
    project_name: str,
    states: list[str],
    domain: str | None,
) -> dict:
    """Generate config.yaml content based on platform."""
    if platform == "healthsparq":
        return {
            "project": {
                "name": project_name,
                "slug": project_slug,
            },
            "site": {
                "domain": domain or f"{project_slug}.healthsparq.com",
                "brand_code": project_slug.upper()[:10],
                "insurer_code": "INSURER",
            },
            "plans": [
                {
                    "product_code": "MA",
                    "name": "Medicare Advantage",
                },
            ],
            "coverage": {
                "states": states or ["TX"],
            },
            "concurrency": {
                "max_browsers": 3,
                "max_concurrent_requests": 10,
            },
        }
    else:  # sapphire
        return {
            "project": {
                "name": project_name,
                "slug": project_slug,
            },
            "api": {
                "base_url": domain or f"https://api.{project_slug}.providerfinder.com",
                "tenant_id": project_slug.upper(),
            },
            "coverage": {
                "states": states or ["TX"],
                "geo_strategy": "small",
            },
            "concurrency": {
                "max_workers": 5,
                "batch_size": 100,
            },
        }


@app.command()
def new(
    name: Annotated[str, typer.Argument(help="Project name (e.g., 'bcbs_ca' or 'BCBS CA')")],
    platform: Annotated[str, typer.Option("--platform", "-p", help="Platform: healthsparq or sapphire")] = "healthsparq",
    states: Annotated[str, typer.Option("--states", "-s", help="Comma-separated state codes (e.g., TX,LA,CA)")] = "",
    domain: Annotated[str | None, typer.Option("--domain", "-d", help="Site domain (auto-generated if not provided)")] = None,
    output_dir: Annotated[Path | None, typer.Option("--output", "-o", help="Output directory (default: repo root)")] = None,
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite existing project")] = False,
) -> None:
    """Create a new scraper project from templates.

    Examples:
        scaffold new bcbs_ca --platform healthsparq --states CA
        scaffold new molina_tx --platform sapphire --states TX,LA
        scaffold new "BCBS Illinois" --platform healthsparq --states IL
    """
    # Validate inputs
    if platform not in PLATFORMS:
        typer.echo(f"Error: Platform must be one of: {', '.join(PLATFORMS)}", err=True)
        raise typer.Exit(1)

    project_slug = validate_project_name(name)
    project_name = slug_to_human_name(project_slug)
    state_list = validate_states(states)

    # Determine output directory
    base_dir = output_dir or REPO_ROOT
    project_dir = base_dir / f"audiobee_{project_slug}"

    if project_dir.exists() and not force:
        typer.echo(f"Error: Project directory already exists: {project_dir}", err=True)
        typer.echo("Use --force to overwrite", err=True)
        raise typer.Exit(1)

    # Get templates directory
    templates_dir = REPO_ROOT / platform / "templates"
    if not templates_dir.exists():
        typer.echo(f"Error: Templates directory not found: {templates_dir}", err=True)
        raise typer.Exit(1)

    # Create project directory
    project_dir.mkdir(parents=True, exist_ok=True)

    # Define replacements
    replacements = {
        "{{PROJECT_NAME}}": project_name,
        "{{PROJECT_SLUG}}": project_slug,
        "{{DATE}}": datetime.now().strftime("%Y%m%d"),
        "{{PLATFORM}}": platform,
    }

    # Copy template files
    template_files = [
        ("run.py.template", "run.py"),
        ("mapper.py.template", "mapper.py"),
        ("pyproject.toml.template", "pyproject.toml"),
        ("requirements.txt.template", "requirements.txt"),
        ("README.md.template", "README.md"),
        (".gitignore.template", ".gitignore"),
        (".env.example", ".env"),
    ]

    typer.echo(f"\nCreating project: audiobee_{project_slug}")
    typer.echo(f"Platform: {platform}")
    typer.echo(f"States: {', '.join(state_list) if state_list else 'TX (default)'}")
    typer.echo(f"Directory: {project_dir}\n")

    for src_name, dst_name in template_files:
        src_path = templates_dir / src_name
        dst_path = project_dir / dst_name

        if src_path.exists():
            copy_and_replace_template(src_path, dst_path, replacements)
            typer.echo(f"  Created: {dst_name}")
        else:
            typer.echo(f"  Skipped: {dst_name} (template not found)")

    # Generate config.yaml
    config_content = generate_config_yaml(
        platform=platform,
        project_slug=project_slug,
        project_name=project_name,
        states=state_list,
        domain=domain,
    )
    config_path = project_dir / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config_content, f, default_flow_style=False, sort_keys=False)
    typer.echo(f"  Created: config.yaml")

    # Copy CLAUDE.md if exists
    claude_md = templates_dir / "CLAUDE.md"
    if claude_md.exists():
        shutil.copy(claude_md, project_dir / "CLAUDE.md")
        typer.echo(f"  Created: CLAUDE.md")

    typer.echo(f"\n✓ Project created successfully!")
    typer.echo(f"\nNext steps:")
    typer.echo(f"  1. cd {project_dir}")
    typer.echo(f"  2. Edit config.yaml with correct site details")
    typer.echo(f"  3. Edit mapper.py if custom normalization needed")
    typer.echo(f"  4. python run.py validate")
    typer.echo(f"  5. python run.py run --curr $(date +%Y%m%d)")


@app.command("list-templates")
def list_templates() -> None:
    """List available templates for each platform."""
    for platform in PLATFORMS:
        templates_dir = REPO_ROOT / platform / "templates"
        typer.echo(f"\n{platform}/ templates:")

        if not templates_dir.exists():
            typer.echo("  (no templates directory)")
            continue

        for f in sorted(templates_dir.iterdir()):
            if f.is_file():
                typer.echo(f"  - {f.name}")


@app.command("list-projects")
def list_projects(
    platform: Annotated[str | None, typer.Option("--platform", "-p", help="Filter by platform")] = None,
) -> None:
    """List existing audiobee_* projects."""
    projects = []

    for d in sorted(REPO_ROOT.iterdir()):
        if d.is_dir() and d.name.startswith("audiobee_"):
            # Detect platform from config.yaml or run.py
            detected_platform = "unknown"
            config_path = d / "config.yaml"
            run_path = d / "run.py"

            if config_path.exists():
                try:
                    with open(config_path) as f:
                        config = yaml.safe_load(f)
                    if "site" in config and "domain" in config.get("site", {}):
                        detected_platform = "healthsparq"
                    elif "api" in config:
                        detected_platform = "sapphire"
                except Exception:
                    pass
            elif run_path.exists():
                content = run_path.read_text()
                if "healthsparq" in content:
                    detected_platform = "healthsparq"
                elif "sapphire" in content:
                    detected_platform = "sapphire"

            if platform is None or detected_platform == platform:
                projects.append((d.name, detected_platform))

    if not projects:
        typer.echo("No projects found")
        return

    typer.echo(f"\nFound {len(projects)} projects:\n")
    for name, plat in projects:
        typer.echo(f"  {name:40} [{plat}]")


if __name__ == "__main__":
    app()

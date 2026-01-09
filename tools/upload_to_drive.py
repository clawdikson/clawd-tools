#!/usr/bin/env python3
"""
Upload 7z archives to Google Drive.

Usage:
    # Audiobee project (reads CURR_DATE from config.py)
    python tools/upload_to_drive.py audiobee_bcbs_il

    # HealthSparq project (requires --date)
    python tools/upload_to_drive.py christus_health_plan --date 20251227

    # Override date for any project
    python tools/upload_to_drive.py audiobee_bcbs_il --date 20251210

    # Dry run (validate without uploading)
    python tools/upload_to_drive.py audiobee_bcbs_il --dry-run

Setup:
    1. Create Google Cloud project and enable Drive API
    2. Create service account and download JSON credentials
    3. Save credentials to tools/google_drive_credentials.json
    4. Share Drive folders with service account email
    5. Add folder mappings to tools/drive_folder_mapping.json
"""
from __future__ import annotations

import sys
from pathlib import Path

import typer
from tqdm import tqdm

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.drive_uploader import DriveUploader
from tools.project_config import load_project_config

try:
    from core.logging import logger, setup_logging
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    setup_logging = None

app = typer.Typer(
    name="upload-to-drive",
    help="Upload 7z archives to Google Drive",
    add_completion=False,
)


def create_progress_bar(file_size: int):
    """Create a tqdm progress bar for upload tracking."""
    pbar = tqdm(
        total=100,
        unit="%",
        desc="Uploading",
        bar_format="{desc}: {percentage:3.0f}%|{bar}| {elapsed}<{remaining}",
    )

    def update_progress(progress: float):
        pbar.n = int(progress * 100)
        pbar.refresh()

    return pbar, update_progress


@app.command()
def upload(
    project_name: str = typer.Argument(
        ...,
        help="Project name (e.g., audiobee_bcbs_il or christus_health_plan)",
    ),
    date: str | None = typer.Option(
        None,
        "--date",
        "-d",
        help="Date in YYYYMMDD format (required for HealthSparq, optional override for Audiobee)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Validate configuration without uploading",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
):
    """Upload a project's 7z archive to Google Drive."""
    # Setup logging
    if setup_logging:
        setup_logging(
            project_name=project_name,
            run_id=date or "upload",
            level="DEBUG" if verbose else "INFO",
        )

    try:
        # Load project config
        config = load_project_config(
            project_name=project_name,
            date_override=date,
            base_dir=Path("."),
        )
        typer.echo(f"Project: {config.name} ({config.project_type})")
        typer.echo(f"Date: {config.curr_date}")

        # Construct file path
        archive_path = config.base_path / config.curr_date / f"{config.curr_date}.7z"
        typer.echo(f"Archive: {archive_path}")

        if not archive_path.exists():
            typer.echo(
                typer.style(f"Error: Archive not found at {archive_path}", fg=typer.colors.RED),
                err=True,
            )
            typer.echo(
                f"Hint: Create the archive first, e.g., with 7z a {archive_path} ...",
                err=True,
            )
            raise typer.Exit(1)

        # Initialize uploader and get folder ID
        uploader = DriveUploader()
        folder_id = uploader.get_folder_id(config.name)
        typer.echo(f"Drive folder ID: {folder_id}")

        if dry_run:
            typer.echo(typer.style("Dry run - skipping upload", fg=typer.colors.YELLOW))
            typer.echo("Configuration valid!")
            raise typer.Exit(0)

        # Upload with progress bar
        file_size = archive_path.stat().st_size
        pbar, progress_callback = create_progress_bar(file_size)

        try:
            result = uploader.upload_file(
                file_path=archive_path,
                folder_id=folder_id,
                progress_callback=progress_callback,
            )
        finally:
            pbar.close()

        # Report success
        typer.echo()
        typer.echo(typer.style("Upload successful!", fg=typer.colors.GREEN))
        typer.echo(f"File ID: {result.get('id')}")
        typer.echo(f"View: {result.get('webViewLink')}")

    except FileNotFoundError as e:
        typer.echo(typer.style(f"Error: {e}", fg=typer.colors.RED), err=True)
        raise typer.Exit(1)

    except KeyError as e:
        typer.echo(typer.style(f"Error: {e}", fg=typer.colors.RED), err=True)
        typer.echo(
            "Hint: Add project to tools/drive_folder_mapping.json",
            err=True,
        )
        raise typer.Exit(1)

    except ValueError as e:
        typer.echo(typer.style(f"Error: {e}", fg=typer.colors.RED), err=True)
        raise typer.Exit(1)

    except typer.Exit:
        raise  # Re-raise Exit exceptions without logging
    except Exception as e:
        logger.exception("Upload failed")
        typer.echo(typer.style(f"Error: {e}", fg=typer.colors.RED), err=True)
        raise typer.Exit(1)


@app.command()
def list_projects():
    """List projects with Drive folder mappings."""
    try:
        uploader = DriveUploader()
        mapping = uploader.load_folder_mapping()

        if not mapping:
            typer.echo("No projects configured in drive_folder_mapping.json")
            raise typer.Exit(0)

        typer.echo(f"Configured projects ({len(mapping)}):")
        for project in sorted(mapping.keys()):
            typer.echo(f"  - {project}")

    except FileNotFoundError as e:
        typer.echo(typer.style(f"Error: {e}", fg=typer.colors.RED), err=True)
        raise typer.Exit(1)


@app.command()
def validate(
    project_name: str = typer.Argument(..., help="Project name to validate"),
    date: str | None = typer.Option(None, "--date", "-d", help="Date in YYYYMMDD format"),
):
    """Validate project configuration and Drive folder mapping."""
    try:
        # Load project config
        config = load_project_config(
            project_name=project_name,
            date_override=date,
            base_dir=Path("."),
        )
        typer.echo(f"[OK] Project type: {config.project_type}")
        typer.echo(f"[OK] CURR_DATE: {config.curr_date}")
        typer.echo(f"[OK] Base path: {config.base_path}")

        # Check archive path
        archive_path = config.base_path / config.curr_date / f"{config.curr_date}.7z"
        if archive_path.exists():
            size_mb = archive_path.stat().st_size / 1024 / 1024
            typer.echo(f"[OK] Archive exists: {archive_path} ({size_mb:.1f} MB)")
        else:
            typer.echo(f"[WARN] Archive not found: {archive_path}")

        # Check Drive folder mapping
        uploader = DriveUploader()
        folder_id = uploader.get_folder_id(config.name)
        typer.echo(f"[OK] Drive folder ID: {folder_id}")

        typer.echo()
        typer.echo(typer.style("Validation passed!", fg=typer.colors.GREEN))

    except Exception as e:
        typer.echo(typer.style(f"[FAIL] {e}", fg=typer.colors.RED), err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()

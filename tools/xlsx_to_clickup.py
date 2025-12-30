#!/usr/bin/env python3
"""Generate screenshots from XLSX state reports and upload to ClickUp.

Usage:
    # Full workflow: generate + upload
    python tools/xlsx_to_clickup.py run audiobee_bcbs_il --task CU12345

    # Generate screenshot only
    python tools/xlsx_to_clickup.py generate audiobee_bcbs_il --output report.png

    # Upload existing image
    python tools/xlsx_to_clickup.py upload report.png --task CU12345

Environment Variables:
    CLICKUP_API_TOKEN: ClickUp API token (required for upload)
"""

from __future__ import annotations

import os
import re
import tempfile
import time
from pathlib import Path
from typing import Annotated, Optional

import pandas as pd
import requests
import typer

try:
    import dataframe_image as dfi
except ImportError:
    dfi = None

try:
    from core.logging import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

from project_config import load_project_config

app = typer.Typer(
    name="xlsx-to-clickup",
    help="Generate screenshots from XLSX state reports and upload to ClickUp",
    no_args_is_help=True,
)


# =============================================================================
# File Resolution
# =============================================================================


def resolve_xlsx_path(project_name: str, curr_date: str, base_path: Path) -> Path:
    """Find the state counts XLSX file.

    Primary: {project}/{date}/processed/{project}-{date}-state_with_surrounding-counts.xlsx
    Fallback: {project}/{date}/processed/{project}-{date}-state_only-counts.xlsx

    Args:
        project_name: Project name (e.g., "audiobee_bcbs_il")
        curr_date: Date in YYYYMMDD format
        base_path: Base path to the project directory

    Returns:
        Path to the XLSX file

    Raises:
        FileNotFoundError: If neither file exists
    """
    processed_dir = base_path / curr_date / "processed"

    if not processed_dir.exists():
        raise FileNotFoundError(f"Processed directory not found: {processed_dir}")

    # Primary pattern
    primary_filename = f"{project_name}-{curr_date}-state_with_surrounding-counts.xlsx"
    primary_path = processed_dir / primary_filename

    if primary_path.exists():
        return primary_path

    # Fallback pattern
    fallback_filename = f"{project_name}-{curr_date}-state_only-counts.xlsx"
    fallback_path = processed_dir / fallback_filename

    if fallback_path.exists():
        return fallback_path

    raise FileNotFoundError(
        f"No state counts file found in {processed_dir}. "
        f"Looked for:\n  - {primary_filename}\n  - {fallback_filename}"
    )


# =============================================================================
# Screenshot Generation
# =============================================================================


def generate_screenshot(
    xlsx_path: Path,
    output_path: Optional[Path] = None,
    dpi: int = 150,
    sheet_name: Optional[str] = None,
) -> Path:
    """Generate PNG screenshot from XLSX file.

    Args:
        xlsx_path: Path to XLSX file
        output_path: Output PNG path (auto-generated if None)
        dpi: Image resolution (default 150)
        sheet_name: Sheet to capture (default: first sheet)

    Returns:
        Path to generated PNG file

    Raises:
        ImportError: If dataframe-image is not installed
        ValueError: If Excel file is empty
    """
    if dfi is None:
        raise ImportError(
            "dataframe-image is required for screenshot generation. "
            "Install with: pip install dataframe-image"
        )

    # Read Excel file
    df = pd.read_excel(
        xlsx_path,
        sheet_name=sheet_name or 0,
        engine="openpyxl",
    )

    # Handle empty DataFrame
    if df.empty:
        raise ValueError(f"Excel file is empty: {xlsx_path}")

    # Style the DataFrame for better appearance
    styled = df.style.set_properties(
        **{
            "text-align": "center",
            "font-size": "10pt",
            "border": "1px solid #ddd",
            "padding": "4px",
        }
    ).set_table_styles(
        [
            {
                "selector": "th",
                "props": [
                    ("background-color", "#4472C4"),
                    ("color", "white"),
                    ("font-weight", "bold"),
                    ("text-align", "center"),
                    ("padding", "6px"),
                ],
            },
            {
                "selector": "tr:nth-child(even)",
                "props": [
                    ("background-color", "#f9f9f9"),
                ],
            },
        ]
    )

    # Generate output path if not provided
    if output_path is None:
        output_path = Path(tempfile.mktemp(suffix=".png"))

    # Export to PNG using matplotlib backend (no browser dependency)
    dfi.export(
        styled,
        str(output_path),
        dpi=dpi,
        table_conversion="matplotlib",
    )

    return output_path


# =============================================================================
# ClickUp Client
# =============================================================================


class ClickUpClient:
    """ClickUp API v2 client for attachment uploads."""

    BASE_URL = "https://api.clickup.com/api/v2"

    def __init__(self, api_token: str, max_retries: int = 3):
        """Initialize ClickUp client.

        Args:
            api_token: ClickUp API token
            max_retries: Maximum retry attempts for rate-limited requests
        """
        self.api_token = api_token
        self.max_retries = max_retries

    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> dict:
        """Make API request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., "/task/{task_id}/attachment")
            **kwargs: Additional arguments for requests

        Returns:
            JSON response as dict

        Raises:
            Exception: If max retries exceeded
            requests.HTTPError: For non-retryable errors
        """
        url = f"{self.BASE_URL}{endpoint}"
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = self.api_token

        for attempt in range(self.max_retries):
            response = requests.request(
                method,
                url,
                headers=headers,
                **kwargs,
            )

            if response.status_code == 429:
                # Rate limited - exponential backoff
                wait_time = 2**attempt
                logger.warning(f"Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue

            response.raise_for_status()
            return response.json()

        raise Exception(f"Max retries ({self.max_retries}) exceeded for {endpoint}")

    def upload_attachment(
        self,
        task_id: str,
        file_path: Path,
        filename: Optional[str] = None,
    ) -> dict:
        """Upload a file as task attachment.

        IMPORTANT: Do NOT set Content-Type header manually.
        Let requests library handle multipart boundary.

        Args:
            task_id: ClickUp task ID
            file_path: Path to file to upload
            filename: Custom filename (defaults to original name)

        Returns:
            API response with attachment details
        """
        endpoint = f"/task/{task_id}/attachment"

        # Use custom filename or original
        upload_name = filename or file_path.name

        with open(file_path, "rb") as f:
            # Key must be "attachment", NOT "attachment[]"
            files = {"attachment": (upload_name, f, "image/png")}
            return self._request("POST", endpoint, files=files)

    def add_comment(
        self,
        task_id: str,
        comment_text: str,
    ) -> dict:
        """Add a comment to a task.

        Args:
            task_id: ClickUp task ID
            comment_text: Comment text

        Returns:
            API response with comment details
        """
        endpoint = f"/task/{task_id}/comment"

        payload = {
            "comment_text": comment_text,
        }

        return self._request(
            "POST",
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
        )


# =============================================================================
# CLI Commands
# =============================================================================


@app.command()
def run(
    project: Annotated[
        str, typer.Argument(help="Project name (e.g., audiobee_bcbs_il)")
    ],
    task_id: Annotated[
        Optional[str], typer.Option("--task", "-t", help="ClickUp task ID")
    ] = None,
    curr_date: Annotated[
        Optional[str],
        typer.Option("--curr", "-c", help="Override CURR_DATE (YYYYMMDD)"),
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Validate without uploading")
    ] = False,
    dpi: Annotated[int, typer.Option("--dpi", help="Screenshot resolution")] = 150,
    comment: Annotated[
        Optional[str], typer.Option("--comment", "-m", help="Comment to add")
    ] = None,
) -> None:
    """Generate screenshot and upload to ClickUp in one step."""
    # Load API token from environment
    api_token = os.environ.get("CLICKUP_API_TOKEN")
    if not api_token and not dry_run:
        typer.echo(
            "Error: CLICKUP_API_TOKEN environment variable not set", err=True
        )
        typer.echo("\nTo set the token:", err=True)
        typer.echo("  export CLICKUP_API_TOKEN='pk_...'", err=True)
        raise typer.Exit(1)

    if not task_id and not dry_run:
        typer.echo("Error: --task/-t is required for upload", err=True)
        raise typer.Exit(1)

    try:
        # Load config using existing project_config module
        typer.echo(f"Loading config for {project}...")
        config = load_project_config(project, date_override=curr_date)

        date = config.curr_date
        if not date:
            typer.echo(
                "Error: CURR_DATE not found in config and --curr not provided",
                err=True,
            )
            raise typer.Exit(1)

        typer.echo(f"Using date: {date}")

        # Resolve XLSX path
        xlsx_path = resolve_xlsx_path(project, date, config.base_path)
        typer.echo(f"Found: {xlsx_path}")

        if dry_run:
            typer.echo("\n[DRY RUN] Would generate screenshot and upload to ClickUp")
            typer.echo(f"  Source: {xlsx_path}")
            typer.echo(f"  Task: {task_id or '(not specified)'}")
            return

        # Generate screenshot
        typer.echo("Generating screenshot...")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            output_path = Path(tmp.name)

        try:
            generate_screenshot(xlsx_path, output_path, dpi=dpi)
            typer.echo(f"Screenshot saved: {output_path}")

            # Upload to ClickUp
            typer.echo(f"Uploading to ClickUp task {task_id}...")
            client = ClickUpClient(api_token)

            # Use descriptive filename
            upload_filename = f"{project}-{date}-state-counts.png"
            result = client.upload_attachment(task_id, output_path, upload_filename)

            typer.echo(typer.style("Upload successful!", fg=typer.colors.GREEN))

            # Add comment if provided (or default comment with metadata)
            if comment or not comment:
                full_comment = (
                    f"{comment or 'State counts report'}\n\n"
                    f"Project: {project}\n"
                    f"Date: {date}"
                )
                client.add_comment(task_id, full_comment)
                typer.echo("Comment added")

        finally:
            # Cleanup temp file
            if output_path.exists():
                output_path.unlink()

    except FileNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except ImportError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(2)


@app.command()
def generate(
    project: Annotated[str, typer.Argument(help="Project name")],
    output: Annotated[
        Optional[Path], typer.Option("--output", "-o", help="Output PNG path")
    ] = None,
    curr_date: Annotated[
        Optional[str], typer.Option("--curr", "-c", help="Override CURR_DATE")
    ] = None,
    dpi: Annotated[int, typer.Option("--dpi", help="Screenshot resolution")] = 150,
) -> None:
    """Generate screenshot only (no upload)."""
    try:
        # Load config
        typer.echo(f"Loading config for {project}...")
        config = load_project_config(project, date_override=curr_date)

        date = config.curr_date
        if not date:
            typer.echo(
                "Error: CURR_DATE not found in config and --curr not provided",
                err=True,
            )
            raise typer.Exit(1)

        typer.echo(f"Using date: {date}")

        # Resolve XLSX path
        xlsx_path = resolve_xlsx_path(project, date, config.base_path)
        typer.echo(f"Found: {xlsx_path}")

        # Determine output path
        if output is None:
            output = Path(f"{project}-{date}-state-counts.png")

        # Generate screenshot
        typer.echo("Generating screenshot...")
        result_path = generate_screenshot(xlsx_path, output, dpi=dpi)
        typer.echo(typer.style(f"Screenshot saved: {result_path}", fg=typer.colors.GREEN))

    except FileNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except ImportError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(2)


@app.command()
def upload(
    image: Annotated[Path, typer.Argument(help="PNG file to upload")],
    task_id: Annotated[str, typer.Option("--task", "-t", help="ClickUp task ID")],
    comment: Annotated[
        Optional[str], typer.Option("--comment", "-m", help="Comment to add")
    ] = None,
) -> None:
    """Upload existing image to ClickUp."""
    # Validate file exists
    if not image.exists():
        typer.echo(f"Error: File not found: {image}", err=True)
        raise typer.Exit(1)

    # Load API token from environment
    api_token = os.environ.get("CLICKUP_API_TOKEN")
    if not api_token:
        typer.echo(
            "Error: CLICKUP_API_TOKEN environment variable not set", err=True
        )
        typer.echo("\nTo set the token:", err=True)
        typer.echo("  export CLICKUP_API_TOKEN='pk_...'", err=True)
        raise typer.Exit(1)

    try:
        # Upload to ClickUp
        typer.echo(f"Uploading {image} to ClickUp task {task_id}...")
        client = ClickUpClient(api_token)

        result = client.upload_attachment(task_id, image)
        typer.echo(typer.style("Upload successful!", fg=typer.colors.GREEN))

        # Add comment if provided
        if comment:
            client.add_comment(task_id, comment)
            typer.echo("Comment added")

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(2)


if __name__ == "__main__":
    app()

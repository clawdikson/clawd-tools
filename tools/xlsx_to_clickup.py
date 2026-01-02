#!/usr/bin/env python3
"""Generate screenshots from XLSX state reports and send via email or upload to ClickUp.

Usage:
    # Send screenshot via email (Gmail OAuth - uses same credentials as Drive upload)
    python tools/xlsx_to_clickup.py email audiobee_bcbs_il --to recipient@example.com

    # Full workflow: generate + upload to ClickUp
    python tools/xlsx_to_clickup.py run audiobee_bcbs_il --task CU12345

    # Generate screenshot only
    python tools/xlsx_to_clickup.py generate audiobee_bcbs_il --output report.png

    # Upload existing image to ClickUp
    python tools/xlsx_to_clickup.py upload report.png --task CU12345

Authentication:
    Email: Uses Gmail OAuth (tools/oauth_credentials.json, same as Google Drive)
           First run opens browser for login. Token saved to tools/gmail_token.json

Environment Variables:
    CLICKUP_API_TOKEN: ClickUp API token (required for upload)
"""

from __future__ import annotations

import base64
import json
import os
import tempfile
import time
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path
from typing import Annotated, Optional, List

import pandas as pd
import requests
import typer

try:
    from core.logging import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

# Handle import from both tools/ directory and workspace root
try:
    from project_config import load_project_config
except ImportError:
    from tools.project_config import load_project_config

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


def resolve_jsonl_path(project_name: str, curr_date: str, base_path: Path) -> Path:
    """Find the JSONL output file for a project.

    Pattern: {base_path}/{date}/processed/{project}-{date}.jsonl

    Args:
        project_name: Project name (e.g., "audiobee_bcbs_il")
        curr_date: Date in YYYYMMDD format
        base_path: Base path to the project directory

    Returns:
        Path to the JSONL file

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    processed_dir = base_path / curr_date / "processed"
    jsonl_filename = f"{project_name}-{curr_date}.jsonl"
    jsonl_path = processed_dir / jsonl_filename

    if not jsonl_path.exists():
        raise FileNotFoundError(f"JSONL file not found: {jsonl_path}")

    return jsonl_path


def parse_run_timestamps(xlsx_path: Path) -> dict:
    """Extract run timestamps from XLSX state counts file.

    Parses cells A8 (First File Created) and A9 (Last File Created).

    Args:
        xlsx_path: Path to XLSX file with state counts

    Returns:
        dict with keys:
        - first_file_created: datetime or None
        - last_file_created: datetime or None
        - run_duration_seconds: int or 0
        - run_ended_str: str (formatted timestamp from Last File Created)
    """
    from openpyxl import load_workbook
    from datetime import datetime

    wb = load_workbook(xlsx_path, data_only=True)
    ws = wb.active

    result = {
        "first_file_created": None,
        "last_file_created": None,
        "run_duration_seconds": 0,
        "run_ended_str": "",
    }

    # Parse cell A8: "First File Created = DD/MM/YYYY HH:MM:SS"
    cell_a8 = str(ws['A8'].value or "")
    if "=" in cell_a8:
        try:
            timestamp_str = cell_a8.split("=")[1].strip()
            result["first_file_created"] = datetime.strptime(
                timestamp_str, "%d/%m/%Y %H:%M:%S"
            )
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse A8: {cell_a8} - {e}")

    # Parse cell A9: "Last File Created = DD/MM/YYYY HH:MM:SS"
    cell_a9 = str(ws['A9'].value or "")
    if "=" in cell_a9:
        try:
            timestamp_str = cell_a9.split("=")[1].strip()
            result["last_file_created"] = datetime.strptime(
                timestamp_str, "%d/%m/%Y %H:%M:%S"
            )
            # Format as YYYY-MM-DD HH:MM:SS with -0330 timezone (Newfoundland)
            result["run_ended_str"] = result["last_file_created"].strftime("%Y-%m-%d %H:%M:%S") + " -0330"
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse A9: {cell_a9} - {e}")

    # Calculate duration
    if result["first_file_created"] and result["last_file_created"]:
        delta = result["last_file_created"] - result["first_file_created"]
        result["run_duration_seconds"] = max(0, int(delta.total_seconds()))

    wb.close()
    return result


# =============================================================================
# Screenshot Generation
# =============================================================================


def generate_screenshot(
    xlsx_path: Path,
    output_path: Optional[Path] = None,
    dpi: int = 150,
    sheet_name: Optional[str] = None,
) -> Path:
    """Generate PNG screenshot from XLSX file - compact summary format.

    Creates a clean summary image showing:
    - In-scope States
    - In-Scope/Out-of-Scope Provider counts (Unique and Non-Unique)

    Args:
        xlsx_path: Path to XLSX file
        output_path: Output PNG path (auto-generated if None)
        dpi: Image resolution (default 150)
        sheet_name: Sheet to capture (default: first sheet)

    Returns:
        Path to generated PNG file

    Raises:
        ImportError: If matplotlib is not installed
        ValueError: If Excel file is empty
    """
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    # Read Excel file
    df = pd.read_excel(
        xlsx_path,
        sheet_name=sheet_name or 0,
        engine="openpyxl",
    )

    # Handle empty DataFrame
    if df.empty:
        raise ValueError(f"Excel file is empty: {xlsx_path}")

    # Extract summary rows (first 5 rows contain the key stats)
    summary_rows = []
    for idx, row in df.iterrows():
        desc = str(row.get("Description", "")).strip()
        data = str(row.get("Data", "")).strip()
        if desc and desc != "nan" and idx < 5:
            # Clean up description (remove trailing colon for cleaner display)
            label = desc.rstrip(":")
            value = data if data and data != "nan" else ""
            summary_rows.append((label, value))

    if not summary_rows:
        raise ValueError(f"No summary data found in: {xlsx_path}")

    # Create figure with matplotlib
    fig, ax = plt.subplots(figsize=(8, 3), facecolor="white")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, len(summary_rows) + 1)
    ax.axis("off")

    # Add a subtle background box
    bg_box = FancyBboxPatch(
        (0.1, 0.3),
        9.8,
        len(summary_rows) + 0.4,
        boxstyle="round,pad=0.02,rounding_size=0.1",
        facecolor="#f8f9fa",
        edgecolor="#dee2e6",
        linewidth=1,
    )
    ax.add_patch(bg_box)

    # Render each row
    y_pos = len(summary_rows)
    for label, value in summary_rows:
        # Label on left (bold, dark gray)
        ax.text(
            0.3,
            y_pos,
            f"{label}:",
            fontsize=11,
            fontweight="bold",
            color="#333333",
            verticalalignment="center",
            fontfamily="sans-serif",
        )
        # Value on right (regular, dark blue)
        ax.text(
            5.0,
            y_pos,
            value,
            fontsize=11,
            fontweight="normal",
            color="#1a5276",
            verticalalignment="center",
            fontfamily="sans-serif",
        )
        y_pos -= 1

    # Adjust layout
    plt.tight_layout(pad=0.5)

    # Generate output path if not provided
    if output_path is None:
        output_path = Path(tempfile.mktemp(suffix=".png"))

    # Save figure
    fig.savefig(
        str(output_path),
        dpi=dpi,
        bbox_inches="tight",
        facecolor="white",
        edgecolor="none",
        pad_inches=0.2,
    )
    plt.close(fig)

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
# Email Client (Gmail API with OAuth)
# =============================================================================

# Gmail API scope
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# Lazy-loaded Google libraries
_gmail_libs_loaded = False
GmailCredentials = None
GmailInstalledAppFlow = None
gmail_build = None


def _load_gmail_libs():
    """Lazy-load Google Gmail libraries on first use."""
    global _gmail_libs_loaded, GmailCredentials, GmailInstalledAppFlow, gmail_build
    if _gmail_libs_loaded:
        return
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        GmailCredentials = Credentials
        gmail_build = build
        _gmail_libs_loaded = True
    except ImportError as e:
        raise ImportError(
            "Gmail API dependencies not installed. Run:\n"
            "  pip install google-api-python-client google-auth google-auth-oauthlib"
        ) from e

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        GmailInstalledAppFlow = InstalledAppFlow
    except ImportError:
        GmailInstalledAppFlow = None


class EmailClient:
    """Gmail API client for sending emails with OAuth authentication."""

    def __init__(
        self,
        credentials_path: Optional[Path] = None,
        token_path: Optional[Path] = None,
    ):
        """Initialize Gmail client with OAuth.

        Args:
            credentials_path: Path to OAuth client credentials JSON.
                Defaults to tools/oauth_credentials.json
            token_path: Path to store OAuth tokens.
                Defaults to tools/gmail_token.json
        """
        tools_dir = Path(__file__).parent
        self.credentials_path = credentials_path or (tools_dir / "oauth_credentials.json")
        self.token_path = token_path or (tools_dir / "gmail_token.json")
        self._service = None

    def _get_credentials(self):
        """Get OAuth credentials, prompting for browser login if needed."""
        _load_gmail_libs()

        if GmailInstalledAppFlow is None:
            raise ImportError(
                "OAuth dependencies not installed. Run:\n"
                "  pip install google-auth-oauthlib"
            )

        creds = None

        # Load existing token if available
        if self.token_path.exists():
            creds = GmailCredentials.from_authorized_user_file(
                str(self.token_path), GMAIL_SCOPES
            )

        # If no valid credentials, run OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                logger.info("Refreshed Gmail OAuth token")
            else:
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f"OAuth credentials not found at {self.credentials_path}. "
                        "See tools/README.md for setup instructions."
                    )
                flow = GmailInstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), GMAIL_SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info("Completed Gmail OAuth login flow")

            # Save token for future use
            with open(self.token_path, "w") as token_file:
                token_file.write(creds.to_json())
            logger.info(f"Saved Gmail OAuth token to {self.token_path}")

        return creds

    @property
    def service(self):
        """Lazy-load authenticated Gmail API service."""
        if self._service is None:
            _load_gmail_libs()
            credentials = self._get_credentials()
            self._service = gmail_build("gmail", "v1", credentials=credentials)
            logger.info("Authenticated with Gmail API (OAuth 2.0)")
        return self._service

    def send_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        attachment_path: Optional[Path] = None,
        attachment_name: Optional[str] = None,
        cc: Optional[List[str]] = None,
    ) -> dict:
        """Send an email with optional attachment via Gmail API.

        Args:
            to: List of recipient email addresses
            subject: Email subject
            body: Email body (plain text)
            attachment_path: Path to file to attach
            attachment_name: Custom filename for attachment
            cc: List of CC email addresses

        Returns:
            Gmail API response with message id and thread id

        Raises:
            Exception: If email fails to send
        """
        # Create message
        msg = MIMEMultipart()
        msg["To"] = ", ".join(to)
        msg["Subject"] = subject

        if cc:
            msg["Cc"] = ", ".join(cc)

        # Add body
        msg.attach(MIMEText(body, "plain"))

        # Add attachment if provided
        if attachment_path and attachment_path.exists():
            with open(attachment_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)

                filename = attachment_name or attachment_path.name
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={filename}",
                )
                msg.attach(part)

        # Encode message for Gmail API
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

        # Send via Gmail API
        result = self.service.users().messages().send(
            userId="me",
            body={"raw": raw_message}
        ).execute()

        logger.info(f"Email sent! Message ID: {result.get('id')}")
        return result


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


@app.command()
def email(
    project: Annotated[
        str, typer.Argument(help="Project name (e.g., audiobee_bcbs_il)")
    ],
    to: Annotated[
        List[str], typer.Option("--to", "-t", help="Recipient email address(es)")
    ],
    curr_date: Annotated[
        Optional[str],
        typer.Option("--curr", "-c", help="Override CURR_DATE (YYYYMMDD)"),
    ] = None,
    cc: Annotated[
        Optional[List[str]], typer.Option("--cc", help="CC email address(es)")
    ] = None,
    subject: Annotated[
        Optional[str], typer.Option("--subject", "-s", help="Email subject")
    ] = None,
    body: Annotated[
        Optional[str], typer.Option("--body", "-b", help="Email body text")
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Validate without sending")
    ] = False,
    dpi: Annotated[int, typer.Option("--dpi", help="Screenshot resolution")] = 150,
    s3_upload: Annotated[
        bool,
        typer.Option("--s3-upload", help="Upload JSONL to S3 and include metadata in email")
    ] = False,
    s3_expires_in: Annotated[
        int,
        typer.Option("--s3-expires-in", help="Presigned URL expiration in seconds")
    ] = 604800,  # 7 days
) -> None:
    """Generate screenshot and send via Gmail (OAuth authentication).

    First run will open browser for Google login. Token is saved for future use.
    Requires: tools/oauth_credentials.json (same as Google Drive upload)

    With --s3-upload: Also uploads JSONL to S3 and includes presigned URL + metadata in email.
    Requires: S3_BUCKET_NAME environment variable and AWS credentials.
    """
    if not to:
        typer.echo("Error: --to/-t is required", err=True)
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

        # Use send_report_email for the actual work
        if dry_run:
            # Resolve XLSX path for dry-run display
            xlsx_path = resolve_xlsx_path(project, date, config.base_path)
            typer.echo("\n[DRY RUN] Would generate screenshot and send email")
            typer.echo(f"  Source: {xlsx_path}")
            typer.echo(f"  To: {', '.join(to)}")
            if cc:
                typer.echo(f"  CC: {', '.join(cc)}")
            typer.echo(f"  Subject: {subject or f'State Counts Report: {project} ({date})'}")
            typer.echo(f"  Auth: Gmail OAuth (tools/oauth_credentials.json)")
            if s3_upload:
                typer.echo(f"  S3 Upload: Enabled (expires in {s3_expires_in // 86400} days)")
                typer.echo(f"  S3 Bucket: {os.environ.get('S3_BUCKET_NAME', '(not set)')}")
            return

        typer.echo("Generating screenshot and sending email...")
        if s3_upload:
            typer.echo(f"S3 upload enabled (expires in {s3_expires_in // 86400} days)")

        result = send_report_email(
            project_name=project,
            curr_date=date,
            base_path=config.base_path,
            to=to,
            cc=cc,
            subject=subject,
            body=body,
            dpi=dpi,
            dry_run=False,
            upload_to_s3=s3_upload,
            s3_expires_in=s3_expires_in,
        )

        typer.echo(typer.style("Email sent successfully!", fg=typer.colors.GREEN))
        typer.echo(f"Message ID: {result.get('message_id')}")

        if result.get("s3_key"):
            typer.echo(typer.style(f"S3 Upload: {result.get('s3_key')}", fg=typer.colors.CYAN))

    except FileNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except ImportError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(2)


# =============================================================================
# Programmatic API (for run_all.py integration)
# =============================================================================

DEFAULT_RECIPIENTS = ["operations@audiobee.ai", "dikson@audiobee.ai"]


def send_report_email(
    project_name: str,
    curr_date: str,
    base_path: Optional[str | Path] = None,
    to: Optional[List[str]] = None,
    cc: Optional[List[str]] = None,
    subject: Optional[str] = None,
    body: Optional[str] = None,
    dpi: int = 150,
    dry_run: bool = False,
    upload_to_s3: bool = False,
    s3_expires_in: int = 604800,  # 7 days
) -> dict:
    """Generate screenshot from XLSX and send via Gmail.

    This is the main entry point for integration with run_all.py.

    When upload_to_s3=True, also:
    - Uploads JSONL to S3
    - Generates presigned URL
    - Parses run timestamps from XLSX
    - Adds JSON metadata block to email body

    Args:
        project_name: Project name (e.g., "audiobee_bcbs_il")
        curr_date: Date string in YYYYMMDD format
        base_path: Base directory containing the project. Defaults to project_name/.
        to: List of recipient emails. Defaults to DEFAULT_RECIPIENTS.
        cc: Optional list of CC emails.
        subject: Custom email subject. Defaults to "State Counts Report: {project} ({date})".
        body: Custom email body.
        dpi: Screenshot resolution (default 150).
        dry_run: If True, validate without sending.
        upload_to_s3: If True, upload JSONL to S3 and include metadata in email.
        s3_expires_in: Presigned URL expiration in seconds (default 7 days).

    Returns:
        dict with:
            - message_id: Gmail message ID
            - xlsx_path: Path to source XLSX file
            - screenshot_path: Path to generated PNG (temp file, deleted after send)
            - s3_key: S3 object key (if upload_to_s3=True)
            - presigned_url: S3 presigned URL (if upload_to_s3=True)
            - run_metadata: Parsed timestamps (if upload_to_s3=True)

    Raises:
        FileNotFoundError: If XLSX file not found
        Exception: If email fails to send

    Example:
        # In run_all.py:
        from tools.xlsx_to_clickup import send_report_email
        result = send_report_email(config.PROJECT_NAME, config.CURR_DATE)
        print(f"Email sent: {result['message_id']}")

        # With S3 upload:
        result = send_report_email(
            config.PROJECT_NAME, config.CURR_DATE,
            upload_to_s3=True
        )
        print(f"S3 URL: {result.get('presigned_url')}")
    """
    # Set defaults
    if to is None:
        to = DEFAULT_RECIPIENTS

    # Construct base path
    if base_path is None:
        base_path = Path(project_name)
    else:
        base_path = Path(base_path)

    # Resolve XLSX path
    xlsx_path = resolve_xlsx_path(project_name, curr_date, base_path)
    logger.info(f"Found XLSX: {xlsx_path}")

    # Parse run timestamps from XLSX (needed for email body)
    run_timestamps = parse_run_timestamps(xlsx_path)

    # Build email content
    email_subject = subject or f"Scrape Completed: {project_name} ({curr_date})"
    email_body = body or (
        f"Project: {project_name}\n"
        f"Run Date: {curr_date}\n"
        f"Run Ended: {run_timestamps['run_ended_str']}\n"
        f"Run Duration: {run_timestamps['run_duration_seconds']} seconds\n"
        f"Source: {xlsx_path.name}"
    )

    # S3 upload results (populated if upload_to_s3=True and succeeds)
    s3_result = {}

    # Handle S3 upload if enabled
    if upload_to_s3:
        try:
            # Lazy import S3 uploader
            try:
                from s3_uploader import S3Uploader, S3Config
            except ImportError:
                from tools.s3_uploader import S3Uploader, S3Config

            # Find JSONL file
            jsonl_path = resolve_jsonl_path(project_name, curr_date, base_path)
            logger.info(f"Found JSONL: {jsonl_path}")

            # Upload to S3
            s3_config = S3Config.from_env()
            s3_config.presigned_expiry = s3_expires_in
            uploader = S3Uploader(s3_config)

            s3_key, presigned_url = uploader.upload_and_get_url(
                jsonl_path, project_name, curr_date, s3_expires_in
            )

            # Build JSON metadata (run_timestamps already parsed above)
            json_metadata = {
                "json_url": presigned_url,
                "project_name": project_name,
                "run_ended": run_timestamps["run_ended_str"],
                "run_duration": run_timestamps["run_duration_seconds"],
                "api_key": ""
            }

            # Append S3 info to email body with clear JSON block for easy copy-paste
            expiry_days = s3_expires_in // 86400
            json_block = json.dumps(json_metadata, indent=2)
            email_body = f"""{email_body}

---
JSONL Download URL (expires in {expiry_days} days):
{presigned_url}

--- JSON START (copy from here) ---
{json_block}
--- JSON END ---
"""

            s3_result = {
                "s3_key": s3_key,
                "presigned_url": presigned_url,
                "run_metadata": run_timestamps,
                "json_metadata": json_metadata,
            }
            logger.info(f"S3 upload complete: {s3_key}")

        except FileNotFoundError as e:
            # JSONL not found - log warning but continue with email
            logger.warning(f"S3 upload skipped: {e}")
        except ValueError as e:
            # S3_BUCKET_NAME not set
            logger.warning(f"S3 upload skipped (config error): {e}")
        except Exception as e:
            # Other S3 errors - log and continue
            logger.warning(f"S3 upload failed: {e}")

    if dry_run:
        logger.info(f"[DRY RUN] Would send email to {to}")
        result = {
            "message_id": "dry-run",
            "xlsx_path": str(xlsx_path),
            "screenshot_path": "dry-run",
        }
        if s3_result:
            result.update(s3_result)
        return result

    # Generate screenshot
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        output_path = Path(tmp.name)

    try:
        generate_screenshot(xlsx_path, output_path, dpi=dpi)
        logger.info(f"Screenshot generated: {output_path}")

        # Send email via Gmail API
        client = EmailClient()
        attachment_name = f"{project_name}-{curr_date}-state-counts.png"

        result = client.send_email(
            to=to,
            subject=email_subject,
            body=email_body,
            attachment_path=output_path,
            attachment_name=attachment_name,
            cc=cc,
        )

        logger.info(f"Email sent! Message ID: {result.get('id')}")

        response = {
            "message_id": result.get("id"),
            "xlsx_path": str(xlsx_path),
            "screenshot_path": str(output_path),
        }

        # Include S3 results if upload was enabled and succeeded
        if s3_result:
            response.update(s3_result)

        return response

    finally:
        # Cleanup temp file
        if output_path.exists():
            output_path.unlink()


if __name__ == "__main__":
    app()

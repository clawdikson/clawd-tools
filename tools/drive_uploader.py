#!/usr/bin/env python3
"""
Google Drive file uploader with resumable upload support.

Supports two authentication methods:
1. Service Account (default) - for Shared Drives or external access
2. OAuth 2.0 (use_oauth=True) - for personal Drive folders

Usage (CLI):
    # Upload archive (reads CURR_DATE from config.py for audiobee projects)
    python tools/drive_uploader.py upload audiobee_bcbs_il

    # HealthSparq project (requires --date)
    python tools/drive_uploader.py upload christus_health_plan --date 20251227

    # Dry run (validate without uploading)
    python tools/drive_uploader.py upload audiobee_bcbs_il --dry-run

    # List configured projects
    python tools/drive_uploader.py list-projects

    # Validate configuration
    python tools/drive_uploader.py validate audiobee_bcbs_il

Usage (Python API):
    from tools.drive_uploader import upload_archive
    result = upload_archive("audiobee_bcbs_il", "20260115", use_oauth=True)
    print(f"Uploaded: {result['webViewLink']}")

Setup:
    1. Create Google Cloud project and enable Drive API
    2. Create service account and download JSON credentials
    3. Save credentials to tools/secrets/google_drive_credentials.json
    4. Share Drive folders with service account email
    5. Add folder mappings to tools/drive_folder_mapping.json

Dependencies:
    pip install google-api-python-client google-auth google-auth-oauthlib typer tqdm

Environment Variables:
    GOOGLE_SERVICE_ACCOUNT_FILE: Path to service account JSON (service account mode)
    GOOGLE_OAUTH_CREDENTIALS: Path to OAuth client credentials JSON (OAuth mode)
"""
from __future__ import annotations

import json
import os
import random
import time
from collections.abc import Callable
from pathlib import Path

# Lazy imports for Google libraries (only required when actually uploading)
# This allows importing drive_uploader without google-auth installed
_google_libs_loaded = False
service_account = None
build = None
MediaFileUpload = None
HttpError = None
Credentials = None
InstalledAppFlow = None


def _load_google_libs():
    """Lazy-load Google libraries on first use."""
    global _google_libs_loaded, service_account, build, MediaFileUpload, HttpError
    global Credentials, InstalledAppFlow
    if _google_libs_loaded:
        return
    try:
        from google.oauth2 import service_account as sa
        from google.oauth2.credentials import Credentials as creds
        from googleapiclient.discovery import build as bld
        from googleapiclient.errors import HttpError as he
        from googleapiclient.http import MediaFileUpload as mfu
        service_account = sa
        Credentials = creds
        build = bld
        MediaFileUpload = mfu
        HttpError = he
        _google_libs_loaded = True
    except ImportError as e:
        raise ImportError(
            "Google Drive dependencies not installed. Run:\n"
            "  pip install google-api-python-client google-auth google-auth-oauthlib\n"
            "Or:\n"
            "  pip install -r tools/requirements.txt"
        ) from e

    # OAuth flow library (optional - only needed for OAuth mode)
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow as iaf
        InstalledAppFlow = iaf
    except ImportError:
        InstalledAppFlow = None  # Will fail if OAuth mode is used without this


try:
    from core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive"]
CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_RETRIES = 5
RETRYABLE_STATUS_CODES = (429, 500, 502, 503, 504)


class DriveUploader:
    """Upload files to Google Drive with resumable upload support."""

    def __init__(
        self,
        credentials_path: str | None = None,
        mapping_path: str | None = None,
        use_oauth: bool = False,
    ):
        """Initialize uploader.

        Args:
            credentials_path: Path to credentials JSON. For service account mode,
                this is the service account key. For OAuth mode, this is the
                OAuth client credentials.
            mapping_path: Path to folder mapping JSON. Defaults to
                tools/drive_folder_mapping.json.
            use_oauth: If True, use OAuth 2.0 flow (for personal Drive folders).
                If False (default), use service account (for Shared Drives).
        """
        # Resolve paths relative to tools/ directory (where this file lives)
        tools_dir = Path(__file__).parent
        self.use_oauth = use_oauth

        if use_oauth:
            self.credentials_path = Path(
                credentials_path
                or os.environ.get("GOOGLE_OAUTH_CREDENTIALS")
                or (tools_dir / "secrets" / "oauth_credentials.json")
            )
            self.token_path = tools_dir / "secrets" / "oauth_token.json"
        else:
            self.credentials_path = Path(
                credentials_path
                or os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
                or (tools_dir / "secrets" / "google_drive_credentials.json")
            )
            self.token_path = None

        self.mapping_path = Path(mapping_path or (tools_dir / "drive_folder_mapping.json"))

        self._service = None
        self._folder_mapping: dict[str, str] = {}

    def _validate_credentials(self) -> None:
        """Validate credentials file exists."""
        if not self.credentials_path.exists():
            raise FileNotFoundError(
                f"Google Drive credentials not found at {self.credentials_path}. "
                "See tools/README.md for setup instructions."
            )

    @property
    def service(self):
        """Lazy-load authenticated Drive API service."""
        if self._service is None:
            _load_google_libs()  # Load Google libraries on first use
            self._validate_credentials()

            if self.use_oauth:
                credentials = self._get_oauth_credentials()
            else:
                credentials = service_account.Credentials.from_service_account_file(
                    str(self.credentials_path),
                    scopes=SCOPES,
                )

            self._service = build("drive", "v3", credentials=credentials)
            auth_type = "OAuth 2.0" if self.use_oauth else "Service Account"
            logger.info(f"Authenticated with Google Drive API ({auth_type})")
        return self._service

    def _get_oauth_credentials(self):
        """Get OAuth credentials, prompting for browser login if needed."""
        if InstalledAppFlow is None:
            raise ImportError(
                "OAuth dependencies not installed. Run:\n"
                "  pip install google-auth-oauthlib"
            )

        creds = None

        # Load existing token if available
        if self.token_path and self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)

        # If no valid credentials, run OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                logger.info("Refreshed OAuth token")
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info("Completed OAuth login flow")

            # Save token for future use
            if self.token_path:
                with open(self.token_path, "w") as token_file:
                    token_file.write(creds.to_json())
                logger.info(f"Saved OAuth token to {self.token_path}")

        return creds

    def load_folder_mapping(self) -> dict[str, str]:
        """Load project -> folder ID mapping from JSON file."""
        if not self._folder_mapping:
            if not self.mapping_path.exists():
                raise FileNotFoundError(
                    f"Folder mapping not found at {self.mapping_path}. "
                    "Create it with project -> folder ID mappings."
                )
            with open(self.mapping_path) as f:
                data = json.load(f)
                self._folder_mapping = data.get("projects", data)
        return self._folder_mapping

    def get_folder_id(self, project_name: str) -> str:
        """Get Google Drive folder ID for a project.

        Args:
            project_name: Project name (e.g., "audiobee_bcbs_il")

        Returns:
            Google Drive folder ID

        Raises:
            KeyError: If project has no folder mapping
        """
        mapping = self.load_folder_mapping()
        if project_name not in mapping:
            available = ", ".join(sorted(mapping.keys())[:10])
            if available:
                raise KeyError(
                    f"No Drive folder mapping for project '{project_name}'. "
                    f"Available projects: {available}..."
                )
            else:
                raise KeyError(
                    f"No Drive folder mapping for project '{project_name}'. "
                    "No projects configured in drive_folder_mapping.json yet."
                )
        return mapping[project_name]

    def validate_folder_access(self, folder_id: str) -> dict:
        """Validate service account has access to the folder.

        Args:
            folder_id: Google Drive folder ID

        Returns:
            dict with folder metadata (name, id, mimeType)

        Raises:
            RuntimeError: If folder is not accessible
        """
        _load_google_libs()
        try:
            folder = self.service.files().get(
                fileId=folder_id,
                fields="id, name, mimeType",
                supportsAllDrives=True,
            ).execute()
            logger.info(f"Folder accessible: {folder.get('name')} ({folder_id})")
            return folder
        except HttpError as error:
            status_code = error.resp.status
            error_content = error.content.decode() if error.content else "No content"
            if status_code == 404:
                raise RuntimeError(
                    f"Folder not found or not shared with service account: {folder_id}\n"
                    "Make sure to share the folder with the service account email."
                )
            elif status_code == 403:
                raise RuntimeError(
                    f"Permission denied for folder {folder_id}: {error_content}\n"
                    "The service account may not have access to this folder."
                )
            else:
                raise RuntimeError(f"Error accessing folder: {error_content}")

    def upload_file(
        self,
        file_path: str | Path,
        folder_id: str,
        custom_name: str | None = None,
        progress_callback: Callable[[float], None] | None = None,
    ) -> dict:
        """Upload a file to Google Drive folder.

        Args:
            file_path: Local path to file
            folder_id: Google Drive folder ID
            custom_name: Optional custom filename in Drive
            progress_callback: Optional callback(progress: float) for progress updates

        Returns:
            dict with id, name, webViewLink

        Raises:
            FileNotFoundError: If file doesn't exist
            HttpError: If upload fails after retries
        """
        _load_google_libs()  # Ensure Google libs are loaded before using MediaFileUpload

        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_name = custom_name or file_path.name
        file_size = file_path.stat().st_size
        logger.info(
            f"Uploading {file_name} ({file_size / 1024 / 1024:.1f} MB) to folder {folder_id}"
        )

        file_metadata = {
            "name": file_name,
            "parents": [folder_id],
        }

        media = MediaFileUpload(
            str(file_path),
            mimetype="application/x-7z-compressed",
            chunksize=CHUNK_SIZE,
            resumable=True,
        )

        request = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, name, webViewLink",
            supportsAllDrives=True,  # Required for Shared Drives
        )

        return self._execute_resumable_upload(request, progress_callback)

    def _execute_resumable_upload(
        self,
        request,
        progress_callback: Callable[[float], None] | None = None,
    ) -> dict:
        """Execute resumable upload with retry logic."""
        response = None
        retries = 0
        chunk_num = 0

        while response is None:
            try:
                chunk_num += 1
                logger.debug(f"Uploading chunk {chunk_num}...")
                status, response = request.next_chunk()
                if status and progress_callback:
                    progress_callback(status.progress())
                    logger.debug(f"Chunk {chunk_num} progress: {status.progress()*100:.1f}%")
                retries = 0  # Reset on success

            except HttpError as error:
                status_code = error.resp.status
                error_content = error.content.decode() if error.content else "No content"
                logger.error(f"HTTP {status_code} on chunk {chunk_num}: {error_content}")

                if status_code in RETRYABLE_STATUS_CODES:
                    retries += 1
                    if retries > MAX_RETRIES:
                        logger.error(f"Max retries exceeded for status {status_code}")
                        raise

                    wait_time = min(2**retries + random.random(), 64)
                    logger.warning(
                        f"Retryable error {status_code}, "
                        f"retry {retries}/{MAX_RETRIES} in {wait_time:.1f}s"
                    )
                    time.sleep(wait_time)

                elif status_code == 404:
                    logger.error(f"404 error details: {error_content}")
                    raise RuntimeError(f"Upload failed (404): {error_content}")

                elif status_code == 403:
                    logger.error(f"Permission denied (403): {error_content}")
                    raise RuntimeError(f"Permission denied: {error_content}")

                else:
                    logger.error(f"Non-retryable error: {error}")
                    raise

        logger.info(f"Upload complete! File ID: {response.get('id')}")
        return response


# ============================================================================
# High-level API for use in run_all.py
# ============================================================================


def upload_archive(
    project_name: str,
    curr_date: str,
    base_path: str | Path | None = None,
    progress_callback: Callable[[float], None] | None = None,
    dry_run: bool = False,
    use_oauth: bool = False,
) -> dict:
    """Upload a project's 7z archive to Google Drive.

    This is the main entry point for integration with run_all.py.

    Args:
        project_name: Project name (e.g., "audiobee_bcbs_il")
        curr_date: Date string in YYYYMMDD format
        base_path: Base directory containing the archive. Defaults to project_name/.
        progress_callback: Optional callback(progress: float) for progress updates
        dry_run: If True, validate configuration without uploading
        use_oauth: If True, use OAuth 2.0 (for personal Drive folders).
            First run will open browser for Google login.

    Returns:
        dict with:
            - id: Google Drive file ID
            - name: Filename
            - webViewLink: URL to view the file
            - archive_path: Local path to the uploaded file

    Raises:
        FileNotFoundError: If archive or credentials not found
        KeyError: If project has no folder mapping
        HttpError: If upload fails

    Example:
        # In run_all.py:
        from tools.drive_uploader import upload_archive
        result = upload_archive(config.PROJECT_NAME, config.CURR_DATE)
        print(f"Uploaded: {result['webViewLink']}")
    """
    # Construct archive path: {base_path}/{curr_date}/{curr_date}.7z
    base_path = Path(project_name) if base_path is None else Path(base_path)

    archive_path = base_path / curr_date / f"{curr_date}.7z"

    if not archive_path.exists():
        raise FileNotFoundError(
            f"Archive not found at {archive_path}. "
            f"Run compress_folder_to_7z() first."
        )

    # Initialize uploader
    uploader = DriveUploader(use_oauth=use_oauth)

    # Get folder ID
    folder_id = uploader.get_folder_id(project_name)
    logger.info(f"Project: {project_name}, Folder ID: {folder_id}")

    # Validate folder access before upload
    folder_info = uploader.validate_folder_access(folder_id)
    logger.info(f"Target folder: {folder_info.get('name')}")

    if dry_run:
        logger.info(f"Dry run - would upload {archive_path} to folder {folder_id}")
        return {
            "id": "dry-run",
            "name": archive_path.name,
            "webViewLink": "dry-run",
            "archive_path": str(archive_path),
        }

    # Upload
    result = uploader.upload_file(
        file_path=archive_path,
        folder_id=folder_id,
        progress_callback=progress_callback,
    )
    result["archive_path"] = str(archive_path)
    return result


# ============================================================================
# CLI Interface
# ============================================================================

import sys

import typer
from tqdm import tqdm

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.project_config import load_project_config

app = typer.Typer(
    name="drive-uploader",
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

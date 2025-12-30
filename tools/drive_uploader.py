"""
Google Drive file uploader with resumable upload support.

Dependencies:
    pip install google-api-python-client google-auth

Environment Variables:
    GOOGLE_SERVICE_ACCOUNT_FILE: Path to service account JSON
"""
from __future__ import annotations

import json
import os
import random
import time
from pathlib import Path
from typing import Optional, Callable, TYPE_CHECKING

# Lazy imports for Google libraries (only required when actually uploading)
# This allows importing drive_uploader without google-auth installed
_google_libs_loaded = False
service_account = None
build = None
MediaFileUpload = None
HttpError = None


def _load_google_libs():
    """Lazy-load Google libraries on first use."""
    global _google_libs_loaded, service_account, build, MediaFileUpload, HttpError
    if _google_libs_loaded:
        return
    try:
        from google.oauth2 import service_account as sa
        from googleapiclient.discovery import build as bld
        from googleapiclient.http import MediaFileUpload as mfu
        from googleapiclient.errors import HttpError as he
        service_account = sa
        build = bld
        MediaFileUpload = mfu
        HttpError = he
        _google_libs_loaded = True
    except ImportError as e:
        raise ImportError(
            "Google Drive dependencies not installed. Run:\n"
            "  pip install google-api-python-client google-auth\n"
            "Or:\n"
            "  pip install -r tools/requirements.txt"
        ) from e


try:
    from core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_RETRIES = 5
RETRYABLE_STATUS_CODES = (429, 500, 502, 503, 504)


class DriveUploader:
    """Upload files to Google Drive with resumable upload support."""

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        mapping_path: Optional[str] = None,
    ):
        """Initialize uploader.

        Args:
            credentials_path: Path to service account JSON. Defaults to
                GOOGLE_SERVICE_ACCOUNT_FILE env var or tools/google_drive_credentials.json.
            mapping_path: Path to folder mapping JSON. Defaults to
                tools/drive_folder_mapping.json.
        """
        # Resolve paths relative to tools/ directory (where this file lives)
        tools_dir = Path(__file__).parent

        self.credentials_path = Path(
            credentials_path
            or os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
            or (tools_dir / "google_drive_credentials.json")
        )
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
            credentials = service_account.Credentials.from_service_account_file(
                str(self.credentials_path),
                scopes=SCOPES,
            )
            self._service = build("drive", "v3", credentials=credentials)
            logger.info("Authenticated with Google Drive API")
        return self._service

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

    def upload_file(
        self,
        file_path: str | Path,
        folder_id: str,
        custom_name: Optional[str] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
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
        )

        return self._execute_resumable_upload(request, progress_callback)

    def _execute_resumable_upload(
        self,
        request,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> dict:
        """Execute resumable upload with retry logic."""
        response = None
        retries = 0

        while response is None:
            try:
                status, response = request.next_chunk()
                if status and progress_callback:
                    progress_callback(status.progress())
                retries = 0  # Reset on success

            except HttpError as error:
                status_code = error.resp.status

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
                    logger.error("Upload session expired - restart required")
                    raise RuntimeError("Upload session expired, please retry")

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
    base_path: Optional[str | Path] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
    dry_run: bool = False,
) -> dict:
    """Upload a project's 7z archive to Google Drive.

    This is the main entry point for integration with run_all.py.

    Args:
        project_name: Project name (e.g., "audiobee_bcbs_il")
        curr_date: Date string in YYYYMMDD format
        base_path: Base directory containing the archive. Defaults to project_name/.
        progress_callback: Optional callback(progress: float) for progress updates
        dry_run: If True, validate configuration without uploading

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
    if base_path is None:
        base_path = Path(project_name)
    else:
        base_path = Path(base_path)

    archive_path = base_path / curr_date / f"{curr_date}.7z"

    if not archive_path.exists():
        raise FileNotFoundError(
            f"Archive not found at {archive_path}. "
            f"Run compress_folder_to_7z() first."
        )

    # Initialize uploader
    uploader = DriveUploader()

    # Get folder ID
    folder_id = uploader.get_folder_id(project_name)
    logger.info(f"Project: {project_name}, Folder ID: {folder_id}")

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

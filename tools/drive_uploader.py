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
from typing import Optional, Callable

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

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
        self.credentials_path = Path(
            credentials_path
            or os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
            or "tools/google_drive_credentials.json"
        )
        self.mapping_path = Path(mapping_path or "tools/drive_folder_mapping.json")

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

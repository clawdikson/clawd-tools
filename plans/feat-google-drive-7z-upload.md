# feat: Google Drive 7z Archive Upload Script

## Overview

Create a Python script that uploads 7z archive files to specific Google Drive folders. The script will:
- Accept a project name as user input
- Auto-detect project type (Audiobee config.py vs HealthSparq YAML)
- Load `CURR_DATE` from project configuration (or accept via CLI for HealthSparq)
- Construct file path: `{PROJECT_NAME}/{CURR_DATE}/{CURR_DATE}.7z`
- Upload to the mapped Google Drive folder for that project

## Problem Statement

Currently, there's no automated way to upload scraper output archives to Google Drive. After completing a scraping run and creating a 7z archive, users must manually:
1. Navigate to Google Drive
2. Find the correct folder for the project
3. Upload the file manually

This is error-prone (wrong folder) and time-consuming (manual process for 86+ projects).

## Proposed Solution

Create `tools/upload_to_drive.py` - a CLI tool that automates Google Drive uploads with:
- Service account authentication (no user interaction)
- Project-to-folder mapping configuration
- Automatic config detection (config.py vs YAML)
- Resumable uploads for large files
- Progress reporting and structured logging

## Technical Approach

### Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          upload_to_drive.py                               │
├──────────────────────────────────────────────────────────────────────────┤
│  CLI Interface (Typer)                                                    │
│  └── upload(project_name: str, date: Optional[str], dry_run: bool)       │
├──────────────────────────────────────────────────────────────────────────┤
│  Project Config Loader                                                    │
│  ├── detect_project_type(project_name) → Audiobee | HealthSparq          │
│  ├── load_audiobee_config(project_name) → CURR_DATE                      │
│  └── load_healthsparq_config(project_name) → project metadata            │
├──────────────────────────────────────────────────────────────────────────┤
│  Drive Folder Mapping                                                     │
│  └── get_folder_id(project_name) → Google Drive folder ID                │
├──────────────────────────────────────────────────────────────────────────┤
│  Google Drive Uploader (google-api-python-client)                        │
│  ├── authenticate() → Service credentials                                │
│  ├── validate_folder(folder_id) → bool                                   │
│  └── upload_file(file_path, folder_id) → file_url                       │
└──────────────────────────────────────────────────────────────────────────┘
```

### Configuration Files

**1. Folder Mapping (`tools/drive_folder_mapping.json`)**

```json
{
  "audiobee_bcbs_il": "1AbCdEfGhIjKlMnOpQrStUvWxYz",
  "audiobee_excellus": "1BcDeFgHiJkLmNoPqRsTuVwXyZ0",
  "christus_health_plan": "1CdEfGhIjKlMnOpQrStUvWxYz12"
}
```

**2. Google Drive Credentials (`tools/google_drive_credentials.json`)**

Service account JSON (excluded from git via .gitignore). Must be created by user in Google Cloud Console.

**3. Environment Variables (`.env`)**

```bash
# Optional: Override default credential path
GOOGLE_SERVICE_ACCOUNT_FILE=tools/google_drive_credentials.json

# Optional: Enable verbose logging
DRIVE_UPLOAD_DEBUG=false
```

### Implementation Phases

#### Phase 1: Foundation (Core Upload Logic)
Tasks 1-3: Configuration loading, Drive authentication, basic upload

#### Phase 2: Project Integration
Tasks 4-6: Config.py parsing, HealthSparq YAML support, file path construction

#### Phase 3: Error Handling & UX
Tasks 7-9: Resumable uploads, progress reporting, error messages

#### Phase 4: Testing & Documentation
Tasks 10-12: Unit tests, integration tests, documentation

## Acceptance Criteria

### Functional Requirements

- [ ] Upload 7z file from `{PROJECT_NAME}/{CURR_DATE}/{CURR_DATE}.7z` to mapped Google Drive folder
- [ ] Support both Audiobee (config.py) and HealthSparq (YAML) project types
- [ ] Accept `--date` argument to override CURR_DATE (required for HealthSparq)
- [ ] Display upload progress for files > 1MB
- [ ] Report success with Google Drive file URL
- [ ] Support `--dry-run` flag to validate without uploading

### Non-Functional Requirements

- [ ] Use resumable uploads for reliability (files can be multi-GB)
- [ ] Implement exponential backoff for rate limit/server errors
- [ ] Integrate with core/logging for structured logging
- [ ] Handle network interruptions gracefully (retry with backoff)
- [ ] Exit with appropriate codes (0=success, 1=error)

### Quality Gates

- [ ] Unit tests for config loading, path construction
- [ ] Integration test with real Google Drive (test folder)
- [ ] Documentation in tools/README.md
- [ ] .gitignore entries for credentials

## Dependencies & Prerequisites

### Python Dependencies

```
google-api-python-client>=2.100.0
google-auth>=2.25.0
typer>=0.9.0
tqdm>=4.66.0
```

### External Setup Required

1. **Google Cloud Project** with Drive API enabled
2. **Service Account** with credentials JSON downloaded
3. **Drive Folders** shared with service account email
4. **Folder Mapping** configured in `tools/drive_folder_mapping.json`

## Risk Analysis & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Credential leakage | Medium | High | .gitignore, environment variables |
| Network failures | Medium | Medium | Resumable uploads, retry logic |
| Rate limiting | Low | Medium | Exponential backoff |
| Wrong folder mapping | Medium | Medium | Dry-run validation, logging |
| Large file uploads | High | Low | Resumable uploads, progress bar |

## MVP Implementation

### Task 1: Create Drive Folder Mapping Schema

**File**: `tools/drive_folder_mapping.json`

```json
{
  "_comment": "Map project names to Google Drive folder IDs. Get folder ID from Drive URL.",
  "_example_url": "https://drive.google.com/drive/folders/1ABC123xyz → folder_id = 1ABC123xyz",
  "projects": {}
}
```

**Why**: Define the data structure before writing code.

---

### Task 2: Create Google Drive Uploader Class

**File**: `tools/drive_uploader.py`

```python
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
from typing import Optional

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

        if not self.credentials_path.exists():
            raise FileNotFoundError(
                f"Google Drive credentials not found at {self.credentials_path}. "
                "See tools/README.md for setup instructions."
            )

        self._service = None
        self._folder_mapping: dict[str, str] = {}

    @property
    def service(self):
        """Lazy-load authenticated Drive API service."""
        if self._service is None:
            credentials = service_account.Credentials.from_service_account_file(
                str(self.credentials_path),
                scopes=SCOPES,
            )
            self._service = build("drive", "v3", credentials=credentials)
            logger.info("Authenticated with Google Drive API")
        return self._service

    def load_folder_mapping(self) -> dict[str, str]:
        """Load project → folder ID mapping from JSON file."""
        if not self._folder_mapping:
            if not self.mapping_path.exists():
                raise FileNotFoundError(
                    f"Folder mapping not found at {self.mapping_path}. "
                    "Create it with project → folder ID mappings."
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
            raise KeyError(
                f"No Drive folder mapping for project '{project_name}'. "
                f"Available projects: {available}..."
            )
        return mapping[project_name]

    def upload_file(
        self,
        file_path: str | Path,
        folder_id: str,
        custom_name: Optional[str] = None,
        progress_callback: Optional[callable] = None,
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
        progress_callback: Optional[callable] = None,
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
```

**Why**: Core upload functionality with production-ready error handling.

---

### Task 3: Create Project Config Loader

**File**: `tools/project_config.py`

```python
"""
Project configuration loader for upload_to_drive.

Supports:
- Audiobee projects: Load CURR_DATE from config.py
- HealthSparq projects: Load metadata from healthsparq/configs/{project}.yaml
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import NamedTuple, Optional

import yaml

try:
    from core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class ProjectConfig(NamedTuple):
    """Project configuration for upload."""

    name: str
    project_type: str  # "audiobee" or "healthsparq"
    curr_date: Optional[str]
    base_path: Path


def detect_project_type(project_name: str, base_dir: Path = Path(".")) -> str:
    """Detect whether project is Audiobee (config.py) or HealthSparq (YAML).

    Args:
        project_name: Project name (e.g., "audiobee_bcbs_il" or "christus_health_plan")
        base_dir: Base directory to search from

    Returns:
        "audiobee" or "healthsparq"

    Raises:
        FileNotFoundError: If project config not found
    """
    # Check for Audiobee config.py
    audiobee_config = base_dir / project_name / "config.py"
    if audiobee_config.exists():
        return "audiobee"

    # Check for HealthSparq YAML config
    healthsparq_config = base_dir / "healthsparq" / "configs" / f"{project_name}.yaml"
    if healthsparq_config.exists():
        return "healthsparq"

    raise FileNotFoundError(
        f"Project '{project_name}' not found. Checked:\n"
        f"  - {audiobee_config}\n"
        f"  - {healthsparq_config}\n"
        "Ensure project name is correct."
    )


def extract_curr_date_from_config_py(config_path: Path) -> str:
    """Extract CURR_DATE from config.py using AST parsing.

    Args:
        config_path: Path to config.py file

    Returns:
        CURR_DATE value as string (e.g., "20251110")

    Raises:
        ValueError: If CURR_DATE not found or has invalid format
    """
    with open(config_path) as f:
        source = f.read()

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        raise ValueError(f"Syntax error in {config_path}: {e}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "CURR_DATE":
                    if isinstance(node.value, ast.Constant):
                        value = str(node.value.value)
                        # Validate date format (YYYYMMDD)
                        if len(value) == 8 and value.isdigit():
                            return value
                        raise ValueError(
                            f"CURR_DATE '{value}' in {config_path} is not YYYYMMDD format"
                        )

    raise ValueError(f"CURR_DATE not found in {config_path}")


def load_project_config(
    project_name: str,
    date_override: Optional[str] = None,
    base_dir: Path = Path("."),
) -> ProjectConfig:
    """Load project configuration for upload.

    Args:
        project_name: Project name
        date_override: Optional date to use instead of config value
        base_dir: Base directory

    Returns:
        ProjectConfig with name, type, date, and path

    Raises:
        FileNotFoundError: If project not found
        ValueError: If date invalid or required but missing
    """
    project_type = detect_project_type(project_name, base_dir)
    curr_date = date_override

    if project_type == "audiobee":
        base_path = base_dir / project_name
        if not curr_date:
            config_path = base_path / "config.py"
            curr_date = extract_curr_date_from_config_py(config_path)
            logger.info(f"Loaded CURR_DATE={curr_date} from {config_path}")

    elif project_type == "healthsparq":
        # HealthSparq projects: output goes to healthsparq/{project_slug}/{date}/
        # or project-specific directory if it exists
        project_dir = base_dir / project_name
        if project_dir.exists():
            base_path = project_dir
        else:
            base_path = base_dir / "healthsparq" / project_name

        if not curr_date:
            # Try to find latest date directory
            possible_dates = []
            for subdir in base_path.iterdir() if base_path.exists() else []:
                if subdir.is_dir() and len(subdir.name) == 8 and subdir.name.isdigit():
                    possible_dates.append(subdir.name)

            if possible_dates:
                curr_date = sorted(possible_dates)[-1]  # Latest date
                logger.info(f"Auto-detected CURR_DATE={curr_date} from {base_path}")
            else:
                raise ValueError(
                    f"HealthSparq project '{project_name}' requires --date argument. "
                    f"No date directories found in {base_path}."
                )

    # Validate date format
    if curr_date and (len(curr_date) != 8 or not curr_date.isdigit()):
        raise ValueError(f"Date '{curr_date}' must be YYYYMMDD format (e.g., 20251227)")

    return ProjectConfig(
        name=project_name,
        project_type=project_type,
        curr_date=curr_date,
        base_path=base_path,
    )
```

**Why**: Clean separation between project detection and upload logic.

---

### Task 4: Create Main CLI Script

**File**: `tools/upload_to_drive.py`

```python
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
from typing import Optional

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
    date: Optional[str] = typer.Option(
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
    date: Optional[str] = typer.Option(None, "--date", "-d", help="Date in YYYYMMDD format"),
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
```

**Why**: Complete CLI with upload, list, and validate commands.

---

### Task 5: Create .gitignore Entries

**Add to**: `.gitignore`

```gitignore
# Google Drive credentials (NEVER commit these)
tools/google_drive_credentials.json
google_drive_credentials.json
**/service-account*.json
**/credentials*.json
```

**Why**: Prevent accidental credential leakage.

---

### Task 6: Create Setup Documentation

**File**: `tools/README.md` (append to existing)

```markdown
---

## upload_to_drive.py

Upload 7z archives to Google Drive.

### Setup

#### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable the **Google Drive API**:
   - Go to APIs & Services → Library
   - Search for "Google Drive API"
   - Click Enable

#### Step 2: Create Service Account

1. Go to APIs & Services → Credentials
2. Click "Create Credentials" → "Service Account"
3. Name it (e.g., "scraper-drive-uploader")
4. Skip optional steps (no roles needed, no users)
5. Click on the created service account
6. Go to "Keys" tab → "Add Key" → "Create new key"
7. Select JSON format and download
8. Save as `tools/google_drive_credentials.json`

**Important**: The service account email looks like `name@project.iam.gserviceaccount.com`. You'll need this to share folders.

#### Step 3: Share Drive Folders

For each project folder in Google Drive:

1. Right-click folder → "Share"
2. Paste the service account email
3. Set permission to "Editor"
4. Uncheck "Notify people"
5. Click "Share"

#### Step 4: Create Folder Mapping

Edit `tools/drive_folder_mapping.json`:

```json
{
  "projects": {
    "audiobee_bcbs_il": "1AbCdEfGhIjKlMnOpQrStUvWxYz",
    "audiobee_excellus": "1BcDeFgHiJkLmNoPqRsTuVwXyZ0",
    "christus_health_plan": "1CdEfGhIjKlMnOpQrStUvWxYz12"
  }
}
```

**Getting Folder IDs**: Open the folder in Google Drive. The URL will be:
```
https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUvWxYz
                                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                        This is the folder ID
```

### Usage

```bash
# Audiobee project (reads CURR_DATE from config.py)
python tools/upload_to_drive.py audiobee_bcbs_il

# HealthSparq project (requires --date since no config.py)
python tools/upload_to_drive.py christus_health_plan --date 20251227

# Override date for any project
python tools/upload_to_drive.py audiobee_bcbs_il --date 20251210

# Validate without uploading
python tools/upload_to_drive.py audiobee_bcbs_il --dry-run

# List configured projects
python tools/upload_to_drive.py list-projects

# Validate project configuration
python tools/upload_to_drive.py validate audiobee_bcbs_il
```

### Example Output

```
Project: audiobee_bcbs_il (audiobee)
Date: 20251110
Archive: audiobee_bcbs_il/20251110/20251110.7z
Drive folder ID: 1AbCdEfGhIjKlMnOpQrStUvWxYz
Uploading: 100%|████████████████████████████| 00:45<00:00

Upload successful!
File ID: 1XyZaBcDeFgHiJkLmNoPqRs
View: https://drive.google.com/file/d/1XyZaBcDeFgHiJkLmNoPqRs/view
```

### Troubleshooting

**Error**: "Google Drive credentials not found"
- **Fix**: Download service account JSON from Google Cloud Console
- **Location**: Save to `tools/google_drive_credentials.json`

**Error**: "No Drive folder mapping for project 'X'"
- **Fix**: Add project to `tools/drive_folder_mapping.json`
- **Get folder ID**: From Google Drive folder URL

**Error**: "The user does not have sufficient permissions for this file"
- **Fix**: Share the Google Drive folder with the service account email
- **Find email**: In `tools/google_drive_credentials.json` under `client_email`

**Error**: "File not found: {project}/{date}/{date}.7z"
- **Fix**: Create the 7z archive first
- **Command**: `cd {project}/{date} && 7z a {date}.7z processed/`

**Error**: "Upload session expired"
- **Cause**: Network interruption during upload
- **Fix**: Re-run the command (uploads are resumable)
```

**Why**: Complete setup guide for users.

---

### Task 7: Add Dependencies to pyproject.toml (or requirements.txt)

**Option A - Add to `tools/requirements.txt`** (new file):

```txt
# Google Drive Upload Dependencies
google-api-python-client>=2.100.0
google-auth>=2.25.0
typer>=0.9.0
tqdm>=4.66.0
pyyaml>=6.0
```

**Option B - If using pyproject.toml**, add to `[project.optional-dependencies]`:

```toml
[project.optional-dependencies]
drive = [
    "google-api-python-client>=2.100.0",
    "google-auth>=2.25.0",
    "typer>=0.9.0",
    "tqdm>=4.66.0",
]
```

**Why**: Document required dependencies.

---

### Task 8: Create Unit Tests

**File**: `tools/tests/test_upload_to_drive.py`

```python
"""Unit tests for upload_to_drive functionality."""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.project_config import (
    detect_project_type,
    extract_curr_date_from_config_py,
    load_project_config,
)


class TestDetectProjectType:
    """Tests for detect_project_type function."""

    def test_audiobee_project_with_config_py(self, tmp_path):
        """Should detect audiobee project when config.py exists."""
        project_dir = tmp_path / "audiobee_test"
        project_dir.mkdir()
        (project_dir / "config.py").write_text('CURR_DATE = "20251227"')

        result = detect_project_type("audiobee_test", tmp_path)
        assert result == "audiobee"

    def test_healthsparq_project_with_yaml(self, tmp_path):
        """Should detect healthsparq project when YAML config exists."""
        configs_dir = tmp_path / "healthsparq" / "configs"
        configs_dir.mkdir(parents=True)
        (configs_dir / "test_project.yaml").write_text("project:\n  name: Test")

        result = detect_project_type("test_project", tmp_path)
        assert result == "healthsparq"

    def test_nonexistent_project_raises_error(self, tmp_path):
        """Should raise FileNotFoundError for unknown project."""
        with pytest.raises(FileNotFoundError, match="not found"):
            detect_project_type("nonexistent", tmp_path)


class TestExtractCurrDate:
    """Tests for extract_curr_date_from_config_py function."""

    def test_extracts_valid_date(self, tmp_path):
        """Should extract CURR_DATE from config.py."""
        config_file = tmp_path / "config.py"
        config_file.write_text('PREV_DATE = "20251010"\nCURR_DATE = "20251227"\n')

        result = extract_curr_date_from_config_py(config_file)
        assert result == "20251227"

    def test_raises_on_missing_curr_date(self, tmp_path):
        """Should raise ValueError if CURR_DATE not found."""
        config_file = tmp_path / "config.py"
        config_file.write_text('PREV_DATE = "20251010"\n')

        with pytest.raises(ValueError, match="not found"):
            extract_curr_date_from_config_py(config_file)

    def test_raises_on_invalid_date_format(self, tmp_path):
        """Should raise ValueError for non-YYYYMMDD format."""
        config_file = tmp_path / "config.py"
        config_file.write_text('CURR_DATE = "2025-12-27"\n')

        with pytest.raises(ValueError, match="not YYYYMMDD"):
            extract_curr_date_from_config_py(config_file)

    def test_raises_on_syntax_error(self, tmp_path):
        """Should raise ValueError for malformed config.py."""
        config_file = tmp_path / "config.py"
        config_file.write_text('CURR_DATE = "20251227\n')  # Missing closing quote

        with pytest.raises(ValueError, match="Syntax error"):
            extract_curr_date_from_config_py(config_file)


class TestLoadProjectConfig:
    """Tests for load_project_config function."""

    def test_loads_audiobee_config(self, tmp_path):
        """Should load config from audiobee project."""
        project_dir = tmp_path / "audiobee_test"
        project_dir.mkdir()
        (project_dir / "config.py").write_text('CURR_DATE = "20251227"')

        config = load_project_config("audiobee_test", base_dir=tmp_path)

        assert config.name == "audiobee_test"
        assert config.project_type == "audiobee"
        assert config.curr_date == "20251227"
        assert config.base_path == project_dir

    def test_date_override_takes_precedence(self, tmp_path):
        """Should use date_override instead of config.py value."""
        project_dir = tmp_path / "audiobee_test"
        project_dir.mkdir()
        (project_dir / "config.py").write_text('CURR_DATE = "20251110"')

        config = load_project_config(
            "audiobee_test",
            date_override="20251227",
            base_dir=tmp_path,
        )

        assert config.curr_date == "20251227"

    def test_validates_date_format(self, tmp_path):
        """Should reject invalid date format."""
        project_dir = tmp_path / "audiobee_test"
        project_dir.mkdir()
        (project_dir / "config.py").write_text('CURR_DATE = "20251227"')

        with pytest.raises(ValueError, match="YYYYMMDD"):
            load_project_config(
                "audiobee_test",
                date_override="2025-12-27",  # Invalid format
                base_dir=tmp_path,
            )
```

**Why**: Ensure config loading works correctly.

---

### Task 9: Create Integration Test

**File**: `tools/tests/test_drive_integration.py`

```python
"""Integration tests for Google Drive upload (requires credentials)."""
import os
import tempfile
from pathlib import Path

import pytest

# Skip all tests if credentials not available
pytestmark = pytest.mark.skipif(
    not os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
    and not Path("tools/google_drive_credentials.json").exists(),
    reason="Google Drive credentials not configured",
)


class TestDriveUploaderIntegration:
    """Integration tests for DriveUploader class."""

    @pytest.fixture
    def uploader(self):
        """Create uploader instance."""
        from tools.drive_uploader import DriveUploader

        return DriveUploader()

    @pytest.fixture
    def test_folder_id(self):
        """Get test folder ID from environment or skip."""
        folder_id = os.environ.get("GOOGLE_DRIVE_TEST_FOLDER_ID")
        if not folder_id:
            pytest.skip("GOOGLE_DRIVE_TEST_FOLDER_ID not set")
        return folder_id

    def test_authentication(self, uploader):
        """Should authenticate successfully with valid credentials."""
        # Accessing .service triggers authentication
        service = uploader.service
        assert service is not None

    def test_upload_small_file(self, uploader, test_folder_id, tmp_path):
        """Should upload a small test file successfully."""
        # Create test file
        test_file = tmp_path / "test_upload.txt"
        test_file.write_text("Test content for upload")

        # Upload
        result = uploader.upload_file(
            file_path=test_file,
            folder_id=test_folder_id,
        )

        assert "id" in result
        assert "webViewLink" in result

        # Cleanup: Delete uploaded file
        uploader.service.files().delete(fileId=result["id"]).execute()
```

**Why**: Verify actual Google Drive integration works.

---

### Task 10: Create Initial Folder Mapping Template

**File**: `tools/drive_folder_mapping.json`

```json
{
  "_comment": "Map project names to Google Drive folder IDs",
  "_setup_instructions": [
    "1. Open the target folder in Google Drive",
    "2. Copy folder ID from URL: https://drive.google.com/drive/folders/[FOLDER_ID]",
    "3. Share folder with service account email (from google_drive_credentials.json)",
    "4. Add mapping below: \"project_name\": \"folder_id\""
  ],
  "projects": {
  }
}
```

**Why**: Ready-to-use template with setup instructions.

---

## References & Research

### Internal References

- `tools/README.md:1-364` - Existing tools documentation structure
- `audiobee_bcbs_il/config.py:7-8` - CURR_DATE/PREV_DATE pattern
- `healthsparq/configs/christus_health_plan.yaml` - YAML config structure
- `core/logging/logger.py` - Logging integration pattern

### External References

- [Google Drive API Python Quickstart](https://developers.google.com/drive/api/quickstart/python)
- [Service Account Authentication](https://cloud.google.com/iam/docs/service-account-creds)
- [Resumable Upload Guide](https://developers.google.com/workspace/drive/api/guides/manage-uploads#resumable)
- [google-api-python-client GitHub](https://github.com/googleapis/google-api-python-client)

### Related Work

- No existing Google Drive integration in codebase
- `output_generator/` has archive creation that could integrate with this

---

## Future Considerations

### Potential Enhancements (Not in MVP)

1. **Batch upload** - `--all` flag to upload all mapped projects
2. **Archive creation** - Integrate with 7z archive creation
3. **Duplicate detection** - Check if file already exists (by hash)
4. **Folder validation** - Pre-check folder exists and is accessible
5. **Notification** - Slack/email notification on upload complete
6. **Audit log** - CSV of all uploads for compliance

### Integration Points

- Add to `run_all.py` pipeline after archiving step
- Add to `tools/run_parallel.py` for batch operations
- Add to CI/CD for automated uploads after scraper runs

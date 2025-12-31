# feat: S3 JSONL Upload with Presigned URL + Enhanced Email Report

## Overview

Add S3 upload functionality for project JSONL files with presigned URL generation, and enhance the existing email report to include the presigned URL and run metadata JSON block.

## Problem Statement / Motivation

Currently, JSONL output files are only stored locally and uploaded to Google Drive. Stakeholders need:
1. Programmatic access to JSONL files via S3 presigned URLs
2. Run metadata (duration, end time) included in email reports for tracking
3. API integration capability via structured JSON data in emails

## Proposed Solution

Create a **new S3 upload module** `tools/s3_uploader.py` and **enhance the existing email** in `xlsx_to_clickup.py`:

1. **`tools/s3_uploader.py`** (NEW) - S3 upload functionality with presigned URL generation
2. **`tools/xlsx_to_clickup.py`** (MODIFY) - Add optional S3 upload + JSON metadata to existing `send_report_email()`

This approach:
- Keeps all email sending in one place (`xlsx_to_clickup.py`)
- Avoids duplicate emails - just enhances the existing one
- S3 upload is a separate reusable module

### JSON Data Structure (in email body)
```json
{
    "json_url": "<presigned_s3_url>",
    "project_name": "<from config.PROJECT_NAME>",
    "run_ended": "<from XLSX cell A8 'Last File Created' timestamp>",
    "run_duration": <seconds_between_first_and_last_file>,
    "api_key": "mc!G3mibFdirRd"
}
```

## Technical Approach

### Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Project Files  │────▶│  S3Uploader      │────▶│  S3 Bucket      │
│  - JSONL        │     │  - upload_jsonl  │     │  /{project}/    │
│  - XLSX         │     │  - presigned_url │     │  /{date}/       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │
         │                       ▼
         │              ┌──────────────────┐
         └─────────────▶│  EmailClient     │
                        │  - parse_xlsx    │
                        │  - send_email    │
                        │  + JSON metadata │
                        └──────────────────┘
```

### S3 Configuration

| Setting | Source | Default |
|---------|--------|---------|
| Bucket Name | `S3_BUCKET_NAME` env var | Required |
| Region | `AWS_DEFAULT_REGION` env var | `us-east-1` |
| Credentials | AWS SDK default chain | `~/.aws/credentials` or env vars |
| Presigned URL Expiry | `--expires-in` CLI flag | 7 days (604800s) |

### S3 Object Key Structure
```
{bucket}/{project_name}/{curr_date}/processed/{project_name}-{curr_date}.jsonl
```
Example: `s3://audiobee-scrapers/audiobee_bcbs_il/20251227/processed/audiobee_bcbs_il-20251227.jsonl`

### File Locations

| File | Purpose |
|------|---------|
| `tools/s3_uploader.py` | **NEW** - S3Uploader class with presigned URL generation |
| `tools/xlsx_to_clickup.py` | **MODIFY** - Add S3 upload + JSON metadata to existing email |
| `tools/tests/test_s3_uploader.py` | **NEW** - Unit tests for S3 upload functionality |

## Implementation Phases

### Phase 1: Create S3 Uploader Module

**Files to create:**
- `tools/s3_uploader.py` (NEW)

```python
#!/usr/bin/env python3
"""S3 upload functionality with presigned URL generation.

This module provides S3 upload capabilities for JSONL files.
Used by xlsx_to_clickup.py for enhanced email reports.

Environment Variables:
    S3_BUCKET_NAME: Target S3 bucket (required)
    AWS_ACCESS_KEY_ID: AWS access key (or use ~/.aws/credentials)
    AWS_SECRET_ACCESS_KEY: AWS secret key (or use ~/.aws/credentials)
    AWS_DEFAULT_REGION: AWS region (default: us-east-1)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


# =============================================================================
# S3 Configuration
# =============================================================================

@dataclass
class S3Config:
    """S3 configuration from environment variables."""
    bucket_name: str
    region: str = "us-east-1"
    presigned_expiry: int = 604800  # 7 days

    @classmethod
    def from_env(cls) -> "S3Config":
        bucket = os.environ.get("S3_BUCKET_NAME")
        if not bucket:
            raise ValueError(
                "S3_BUCKET_NAME environment variable not set.\n"
                "Set it with: export S3_BUCKET_NAME='your-bucket-name'"
            )
        return cls(
            bucket_name=bucket,
            region=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
        )


# =============================================================================
# S3 Uploader
# =============================================================================

# Lazy-loaded boto3
_boto3_loaded = False
boto3_client = None
botocore_config = None


def _load_boto3():
    """Lazy-load boto3 on first use."""
    global _boto3_loaded, boto3_client, botocore_config
    if _boto3_loaded:
        return
    try:
        import boto3
        from botocore.config import Config
        boto3_client = boto3
        botocore_config = Config
        _boto3_loaded = True
    except ImportError as e:
        raise ImportError(
            "boto3 not installed. Run:\n"
            "  pip install boto3"
        ) from e


class S3Uploader:
    """S3 client for JSONL uploads with presigned URL generation."""

    def __init__(self, config: S3Config):
        self.config = config
        self._client = None

    @property
    def client(self):
        """Lazy-load boto3 S3 client."""
        if self._client is None:
            _load_boto3()
            boto_config = botocore_config(
                signature_version='s3v4',
                retries={'max_attempts': 5, 'mode': 'standard'}
            )
            self._client = boto3_client.client(
                's3',
                region_name=self.config.region,
                config=boto_config
            )
        return self._client

    def upload_jsonl(
        self,
        local_path: Path,
        project_name: str,
        curr_date: str,
    ) -> str:
        """Upload JSONL file to S3.

        Returns:
            S3 object key
        """
        object_key = f"{project_name}/{curr_date}/processed/{project_name}-{curr_date}.jsonl"

        self.client.upload_file(
            str(local_path),
            self.config.bucket_name,
            object_key,
            ExtraArgs={'ContentType': 'application/x-ndjson'}
        )

        logger.info(f"Uploaded to s3://{self.config.bucket_name}/{object_key}")
        return object_key

    def generate_presigned_url(
        self,
        object_key: str,
        expiration: Optional[int] = None,
    ) -> str:
        """Generate presigned URL for S3 object."""
        expiry = expiration or self.config.presigned_expiry

        url = self.client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': self.config.bucket_name,
                'Key': object_key,
            },
            ExpiresIn=expiry
        )

        logger.info(f"Generated presigned URL (expires in {expiry}s)")
        return url
```

**Tasks:**
- [ ] Create `tools/s3_uploader.py` with S3Config and S3Uploader classes
- [ ] Implement upload_jsonl() with Content-Type header
- [ ] Implement generate_presigned_url() with s3v4 signature
- [ ] Add lazy boto3 import pattern (like Gmail libraries)
- [ ] Add boto3 to `tools/requirements.txt`

### Phase 2: XLSX Timestamp Parsing

**Files to modify:**
- `tools/xlsx_to_clickup.py` (add timestamp parsing function)

```python
# Add to xlsx_to_clickup.py

# =============================================================================
# XLSX Timestamp Parsing (for S3 email metadata)
# =============================================================================

def parse_run_timestamps(xlsx_path: Path) -> dict:
    """Extract run timestamps from XLSX state counts file.

    Parses cells A8 (First File Created) and A9 (Last File Created).

    Returns:
        dict with keys:
        - first_file_created: datetime or None
        - last_file_created: datetime or None
        - run_duration_seconds: int or 0
        - run_ended_str: str (formatted timestamp)
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
            result["run_ended_str"] = timestamp_str
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse A9: {cell_a9} - {e}")

    # Calculate duration
    if result["first_file_created"] and result["last_file_created"]:
        delta = result["last_file_created"] - result["first_file_created"]
        result["run_duration_seconds"] = max(0, int(delta.total_seconds()))

    wb.close()
    return result
```

**Tasks:**
- [ ] Implement parse_run_timestamps() function
- [ ] Handle missing/malformed cells gracefully
- [ ] Return structured dict with timestamps and duration

### Phase 3: Enhance send_report_email() with S3 Support

**Files to modify:**
- `tools/xlsx_to_clickup.py` (modify existing function)

```python
# Modify send_report_email() in xlsx_to_clickup.py to add optional S3 upload

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
    # NEW PARAMETERS:
    upload_to_s3: bool = False,  # Enable S3 upload
    s3_expires_in: int = 604800,  # Presigned URL expiry (7 days)
) -> dict:
    """Generate screenshot from XLSX and send via Gmail.

    When upload_to_s3=True, also:
    - Uploads JSONL to S3
    - Generates presigned URL
    - Parses run timestamps from XLSX
    - Adds JSON metadata block to email body

    Args:
        ...existing args...
        upload_to_s3: If True, upload JSONL to S3 and include metadata in email
        s3_expires_in: Presigned URL expiration in seconds (default 7 days)

    Returns:
        dict with:
        - message_id: Gmail message ID
        - xlsx_path: Path to source XLSX file
        - screenshot_path: Path to generated PNG
        - s3_key: S3 object key (if upload_to_s3=True)
        - presigned_url: S3 presigned URL (if upload_to_s3=True)
        - run_metadata: Parsed timestamps (if upload_to_s3=True)
    """
    # ... existing code ...

    # NEW: S3 upload and metadata if enabled
    s3_result = {}
    if upload_to_s3:
        try:
            from s3_uploader import S3Uploader, S3Config
        except ImportError:
            from tools.s3_uploader import S3Uploader, S3Config

        # Upload JSONL to S3
        jsonl_path = resolve_jsonl_path(project_name, curr_date, base_path)
        s3_config = S3Config.from_env()
        s3_config.presigned_expiry = s3_expires_in
        uploader = S3Uploader(s3_config)

        s3_key = uploader.upload_jsonl(jsonl_path, project_name, curr_date)
        presigned_url = uploader.generate_presigned_url(s3_key)

        # Parse run timestamps
        run_timestamps = parse_run_timestamps(xlsx_path)

        # Build JSON metadata
        json_metadata = {
            "json_url": presigned_url,
            "project_name": project_name,
            "run_ended": run_timestamps["run_ended_str"],
            "run_duration": run_timestamps["run_duration_seconds"],
            "api_key": "mc!G3mibFdirRd"
        }

        # Append to email body
        email_body = f"""{email_body}

---
JSONL Download URL (expires in {s3_expires_in // 86400} days):
{presigned_url}

Run Metadata:
{json.dumps(json_metadata, indent=2)}
"""
        s3_result = {
            "s3_key": s3_key,
            "presigned_url": presigned_url,
            "run_metadata": run_timestamps,
        }

    # ... rest of existing send_report_email code ...

    return {
        "message_id": result.get("id"),
        "xlsx_path": str(xlsx_path),
        "screenshot_path": str(output_path),
        **s3_result,  # Include S3 results if upload was enabled
    }
```

**Tasks:**
- [ ] Add `upload_to_s3` and `s3_expires_in` parameters to `send_report_email()`
- [ ] Import S3Uploader from s3_uploader module
- [ ] Add `resolve_jsonl_path()` helper function
- [ ] Build JSON metadata and append to email body
- [ ] Return S3 results in response dict

### Phase 4: Add CLI Flag to email Command

**Files to modify:**
- `tools/xlsx_to_clickup.py` (modify existing CLI command)

```python
# Modify the existing email command to add --s3-upload flag

@app.command()
def email(
    project: Annotated[str, typer.Argument(help="Project name")],
    to: Annotated[List[str], typer.Option("--to", "-t", help="Recipient emails")],
    curr_date: Annotated[Optional[str], typer.Option("--curr", "-c")] = None,
    cc: Annotated[Optional[List[str]], typer.Option("--cc")] = None,
    subject: Annotated[Optional[str], typer.Option("--subject", "-s")] = None,
    body: Annotated[Optional[str], typer.Option("--body", "-b")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    dpi: Annotated[int, typer.Option("--dpi")] = 150,
    # NEW FLAGS:
    s3_upload: Annotated[bool, typer.Option("--s3-upload", help="Upload JSONL to S3 and include metadata")] = False,
    s3_expires_in: Annotated[int, typer.Option("--s3-expires-in", help="Presigned URL expiry in seconds")] = 604800,
) -> None:
    """Generate screenshot and send via Gmail.

    With --s3-upload: Also uploads JSONL to S3 and includes presigned URL + metadata in email.
    """
    # ... existing implementation, pass new flags to send_report_email() ...
```

**Tasks:**
- [ ] Add `--s3-upload` flag to `email` command
- [ ] Add `--s3-expires-in` flag for configurable expiration
- [ ] Pass new flags to `send_report_email()` function

### Phase 5: run_all.py Integration

**Files to modify:**
- `audiobee_bcbs_il/run_all.py` (example project)

```python
# Modify existing send_email_report task to enable S3 upload

elif task == "send_email_report":
    if config.PROJECT_NAME in SKIP_EMAIL_PROJECTS:
        print(f"⏭️ Skipping email report for {config.PROJECT_NAME}")
        continue

    print("Executing function 📋 send_report_email (with S3 upload)")
    result = send_report_email(
        project_name=config.PROJECT_NAME,
        curr_date=config.CURR_DATE,
        base_path=".",
        upload_to_s3=True,  # NEW: Enable S3 upload
    )
    if result.get("s3_key"):
        print(f"☁️ S3 Upload: {result.get('s3_key')}")
    print(f"📧 Email sent! Message ID: {result.get('message_id', 'N/A')}")
    print("✅ Success: send_email_report")
```

**Tasks:**
- [ ] Update `send_email_report` task to pass `upload_to_s3=True`
- [ ] Log S3 upload result if present
- [ ] No new task needed - reuse existing `send_email_report`

### Phase 6: Testing

**Files to create:**
- `tools/tests/test_s3_uploader.py`

```python
# tools/tests/test_s3_uploader.py
"""Tests for S3 upload functionality."""
import pytest
from unittest.mock import Mock, patch
from pathlib import Path

class TestS3Uploader:
    def test_upload_jsonl_success(self):
        """Test successful JSONL upload."""
        ...

    def test_generate_presigned_url(self):
        """Test presigned URL generation."""
        ...

    def test_missing_credentials(self):
        """Test error handling for missing AWS credentials."""
        ...

class TestTimestampParsing:
    def test_parse_valid_timestamps(self):
        """Test parsing valid XLSX timestamps."""
        ...

    def test_parse_missing_cells(self):
        """Test graceful handling of missing cells."""
        ...

    def test_calculate_duration(self):
        """Test run duration calculation."""
        ...

class TestSendReportEmailWithS3:
    def test_send_with_s3_upload(self):
        """Test send_report_email with upload_to_s3=True."""
        ...

    def test_send_without_s3_upload(self):
        """Test send_report_email with upload_to_s3=False (backward compatible)."""
        ...
```

**Tasks:**
- [ ] Write unit tests for S3Uploader class
- [ ] Write unit tests for timestamp parsing
- [ ] Write tests for enhanced send_report_email()
- [ ] Ensure backward compatibility when upload_to_s3=False

## Acceptance Criteria

### Functional Requirements
- [ ] JSONL file uploads to S3 with correct Content-Type (`application/x-ndjson`)
- [ ] Presigned URL generated with configurable expiration (default 7 days)
- [ ] Existing email from `xlsx_to_clickup.py` includes JSON metadata block when `upload_to_s3=True`
- [ ] Timestamps parsed correctly from XLSX cells A8/A9 (row 7 and 8, 0-indexed)
- [ ] Run duration calculated as seconds between first and last file
- [ ] Backward compatible - existing email functionality works when `upload_to_s3=False`

### Non-Functional Requirements
- [ ] S3 upload uses signature version 4 (s3v4)
- [ ] Retry logic with exponential backoff (5 attempts)
- [ ] Lazy loading of boto3 (like Gmail libraries)
- [ ] Graceful error handling for missing credentials/files

### CLI Requirements
- [ ] New `--s3-upload` flag on existing `email` command
- [ ] New `--s3-expires-in` flag for configurable expiration
- [ ] `--dry-run` validates files, credentials, and S3 access without uploading
- [ ] Clear error messages for common issues (missing env vars, files)

## Dependencies & Prerequisites

### New Dependencies
```
boto3>=1.35.0
botocore>=1.35.0
```

Add to `tools/requirements.txt`.

### Environment Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `S3_BUCKET_NAME` | Yes | Target S3 bucket name |
| `AWS_ACCESS_KEY_ID` | Conditional | AWS access key (or use ~/.aws/credentials) |
| `AWS_SECRET_ACCESS_KEY` | Conditional | AWS secret key (or use ~/.aws/credentials) |
| `AWS_DEFAULT_REGION` | No | AWS region (default: us-east-1) |

### AWS IAM Permissions
Minimum required permissions for the IAM user/role:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject"
            ],
            "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME/*"
        },
        {
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME"
        }
    ]
}
```

## Error Handling Strategy

### Partial Failure Behavior
- **Best-effort approach**: S3 upload failure does not block email send
- If `upload_to_s3=False`: Email sends normally (no S3 interaction)
- If `upload_to_s3=True` and S3 upload succeeds: Email includes presigned URL + JSON metadata
- If `upload_to_s3=True` and S3 upload fails: Log warning, send email WITHOUT S3 metadata
- In run_all.py: Log S3 upload status, continue regardless of S3 success

### Error Codes
| Error | Exit Code | Message |
|-------|-----------|---------|
| Missing S3_BUCKET_NAME | 1 | "S3_BUCKET_NAME environment variable not set" |
| AWS credentials invalid | 1 | "AWS credentials not found or invalid" |
| JSONL file not found | 1 | "JSONL file not found: {path}" |
| XLSX file not found | 1 | "XLSX file not found: {path}" |
| S3 upload failed | 2 | "S3 upload failed: {error}" |
| Email send failed | 2 | "Email send failed: {error}" |

## Success Metrics

- S3 upload completes within 60s for typical JSONL files (<100MB)
- Presigned URLs are valid and accessible for configured duration
- Email delivery success rate matches existing xlsx_to_clickup.py
- No regression in existing email/ClickUp functionality

## References & Research

### Internal References
- `tools/xlsx_to_clickup.py:392-526` - EmailClient OAuth implementation pattern
- `tools/drive_uploader.py:265-371` - Resumable upload with retry logic
- `tools/project_config.py:61-94` - Config loading via AST parsing
- `output_generator/report_generator.py:110-122` - Timestamp extraction pattern

### External References
- [boto3 Presigned URLs Guide](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-presigned-urls.html)
- [boto3 S3 Client Reference](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html)
- [AWS Presigned URL Best Practices](https://docs.aws.amazon.com/prescriptive-guidance/latest/presigned-url-best-practices/overview.html)

### Related Work
- Commit 0466cae: Added send_report_email() API for run_all.py integration
- Commit c269b2b: Enhanced drive_uploader with folder validation

#!/usr/bin/env python3
"""
Sample run_all.py showing how to integrate drive_uploader and xlsx_to_clickup.

This is a template you can copy into your project folder and customize.

Usage:
    # From project folder
    python run_all.py

    # Or from workspace root
    python audiobee_bcbs_il/run_all.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_DIR = Path(__file__).parent
WORKSPACE_ROOT = PROJECT_DIR.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

# ============================================================================
# Configuration - Customize these for your project
# ============================================================================

# Option 1: Import from config.py (for legacy audiobee projects)
# from config import PROJECT_NAME, CURR_DATE

# Option 2: Set directly (for HealthSparq or standalone use)
PROJECT_NAME = "audiobee_bcbs_il"  # Change this to your project name
CURR_DATE = "20260115"  # Change this to your run date


# ============================================================================
# Task Configuration
# ============================================================================

# Scripts to run before post-processing (customize for your project)
SCRAPER_SCRIPTS = [
    # "index_0.py",
    # "index_1.py",
    # "3_map_json_to_ideon_format.py",
]

# Post-processing options
COMPRESS_TO_7Z = True
UPLOAD_TO_DRIVE = True
SEND_EMAIL_REPORT = True
UPLOAD_JSONL_TO_S3 = True  # Include S3 upload with presigned URL in email

# Email recipients (uses defaults from xlsx_to_clickup if not specified)
EMAIL_RECIPIENTS = None  # Uses DEFAULT_RECIPIENTS: ["operations@audiobee.ai", "dikson@audiobee.ai"]
# EMAIL_RECIPIENTS = ["custom@example.com"]  # Or specify custom recipients


# ============================================================================
# Helper Functions
# ============================================================================

def run_script(script_name: str) -> None:
    """Run a Python script and raise on failure."""
    print(f"\n{'='*60}")
    print(f"Running: {script_name}")
    print('='*60)

    result = subprocess.run(
        [sys.executable, script_name],
        cwd=PROJECT_DIR,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Script failed: {script_name}")

    print(f"Completed: {script_name}")


def compress_folder() -> Path:
    """Compress the date folder to 7z archive."""
    print(f"\n{'='*60}")
    print(f"Compressing {CURR_DATE} folder to 7z")
    print('='*60)

    date_folder = PROJECT_DIR / CURR_DATE
    archive_path = date_folder / f"{CURR_DATE}.7z"

    if archive_path.exists():
        print(f"Archive already exists: {archive_path}")
        return archive_path

    # Use 7z command to compress
    result = subprocess.run(
        ["7z", "a", "-mx=5", str(archive_path), str(date_folder / "*")],
        cwd=PROJECT_DIR,
    )

    if result.returncode != 0:
        raise RuntimeError(f"7z compression failed")

    size_mb = archive_path.stat().st_size / 1024 / 1024
    print(f"Created archive: {archive_path} ({size_mb:.1f} MB)")
    return archive_path


def upload_to_drive() -> dict:
    """Upload 7z archive to Google Drive."""
    print(f"\n{'='*60}")
    print(f"Uploading to Google Drive")
    print('='*60)

    from tools.drive_uploader import upload_archive

    result = upload_archive(
        project_name=PROJECT_NAME,
        curr_date=CURR_DATE,
        base_path=PROJECT_DIR,
        use_oauth=True,  # Use OAuth for personal Drive folders
    )

    print(f"Upload successful!")
    print(f"  File ID: {result.get('id')}")
    print(f"  View: {result.get('webViewLink')}")

    return result


def send_email_report() -> dict:
    """Send email report with screenshot and optional S3 upload."""
    print(f"\n{'='*60}")
    print(f"Sending email report")
    print('='*60)

    from tools.xlsx_to_clickup import send_report_email

    result = send_report_email(
        project_name=PROJECT_NAME,
        curr_date=CURR_DATE,
        base_path=PROJECT_DIR,
        to=EMAIL_RECIPIENTS,  # None uses defaults
        upload_to_s3=UPLOAD_JSONL_TO_S3,
    )

    print(f"Email sent!")
    print(f"  Message ID: {result.get('message_id')}")

    if result.get("s3_key"):
        print(f"  S3 Key: {result.get('s3_key')}")
        print(f"  Presigned URL: {result.get('presigned_url', '')[:80]}...")

    return result


# ============================================================================
# Main
# ============================================================================

def main():
    """Run the complete pipeline."""
    print(f"\n{'#'*60}")
    print(f"# Project: {PROJECT_NAME}")
    print(f"# Date: {CURR_DATE}")
    print(f"{'#'*60}")

    results = {}

    try:
        # Step 1: Run scraper scripts
        for script in SCRAPER_SCRIPTS:
            run_script(script)

        # Step 2: Compress to 7z
        if COMPRESS_TO_7Z:
            results["archive"] = compress_folder()

        # Step 3: Upload to Google Drive
        if UPLOAD_TO_DRIVE:
            results["drive"] = upload_to_drive()

        # Step 4: Send email report
        if SEND_EMAIL_REPORT:
            results["email"] = send_email_report()

        # Summary
        print(f"\n{'#'*60}")
        print(f"# Pipeline Complete!")
        print(f"{'#'*60}")

        if "drive" in results:
            print(f"Drive: {results['drive'].get('webViewLink')}")
        if "email" in results:
            print(f"Email: {results['email'].get('message_id')}")

        return 0

    except Exception as e:
        print(f"\n{'!'*60}")
        print(f"! Pipeline failed: {e}")
        print(f"{'!'*60}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

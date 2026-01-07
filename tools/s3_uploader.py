#!/usr/bin/env python3
"""S3 upload functionality with presigned URL generation.

This module provides S3 upload capabilities for JSONL files.
Used by xlsx_to_clickup.py for enhanced email reports.

Configuration (in order of precedence):
    1. tools/aws_credentials.json (recommended)
    2. Environment variables:
       - S3_BUCKET_NAME: Target S3 bucket
       - AWS_ACCESS_KEY_ID: AWS access key
       - AWS_SECRET_ACCESS_KEY: AWS secret key
       - AWS_DEFAULT_REGION: AWS region (default: us-east-1)
    3. ~/.aws/credentials (boto3 default)

Setup:
    1. Copy tools/aws_credentials.example.json to tools/aws_credentials.json
    2. Fill in your AWS credentials and bucket name
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

try:
    from core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


# =============================================================================
# Credentials Loading
# =============================================================================

# Path to credentials file (relative to this file)
CREDENTIALS_FILE = Path(__file__).parent / "aws_credentials.json"


def _load_credentials_file() -> dict | None:
    """Load AWS credentials from JSON file if it exists.

    Returns:
        Dict with credentials or None if file doesn't exist
    """
    if not CREDENTIALS_FILE.exists():
        return None

    try:
        with open(CREDENTIALS_FILE) as f:
            creds = json.load(f)
        logger.debug(f"Loaded AWS credentials from {CREDENTIALS_FILE}")
        return creds
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to load {CREDENTIALS_FILE}: {e}")
        return None


# =============================================================================
# S3 Configuration
# =============================================================================

@dataclass
class S3Config:
    """S3 configuration from credentials file or environment variables."""
    bucket_name: str
    region: str = "us-east-1"
    presigned_expiry: int = 604800  # 7 days
    access_key_id: str | None = None
    secret_access_key: str | None = None

    @classmethod
    def from_env(cls) -> S3Config:
        """Load S3 configuration from credentials file or environment.

        Precedence:
            1. tools/aws_credentials.json
            2. Environment variables
            3. ~/.aws/credentials (handled by boto3)
        """
        # Try credentials file first
        creds = _load_credentials_file()

        if creds:
            bucket = creds.get("bucket_name")
            if not bucket:
                raise ValueError(
                    "bucket_name not set in aws_credentials.json.\n"
                    "Add it to tools/aws_credentials.json"
                )
            return cls(
                bucket_name=bucket,
                region=creds.get("region", "us-east-1"),
                access_key_id=creds.get("aws_access_key_id"),
                secret_access_key=creds.get("aws_secret_access_key"),
            )

        # Fall back to environment variables
        bucket = os.environ.get("S3_BUCKET_NAME")
        if not bucket:
            raise ValueError(
                "S3 not configured. Either:\n"
                "  1. Copy tools/aws_credentials.example.json to tools/aws_credentials.json\n"
                "  2. Or set S3_BUCKET_NAME environment variable"
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
            # Use credentials from config if provided, otherwise boto3 default chain
            client_kwargs = {
                's3': None,
                'region_name': self.config.region,
                'config': boto_config,
            }
            if self.config.access_key_id and self.config.secret_access_key:
                client_kwargs['aws_access_key_id'] = self.config.access_key_id
                client_kwargs['aws_secret_access_key'] = self.config.secret_access_key
                logger.debug("Using credentials from aws_credentials.json")

            self._client = boto3_client.client(
                's3',
                region_name=self.config.region,
                config=boto_config,
                aws_access_key_id=self.config.access_key_id,
                aws_secret_access_key=self.config.secret_access_key,
            )
        return self._client

    def upload_jsonl(
        self,
        local_path: Path,
        project_name: str,
        curr_date: str,
    ) -> str:
        """Upload JSONL file to S3.

        Args:
            local_path: Path to local JSONL file
            project_name: Project name for S3 key
            curr_date: Date string (YYYYMMDD) for S3 key

        Returns:
            S3 object key

        Raises:
            FileNotFoundError: If local_path doesn't exist
            botocore.exceptions.ClientError: If upload fails
        """
        local_path = Path(local_path)
        if not local_path.exists():
            raise FileNotFoundError(f"JSONL file not found: {local_path}")

        object_key = f"{project_name}-{curr_date}.jsonl"

        logger.info(f"Uploading {local_path} to s3://{self.config.bucket_name}/{object_key}")

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
        expiration: int | None = None,
    ) -> str:
        """Generate presigned URL for S3 object.

        Args:
            object_key: S3 object key
            expiration: URL expiration in seconds (default: config.presigned_expiry)

        Returns:
            Presigned URL string
        """
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

    def upload_and_get_url(
        self,
        local_path: Path,
        project_name: str,
        curr_date: str,
        expiration: int | None = None,
    ) -> tuple[str, str]:
        """Upload JSONL and generate presigned URL in one call.

        Args:
            local_path: Path to local JSONL file
            project_name: Project name for S3 key
            curr_date: Date string (YYYYMMDD) for S3 key
            expiration: URL expiration in seconds (default: config.presigned_expiry)

        Returns:
            Tuple of (object_key, presigned_url)
        """
        object_key = self.upload_jsonl(local_path, project_name, curr_date)
        presigned_url = self.generate_presigned_url(object_key, expiration)
        return object_key, presigned_url

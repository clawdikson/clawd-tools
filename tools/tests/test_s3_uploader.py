#!/usr/bin/env python3
"""Tests for S3 upload functionality."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest


class TestS3Config:
    """Tests for S3Config dataclass."""

    def test_from_env_success(self):
        """Test loading config from environment variables."""
        from tools.s3_uploader import S3Config

        with patch.dict(os.environ, {
            "S3_BUCKET_NAME": "test-bucket",
            "AWS_DEFAULT_REGION": "us-west-2"
        }):
            config = S3Config.from_env()
            assert config.bucket_name == "test-bucket"
            assert config.region == "us-west-2"
            assert config.presigned_expiry == 604800  # Default 7 days

    def test_from_env_default_region(self):
        """Test default region when not specified."""
        from tools.s3_uploader import S3Config

        with patch.dict(os.environ, {"S3_BUCKET_NAME": "test-bucket"}, clear=False):
            # Remove AWS_DEFAULT_REGION if present
            env_copy = os.environ.copy()
            env_copy.pop("AWS_DEFAULT_REGION", None)
            with patch.dict(os.environ, env_copy, clear=True):
                with patch.dict(os.environ, {"S3_BUCKET_NAME": "test-bucket"}):
                    config = S3Config.from_env()
                    assert config.region == "us-east-1"

    def test_from_env_missing_bucket(self):
        """Test error when S3 not configured."""
        from tools.s3_uploader import S3Config

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="S3 not configured"):
                S3Config.from_env()


class TestS3Uploader:
    """Tests for S3Uploader class."""

    @pytest.fixture
    def mock_boto3(self):
        """Mock boto3 for testing."""
        with patch("tools.s3_uploader._boto3_loaded", False):
            with patch("tools.s3_uploader.boto3_client", None):
                with patch("tools.s3_uploader.botocore_config", None):
                    # Set up fresh boto3 mock
                    mock_boto = MagicMock()
                    mock_config = MagicMock()

                    with patch.dict("sys.modules", {"boto3": mock_boto, "botocore.config": MagicMock(Config=mock_config)}):
                        yield mock_boto, mock_config

    @pytest.fixture
    def s3_config(self):
        """Create test S3 config."""
        from tools.s3_uploader import S3Config
        return S3Config(bucket_name="test-bucket", region="us-east-1")

    @pytest.fixture
    def temp_jsonl(self):
        """Create temporary JSONL file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"npi": "1234567890", "name": "Test Provider"}\n')
            f.write('{"npi": "0987654321", "name": "Another Provider"}\n')
            temp_path = Path(f.name)
        yield temp_path
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    def test_upload_jsonl_file_not_found(self, s3_config):
        """Test error when JSONL file doesn't exist."""
        from tools.s3_uploader import S3Uploader

        uploader = S3Uploader(s3_config)
        with pytest.raises(FileNotFoundError, match="JSONL file not found"):
            uploader.upload_jsonl(Path("/nonexistent/file.jsonl"), "test_project", "20251231")

    def test_upload_jsonl_object_key_format(self, s3_config, temp_jsonl):
        """Test S3 object key follows expected format."""
        from tools.s3_uploader import S3Uploader

        # Mock the boto3 client
        with patch.object(S3Uploader, "client", new_callable=lambda: MagicMock()) as mock_client:
            uploader = S3Uploader(s3_config)
            uploader._client = mock_client

            object_key = uploader.upload_jsonl(temp_jsonl, "audiobee_bcbs_il", "20251231")

            assert object_key == "audiobee_bcbs_il/20251231/processed/audiobee_bcbs_il-20251231.jsonl"
            mock_client.upload_file.assert_called_once()

            # Verify Content-Type header
            call_args = mock_client.upload_file.call_args
            assert call_args[1]["ExtraArgs"]["ContentType"] == "application/x-ndjson"

    def test_generate_presigned_url(self, s3_config):
        """Test presigned URL generation."""
        from tools.s3_uploader import S3Uploader

        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = "https://test-bucket.s3.amazonaws.com/test/key?signature=xyz"

        with patch.object(S3Uploader, "client", new_callable=lambda: mock_client):
            uploader = S3Uploader(s3_config)
            uploader._client = mock_client

            url = uploader.generate_presigned_url("test/object/key.jsonl")

            assert "s3.amazonaws.com" in url
            mock_client.generate_presigned_url.assert_called_once_with(
                'get_object',
                Params={'Bucket': 'test-bucket', 'Key': 'test/object/key.jsonl'},
                ExpiresIn=604800
            )

    def test_generate_presigned_url_custom_expiry(self, s3_config):
        """Test presigned URL with custom expiration."""
        from tools.s3_uploader import S3Uploader

        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = "https://test.s3.amazonaws.com/key"

        with patch.object(S3Uploader, "client", new_callable=lambda: mock_client):
            uploader = S3Uploader(s3_config)
            uploader._client = mock_client

            uploader.generate_presigned_url("key", expiration=3600)

            mock_client.generate_presigned_url.assert_called_once_with(
                'get_object',
                Params={'Bucket': 'test-bucket', 'Key': 'key'},
                ExpiresIn=3600
            )

    def test_upload_and_get_url(self, s3_config, temp_jsonl):
        """Test combined upload and URL generation."""
        from tools.s3_uploader import S3Uploader

        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = "https://presigned.url"

        with patch.object(S3Uploader, "client", new_callable=lambda: mock_client):
            uploader = S3Uploader(s3_config)
            uploader._client = mock_client

            key, url = uploader.upload_and_get_url(temp_jsonl, "test_project", "20251231")

            assert key == "test_project/20251231/processed/test_project-20251231.jsonl"
            assert url == "https://presigned.url"


class TestTimestampParsing:
    """Tests for parse_run_timestamps function."""

    @pytest.fixture
    def mock_xlsx(self):
        """Create mock XLSX workbook."""
        mock_wb = MagicMock()
        mock_ws = MagicMock()
        mock_wb.active = mock_ws
        mock_wb.close = MagicMock()
        return mock_wb, mock_ws

    def test_parse_valid_timestamps(self, mock_xlsx):
        """Test parsing valid timestamps from XLSX."""
        from tools.xlsx_to_clickup import parse_run_timestamps

        mock_wb, mock_ws = mock_xlsx
        # Set up cell mocks properly
        mock_cell_a8 = MagicMock()
        mock_cell_a8.value = "First File Created = 25/12/2025 10:30:00"
        mock_cell_a9 = MagicMock()
        mock_cell_a9.value = "Last File Created = 25/12/2025 12:45:30"
        mock_ws.__getitem__ = lambda self, key: mock_cell_a8 if key == 'A8' else mock_cell_a9

        with patch("openpyxl.load_workbook", return_value=mock_wb):
            result = parse_run_timestamps(Path("test.xlsx"))

            assert result["run_ended_str"] == "25/12/2025 12:45:30"
            assert result["run_duration_seconds"] == 8130  # 2h 15m 30s

    def test_parse_missing_cells(self, mock_xlsx):
        """Test graceful handling of missing cells."""
        from tools.xlsx_to_clickup import parse_run_timestamps

        mock_wb, mock_ws = mock_xlsx
        # Set up cell mocks with None values
        mock_cell_a8 = MagicMock()
        mock_cell_a8.value = None
        mock_cell_a9 = MagicMock()
        mock_cell_a9.value = None
        mock_ws.__getitem__ = lambda self, key: mock_cell_a8 if key == 'A8' else mock_cell_a9

        with patch("openpyxl.load_workbook", return_value=mock_wb):
            result = parse_run_timestamps(Path("test.xlsx"))

            assert result["first_file_created"] is None
            assert result["last_file_created"] is None
            assert result["run_duration_seconds"] == 0
            assert result["run_ended_str"] == ""

    def test_parse_malformed_timestamps(self, mock_xlsx):
        """Test handling of malformed timestamp strings."""
        from tools.xlsx_to_clickup import parse_run_timestamps

        mock_wb, mock_ws = mock_xlsx
        # Set up cell mocks with malformed values
        mock_cell_a8 = MagicMock()
        mock_cell_a8.value = "Invalid format"
        mock_cell_a9 = MagicMock()
        mock_cell_a9.value = "Also invalid"
        mock_ws.__getitem__ = lambda self, key: mock_cell_a8 if key == 'A8' else mock_cell_a9

        with patch("openpyxl.load_workbook", return_value=mock_wb):
            result = parse_run_timestamps(Path("test.xlsx"))

            assert result["first_file_created"] is None
            assert result["last_file_created"] is None
            assert result["run_duration_seconds"] == 0


class TestSendReportEmailWithS3:
    """Tests for send_report_email with S3 upload."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies."""
        with patch("tools.xlsx_to_clickup.resolve_xlsx_path") as mock_xlsx:
            with patch("tools.xlsx_to_clickup.resolve_jsonl_path") as mock_jsonl:
                with patch("tools.xlsx_to_clickup.parse_run_timestamps") as mock_timestamps:
                    with patch("tools.xlsx_to_clickup.generate_screenshot") as mock_screenshot:
                        with patch("tools.xlsx_to_clickup.EmailClient") as mock_email:
                            mock_xlsx.return_value = Path("/fake/path/report.xlsx")
                            mock_jsonl.return_value = Path("/fake/path/data.jsonl")
                            mock_timestamps.return_value = {
                                "first_file_created": None,
                                "last_file_created": None,
                                "run_duration_seconds": 3600,
                                "run_ended_str": "25/12/2025 12:00:00"
                            }
                            mock_email_instance = MagicMock()
                            mock_email_instance.send_email.return_value = {"id": "test-message-id"}
                            mock_email.return_value = mock_email_instance

                            yield {
                                "xlsx": mock_xlsx,
                                "jsonl": mock_jsonl,
                                "timestamps": mock_timestamps,
                                "screenshot": mock_screenshot,
                                "email": mock_email_instance
                            }

    def test_send_without_s3_upload(self, mock_dependencies):
        """Test send_report_email with upload_to_s3=False (backward compatible)."""
        from tools.xlsx_to_clickup import send_report_email

        result = send_report_email(
            project_name="test_project",
            curr_date="20251231",
            to=["test@example.com"],
            upload_to_s3=False,
        )

        assert result["message_id"] == "test-message-id"
        assert "s3_key" not in result
        assert "presigned_url" not in result

    def test_send_with_s3_upload_success(self, mock_dependencies):
        """Test send_report_email with successful S3 upload."""
        from tools.xlsx_to_clickup import send_report_email

        mock_uploader = MagicMock()
        mock_uploader.upload_and_get_url.return_value = (
            "test_project/20251231/processed/test_project-20251231.jsonl",
            "https://presigned.url"
        )

        with patch("tools.s3_uploader.S3Config") as mock_config:
            with patch("tools.s3_uploader.S3Uploader", return_value=mock_uploader):
                mock_config.from_env.return_value = MagicMock(presigned_expiry=604800)

                result = send_report_email(
                    project_name="test_project",
                    curr_date="20251231",
                    to=["test@example.com"],
                    upload_to_s3=True,
                )

                assert result["s3_key"] == "test_project/20251231/processed/test_project-20251231.jsonl"
                assert result["presigned_url"] == "https://presigned.url"

    def test_send_with_s3_upload_failure_continues(self, mock_dependencies):
        """Test that S3 upload failure doesn't block email."""
        from tools.xlsx_to_clickup import send_report_email

        with patch("tools.s3_uploader.S3Config") as mock_config:
            mock_config.from_env.side_effect = ValueError("S3_BUCKET_NAME not set")

            # Should not raise, just log warning and send email without S3
            result = send_report_email(
                project_name="test_project",
                curr_date="20251231",
                to=["test@example.com"],
                upload_to_s3=True,
            )

            assert result["message_id"] == "test-message-id"
            assert "s3_key" not in result

    def test_dry_run_with_s3(self, mock_dependencies):
        """Test dry run mode with S3 upload enabled."""
        from tools.xlsx_to_clickup import send_report_email

        mock_uploader = MagicMock()
        mock_uploader.upload_and_get_url.return_value = ("key", "https://url")

        with patch("tools.s3_uploader.S3Config") as mock_config:
            with patch("tools.s3_uploader.S3Uploader", return_value=mock_uploader):
                mock_config.from_env.return_value = MagicMock(presigned_expiry=604800)

                result = send_report_email(
                    project_name="test_project",
                    curr_date="20251231",
                    to=["test@example.com"],
                    upload_to_s3=True,
                    dry_run=True,
                )

                assert result["message_id"] == "dry-run"
                # S3 upload should still happen in dry-run to validate
                assert "s3_key" in result


class TestResolveJsonlPath:
    """Tests for resolve_jsonl_path function."""

    def test_resolve_existing_file(self, tmp_path):
        """Test resolving existing JSONL file."""
        from tools.xlsx_to_clickup import resolve_jsonl_path

        # Create directory structure
        processed_dir = tmp_path / "20251231" / "processed"
        processed_dir.mkdir(parents=True)

        # Create JSONL file
        jsonl_file = processed_dir / "test_project-20251231.jsonl"
        jsonl_file.write_text('{"npi": "1234567890"}\n')

        result = resolve_jsonl_path("test_project", "20251231", tmp_path)
        assert result == jsonl_file

    def test_resolve_missing_file(self, tmp_path):
        """Test error when JSONL file doesn't exist."""
        from tools.xlsx_to_clickup import resolve_jsonl_path

        # Create directory structure but no file
        processed_dir = tmp_path / "20251231" / "processed"
        processed_dir.mkdir(parents=True)

        with pytest.raises(FileNotFoundError, match="JSONL file not found"):
            resolve_jsonl_path("test_project", "20251231", tmp_path)

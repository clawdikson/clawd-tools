"""Tests for xlsx_to_clickup CLI tool."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest

# Import from tools directory
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from xlsx_to_clickup import (
    ClickUpClient,
    EmailClient,
    generate_screenshot,
    resolve_xlsx_path,
)


class TestResolveXlsxPath:
    """Tests for XLSX file resolution."""

    def test_finds_primary_file(self, tmp_path):
        """Should find primary state_with_surrounding file."""
        project = tmp_path / "test_project"
        processed = project / "20251227" / "processed"
        processed.mkdir(parents=True)

        primary = (
            processed / "test_project-20251227-state_with_surrounding-counts.xlsx"
        )
        primary.touch()

        result = resolve_xlsx_path("test_project", "20251227", project)
        assert result == primary

    def test_falls_back_to_state_only(self, tmp_path):
        """Should fall back to state_only when primary doesn't exist."""
        project = tmp_path / "test_project"
        processed = project / "20251227" / "processed"
        processed.mkdir(parents=True)

        fallback = processed / "test_project-20251227-state_only-counts.xlsx"
        fallback.touch()

        result = resolve_xlsx_path("test_project", "20251227", project)
        assert result == fallback

    def test_prefers_primary_over_fallback(self, tmp_path):
        """Should prefer primary when both exist."""
        project = tmp_path / "test_project"
        processed = project / "20251227" / "processed"
        processed.mkdir(parents=True)

        primary = (
            processed / "test_project-20251227-state_with_surrounding-counts.xlsx"
        )
        fallback = processed / "test_project-20251227-state_only-counts.xlsx"
        primary.touch()
        fallback.touch()

        result = resolve_xlsx_path("test_project", "20251227", project)
        assert result == primary

    def test_raises_when_neither_exists(self, tmp_path):
        """Should raise FileNotFoundError when no matching file exists."""
        project = tmp_path / "test_project"
        processed = project / "20251227" / "processed"
        processed.mkdir(parents=True)

        with pytest.raises(FileNotFoundError, match="No state counts file found"):
            resolve_xlsx_path("test_project", "20251227", project)

    def test_raises_when_processed_dir_missing(self, tmp_path):
        """Should raise FileNotFoundError when processed directory doesn't exist."""
        project = tmp_path / "test_project"
        project.mkdir()

        with pytest.raises(FileNotFoundError, match="Processed directory not found"):
            resolve_xlsx_path("test_project", "20251227", project)


class TestGenerateScreenshot:
    """Tests for screenshot generation."""

    @pytest.fixture
    def sample_xlsx(self, tmp_path):
        """Create a sample XLSX file for testing (compact summary format)."""
        xlsx_path = tmp_path / "test.xlsx"
        df = pd.DataFrame(
            {
                "Description": [
                    "In-scope States:",
                    "In-Scope Providers (Unique):",
                    "Out-of-Scope Provider (Unique):",
                    "In-Scope Providers (Non-Unique):",
                    "Out-of-Scope Providers (Non-Unique):",
                ],
                "Data": [
                    "IL, TX, CA",
                    "100 (100.0%)",
                    "0 (0.0%)",
                    "200 (95.2%)",
                    "10 (4.8%)",
                ],
            }
        )
        df.to_excel(xlsx_path, index=False)
        return xlsx_path

    def test_generates_png(self, sample_xlsx, tmp_path):
        """Should generate a valid PNG file."""
        output_path = tmp_path / "output.png"
        result = generate_screenshot(sample_xlsx, output_path)

        assert result.exists()
        assert result.suffix == ".png"
        # Verify it's actually a PNG (check magic bytes)
        with open(result, "rb") as f:
            magic = f.read(8)
            assert magic[:4] == b"\x89PNG"

    def test_uses_temp_file_when_no_output_specified(self, sample_xlsx):
        """Should create a temp file when no output path provided."""
        result = generate_screenshot(sample_xlsx)

        try:
            assert result.exists()
            assert result.suffix == ".png"
        finally:
            # Cleanup temp file
            if result.exists():
                result.unlink()

    def test_raises_on_empty_file(self, tmp_path):
        """Should raise ValueError when Excel file is empty."""
        xlsx_path = tmp_path / "empty.xlsx"
        df = pd.DataFrame()
        df.to_excel(xlsx_path, index=False)

        with pytest.raises(ValueError, match="empty"):
            generate_screenshot(xlsx_path)

    def test_respects_dpi_setting(self, sample_xlsx, tmp_path):
        """Should generate larger file with higher DPI."""
        output_low = tmp_path / "low.png"
        output_high = tmp_path / "high.png"

        generate_screenshot(sample_xlsx, output_low, dpi=72)
        generate_screenshot(sample_xlsx, output_high, dpi=300)

        # Higher DPI should produce larger file
        assert output_high.stat().st_size > output_low.stat().st_size


class TestClickUpClient:
    """Tests for ClickUp API client."""

    @patch("xlsx_to_clickup.requests.request")
    def test_upload_attachment(self, mock_request):
        """Should upload attachment with correct parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "att123", "url": "https://..."}
        mock_request.return_value = mock_response

        client = ClickUpClient("pk_test_token")

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake png data")
            file_path = Path(f.name)

        try:
            result = client.upload_attachment("task123", file_path)

            assert result["id"] == "att123"

            # Verify request was made correctly
            call_args = mock_request.call_args
            # requests.request(method, url, **kwargs) - method and url are positional
            assert call_args.args[0] == "POST"
            assert "task123" in call_args.args[1]
            assert "Authorization" in call_args.kwargs["headers"]
            assert "files" in call_args.kwargs
        finally:
            file_path.unlink()

    @patch("xlsx_to_clickup.requests.request")
    def test_add_comment(self, mock_request):
        """Should add comment with correct parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "c123"}
        mock_request.return_value = mock_response

        client = ClickUpClient("pk_test_token")
        result = client.add_comment("task123", "Test comment")

        assert result["id"] == "c123"

        # Verify request
        call_args = mock_request.call_args
        assert call_args.kwargs["json"]["comment_text"] == "Test comment"

    @patch("xlsx_to_clickup.requests.request")
    @patch("xlsx_to_clickup.time.sleep")
    def test_retry_on_rate_limit(self, mock_sleep, mock_request):
        """Should retry with exponential backoff on 429."""
        mock_response_429 = Mock()
        mock_response_429.status_code = 429

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"id": "c123"}

        mock_request.side_effect = [mock_response_429, mock_response_200]

        client = ClickUpClient("pk_test_token")
        result = client.add_comment("task123", "Test comment")

        assert result["id"] == "c123"
        assert mock_request.call_count == 2
        mock_sleep.assert_called_once()

    @patch("xlsx_to_clickup.requests.request")
    @patch("xlsx_to_clickup.time.sleep")
    def test_max_retries_exceeded(self, mock_sleep, mock_request):
        """Should raise exception after max retries."""
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_request.return_value = mock_response_429

        client = ClickUpClient("pk_test_token", max_retries=3)

        with pytest.raises(Exception, match="Max retries"):
            client.add_comment("task123", "Test comment")

        assert mock_request.call_count == 3

    @patch("xlsx_to_clickup.requests.request")
    def test_custom_filename(self, mock_request):
        """Should use custom filename when provided."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "att123"}
        mock_request.return_value = mock_response

        client = ClickUpClient("pk_test_token")

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake png data")
            file_path = Path(f.name)

        try:
            client.upload_attachment(
                "task123", file_path, filename="custom-report.png"
            )

            # Verify custom filename was used
            call_args = mock_request.call_args
            files = call_args.kwargs["files"]
            assert files["attachment"][0] == "custom-report.png"
        finally:
            file_path.unlink()


class TestEmailClient:
    """Tests for Gmail OAuth Email client."""

    @patch("xlsx_to_clickup.EmailClient._get_credentials")
    @patch("xlsx_to_clickup.gmail_build")
    @patch("xlsx_to_clickup._load_gmail_libs")
    def test_send_email_basic(self, mock_load_libs, mock_build, mock_get_creds):
        """Should send email via Gmail API."""
        # Setup mocks
        mock_service = Mock()
        mock_messages = Mock()
        mock_send = Mock()
        mock_send.execute.return_value = {"id": "msg123", "threadId": "thread123"}
        mock_messages.send.return_value = mock_send
        mock_service.users.return_value.messages.return_value = mock_messages
        mock_build.return_value = mock_service
        mock_get_creds.return_value = Mock()

        client = EmailClient()
        result = client.send_email(
            to=["recipient@test.com"],
            subject="Test Subject",
            body="Test body",
        )

        # Verify Gmail API was called
        assert result["id"] == "msg123"
        mock_messages.send.assert_called_once()

        # Verify the message structure
        call_args = mock_messages.send.call_args
        assert call_args.kwargs["userId"] == "me"
        assert "raw" in call_args.kwargs["body"]

    @patch("xlsx_to_clickup.EmailClient._get_credentials")
    @patch("xlsx_to_clickup.gmail_build")
    @patch("xlsx_to_clickup._load_gmail_libs")
    def test_send_email_with_attachment(self, mock_load_libs, mock_build, mock_get_creds):
        """Should include attachment in email."""
        # Setup mocks
        mock_service = Mock()
        mock_messages = Mock()
        mock_send = Mock()
        mock_send.execute.return_value = {"id": "msg123"}
        mock_messages.send.return_value = mock_send
        mock_service.users.return_value.messages.return_value = mock_messages
        mock_build.return_value = mock_service
        mock_get_creds.return_value = Mock()

        client = EmailClient()

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake image data")
            file_path = Path(f.name)

        try:
            result = client.send_email(
                to=["recipient@test.com"],
                subject="Test Subject",
                body="Test body",
                attachment_path=file_path,
                attachment_name="report.png",
            )

            # Verify email was sent
            assert result["id"] == "msg123"
            mock_messages.send.assert_called_once()

            # Verify attachment is in the encoded message
            call_args = mock_messages.send.call_args
            raw_message = call_args.kwargs["body"]["raw"]
            # Decode to check content
            import base64
            decoded = base64.urlsafe_b64decode(raw_message).decode("utf-8", errors="ignore")
            assert "report.png" in decoded
        finally:
            file_path.unlink()

    @patch("xlsx_to_clickup.EmailClient._get_credentials")
    @patch("xlsx_to_clickup.gmail_build")
    @patch("xlsx_to_clickup._load_gmail_libs")
    def test_send_email_with_cc(self, mock_load_libs, mock_build, mock_get_creds):
        """Should include CC in email headers."""
        # Setup mocks
        mock_service = Mock()
        mock_messages = Mock()
        mock_send = Mock()
        mock_send.execute.return_value = {"id": "msg123"}
        mock_messages.send.return_value = mock_send
        mock_service.users.return_value.messages.return_value = mock_messages
        mock_build.return_value = mock_service
        mock_get_creds.return_value = Mock()

        client = EmailClient()
        result = client.send_email(
            to=["recipient@test.com"],
            subject="Test Subject",
            body="Test body",
            cc=["cc1@test.com", "cc2@test.com"],
        )

        # Verify email was sent
        assert result["id"] == "msg123"

        # Verify CC is in the encoded message
        call_args = mock_messages.send.call_args
        raw_message = call_args.kwargs["body"]["raw"]
        import base64
        decoded = base64.urlsafe_b64decode(raw_message).decode("utf-8", errors="ignore")
        assert "cc1@test.com" in decoded
        assert "cc2@test.com" in decoded

    @patch("xlsx_to_clickup.EmailClient._get_credentials")
    @patch("xlsx_to_clickup.gmail_build")
    @patch("xlsx_to_clickup._load_gmail_libs")
    def test_send_email_multiple_recipients(self, mock_load_libs, mock_build, mock_get_creds):
        """Should send to multiple TO recipients."""
        # Setup mocks
        mock_service = Mock()
        mock_messages = Mock()
        mock_send = Mock()
        mock_send.execute.return_value = {"id": "msg123"}
        mock_messages.send.return_value = mock_send
        mock_service.users.return_value.messages.return_value = mock_messages
        mock_build.return_value = mock_service
        mock_get_creds.return_value = Mock()

        client = EmailClient()
        result = client.send_email(
            to=["r1@test.com", "r2@test.com"],
            subject="Test Subject",
            body="Test body",
        )

        # Verify email was sent
        assert result["id"] == "msg123"

        # Verify recipients in the encoded message
        call_args = mock_messages.send.call_args
        raw_message = call_args.kwargs["body"]["raw"]
        import base64
        decoded = base64.urlsafe_b64decode(raw_message).decode("utf-8", errors="ignore")
        assert "r1@test.com" in decoded
        assert "r2@test.com" in decoded

"""Integration tests for Google Drive upload (requires credentials)."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

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


class TestDriveUploaderUnit:
    """Unit tests for DriveUploader class (no credentials needed)."""

    def test_load_folder_mapping(self, tmp_path):
        """Should load folder mapping from JSON file."""
        from tools.drive_uploader import DriveUploader

        # Create mapping file
        mapping_file = tmp_path / "mapping.json"
        mapping_file.write_text('{"projects": {"test_project": "folder123"}}')

        # Create fake credentials file (won't be used in this test)
        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{}')

        uploader = DriveUploader(
            credentials_path=str(creds_file),
            mapping_path=str(mapping_file),
        )

        mapping = uploader.load_folder_mapping()
        assert mapping == {"test_project": "folder123"}

    def test_get_folder_id_success(self, tmp_path):
        """Should return folder ID for mapped project."""
        from tools.drive_uploader import DriveUploader

        # Create mapping file
        mapping_file = tmp_path / "mapping.json"
        mapping_file.write_text('{"projects": {"test_project": "folder123"}}')

        # Create fake credentials file
        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{}')

        uploader = DriveUploader(
            credentials_path=str(creds_file),
            mapping_path=str(mapping_file),
        )

        folder_id = uploader.get_folder_id("test_project")
        assert folder_id == "folder123"

    def test_get_folder_id_missing_project(self, tmp_path):
        """Should raise KeyError for unmapped project."""
        from tools.drive_uploader import DriveUploader

        # Create mapping file with one project
        mapping_file = tmp_path / "mapping.json"
        mapping_file.write_text('{"projects": {"other_project": "folder456"}}')

        # Create fake credentials file
        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{}')

        uploader = DriveUploader(
            credentials_path=str(creds_file),
            mapping_path=str(mapping_file),
        )

        with pytest.raises(KeyError, match="No Drive folder mapping"):
            uploader.get_folder_id("nonexistent_project")

    def test_missing_mapping_file(self, tmp_path):
        """Should raise FileNotFoundError for missing mapping file."""
        from tools.drive_uploader import DriveUploader

        # Create fake credentials file
        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{}')

        uploader = DriveUploader(
            credentials_path=str(creds_file),
            mapping_path=str(tmp_path / "nonexistent.json"),
        )

        with pytest.raises(FileNotFoundError, match="Folder mapping not found"):
            uploader.load_folder_mapping()

    def test_upload_file_not_found(self, tmp_path):
        """Should raise FileNotFoundError for missing file."""
        from tools.drive_uploader import DriveUploader

        # Create mapping file
        mapping_file = tmp_path / "mapping.json"
        mapping_file.write_text('{"projects": {}}')

        # Create fake credentials file
        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{}')

        uploader = DriveUploader(
            credentials_path=str(creds_file),
            mapping_path=str(mapping_file),
        )

        with pytest.raises(FileNotFoundError, match="File not found"):
            uploader.upload_file(
                file_path=tmp_path / "nonexistent.7z",
                folder_id="folder123",
            )

    def test_flat_mapping_format(self, tmp_path):
        """Should support flat mapping format (without 'projects' key)."""
        from tools.drive_uploader import DriveUploader

        # Create flat mapping file (legacy format)
        mapping_file = tmp_path / "mapping.json"
        mapping_file.write_text('{"test_project": "folder123"}')

        # Create fake credentials file
        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{}')

        uploader = DriveUploader(
            credentials_path=str(creds_file),
            mapping_path=str(mapping_file),
        )

        folder_id = uploader.get_folder_id("test_project")
        assert folder_id == "folder123"

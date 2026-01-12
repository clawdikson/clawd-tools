"""Tests for dashboard validator service.

TDD tests written before implementation.
"""

import tempfile
from dataclasses import dataclass
from pathlib import Path

import pytest


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_validation_result_fields(self):
        """ValidationResult should have category, status, message, fix_action."""
        from tools.dashboard.services.validator import ValidationResult

        result = ValidationResult(
            category="env",
            status="error",
            message="Missing SCRAPER_PROJECT_NAME",
            fix_action="Add SCRAPER_PROJECT_NAME to .env file",
        )

        assert result.category == "env"
        assert result.status == "error"
        assert result.message == "Missing SCRAPER_PROJECT_NAME"
        assert result.fix_action == "Add SCRAPER_PROJECT_NAME to .env file"

    def test_validation_result_optional_fix_action(self):
        """fix_action should be optional."""
        from tools.dashboard.services.validator import ValidationResult

        result = ValidationResult(
            category="security",
            status="warning",
            message="Possible hardcoded credential found",
            fix_action=None,
        )

        assert result.fix_action is None


class TestSecurityIssue:
    """Tests for SecurityIssue dataclass."""

    def test_security_issue_fields(self):
        """SecurityIssue should have file, line_num, pattern, value."""
        from tools.dashboard.services.validator import SecurityIssue

        issue = SecurityIssue(
            file=Path("/tmp/test.py"),
            line_num=42,
            pattern="Password",
            value="secret123...",
        )

        assert issue.file == Path("/tmp/test.py")
        assert issue.line_num == 42
        assert issue.pattern == "Password"
        assert issue.value == "secret123..."


class TestValidator:
    """Tests for Validator service."""

    def test_validator_init(self):
        """Validator should initialize without arguments."""
        from tools.dashboard.services.validator import Validator

        validator = Validator()
        assert validator is not None

    def test_validate_env_missing_file(self, tmp_path: Path):
        """Should return error for missing .env file."""
        from tools.dashboard.services.validator import Validator

        project_path = tmp_path / "audiobee_no_env"
        project_path.mkdir()

        validator = Validator()
        results = validator.validate_env(project_path)

        assert len(results) >= 1
        assert any(r.status == "error" and ".env" in r.message.lower() for r in results)

    def test_validate_env_empty_file(self, tmp_path: Path):
        """Should return warning for empty .env file."""
        from tools.dashboard.services.validator import Validator

        project_path = tmp_path / "audiobee_empty_env"
        project_path.mkdir()
        (project_path / ".env").touch()

        validator = Validator()
        results = validator.validate_env(project_path)

        # Should have warnings about missing required variables
        assert len(results) >= 1

    def test_validate_env_valid_file(self, tmp_path: Path):
        """Should return no errors for valid .env file."""
        from tools.dashboard.services.validator import Validator

        project_path = tmp_path / "audiobee_valid"
        project_path.mkdir()
        env_content = """
SCRAPER_PROJECT_NAME=audiobee_valid
SCRAPER_SITE_TYPE=standalone
"""
        (project_path / ".env").write_text(env_content)

        validator = Validator()
        results = validator.validate_env(project_path)

        errors = [r for r in results if r.status == "error"]
        assert len(errors) == 0

    def test_validate_env_invalid_date_format(self, tmp_path: Path):
        """Should return error for invalid date format."""
        from tools.dashboard.services.validator import Validator

        project_path = tmp_path / "audiobee_bad_date"
        project_path.mkdir()
        env_content = """
SCRAPER_PROJECT_NAME=audiobee_bad_date
SCRAPER_CURR_DATE=2026-01-10
"""
        (project_path / ".env").write_text(env_content)

        validator = Validator()
        results = validator.validate_env(project_path)

        assert any(
            r.status == "error" and "YYYYMMDD" in r.message for r in results
        )

    def test_validate_env_checks_proxy_config(self, tmp_path: Path):
        """Should validate proxy configuration."""
        from tools.dashboard.services.validator import Validator

        project_path = tmp_path / "audiobee_proxy"
        project_path.mkdir()
        # Missing proxy credentials
        env_content = """
SCRAPER_PROJECT_NAME=audiobee_proxy
PROXY_TYPES=smartproxy_session
"""
        (project_path / ".env").write_text(env_content)

        validator = Validator()
        results = validator.validate_env(project_path)

        # Should warn about missing proxy credentials
        assert any(
            "smartproxy" in r.message.lower() or "proxy" in r.message.lower()
            for r in results
        )

    def test_scan_credentials_clean_file(self, tmp_path: Path):
        """Should return empty list for clean file."""
        from tools.dashboard.services.validator import Validator

        project_path = tmp_path / "audiobee_clean"
        project_path.mkdir()
        script = project_path / "scraper.py"
        script.write_text("""
import os
password = os.environ.get("PASSWORD")
username = os.environ.get("USERNAME")
""")

        validator = Validator()
        issues = validator.scan_credentials(project_path)

        assert len(issues) == 0

    def test_scan_credentials_hardcoded_password(self, tmp_path: Path):
        """Should detect hardcoded password."""
        from tools.dashboard.services.validator import Validator

        project_path = tmp_path / "audiobee_hardcoded"
        project_path.mkdir()
        script = project_path / "scraper.py"
        script.write_text("""
password = "supersecret123"
""")

        validator = Validator()
        issues = validator.scan_credentials(project_path)

        assert len(issues) >= 1
        assert any(i.pattern == "Password" for i in issues)

    def test_scan_credentials_hardcoded_api_key(self, tmp_path: Path):
        """Should detect hardcoded API key."""
        from tools.dashboard.services.validator import Validator

        project_path = tmp_path / "audiobee_apikey"
        project_path.mkdir()
        script = project_path / "scraper.py"
        script.write_text("""
api_key = "sk-1234567890abcdef"
""")

        validator = Validator()
        issues = validator.scan_credentials(project_path)

        assert len(issues) >= 1
        assert any("api" in i.pattern.lower() or "key" in i.pattern.lower() for i in issues)

    def test_scan_credentials_skips_safe_patterns(self, tmp_path: Path):
        """Should skip patterns that load from env/config."""
        from tools.dashboard.services.validator import Validator

        project_path = tmp_path / "audiobee_safe"
        project_path.mkdir()
        script = project_path / "scraper.py"
        script.write_text("""
password = os.getenv("PASSWORD")
api_key = config.get("api_key")
secret = settings.SECRET_KEY
""")

        validator = Validator()
        issues = validator.scan_credentials(project_path)

        # Should find nothing because these are safe patterns
        assert len(issues) == 0

    def test_scan_credentials_returns_file_and_line(self, tmp_path: Path):
        """SecurityIssue should include file path and line number."""
        from tools.dashboard.services.validator import Validator

        project_path = tmp_path / "audiobee_line_check"
        project_path.mkdir()
        script = project_path / "scraper.py"
        script.write_text("""# line 1
# line 2
password = "secretvalue"
# line 4
""")

        validator = Validator()
        issues = validator.scan_credentials(project_path)

        assert len(issues) >= 1
        issue = issues[0]
        assert issue.file == script
        assert issue.line_num == 3

    def test_validate_all(self, tmp_path: Path):
        """validate_all should run all validations."""
        from tools.dashboard.services.validator import Validator

        project_path = tmp_path / "audiobee_all"
        project_path.mkdir()
        (project_path / ".env").write_text("SCRAPER_PROJECT_NAME=test")
        (project_path / "scraper.py").write_text("x = 1")

        validator = Validator()
        results = validator.validate_all(project_path)

        # Should return dict with 'env' and 'security' keys
        assert "env" in results
        assert "security" in results

    def test_get_validation_summary(self, tmp_path: Path):
        """Should return summary of validation results."""
        from tools.dashboard.services.validator import Validator

        project_path = tmp_path / "audiobee_summary"
        project_path.mkdir()

        validator = Validator()
        results = validator.validate_env(project_path)
        summary = validator.get_summary(results)

        assert "errors" in summary
        assert "warnings" in summary
        assert "ok" in summary
        assert isinstance(summary["errors"], int)
        assert isinstance(summary["warnings"], int)
        assert isinstance(summary["ok"], int)

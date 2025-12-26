"""Tests for HealthSparq CLI."""

import pytest
from typer.testing import CliRunner

from healthsparq.cli import app

runner = CliRunner()


class TestCLIHelp:
    """Test CLI help output."""

    def test_help_shows_commands(self):
        """--help shows all available commands."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "list" in result.stdout
        assert "validate" in result.stdout
        assert "run" in result.stdout
        assert "doctor" in result.stdout

    def test_version_flag(self):
        """--version shows version."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "healthsparq" in result.stdout


class TestListCommand:
    """Test list command."""

    def test_list_shows_projects(self):
        """list command shows available projects."""
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "christus_health_plan" in result.stdout
        assert "Available projects" in result.stdout

    def test_list_count_only(self):
        """list --count shows only count."""
        result = runner.invoke(app, ["list", "--count"])
        assert result.exit_code == 0
        # Should be a number
        assert result.stdout.strip().isdigit()


class TestValidateCommand:
    """Test validate command."""

    def test_validate_christus(self):
        """validate christus_health_plan succeeds."""
        result = runner.invoke(app, ["validate", "christus_health_plan"])
        assert result.exit_code == 0
        assert "Configuration valid" in result.stdout
        assert "Christus Health Plan" in result.stdout

    def test_validate_nonexistent(self):
        """validate nonexistent project fails."""
        result = runner.invoke(app, ["validate", "nonexistent_project"])
        assert result.exit_code == 1
        assert "not found" in result.output


class TestRunCommand:
    """Test run command."""

    def test_run_dry_run(self):
        """run --dry-run shows what would be done."""
        result = runner.invoke(
            app,
            ["run", "christus_health_plan", "--curr", "20251226", "--dry-run"],
        )
        assert result.exit_code == 0
        assert "Dry run mode" in result.stdout
        assert "christus_health_plan" in result.stdout
        assert "20251226" in result.stdout

    def test_run_with_phase(self):
        """run --phase works."""
        result = runner.invoke(
            app,
            ["run", "christus_health_plan", "--curr", "20251226", "--phase", "1", "--dry-run"],
        )
        assert result.exit_code == 0
        assert "Phase: 1" in result.stdout

    def test_run_nonexistent_project(self):
        """run nonexistent project fails."""
        result = runner.invoke(
            app,
            ["run", "nonexistent_project", "--curr", "20251226"],
        )
        assert result.exit_code == 1
        assert "not found" in result.output


class TestDoctorCommand:
    """Test doctor command."""

    def test_doctor_passes(self):
        """doctor command passes with valid configs."""
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "health checks passed" in result.stdout

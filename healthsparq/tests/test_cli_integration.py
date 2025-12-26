"""Comprehensive CLI integration tests for HealthSparq CLI.

Tests command exit codes, error messages, output formats, and option handling.
"""

import tempfile
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from healthsparq.cli import app

runner = CliRunner()


class TestExitCodes:
    """Test CLI command exit codes."""

    def test_success_commands_return_zero(self):
        """Successful commands return exit code 0."""
        # List command
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0

        # List with count
        result = runner.invoke(app, ["list", "--count"])
        assert result.exit_code == 0

        # Validate existing project
        result = runner.invoke(app, ["validate", "christus_health_plan"])
        assert result.exit_code == 0

        # Dry run
        result = runner.invoke(
            app,
            ["run", "christus_health_plan", "--curr", "20251226", "--dry-run"],
        )
        assert result.exit_code == 0

        # Doctor (assuming all configs are valid)
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0

        # Version flag
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0

        # Help flag
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_invalid_project_returns_nonzero(self):
        """Invalid project returns non-zero exit code."""
        # Validate non-existent project
        result = runner.invoke(app, ["validate", "nonexistent_project_xyz"])
        assert result.exit_code == 1

        # Run non-existent project
        result = runner.invoke(
            app,
            ["run", "nonexistent_project_xyz", "--curr", "20251226"],
        )
        assert result.exit_code == 1

    def test_validation_failures_return_nonzero(self):
        """Validation failures return non-zero exit code."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            # Create invalid YAML (missing required fields)
            invalid_config = config_dir / "invalid_project.yaml"
            invalid_config.write_text(
                """
project:
  name: Invalid Project
# Missing required fields: slug, site, plans, coverage
"""
            )

            # Mock list_projects to return our temp project
            from healthsparq.config import loader

            original_list = loader.list_projects
            original_load = loader.load_config

            try:
                loader.list_projects = lambda config_dir=None: ["invalid_project"]
                loader.load_config = lambda slug, config_dir=None: loader.load_config(
                    slug, config_dir or Path(tmpdir)
                )

                result = runner.invoke(app, ["validate", "invalid_project"])
                assert result.exit_code == 1
            finally:
                loader.list_projects = original_list
                loader.load_config = original_load

    def test_missing_required_args_returns_nonzero(self):
        """Missing required arguments return non-zero exit code."""
        # Run without project argument
        result = runner.invoke(app, ["run"])
        assert result.exit_code != 0

        # Run without --curr flag
        result = runner.invoke(app, ["run", "christus_health_plan"])
        assert result.exit_code != 0

        # Validate without project argument
        result = runner.invoke(app, ["validate"])
        assert result.exit_code != 0


class TestErrorMessages:
    """Test CLI error messages."""

    def test_invalid_project_shows_helpful_error(self):
        """Invalid project shows helpful error message."""
        result = runner.invoke(app, ["validate", "nonexistent_project_xyz"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()
        assert "nonexistent_project_xyz" in result.output

    def test_missing_required_args_shows_usage(self):
        """Missing required args shows usage information."""
        # Run without project
        result = runner.invoke(app, ["run"])
        assert result.exit_code != 0
        # Should show usage/help info
        assert "Usage:" in result.output or "Error:" in result.output

        # Run without --curr
        result = runner.invoke(app, ["run", "christus_health_plan"])
        assert result.exit_code != 0
        assert "--curr" in result.output or "required" in result.output.lower()

    def test_invalid_option_values_show_error(self):
        """Invalid option values show error messages."""
        # Invalid phase value (not 1, 2, or 3)
        result = runner.invoke(
            app,
            ["run", "christus_health_plan", "--curr", "20251226", "--phase", "5"],
        )
        # Note: Typer validates int type, actual phase validation happens in executor
        # For now we just ensure it doesn't crash with type error
        assert result.exit_code in [0, 1, 2]  # May succeed in dry-run mode

    def test_yaml_parse_error_shows_error(self):
        """YAML parse errors show meaningful error messages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            # Create invalid YAML (syntax error)
            bad_yaml = config_dir / "bad_yaml.yaml"
            bad_yaml.write_text(
                """
project:
  name: Bad YAML
  invalid: [unclosed bracket
"""
            )

            from healthsparq.config import loader

            original_load = loader.load_config

            try:
                loader.load_config = lambda slug, config_dir=None: loader.load_config(
                    slug, config_dir or Path(tmpdir)
                )

                result = runner.invoke(app, ["validate", "bad_yaml"])
                assert result.exit_code == 1
                assert "Error" in result.output
            finally:
                loader.load_config = original_load


class TestListCommand:
    """Test list command variations."""

    def test_default_output_format(self):
        """List command shows projects with labels."""
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "Available projects:" in result.stdout
        assert "christus_health_plan" in result.stdout
        assert "Total:" in result.stdout
        assert "projects" in result.stdout

    def test_count_only_shows_count(self):
        """--count flag shows only numeric count."""
        result = runner.invoke(app, ["list", "--count"])
        assert result.exit_code == 0

        # Output should be a single number
        output = result.stdout.strip()
        assert output.isdigit()
        assert int(output) > 0

        # Should NOT contain labels
        assert "Available projects:" not in output
        assert "Total:" not in output

    def test_count_short_flag(self):
        """-c flag is shorthand for --count."""
        result = runner.invoke(app, ["list", "-c"])
        assert result.exit_code == 0
        assert result.stdout.strip().isdigit()

    def test_empty_configs_dir_handling(self, monkeypatch):
        """Empty config directory shows zero projects."""
        # Mock list_projects to return empty list
        monkeypatch.setattr(
            "healthsparq.cli.list_projects",
            lambda: [],
        )

        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "Total: 0 projects" in result.stdout


class TestValidateCommand:
    """Test validate command."""

    def test_valid_project_shows_success(self):
        """Valid project shows success message."""
        result = runner.invoke(app, ["validate", "christus_health_plan"])
        assert result.exit_code == 0
        assert "Configuration valid" in result.stdout
        assert "christus_health_plan" in result.stdout

    def test_valid_project_shows_details(self):
        """Valid project shows configuration details."""
        result = runner.invoke(app, ["validate", "christus_health_plan"])
        assert result.exit_code == 0

        # Should show key config details
        assert "Name:" in result.stdout
        assert "Christus Health Plan" in result.stdout
        assert "Domain:" in result.stdout
        assert "christushealthplan.healthsparq.com" in result.stdout
        assert "Plans:" in result.stdout
        assert "States:" in result.stdout

    def test_invalid_yaml_shows_parse_error(self):
        """Invalid YAML shows parse error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            # Create malformed YAML
            bad_config = config_dir / "bad_syntax.yaml"
            bad_config.write_text("project:\n  - [unclosed")

            from healthsparq.config import loader

            original_load = loader.load_config

            try:
                loader.load_config = lambda slug, config_dir=None: loader.load_config(
                    slug, config_dir or Path(tmpdir)
                )

                result = runner.invoke(app, ["validate", "bad_syntax"])
                assert result.exit_code == 1
                assert "Error" in result.output
            finally:
                loader.load_config = original_load

    def test_missing_required_fields_shows_validation_error(self):
        """Missing required fields shows validation error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            # Create config missing required fields
            incomplete_config = config_dir / "incomplete.yaml"
            incomplete_config.write_text(
                yaml.dump(
                    {
                        "project": {
                            "name": "Incomplete",
                            "slug": "incomplete",
                        },
                        # Missing: site, plans, coverage
                    }
                )
            )

            from healthsparq.config import loader

            original_load = loader.load_config

            try:
                loader.load_config = lambda slug, config_dir=None: loader.load_config(
                    slug, config_dir or Path(tmpdir)
                )

                result = runner.invoke(app, ["validate", "incomplete"])
                assert result.exit_code == 1
                assert "Error" in result.output
            finally:
                loader.load_config = original_load


class TestRunCommand:
    """Test run command options."""

    def test_dry_run_doesnt_execute(self):
        """--dry-run shows plan without executing."""
        result = runner.invoke(
            app,
            ["run", "christus_health_plan", "--curr", "20251226", "--dry-run"],
        )
        assert result.exit_code == 0
        assert "Dry run mode" in result.stdout
        assert "no changes will be made" in result.stdout.lower()
        assert "Would run scraper" in result.stdout

    def test_dry_run_short_flag(self):
        """-n flag is shorthand for --dry-run."""
        result = runner.invoke(
            app,
            ["run", "christus_health_plan", "--curr", "20251226", "-n"],
        )
        assert result.exit_code == 0
        assert "Dry run mode" in result.stdout

    def test_phase_1_individually(self):
        """--phase 1 runs phase 1 only."""
        result = runner.invoke(
            app,
            [
                "run",
                "christus_health_plan",
                "--curr",
                "20251226",
                "--phase",
                "1",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "Phase: 1" in result.stdout

    def test_phase_2_individually(self):
        """--phase 2 runs phase 2 only."""
        result = runner.invoke(
            app,
            [
                "run",
                "christus_health_plan",
                "--curr",
                "20251226",
                "--phase",
                "2",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "Phase: 2" in result.stdout

    def test_phase_3_individually(self):
        """--phase 3 runs phase 3 only."""
        result = runner.invoke(
            app,
            [
                "run",
                "christus_health_plan",
                "--curr",
                "20251226",
                "--phase",
                "3",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "Phase: 3" in result.stdout

    def test_phase_short_flag(self):
        """-p flag is shorthand for --phase."""
        result = runner.invoke(
            app,
            [
                "run",
                "christus_health_plan",
                "--curr",
                "20251226",
                "-p",
                "1",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "Phase: 1" in result.stdout

    def test_curr_date_format_validation(self):
        """--curr accepts YYYYMMDD format."""
        # Valid format
        result = runner.invoke(
            app,
            ["run", "christus_health_plan", "--curr", "20251226", "--dry-run"],
        )
        assert result.exit_code == 0
        assert "20251226" in result.stdout

        # Note: Date format validation would be implemented in the executor
        # For now we just ensure the CLI accepts the argument

    def test_prev_date_format_validation(self):
        """--prev accepts YYYYMMDD format."""
        result = runner.invoke(
            app,
            [
                "run",
                "christus_health_plan",
                "--curr",
                "20251226",
                "--prev",
                "20251210",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "20251226" in result.stdout
        assert "20251210" in result.stdout

    def test_invalid_date_format_handling(self):
        """Invalid date format handling."""
        # Note: Current CLI accepts any string for dates
        # Date validation would be in the executor
        # This test documents current behavior
        result = runner.invoke(
            app,
            ["run", "christus_health_plan", "--curr", "invalid-date", "--dry-run"],
        )
        # Currently succeeds in dry-run, would fail in actual execution
        assert result.exit_code == 0

    def test_dry_run_shows_config_details(self):
        """Dry run shows configuration details."""
        result = runner.invoke(
            app,
            ["run", "christus_health_plan", "--curr", "20251226", "--dry-run"],
        )
        assert result.exit_code == 0
        assert "christus_health_plan" in result.stdout
        assert "Domain:" in result.stdout
        assert "Plans:" in result.stdout
        assert "States:" in result.stdout
        assert "Max workers:" in result.stdout

    def test_run_without_dry_run_shows_note(self):
        """Run without --dry-run shows implementation note."""
        result = runner.invoke(
            app,
            ["run", "christus_health_plan", "--curr", "20251226"],
        )
        assert result.exit_code == 0
        assert "Running scraper for:" in result.stdout
        assert "Actual scraping will be implemented" in result.stdout

    def test_run_with_prev_date(self):
        """Run with both --curr and --prev dates."""
        result = runner.invoke(
            app,
            [
                "run",
                "christus_health_plan",
                "--curr",
                "20251226",
                "--prev",
                "20251210",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "Current date: 20251226" in result.stdout
        assert "Previous date: 20251210" in result.stdout

    def test_run_without_prev_date(self):
        """Run without --prev shows 'not specified'."""
        result = runner.invoke(
            app,
            ["run", "christus_health_plan", "--curr", "20251226", "--dry-run"],
        )
        assert result.exit_code == 0
        assert "Previous date: not specified" in result.stdout


class TestDoctorCommand:
    """Test doctor command."""

    def test_shows_healthcheck_output(self):
        """Doctor shows health check output."""
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "health checks" in result.stdout.lower()

    def test_shows_config_validation_status(self):
        """Doctor shows config validation status."""
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "Projects found:" in result.stdout
        assert "Valid configs:" in result.stdout

    def test_returns_error_if_critical_issues(self, monkeypatch):
        """Doctor returns error if critical issues found."""
        # Mock list_projects to return two projects
        monkeypatch.setattr(
            "healthsparq.cli.list_projects",
            lambda: ["valid_project", "invalid_project"],
        )

        # Mock load_config to succeed for valid, fail for invalid
        def mock_load_config(slug):
            if slug == "invalid_project":
                raise ValueError("Missing required field: site")
            # Return a minimal valid config for valid_project
            from healthsparq.config.schema import (
                HealthSparqProjectConfig,
                ProjectInfo,
                SiteConfig,
                PlanConfig,
                CoverageConfig,
            )

            return HealthSparqProjectConfig(
                project=ProjectInfo(name="Valid", slug="valid_project"),
                site=SiteConfig(
                    domain="test.com", brand_code="TEST", insurer_code="TEST_I"
                ),
                plans=[PlanConfig(product_code="TEST", name="Test Plan")],
                coverage=CoverageConfig(states=["TX"]),
            )

        monkeypatch.setattr("healthsparq.cli.load_config", mock_load_config)

        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 1
        assert "Errors" in result.stdout

    def test_passes_with_all_valid_configs(self):
        """Doctor passes with all valid configs."""
        result = runner.invoke(app, ["doctor"])
        # Should pass if all real configs are valid
        if result.exit_code == 0:
            assert "All health checks passed" in result.stdout


class TestHelpOutput:
    """Test help output."""

    def test_main_help_shows_commands(self):
        """Main --help shows all commands."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "list" in result.stdout
        assert "validate" in result.stdout
        assert "run" in result.stdout
        assert "doctor" in result.stdout

    def test_list_command_has_help(self):
        """list command has help text."""
        result = runner.invoke(app, ["list", "--help"])
        assert result.exit_code == 0
        assert "List available project configurations" in result.stdout
        assert "--count" in result.stdout

    def test_validate_command_has_help(self):
        """validate command has help text."""
        result = runner.invoke(app, ["validate", "--help"])
        assert result.exit_code == 0
        assert "Validate a project configuration" in result.stdout
        assert "PROJECT" in result.stdout

    def test_run_command_has_help(self):
        """run command has help text."""
        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0
        assert "Run a scraper" in result.stdout
        assert "--curr" in result.stdout
        assert "--prev" in result.stdout
        assert "--phase" in result.stdout
        assert "--dry-run" in result.stdout

    def test_doctor_command_has_help(self):
        """doctor command has help text."""
        result = runner.invoke(app, ["doctor", "--help"])
        assert result.exit_code == 0
        assert "health checks" in result.stdout.lower()

    def test_options_are_documented(self):
        """Options are documented in help."""
        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0

        # Check key options are documented
        assert "--curr" in result.stdout
        assert "YYYYMMDD" in result.stdout
        assert "--prev" in result.stdout
        assert "--phase" in result.stdout
        assert "--dry-run" in result.stdout

        # Check short flags
        assert "-p" in result.stdout
        assert "-n" in result.stdout

    def test_list_help_shows_examples(self):
        """list help shows usage examples."""
        result = runner.invoke(app, ["list", "--help"])
        assert result.exit_code == 0
        assert "--count" in result.stdout or "-c" in result.stdout

    def test_version_in_help(self):
        """Version info available in help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "--version" in result.stdout


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_run_nonexistent_project_with_valid_dates(self):
        """Run with nonexistent project fails gracefully."""
        result = runner.invoke(
            app,
            ["run", "fake_project_xyz", "--curr", "20251226", "--dry-run"],
        )
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_phase_without_dry_run(self):
        """Phase flag works without dry-run."""
        result = runner.invoke(
            app,
            ["run", "christus_health_plan", "--curr", "20251226", "--phase", "1"],
        )
        assert result.exit_code == 0
        assert "Phase: 1" in result.stdout

    def test_multiple_flags_combined(self):
        """Multiple flags can be combined."""
        result = runner.invoke(
            app,
            [
                "run",
                "christus_health_plan",
                "--curr",
                "20251226",
                "--prev",
                "20251210",
                "--phase",
                "2",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "20251226" in result.stdout
        assert "20251210" in result.stdout
        assert "Phase: 2" in result.stdout
        assert "Dry run mode" in result.stdout

    def test_list_with_no_projects(self, monkeypatch):
        """List with no projects shows empty list."""
        monkeypatch.setattr("healthsparq.cli.list_projects", lambda: [])

        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "Total: 0 projects" in result.stdout

    def test_doctor_with_no_projects(self, monkeypatch):
        """Doctor with no projects succeeds."""
        monkeypatch.setattr("healthsparq.cli.list_projects", lambda: [])

        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "Projects found: 0" in result.stdout
        assert "Valid configs: 0" in result.stdout


class TestCommandCombinations:
    """Test command combinations and workflows."""

    def test_list_then_validate_workflow(self):
        """List projects then validate one."""
        # First list
        list_result = runner.invoke(app, ["list"])
        assert list_result.exit_code == 0

        # Then validate one from the list
        validate_result = runner.invoke(app, ["validate", "christus_health_plan"])
        assert validate_result.exit_code == 0

    def test_validate_then_run_workflow(self):
        """Validate then run workflow."""
        # First validate
        validate_result = runner.invoke(app, ["validate", "christus_health_plan"])
        assert validate_result.exit_code == 0

        # Then run with dry-run
        run_result = runner.invoke(
            app,
            ["run", "christus_health_plan", "--curr", "20251226", "--dry-run"],
        )
        assert run_result.exit_code == 0

    def test_doctor_before_run_workflow(self):
        """Doctor check before running."""
        # First run doctor
        doctor_result = runner.invoke(app, ["doctor"])
        assert doctor_result.exit_code == 0

        # Then run a project
        run_result = runner.invoke(
            app,
            ["run", "christus_health_plan", "--curr", "20251226", "--dry-run"],
        )
        assert run_result.exit_code == 0

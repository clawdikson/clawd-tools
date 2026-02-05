"""Validation screen - run validation checks on projects.

Provides environment validation and security scanning
with results display and fix suggestions.
"""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, DataTable, Select, Static

from tools.dashboard.services.validator import Validator, ValidationResult, SecurityIssue
from tools.dashboard.services.registry import ProjectRegistry


class ValidateScreen(Container):
    """Validation tools screen.

    Shows:
    - Project selector
    - Validation buttons (env, security, all)
    - Results table with status, message, fix action

    Supports batch validation of all projects.
    """

    DEFAULT_CSS = """
    ValidateScreen {
        layout: vertical;
        height: 1fr;
        width: 1fr;
        padding: 1;
    }

    #validate-header {
        height: auto;
        margin-bottom: 1;
    }

    #validate-header Static {
        width: auto;
        padding-right: 1;
    }

    #validate-header #project-select {
        width: 1fr;
    }

    #validate-actions {
        height: auto;
        layout: horizontal;
        margin-bottom: 1;
    }

    #validate-actions Button {
        margin-right: 1;
    }

    #validate-results {
        height: 1fr;
    }

    .summary-ok { color: green; }
    .summary-warning { color: yellow; }
    .summary-error { color: red; }
    """

    def __init__(self, *args, **kwargs):
        """Initialize the validation screen."""
        super().__init__(*args, **kwargs)
        self._validator = Validator()
        self._current_project = None

    def compose(self) -> ComposeResult:
        """Compose the validation screen layout."""
        with Horizontal(id="validate-header"):
            yield Static("Project: ")
            yield Select(
                [("Select a project", None)],
                id="project-select",
                allow_blank=True,
            )

        with Horizontal(id="validate-actions"):
            yield Button("Validate Env", id="btn-validate-env", variant="primary")
            yield Button("Security Scan", id="btn-security-scan")
            yield Button("Validate All Projects", id="btn-validate-all")

        yield Static("", id="validate-summary")

        with VerticalScroll(id="validate-results"):
            yield DataTable(id="results-table")

    def on_mount(self) -> None:
        """Initialize the screen."""
        self._populate_projects()
        self._setup_table()

    def _populate_projects(self) -> None:
        """Populate project selector."""
        registry = ProjectRegistry()
        projects = registry.discover_projects()

        select = self.query_one("#project-select", Select)
        options = [("Select a project", None)]
        for project in projects:
            options.append((project.name, project.name))

        select.set_options(options)

    def _setup_table(self) -> None:
        """Set up the results table."""
        table = self.query_one("#results-table", DataTable)
        table.add_columns("Status", "Category", "Message", "Fix Action")

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle project selection."""
        self._current_project = event.value
        # Clear results when project changes
        table = self.query_one("#results-table", DataTable)
        table.clear()
        self.query_one("#validate-summary", Static).update("")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-validate-env":
            self._run_env_validation()
        elif event.button.id == "btn-security-scan":
            self._run_security_scan()
        elif event.button.id == "btn-validate-all":
            self._run_validate_all()

    def _run_env_validation(self) -> None:
        """Run environment validation on selected project."""
        if not self._current_project:
            self.notify("Please select a project first", severity="warning")
            return

        registry = ProjectRegistry()
        project = registry.get_project_by_name(self._current_project)

        if not project:
            return

        results = self._validator.validate_env(project.path)
        self._display_validation_results(results)

    def _run_security_scan(self) -> None:
        """Run security scan on selected project."""
        if not self._current_project:
            self.notify("Please select a project first", severity="warning")
            return

        registry = ProjectRegistry()
        project = registry.get_project_by_name(self._current_project)

        if not project:
            return

        issues = self._validator.scan_credentials(project.path)
        self._display_security_issues(issues)

    def _run_validate_all(self) -> None:
        """Run validation on all projects."""
        registry = ProjectRegistry()
        projects = registry.discover_projects()

        table = self.query_one("#results-table", DataTable)
        table.clear()

        total_errors = 0
        total_warnings = 0

        for project in projects:
            results = self._validator.validate_env(project.path)
            for result in results:
                status_icon = self._get_status_icon(result.status)
                table.add_row(
                    status_icon,
                    f"{project.name}:{result.category}",
                    result.message,
                    result.fix_action or "",
                )
                if result.status == "error":
                    total_errors += 1
                elif result.status == "warning":
                    total_warnings += 1

        summary = self.query_one("#validate-summary", Static)
        summary.update(
            f"Validated {len(projects)} projects: "
            f"[red]{total_errors} errors[/red], "
            f"[yellow]{total_warnings} warnings[/yellow]"
        )

    def _display_validation_results(self, results: list[ValidationResult]) -> None:
        """Display validation results in the table."""
        table = self.query_one("#results-table", DataTable)
        table.clear()

        for result in results:
            status_icon = self._get_status_icon(result.status)
            table.add_row(
                status_icon,
                result.category,
                result.message,
                result.fix_action or "",
            )

        summary = self._validator.get_summary(results)
        summary_widget = self.query_one("#validate-summary", Static)
        summary_widget.update(
            f"[red]{summary['errors']} errors[/red], "
            f"[yellow]{summary['warnings']} warnings[/yellow], "
            f"[green]{summary['ok']} ok[/green]"
        )

    def _display_security_issues(self, issues: list[SecurityIssue]) -> None:
        """Display security issues in the table."""
        table = self.query_one("#results-table", DataTable)
        table.clear()

        for issue in issues:
            table.add_row(
                "[red]![/red]",
                "security",
                f"{issue.pattern} at {issue.file.name}:{issue.line_num}",
                f"Value: {issue.value}",
            )

        summary = self.query_one("#validate-summary", Static)
        if issues:
            summary.update(f"[red]{len(issues)} potential security issues found[/red]")
        else:
            summary.update("[green]No security issues found[/green]")

    def _get_status_icon(self, status: str) -> str:
        """Get icon for status."""
        if status == "error":
            return "[red]X[/red]"
        elif status == "warning":
            return "[yellow]![/yellow]"
        else:
            return "[green]OK[/green]"

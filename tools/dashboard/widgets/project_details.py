"""Project details widget - displays selected project information.

Shows project metadata, status, and available actions.
"""

from textual.app import ComposeResult
from textual.widgets import Static

from tools.dashboard.services.registry import Project


class ProjectDetails(Static):
    """Widget showing details of a selected project.

    Displays:
    - Project name
    - Platform type
    - Last run date
    - Status
    - Record count (if available)
    - Available actions

    Listens for ProjectSelected messages from ProjectTree.
    """

    DEFAULT_CSS = """
    ProjectDetails {
        height: 100%;
        padding: 1;
    }

    .detail-title {
        text-style: bold;
        margin-bottom: 1;
    }

    .detail-row {
        margin-bottom: 0;
    }

    .detail-label {
        color: $text-muted;
    }

    .detail-value {
        color: $text;
    }

    .detail-actions {
        margin-top: 2;
        border-top: solid $primary-darken-2;
        padding-top: 1;
    }

    .status-healthy { color: green; }
    .status-warning { color: yellow; }
    .status-error { color: red; }
    """

    def __init__(self, *args, **kwargs):
        """Initialize the details widget."""
        super().__init__(*args, **kwargs)
        self._current_project: Project | None = None

    def compose(self) -> ComposeResult:
        """Initial empty state."""
        yield Static("Select a project to view details", classes="detail-title")

    def set_project(self, project: Project) -> None:
        """Update display with project information.

        Args:
            project: Project to display
        """
        self._current_project = project
        self._update_display()

    def _update_display(self) -> None:
        """Rebuild the display with current project data."""
        if not self._current_project:
            return

        project = self._current_project

        # Format status
        status_class = f"status-{project.status}"
        status_text = project.status.upper()

        # Format last run
        if project.last_run:
            # Format YYYYMMDD to YYYY-MM-DD
            d = project.last_run
            last_run_text = f"{d[:4]}-{d[4:6]}-{d[6:]}"
        else:
            last_run_text = "Never"

        # Build content
        content = f"""[bold]{project.name}[/bold]

Platform:   {project.platform}
Last Run:   {last_run_text}
Status:     [{status_class}]{status_text}[/{status_class}]
Has .env:   {'Yes' if project.has_env else 'No'}
Path:       {project.path}

[dim]Actions:[/dim]
  [R]un  [V]alidate  [D]ata  [L]ogs
"""
        self.update(content)

    def on_project_selected(self, event) -> None:
        """Handle project selection from tree.

        This method is called when a ProjectSelected message bubbles up.
        """
        # Import here to avoid circular imports
        from tools.dashboard.widgets.project_tree import ProjectSelected

        if isinstance(event, ProjectSelected):
            self.set_project(event.project)

"""Projects screen - browse and manage scraper projects.

Displays a tree view of all projects grouped by platform,
with details panel showing project information and actions.
"""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static

from tools.dashboard.widgets.project_tree import ProjectTree, ProjectSelected
from tools.dashboard.widgets.project_details import ProjectDetails


class ProjectsScreen(Container):
    """Projects browser screen.

    Shows:
    - Left panel: Tree of projects grouped by platform
    - Right panel: Selected project details and actions

    Keybindings:
    - r: Run selected project
    - v: Validate selected project
    - d: Open data explorer for project
    - l: View project logs
    """

    DEFAULT_CSS = """
    ProjectsScreen {
        layout: horizontal;
        height: 1fr;
        width: 1fr;
    }

    #project-tree-container {
        width: 40%;
        height: 100%;
        border-right: solid $primary-darken-2;
    }

    #project-details-container {
        width: 60%;
        height: 100%;
        padding: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the projects screen layout."""
        with Vertical(id="project-tree-container"):
            yield ProjectTree(id="project-tree")

        with Vertical(id="project-details-container"):
            yield ProjectDetails(id="project-details")

    def on_project_selected(self, event: ProjectSelected) -> None:
        """Handle project selection and forward to details panel."""
        details = self.query_one("#project-details", ProjectDetails)
        details.set_project(event.project)

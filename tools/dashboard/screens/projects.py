"""Projects screen - browse and manage scraper projects.

Displays a tree view of all projects grouped by platform,
with details panel showing project information and actions.
"""

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from tools.dashboard.widgets.project_tree import ProjectTree
from tools.dashboard.widgets.project_details import ProjectDetails


class ProjectsScreen(Static):
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
        height: 100%;
    }

    #project-tree-container {
        width: 40%;
        border-right: solid $primary-darken-2;
    }

    #project-details-container {
        width: 60%;
        padding: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the projects screen layout."""
        with Horizontal():
            with Vertical(id="project-tree-container"):
                yield ProjectTree(id="project-tree")

            with Vertical(id="project-details-container"):
                yield ProjectDetails(id="project-details")

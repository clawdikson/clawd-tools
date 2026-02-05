"""Project tree widget - displays projects grouped by platform.

Extends Textual's Tree widget to show projects organized by
platform type (healthsparq, sapphire, standalone).
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from textual.message import Message
from textual.widgets import Tree
from textual.widgets.tree import TreeNode

from tools.dashboard.services.registry import Project, ProjectRegistry


class ProjectSelected(Message):
    """Message sent when a project is selected.

    Attributes:
        project: The selected Project object
    """

    def __init__(self, project: Project) -> None:
        super().__init__()
        self.project = project


class ProjectTree(Tree[Project]):
    """Tree widget showing projects grouped by platform.

    Groups projects under:
    - healthsparq/ (count)
    - sapphire/ (count)
    - standalone/ (count)

    Shows status icons:
    - OK: healthy
    - !: warning
    - X: error
    """

    DEFAULT_CSS = """
    ProjectTree {
        height: 100%;
        scrollbar-gutter: stable;
    }
    """

    BINDINGS: ClassVar = [
        ("r", "run_project", "Run"),
        ("v", "validate_project", "Validate"),
        ("d", "view_data", "Data"),
        ("l", "view_logs", "Logs"),
    ]

    STATUS_ICONS = {
        "healthy": "[green]OK[/green]",
        "warning": "[yellow]![/yellow]",
        "error": "[red]X[/red]",
    }

    def __init__(
        self,
        *args,
        root_path: Path | None = None,
        **kwargs,
    ):
        """Initialize the project tree.

        Args:
            root_path: Root directory to scan for projects
        """
        super().__init__("Projects", *args, **kwargs)
        self._registry = ProjectRegistry(root_path=root_path)
        self._platform_nodes: dict[str, TreeNode] = {}

    def on_mount(self) -> None:
        """Build the tree when mounted."""
        self.root.expand()
        self._build_tree()

    def _build_tree(self) -> None:
        """Build the project tree from registry."""
        projects = self._registry.discover_projects()

        # Group by platform
        by_platform: dict[str, list[Project]] = {
            "healthsparq": [],
            "sapphire": [],
            "standalone": [],
        }

        for project in projects:
            platform = project.platform
            if platform not in by_platform:
                platform = "standalone"
            by_platform[platform].append(project)

        # Create platform nodes
        for platform, platform_projects in by_platform.items():
            if not platform_projects:
                continue

            label = f"{platform}/ ({len(platform_projects)})"
            platform_node = self.root.add(label)
            self._platform_nodes[platform] = platform_node

            # Add project nodes
            for project in sorted(platform_projects, key=lambda p: p.name):
                status_icon = self.STATUS_ICONS.get(project.status, "")
                label = f"{project.name} {status_icon}"
                platform_node.add_leaf(label, data=project)

            platform_node.expand()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle tree node selection."""
        node = event.node
        if node.data is not None and isinstance(node.data, Project):
            self.post_message(ProjectSelected(node.data))

    def refresh_tree(self) -> None:
        """Refresh the project tree."""
        self.root.remove_children()
        self._platform_nodes.clear()
        self._registry.refresh()
        self._build_tree()

    def action_run_project(self) -> None:
        """Run the selected project."""
        node = self.cursor_node
        if node and node.data:
            self.app.notify(f"Run: {node.data.name}")

    def action_validate_project(self) -> None:
        """Validate the selected project."""
        node = self.cursor_node
        if node and node.data:
            self.app.notify(f"Validate: {node.data.name}")

    def action_view_data(self) -> None:
        """Open data explorer for selected project."""
        node = self.cursor_node
        if node and node.data:
            self.app.notify(f"Data: {node.data.name}")

    def action_view_logs(self) -> None:
        """View logs for selected project."""
        node = self.cursor_node
        if node and node.data:
            self.app.notify(f"Logs: {node.data.name}")

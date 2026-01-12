"""Data explorer screen - browse SQLiteFS databases.

Wraps the existing sqlitefs_explorer components to provide
an integrated data browsing experience.
"""

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Select, Static


class DataScreen(Static):
    """Data explorer screen.

    Shows:
    - Project selector dropdown
    - SQLiteFS tree browser
    - JSON viewer for selected files

    Reuses components from tools.sqlitefs_explorer.
    """

    DEFAULT_CSS = """
    DataScreen {
        height: 100%;
        padding: 1;
    }

    #data-header {
        height: 3;
        margin-bottom: 1;
    }

    #data-browser {
        height: 1fr;
        layout: horizontal;
    }

    #data-tree-pane {
        width: 40%;
        border-right: solid $primary-darken-2;
    }

    #data-viewer-pane {
        width: 60%;
    }

    .placeholder {
        text-align: center;
        color: $text-muted;
        padding: 4;
    }
    """

    def __init__(self, *args, **kwargs):
        """Initialize the data screen."""
        super().__init__(*args, **kwargs)
        self._current_project = None
        self._current_db = None

    def compose(self) -> ComposeResult:
        """Compose the data screen layout."""
        with Vertical():
            with Horizontal(id="data-header"):
                yield Static("Project: ")
                yield Select(
                    [(("Select a project", None))],
                    id="project-select",
                    allow_blank=True,
                )

            with Horizontal(id="data-browser"):
                with Vertical(id="data-tree-pane"):
                    yield Static(
                        "Select a project to browse data",
                        classes="placeholder",
                    )

                with Vertical(id="data-viewer-pane"):
                    yield Static(
                        "Select a file to view",
                        classes="placeholder",
                    )

    def on_mount(self) -> None:
        """Populate project selector on mount."""
        self._populate_projects()

    def _populate_projects(self) -> None:
        """Populate project selector with discovered projects."""
        from tools.dashboard.services.registry import ProjectRegistry

        registry = ProjectRegistry()
        projects = registry.discover_projects()

        select = self.query_one("#project-select", Select)
        options = [("Select a project", None)]
        for project in projects:
            options.append((project.name, project.name))

        select.set_options(options)

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle project selection change."""
        if event.value is None:
            return

        self._current_project = event.value
        self._load_project_data(event.value)

    def _load_project_data(self, project_name: str) -> None:
        """Load data browser for selected project.

        Finds SQLite databases in the project directory and
        loads them into the tree browser.
        """
        from tools.dashboard.services.registry import ProjectRegistry

        registry = ProjectRegistry()
        project = registry.get_project_by_name(project_name)

        if not project:
            return

        # Find SQLite databases
        db_files = list(project.path.rglob("*.db"))

        if not db_files:
            tree_pane = self.query_one("#data-tree-pane")
            tree_pane.remove_children()
            tree_pane.mount(
                Static(f"No databases found in {project_name}", classes="placeholder")
            )
            return

        # Use the first database found (typically the most recent)
        # In future, could add database selector
        db_path = db_files[0]
        self._load_database(db_path)

    def _load_database(self, db_path: Path) -> None:
        """Load a SQLiteFS database into the browser.

        Args:
            db_path: Path to SQLite database file
        """
        from tools.sqlitefs_explorer.backend import LazyTreeBackend
        from tools.sqlitefs_explorer.widgets.tree import VirtualFSTree
        from tools.sqlitefs_explorer.widgets.viewer import JSONViewer

        self._current_db = db_path

        # Replace tree pane contents
        tree_pane = self.query_one("#data-tree-pane")
        tree_pane.remove_children()

        backend = LazyTreeBackend(str(db_path))
        tree = VirtualFSTree(backend, id="data-tree")
        tree_pane.mount(tree)

        # Replace viewer pane contents
        viewer_pane = self.query_one("#data-viewer-pane")
        viewer_pane.remove_children()

        viewer = JSONViewer(id="data-viewer")
        viewer_pane.mount(viewer)

"""Data explorer screen - browse SQLiteFS databases.

Shows a tree of projects/runs/databases on the left,
and the SQLiteFS explorer on the right when a database is selected.
"""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static

from tools.dashboard.widgets.database_tree import DatabaseTree, DatabaseSelected
from tools.dashboard.utils.db_validation import is_sqlitefs_database


class DataScreen(Container):
    """Data explorer screen.

    Shows:
    - Left panel: Tree of projects → runs → databases
    - Right panel: SQLiteFS tree browser and JSON viewer

    Similar layout to Projects tab but for data exploration.
    """

    DEFAULT_CSS = """
    DataScreen {
        layout: horizontal;
        height: 1fr;
        width: 1fr;
    }

    #db-tree-pane {
        width: 30%;
        height: 100%;
        border-right: solid $primary-darken-2;
    }

    #data-explorer-pane {
        width: 70%;
        height: 100%;
        layout: vertical;
    }

    #db-info {
        height: auto;
        padding: 1;
        background: $surface;
        border-bottom: solid $primary-darken-2;
    }

    #data-browser {
        height: 1fr;
        width: 100%;
    }

    #data-tree-pane {
        width: 50%;
        height: 100%;
        border-right: solid $primary-darken-2;
    }

    #data-viewer-pane {
        width: 50%;
        height: 100%;
        padding: 1;
    }

    .placeholder {
        text-align: center;
        color: $text-muted;
        padding: 4;
    }

    .loading-status {
        padding: 2;
    }
    """

    def __init__(self, *args, **kwargs):
        """Initialize the data screen."""
        super().__init__(*args, **kwargs)
        self._current_db: Path | None = None

    def compose(self) -> ComposeResult:
        """Compose the data screen layout."""
        # Left panel: Database tree
        with Vertical(id="db-tree-pane"):
            yield DatabaseTree(id="db-tree")

        # Right panel: Data explorer (tree + viewer)
        with Vertical(id="data-explorer-pane"):
            yield Static("Select a database from the tree", id="db-info")
            with Horizontal(id="data-browser"):
                with Vertical(id="data-tree-pane"):
                    yield Static(
                        "Select a database to browse",
                        classes="placeholder",
                    )
                with Vertical(id="data-viewer-pane"):
                    yield Static(
                        "Select a file to view",
                        classes="placeholder",
                    )

    def on_database_selected(self, event: DatabaseSelected) -> None:
        """Handle database selection from the tree."""
        # Update info bar immediately
        info = self.query_one("#db-info", Static)
        info.update(f"[bold]{event.project_name}[/bold] / {event.run_date} / {event.db_path.name}")

        # Load the database directly
        self._load_database(event.db_path, event.project_name, event.run_date)

    def _load_database(self, db_path: Path, project_name: str, run_date: str) -> None:
        """Load a SQLiteFS database into the browser.

        Args:
            db_path: Path to SQLite database file
            project_name: Name of the project
            run_date: Run date folder
        """
        import time

        # Get panes
        tree_pane = self.query_one("#data-tree-pane")
        viewer_pane = self.query_one("#data-viewer-pane")

        # Clear existing content
        tree_pane.remove_children()
        viewer_pane.remove_children()

        # Validate database has 'files' table before loading
        if not is_sqlitefs_database(db_path):
            tree_pane.mount(
                Static(f"[red]Error:[/red] {db_path.name} is not a SQLiteFS database", classes="placeholder")
            )
            return

        self._current_db = db_path

        # Generate unique IDs based on timestamp to avoid duplicates
        unique_suffix = str(int(time.time() * 1000))[-6:]

        # Load tree
        try:
            from tools.sqlitefs_explorer.backend import LazyTreeBackend
            from tools.sqlitefs_explorer.widgets.tree import VirtualFSTree
            from tools.sqlitefs_explorer.widgets.viewer import JSONViewer

            backend = LazyTreeBackend(str(db_path))
            tree = VirtualFSTree(backend, id=f"data-tree-{unique_suffix}")
            tree_pane.mount(tree)

            viewer = JSONViewer(id=f"data-viewer-{unique_suffix}")
            viewer_pane.mount(viewer)

        except Exception as e:
            tree_pane.mount(
                Static(f"[red]Error loading database:[/red]\n{e}", classes="placeholder")
            )
            import traceback
            self.log.error(f"Database load error: {traceback.format_exc()}")

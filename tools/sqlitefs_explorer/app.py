"""Main Textual App for SQLiteFS Explorer."""

import json
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from tools.sqlitefs_explorer.backend import LazyTreeBackend
from tools.sqlitefs_explorer.widgets.tree import FileSelected, VirtualFSTree
from tools.sqlitefs_explorer.widgets.viewer import JSONViewer


def format_size(size: int) -> str:
    """Format byte size to human readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


class StatusBar(Static):
    """Status bar showing current path, file count, and size."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        dock: bottom;
        background: $primary-darken-2;
        color: $text;
        padding: 0 1;
    }
    """

    def __init__(
        self,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        super().__init__(name=name, id=id, classes=classes)
        self._path = ""
        self._file_count = 0
        self._db_size = 0

    def set_info(self, path: str = "", file_count: int = 0, db_size: int = 0) -> None:
        """Update status bar information."""
        self._path = path
        self._file_count = file_count
        self._db_size = db_size
        self.refresh()

    def render(self) -> str:
        """Render the status bar."""
        path_display = self._path or "(root)"
        return (
            f"Path: {path_display} | "
            f"Files: {self._file_count:,} | "
            f"Size: {format_size(self._db_size)}"
        )


class SQLiteFSExplorerApp(App[None]):
    """Terminal UI for exploring SQLiteFS databases.

    Features:
    - Tree navigation with lazy loading
    - JSON viewer with syntax highlighting
    - Status bar with path, file count, and size

    Attributes:
        db_path: Path to the SQLite database file
    """

    CSS = """
    Screen {
        layout: vertical;
    }

    #main-container {
        layout: horizontal;
        height: 1fr;
    }

    #tree-pane {
        width: 40%;
        border-right: solid $primary-darken-2;
    }

    #viewer-pane {
        width: 60%;
    }

    VirtualFSTree {
        height: 100%;
    }

    JSONViewer {
        height: 100%;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("?", "help", "Help"),
    ]

    TITLE = "SQLiteFS Explorer"

    def __init__(self, db_path: str):
        """Initialize the app.

        Args:
            db_path: Path to SQLiteFS database file

        Raises:
            FileNotFoundError: If database file does not exist
        """
        super().__init__()

        # Validate database exists
        if not Path(db_path).exists():
            raise FileNotFoundError(f"Database file not found: {db_path}")

        self.db_path = db_path
        self.backend = LazyTreeBackend(db_path)
        self._current_path = ""

    def compose(self) -> ComposeResult:
        """Compose the app layout."""
        yield Header()

        with Horizontal(id="main-container"):
            with Vertical(id="tree-pane"):
                yield VirtualFSTree(self.backend, id="tree")

            with Vertical(id="viewer-pane"):
                yield JSONViewer(id="viewer")

        yield StatusBar(id="status")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize app state on mount."""
        # Update status bar with initial stats
        stats = self.backend.get_db_stats()
        status = self.query_one("#status", StatusBar)
        status.set_info(
            path="",
            file_count=stats["file_count"],
            db_size=stats["db_size"],
        )

        # Set app title
        self.title = f"SQLiteFS Explorer - {Path(self.db_path).name}"

    def on_file_selected(self, event: FileSelected) -> None:
        """Handle file selection from tree."""
        viewer = self.query_one("#viewer", JSONViewer)
        status = self.query_one("#status", StatusBar)

        self._current_path = event.path

        if event.is_directory:
            # For directories, just show info
            count = self.backend.get_child_count(event.path)
            viewer.set_data(
                {
                    "type": "directory",
                    "path": event.path,
                    "file_count": count,
                }
            )
            status.set_info(
                path=event.path,
                file_count=count,
                db_size=self.backend.get_db_stats()["db_size"],
            )
        else:
            # For files, load and display content
            data = self.backend.get_file_data(event.path)
            if data is None:
                viewer.set_error("File not found in database")
            else:
                try:
                    parsed = json.loads(data.decode("utf-8"))
                    viewer.set_data(parsed, warn_truncation=True)
                except json.JSONDecodeError as e:
                    # Try to show raw content for non-JSON files
                    try:
                        text = data.decode("utf-8")
                        viewer.set_data({"raw_content": text[:10000]})
                    except UnicodeDecodeError:
                        viewer.set_error(f"Cannot decode file: {e}")
                except UnicodeDecodeError:
                    viewer.set_error("Cannot decode file content (binary data)")

            stats = self.backend.get_db_stats()
            status.set_info(
                path=event.path,
                file_count=stats["file_count"],
                db_size=stats["db_size"],
            )

    def action_refresh(self) -> None:
        """Refresh the tree."""
        tree = self.query_one("#tree", VirtualFSTree)
        tree.refresh_tree()

        # Update status
        stats = self.backend.get_db_stats()
        status = self.query_one("#status", StatusBar)
        status.set_info(
            path=self._current_path,
            file_count=stats["file_count"],
            db_size=stats["db_size"],
        )

    def action_help(self) -> None:
        """Show help information."""
        viewer = self.query_one("#viewer", JSONViewer)
        viewer.set_data(
            {
                "help": {
                    "navigation": {
                        "up/down": "Navigate tree",
                        "enter": "Expand/collapse directory or view file",
                        "left/right": "Collapse/expand directory",
                    },
                    "commands": {
                        "q": "Quit",
                        "r": "Refresh tree",
                        "?": "Show this help",
                    },
                }
            }
        )

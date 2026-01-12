"""Main Textual App for SQLiteFS Explorer."""

import json
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import Footer, Header, Static

from tools.sqlitefs_explorer.backend import LazyTreeBackend
from tools.sqlitefs_explorer.models import FilterConfig
from tools.sqlitefs_explorer.widgets.filter import FilterModal
from tools.sqlitefs_explorer.widgets.search import ContentSearchModal, PathSearchModal
from tools.sqlitefs_explorer.widgets.tree import (
    DisplaySettings,
    FileSelected,
    VirtualFSTree,
)
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
        self._filter_active = False
        self._display_settings: DisplaySettings | None = None

    def set_info(
        self,
        path: str = "",
        file_count: int = 0,
        db_size: int = 0,
        filter_active: bool = False,
        display_settings: DisplaySettings | None = None,
    ) -> None:
        """Update status bar information."""
        self._path = path
        self._file_count = file_count
        self._db_size = db_size
        self._filter_active = filter_active
        self._display_settings = display_settings
        self.refresh()

    def render(self) -> str:
        """Render the status bar."""
        path_display = self._path or "(root)"
        parts = [
            f"Path: {path_display}",
            f"Files: {self._file_count:,}",
            f"Size: {format_size(self._db_size)}",
        ]

        if self._filter_active:
            parts.append("[yellow]FILTER[/yellow]")

        if self._display_settings:
            indicators = []
            if self._display_settings.show_size:
                indicators.append("S")
            if self._display_settings.show_date:
                indicators.append("D")
            if indicators:
                parts.append(f"[{'/'.join(indicators)}]")

        return " | ".join(parts)


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
        overflow: hidden;
    }

    #viewer-pane {
        width: 60%;
        height: 100%;
    }

    #tree-scroll {
        height: 100%;
        scrollbar-gutter: stable;
        overflow-x: scroll;
        overflow-y: scroll;
    }

    VirtualFSTree {
        height: auto;
        width: auto;
    }

    JSONViewer {
        height: 1fr;
        width: 100%;
    }
    """

    BINDINGS = [
        # General
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("?", "help", "Help"),
        # Pane focus
        Binding("1", "focus_tree", "Focus Tree", show=False),
        Binding("2", "focus_viewer", "Focus Viewer", show=False),
        Binding("tab", "toggle_focus", "Switch Pane"),
        # Metadata display toggles
        Binding("s", "toggle_size", "Toggle Size"),
        Binding("d", "toggle_date", "Toggle Date"),
        Binding("m", "toggle_metadata", "Toggle All Metadata"),
        Binding("S", "cycle_size_format", "Cycle Size Format", show=False),
        # Search
        Binding("/", "search_path", "Search"),
        Binding("ctrl+f", "search_path", "Search", show=False),
        Binding("ctrl+g", "search_content", "Content Search"),
        # Filter
        Binding("f", "open_filter", "Filter"),
        Binding("F", "clear_filter", "Clear Filter", show=False),
        # Scroll (when viewer focused)
        Binding("left", "scroll_left", "Scroll Left", show=False),
        Binding("right", "scroll_right", "Scroll Right", show=False),
    ]

    TITLE = "SQLiteFS Explorer"

    # Size format cycle order
    SIZE_FORMATS = ["human", "bytes", "kb", "mb", "gb"]

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
        self._display_settings = DisplaySettings()
        self._active_filter: FilterConfig | None = None
        self._search_results: list[str] = []
        self._search_index = 0

    def compose(self) -> ComposeResult:
        """Compose the app layout."""
        yield Header()

        with Horizontal(id="main-container"):
            with Vertical(id="tree-pane"):
                with ScrollableContainer(id="tree-scroll"):
                    yield VirtualFSTree(self.backend, id="tree")

            with Vertical(id="viewer-pane"):
                yield JSONViewer(id="viewer")

        yield StatusBar(id="status")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize app state on mount."""
        # Sync display settings to tree widget
        self._update_tree_settings()

        # Update status bar with initial stats
        stats = self.backend.get_db_stats()
        status = self.query_one("#status", StatusBar)
        status.set_info(
            path="",
            file_count=stats["file_count"],
            db_size=stats["db_size"],
            display_settings=self._display_settings,
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
                        "left/right": "Collapse/expand directory or scroll viewer",
                        "tab": "Switch between tree and viewer pane",
                        "1/2": "Focus tree/viewer pane",
                        "pageup/pagedown": "Scroll viewer content",
                    },
                    "metadata": {
                        "s": "Toggle size display",
                        "d": "Toggle date display",
                        "m": "Toggle all metadata",
                        "S": "Cycle size format (human/B/KB/MB/GB)",
                    },
                    "search": {
                        "/": "Fuzzy path search",
                        "Ctrl+g": "Content search (search in JSON)",
                    },
                    "filter": {
                        "f": "Open filter modal",
                        "F": "Clear all filters",
                    },
                    "commands": {
                        "q": "Quit",
                        "r": "Refresh tree",
                        "?": "Show this help",
                    },
                }
            }
        )

    def action_focus_tree(self) -> None:
        """Focus the tree pane."""
        tree = self.query_one("#tree", VirtualFSTree)
        tree.focus()

    def action_focus_viewer(self) -> None:
        """Focus the viewer pane for scrolling."""
        viewer = self.query_one("#viewer", JSONViewer)
        viewer.focus()

    def action_toggle_focus(self) -> None:
        """Toggle focus between tree and viewer."""
        tree = self.query_one("#tree", VirtualFSTree)
        viewer = self.query_one("#viewer", JSONViewer)

        if tree.has_focus:
            viewer.focus()
        else:
            tree.focus()

    def action_scroll_left(self) -> None:
        """Scroll viewer left."""
        viewer = self.query_one("#viewer", JSONViewer)
        viewer.scroll_left(animate=False)

    def action_scroll_right(self) -> None:
        """Scroll viewer right."""
        viewer = self.query_one("#viewer", JSONViewer)
        viewer.scroll_right(animate=False)

    def _update_status(self) -> None:
        """Update status bar with current state."""
        stats = self.backend.get_db_stats()
        status = self.query_one("#status", StatusBar)
        status.set_info(
            path=self._current_path,
            file_count=stats["file_count"],
            db_size=stats["db_size"],
            filter_active=self._active_filter is not None,
            display_settings=self._display_settings,
        )

    # -------------------------------------------------------------------------
    # Metadata display toggles (Phase 2A)
    # -------------------------------------------------------------------------

    def _update_tree_settings(self) -> None:
        """Sync display settings to tree widget."""
        tree = self.query_one("#tree", VirtualFSTree)
        tree.display_settings = self._display_settings

    def action_toggle_size(self) -> None:
        """Toggle size display in tree."""
        self._display_settings = DisplaySettings(
            show_size=not self._display_settings.show_size,
            show_date=self._display_settings.show_date,
            date_format=self._display_settings.date_format,
            size_format=self._display_settings.size_format,
        )
        self._update_tree_settings()
        self._update_status()
        self.notify(f"Size display: {'ON' if self._display_settings.show_size else 'OFF'}")

    def action_toggle_date(self) -> None:
        """Toggle date display in tree."""
        self._display_settings = DisplaySettings(
            show_size=self._display_settings.show_size,
            show_date=not self._display_settings.show_date,
            date_format=self._display_settings.date_format,
            size_format=self._display_settings.size_format,
        )
        self._update_tree_settings()
        self._update_status()
        self.notify(f"Date display: {'ON' if self._display_settings.show_date else 'OFF'}")

    def action_toggle_metadata(self) -> None:
        """Toggle all metadata display."""
        # If both are off, turn both on; otherwise turn both off
        both_on = self._display_settings.show_size and self._display_settings.show_date
        new_state = not both_on
        self._display_settings = DisplaySettings(
            show_size=new_state,
            show_date=new_state,
            date_format=self._display_settings.date_format,
            size_format=self._display_settings.size_format,
        )
        self._update_tree_settings()
        self._update_status()
        self.notify(f"Metadata display: {'ON' if new_state else 'OFF'}")

    def action_cycle_size_format(self) -> None:
        """Cycle through size display formats."""
        current_idx = self.SIZE_FORMATS.index(self._display_settings.size_format)
        next_idx = (current_idx + 1) % len(self.SIZE_FORMATS)
        new_format = self.SIZE_FORMATS[next_idx]
        self._display_settings = DisplaySettings(
            show_size=self._display_settings.show_size,
            show_date=self._display_settings.show_date,
            date_format=self._display_settings.date_format,
            size_format=new_format,
        )
        self._update_tree_settings()
        self._update_status()
        self.notify(f"Size format: {new_format.upper()}")

    # -------------------------------------------------------------------------
    # Search functionality (Phase 2B)
    # -------------------------------------------------------------------------

    def action_search_path(self) -> None:
        """Open path search modal."""
        self.push_screen(
            PathSearchModal(self.backend),
            self._handle_path_search_result,
        )

    def _handle_path_search_result(self, result: str | None) -> None:
        """Handle result from path search modal."""
        if result:
            self._current_path = result
            # Navigate to the selected path in tree
            tree = self.query_one("#tree", VirtualFSTree)
            node = tree._find_node_by_path(result)
            if node:
                tree.select_node(node)
            # Load file content
            is_dir = self.backend.is_directory(result)
            self._load_file_or_directory(result, is_dir)

    def action_search_content(self) -> None:
        """Open content search modal."""
        self.push_screen(
            ContentSearchModal(self.backend, search_type="any"),
            self._handle_content_search_result,
        )

    def _handle_content_search_result(self, results: list[str]) -> None:
        """Handle result from content search modal."""
        if results:
            self._search_results = results
            self._search_index = 0
            self._navigate_to_search_result()
            if len(results) > 1:
                self.notify(f"Found {len(results)} matches. Use n/N to navigate.")

    def _navigate_to_search_result(self) -> None:
        """Navigate to current search result."""
        if not self._search_results:
            return

        path = self._search_results[self._search_index]
        self._current_path = path
        self._load_file_or_directory(path, is_dir=False)

    def _load_file_or_directory(self, path: str, is_dir: bool) -> None:
        """Load and display a file or directory.

        Args:
            path: Path to load
            is_dir: Whether path is a directory
        """
        viewer = self.query_one("#viewer", JSONViewer)

        if is_dir:
            count = self.backend.get_child_count(path)
            viewer.set_data(
                {
                    "type": "directory",
                    "path": path,
                    "file_count": count,
                }
            )
        else:
            data = self.backend.get_file_data(path)
            if data is None:
                viewer.set_error("File not found in database")
            else:
                try:
                    parsed = json.loads(data.decode("utf-8"))
                    viewer.set_data(parsed, warn_truncation=True)
                except json.JSONDecodeError:
                    try:
                        text = data.decode("utf-8")
                        viewer.set_data({"raw_content": text[:10000]})
                    except UnicodeDecodeError:
                        viewer.set_error("Cannot decode file content")
                except UnicodeDecodeError:
                    viewer.set_error("Cannot decode file content (binary data)")

        self._update_status()

    # -------------------------------------------------------------------------
    # Filter functionality (Phase 2C)
    # -------------------------------------------------------------------------

    def action_open_filter(self) -> None:
        """Open filter configuration modal."""
        self.push_screen(
            FilterModal(self._active_filter),
            self._handle_filter_result,
        )

    def _handle_filter_result(self, result: FilterConfig | None) -> None:
        """Handle result from filter modal.

        Args:
            result: FilterConfig if applied, None if cancelled
        """
        if result is None:
            # Cancelled - no change
            return

        # Check if filter is empty (all defaults)
        is_empty = (
            not result.extensions
            and result.min_size is None
            and result.max_size is None
            and result.date_from is None
            and result.date_to is None
            and result.path_pattern is None
        )

        if is_empty:
            self._active_filter = None
            self.notify("Filters cleared")
        else:
            self._active_filter = result
            self.notify("Filter applied")

        self._update_status()
        # Refresh tree to apply filter
        tree = self.query_one("#tree", VirtualFSTree)
        tree.refresh_tree()

    def action_clear_filter(self) -> None:
        """Clear all active filters."""
        if self._active_filter is not None:
            self._active_filter = None
            self._update_status()
            tree = self.query_one("#tree", VirtualFSTree)
            tree.refresh_tree()
            self.notify("Filters cleared")

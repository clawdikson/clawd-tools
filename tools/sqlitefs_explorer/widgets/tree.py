"""Virtual filesystem tree widget with lazy loading."""

from dataclasses import dataclass
from datetime import datetime

from textual.message import Message
from textual.widgets import Tree
from textual.widgets.tree import TreeNode
from textual.worker import get_current_worker
from textual.reactive import reactive
from textual import work

from tools.sqlitefs_explorer.backend import LazyTreeBackend


@dataclass
class DisplaySettings:
    """Settings for tree display metadata.

    Attributes:
        show_size: Whether to display file/directory sizes
        show_date: Whether to display dates
        date_format: strftime format string for dates
        size_format: Size display format ("human", "bytes", "kb", "mb")
    """

    show_size: bool = True
    show_date: bool = True
    date_format: str = "%Y-%m-%d %H:%M"
    size_format: str = "human"


def format_size(size: int, fmt: str = "human") -> str:
    """Format byte size to human-readable string.

    Args:
        size: Size in bytes
        fmt: Format type ("human", "bytes", "kb", "mb", "gb")

    Returns:
        Formatted size string
    """
    if fmt == "bytes":
        return f"{size}B"
    elif fmt == "kb":
        return f"{size / 1024:.1f}KB"
    elif fmt == "mb":
        return f"{size / (1024 * 1024):.1f}MB"
    elif fmt == "gb":
        return f"{size / (1024 ** 3):.1f}GB"
    else:  # human - auto-select unit
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size = size / 1024
        return f"{size:.1f}TB"


def format_date(date_str: str | None, date_format: str = "%Y-%m-%d %H:%M") -> str:
    """Format date string for display.

    Args:
        date_str: ISO or SQLite format date string
        date_format: strftime format string

    Returns:
        Formatted date string, or empty string if invalid
    """
    if not date_str:
        return ""

    try:
        # Handle both ISO and SQLite timestamp formats
        clean_str = date_str.replace("Z", "+00:00").replace(" ", "T")
        dt = datetime.fromisoformat(clean_str)
        return dt.strftime(date_format)
    except (ValueError, AttributeError):
        # Fallback: return first 10 chars if long enough
        if len(date_str) >= 10:
            return date_str[:10]
        return ""


def format_node_label(name: str, metadata: dict, settings: DisplaySettings) -> str:
    """Format tree node label with optional metadata.

    Args:
        name: Node name (file or directory name)
        metadata: Metadata dict with size, newest_update, is_dir, file_count
        settings: Display settings

    Returns:
        Formatted label string with Rich markup for dim metadata
    """
    parts = [name]

    if settings.show_size and metadata.get("size"):
        size_str = format_size(metadata["size"], settings.size_format)
        parts.append(f"[dim]{size_str}[/dim]")

    if settings.show_date and metadata.get("newest_update"):
        date_str = format_date(metadata["newest_update"], settings.date_format)
        parts.append(f"[dim]{date_str}[/dim]")

    if metadata.get("is_dir") and metadata.get("file_count", 0) > 1:
        parts.append(f"[dim]({metadata['file_count']} files)[/dim]")

    return "  ".join(parts)


@dataclass
class ChildrenLoaded(Message):
    """Posted when background loading completes."""

    prefix: str
    children: list[str]
    is_complete: bool = True


@dataclass
class FileSelected(Message):
    """Posted when a file is selected."""

    path: str
    is_directory: bool


@dataclass
class ChildrenLoadedWithMetadata(Message):
    """Posted when background loading with metadata completes."""

    prefix: str
    children: list[dict]  # List of metadata dicts from get_children_with_metadata
    is_complete: bool = True


class VirtualFSTree(Tree[str]):
    """Tree widget with background loading via Textual Workers.

    Uses Textual's Worker API for thread-safe background loading
    of tree nodes from SQLiteFS database.

    Attributes:
        backend: LazyTreeBackend instance for database access
        display_settings: Reactive display settings for metadata
    """

    DEFAULT_CSS = """
    VirtualFSTree {
        background: $surface;
        padding: 1;
    }

    VirtualFSTree > .tree--guides {
        color: $primary-darken-2;
    }

    VirtualFSTree > .tree--cursor {
        background: $accent;
        color: $text;
    }
    """

    # Reactive display settings - tree refreshes when these change
    display_settings: reactive[DisplaySettings] = reactive(DisplaySettings)

    def __init__(
        self,
        backend: LazyTreeBackend,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        """Initialize the tree widget.

        Args:
            backend: LazyTreeBackend for database access
            name: Widget name
            id: Widget ID
            classes: CSS classes
        """
        super().__init__(
            "Database",
            data="",  # Root path is empty string
            name=name,
            id=id,
            classes=classes,
        )
        self.backend = backend
        self._pending_loads: set[str] = set()
        # Cache metadata for each path to avoid re-fetching
        self._metadata_cache: dict[str, dict] = {}

    def on_mount(self) -> None:
        """Load root children when mounted."""
        self.root.expand()
        self._load_children_for_node(self.root)

    def on_tree_node_expanded(self, event: Tree.NodeExpanded[str]) -> None:
        """Handle node expansion by loading children if needed."""
        node = event.node
        path = node.data or ""

        # Skip if already has children or is being loaded
        if len(node.children) > 0 or path in self._pending_loads:
            return

        # Check if this is a directory
        if path and not self.backend.is_directory(path):
            return

        self._load_children_for_node(node)

    def on_tree_node_selected(self, event: Tree.NodeSelected[str]) -> None:
        """Handle node selection - post FileSelected message."""
        node = event.node
        path = node.data or ""

        if not path:
            return

        is_dir = self.backend.is_directory(path)
        self.post_message(FileSelected(path=path, is_directory=is_dir))

    def _load_children_for_node(self, node: TreeNode[str]) -> None:
        """Start background loading of children for a node."""
        path = node.data or ""

        if path in self._pending_loads:
            return

        self._pending_loads.add(path)

        # Add loading indicator
        if len(node.children) == 0:
            node.add_leaf("Loading...", data=None)

        # Start background load
        self.load_children_async(path)

    @work(thread=True, exclusive=True, group="tree_load")
    def load_children_async(self, prefix: str) -> None:
        """Load children in background thread with metadata. Posts message when done.

        Args:
            prefix: Path prefix to load children for
        """
        worker = get_current_worker()

        # Use get_children_with_metadata for full metadata support
        children_with_meta = self.backend.get_children_with_metadata(prefix)

        if worker.is_cancelled:
            return

        # Thread-safe: post_message() is safe from worker threads
        self.post_message(ChildrenLoadedWithMetadata(prefix=prefix, children=children_with_meta))

    def on_children_loaded_with_metadata(self, event: ChildrenLoadedWithMetadata) -> None:
        """Handle loaded children with metadata on main thread (thread-safe)."""
        prefix = event.prefix
        children = event.children

        # Remove from pending
        self._pending_loads.discard(prefix)

        # Find the node for this prefix
        node = self._find_node_by_path(prefix)
        if node is None:
            return

        # Clear loading indicator
        node.remove_children()

        # Add children with metadata
        for child_meta in children:
            child_path = child_meta["path"]
            name = child_meta["name"]
            is_dir = child_meta["is_dir"]

            # Cache metadata for refresh
            self._metadata_cache[child_path] = child_meta

            # Format label with metadata
            label = format_node_label(name, child_meta, self.display_settings)

            if is_dir:
                # Add as expandable node with folder icon
                child_node = node.add(f"[bold]{label}[/bold]", data=child_path)
                child_node.allow_expand = True
            else:
                # Add as leaf
                node.add_leaf(label, data=child_path)

    # Keep old handler for backwards compatibility
    def on_children_loaded(self, event: ChildrenLoaded) -> None:
        """Handle loaded children on main thread (legacy support)."""
        prefix = event.prefix
        children = event.children

        # Remove from pending
        self._pending_loads.discard(prefix)

        # Find the node for this prefix
        node = self._find_node_by_path(prefix)
        if node is None:
            return

        # Clear loading indicator
        node.remove_children()

        # Add children (without metadata - legacy path)
        for child_path in children:
            # Get just the name (last segment)
            if "/" in child_path:
                name = child_path.rsplit("/", 1)[-1]
            else:
                name = child_path

            is_dir = self.backend.is_directory(child_path)

            if is_dir:
                # Add as expandable node with folder icon
                child_node = node.add(f"[bold]{name}[/bold]", data=child_path)
                child_node.allow_expand = True
            else:
                # Add as leaf with file icon
                node.add_leaf(name, data=child_path)

    def watch_display_settings(self, new_settings: DisplaySettings) -> None:
        """Called when display_settings reactive changes. Refresh node labels."""
        self._refresh_node_labels(self.root)

    def _find_node_by_path(self, path: str) -> TreeNode[str] | None:
        """Find a tree node by its path.

        Args:
            path: Path to find (empty string for root)

        Returns:
            TreeNode or None if not found
        """
        if path == "":
            return self.root

        # BFS through tree to find node
        queue = [self.root]
        while queue:
            node = queue.pop(0)
            if node.data == path:
                return node
            queue.extend(node.children)

        return None

    def _refresh_node_labels(self, node: TreeNode[str]) -> None:
        """Recursively refresh labels for all nodes using cached metadata.

        Args:
            node: Starting node to refresh from
        """
        for child in node.children:
            child_path = child.data
            if child_path and child_path in self._metadata_cache:
                meta = self._metadata_cache[child_path]
                name = meta["name"]
                is_dir = meta["is_dir"]

                # Format new label with current settings
                label = format_node_label(name, meta, self.display_settings)

                if is_dir:
                    child.set_label(f"[bold]{label}[/bold]")
                else:
                    child.set_label(label)

            # Recursively refresh children
            if child.children:
                self._refresh_node_labels(child)

    def refresh_tree(self) -> None:
        """Refresh the entire tree."""
        self.backend.clear_cache()
        self._pending_loads.clear()
        self._metadata_cache.clear()
        self.root.remove_children()
        self._load_children_for_node(self.root)

"""Virtual filesystem tree widget with lazy loading."""

from dataclasses import dataclass

from textual.message import Message
from textual.widgets import Tree
from textual.widgets.tree import TreeNode
from textual.worker import get_current_worker
from textual import work

from tools.sqlitefs_explorer.backend import LazyTreeBackend


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


class VirtualFSTree(Tree[str]):
    """Tree widget with background loading via Textual Workers.

    Uses Textual's Worker API for thread-safe background loading
    of tree nodes from SQLiteFS database.

    Attributes:
        backend: LazyTreeBackend instance for database access
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
        """Load children in background thread. Posts message when done.

        Args:
            prefix: Path prefix to load children for
        """
        worker = get_current_worker()

        children = []
        for child in self.backend._iter_children(prefix):
            if worker.is_cancelled:
                return  # Respect cancellation
            children.append(child)

        # Thread-safe: post_message() is safe from worker threads
        self.post_message(ChildrenLoaded(prefix=prefix, children=children))

    def on_children_loaded(self, event: ChildrenLoaded) -> None:
        """Handle loaded children on main thread (thread-safe)."""
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

        # Add children
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

    def refresh_tree(self) -> None:
        """Refresh the entire tree."""
        self.backend.clear_cache()
        self._pending_loads.clear()
        self.root.remove_children()
        self._load_children_for_node(self.root)

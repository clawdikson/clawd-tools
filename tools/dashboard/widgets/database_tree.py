"""Database tree widget - displays projects, runs, and databases.

Shows a hierarchical view with lazy loading:
- Projects (audiobee_*) - loaded immediately (just names)
  - Runs (20*) - loaded when project expanded
    - Databases (*.db with 'files' table) - loaded when run expanded
"""

from __future__ import annotations

import re
from pathlib import Path

from textual.message import Message
from textual.widgets import Tree
from textual.widgets.tree import TreeNode

from tools.dashboard.services.registry import ProjectRegistry
from tools.dashboard.utils.db_validation import is_sqlitefs_database


class DatabaseSelected(Message):
    """Message sent when a database is selected.

    Attributes:
        db_path: Path to the selected database
        project_name: Name of the parent project
        run_date: Run date folder name
    """

    def __init__(self, db_path: Path, project_name: str, run_date: str) -> None:
        super().__init__()
        self.db_path = db_path
        self.project_name = project_name
        self.run_date = run_date


class DatabaseTree(Tree[Path | None]):
    """Tree widget showing projects, runs, and databases with lazy loading.

    Hierarchy:
    - Projects (audiobee_*) - loaded on mount
      - Runs (20YYMMDD) - loaded on project expand
        - Databases (*.db) - loaded on run expand
    """

    DEFAULT_CSS = """
    DatabaseTree {
        height: 100%;
        scrollbar-gutter: stable;
    }
    """

    # Pattern for run date folders
    DATE_PATTERN = re.compile(r"^20\d{6}$")

    def __init__(self, *args, **kwargs):
        """Initialize the database tree."""
        super().__init__("Data Explorer", *args, **kwargs)
        self._registry = ProjectRegistry()
        self._loading_nodes: set[int] = set()  # Track nodes being loaded
        self._db_cache: dict[str, bool] = {}  # Instance-level cache for SQLiteFS validation

    def on_mount(self) -> None:
        """Build the tree when mounted - only project names (fast)."""
        self.root.expand()
        self._load_projects()

    def _load_projects(self) -> None:
        """Load just project names (no scanning inside projects)."""
        projects = self._registry.discover_projects()

        for project in projects:
            # Just add project name - contents loaded on expand
            # data=project.path so we can scan it later
            node = self.root.add(f"{project.name}", data=project.path)
            # Add a placeholder child so the expand arrow shows
            node.add_leaf("[dim]Loading...[/dim]", data=None)

    def on_tree_node_expanded(self, event: Tree.NodeExpanded) -> None:
        """Handle node expansion - load children lazily."""
        node = event.node

        # Skip if already loaded (no placeholder) or currently loading
        if id(node) in self._loading_nodes:
            return

        children = list(node.children)
        if not children:
            return

        # Check if this is a placeholder node (first child has "Loading..." label)
        first_child = children[0]
        if first_child.data is None and "Loading" in str(first_child.label):
            # This node needs to be loaded
            self._loading_nodes.add(id(node))

            if node.parent == self.root:
                # This is a project node - load runs
                self._load_runs_async(node)
            else:
                # This is a run node - load databases
                self._load_databases_async(node)

    def _load_runs_async(self, project_node: TreeNode) -> None:
        """Load run folders for a project in background."""
        project_path = project_node.data
        if not isinstance(project_path, Path):
            return

        # Remove placeholder
        project_node.remove_children()

        # Find run folders synchronously (fast - just directory listing)
        run_folders = []
        try:
            for item in project_path.iterdir():
                if item.is_dir() and self.DATE_PATTERN.match(item.name):
                    run_folders.append(item)
        except PermissionError:
            pass

        if not run_folders:
            project_node.add_leaf("[dim]No runs found[/dim]", data=None)
            self._loading_nodes.discard(id(project_node))
            return

        # Add run nodes with placeholders (sorted newest first)
        for run_folder in sorted(run_folders, reverse=True):
            run_node = project_node.add(run_folder.name, data=run_folder)
            run_node.add_leaf("[dim]Loading...[/dim]", data=None)

        self._loading_nodes.discard(id(project_node))

    def _load_databases_async(self, run_node: TreeNode) -> None:
        """Load databases for a run folder."""
        run_folder = run_node.data
        if not isinstance(run_folder, Path):
            return

        # Remove placeholder
        run_node.remove_children()

        # Find and validate databases
        databases = self._get_sqlitefs_databases(run_folder)

        if not databases:
            run_node.add_leaf("[dim]No databases[/dim]", data=None)
        else:
            for db_path in databases:
                run_node.add_leaf(db_path.name, data=db_path)

        self._loading_nodes.discard(id(run_node))

    def _get_sqlitefs_databases(self, run_folder: Path) -> list[Path]:
        """Get SQLiteFS databases from a run folder.

        Uses cache to avoid re-validating same databases.
        """
        databases = []
        try:
            for db_path in run_folder.rglob("*.db"):
                if self._is_sqlitefs_db(db_path):
                    databases.append(db_path)
        except PermissionError:
            pass
        return sorted(databases, key=lambda p: p.name)

    def _is_sqlitefs_db(self, db_path: Path) -> bool:
        """Check if a database has a 'files' table (SQLiteFS).

        Uses cache to avoid repeated checks.
        """
        cache_key = str(db_path)

        # Check cache first
        if cache_key in self._db_cache:
            return self._db_cache[cache_key]

        # Validate using shared utility
        result = is_sqlitefs_database(db_path)
        self._db_cache[cache_key] = result
        return result

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle tree node selection."""
        node = event.node
        if node.data is not None and isinstance(node.data, Path) and node.data.suffix == ".db":
            # This is a database node - extract project name and run date
            project_name = ""
            run_date = ""

            # Walk up: db -> run -> project
            if node.parent:  # run node
                run_date = str(node.parent.label).split()[0]
                if node.parent.parent:  # project node
                    project_name = str(node.parent.parent.label).split()[0]

            self.post_message(DatabaseSelected(
                db_path=node.data,
                project_name=project_name,
                run_date=run_date,
            ))

    def refresh_tree(self) -> None:
        """Refresh the database tree."""
        self.root.remove_children()
        self._db_cache.clear()
        self._loading_nodes.clear()
        self._registry.refresh()
        self._load_projects()

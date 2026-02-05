"""SQLiteFS Explorer TUI - Terminal UI for exploring SQLiteFS databases.

Usage:
    python -m tools.sqlitefs_explorer <db_path>
"""

from tools.sqlitefs_explorer.app import SQLiteFSExplorerApp
from tools.sqlitefs_explorer.backend import LazyTreeBackend

__all__ = ["SQLiteFSExplorerApp", "LazyTreeBackend"]
__version__ = "0.1.0"

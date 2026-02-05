"""Database validation utilities.

Provides shared functions for validating SQLiteFS databases.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


def is_sqlitefs_database(db_path: Path) -> bool:
    """Check if a database has a 'files' table (SQLiteFS format).

    Args:
        db_path: Path to the SQLite database file

    Returns:
        True if the database has a 'files' table, False otherwise
    """
    conn = None
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='files'"
        )
        return cursor.fetchone() is not None
    except Exception:
        return False
    finally:
        if conn is not None:
            conn.close()

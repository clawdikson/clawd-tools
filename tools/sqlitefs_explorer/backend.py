"""Thread-safe lazy-loading backend for SQLiteFS.

Uses separate read-only connections for worker threads to avoid
lock contention with main SQLiteFS connection.
"""

import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path


class LazyTreeBackend:
    """Thread-safe lazy-loading backend for SQLiteFS.

    IMPORTANT: Uses separate read-only connection for worker threads
    to avoid lock contention with main SQLiteFS connection.

    Attributes:
        db_path: Path to the SQLite database file
    """

    def __init__(self, db_path: str):
        """Initialize the backend.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._children_cache: dict[str, list[str]] = {}
        self._loading: set[str] = set()

    def _get_readonly_conn(self) -> sqlite3.Connection:
        """Create a new read-only connection for worker thread.

        Returns:
            A new SQLite connection in read-only mode
        """
        conn = sqlite3.connect(
            f"file:{self.db_path}?mode=ro",
            uri=True,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        return conn

    def get_children_sync(self, prefix: str) -> list[str]:
        """Get children synchronously. Safe to call from main thread.

        Args:
            prefix: Path prefix to get children for (empty string for root)

        Returns:
            List of child paths
        """
        if prefix not in self._children_cache:
            self._children_cache[prefix] = list(self._iter_children(prefix))
        return self._children_cache[prefix]

    def _iter_children(self, prefix: str) -> Iterator[str]:
        """Stream immediate children (files AND directories) from SQLite.

        Returns unique immediate children under prefix:
        - For "20251230/raw/": returns ["20251230/raw/search", "20251230/raw/details", ...]
        - Distinguishes directories (have children) from files (leaf nodes)

        Args:
            prefix: Path prefix (empty string for root)

        Yields:
            Child path strings
        """
        conn = self._get_readonly_conn()
        try:
            # Normalize prefix: ensure it ends with / for non-root, empty for root
            if prefix:
                normalized = prefix.rstrip("/") + "/"
            else:
                normalized = ""
            prefix_len = len(normalized)

            # Query: Get all unique immediate children under prefix
            # This extracts the first path segment after the prefix
            if normalized:
                # For non-root: find paths starting with prefix
                cursor = conn.execute(
                    """
                    SELECT DISTINCT
                        CASE
                            WHEN instr(substr(path, ?), '/') > 0
                            THEN substr(path, 1, ? + instr(substr(path, ?), '/') - 1)
                            ELSE path
                        END as child_path,
                        CASE
                            WHEN instr(substr(path, ?), '/') > 0 THEN 1
                            ELSE 0
                        END as is_dir
                    FROM files
                    WHERE path LIKE ?
                      AND length(path) > ?
                    ORDER BY is_dir DESC, child_path
                    """,
                    (
                        prefix_len + 1,  # Start position for substr
                        prefix_len,  # Position to cut for directory
                        prefix_len + 1,  # Start position for substr (for instr check)
                        prefix_len + 1,  # Start position for is_dir check
                        f"{normalized}%",  # LIKE pattern
                        prefix_len,  # Ensure path is longer than prefix
                    ),
                )
            else:
                # For root: get top-level entries
                cursor = conn.execute(
                    """
                    SELECT DISTINCT
                        CASE
                            WHEN instr(path, '/') > 0
                            THEN substr(path, 1, instr(path, '/') - 1)
                            ELSE path
                        END as child_path,
                        CASE
                            WHEN instr(path, '/') > 0 THEN 1
                            ELSE 0
                        END as is_dir
                    FROM files
                    ORDER BY is_dir DESC, child_path
                    """
                )

            seen = set()
            for row in cursor:
                child_path = row[0]
                if child_path and child_path not in seen:
                    seen.add(child_path)
                    yield child_path
        finally:
            conn.close()

    def get_child_count(self, prefix: str) -> int:
        """Get count of all files under prefix (recursive).

        Args:
            prefix: Path prefix to count under

        Returns:
            Number of files under this prefix
        """
        conn = self._get_readonly_conn()
        try:
            if prefix:
                normalized = prefix.rstrip("/") + "/"
                pattern = f"{normalized}%"
            else:
                pattern = "%"

            row = conn.execute(
                "SELECT COUNT(*) FROM files WHERE path LIKE ?", (pattern,)
            ).fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    def is_directory(self, path: str) -> bool:
        """Check if path is a directory (has children) vs file (leaf).

        Args:
            path: Path to check

        Returns:
            True if path has children (is a directory), False otherwise
        """
        conn = self._get_readonly_conn()
        try:
            pattern = f"{path.rstrip('/')}/%"
            row = conn.execute(
                "SELECT 1 FROM files WHERE path LIKE ? LIMIT 1", (pattern,)
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    def get_file_data(self, path: str) -> bytes | None:
        """Read file data from database.

        Args:
            path: Path to the file

        Returns:
            File contents as bytes, or None if not found
        """
        conn = self._get_readonly_conn()
        try:
            row = conn.execute(
                "SELECT data FROM files WHERE path = ?", (path,)
            ).fetchone()
            if row:
                data = row[0]
                if isinstance(data, bytes):
                    return data
                elif isinstance(data, str):
                    return data.encode("utf-8")
                else:
                    return bytes(data)
            return None
        finally:
            conn.close()

    def get_db_stats(self) -> dict:
        """Get database statistics.

        Returns:
            Dictionary with file_count, db_size, db_path
        """
        conn = self._get_readonly_conn()
        try:
            row = conn.execute("SELECT COUNT(*) FROM files").fetchone()
            file_count = row[0] if row else 0
        finally:
            conn.close()

        # Get file size from filesystem
        db_size = 0
        if os.path.exists(self.db_path):
            db_size = os.path.getsize(self.db_path)

        return {
            "file_count": file_count,
            "db_size": db_size,
            "db_path": self.db_path,
        }

    def clear_cache(self) -> None:
        """Clear the children cache."""
        self._children_cache.clear()

    def get_file_metadata(self, path: str) -> dict | None:
        """Get metadata for a single file.

        Args:
            path: File path to get metadata for

        Returns:
            Dictionary with path, size, created_at, updated_at or None if not found
        """
        conn = self._get_readonly_conn()
        try:
            row = conn.execute(
                """
                SELECT
                    path,
                    length(data) as size,
                    created_at,
                    updated_at
                FROM files
                WHERE path = ?
                """,
                (path,),
            ).fetchone()
            if row:
                return {
                    "path": row[0],
                    "size": row[1],
                    "created_at": row[2],
                    "updated_at": row[3],
                }
            return None
        finally:
            conn.close()

    def get_children_with_metadata(self, prefix: str) -> list[dict]:
        """Get children with size and date metadata for directory listing.

        Returns aggregated metadata for each immediate child:
        - For directories: total size, file count, newest update, oldest create
        - For files: size, created_at, updated_at

        Args:
            prefix: Path prefix (empty string for root)

        Returns:
            List of child dictionaries sorted by (is_dir DESC, name ASC)
        """
        conn = self._get_readonly_conn()
        try:
            # Normalize prefix
            if prefix:
                normalized = prefix.rstrip("/") + "/"
            else:
                normalized = ""
            prefix_len = len(normalized)

            # Get all files under prefix with metadata
            cursor = conn.execute(
                """
                SELECT
                    path,
                    length(data) as size,
                    created_at,
                    updated_at
                FROM files
                WHERE path LIKE ?
                """,
                (f"{normalized}%" if normalized else "%",),
            )

            # Build children with aggregated metadata
            children: dict[str, dict] = {}

            for row in cursor:
                full_path = row[0]
                relative = full_path[prefix_len:] if normalized else full_path

                # Get immediate child name
                if "/" in relative:
                    child_name = relative.split("/")[0]
                    child_path = f"{normalized}{child_name}" if normalized else child_name
                    is_dir = True
                else:
                    child_name = relative
                    child_path = full_path
                    is_dir = False

                if child_path not in children:
                    children[child_path] = {
                        "path": child_path,
                        "name": child_name,
                        "is_dir": is_dir,
                        "size": 0,
                        "file_count": 0,
                        "newest_update": None,
                        "oldest_create": None,
                    }

                # Aggregate stats
                children[child_path]["size"] += row[1] or 0
                children[child_path]["file_count"] += 1

                # Track newest update
                if row[3]:  # updated_at
                    if children[child_path]["newest_update"] is None:
                        children[child_path]["newest_update"] = row[3]
                    else:
                        children[child_path]["newest_update"] = max(
                            children[child_path]["newest_update"], row[3]
                        )

                # Track oldest creation
                if row[2]:  # created_at
                    if children[child_path]["oldest_create"] is None:
                        children[child_path]["oldest_create"] = row[2]
                    else:
                        children[child_path]["oldest_create"] = min(
                            children[child_path]["oldest_create"], row[2]
                        )

            # Sort: directories first, then by name (case-insensitive)
            return sorted(
                children.values(),
                key=lambda x: (not x["is_dir"], x["name"].lower()),
            )
        finally:
            conn.close()

    def iter_all_paths(self) -> Iterator[str]:
        """Iterate all file paths in database.

        Yields:
            File path strings in sorted order
        """
        conn = self._get_readonly_conn()
        try:
            cursor = conn.execute("SELECT path FROM files ORDER BY path")
            for row in cursor:
                yield row[0]
        finally:
            conn.close()

    def iter_all_files(self) -> Iterator[tuple[str, bytes]]:
        """Iterate all files with content (for content search).

        Yields:
            Tuples of (path, data) where data is bytes
        """
        conn = self._get_readonly_conn()
        try:
            cursor = conn.execute("SELECT path, data FROM files ORDER BY path")
            for row in cursor:
                data = row[1]
                if isinstance(data, bytes):
                    yield row[0], data
                elif isinstance(data, str):
                    yield row[0], data.encode("utf-8")
                else:
                    yield row[0], bytes(data)
        finally:
            conn.close()

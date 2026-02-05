"""Shared state service for cross-terminal coordination.

Uses SQLite to track active scraper runs across multiple terminal sessions.
Enables the dashboard to show all running scrapers regardless of which
terminal started them.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

# Default location for state database
DEFAULT_STATE_DB = Path.home() / ".scraping-toolkit" / "state.db"


class SharedState:
    """SQLite-based state shared across terminals.

    Tracks active scraper runs with heartbeat mechanism to detect
    stale/crashed runs.

    Attributes:
        db_path: Path to the SQLite database file

    Example:
        >>> state = SharedState()
        >>> run_id = state.register_run("audiobee_test", pid=12345)
        >>> state.update_progress(run_id, "search", 0.5, 100)
        >>> runs = state.get_active_runs()
    """

    def __init__(self, db_path: Path | None = None):
        """Initialize shared state.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.scraping-toolkit/state.db
        """
        self.db_path = db_path or DEFAULT_STATE_DB

        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_db()

    def _init_db(self) -> None:
        """Create database tables if they don't exist."""
        conn = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project TEXT NOT NULL,
                    pid INTEGER NOT NULL,
                    phase TEXT DEFAULT '',
                    progress REAL DEFAULT 0.0,
                    records INTEGER DEFAULT 0,
                    started_at REAL NOT NULL,
                    heartbeat REAL NOT NULL,
                    completed INTEGER DEFAULT 0
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection.

        Returns:
            SQLite connection
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def register_run(self, project: str, pid: int) -> int:
        """Register a new scraper run.

        Args:
            project: Project name (e.g., audiobee_bcbs_il)
            pid: Process ID of the scraper

        Returns:
            Run ID for tracking
        """
        now = time.time()
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                INSERT INTO runs (project, pid, started_at, heartbeat)
                VALUES (?, ?, ?, ?)
                """,
                (project, pid, now, now),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def update_progress(
        self,
        run_id: int,
        phase: str,
        progress: float,
        records: int,
    ) -> None:
        """Update run progress.

        Args:
            run_id: Run ID from register_run
            phase: Current phase name
            progress: Progress as float (0.0 to 1.0)
            records: Number of records processed
        """
        now = time.time()
        conn = self._get_connection()
        try:
            conn.execute(
                """
                UPDATE runs
                SET phase = ?, progress = ?, records = ?, heartbeat = ?
                WHERE id = ?
                """,
                (phase, progress, records, now, run_id),
            )
            conn.commit()
        finally:
            conn.close()

    def heartbeat(self, run_id: int) -> None:
        """Update heartbeat timestamp.

        Should be called periodically to indicate run is still active.

        Args:
            run_id: Run ID to update
        """
        now = time.time()
        conn = self._get_connection()
        try:
            conn.execute(
                "UPDATE runs SET heartbeat = ? WHERE id = ?",
                (now, run_id),
            )
            conn.commit()
        finally:
            conn.close()

    def complete_run(self, run_id: int) -> None:
        """Mark a run as completed.

        Args:
            run_id: Run ID to mark as complete
        """
        conn = self._get_connection()
        try:
            conn.execute(
                "UPDATE runs SET completed = 1 WHERE id = ?",
                (run_id,),
            )
            conn.commit()
        finally:
            conn.close()

    def get_active_runs(self, timeout_seconds: int = 30) -> list[dict[str, Any]]:
        """Get all active runs across terminals.

        Args:
            timeout_seconds: Consider runs stale after this many seconds
                without heartbeat

        Returns:
            List of active run dictionaries
        """
        cutoff = time.time() - timeout_seconds
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT id, project, pid, phase, progress, records,
                       started_at, heartbeat
                FROM runs
                WHERE completed = 0 AND heartbeat > ?
                ORDER BY started_at DESC
                """,
                (cutoff,),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_run(self, run_id: int) -> dict[str, Any] | None:
        """Get a specific run by ID.

        Args:
            run_id: Run ID to retrieve

        Returns:
            Run dictionary or None if not found
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT id, project, pid, phase, progress, records,
                       started_at, heartbeat, completed
                FROM runs
                WHERE id = ?
                """,
                (run_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def cleanup_stale(self, timeout_seconds: int = 300) -> int:
        """Remove stale runs from database.

        Args:
            timeout_seconds: Consider runs stale after this many seconds

        Returns:
            Number of runs removed
        """
        cutoff = time.time() - timeout_seconds
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                DELETE FROM runs
                WHERE completed = 0 AND heartbeat < ?
                """,
                (cutoff,),
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

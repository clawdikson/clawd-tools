"""Data models for SQLiteFS Explorer.

Contains FilterConfig for filtering files and other data classes.
"""

import fnmatch
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal


@dataclass
class FilterConfig:
    """Configuration for file filtering.

    Supports filtering by extension, size range, date range, and path pattern.
    All filters use AND logic - a file must match all active filters.

    Attributes:
        extensions: List of allowed extensions (e.g., [".json", ".jsonl"])
        min_size: Minimum file size in bytes
        max_size: Maximum file size in bytes
        date_from: Minimum date (inclusive)
        date_to: Maximum date (inclusive)
        date_field: Which date field to use ("created" or "updated")
        path_pattern: Glob pattern for path matching
    """

    extensions: list[str] = field(default_factory=list)
    min_size: int | None = None
    max_size: int | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    date_field: Literal["created", "updated"] = "updated"
    path_pattern: str | None = None

    def matches(self, path: str, size: int, created: str, updated: str) -> bool:
        """Check if a file matches all active filters.

        Args:
            path: File path
            size: File size in bytes
            created: Creation timestamp (ISO format or SQLite format)
            updated: Update timestamp (ISO format or SQLite format)

        Returns:
            True if file matches all filters, False otherwise
        """
        # Extension check
        if self.extensions:
            if "." in path:
                ext = "." + path.rsplit(".", 1)[-1]
            else:
                ext = ""
            if ext.lower() not in [e.lower() for e in self.extensions]:
                return False

        # Size check
        if self.min_size is not None and size < self.min_size:
            return False
        if self.max_size is not None and size > self.max_size:
            return False

        # Date check
        if self.date_from or self.date_to:
            date_str = updated if self.date_field == "updated" else created
            try:
                # Handle both ISO and SQLite timestamp formats
                date_str_clean = date_str.replace("Z", "+00:00").replace(" ", "T")
                # Try to parse - may need to add time if not present
                if "T" not in date_str_clean:
                    date_str_clean = date_str + "T00:00:00"
                file_date = datetime.fromisoformat(date_str_clean)
                # Remove timezone info for comparison if present
                if file_date.tzinfo is not None:
                    file_date = file_date.replace(tzinfo=None)

                if self.date_from and file_date < self.date_from:
                    return False
                if self.date_to and file_date > self.date_to:
                    return False
            except (ValueError, AttributeError):
                return False

        # Path pattern check
        if self.path_pattern:
            if not fnmatch.fnmatch(path, self.path_pattern):
                return False

        return True

    @classmethod
    def parse_size(cls, size_str: str) -> int:
        """Parse a size string like '10MB' to bytes.

        Supports: B, KB, MB, GB, TB (case insensitive)
        Supports decimal values (e.g., '1.5MB')
        Supports optional space between number and unit

        Args:
            size_str: Size string (e.g., "10MB", "1.5 GB", "1024")

        Returns:
            Size in bytes

        Raises:
            ValueError: If size_str is invalid
        """
        size_str = size_str.strip()
        match = re.match(r"(\d+(?:\.\d+)?)\s*(B|KB|MB|GB|TB)?", size_str, re.IGNORECASE)
        if not match:
            raise ValueError(f"Invalid size: {size_str}")

        value = float(match.group(1))
        unit = (match.group(2) or "B").upper()

        multipliers = {
            "B": 1,
            "KB": 1024,
            "MB": 1024 ** 2,
            "GB": 1024 ** 3,
            "TB": 1024 ** 4,
        }

        return int(value * multipliers[unit])

    @classmethod
    def parse_date_range(cls, date_str: str) -> tuple[datetime | None, datetime | None]:
        """Parse a date range string.

        Supported formats:
        - "today" - start of today to now
        - "yesterday" - full day yesterday
        - "lastNd" - last N days (e.g., "last7d")
        - "YYYY-MM-DD..YYYY-MM-DD" - explicit range
        - "..YYYY-MM-DD" - up to date
        - "YYYY-MM-DD.." - from date onwards
        - "YYYY-MM-DD" - single day

        Args:
            date_str: Date range string

        Returns:
            Tuple of (start_datetime, end_datetime), either can be None for open range
        """
        now = datetime.now()

        if date_str == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return start, now

        if date_str == "yesterday":
            yesterday = now - timedelta(days=1)
            start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end = yesterday.replace(hour=23, minute=59, second=59, microsecond=0)
            return start, end

        if date_str.startswith("last"):
            match = re.match(r"last(\d+)d", date_str)
            if match:
                days = int(match.group(1))
                start = now - timedelta(days=days)
                return start, now

        if ".." in date_str:
            parts = date_str.split("..")
            start = datetime.fromisoformat(parts[0]) if parts[0] else None
            end = datetime.fromisoformat(parts[1]) if parts[1] else None
            return start, end

        # Single date - return start and end of that day
        date = datetime.fromisoformat(date_str)
        end = date.replace(hour=23, minute=59, second=59, microsecond=0)
        return date, end

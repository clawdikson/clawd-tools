"""DataStore Migration Tool.

High-performance migration between DataStore backends:
- JSON_FILES (individual files on disk)
- SQLITE (SQLite database)
- JSONL (line-delimited JSON)

Optimized for large-scale migrations (100k+ files, 10-50GB data).
"""

from .cli import (
    app,
    migrate_store,
    migrate_json_files_to_sqlite_fast,
    configure_sqlite_for_bulk_insert,
    restore_sqlite_safe_settings,
    detect_backend,
    get_default_output,
    DEFAULT_WORKERS,
    DEFAULT_MAX_IN_FLIGHT,
    DEFAULT_BATCH_MB,
)

__all__ = [
    "app",
    "migrate_store",
    "migrate_json_files_to_sqlite_fast",
    "configure_sqlite_for_bulk_insert",
    "restore_sqlite_safe_settings",
    "detect_backend",
    "get_default_output",
    "DEFAULT_WORKERS",
    "DEFAULT_MAX_IN_FLIGHT",
    "DEFAULT_BATCH_MB",
]

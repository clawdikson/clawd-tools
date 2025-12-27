# DataStore Abstraction Layer for core/io

## Overview

Create a unified abstraction layer in `core/io` that provides a consistent interface for reading/writing JSON records across three storage backends: JSONL, JSON files, and SQLite.

## Problem Statement

Current state:

- `core/io/jsonl.py` - JSONLWriter, JSONLReader for line-based JSON
- `core/io/sqlite_fs.py` - SQLiteFS for virtual filesystem with 15x faster writes
- Individual JSON files - No abstraction, uses raw file I/O

Issues:

1. No unified interface - callers must know which backend to use
2. Different APIs: `JSONLWriter.write()` vs `SQLiteFS.write(path, data)`
3. No configuration-driven backend selection
4. Code duplication in scrapers for different I/O patterns

## Solution: DataStore Protocol

A **filepath-keyed** interface where keys represent logical file paths (e.g., `"search_results/TX_Dallas_1.json"` or `"provider_details/1234567890.json"`). This mirrors how scrapers currently organize raw files but abstracts the underlying storage mechanism.

| Operation           | JSONL                  | JSON Files         | SQLite           |
| ------------------- | ---------------------- | ------------------ | ---------------- |
| `put(path, record)` | Append with path index | Write to path.json | INSERT path,data |
| `get(path)`         | Lookup in index\*      | Read file          | SELECT by path   |
| `exists(path)`      | Check index\*          | Check file exists  | SELECT EXISTS    |
| `__iter__()`        | Read all lines         | Glob + read        | SELECT \*        |
| `keys(pattern)`     | Filter index\*         | Glob pattern       | LIKE query       |

\*JSONL maintains an in-memory path→line_number index for random access

**Key = Filepath**, not record content. Examples:

- `"search_results/TX/Dallas_County/page_1.json"`
- `"provider_details/1234567890.json"` (NPI as filename)
- `"raw/IL_60601_Family_Medicine.json"`

## Module Structure

```
core/io/
├── __init__.py           # Exports: DataStore, create_store, BackendType
├── base.py               # Protocol definitions, BackendType enum
├── jsonl.py              # Existing + JSONLStore implementation
├── sqlite_fs.py          # Existing + SQLiteStore implementation
├── json_files.py         # NEW: JSONFileStore implementation
└── factory.py            # NEW: create_store() factory function
```

## Implementation

### Phase 1: Core Abstractions (base.py)

```python
from enum import Enum
from typing import Protocol, Iterator, Self, Any

class BackendType(Enum):
    JSONL = "jsonl"
    JSON_FILES = "json_files"
    SQLITE = "sqlite"
    AUTO = "auto"

class DataStore(Protocol):
    """Unified interface for storing/retrieving JSON records by filepath."""

    def put(self, path: str, record: dict) -> None:
        """Store record at the given path."""
        ...

    def get(self, path: str) -> dict | None:
        """Retrieve record by path. Returns None if not found."""
        ...

    def exists(self, path: str) -> bool:
        """Check if path exists without loading data."""
        ...

    def __iter__(self) -> Iterator[tuple[str, dict]]:
        """Iterate (path, record) pairs."""
        ...

    def keys(self, pattern: str = "*") -> Iterator[str]:
        """List paths matching glob pattern (e.g., 'provider_details/*.json')."""
        ...

    def __len__(self) -> int:
        """Count of records."""
        ...

    def __enter__(self) -> Self:
        ...

    def __exit__(self, *args) -> None:
        ...

    def flush(self) -> None:
        """Ensure all data is persisted."""
        ...

    def close(self) -> None:
        """Close the store and release resources."""
        ...
```

### Phase 2: Factory Function (factory.py)

```python
from pathlib import Path
from .base import BackendType, DataStore

def create_store(
    base_path: Path | str,
    backend: BackendType = BackendType.AUTO,
    *,
    buffer_size: int = 100,         # For SQLite batching
    read_only: bool = False,        # For reading existing data
) -> DataStore:
    """Create a DataStore with the specified backend.

    Args:
        base_path: Base path for storage:
            - JSONL: Path to .jsonl file (paths stored as JSON field)
            - SQLite: Path to .db file (paths stored as table keys)
            - JSON Files: Directory path (paths become actual files)
        backend: Backend type (auto-detects if AUTO)
        buffer_size: Write buffer size (SQLite only)
        read_only: Open in read-only mode

    Returns:
        DataStore implementation for the chosen backend

    Examples:
        # Auto-detect from extension
        store = create_store("raw_data.jsonl")  # JSONL
        store = create_store("raw_data.db")     # SQLite
        store = create_store("raw_data/")       # JSON files

        # Explicit backend
        store = create_store("raw_data", backend=BackendType.SQLITE)

        # All backends support the same API:
        store.put("provider_details/1234567890.json", provider_data)
        store.put("search_results/TX/Dallas/page_1.json", search_data)
        data = store.get("provider_details/1234567890.json")
    """
    path = Path(path)

    if backend == BackendType.AUTO:
        backend = _auto_select_backend(path)

    match backend:
        case BackendType.JSONL:
            from .jsonl import JSONLStore
            return JSONLStore(path, dedup_key=dedup_key, read_only=read_only)
        case BackendType.JSON_FILES:
            from .json_files import JSONFileStore
            return JSONFileStore(path, read_only=read_only)
        case BackendType.SQLITE:
            from .sqlite_fs import SQLiteStore
            return SQLiteStore(path, buffer_size=buffer_size, read_only=read_only)

def _auto_select_backend(path: Path) -> BackendType:
    """Auto-select backend based on path."""
    if path.suffix == ".jsonl":
        return BackendType.JSONL
    if path.suffix in (".db", ".sqlite", ".sqlite3"):
        return BackendType.SQLITE
    if path.is_dir() or (not path.exists() and not path.suffix):
        return BackendType.JSON_FILES
    return BackendType.JSONL  # Default
```

### Phase 3: JSONL Backend (jsonl.py additions)

```python
class JSONLStore:
    """DataStore implementation using JSONL file storage.

    Each record is stored as a JSON line with a "_path" field for the filepath key.
    The path is used for deduplication and retrieval.
    """

    PATH_FIELD = "_path"  # Internal field to store filepath

    def __init__(
        self,
        jsonl_path: Path,
        read_only: bool = False,
    ):
        self.jsonl_path = Path(jsonl_path)
        self.read_only = read_only
        self._paths: BoundedSet = BoundedSet(max_size=100_000)
        self._file = None
        self._loaded = False

    def put(self, path: str, record: dict) -> None:
        if self.read_only:
            raise IOError("Store is read-only")

        # Skip if already exists
        if path in self._paths:
            return

        # Open file for appending
        if self._file is None:
            self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
            self._file = open(self.jsonl_path, "ab")

        # Add path field and write
        record_with_path = {self.PATH_FIELD: path, **record}
        self._file.write(orjson.dumps(record_with_path) + b"\n")
        self._paths.add(path)

    def get(self, path: str) -> dict | None:
        """Get record by path. Note: Requires loading index if not cached."""
        self._ensure_loaded()
        if path not in self._paths:
            return None

        # Scan file for matching path
        with open(self.jsonl_path, "rb") as f:
            for line in f:
                record = orjson.loads(line)
                if record.get(self.PATH_FIELD) == path:
                    del record[self.PATH_FIELD]  # Remove internal field
                    return record
        return None

    def exists(self, path: str) -> bool:
        self._ensure_loaded()
        return path in self._paths

    def __iter__(self) -> Iterator[tuple[str, dict]]:
        if not self.jsonl_path.exists():
            return
        with open(self.jsonl_path, "rb") as f:
            for line in f:
                if not line.strip():
                    continue
                record = orjson.loads(line)
                path = record.pop(self.PATH_FIELD, None)
                if path:
                    yield path, record

    def _ensure_loaded(self) -> None:
        """Load path index from existing file."""
        if self._loaded:
            return
        if self.jsonl_path.exists():
            with open(self.jsonl_path, "rb") as f:
                for line in f:
                    if line.strip():
                        record = orjson.loads(line)
                        path = record.get(self.PATH_FIELD)
                        if path:
                            self._paths.add(path)
        self._loaded = True

    def keys(self, pattern: str = "*") -> Iterator[str]:
        self._ensure_loaded()
        import fnmatch
        for path in self._paths:
            if fnmatch.fnmatch(path, pattern):
                yield path

    # ... context manager methods
```

### Phase 4: SQLite Backend (sqlite_fs.py additions)

```python
class SQLiteStore:
    """DataStore implementation using SQLite storage.

    Uses existing SQLiteFS which stores (path, data) pairs in a table.
    Provides O(log n) lookups and efficient iteration.
    """

    def __init__(
        self,
        db_path: Path,
        buffer_size: int = 100,
        read_only: bool = False,
    ):
        self.db_path = Path(db_path)
        self._fs = SQLiteFS(str(db_path), buffer_size=buffer_size)
        self.read_only = read_only

    def put(self, path: str, record: dict) -> None:
        if self.read_only:
            raise IOError("Store is read-only")
        self._fs.write(path, record)

    def get(self, path: str) -> dict | None:
        try:
            return self._fs.read(path)
        except KeyError:
            return None

    def exists(self, path: str) -> bool:
        return path in self._fs

    def __iter__(self) -> Iterator[tuple[str, dict]]:
        for path in self._fs.glob("*"):
            yield path, self._fs.read(path)

    def keys(self, pattern: str = "*") -> Iterator[str]:
        return iter(self._fs.glob(pattern))

    def __len__(self) -> int:
        return len(self._fs)

    def flush(self) -> None:
        self._fs.flush()

    def close(self) -> None:
        self._fs.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.flush()
        self.close()
```

### Phase 5: JSON Files Backend (json_files.py - new)

```python
"""JSON file-based DataStore implementation."""

from pathlib import Path
from typing import Iterator
import orjson
import fnmatch

class JSONFileStore:
    """DataStore implementation using individual JSON files.

    Each filepath key becomes an actual file on disk.
    E.g., put("provider_details/123.json", data) creates
    base_dir/provider_details/123.json
    """

    def __init__(self, base_dir: Path, read_only: bool = False):
        self.base_dir = Path(base_dir)
        self.read_only = read_only
        if not read_only:
            self.base_dir.mkdir(parents=True, exist_ok=True)

    def put(self, path: str, record: dict) -> None:
        if self.read_only:
            raise IOError("Store is read-only")

        file_path = self.base_dir / path
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(orjson.dumps(record))

    def get(self, path: str) -> dict | None:
        file_path = self.base_dir / path
        if not file_path.exists():
            return None

        try:
            with open(file_path, "rb") as f:
                return orjson.loads(f.read())
        except (orjson.JSONDecodeError, IOError):
            return None

    def exists(self, path: str) -> bool:
        return (self.base_dir / path).exists()

    def __iter__(self) -> Iterator[tuple[str, dict]]:
        for file_path in self.base_dir.rglob("*.json"):
            # Convert absolute path back to relative path key
            path = str(file_path.relative_to(self.base_dir))
            try:
                with open(file_path, "rb") as f:
                    record = orjson.loads(f.read())
                yield path, record
            except (orjson.JSONDecodeError, IOError):
                continue  # Skip corrupted files

    def keys(self, pattern: str = "*") -> Iterator[str]:
        # Support glob patterns like "provider_details/*.json"
        for file_path in self.base_dir.rglob("*.json"):
            path = str(file_path.relative_to(self.base_dir))
            if fnmatch.fnmatch(path, pattern):
                yield path

    def __len__(self) -> int:
        return sum(1 for _ in self.base_dir.rglob("*.json"))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass  # No cleanup needed for file-based store

    def flush(self) -> None:
        pass  # Files are written immediately

    def close(self) -> None:
        pass
```

## Usage Examples

### Search Phase (write search results with filepath keys)

```python
from core.io import create_store

# Using JSONL backend (auto-detected from .jsonl extension)
with create_store("20251227/raw/search_results.jsonl") as store:
    for state, county, page, results in search_results:
        # Filepath as key
        path = f"search/{state}/{county}/page_{page}.json"
        store.put(path, results)
```

### Details Phase (check exists before fetching)

```python
from core.io import create_store, BackendType

# SQLite backend for efficient exists() checks
with create_store("20251227/raw/provider_details.db", backend=BackendType.SQLITE) as store:
    for npi in npis_to_fetch:
        path = f"provider_details/{npi}.json"
        if not store.exists(path):
            details = await fetch_details(npi)
            store.put(path, details)
```

### Normalize Phase (iterate all raw records)

```python
from core.io import create_store

with create_store("20251227/raw/provider_details.db", read_only=True) as store:
    # Iterate all provider detail files
    for path, record in store:
        mapped = mapper(record)
        output_writer.write(mapped)

    # Or filter by pattern
    for path in store.keys("provider_details/*.json"):
        record = store.get(path)
        # process...
```

### JSON Files Backend (human-readable, debugging)

```python
from core.io import create_store, BackendType

# Each record becomes an actual .json file on disk
with create_store("20251227/raw/", backend=BackendType.JSON_FILES) as store:
    store.put("search/TX/Dallas/page_1.json", search_data)
    # Creates: 20251227/raw/search/TX/Dallas/page_1.json

    store.put("provider_details/1234567890.json", provider_data)
    # Creates: 20251227/raw/provider_details/1234567890.json
```

### Configuration-Driven Selection

```python
from core.config import load_config
from core.io import create_store

config = load_config("healthsparq")
store = create_store(
    base_path=config.output_dir / "raw.db",
    backend=config.storage_backend,  # From SCRAPER_STORAGE_BACKEND env
)
```

## Backend Selection Guidelines

| Use Case                 | Recommended Backend | Reason                         |
| ------------------------ | ------------------- | ------------------------------ |
| Append-only, iterate all | JSONL               | Smallest files, streaming read |
| Need exists() checks     | SQLite              | O(log n) lookups               |
| Human-readable output    | JSON Files          | Easy debugging                 |
| High write throughput    | SQLite              | 15x faster with buffering      |
| Large datasets (>100k)   | SQLite              | Better memory efficiency       |
| Need atomic operations   | SQLite              | ACID transactions              |

## Implementation Tasks

- [ ] Phase 1: Create `base.py` with Protocol and Enum (~50 LOC)
- [ ] Phase 2: Create `factory.py` with create_store() (~60 LOC)
- [ ] Phase 3: Add JSONLStore to `jsonl.py` (~100 LOC)
- [ ] Phase 4: Add SQLiteStore to `sqlite_fs.py` (~80 LOC)
- [ ] Phase 5: Create `json_files.py` with JSONFileStore (~100 LOC)
- [ ] Phase 6: Add async variants for all stores (~100 LOC)
- [ ] Phase 7: Create `test_datastore.py` with parametrized tests (~200 LOC)
- [ ] Phase 8: Update `__init__.py` exports
- [ ] Phase 9: Update documentation

## Backward Compatibility

- All existing exports (JSONLWriter, JSONLReader, SQLiteFS, BoundedSet) remain unchanged
- New DataStore is additive - scrapers can migrate incrementally
- No breaking changes to existing code

## Dependencies

- `orjson` - Already used for JSON serialization
- No new dependencies required

## Estimated Effort

- Implementation: ~600 LOC
- Tests: ~200 LOC
- Documentation: ~100 LOC
- Total: ~900 LOC

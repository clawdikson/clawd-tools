# Database Architecture Documentation

> **Generated**: 2026-01-10
> **Version**: 3.0 (YAGNI Simplified)
> **Location**: `core/io/`

## Overview

The scraping framework uses a **DataStore abstraction layer** that provides unified access to three storage backends. All backends use **filepath-keyed storage** where keys represent logical file paths (e.g., `"provider_details/1234567890.json"`).

This design enables:

- **Backend swapping** without code changes
- **Consistent API** across SQLite, JSONL, and JSON files
- **Performance optimization** based on use case

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Application Layer                           │
│                    (healthsparq, sapphire, scrapers)                │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      create_store() Factory                         │
│                        (factory.py)                                 │
│                                                                     │
│   Auto-detection:  .jsonl → JSONL | .db → SQLite | dir/ → JSON     │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    DataStore Protocol (base.py)                     │
│                                                                     │
│   put(path, record)    →  Store record at logical path              │
│   get(path)            →  Retrieve record by path                   │
│   exists(path)         →  O(1) or O(log n) existence check          │
│   keys(pattern)        →  Glob pattern matching                     │
│   __iter__()           →  Iterate (path, record) pairs              │
│   __len__()            →  Count records                             │
│   flush()              →  Force persist buffered data               │
│   close()              →  Release resources                         │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   SQLiteStore   │ │   JSONLStore    │ │  JSONFileStore  │
│   (sqlite_fs.py)│ │   (jsonl.py)    │ │ (json_files.py) │
│                 │ │                 │ │                 │
│ 15x faster      │ │ Streaming       │ │ Human-readable  │
│ ACID guarantees │ │ Append-only     │ │ Easy debugging  │
│ O(log n) exists │ │ O(1) exists     │ │ O(1) fs stat    │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   SQLite DB     │ │  .jsonl file    │ │   Directory     │
│   (WAL mode)    │ │  (newline JSON) │ │   (JSON files)  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

## Storage Backends

### 1. SQLiteStore (Recommended for Production)

**File**: `core/io/sqlite_fs.py`

**Schema**:

```sql
CREATE TABLE files (
    path TEXT PRIMARY KEY,
    data BLOB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_path_prefix ON files(path);
```

**Performance Optimizations**:

- **WAL Mode**: Write-Ahead Logging for crash safety + concurrent reads
- **PRAGMA synchronous=NORMAL**: Balance safety/performance
- **PRAGMA cache_size=-64000**: 64MB in-memory cache
- **PRAGMA mmap_size=268435456**: 256MB memory-mapped I/O
- **Buffered writes**: Commits every N writes (default: 100)

**Key Features**:
| Feature | Details |
|---------|---------|
| Write throughput | 15x faster than commit-per-write |
| Existence check | O(log n) indexed query |
| Concurrent reads | Yes (WAL mode) |
| ACID guarantees | Yes |
| Max records | Millions (no FS limits) |

**Usage**:

```python
from core.io import BackendType, create_store

# Auto-detect from extension
store = create_store("scraper.db")

# Explicit backend
store = create_store("data", backend=BackendType.SQLITE)

# With buffer size
store = create_store("data.db", buffer_size=200)

# Context manager (auto-flush on exit)
with create_store("data.db") as store:
    store.put("providers/123.json", {"npi": "123"})
```

**Underlying Class: SQLiteFS**

The `SQLiteStore` wraps `SQLiteFS` which provides additional low-level operations:

```python
from core.io import SQLiteFS

fs = SQLiteFS("scraper.db", buffer_size=100)

# Direct write/read
fs.write("path/to/data.json", {"key": "value"})
data = fs.read("path/to/data.json")

# JSONL operations
fs.append_jsonl_line("logs.jsonl", {"event": "start"})
for record in fs.read_jsonl("logs.jsonl"):
    print(record)

# Batch write (fastest)
fs.batch_write(
    [
        ("file1.json", {"id": 1}),
        ("file2.json", {"id": 2}),
    ]
)

# Export to filesystem
fs.export_to_disk(Path("output/"))

# Import from filesystem
fs.import_from_disk(Path("data/"), pattern="**/*.json")
```

### 2. JSONLStore (Streaming/Append-Only)

**File**: `core/io/jsonl.py`

**Storage Format**:

```jsonl
{"_path": "providers/123.json", "npi": "123", "name": "John"}
{"_path": "providers/456.json", "npi": "456", "name": "Jane"}
```

**Key Features**:
| Feature | Details |
|---------|---------|
| Write behavior | Append-only (skips duplicates via BoundedSet) |
| Existence check | O(1) in-memory BoundedSet |
| Memory limit | 100k paths in LRU set |
| Human-readable | Yes (newline-delimited JSON) |
| Streaming | Yes (no full load required) |

**Usage**:

```python
from core.io import create_store

store = create_store("data.jsonl")

# Puts are append-only (duplicates skipped)
store.put("providers/123.json", {"npi": "123"})
store.put("providers/123.json", {"npi": "123"})  # Skipped

# Retrieval requires file scan
data = store.get("providers/123.json")
```

**BoundedSet (Memory-Safe Deduplication)**:

```python
from core.io import BoundedSet

# LRU eviction at capacity
seen = BoundedSet(max_size=100_000)
seen.add("item1")
if "item1" in seen:
    print("Already seen")
```

**Legacy Writer/Reader**:

```python
from core.io import JSONLReader, JSONLWriter

# Write with deduplication
with JSONLWriter("data.jsonl", dedup_key="npi") as writer:
    writer.write({"npi": "123", "name": "John"})

# Read with streaming
with JSONLReader("data.jsonl", skip_invalid_lines=True) as reader:
    for record in reader:
        process(record)
```

### 3. JSONFileStore (Debugging/Human-Readable)

**File**: `core/io/json_files.py`

**Storage Layout**:

```
base_dir/
├── providers/
│   ├── 123.json    → {"npi": "123", "name": "John"}
│   └── 456.json    → {"npi": "456", "name": "Jane"}
└── search/
    └── TX/
        └── Dallas.json
```

**Key Features**:
| Feature | Details |
|---------|---------|
| Write behavior | Overwrites existing file |
| Existence check | O(1) filesystem stat |
| Human-readable | Yes (individual JSON files) |
| Best for | Debugging, < 100k records |

**Usage**:

```python
from core.io import create_store

# Auto-detect from directory path
store = create_store("output/")

# Or trailing slash
store = create_store("output/20251227/")

store.put("providers/123.json", {"npi": "123"})
# Creates: output/providers/123.json
```

## Backend Selection Guide

| Use Case             | Backend      | Reason                         |
| -------------------- | ------------ | ------------------------------ |
| Production scrapers  | `SQLITE`     | 15x faster, ACID, no FS limits |
| Debugging/inspection | `JSON_FILES` | Human-readable files           |
| Streaming/logs       | `JSONL`      | Append-only, simple format     |
| Frequent exists()    | `SQLITE`     | O(log n) indexed query         |
| < 10k records        | Any          | All perform similarly          |
| > 100k records       | `SQLITE`     | Required for performance       |

## Write Behavior Differences

| Backend    | On Duplicate Path              |
| ---------- | ------------------------------ |
| SQLite     | **Upsert** (replaces existing) |
| JSONL      | **Skip** (BoundedSet dedup)    |
| JSON Files | **Overwrite** (file replaced)  |

## Async Support

All backends provide `*_async` variants that run sync operations in a `ThreadPoolExecutor`:

```python
# Async write
await store.put_async("path.json", data)

# Async read
data = await store.get_async("path.json")

# Async exists
if await store.exists_async("path.json"):
    ...
```

**Executor Configuration**:

- 4 worker threads per store type
- Shared executor via module-level singleton
- `atexit` cleanup with `wait=True` for data integrity

## Thread Safety

| Backend       | Thread-Safe | Notes                                   |
| ------------- | ----------- | --------------------------------------- |
| SQLiteStore   | Yes         | Uses `threading.Lock` around connection |
| JSONLStore    | Yes         | File handle protected by lock           |
| JSONFileStore | Partially   | Individual files are atomic             |

## Resource Management

### Context Managers (Recommended)

```python
with create_store("data.db") as store:
    store.put("key", {"value": 1})
    # Auto-flush and close on exit
```

### Manual Cleanup

```python
store = create_store("data.db")
try:
    store.put("key", {"value": 1})
finally:
    store.flush()  # Ensure data written
    store.close()  # Release resources
```

### atexit Cleanup

SQLiteStore registers `atexit` handler to shutdown executor on process exit.

## Performance Benchmarks

Based on production usage (v3.0):

| Operation    | SQLite | JSONL     | JSON Files |
| ------------ | ------ | --------- | ---------- |
| 100k writes  | 2.1s   | 4.8s      | 31.2s      |
| 100k reads   | 1.8s   | 45s\*     | 12.4s      |
| 100k exists  | 0.9s   | 0.01s\*\* | 1.2s       |
| Storage size | 38MB   | 42MB      | 55MB       |

\*JSONL requires file scan for non-sequential reads
\*\*BoundedSet O(1) in-memory check

## Integration with Platform Libraries

### HealthSparq

```python
# In healthsparq phases
from core.io import create_store

store = create_store(f"{curr_date}/raw.db")
store.put(f"search/{state}/{county}.json", results)
```

### Sapphire

```python
# In sapphire pipeline
from core.io import create_store

store = create_store(f"{curr_date}/providers.db")
for provider in providers:
    store.put(f"details/{provider['npi']}.json", provider)
```

## Migration Between Backends

```python
from core.io import BackendType, create_store

# Read from JSONL
source = create_store("data.jsonl", read_only=True)

# Write to SQLite
target = create_store("data.db", backend=BackendType.SQLITE)

for path, record in source:
    target.put(path, record)

target.flush()
```

## Error Handling

```python
from core.io import create_store

store = create_store("data.db", read_only=True)

try:
    store.put("key", {"value": 1})
except OSError as e:
    # "Store is read-only"
    pass
```

## Files Reference

| File            | Purpose                                      |
| --------------- | -------------------------------------------- |
| `base.py`       | DataStore Protocol + BackendType enum        |
| `factory.py`    | `create_store()` factory function            |
| `sqlite_fs.py`  | SQLiteFS + SQLiteStore implementations       |
| `jsonl.py`      | JSONLStore + JSONLWriter/Reader + BoundedSet |
| `json_files.py` | JSONFileStore implementation                 |
| `__init__.py`   | Public API exports                           |

## Related Documentation

- `core/io/CLAUDE.md` - Quick reference for Claude Code
- `core/io/SQLITE_FS.md` - Detailed SQLiteFS documentation
- `core/CLAUDE.md` - Full core package documentation

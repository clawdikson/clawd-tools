# File Utilities Design

**Purpose**: Thread-safe JSON/JSONL read/write with caching, atomic writes, and memory-efficient streaming.

---

## Current Patterns Found

### Existing Implementations

| File | Pattern | Notes |
|------|---------|-------|
| `audiobee_capital_blue/healthspark.py` | FileWriteWorker + Queue | Most sophisticated |
| `audiobee_anthem_new/file_writer.py` | Thread-safe JSONLWriter | Simpler version |
| `audiobee_emblem/core/helpers.py` | Async file operations | aiofiles pattern |
| `audiobee_bcbs_sc_medicaid/index_1.py` | Atomic write (.tmp + rename) | Crash recovery |

### Common Operations

```python
# Reading JSONL (found in 50+ files)
with open(file, 'r') as f:
    for line in f:
        data = orjson.loads(line)

# Writing JSONL (found in 50+ files)
with open(file, 'a') as f:
    f.write(orjson.dumps(data).decode() + '\n')

# JSON caching (found in 30+ files)
if os.path.exists(cache_file):
    return orjson.loads(open(cache_file, 'rb').read())
```

---

## Design Specification

### JSONLReader

```python
# shared/io/jsonl.py

import os
from typing import Iterator, Optional, Callable, Any, List
import orjson


class JSONLReader:
    """
    Memory-efficient JSONL reader with streaming support.

    Features:
    - Generator-based reading (O(1) memory)
    - Error recovery (skip bad lines)
    - Progress callback
    - Line filtering

    Usage:
        reader = JSONLReader("/path/to/data")

        # Stream all records
        for record in reader.read_all("providers.jsonl"):
            process(record)

        # With filter
        for record in reader.read_filtered("providers.jsonl", lambda r: r.get("npi")):
            process(record)

        # Count lines
        count = reader.count_lines("providers.jsonl")
    """

    def __init__(
        self,
        base_dir: str,
        encoding: str = "utf-8",
        skip_errors: bool = True,
    ):
        self.base_dir = base_dir
        self.encoding = encoding
        self.skip_errors = skip_errors
        self._error_count = 0

    def read_all(
        self,
        filename: str,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> Iterator[dict]:
        """
        Stream all records from JSONL file.

        Args:
            filename: File name (relative to base_dir)
            progress_callback: Optional callback(line_number)

        Yields:
            Parsed JSON objects
        """
        filepath = os.path.join(self.base_dir, filename)

        if not os.path.exists(filepath):
            return

        with open(filepath, 'r', encoding=self.encoding) as f:
            for line_num, line in enumerate(f, 1):
                if progress_callback and line_num % 10000 == 0:
                    progress_callback(line_num)

                line = line.strip()
                if not line:
                    continue

                try:
                    yield orjson.loads(line)
                except orjson.JSONDecodeError as e:
                    self._error_count += 1
                    if not self.skip_errors:
                        raise ValueError(f"Line {line_num}: {e}")

    def read_filtered(
        self,
        filename: str,
        predicate: Callable[[dict], bool],
    ) -> Iterator[dict]:
        """
        Stream records matching predicate.

        Args:
            filename: File name
            predicate: Function returning True for records to include

        Yields:
            Matching records
        """
        for record in self.read_all(filename):
            if predicate(record):
                yield record

    def read_batch(
        self,
        filename: str,
        batch_size: int = 1000,
    ) -> Iterator[List[dict]]:
        """
        Stream records in batches.

        Args:
            filename: File name
            batch_size: Records per batch

        Yields:
            Lists of records
        """
        batch = []
        for record in self.read_all(filename):
            batch.append(record)
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    def count_lines(self, filename: str) -> int:
        """Count non-empty lines in file."""
        filepath = os.path.join(self.base_dir, filename)
        if not os.path.exists(filepath):
            return 0

        count = 0
        with open(filepath, 'r', encoding=self.encoding) as f:
            for line in f:
                if line.strip():
                    count += 1
        return count

    def load_all(self, filename: str) -> List[dict]:
        """Load entire file into memory (use with caution)."""
        return list(self.read_all(filename))

    @property
    def error_count(self) -> int:
        """Number of parse errors encountered."""
        return self._error_count
```

### JSONLWriter

```python
# shared/io/jsonl.py (continued)

import threading
import queue
from typing import Optional, Set


class JSONLWriter:
    """
    Thread-safe JSONL writer with buffering and deduplication.

    Features:
    - Thread-safe writes via queue
    - Automatic buffering
    - Optional NPI deduplication
    - Flush on close

    Usage:
        writer = JSONLWriter("/path/to/output")

        # Simple write
        writer.write(record, "providers.jsonl")

        # With deduplication
        writer.write(record, "providers.jsonl", dedup_key="npi")

        # Always close when done
        writer.close()

        # Or use context manager
        with JSONLWriter("/path") as writer:
            writer.write(record, "file.jsonl")
    """

    def __init__(
        self,
        base_dir: str,
        buffer_size: int = 100,
        encoding: str = "utf-8",
    ):
        self.base_dir = base_dir
        self.buffer_size = buffer_size
        self.encoding = encoding

        self._buffers: dict[str, list] = {}
        self._seen_keys: dict[str, Set[str]] = {}
        self._lock = threading.Lock()
        self._counts: dict[str, int] = {}

        os.makedirs(base_dir, exist_ok=True)

    def write(
        self,
        record: dict,
        filename: str,
        dedup_key: Optional[str] = None,
    ) -> bool:
        """
        Write record to JSONL file.

        Args:
            record: Data to write
            filename: Output file name
            dedup_key: Optional key for deduplication (e.g., "npi")

        Returns:
            True if written, False if duplicate
        """
        with self._lock:
            # Deduplication check
            if dedup_key:
                key_value = self._extract_key(record, dedup_key)
                if key_value:
                    if filename not in self._seen_keys:
                        self._seen_keys[filename] = set()
                    if key_value in self._seen_keys[filename]:
                        return False
                    self._seen_keys[filename].add(key_value)

            # Add to buffer
            if filename not in self._buffers:
                self._buffers[filename] = []

            self._buffers[filename].append(record)

            # Flush if buffer full
            if len(self._buffers[filename]) >= self.buffer_size:
                self._flush_file(filename)

            return True

    def _extract_key(self, record: dict, key_path: str) -> Optional[str]:
        """Extract nested key value (supports dot notation)."""
        parts = key_path.split('.')
        value = record
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return str(value) if value else None

    def _flush_file(self, filename: str) -> None:
        """Flush buffer to disk."""
        if filename not in self._buffers or not self._buffers[filename]:
            return

        filepath = os.path.join(self.base_dir, filename)

        with open(filepath, 'ab') as f:
            for record in self._buffers[filename]:
                line = orjson.dumps(record) + b'\n'
                f.write(line)

        if filename not in self._counts:
            self._counts[filename] = 0
        self._counts[filename] += len(self._buffers[filename])

        self._buffers[filename] = []

    def flush(self) -> None:
        """Flush all buffers to disk."""
        with self._lock:
            for filename in list(self._buffers.keys()):
                self._flush_file(filename)

    def close(self) -> None:
        """Flush and close writer."""
        self.flush()

    def get_count(self, filename: str) -> int:
        """Get number of records written to file."""
        return self._counts.get(filename, 0) + len(self._buffers.get(filename, []))

    def __enter__(self) -> 'JSONLWriter':
        return self

    def __exit__(self, *args) -> None:
        self.close()


class AsyncJSONLWriter:
    """
    Async-compatible JSONL writer using background thread.

    Usage:
        async with AsyncJSONLWriter("/path") as writer:
            await writer.write(record, "file.jsonl")
    """

    def __init__(
        self,
        base_dir: str,
        buffer_size: int = 100,
    ):
        self.base_dir = base_dir
        self.buffer_size = buffer_size

        self._queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
        self._worker: Optional[threading.Thread] = None
        self._writer: Optional[JSONLWriter] = None

    def start(self) -> None:
        """Start background writer thread."""
        self._writer = JSONLWriter(self.base_dir, self.buffer_size)
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

    def _worker_loop(self) -> None:
        """Background worker loop."""
        while not self._stop_event.is_set():
            try:
                item = self._queue.get(timeout=0.1)
                if item is None:
                    break
                record, filename, dedup_key = item
                self._writer.write(record, filename, dedup_key)
            except queue.Empty:
                continue

    async def write(
        self,
        record: dict,
        filename: str,
        dedup_key: Optional[str] = None,
    ) -> None:
        """Queue record for writing."""
        self._queue.put((record, filename, dedup_key))

    async def close(self) -> None:
        """Stop worker and flush."""
        self._queue.put(None)
        self._stop_event.set()
        if self._worker:
            self._worker.join(timeout=5.0)
        if self._writer:
            self._writer.close()

    async def __aenter__(self) -> 'AsyncJSONLWriter':
        self.start()
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()
```

### FileManager

```python
# shared/io/file_manager.py

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional
import orjson


def ensure_dir(path: str) -> str:
    """
    Ensure directory exists, create if needed.

    Args:
        path: Directory path

    Returns:
        Absolute path to directory
    """
    os.makedirs(path, exist_ok=True)
    return os.path.abspath(path)


def atomic_write(
    filepath: str,
    data: bytes,
    mode: str = 'wb',
) -> None:
    """
    Write file atomically using tmp + rename pattern.

    Prevents partial writes on crash.

    Args:
        filepath: Target file path
        data: Data to write
        mode: File mode ('wb' for bytes, 'w' for text)
    """
    dir_path = os.path.dirname(filepath)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)

    # Write to temp file
    fd, tmp_path = tempfile.mkstemp(
        suffix='.tmp',
        dir=dir_path or '.',
    )
    try:
        with os.fdopen(fd, mode) as f:
            f.write(data)
        # Atomic rename
        os.replace(tmp_path, filepath)
    except Exception:
        # Clean up on error
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def atomic_json_write(filepath: str, data: dict) -> None:
    """
    Write JSON atomically.

    Args:
        filepath: Target file path
        data: Dictionary to serialize
    """
    atomic_write(filepath, orjson.dumps(data, option=orjson.OPT_INDENT_2))


class JSONCache:
    """
    Simple JSON file cache with TTL support.

    Usage:
        cache = JSONCache("/path/to/cache")

        # Check and load
        data = cache.get("key.json")
        if data is None:
            data = fetch_data()
            cache.set("key.json", data)
    """

    def __init__(
        self,
        base_dir: str,
        default_ttl: Optional[int] = None,  # seconds, None = forever
    ):
        self.base_dir = base_dir
        self.default_ttl = default_ttl
        os.makedirs(base_dir, exist_ok=True)

    def get(
        self,
        key: str,
        ttl: Optional[int] = None,
    ) -> Optional[dict]:
        """
        Get cached value if exists and not expired.

        Args:
            key: Cache key (file name)
            ttl: Override TTL in seconds

        Returns:
            Cached data or None
        """
        filepath = os.path.join(self.base_dir, key)

        if not os.path.exists(filepath):
            return None

        # Check TTL
        check_ttl = ttl if ttl is not None else self.default_ttl
        if check_ttl is not None:
            import time
            age = time.time() - os.path.getmtime(filepath)
            if age > check_ttl:
                return None

        try:
            with open(filepath, 'rb') as f:
                return orjson.loads(f.read())
        except (orjson.JSONDecodeError, IOError):
            return None

    def set(self, key: str, data: dict) -> None:
        """
        Set cached value.

        Args:
            key: Cache key
            data: Data to cache
        """
        filepath = os.path.join(self.base_dir, key)
        atomic_json_write(filepath, data)

    def delete(self, key: str) -> bool:
        """Delete cached value."""
        filepath = os.path.join(self.base_dir, key)
        if os.path.exists(filepath):
            os.unlink(filepath)
            return True
        return False

    def clear(self) -> int:
        """Clear all cached values. Returns count deleted."""
        count = 0
        for f in os.listdir(self.base_dir):
            filepath = os.path.join(self.base_dir, f)
            if os.path.isfile(filepath):
                os.unlink(filepath)
                count += 1
        return count


class FileIndex:
    """
    Track processed files/IDs to enable resume after crash.

    Usage:
        index = FileIndex("/path/to/index.json")

        for item_id in items:
            if index.is_processed(item_id):
                continue
            process(item_id)
            index.mark_processed(item_id)
            index.save()  # Periodic save
    """

    def __init__(self, filepath: str):
        self.filepath = filepath
        self._processed: Set[str] = set()
        self._load()

    def _load(self) -> None:
        """Load index from disk."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'rb') as f:
                    data = orjson.loads(f.read())
                    self._processed = set(data.get("processed", []))
            except (orjson.JSONDecodeError, IOError):
                self._processed = set()

    def save(self) -> None:
        """Save index to disk."""
        atomic_json_write(self.filepath, {
            "processed": list(self._processed),
            "count": len(self._processed),
        })

    def is_processed(self, item_id: str) -> bool:
        """Check if item was processed."""
        return item_id in self._processed

    def mark_processed(self, item_id: str) -> None:
        """Mark item as processed."""
        self._processed.add(item_id)

    def get_pending(self, all_ids: list) -> list:
        """Get IDs not yet processed."""
        return [i for i in all_ids if i not in self._processed]

    @property
    def count(self) -> int:
        """Number of processed items."""
        return len(self._processed)
```

---

## Usage Examples

### Reading JSONL Files

```python
from shared.io import JSONLReader

reader = JSONLReader(config.DIRS["raw"])

# Stream all providers
for provider in reader.read_all("providers.jsonl"):
    process(provider)

# Filter to specific state
il_providers = reader.read_filtered(
    "providers.jsonl",
    lambda p: p.get("state") == "IL"
)

# Batch processing
for batch in reader.read_batch("providers.jsonl", batch_size=1000):
    bulk_insert(batch)
```

### Writing JSONL Files

```python
from shared.io import JSONLWriter

with JSONLWriter(config.DIRS["processed"]) as writer:
    for provider in providers:
        # Deduplicate by NPI
        writer.write(
            provider,
            f"{config.PROJECT_NAME}-{config.CURR_DATE}.jsonl",
            dedup_key="provider.npi"
        )

print(f"Wrote {writer.get_count('...')} records")
```

### Async Writing

```python
from shared.io import AsyncJSONLWriter

async def main():
    async with AsyncJSONLWriter(config.DIRS["raw"]) as writer:
        async for result in fetch_all():
            await writer.write(result, "search_results.jsonl")
```

### JSON Caching

```python
from shared.io import JSONCache

cache = JSONCache(config.DIRS["search_results"])

async def fetch_provider_cached(provider_id: str) -> dict:
    cache_key = f"provider_{provider_id}.json"

    # Try cache
    data = cache.get(cache_key)
    if data is not None:
        return data

    # Fetch and cache
    data = await fetch_provider(provider_id)
    cache.set(cache_key, data)
    return data
```

### Resume Support

```python
from shared.io import FileIndex

index = FileIndex(f"{config.DIRS['raw']}/processed_index.json")

pending = index.get_pending(all_provider_ids)
print(f"Resuming: {len(pending)} remaining of {len(all_provider_ids)}")

for provider_id in tqdm(pending):
    result = await fetch_provider(provider_id)
    save_result(result)
    index.mark_processed(provider_id)

    # Save every 100 items
    if index.count % 100 == 0:
        index.save()

index.save()  # Final save
```

---

## Dependencies

```toml
# shared/pyproject.toml

dependencies = [
    "orjson>=3.9.0",  # Fast JSON
]
```

---

## Migration from Existing Code

### Before

```python
# Manual file writing
with open(output_file, 'a') as f:
    f.write(orjson.dumps(record).decode() + '\n')
```

### After

```python
from shared.io import JSONLWriter

writer = JSONLWriter(config.DIRS["processed"])
writer.write(record, "output.jsonl")
writer.close()
```

Both produce identical output, but the new version:
- Is thread-safe
- Buffers writes for performance
- Handles directory creation
- Supports deduplication

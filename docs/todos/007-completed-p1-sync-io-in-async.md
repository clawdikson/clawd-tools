# P1-PERF-003: Synchronous I/O in Async Context

**Priority:** P1 - Critical
**Category:** Performance
**Component:** core/io/jsonl.py, core/io/sqlite_fs.py
**Status:** COMPLETED

## Problem

All file I/O operations are synchronous, blocking the event loop when called from async contexts. This negates the benefits of async browser/HTTP sessions.

## Resolution

Added async variants to both `SQLiteFS` and `JSONLWriter`/`JSONLReader` using `run_in_executor`:

### SQLiteFS Async Methods (core/io/sqlite_fs.py)

```python
async def write_async(self, path: str, data: dict | list) -> None
async def read_async(self, path: str) -> dict | list | None
async def flush_async(self) -> None
async def exists_async(self, path: str) -> bool
async def delete_async(self, path: str) -> bool
async def append_jsonl_line_async(self, path: str, record: dict) -> None
```

### JSONLWriter Async Methods (core/io/jsonl.py)

```python
async def write_async(self, record: dict) -> bool
async def write_batch_async(self, records: list[dict]) -> tuple[int, int]
async def flush_async(self) -> None
```

### JSONLReader Async Methods (core/io/jsonl.py)

```python
async def read_all_async(self) -> list[dict]
```

### Implementation Details

- Uses shared `ThreadPoolExecutor(max_workers=4)` for each module
- All async methods wrap sync methods with `loop.run_in_executor()`
- Backward compatible - sync methods unchanged
- Thread pool prevents event loop blocking

## Usage Example

```python
import asyncio
from core.io import SQLiteFS

async def fetch_and_store(url: str, fs: SQLiteFS):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            await fs.write_async(f"data/{url_hash}.json", data)
```

## Original Problem Description

`core/io/jsonl.py`:

```python
class JSONLWriter:
    def write(self, data: dict) -> None:
        # Synchronous file write - blocks event loop
        self._file.write(orjson.dumps(data) + b"\n")
```

`core/io/sqlite_fs.py`:

```python
def write(self, path: str, data: dict | list) -> None:
    # Synchronous SQLite write - blocks event loop
    self.conn.execute(...)
    self.conn.commit()
```

## Impact (Before Fix)

- **Async scrapers**: Event loop blocked during I/O, reducing concurrency
- **Browser sessions**: Cannot process other requests while writing
- **Throughput**: 50-70% reduction in effective parallelism

## Related Issues

- P1-PERF-001: SQLite commit-per-write (003-pending-p1-sqlite-commit-per-write.md) - COMPLETED

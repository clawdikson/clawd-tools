---
status: completed
priority: p1
issue_id: "003"
tags: [code-review, performance, shared-package]
dependencies: []
completed_at: 2025-12-27
---

# SQLiteFS Commit-Per-Write Anti-Pattern

## Problem Statement

The `SQLiteFS.write()` method calls `commit()` after every single write operation. This forces a disk sync on each write, making the implementation 10-100x slower than batched commits. At scale (95+ scrapers), this creates severe disk I/O contention.

## Findings

**File:** `shared_package/io/sqlite_fs.py:126`

**Current Implementation:**

```python
def write(self, path: str, data: dict | list) -> None:
    self.conn.execute("""
        INSERT OR REPLACE INTO files (path, data, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    """, (path, orjson.dumps(data)))
    self.conn.commit()  # COMMIT AFTER EVERY SINGLE WRITE
```

**Performance Impact:**

- At 1000 writes/second: ~500ms-1s of unnecessary disk wait time per scraper
- At 95 scrapers: Creates disk I/O contention across all processes
- WAL mode helps but still 10x slower than needed

**Scaling Projections:**
| Scale | Impact |
|-------|--------|
| 1x (current) | 100 files/s acceptable |
| 10x | 1000 files/s - disk becomes bottleneck |
| 100x | 10K files/s - I/O starvation |

## Proposed Solutions

### Option 1: Implement Write Buffer (Recommended)

**Pros:** 5-15x performance improvement, backward compatible API
**Cons:** Slightly more complex, needs flush-on-close logic
**Effort:** Medium (2-3 hours)
**Risk:** Low

```python
class SQLiteFS:
    def __init__(self, db_path, buffer_size: int = 100):
        self._buffer: list[tuple[str, bytes]] = []
        self._buffer_size = buffer_size

    def write(self, path: str, data: dict | list) -> None:
        self._buffer.append((path, orjson.dumps(data)))
        if len(self._buffer) >= self._buffer_size:
            self._flush_buffer()

    def _flush_buffer(self) -> None:
        if self._buffer:
            self.conn.executemany("""
                INSERT OR REPLACE INTO files (path, data, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, self._buffer)
            self.conn.commit()
            self._buffer.clear()

    def close(self) -> None:
        self._flush_buffer()  # Flush remaining on close
        self.conn.close()
```

### Option 2: Remove Auto-Commit, Require Manual flush()

**Pros:** Most control for caller
**Cons:** Breaking API change, callers must remember to flush
**Effort:** Small (1 hour)
**Risk:** Medium - data loss if flush forgotten

### Option 3: Periodic Background Flush

**Pros:** Transparent to callers
**Cons:** More complex, needs thread/async handling
**Effort:** Large (4-6 hours)
**Risk:** Medium

## Recommended Action

**COMPLETED**: Implemented Option 1 (Write Buffer) in `core/io/sqlite_fs.py`:
- Added `_buffer` and `_buffer_size` attributes to SQLiteFS class
- Modified `write()` to buffer writes and auto-flush at buffer_size (default: 100)
- Added `_flush_buffer()` internal method for batched commits
- Added public `flush()` method for explicit flushing
- Updated `read()` and `exists()` to auto-flush buffer for consistency
- Updated `close()` and `__exit__()` to flush on close

## Technical Details

**Affected Files:**

- `shared_package/io/sqlite_fs.py`

**Affected Components:**

- `SQLiteFS.write()` method
- `SQLiteFS.close()` method (needs flush)
- `SQLiteFS.__exit__()` method (needs flush)

**Database Changes:** None

## Acceptance Criteria

- [x] Batched commits (configurable batch size)
- [x] Automatic flush on close/exit
- [x] No data loss on normal shutdown
- [ ] Performance benchmark shows 5x+ improvement (not yet benchmarked)
- [x] Backward compatible API

## Work Log

| Date       | Action                                  | Learnings                                      |
| ---------- | --------------------------------------- | ---------------------------------------------- |
| 2025-12-27 | Created finding from performance review | Commit-per-write identified as main bottleneck |
| 2025-12-27 | Implemented write buffer solution       | Buffer + auto-flush on read/close provides consistency |

## Resources

- Performance review agent findings
- SQLite documentation on transactions
- [SQLite Performance FAQ](https://www.sqlite.org/faq.html#q19)

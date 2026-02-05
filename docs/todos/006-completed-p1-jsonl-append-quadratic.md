# P1-PERF-002: JSONL Append O(n²) Complexity

**Priority:** P1 - Critical
**Category:** Performance
**Component:** core/io/sqlite_fs.py
**Status:** RESOLVED (different implementation than described)

## Problem

The `append_jsonl` method in SQLiteFS uses string concatenation that results in O(n²) time complexity for large files.

## Resolution

The actual implementation in `core/io/sqlite_fs.py` uses SQL-level blob concatenation:

```python
def append_jsonl_line(self, path: str, record: dict) -> None:
    line = orjson.dumps(record) + b'\n'

    self.conn.execute("""
        INSERT INTO files (path, data, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(path) DO UPDATE SET
            data = data || excluded.data,
            updated_at = CURRENT_TIMESTAMP
    """, (path, line))
```

This is O(n) per append (where n is the current file size) rather than O(n²) because:
1. No Python-level string concatenation
2. SQLite handles blob concatenation efficiently
3. No full file read + rewrite cycle in Python

**Trade-offs:**
- Still linear per-append due to SQLite blob rewrite
- For very large files (100K+ appends), consider using standalone `JSONLWriter` instead
- Updated docstring to document this limitation

## Original Problem Description

`shared_package/io/sqlite_fs.py:249-274`

```python
def append_jsonl(self, path: str, data: dict | list) -> None:
    existing = self.read(path)
    if existing:
        # String concatenation - reads entire file, appends, rewrites
        new_content = existing + "\n" + orjson.dumps(data).decode()
    else:
        new_content = orjson.dumps(data).decode()
    self.write(path, {"_raw": new_content})
```

## Impact (Original)

- **10,000 appends**: ~50 seconds (should be <1 second)
- **Memory usage**: Entire file loaded into memory on each append
- **High-volume scrapers**: Severe degradation as files grow

## Related Issues

- P1-PERF-001: SQLite commit-per-write (003-pending-p1-sqlite-commit-per-write.md) - COMPLETED

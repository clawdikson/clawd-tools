# P1-CODE-002: Missing Context Manager on JSONLReader

**Priority:** P1 - Critical
**Category:** Code Quality
**Component:** core/io/jsonl.py
**Status:** COMPLETED

## Problem

`JSONLReader` lacks `__enter__`/`__exit__` methods but is expected to be used as a context manager. This causes AttributeError at runtime.

## Resolution

Added full context manager support to `JSONLReader`:

```python
class JSONLReader:
    def __init__(self, file_path: str | Path, skip_invalid_lines: bool = False):
        self.file_path = Path(file_path)
        self._file = None
        self._skip_invalid_lines = skip_invalid_lines

    def __enter__(self) -> "JSONLReader":
        """Context manager entry - open file for reading."""
        self._file = open(self.file_path, "r", encoding="utf-8")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - ensure file is closed."""
        self.close()

    def close(self) -> None:
        """Close the file if open."""
        if self._file:
            self._file.close()
            self._file = None

    def __iter__(self) -> Iterator[dict[str, Any]]:
        """Iterate over records. Works with or without context manager."""
        if self._file is not None:
            # Using context manager - iterate over open file
            yield from self._iter_file(self._file)
        else:
            # Not using context manager - open file just for this iteration
            with open(self.file_path, "r", encoding="utf-8") as f:
                yield from self._iter_file(f)
```

### Additional Features

- Added `skip_invalid_lines` parameter to skip malformed JSON instead of raising
- Added `read_all_async()` method for async contexts
- Symmetric API with JSONLWriter (both support context manager)

## Usage Examples

```python
# Context manager usage (recommended)
with JSONLReader("data.jsonl") as reader:
    for record in reader:
        process(record)

# Direct usage (also works)
reader = JSONLReader("data.jsonl")
for record in reader:
    process(record)

# Skip invalid lines
reader = JSONLReader("data.jsonl", skip_invalid_lines=True)
records = reader.read_all()  # Silently skips malformed JSON
```

## Original Problem

```python
class JSONLReader:
    def __init__(self, path: Path | str):
        self._path = Path(path)
        # No __enter__/__exit__ defined
```

## Impact (Before Fix)

- **Runtime error**: `AttributeError: __enter__` when used with `with` statement
- **Resource leaks**: File handles may not be properly closed
- **Test failures**: Tests expecting context manager usage will fail

## Related Issues

- JSONLWriter already had proper context manager implementation (now symmetric)

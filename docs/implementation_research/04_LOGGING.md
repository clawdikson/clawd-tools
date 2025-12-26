# Logging Infrastructure Design

**Technology**: loguru (drop-in print() replacement)
**Pattern**: Centralized logger with JSON + console output

---

## Current State

### Problems Found

| Issue | Occurrence | Example |
|-------|------------|---------|
| print() statements | 90%+ files | `print(f"Processing {item}")` |
| Inconsistent format | High | Some use emoji, some don't |
| No structured logs | Most files | Can't parse/aggregate |
| No file logging | Most files | Logs lost on terminal close |

### Existing Logger (Rare)

Found one implementation in `audiobee_emblem/logger/logger.py`:

```python
# Current pattern (stdlib logging)
import logging
from logging.handlers import RotatingFileHandler

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler("app.log", maxBytes=10*1024*1024)
logger.addHandler(handler)
```

---

## Solution: loguru

### Why loguru over stdlib

| Feature | loguru | stdlib |
|---------|--------|--------|
| Setup | 1 line | 10+ lines |
| Structured | Built-in | Manual |
| Colors | Default | Manual |
| Rotation | Built-in | Handler needed |
| print() drop-in | Native | Manual |

---

## Implementation

### ScraperLogger

```python
# shared/logging/logger.py

import sys
from typing import Optional, Any
from pathlib import Path
from loguru import logger as _logger


def configure_logger(
    project_name: str,
    log_dir: Optional[str] = None,
    level: str = "INFO",
    json_output: bool = False,
    rotation: str = "10 MB",
) -> None:
    """
    Configure loguru logger for scraper project.

    Args:
        project_name: Project name for log file naming
        log_dir: Directory for log files (default: logs/)
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        json_output: If True, output JSON format
        rotation: Log rotation size/time

    Usage:
        from shared.logging import configure_logger, logger

        configure_logger("audiobee_bcbs_il", log_dir="20251210/logs")
        logger.info("Starting scrape")
    """
    # Remove default handler
    _logger.remove()

    # Console format
    console_format = (
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # Simple format (like print)
    simple_format = "{level.icon} {message}"

    # JSON format for structured logging
    json_format = (
        '{{"time":"{time:YYYY-MM-DD HH:mm:ss}", '
        '"level":"{level}", '
        '"project":"{extra[project]}", '
        '"message":"{message}", '
        '"module":"{name}", '
        '"function":"{function}", '
        '"line":{line}}}'
    )

    # Add console handler
    if json_output:
        _logger.add(
            sys.stderr,
            format=json_format,
            level=level,
            colorize=False,
        )
    else:
        _logger.add(
            sys.stderr,
            format=simple_format,
            level=level,
            colorize=True,
        )

    # Add file handler if log_dir specified
    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # Main log file
        _logger.add(
            log_path / f"{project_name}.log",
            format=console_format,
            level=level,
            rotation=rotation,
            retention="7 days",
            compression="gz",
        )

        # Error-only log file
        _logger.add(
            log_path / f"{project_name}_errors.log",
            format=console_format,
            level="ERROR",
            rotation=rotation,
            retention="30 days",
        )

        # JSON log for analysis
        _logger.add(
            log_path / f"{project_name}.jsonl",
            format=json_format,
            level=level,
            rotation=rotation,
            serialize=True,
        )

    # Bind project name to all logs
    _logger.configure(extra={"project": project_name})


def get_logger(name: str = None):
    """
    Get configured logger instance.

    Args:
        name: Module name (usually __name__)

    Returns:
        Configured logger

    Usage:
        from shared.logging import get_logger
        logger = get_logger(__name__)
        logger.info("Processing started")
    """
    if name:
        return _logger.bind(module=name)
    return _logger


# Export the logger directly
logger = _logger


class PrintCapture:
    """
    Capture print() statements and redirect to logger.

    Usage:
        # At start of script
        from shared.logging import PrintCapture
        PrintCapture.install()

        # Now print() goes to logger
        print("Hello")  # Logged as INFO
    """

    @staticmethod
    def install(level: str = "INFO"):
        """Install print capture."""
        import builtins
        original_print = builtins.print

        def captured_print(*args, **kwargs):
            message = " ".join(str(a) for a in args)
            # Skip empty prints
            if message.strip():
                _logger.opt(depth=1).log(level, message)

        builtins.print = captured_print

    @staticmethod
    def uninstall():
        """Restore original print."""
        import builtins
        builtins.print = print
```

### Context Managers

```python
# shared/logging/context.py

from contextlib import contextmanager
from time import time
from typing import Optional
from .logger import logger


@contextmanager
def log_duration(operation: str, level: str = "INFO"):
    """
    Log duration of an operation.

    Usage:
        with log_duration("Fetching providers"):
            fetch_providers()
        # Logs: "Fetching providers completed in 2.34s"
    """
    start = time()
    try:
        yield
    finally:
        duration = time() - start
        logger.log(level, f"{operation} completed in {duration:.2f}s")


@contextmanager
def log_operation(
    operation: str,
    start_msg: Optional[str] = None,
    end_msg: Optional[str] = None,
):
    """
    Log start and end of operation.

    Usage:
        with log_operation("Phase 1", "Starting discovery", "Discovery complete"):
            run_discovery()
    """
    logger.info(start_msg or f"Starting {operation}")
    try:
        yield
        logger.info(end_msg or f"{operation} complete")
    except Exception as e:
        logger.error(f"{operation} failed: {e}")
        raise


class ProgressLogger:
    """
    Log progress for long-running operations.

    Usage:
        progress = ProgressLogger("Processing providers", total=1000)
        for item in items:
            process(item)
            progress.update()
        progress.complete()
    """

    def __init__(
        self,
        operation: str,
        total: Optional[int] = None,
        log_interval: int = 100,
    ):
        self.operation = operation
        self.total = total
        self.log_interval = log_interval
        self.count = 0
        self.success = 0
        self.failed = 0
        self.start_time = time()

    def update(self, success: bool = True):
        """Update progress counter."""
        self.count += 1
        if success:
            self.success += 1
        else:
            self.failed += 1

        if self.count % self.log_interval == 0:
            self._log_progress()

    def _log_progress(self):
        elapsed = time() - self.start_time
        rate = self.count / elapsed if elapsed > 0 else 0

        if self.total:
            pct = (self.count / self.total) * 100
            remaining = (self.total - self.count) / rate if rate > 0 else 0
            logger.info(
                f"{self.operation}: {self.count}/{self.total} ({pct:.1f}%) "
                f"| {rate:.1f}/s | ETA: {remaining:.0f}s"
            )
        else:
            logger.info(
                f"{self.operation}: {self.count} processed | {rate:.1f}/s"
            )

    def complete(self):
        """Log completion summary."""
        elapsed = time() - self.start_time
        logger.info(
            f"{self.operation} complete: "
            f"{self.success} success, {self.failed} failed "
            f"in {elapsed:.1f}s"
        )
```

---

## Usage Examples

### Basic Setup

```python
# At top of index_1.py
from shared.logging import configure_logger, logger

configure_logger(
    project_name="audiobee_bcbs_il",
    log_dir="20251210/logs",
    level="INFO",
)

logger.info("Starting Phase 1: Discovery")
logger.debug(f"Using config: {config}")
```

### Drop-in print() Replacement

```python
# BEFORE (existing code)
print(f"Processing {len(items)} items")
print(f"Found {count} providers")
print(f"Error: {error}")

# AFTER (minimal change)
from shared.logging import logger

logger.info(f"Processing {len(items)} items")
logger.info(f"Found {count} providers")
logger.error(f"Error: {error}")
```

### Automatic print() Capture

```python
# Install at script start to capture existing print()
from shared.logging import PrintCapture, configure_logger

configure_logger("audiobee_bcbs_il")
PrintCapture.install()

# Existing code unchanged
print("Hello")  # Now logged as INFO
```

### Structured Logging

```python
from shared.logging import logger

# Add context to logs
logger.bind(provider_id="123", npi="1234567890").info("Processing provider")

# Output: {"time": "...", "level": "INFO", "provider_id": "123", "npi": "1234567890", ...}
```

### Progress Tracking

```python
from shared.logging import ProgressLogger

progress = ProgressLogger("Fetching providers", total=len(provider_ids))

for pid in provider_ids:
    try:
        result = await fetch_provider(pid)
        progress.update(success=True)
    except Exception as e:
        logger.warning(f"Failed {pid}: {e}")
        progress.update(success=False)

progress.complete()
# Output: "Fetching providers complete: 950 success, 50 failed in 120.5s"
```

### Duration Logging

```python
from shared.logging import log_duration

with log_duration("API request"):
    response = await client.get(url)
# Output: "API request completed in 0.34s"
```

---

## Log Levels Guide

| Level | Use For | Example |
|-------|---------|---------|
| DEBUG | Verbose details | `logger.debug(f"Request body: {body}")` |
| INFO | Normal operation | `logger.info("Starting phase 1")` |
| WARNING | Recoverable issues | `logger.warning("Rate limited, retrying")` |
| ERROR | Failures | `logger.error(f"Failed to fetch: {e}")` |
| CRITICAL | Fatal errors | `logger.critical("Cannot connect to API")` |

---

## Migration Strategy

### Phase 1: Add logger alongside print

```python
from shared.logging import configure_logger, logger

configure_logger(...)

# Keep print, add logger
print("Processing...")  # Terminal
logger.info("Processing...")  # File + terminal
```

### Phase 2: Replace print with logger

```python
# Find and replace
# print(f"...") -> logger.info(f"...")
# print(f"Error: ...") -> logger.error(f"...")
```

### Phase 3: Use PrintCapture for legacy code

```python
# For files with many prints
PrintCapture.install()
# All existing print() now logged
```

---

## Output Examples

### Console Output

```
ℹ️ Starting Phase 1: Discovery
ℹ️ Processing providers: 100/1000 (10.0%) | 45.2/s | ETA: 20s
⚠️ Rate limited for provider 12345, retrying...
ℹ️ Processing providers: 200/1000 (20.0%) | 44.8/s | ETA: 18s
✅ Phase 1 complete: 950 success, 50 failed in 22.3s
```

### JSON Log Output (for analysis)

```json
{"time": "2024-12-10 14:30:00", "level": "INFO", "project": "audiobee_bcbs_il", "message": "Starting Phase 1: Discovery"}
{"time": "2024-12-10 14:30:01", "level": "WARNING", "project": "audiobee_bcbs_il", "message": "Rate limited for provider 12345"}
{"time": "2024-12-10 14:30:22", "level": "INFO", "project": "audiobee_bcbs_il", "message": "Phase 1 complete: 950 success, 50 failed"}
```

---

## Dependencies

```toml
# shared/pyproject.toml

dependencies = [
    "loguru>=0.7.0",
]
```

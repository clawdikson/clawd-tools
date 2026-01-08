# DataStore Migration Tool

High-performance migration between DataStore backends, optimized for large-scale data (100k+ files, 10-50GB).

## Quick Start

```bash
# Run as module
python -m tools.migrate_datastore run provider_details/ --to sqlite

# Or directly
python tools/migrate_datastore/cli.py run provider_details/ --to sqlite

# Sapphire project (all phases)
python -m tools.migrate_datastore sapphire molina 20251230
```

## Supported Backends

| Backend | Format | Best For |
|---------|--------|----------|
| `json_files` | Directory of .json files | Debugging, human-readable output |
| `sqlite` | Single .db file | Production, large datasets |
| `jsonl` | Line-delimited JSON | Streaming, append-only logs |

## Commands

### `run` - Generic Migration

Migrate any source to any target backend.

```bash
# Basic: JSON files to SQLite
python -m tools.migrate_datastore run provider_details/ --to sqlite

# With custom output path
python -m tools.migrate_datastore run data/ --to sqlite --output providers.db

# SQLite to JSON (for debugging)
python -m tools.migrate_datastore run data.db --to json_files

# JSONL to SQLite
python -m tools.migrate_datastore run providers.jsonl --to sqlite
```

#### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--to` | `-t` | Target backend: `sqlite`, `json_files`, `jsonl` |
| `--output` | `-o` | Output path (auto-generated if not specified) |
| `--subdirs` | `-s` | Auto-discover and migrate all subdirectories |
| `--include` | `-i` | Include only subdirs matching pattern (fnmatch) |
| `--exclude` | `-e` | Exclude subdirs matching pattern (fnmatch) |
| `--batch` | `-b` | Treat source as glob pattern |
| `--workers` | `-w` | Parallel reader threads (default: 8) |
| `--batch-mb` | | Batch size in MB (default: 128) |
| `--force` | `-f` | Overwrite existing target |
| `--dry-run` | `-n` | Preview without writing |
| `--no-fast` | | Disable parallel mode |

#### Examples

```bash
# Migrate all subdirectories
python -m tools.migrate_datastore run molina/20251230/raw/ --to sqlite --subdirs

# Only provider_* directories
python -m tools.migrate_datastore run molina/20251230/raw/ --to sqlite --subdirs -i "provider_*"

# Exclude networks and affiliations
python -m tools.migrate_datastore run molina/20251230/raw/ --to sqlite --subdirs -e networks -e affiliations

# Batch migrate with glob pattern
python -m tools.migrate_datastore run "*/*/raw/provider_details/" --to sqlite --batch

# High-performance settings
python -m tools.migrate_datastore run data/ --to sqlite --workers 16 --batch-mb 256
```

### `sapphire` - Sapphire Project Migration

One-liner migration for all Sapphire raw directories.

```bash
# Migrate all phases
python -m tools.migrate_datastore sapphire molina 20251230

# Specific phases only
python -m tools.migrate_datastore sapphire molina 20251230 -p provider_details -p locations

# Exclude phases
python -m tools.migrate_datastore sapphire molina 20251230 -e networks -e affiliations

# List available phases
python -m tools.migrate_datastore sapphire molina 20251230 --list-phases
```

#### Available Phases

| Phase | Description |
|-------|-------------|
| `provider_ids` | Provider ID discovery results |
| `provider_details` | Full provider detail records |
| `locations` | Provider location data |
| `affiliations` | Provider affiliations |
| `networks` | Network participation data |

#### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--phase` | `-p` | Specific phase(s) to migrate (can repeat) |
| `--exclude` | `-e` | Phase(s) to exclude (can repeat) |
| `--workers` | `-w` | Parallel reader threads (default: 8) |
| `--batch-mb` | | Batch size in MB (default: 128) |
| `--force` | `-f` | Overwrite existing .db files |
| `--dry-run` | `-n` | Preview without writing |
| `--list-phases` | `-l` | List available phases and exit |

---

## Performance Optimizations

This tool implements several optimizations for large-scale migrations:

### 1. Parallel File Reads

Uses `ThreadPoolExecutor` with bounded in-flight work to prevent memory blowup.

```
Default: 8 workers, max 64 concurrent reads
Tune with: --workers 16
```

### 2. Byte-Based Batching

Batches SQLite commits by total bytes, not record count. This provides consistent memory usage regardless of file size variation.

```
Default: 128MB batches
Tune with: --batch-mb 256
```

### 3. SQLite Bulk PRAGMAs

Configures SQLite for maximum bulk insert performance:

```sql
PRAGMA journal_mode=WAL;
PRAGMA synchronous=OFF;      -- During migration only
PRAGMA temp_store=MEMORY;
PRAGMA cache_size=-200000;   -- 200MB cache
PRAGMA mmap_size=536870912;  -- 512MB memory-mapped I/O
PRAGMA locking_mode=EXCLUSIVE;
```

### 4. Raw Bytes Transfer

For JSON_FILES to SQLite migrations, files are read as raw bytes and stored directly without JSON parsing. This eliminates serialization overhead.

### 5. Throttled Progress Updates

Progress bar updates at most 10 times/second to reduce UI overhead.

---

## Performance Tuning Guide

### Small Datasets (< 10k files, < 1GB)

Default settings work well:

```bash
python -m tools.migrate_datastore run data/ --to sqlite
```

### Medium Datasets (10k-100k files, 1-10GB)

Increase workers and batch size:

```bash
python -m tools.migrate_datastore run data/ --to sqlite --workers 12 --batch-mb 256
```

### Large Datasets (100k+ files, 10-50GB)

Maximum performance settings:

```bash
python -m tools.migrate_datastore run data/ --to sqlite --workers 16 --batch-mb 512
```

### Memory-Constrained Environments

Reduce in-flight work:

```bash
python -m tools.migrate_datastore run data/ --to sqlite --workers 4 --batch-mb 64
```

### Network/Slow Storage

More workers can help overlap I/O:

```bash
python -m tools.migrate_datastore run data/ --to sqlite --workers 24 --batch-mb 64
```

---

## Expected Performance

| Scale | Files | Size | Time (est.) | Rate |
|-------|-------|------|-------------|------|
| Small | 10k | 500MB | 10-30s | 300-1000/s |
| Medium | 100k | 5GB | 2-5min | 300-800/s |
| Large | 500k | 25GB | 10-20min | 400-800/s |

*Performance varies with hardware (SSD vs HDD), file sizes, and system load.*

---

## Programmatic API

Use the migration functions directly in Python:

```python
from pathlib import Path
from tools.migrate_datastore import (
    migrate_store,
    migrate_json_files_to_sqlite_fast,
    configure_sqlite_for_bulk_insert,
    DEFAULT_WORKERS,
    DEFAULT_BATCH_MB,
)
from core.io import BackendType

# High-level migration
records, elapsed = migrate_store(
    source_path=Path("data/provider_details"),
    target_path=Path("data/provider_details.db"),
    target_backend=BackendType.SQLITE,
    workers=16,
    batch_mb=256,
)
print(f"Migrated {records:,} records in {elapsed:.1f}s")

# Low-level fast migration (JSON_FILES to SQLite only)
records, elapsed = migrate_json_files_to_sqlite_fast(
    source_dir=Path("data/provider_details"),
    target_path=Path("data/provider_details.db"),
    workers=16,
    batch_mb=256,
    progress_callback=lambda done, total: print(f"Progress: {done}"),
)
```

---

## Troubleshooting

### "Target already exists"

Use `--force` to overwrite:

```bash
python -m tools.migrate_datastore run data/ --to sqlite --force
```

### Out of Memory

Reduce batch size and workers:

```bash
python -m tools.migrate_datastore run data/ --to sqlite --workers 4 --batch-mb 32
```

### Slow Performance

1. Check if running on SSD (HDD is 10x slower)
2. Increase workers: `--workers 16`
3. Increase batch size: `--batch-mb 256`
4. Exclude antivirus/Spotlight from data directory

### Migration Verification Failed

The tool verifies record counts after migration. If counts don't match:

1. Check for read errors in output
2. Try again with `--force`
3. Check disk space

### Sequential Mode

If parallel mode causes issues, disable it:

```bash
python -m tools.migrate_datastore run data/ --to sqlite --no-fast
```

---

## Directory Structure

```
tools/migrate_datastore/
    __init__.py      # Package exports
    __main__.py      # Module entry point
    cli.py           # CLI implementation
    README.md        # This guide
```

---

## See Also

- `core/io/CLAUDE.md` - DataStore abstraction documentation
- `core/io/sqlite_fs.py` - SQLiteFS implementation
- `core/io/json_files.py` - JSONFileStore implementation
- `sapphire/CLAUDE.md` - Sapphire platform documentation

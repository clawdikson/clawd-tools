#!/usr/bin/env python3
"""Migrate data between DataStore backends.

Supports migration between any combination of:
- JSON_FILES (individual files on disk)
- SQLITE (SQLite database)
- JSONL (line-delimited JSON)

Optimized for large-scale migrations (100k+ files, 10-50GB data):
- Parallel file reads with bounded in-flight work
- Batching by bytes (not record count) for consistent memory usage
- SQLite bulk PRAGMAs for 2-5x faster inserts
- Raw bytes transfer (skip JSON parsing during migration)
- Time-based progress throttling (10 updates/sec max)

Usage:
    # JSON Files to SQLite (primary use case)
    python tools/migrate_datastore.py audiobee_bcbs_il/20251230/raw/ --to sqlite

    # SQLite to JSON Files (for debugging)
    python tools/migrate_datastore.py data.db --to json_files --output data/

    # JSONL to SQLite
    python tools/migrate_datastore.py providers.jsonl --to sqlite --output providers.db

    # Dry run (validate without writing)
    python tools/migrate_datastore.py data/ --to sqlite --dry-run

    # Batch migrate all directories matching pattern
    python tools/migrate_datastore.py "audiobee_*/*/raw/" --to sqlite --batch

    # High-performance migration with tuned settings
    python tools/migrate_datastore.py data/ --to sqlite --workers 16 --batch-mb 128
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import time
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from enum import Enum
from glob import glob
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.io import BackendType, create_store

# Try to import orjson for faster JSON parsing
try:
    import orjson

    def json_loads(data: bytes) -> Any:
        return orjson.loads(data)

    def json_dumps(obj: Any) -> bytes:
        return orjson.dumps(obj)
except ImportError:
    import json

    def json_loads(data: bytes) -> Any:
        return json.loads(data.decode("utf-8"))

    def json_dumps(obj: Any) -> bytes:
        return json.dumps(obj).encode("utf-8")


app = typer.Typer(
    name="migrate-datastore",
    help="Migrate data between DataStore backends (JSON Files, SQLite, JSONL).",
    no_args_is_help=True,
)
console = Console()

# Default performance settings
DEFAULT_WORKERS = 8
DEFAULT_MAX_IN_FLIGHT = 64
DEFAULT_BATCH_MB = 128  # MB
DEFAULT_PROGRESS_INTERVAL = 0.1  # seconds


class TargetBackend(str, Enum):
    """Target backend types for migration."""

    sqlite = "sqlite"
    json_files = "json_files"
    jsonl = "jsonl"


def detect_backend(path: Path) -> BackendType:
    """Detect backend type from path."""
    if path.suffix == ".jsonl":
        return BackendType.JSONL
    if path.suffix in (".db", ".sqlite", ".sqlite3"):
        return BackendType.SQLITE
    if path.is_dir() or (not path.exists() and not path.suffix):
        return BackendType.JSON_FILES
    return BackendType.JSONL


def get_default_output(source: Path, target_backend: BackendType) -> Path:
    """Generate default output path based on target backend."""
    match target_backend:
        case BackendType.SQLITE:
            return source.with_suffix(".db")
        case BackendType.JSON_FILES:
            if source.suffix:
                return source.with_suffix("")  # Remove extension, becomes directory
            return source.parent / f"{source.name}_files"
        case BackendType.JSONL:
            return source.with_suffix(".jsonl")
        case _:
            raise ValueError(f"Unsupported target backend: {target_backend}")


def format_size(bytes_count: float) -> str:
    """Format bytes to human-readable size."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_count < 1024:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024
    return f"{bytes_count:.1f} TB"


def get_store_size(path: Path) -> int:
    """Get total size of a store in bytes."""
    if path.is_file():
        return path.stat().st_size
    if path.is_dir():
        return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return 0


def configure_sqlite_for_bulk_insert(conn: sqlite3.Connection) -> None:
    """Configure SQLite connection for maximum bulk insert performance.

    These settings trade durability during migration for speed.
    Data is still safe as long as migration completes successfully.
    """
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=OFF")  # Faster, safe for bulk loads
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA cache_size=-200000")  # ~200MB cache
    conn.execute("PRAGMA mmap_size=536870912")  # 512MB memory-mapped I/O
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("PRAGMA locking_mode=EXCLUSIVE")  # Single writer optimization


def restore_sqlite_safe_settings(conn: sqlite3.Connection) -> None:
    """Restore safe SQLite settings after bulk insert."""
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA locking_mode=NORMAL")


def migrate_json_files_to_sqlite_fast(
    source_dir: Path,
    target_path: Path,
    *,
    workers: int = DEFAULT_WORKERS,
    max_in_flight: int = DEFAULT_MAX_IN_FLIGHT,
    batch_mb: int = DEFAULT_BATCH_MB,
    dry_run: bool = False,
    progress_callback: Callable[[int, int | None], None] | None = None,
) -> tuple[int, float]:
    """High-performance JSON_FILES to SQLite migration.

    Uses parallel file reads with bounded in-flight work and byte-based batching.
    Transfers raw bytes without JSON parsing for maximum throughput.

    Args:
        source_dir: Directory containing JSON files
        target_path: Path for SQLite database
        workers: Number of reader threads (default: 8)
        max_in_flight: Maximum concurrent reads (default: 64)
        batch_mb: Batch size in MB before SQLite commit (default: 128)
        dry_run: If True, only count files without migrating
        progress_callback: Optional callback(done, total) for progress updates

    Returns:
        Tuple of (records_migrated, elapsed_seconds)
    """
    batch_bytes_limit = batch_mb * 1024 * 1024

    def read_file(path: str) -> tuple[str, bytes]:
        """Read file as raw bytes (no JSON parsing)."""
        with open(path, "rb", buffering=1 << 20) as f:  # 1MB buffer
            return path, f.read()

    # Count files first (fast with os.scandir)
    if dry_run:
        total = sum(1 for e in os.scandir(source_dir) if e.is_file() and e.name.endswith(".json"))
        return total, 0.0

    start_time = time.time()

    # Create target database with bulk settings
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_path), check_same_thread=False)
    configure_sqlite_for_bulk_insert(conn)

    # Create schema
    conn.execute("""
        CREATE TABLE IF NOT EXISTS files (
            path TEXT PRIMARY KEY,
            data BLOB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_path_prefix ON files(path)")
    conn.commit()

    pending: set[Any] = set()
    batch: list[tuple[str, bytes]] = []
    batch_sz = 0
    done = 0
    last_progress_time = time.monotonic()

    try:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            # Stream files using os.scandir (faster than Path.rglob for flat dirs)
            for entry in os.scandir(source_dir):
                if not (entry.is_file() and entry.name.endswith(".json")):
                    continue

                # Bound in-flight work to prevent memory blowup
                while len(pending) >= max_in_flight:
                    finished, pending = wait(pending, return_when=FIRST_COMPLETED)
                    for fut in finished:
                        try:
                            full_path, data = fut.result()
                            # Convert to relative path (just filename)
                            rel_path = os.path.basename(full_path)
                            batch.append((rel_path, data))
                            batch_sz += len(data)
                            done += 1
                        except Exception as e:
                            console.print(f"  [yellow]⚠ Read error: {e}[/]")

                pending.add(executor.submit(read_file, entry.path))

                # Flush batch when size threshold reached
                if batch_sz >= batch_bytes_limit:
                    conn.execute("BEGIN")
                    conn.executemany(
                        "INSERT OR REPLACE INTO files (path, data, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                        batch,
                    )
                    conn.execute("COMMIT")
                    batch.clear()
                    batch_sz = 0

                    # Throttled progress update
                    now = time.monotonic()
                    if progress_callback and now - last_progress_time >= DEFAULT_PROGRESS_INTERVAL:
                        progress_callback(done, None)
                        last_progress_time = now

            # Process remaining pending futures
            for fut in pending:
                try:
                    full_path, data = fut.result()
                    rel_path = os.path.basename(full_path)
                    batch.append((rel_path, data))
                    batch_sz += len(data)
                    done += 1
                except Exception as e:
                    console.print(f"  [yellow]⚠ Read error: {e}[/]")

        # Flush final batch
        if batch:
            conn.execute("BEGIN")
            conn.executemany(
                "INSERT OR REPLACE INTO files (path, data, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                batch,
            )
            conn.execute("COMMIT")

        # Restore safe settings and optimize
        restore_sqlite_safe_settings(conn)
        conn.execute("PRAGMA optimize")

    finally:
        conn.close()

    elapsed = time.time() - start_time

    if progress_callback:
        progress_callback(done, done)  # Final update

    return done, elapsed


def migrate_store(
    source_path: Path,
    target_path: Path,
    target_backend: BackendType,
    *,
    dry_run: bool = False,
    buffer_size: int = 1000,
    workers: int = DEFAULT_WORKERS,
    batch_mb: int = DEFAULT_BATCH_MB,
    fast_mode: bool = True,
) -> tuple[int, float]:
    """Migrate data from source to target store.

    Args:
        source_path: Path to source store
        target_path: Path for target store
        target_backend: Backend type for target
        dry_run: If True, validate without writing
        buffer_size: Write buffer size for SQLite (legacy mode)
        workers: Number of parallel reader threads (fast mode)
        batch_mb: Batch size in MB (fast mode)
        fast_mode: Use optimized parallel migration for JSON_FILES→SQLite

    Returns:
        Tuple of (records_migrated, elapsed_seconds)
    """
    source_backend = detect_backend(source_path)

    console.print(f"\n  Source: [cyan]{source_path}[/] ({source_backend.value})")
    console.print(f"  Target: [cyan]{target_path}[/] ({target_backend.value})")

    # Use fast path for JSON_FILES → SQLite
    use_fast_path = (
        fast_mode
        and source_backend == BackendType.JSON_FILES
        and target_backend == BackendType.SQLITE
        and source_path.is_dir()
    )

    if use_fast_path:
        console.print(
            f"  Mode: [green]Fast (parallel reads, {workers} workers, {batch_mb}MB batches)[/]"
        )

        # Quick file count with os.scandir
        source_size = get_store_size(source_path)

        if dry_run:
            total = sum(
                1 for e in os.scandir(source_path) if e.is_file() and e.name.endswith(".json")
            )
            console.print(
                f"  Files: [green]{total:,}[/] | Size: [green]{format_size(source_size)}[/]"
            )
            console.print("\n  [yellow][DRY RUN][/] Would migrate all JSON files")
            return total, 0.0

        # Check target doesn't exist
        if target_path.exists():
            raise FileExistsError(f"Target already exists: {target_path}")

        # Progress bar with indeterminate total (set later)
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("  Migrating...", total=None)

            def update_progress(done: int, total: int | None):
                if total:
                    progress.update(task, completed=done, total=total)
                else:
                    progress.update(task, completed=done)

            total, elapsed = migrate_json_files_to_sqlite_fast(
                source_path,
                target_path,
                workers=workers,
                batch_mb=batch_mb,
                progress_callback=update_progress,
            )

        # Verify migration
        conn = sqlite3.connect(str(target_path))
        target_count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        conn.close()

        if target_count != total:
            raise RuntimeError(
                f"Migration verification failed: expected {total}, got {target_count}"
            )

        target_size = get_store_size(target_path)
        compression = (1 - target_size / source_size) * 100 if source_size > 0 else 0
        rate = total / elapsed if elapsed > 0 else 0

        console.print(
            f"  [green]✓[/] Migrated {total:,} records in {elapsed:.1f}s ({rate:,.0f} rec/s)"
        )
        console.print(
            f"  Size: {format_size(source_size)} → {format_size(target_size)} "
            f"([{'green' if compression > 0 else 'red'}]{compression:+.1f}%[/])"
        )

        return total, elapsed

    # Fallback to standard migration for other backend combinations
    console.print("  Mode: [yellow]Standard (sequential)[/]")

    # Open source read-only
    with create_store(source_path, backend=source_backend, read_only=True) as source:
        total = len(source)  # type: ignore[arg-type]

        if total == 0:
            console.print("  [yellow]⚠ Source store is empty, nothing to migrate[/]")
            return 0, 0.0

        source_size = get_store_size(source_path)
        console.print(
            f"  Records: [green]{total:,}[/] | Size: [green]{format_size(source_size)}[/]"
        )

        if dry_run:
            console.print("\n  [yellow][DRY RUN][/] Would migrate the following:")
            sample_count = min(5, total)
            for i, (path, _) in enumerate(source):  # type: ignore[union-attr]
                if i >= sample_count:
                    console.print(f"    ... and {total - sample_count:,} more")
                    break
                console.print(f"    - {path}")
            return total, 0.0

        # Check target doesn't exist (safety)
        if target_path.exists():
            if target_path.is_file():
                raise FileExistsError(f"Target already exists: {target_path}")
            if target_path.is_dir() and any(target_path.iterdir()):
                raise FileExistsError(f"Target directory not empty: {target_path}")

        start_time = time.time()

        # Create target and migrate with progress bar
        with create_store(
            target_path,
            backend=target_backend,
            buffer_size=buffer_size,
        ) as target:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("  Migrating...", total=total)
                last_update = time.monotonic()
                batch_done = 0

                for path, record in source:  # type: ignore[union-attr]
                    target.put(path, record)  # type: ignore[union-attr]
                    batch_done += 1

                    # Throttled progress updates (10/sec max)
                    now = time.monotonic()
                    if now - last_update >= DEFAULT_PROGRESS_INTERVAL:
                        progress.update(task, advance=batch_done)
                        batch_done = 0
                        last_update = now

                # Final progress update
                if batch_done > 0:
                    progress.update(task, advance=batch_done)

            target.flush()  # type: ignore[union-attr]

        elapsed = time.time() - start_time

        # Verify migration
        with create_store(target_path, backend=target_backend, read_only=True) as target:
            target_count = len(target)  # type: ignore[arg-type]

        if target_count != total:
            raise RuntimeError(
                f"Migration verification failed: expected {total}, got {target_count}"
            )

        target_size = get_store_size(target_path)
        compression = (1 - target_size / source_size) * 100 if source_size > 0 else 0
        rate = total / elapsed if elapsed > 0 else 0

        console.print(
            f"  [green]✓[/] Migrated {total:,} records in {elapsed:.1f}s ({rate:,.0f} rec/s)"
        )
        console.print(
            f"  Size: {format_size(source_size)} → {format_size(target_size)} "
            f"([{'green' if compression > 0 else 'red'}]{compression:+.1f}%[/])"
        )

        return total, elapsed


def expand_glob_pattern(pattern: str) -> list[Path]:
    """Expand glob pattern to list of paths."""
    # Handle both absolute and relative patterns
    matches = glob(pattern) if Path(pattern).is_absolute() else glob(str(Path.cwd() / pattern))

    return sorted(Path(m) for m in matches if Path(m).exists())


def target_to_backend(target: TargetBackend) -> BackendType:
    """Convert CLI target enum to BackendType."""
    return {
        TargetBackend.sqlite: BackendType.SQLITE,
        TargetBackend.json_files: BackendType.JSON_FILES,
        TargetBackend.jsonl: BackendType.JSONL,
    }[target]


# Default sapphire phases
SAPPHIRE_PHASES = [
    "provider_ids",
    "provider_details",
    "locations",
    "affiliations",
    "networks",
]


def parse_phases(
    phases: list[str] | None, exclude: list[str] | None, available: list[str]
) -> list[str]:
    """Parse phase selection with include/exclude logic.

    Args:
        phases: Explicit phases to include (None = all)
        exclude: Phases to exclude
        available: All available phases

    Returns:
        Filtered list of phases
    """
    # Start with explicit selection or all available
    if phases:
        selected = [p for p in phases if p in available]
        unknown = [p for p in phases if p not in available]
        if unknown:
            console.print(f"[yellow]⚠ Unknown phase(s) ignored: {', '.join(unknown)}[/]")
    else:
        selected = available.copy()

    # Apply exclusions
    if exclude:
        selected = [p for p in selected if p not in exclude]

    return selected


@app.command("sapphire")
def migrate_sapphire(
    project: Annotated[
        str,
        typer.Argument(help="Sapphire project slug (e.g., molina, bcbs_mn)."),
    ],
    date: Annotated[
        str,
        typer.Argument(help="Date folder (YYYYMMDD format)."),
    ],
    phases: Annotated[
        list[str] | None,
        typer.Option(
            "--phase",
            "-p",
            help="Specific phase(s) to migrate. Can repeat. Default: all phases.",
        ),
    ] = None,
    exclude: Annotated[
        list[str] | None,
        typer.Option(
            "--exclude",
            "-e",
            help="Phase(s) to exclude from migration. Can repeat.",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Preview migration without writing."),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing .db files."),
    ] = False,
    list_phases: Annotated[
        bool,
        typer.Option("--list-phases", "-l", help="List available phases and exit."),
    ] = False,
    workers: Annotated[
        int,
        typer.Option("--workers", "-w", help="Parallel reader threads (default: 8)."),
    ] = DEFAULT_WORKERS,
    batch_mb: Annotated[
        int,
        typer.Option("--batch-mb", help="Batch size in MB before SQLite commit (default: 128)."),
    ] = DEFAULT_BATCH_MB,
) -> None:
    """Migrate Sapphire raw JSON_FILES directories to SQLite.

    Available phases: provider_ids, provider_details, locations, affiliations, networks

    Examples:
        # Migrate all phases
        migrate sapphire molina 20251230

        # Migrate specific phases
        migrate sapphire molina 20251230 -p provider_details -p locations

        # Migrate all except networks
        migrate sapphire molina 20251230 -e networks

        # High-performance migration
        migrate sapphire molina 20251230 --workers 16 --batch-mb 256
    """
    if list_phases:
        console.print("[bold]Available Sapphire phases:[/]")
        for phase in SAPPHIRE_PHASES:
            console.print(f"  - {phase}")
        raise typer.Exit(0)

    raw_dir = Path(project) / date / "raw"

    if not raw_dir.exists():
        console.print(f"[red]✗[/] Raw directory not found: {raw_dir}")
        raise typer.Exit(1)

    # Filter phases based on selection
    selected_phases = parse_phases(phases, exclude, SAPPHIRE_PHASES)

    if not selected_phases:
        console.print("[red]✗[/] No phases selected after filtering.")
        console.print(f"  Available: {', '.join(SAPPHIRE_PHASES)}")
        raise typer.Exit(1)

    console.print(f"[bold]Selected phases:[/] {', '.join(selected_phases)}")

    sources_found = []
    for phase in selected_phases:
        phase_path = raw_dir / phase
        if phase_path.is_dir() and any(phase_path.iterdir()):
            sources_found.append(phase_path)

    if not sources_found:
        console.print(f"[yellow]⚠[/] No JSON_FILES directories found in {raw_dir}")
        console.print("  (Already migrated to SQLite, or no data yet)")
        raise typer.Exit(0)

    console.print(f"Found {len(sources_found)} directory(ies) to migrate:")
    for src in sources_found:
        console.print(f"  - {src.name}/ → {src.name}.db")

    total_records = 0
    total_time = 0.0
    success_count = 0
    failed_sources: list[tuple[Path, str]] = []

    for src_path in sources_found:
        target_path = src_path.with_suffix(".db")

        console.print(f"\n{'=' * 60}")
        console.print(f"Migrating: [bold]{src_path.name}/[/] → [bold]{target_path.name}[/]")
        console.print("=" * 60)

        try:
            if target_path.exists() and force and not dry_run:
                console.print(f"  [yellow]⚠ Removing existing: {target_path.name}[/]")
                target_path.unlink()

            records, elapsed = migrate_store(
                src_path,
                target_path,
                BackendType.SQLITE,
                dry_run=dry_run,
                workers=workers,
                batch_mb=batch_mb,
            )

            total_records += records
            total_time += elapsed
            success_count += 1

        except Exception as e:
            console.print(f"  [red]✗[/] Migration failed: {e}")
            failed_sources.append((src_path, str(e)))

    # Summary
    console.print(f"\n{'=' * 60}")
    console.print("[bold]SAPPHIRE MIGRATION SUMMARY[/]")
    console.print("=" * 60)

    if dry_run:
        console.print(
            f"[yellow][DRY RUN][/] Would migrate {total_records:,} records "
            f"from {success_count} phase(s)"
        )
    else:
        console.print(
            f"Migrated: [green]{total_records:,}[/] records from {success_count} phase(s)"
        )
        if total_time > 0:
            console.print(f"Time: {total_time:.1f}s ({total_records / total_time:.0f} rec/s)")

    if failed_sources:
        console.print(f"\n[red]✗[/] Failed migrations ({len(failed_sources)}):")
        for src, error in failed_sources:
            console.print(f"  - {src.name}: {error}")
        raise typer.Exit(1)

    console.print("\n[green]✓[/] All sapphire phases migrated successfully!")


def filter_by_patterns(
    names: list[str],
    include: list[str] | None,
    exclude: list[str] | None,
) -> list[str]:
    """Filter names by include/exclude patterns using fnmatch.

    Args:
        names: List of names to filter
        include: Patterns to include (None = all). Supports fnmatch wildcards.
        exclude: Patterns to exclude. Supports fnmatch wildcards.

    Returns:
        Filtered list of names
    """
    from fnmatch import fnmatch

    # Apply include filter
    if include:
        filtered = []
        for name in names:
            if any(fnmatch(name, pat) for pat in include):
                filtered.append(name)
    else:
        filtered = names.copy()

    # Apply exclude filter
    if exclude:
        filtered = [name for name in filtered if not any(fnmatch(name, pat) for pat in exclude)]

    return filtered


@app.command("run")
def migrate(
    source: Annotated[
        str,
        typer.Argument(
            help="Source path (directory, .db file, or .jsonl file). "
            "Use glob pattern with --batch for multiple sources."
        ),
    ],
    to: Annotated[
        TargetBackend,
        typer.Option("--to", "-t", help="Target backend type."),
    ],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output path (auto-generated if not specified)."),
    ] = None,
    batch: Annotated[
        bool,
        typer.Option("--batch", "-b", help="Treat source as glob pattern and migrate all matches."),
    ] = False,
    subdirs: Annotated[
        bool,
        typer.Option(
            "--subdirs",
            "-s",
            help="Auto-discover and migrate all subdirectories within source.",
        ),
    ] = False,
    include: Annotated[
        list[str] | None,
        typer.Option(
            "--include",
            "-i",
            help="Include only subdirs matching pattern (fnmatch). Can repeat.",
        ),
    ] = None,
    exclude: Annotated[
        list[str] | None,
        typer.Option(
            "--exclude",
            "-e",
            help="Exclude subdirs matching pattern (fnmatch). Can repeat.",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Preview migration without writing."),
    ] = False,
    buffer_size: Annotated[
        int,
        typer.Option("--buffer-size", help="Write buffer size for SQLite (legacy mode)."),
    ] = 1000,
    workers: Annotated[
        int,
        typer.Option("--workers", "-w", help="Parallel reader threads (default: 8)."),
    ] = DEFAULT_WORKERS,
    batch_mb: Annotated[
        int,
        typer.Option("--batch-mb", help="Batch size in MB before SQLite commit (default: 128)."),
    ] = DEFAULT_BATCH_MB,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing target (use with caution)."),
    ] = False,
    no_fast: Annotated[
        bool,
        typer.Option("--no-fast", help="Disable fast parallel mode (use sequential migration)."),
    ] = False,
) -> None:
    """Migrate data between DataStore backends.

    Examples:
        # Single directory to SQLite (fast mode auto-enabled)
        migrate run provider_details/ --to sqlite

        # All subdirs in a directory
        migrate run molina/20251230/raw/ --to sqlite --subdirs

        # Only specific subdirs (fnmatch patterns)
        migrate run molina/20251230/raw/ --to sqlite --subdirs -i "provider_*"

        # Exclude certain subdirs
        migrate run molina/20251230/raw/ --to sqlite --subdirs -e "networks" -e "affiliations"

        # Batch mode with glob
        migrate run "*/*/raw/provider_details/" --to sqlite --batch

        # High-performance migration with custom settings
        migrate run data/ --to sqlite --workers 16 --batch-mb 256
    """
    target_backend = target_to_backend(to)

    # Validate option combinations
    if (include or exclude) and not subdirs:
        console.print("[yellow]⚠ --include/--exclude only apply with --subdirs[/]")

    if batch and subdirs:
        console.print("[red]✗[/] Cannot use --batch with --subdirs")
        raise typer.Exit(1)

    # Expand sources
    if batch:
        sources = expand_glob_pattern(source)
        if not sources:
            console.print(f"[red]✗[/] No matches found for pattern: {source}")
            raise typer.Exit(1)
        console.print(f"Found {len(sources)} source(s) to migrate:")
        for src in sources:
            console.print(f"  - {src}")
    elif subdirs:
        # Auto-discover subdirectories
        source_path = Path(source)
        if not source_path.exists():
            console.print(f"[red]✗[/] Source not found: {source}")
            raise typer.Exit(1)
        if not source_path.is_dir():
            console.print(f"[red]✗[/] --subdirs requires a directory: {source}")
            raise typer.Exit(1)

        # Find all non-empty subdirectories
        all_subdirs = [
            d.name for d in sorted(source_path.iterdir()) if d.is_dir() and any(d.iterdir())
        ]

        if not all_subdirs:
            console.print(f"[yellow]⚠[/] No non-empty subdirectories found in {source}")
            raise typer.Exit(0)

        # Apply include/exclude filters
        filtered_subdirs = filter_by_patterns(all_subdirs, include, exclude)

        if not filtered_subdirs:
            console.print("[red]✗[/] No subdirectories remain after filtering.")
            console.print(f"  Available: {', '.join(all_subdirs)}")
            if include:
                console.print(f"  Include patterns: {', '.join(include)}")
            if exclude:
                console.print(f"  Exclude patterns: {', '.join(exclude)}")
            raise typer.Exit(1)

        sources = [source_path / name for name in filtered_subdirs]

        console.print(f"[bold]Discovered {len(sources)} subdir(s) to migrate:[/]")
        for src in sources:
            console.print(f"  - {src.name}/")
    else:
        source_path = Path(source)
        if not source_path.exists():
            console.print(f"[red]✗[/] Source not found: {source}")
            raise typer.Exit(1)
        sources = [source_path]

    # Batch/subdirs mode doesn't support explicit output
    if (batch or subdirs) and output:
        console.print("[red]✗[/] Cannot use --output with --batch or --subdirs mode")
        raise typer.Exit(1)

    total_records = 0
    total_time = 0.0
    success_count = 0
    failed_sources: list[tuple[Path, str]] = []

    for src_path in sources:
        console.print(f"\n{'=' * 60}")
        console.print(f"Migrating: [bold]{src_path}[/]")
        console.print("=" * 60)

        try:
            # Determine output path
            target_path = output or get_default_output(src_path, target_backend)

            # Handle force flag
            if target_path.exists() and force and not dry_run:
                console.print(f"  [yellow]⚠ Removing existing target: {target_path}[/]")
                if target_path.is_file():
                    target_path.unlink()
                else:
                    shutil.rmtree(target_path)

            records, elapsed = migrate_store(
                src_path,
                target_path,
                target_backend,
                dry_run=dry_run,
                buffer_size=buffer_size,
                workers=workers,
                batch_mb=batch_mb,
                fast_mode=not no_fast,
            )

            total_records += records
            total_time += elapsed
            success_count += 1

        except Exception as e:
            console.print(f"  [red]✗[/] Migration failed: {e}")
            failed_sources.append((src_path, str(e)))

    # Summary
    console.print(f"\n{'=' * 60}")
    console.print("[bold]MIGRATION SUMMARY[/]")
    console.print("=" * 60)

    if dry_run:
        console.print(
            f"[yellow][DRY RUN][/] Would migrate {total_records:,} records "
            f"from {success_count} source(s)"
        )
    else:
        console.print(
            f"Migrated: [green]{total_records:,}[/] records from {success_count} source(s)"
        )
        if total_time > 0:
            console.print(f"Time: {total_time:.1f}s ({total_records / total_time:.0f} rec/s)")

    if failed_sources:
        console.print(f"\n[red]✗[/] Failed migrations ({len(failed_sources)}):")
        for src, error in failed_sources:
            console.print(f"  - {src}: {error}")
        raise typer.Exit(1)

    console.print("\n[green]✓[/] All migrations completed successfully!")


if __name__ == "__main__":
    app()

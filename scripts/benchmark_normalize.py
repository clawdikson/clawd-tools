#!/usr/bin/env python3
"""Benchmark Phase 3 normalization: dict-based vs SQLite-backed NPI map.

Usage:
    python scripts/benchmark_normalize.py --project medica_sg --curr 20260109
    python scripts/benchmark_normalize.py --raw-dir path/to/provider_details --output-dir /tmp/bench

    # For SQLite storage backends (e.g., wellmark):
    python scripts/benchmark_normalize.py --raw-dir audiobee_wellmark/20260103/raw/provider_details.db --storage-backend sqlite
"""

import argparse
import gc
import os
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import orjson

from healthsparq.config.schema import StorageBackend


def get_memory_mb() -> float:
    """Get current memory usage in MB."""
    current, peak = tracemalloc.get_traced_memory()
    return peak / 1024 / 1024


def count_jsonl_lines(path: Path) -> int:
    """Count lines in JSONL file."""
    if not path.exists():
        return 0
    with open(path, "rb") as f:
        return sum(1 for _ in f)


def hash_jsonl_content(path: Path) -> str:
    """Hash JSONL content for comparison (order-independent)."""
    import hashlib
    if not path.exists():
        return "MISSING"

    # Read all records, sort by NPI for deterministic comparison
    records = []
    with open(path, "rb") as f:
        for line in f:
            try:
                record = orjson.loads(line)
                npi = record.get("provider", {}).get("npi", "")
                records.append((npi, line))
            except Exception:
                continue

    # Sort by NPI and hash (handle None NPIs)
    records.sort(key=lambda x: x[0] or "")
    hasher = hashlib.md5()
    for _, line in records:
        hasher.update(line)
    return hasher.hexdigest()


def benchmark_dict_mode(raw_dir: Path, output_dir: Path, config, curr_date: str, storage_backend=None) -> dict:
    """Benchmark dict-based normalization."""
    from healthsparq.phases.normalize import NormalizeConfig, run_normalize

    gc.collect()
    tracemalloc.start()
    start_time = time.perf_counter()

    normalize_config = NormalizeConfig(
        config=config,
        curr_date=curr_date,
        raw_dir=raw_dir,
        output_dir=output_dir,
        use_sqlite_stage=False,
        storage_backend=storage_backend,
    )

    result = run_normalize(normalize_config)

    elapsed = time.perf_counter() - start_time
    peak_memory = get_memory_mb()
    tracemalloc.stop()

    output_file = Path(result.output_file) if result.output_file else None

    return {
        "mode": "dict",
        "elapsed_seconds": elapsed,
        "peak_memory_mb": peak_memory,
        "total_raw": result.total_raw,
        "total_normalized": result.total_normalized,
        "duplicates_merged": result.duplicates_merged,
        "output_file": output_file,
        "output_lines": count_jsonl_lines(output_file) if output_file else 0,
        "content_hash": hash_jsonl_content(output_file) if output_file else "N/A",
    }


def benchmark_sqlite_mode(raw_dir: Path, output_dir: Path, config, curr_date: str, storage_backend=None) -> dict:
    """Benchmark SQLite-backed normalization."""
    from healthsparq.phases.normalize import NormalizeConfig, run_normalize

    gc.collect()
    tracemalloc.start()
    start_time = time.perf_counter()

    normalize_config = NormalizeConfig(
        config=config,
        curr_date=curr_date,
        raw_dir=raw_dir,
        output_dir=output_dir,
        use_sqlite_stage=True,
        storage_backend=storage_backend,
    )

    result = run_normalize(normalize_config)

    elapsed = time.perf_counter() - start_time
    peak_memory = get_memory_mb()
    tracemalloc.stop()

    output_file = Path(result.output_file) if result.output_file else None

    return {
        "mode": "sqlite",
        "elapsed_seconds": elapsed,
        "peak_memory_mb": peak_memory,
        "total_raw": result.total_raw,
        "total_normalized": result.total_normalized,
        "duplicates_merged": result.duplicates_merged,
        "output_file": output_file,
        "output_lines": count_jsonl_lines(output_file) if output_file else 0,
        "content_hash": hash_jsonl_content(output_file) if output_file else "N/A",
    }


def print_results(dict_result: dict, sqlite_result: dict):
    """Print benchmark comparison."""
    print("\n" + "=" * 70)
    print("BENCHMARK RESULTS: Phase 3 Normalization")
    print("=" * 70)

    print(f"\n{'Metric':<30} {'Dict Mode':<20} {'SQLite Mode':<20}")
    print("-" * 70)

    print(f"{'Total raw records':<30} {dict_result['total_raw']:<20} {sqlite_result['total_raw']:<20}")
    print(f"{'Total normalized':<30} {dict_result['total_normalized']:<20} {sqlite_result['total_normalized']:<20}")
    print(f"{'Duplicates merged':<30} {dict_result['duplicates_merged']:<20} {sqlite_result['duplicates_merged']:<20}")
    print(f"{'Output lines':<30} {dict_result['output_lines']:<20} {sqlite_result['output_lines']:<20}")

    print(f"\n{'Time (seconds)':<30} {dict_result['elapsed_seconds']:<20.2f} {sqlite_result['elapsed_seconds']:<20.2f}")
    print(f"{'Peak memory (MB)':<30} {dict_result['peak_memory_mb']:<20.1f} {sqlite_result['peak_memory_mb']:<20.1f}")

    # Calculate improvements
    time_diff = dict_result['elapsed_seconds'] - sqlite_result['elapsed_seconds']
    time_pct = (time_diff / dict_result['elapsed_seconds']) * 100 if dict_result['elapsed_seconds'] > 0 else 0

    mem_diff = dict_result['peak_memory_mb'] - sqlite_result['peak_memory_mb']
    mem_pct = (mem_diff / dict_result['peak_memory_mb']) * 100 if dict_result['peak_memory_mb'] > 0 else 0

    print(f"\n{'Time improvement':<30} {time_diff:+.2f}s ({time_pct:+.1f}%)")
    print(f"{'Memory improvement':<30} {mem_diff:+.1f}MB ({mem_pct:+.1f}%)")

    # Output consistency check
    print(f"\n{'Output consistency':<30}", end=" ")
    if dict_result['content_hash'] == sqlite_result['content_hash']:
        print("✓ IDENTICAL OUTPUT")
    else:
        print("✗ OUTPUT DIFFERS")
        print(f"  Dict hash:   {dict_result['content_hash']}")
        print(f"  SQLite hash: {sqlite_result['content_hash']}")

    print("\n" + "=" * 70)

    # Recommendation
    print("\nRECOMMENDATION:")
    if sqlite_result['elapsed_seconds'] <= dict_result['elapsed_seconds'] * 1.1:  # Within 10%
        if mem_pct > 20:  # >20% memory savings
            print("  ✓ SQLite mode recommended (significant memory savings, acceptable speed)")
        elif mem_pct > 0:
            print("  ~ SQLite mode acceptable (some memory savings)")
        else:
            print("  ~ Dict mode preferred (no significant benefit from SQLite)")
    else:
        print("  ✗ Dict mode preferred (SQLite too slow)")

    return dict_result['content_hash'] == sqlite_result['content_hash']


def main():
    parser = argparse.ArgumentParser(description="Benchmark Phase 3 normalization modes")
    parser.add_argument("--project", help="HealthSparq project slug (e.g., medica_sg)")
    parser.add_argument("--curr", help="Current date (YYYYMMDD)")
    parser.add_argument("--raw-dir", type=Path, help="Direct path to raw provider_details/ or .db file")
    parser.add_argument("--output-dir", type=Path, help="Output directory for benchmark results")
    parser.add_argument(
        "--storage-backend",
        choices=["json_files", "sqlite", "jsonl", "auto"],
        default="auto",
        help="Storage backend type (default: auto-detect from path)",
    )

    args = parser.parse_args()

    # Parse storage backend
    storage_backend_map = {
        "json_files": StorageBackend.JSON_FILES,
        "sqlite": StorageBackend.SQLITE,
        "jsonl": StorageBackend.JSONL,
        "auto": StorageBackend.AUTO,
    }
    storage_backend = storage_backend_map.get(args.storage_backend, StorageBackend.AUTO)

    # Determine raw_dir and output_dir
    if args.project and args.curr:
        from healthsparq.config import load_config
        config = load_config(args.project)
        base_dir = Path(config.output.base_dir) if config.output.base_dir else Path(".")
        raw_dir = base_dir / args.curr / config.output.raw_subdir / "provider_details"
        curr_date = args.curr
        # Use project's storage backend if auto
        if storage_backend == StorageBackend.AUTO:
            storage_backend = config.output.storage_backend
    elif args.raw_dir:
        raw_dir = args.raw_dir
        curr_date = "benchmark"
        # Create minimal config
        from healthsparq.config.schema import (
            HealthSparqProjectConfig, ProjectMetadata, SiteConfig, OutputConfig,
            PlanConfig, CoverageConfig
        )
        config = HealthSparqProjectConfig(
            project=ProjectMetadata(name="Benchmark", slug="benchmark"),
            site=SiteConfig(domain="example.com", brand_code="TEST", insurer_code="TEST"),
            plans=[PlanConfig(product_code="BENCH", name="Benchmark Plan")],
            coverage=CoverageConfig(states=["TX"]),
            output=OutputConfig(),
        )
        # Auto-detect storage backend from path
        if storage_backend == StorageBackend.AUTO:
            if raw_dir.suffix == ".db":
                storage_backend = StorageBackend.SQLITE
            elif raw_dir.suffix == ".jsonl":
                storage_backend = StorageBackend.JSONL
            else:
                storage_backend = StorageBackend.JSON_FILES
    else:
        parser.error("Either --project/--curr or --raw-dir required")
        return

    if not raw_dir.exists():
        print(f"ERROR: Raw path not found: {raw_dir}")
        sys.exit(1)

    # Count records for preview
    print(f"Raw path: {raw_dir}")
    print(f"Storage backend: {storage_backend.value}")

    if storage_backend == StorageBackend.SQLITE:
        import sqlite3
        conn = sqlite3.connect(raw_dir)
        record_count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        conn.close()
        print(f"Provider records: {record_count}")
    elif storage_backend == StorageBackend.JSONL:
        with open(raw_dir, "rb") as f:
            record_count = sum(1 for _ in f)
        print(f"Provider records: {record_count}")
    else:
        record_count = sum(1 for _ in raw_dir.glob("*.json"))
        print(f"Provider files: {record_count}")

    if record_count == 0:
        print("ERROR: No provider records found")
        sys.exit(1)

    # Create temp directories for output
    with tempfile.TemporaryDirectory() as tmpdir:
        dict_output = Path(tmpdir) / "dict_mode"
        sqlite_output = Path(tmpdir) / "sqlite_mode"
        dict_output.mkdir()
        sqlite_output.mkdir()

        print("\n--- Running dict-based normalization ---")
        dict_result = benchmark_dict_mode(raw_dir, dict_output, config, curr_date, storage_backend)

        print("\n--- Running SQLite-backed normalization ---")
        sqlite_result = benchmark_sqlite_mode(raw_dir, sqlite_output, config, curr_date, storage_backend)

        identical = print_results(dict_result, sqlite_result)

        sys.exit(0 if identical else 1)


if __name__ == "__main__":
    main()

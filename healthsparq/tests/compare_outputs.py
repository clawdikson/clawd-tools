#!/usr/bin/env python3
"""Compare singleton vs legacy scraper outputs.

Usage:
    python compare_outputs.py --legacy path/to/legacy/processed --singleton path/to/singleton/processed
    python compare_outputs.py --legacy audiobee_christus_health_plan/20251226/processed --singleton healthsparq/output/christus_health_plan/20251226/processed --threshold 0.99
"""

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import orjson


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load JSONL file into list of dicts."""
    records = []
    for file in path.glob("*.jsonl"):
        with open(file, "rb") as f:
            for line in f:
                if line.strip():
                    records.append(orjson.loads(line))
    return records


def get_schema_fields(records: list[dict]) -> set[str]:
    """Extract all unique field names from records."""
    fields = set()
    for record in records[:1000]:  # Sample first 1000
        fields.update(get_all_keys(record))
    return fields


def get_all_keys(d: dict, prefix: str = "") -> set[str]:
    """Recursively get all keys including nested."""
    keys = set()
    for k, v in d.items():
        full_key = f"{prefix}.{k}" if prefix else k
        keys.add(full_key)
        if isinstance(v, dict):
            keys.update(get_all_keys(v, full_key))
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            keys.update(get_all_keys(v[0], f"{full_key}[]"))
    return keys


def compare_schemas(legacy: set[str], singleton: set[str]) -> dict:
    """Compare schema fields between outputs."""
    return {
        "legacy_only": sorted(legacy - singleton),
        "singleton_only": sorted(singleton - legacy),
        "common": sorted(legacy & singleton),
        "match": legacy == singleton,
    }


def compare_counts(legacy: list, singleton: list, threshold: float) -> dict:
    """Compare record counts."""
    legacy_count = len(legacy)
    singleton_count = len(singleton)

    if legacy_count == 0 and singleton_count == 0:
        ratio = 1.0
    elif legacy_count == 0:
        ratio = 0.0
    else:
        ratio = singleton_count / legacy_count

    return {
        "legacy_count": legacy_count,
        "singleton_count": singleton_count,
        "ratio": ratio,
        "within_threshold": ratio >= threshold,
        "difference": abs(legacy_count - singleton_count),
    }


def compare_npis(legacy: list, singleton: list) -> dict:
    """Compare NPI coverage."""
    legacy_npis = {r.get("npi") for r in legacy if r.get("npi")}
    singleton_npis = {r.get("npi") for r in singleton if r.get("npi")}

    return {
        "legacy_unique_npis": len(legacy_npis),
        "singleton_unique_npis": len(singleton_npis),
        "common_npis": len(legacy_npis & singleton_npis),
        "legacy_only_npis": len(legacy_npis - singleton_npis),
        "singleton_only_npis": len(singleton_npis - legacy_npis),
        "overlap_ratio": len(legacy_npis & singleton_npis) / len(legacy_npis) if legacy_npis else 0,
    }


def compare_provider_types(legacy: list, singleton: list) -> dict:
    """Compare provider type distribution."""
    legacy_types = Counter(r.get("provider_type") for r in legacy)
    singleton_types = Counter(r.get("provider_type") for r in singleton)

    return {
        "legacy_distribution": dict(legacy_types),
        "singleton_distribution": dict(singleton_types),
        "match": legacy_types == singleton_types,
    }


def validate_deduplication(records: list) -> dict:
    """Check NPI deduplication."""
    npis = [r.get("npi") for r in records if r.get("npi")]
    npi_counts = Counter(npis)
    duplicates = {npi: count for npi, count in npi_counts.items() if count > 1}

    return {
        "total_with_npi": len(npis),
        "unique_npis": len(set(npis)),
        "duplicate_npis": len(duplicates),
        "properly_deduplicated": len(duplicates) == 0,
        "sample_duplicates": list(duplicates.items())[:5],
    }


def run_comparison(legacy_path: Path, singleton_path: Path, threshold: float) -> dict:
    """Run full comparison between outputs."""
    print(f"Loading legacy from: {legacy_path}")
    legacy = load_jsonl(legacy_path)
    print(f"  Loaded {len(legacy)} records")

    print(f"Loading singleton from: {singleton_path}")
    singleton = load_jsonl(singleton_path)
    print(f"  Loaded {len(singleton)} records")

    results = {
        "schema": compare_schemas(
            get_schema_fields(legacy),
            get_schema_fields(singleton)
        ),
        "counts": compare_counts(legacy, singleton, threshold),
        "npis": compare_npis(legacy, singleton),
        "provider_types": compare_provider_types(legacy, singleton),
        "deduplication": {
            "legacy": validate_deduplication(legacy),
            "singleton": validate_deduplication(singleton),
        },
    }

    # Overall pass/fail
    results["passed"] = all([
        results["schema"]["match"],
        results["counts"]["within_threshold"],
        results["deduplication"]["singleton"]["properly_deduplicated"],
    ])

    return results


def print_results(results: dict) -> None:
    """Print comparison results."""
    print("\n" + "=" * 60)
    print("COMPARISON RESULTS")
    print("=" * 60)

    print("\n📋 Schema Comparison:")
    if results["schema"]["match"]:
        print("  ✅ Schemas match")
    else:
        print("  ❌ Schema mismatch")
        if results["schema"]["legacy_only"]:
            print(f"     Legacy only: {results['schema']['legacy_only'][:5]}")
        if results["schema"]["singleton_only"]:
            print(f"     Singleton only: {results['schema']['singleton_only'][:5]}")

    print("\n📊 Count Comparison:")
    counts = results["counts"]
    print(f"  Legacy:    {counts['legacy_count']:,}")
    print(f"  Singleton: {counts['singleton_count']:,}")
    print(f"  Ratio:     {counts['ratio']:.2%}")
    if counts["within_threshold"]:
        print("  ✅ Within threshold")
    else:
        print("  ❌ Outside threshold")

    print("\n🔢 NPI Comparison:")
    npis = results["npis"]
    print(f"  Legacy unique:    {npis['legacy_unique_npis']:,}")
    print(f"  Singleton unique: {npis['singleton_unique_npis']:,}")
    print(f"  Overlap:          {npis['overlap_ratio']:.2%}")

    print("\n🔄 Deduplication:")
    dedup = results["deduplication"]["singleton"]
    if dedup["properly_deduplicated"]:
        print("  ✅ Singleton properly deduplicated")
    else:
        print(f"  ❌ Found {dedup['duplicate_npis']} duplicate NPIs")

    print("\n" + "=" * 60)
    if results["passed"]:
        print("✅ OVERALL: PASSED")
    else:
        print("❌ OVERALL: FAILED")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Compare singleton vs legacy outputs")
    parser.add_argument("--legacy", required=True, help="Path to legacy processed output")
    parser.add_argument("--singleton", required=True, help="Path to singleton processed output")
    parser.add_argument("--threshold", type=float, default=0.99,
                        help="Minimum ratio threshold (default: 0.99)")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of text")

    args = parser.parse_args()

    legacy_path = Path(args.legacy)
    singleton_path = Path(args.singleton)

    if not legacy_path.exists():
        print(f"Error: Legacy path does not exist: {legacy_path}")
        return 1

    if not singleton_path.exists():
        print(f"Error: Singleton path does not exist: {singleton_path}")
        return 1

    results = run_comparison(legacy_path, singleton_path, args.threshold)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_results(results)

    return 0 if results["passed"] else 1


if __name__ == "__main__":
    exit(main())

#!/usr/bin/env python3
"""Validate shared_package v3.0 migration by comparing outputs.

Usage:
    python tools/validate_migration.py audiobee_bcbs_il --prev 20251110 --curr 20251210
    python tools/validate_migration.py --all --prev 20251110 --curr 20251210

Validates migration by comparing:
- Provider count (should be similar ±5%)
- NPI format (must be 10 digits)
- Required fields presence
- Schema compliance
"""
import argparse
import sys
from pathlib import Path
from typing import Any

import orjson


def load_jsonl(file_path: Path) -> list[dict[str, Any]]:
    """Load JSONL file into list of dicts."""
    records = []
    if not file_path.exists():
        return records

    with open(file_path, "rb") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(orjson.loads(line))
            except Exception as e:
                print(f"  ! Skipping invalid JSON line: {e}")
                continue

    return records


def validate_npi(npi: str) -> bool:
    """Validate NPI is 10 digits."""
    if not npi:
        return False
    npi = str(npi).strip()
    return npi.isdigit() and len(npi) == 10


def validate_schema(record: dict[str, Any]) -> list[str]:
    """Validate record against v3.0 schema.

    Returns list of validation errors (empty if valid).
    """
    errors = []

    # Required field: NPI
    if "npi" not in record:
        errors.append("Missing required field: npi")
    elif not validate_npi(record["npi"]):
        errors.append(f"Invalid NPI format: {record.get('npi')}")

    # At least one name field required
    if not any([
        record.get("first_name"),
        record.get("last_name"),
        record.get("organization_name")
    ]):
        errors.append("Missing name fields (first_name, last_name, or organization_name)")

    # State validation (if present)
    if "state" in record and record["state"]:
        state = str(record["state"]).strip()
        if len(state) != 2 or not state.isupper():
            errors.append(f"Invalid state format: {record['state']} (should be 2-char uppercase)")

    # ZIP validation (if present)
    if "zip" in record and record["zip"]:
        zip_code = str(record["zip"]).replace("-", "")
        if not zip_code.isdigit() or len(zip_code) not in (5, 9):
            errors.append(f"Invalid ZIP format: {record['zip']} (should be 5 or 9 digits)")

    return errors


def compare_runs(
    prev_file: Path,
    curr_file: Path,
    project_name: str
) -> tuple[bool, list[str]]:
    """Compare previous and current run outputs.

    Returns:
        (is_valid, issues_list)
    """
    issues = []

    # Load data
    print(f"  Loading previous run: {prev_file}")
    prev_records = load_jsonl(prev_file)

    print(f"  Loading current run: {curr_file}")
    curr_records = load_jsonl(curr_file)

    if not curr_records:
        issues.append("Current run produced no records")
        return False, issues

    # Count comparison
    prev_count = len(prev_records)
    curr_count = len(curr_records)

    print(f"  Previous count: {prev_count}")
    print(f"  Current count:  {curr_count}")

    if prev_records:
        pct_diff = abs(curr_count - prev_count) / prev_count * 100
        if pct_diff > 5:
            issues.append(f"Count difference: {pct_diff:.1f}% (threshold: 5%)")

    # Schema validation on current run
    print(f"  Validating {curr_count} records...")

    validation_errors = 0
    for idx, record in enumerate(curr_records):
        errors = validate_schema(record)
        if errors:
            validation_errors += 1
            if validation_errors <= 5:  # Show first 5 errors
                issues.append(f"Record {idx}: {', '.join(errors)}")

    if validation_errors > 5:
        issues.append(f"... and {validation_errors - 5} more validation errors")

    # NPI uniqueness check
    npis = [r.get("npi") for r in curr_records if r.get("npi")]
    unique_npis = set(npis)

    if len(npis) != len(unique_npis):
        duplicates = len(npis) - len(unique_npis)
        issues.append(f"Found {duplicates} duplicate NPIs")

    is_valid = len(issues) == 0
    return is_valid, issues


def validate_project(
    project_dir: Path,
    prev_date: str,
    curr_date: str
) -> tuple[bool, list[str]]:
    """Validate a single project migration.

    Returns:
        (is_valid, issues_list)
    """
    project_name = project_dir.name
    print(f"\nValidating {project_name}...")

    # Find output files
    prev_file = project_dir / prev_date / "processed" / "providers.jsonl"
    curr_file = project_dir / curr_date / "processed" / "providers.jsonl"

    if not prev_file.exists() and not curr_file.exists():
        return True, [f"Skipping {project_name} (no output files found)"]

    if not curr_file.exists():
        return False, [f"Current run output not found: {curr_file}"]

    return compare_runs(prev_file, curr_file, project_name)


def main():
    parser = argparse.ArgumentParser(description="Validate shared_package v3.0 migration")
    parser.add_argument("project", nargs="?", help="Project name (e.g., audiobee_bcbs_il)")
    parser.add_argument("--prev", required=True, help="Previous run date (YYYYMMDD)")
    parser.add_argument("--curr", required=True, help="Current run date (YYYYMMDD)")
    parser.add_argument("--all", action="store_true", help="Validate all projects")

    args = parser.parse_args()

    if not args.project and not args.all:
        parser.error("Provide either project name or --all flag")

    root = Path.cwd()

    if args.all:
        # Find all audiobee_* projects
        projects = sorted(root.glob("audiobee_*"))
        print(f"Found {len(projects)} projects to validate\n")

        all_valid = True
        for project_dir in projects:
            if not project_dir.is_dir():
                continue

            is_valid, issues = validate_project(project_dir, args.prev, args.curr)

            if is_valid:
                print(f"  ✓ Valid")
            else:
                print(f"  ✗ Issues found:")
                for issue in issues:
                    print(f"    - {issue}")
                all_valid = False

        sys.exit(0 if all_valid else 1)

    else:
        # Validate single project
        project_dir = root / args.project
        if not project_dir.exists():
            print(f"✗ Project not found: {project_dir}")
            sys.exit(1)

        is_valid, issues = validate_project(project_dir, args.prev, args.curr)

        if is_valid:
            print("\n✓ Migration validation passed!")
            sys.exit(0)
        else:
            print("\n✗ Migration validation failed:")
            for issue in issues:
                print(f"  - {issue}")
            sys.exit(1)


if __name__ == "__main__":
    main()

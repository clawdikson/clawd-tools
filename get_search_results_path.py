"""Get virtual file paths stored inside search_results.db for healthsparq sites.

The SQLite database uses a 2-column schema (path, data) as a virtual filesystem.
This script lists the paths without loading the full data (important for large DBs).
"""

import sqlite3
from pathlib import Path
from typing import Iterator

import xlsxwriter


def get_db_path(
    project_dir: str | Path,
    date: str,
) -> Path:
    """Get the filesystem path to search_results.db.

    Args:
        project_dir: Path to the project directory
        date: Run date in YYYYMMDD format

    Returns:
        Path to search_results.db
    """
    return Path(project_dir) / date / "raw" / "search_results.db"


def list_virtual_paths(
    db_path: str | Path,
    prefix: str = "",
    limit: int | None = None,
) -> Iterator[str]:
    """List virtual file paths stored in the SQLite database.

    Args:
        db_path: Path to the .db file
        prefix: Optional prefix to filter paths (e.g., "BCBSAPPO/")
        limit: Optional limit on number of paths to return

    Yields:
        Virtual file paths stored in the database
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        if prefix:
            query = "SELECT path FROM files WHERE path LIKE ? ORDER BY path"
            params = (f"{prefix}%",)
        else:
            query = "SELECT path FROM files ORDER BY path"
            params = ()

        if limit:
            query += f" LIMIT {limit}"

        cursor = conn.execute(query, params)
        for row in cursor:
            yield row[0]
    finally:
        conn.close()


def count_paths(db_path: str | Path, prefix: str = "") -> int:
    """Count virtual file paths in the database.

    Args:
        db_path: Path to the .db file
        prefix: Optional prefix to filter paths

    Returns:
        Number of paths matching the prefix
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        if prefix:
            query = "SELECT COUNT(*) FROM files WHERE path LIKE ?"
            row = conn.execute(query, (f"{prefix}%",)).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) FROM files").fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


def get_path_prefixes(db_path: str | Path, depth: int = 1) -> list[str]:
    """Get unique path prefixes (like listing directories).

    Args:
        db_path: Path to the .db file
        depth: Number of path segments to include (1 = top-level folders)

    Returns:
        List of unique prefixes at the specified depth
    """
    prefixes = set()
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        cursor = conn.execute("SELECT DISTINCT path FROM files")
        for row in cursor:
            path = row[0]
            parts = path.split("/")
            if len(parts) >= depth:
                prefix = "/".join(parts[:depth])
                prefixes.add(prefix)
    finally:
        conn.close()
    return sorted(prefixes)


def parse_path(path: str) -> tuple[str, str] | None:
    """Parse plan name and state code from a virtual file path.

    Path format: PLAN_NAME/STATE-rest_of_filename.json
    Example: BCBSA_I_BCBSANDHF_BCBSABASIC/AK-Aleutians East_County-PROVIDER_TYPE_CNSLR-1-NAME_ASC.json

    Args:
        path: Virtual file path

    Returns:
        Tuple of (plan_name, state_code) or None if parsing fails
    """
    if "/" not in path:
        return None

    plan_name, rest = path.split("/", 1)
    if "-" not in rest:
        return None

    state_code = rest.split("-", 1)[0]
    return plan_name, state_code


def get_plans_and_states(db_path: str | Path) -> dict[str, dict[str, int]]:
    """Extract plans, their available states, and file counts from the database.

    Args:
        db_path: Path to the .db file

    Returns:
        Dict mapping plan names to dicts of {state_code: file_count}
    """
    plans: dict[str, dict[str, int]] = {}

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        cursor = conn.execute("SELECT path FROM files")
        count = 0
        for row in cursor:
            parsed = parse_path(row[0])
            if parsed:
                plan_name, state_code = parsed
                if plan_name not in plans:
                    plans[plan_name] = {}
                if state_code not in plans[plan_name]:
                    plans[plan_name][state_code] = 0
                plans[plan_name][state_code] += 1

            count += 1
            if count % 100_000 == 0:
                print(f"  Processed {count:,} paths...")
    finally:
        conn.close()

    print(f"  Found {len(plans)} plans across {count:,} paths")
    return plans


def write_plans_states_to_xlsx(
    db_path: str | Path,
    output_path: str | Path,
) -> int:
    """Write plans and their available states to an Excel file.

    Args:
        db_path: Path to the .db file
        output_path: Path to output .xlsx file

    Returns:
        Number of plans written
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Get plans and states with counts
    plans = get_plans_and_states(db_path)

    workbook = xlsxwriter.Workbook(str(output_path))

    # Header format
    header_format = workbook.add_format({
        "bold": True,
        "bg_color": "#4472C4",
        "font_color": "white",
    })

    # Number format with commas
    number_format = workbook.add_format({"num_format": "#,##0"})

    # --- Sheet 1: Summary (Plan | State Count | Total Files | States) ---
    summary_sheet = workbook.add_worksheet("Summary")
    summary_sheet.write(0, 0, "Plan", header_format)
    summary_sheet.write(0, 1, "State Count", header_format)
    summary_sheet.write(0, 2, "Total Files", header_format)
    summary_sheet.write(0, 3, "States", header_format)
    summary_sheet.set_column(0, 0, 40)
    summary_sheet.set_column(1, 1, 12)
    summary_sheet.set_column(2, 2, 12)
    summary_sheet.set_column(3, 3, 150)

    row = 1
    for plan_name in sorted(plans.keys()):
        state_counts = plans[plan_name]
        states = sorted(state_counts.keys())
        total_files = sum(state_counts.values())
        summary_sheet.write(row, 0, plan_name)
        summary_sheet.write(row, 1, len(states))
        summary_sheet.write(row, 2, total_files, number_format)
        summary_sheet.write(row, 3, ", ".join(states))
        row += 1

    # --- Sheet 2: Detail (Plan | State | File Count) one row per combination ---
    detail_sheet = workbook.add_worksheet("Detail")
    detail_sheet.write(0, 0, "Plan", header_format)
    detail_sheet.write(0, 1, "State", header_format)
    detail_sheet.write(0, 2, "File Count", header_format)
    detail_sheet.set_column(0, 0, 40)
    detail_sheet.set_column(1, 1, 10)
    detail_sheet.set_column(2, 2, 12)

    row = 1
    for plan_name in sorted(plans.keys()):
        state_counts = plans[plan_name]
        for state in sorted(state_counts.keys()):
            detail_sheet.write(row, 0, plan_name)
            detail_sheet.write(row, 1, state)
            detail_sheet.write(row, 2, state_counts[state], number_format)
            row += 1

    workbook.close()
    print(f"  Wrote {len(plans)} plans to {output_path}")
    return len(plans)


def write_paths_to_xlsx(
    db_path: str | Path,
    output_path: str | Path,
    prefix: str = "",
) -> int:
    """Write virtual file paths to an Excel file.

    Args:
        db_path: Path to the .db file
        output_path: Path to output .xlsx file
        prefix: Optional prefix to filter paths

    Returns:
        Number of paths written
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    workbook = xlsxwriter.Workbook(str(output_path))
    worksheet = workbook.add_worksheet("Paths")

    # Header format
    header_format = workbook.add_format({
        "bold": True,
        "bg_color": "#4472C4",
        "font_color": "white",
    })

    # Write headers
    worksheet.write(0, 0, "Row", header_format)
    worksheet.write(0, 1, "Path", header_format)
    worksheet.set_column(0, 0, 10)
    worksheet.set_column(1, 1, 100)

    # Write paths
    row = 1
    for path in list_virtual_paths(db_path, prefix=prefix):
        worksheet.write(row, 0, row)
        worksheet.write(row, 1, path)
        row += 1

        # Progress indicator every 100k rows
        if row % 100_000 == 0:
            print(f"  Written {row:,} rows...")

    workbook.close()
    print(f"  Wrote {row - 1:,} paths to {output_path}")
    return row - 1


if __name__ == "__main__":
    # BlueCard National (500GB+)
    bluecard_db = get_db_path(
        r"\\Pc2\e\scraping-base\audiobee_bluecard_national",
        "20260117"
    )
    print(f"BlueCard National DB: {bluecard_db}")
    print(f"  Exists: {bluecard_db.exists()}")

    if bluecard_db.exists():
        # Count total paths (fast)
        total = count_paths(bluecard_db)
        print(f"  Total virtual files: {total:,}")

        # Get top-level folders
        prefixes = get_path_prefixes(bluecard_db, depth=1)
        print(f"  Top-level folders: {prefixes}")

        # Write plans and states to Excel
        xlsx_path = bluecard_db.parent / "plans_states.xlsx"
        print(f"  Writing plans/states to Excel: {xlsx_path}")
        write_plans_states_to_xlsx(bluecard_db, xlsx_path)

    print()

    # # Maine Community Health Options (for reference)
    # maine_db = get_db_path(
    #     r"\\Pc2\e\scraping-base\audiobee_maine_community_health_options",
    #     "20260119"
    # )
    # print(f"Maine Community DB: {maine_db}")
    # print(f"  Exists: {maine_db.exists()}")

    # if maine_db.exists():
    #     total = count_paths(maine_db)
    #     print(f"  Total virtual files: {total:,}")

    #     prefixes = get_path_prefixes(maine_db, depth=1)
    #     print(f"  Top-level folders: {prefixes}")

    #     # Write paths to Excel
    #     xlsx_path = maine_db.parent / "search_results_paths.xlsx"
    #     print(f"  Writing to Excel: {xlsx_path}")
    #     write_paths_to_xlsx(maine_db, xlsx_path)

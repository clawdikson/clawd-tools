# Custom Carrier Architecture Pattern

This document defines a standardized architecture pattern for custom carrier scrapers (audiobee_* projects). All custom carriers should follow this structure for consistency.

> **Note**: This is a convention-based pattern, not a shared package. Each project has its own codebase but follows the same architecture.

> **Reference Implementation**: See `audiobee_peak/` for a complete working example.

## Quick Reference

| Component | Purpose |
|-----------|---------|
| `run.py` | Typer CLI entry point |
| `config.yaml` | Project configuration |
| `pipeline.py` | Phase orchestration |
| `src/collector.py` | Phase 1: Data collection with checkpointing |
| `src/mapper.py` | Phase 3: Custom normalization mapping |
| `src/checkpoint.py` | SQLite checkpoint for resume capability |

## Standard Project Structure

```
audiobee_{carrier}/
├── run.py                      # Typer CLI entry point (required)
├── config.yaml                 # Project configuration (required)
├── pipeline.py                 # Phase orchestration (required)
├── pyproject.toml              # Dependencies
├── CLAUDE.md                   # Project documentation
├── .gitignore                  # Ignore output dirs, __pycache__, .env
│
├── src/                        # Source code directory
│   ├── __init__.py             # Package exports
│   ├── collector.py            # Phase 1: Data collection (required)
│   ├── mapper.py               # Phase 3: Normalization mapping (optional)
│   ├── checkpoint.py           # SQLite checkpoint class (required)
│   └── {api_client}.py         # API-specific client (optional)
│
├── archive/                    # Old/legacy files (for reference)
│   └── ...
│
└── {YYYYMMDD}/                 # Output directories (auto-created, gitignored)
    ├── checkpoint.db           # SQLite checkpoint for resume
    ├── logs/                   # Run logs
    ├── raw/
    │   └── {index}.db          # SQLite stores for collected data
    └── processed/
        ├── {slug}-{date}.jsonl           # Final output
        ├── {slug}-sample-{date}-*.json   # Sample files
        ├── {slug}-debug_data-{date}.xlsx # Debug data report
        └── {slug}-debug_specialty_network-{date}.xlsx
```

## 5-Phase Pipeline

```
Phase 1 (Collect)     → Phase 2 (Enrich)    → Phase 3 (Normalize)
src/collector.py        (optional/skip)       src/mapper.py + core.mapper
PROJECT-SPECIFIC        PROJECT-SPECIFIC      SHARED + custom hooks
+ mandatory checkpoint                        NPI dedup, schema mapping

Phase 4 (QA)          → Phase 5 (Report)
core.qa.validate        core.qa.sample + core.qa.generate_debug_reports
SHARED                  SHARED
Schema validation       Samples + Debug Excel reports
```

| Phase | File | Responsibility | Checkpointing |
|-------|------|----------------|---------------|
| 1 | `src/collector.py` | Fetch raw provider data | **Mandatory** |
| 2 | `src/enricher.py` | Enrich with additional details | **Mandatory** if present |
| 3 | `src/mapper.py` + core | NPI dedup, schema mapping | N/A |
| 4 | core.qa | Validation, comparison | N/A |
| 5 | core.qa | Samples, debug Excel reports | N/A |

## CLI Interface

```bash
# Full pipeline (auto-resumes from checkpoint)
.venv/bin/python audiobee_peak/run.py run --curr 20260121

# Fresh run (clear checkpoint)
.venv/bin/python audiobee_peak/run.py run --curr 20260121 --fresh

# With previous date (enables comparison)
.venv/bin/python audiobee_peak/run.py run --curr 20260121 --prev 20260115

# Phase control
.venv/bin/python audiobee_peak/run.py run --curr 20260121 --phase 1        # Phase 1 only
.venv/bin/python audiobee_peak/run.py run --curr 20260121 --phase 1-5      # Phases 1-5
.venv/bin/python audiobee_peak/run.py run --curr 20260121 --phase 1,3,5    # Specific phases

# QA and reporting
.venv/bin/python audiobee_peak/run.py run --curr 20260121 --qa             # Include QA phase
.venv/bin/python audiobee_peak/run.py run --curr 20260121 --report         # Include report phase

# Dry run (show what would happen)
.venv/bin/python audiobee_peak/run.py run --curr 20260121 --dry-run

# Individual phase commands
.venv/bin/python audiobee_peak/run.py collect --curr 20260121
.venv/bin/python audiobee_peak/run.py normalize --curr 20260121

# View metrics
.venv/bin/python audiobee_peak/run.py metrics                              # Latest run
.venv/bin/python audiobee_peak/run.py metrics --date 20260121              # Specific date

# Validation (test config and API connectivity)
.venv/bin/python audiobee_peak/run.py validate
```

## Configuration (config.yaml)

```yaml
project:
  name: "Peak Health"
  slug: "audiobee_peak"
  version: "1.0"

site:
  base_url: "https://api.example.com"
  auth_type: none  # none, cookie, bearer, oauth, basic

# API-specific configuration
algolia:
  app_id: "APP_ID"
  api_key: "API_KEY"
  indices:
    - IndexName1
    - IndexName2

coverage:
  states: [NV]
  network_name: "Network Name"
  network_filter: "networks:'Medicare'"

phases:
  collect: true
  enrich: false  # Skip if not needed
  normalize_input: collected  # or 'enriched' if Phase 2 runs

concurrency:
  max_concurrent: 5
  hits_per_page: 1000

output:
  storage_backend: sqlite

qa:
  churn_threshold_percent: 5  # Alert if >5% providers dropped
  sample_count: 10

# Environment variable overrides (PROJECT_* prefix):
# PROJECT_HITS_PER_PAGE, PROJECT_CHURN_THRESHOLD, etc.
```

## Key Implementation Patterns

### run.py - Typer CLI

```python
#!/usr/bin/env python
"""CLI for {Carrier} scraper pipeline."""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from core.logging import setup_logging

app = typer.Typer(name="audiobee_carrier", help="Carrier provider scraper.")

@app.command()
def run(
    curr: str = typer.Option(..., "--curr", help="Current date (YYYYMMDD)"),
    prev: Optional[str] = typer.Option(None, "--prev", help="Previous date for comparison"),
    phase: Optional[str] = typer.Option(None, "--phase", help="Phases to run (1,3,4,5 or 1-5)"),
    fresh: bool = typer.Option(False, "--fresh", help="Clear checkpoint and start fresh"),
    qa: bool = typer.Option(False, "--qa", help="Run QA after normalize"),
    report: bool = typer.Option(False, "--report", help="Run report phase"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would happen"),
):
    """Run scraper pipeline."""
    setup_logging(project_name="audiobee_carrier", run_id=curr)
    from pipeline import run_pipeline, parse_phases

    phases = parse_phases(phase)
    if qa and 4 not in phases:
        phases.append(4)
    if report and 5 not in phases:
        phases.append(5)

    asyncio.run(run_pipeline(curr, prev, phases, fresh, dry_run))

@app.command()
def validate():
    """Validate config and test API connectivity."""
    # Test API connection
    ...

@app.command()
def metrics(date: Optional[str] = None):
    """Show collection metrics."""
    from src.checkpoint import Checkpoint
    # Load and display metrics
    ...

if __name__ == "__main__":
    app()
```

### src/checkpoint.py - Resume Capability

```python
"""SQLite-based checkpoint for collection resume capability."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

@dataclass
class Checkpoint:
    """SQLite checkpoint for tracking collection progress."""

    db_path: Path

    def __post_init__(self):
        self.db_path = Path(self.db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._create_schema()

    def _create_schema(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS collected_pages (
                index_name TEXT NOT NULL,
                page_num INTEGER NOT NULL,
                collected_at TEXT NOT NULL,
                hits_count INTEGER DEFAULT 0,
                PRIMARY KEY (index_name, page_num)
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS collection_metadata (
                index_name TEXT PRIMARY KEY,
                total_hits INTEGER,
                total_pages INTEGER,
                started_at TEXT,
                completed_at TEXT
            )
        """)
        self._conn.commit()

    def is_collected(self, index_name: str, page: int) -> bool:
        cursor = self._conn.execute(
            "SELECT 1 FROM collected_pages WHERE index_name = ? AND page_num = ?",
            (index_name, page),
        )
        return cursor.fetchone() is not None

    def mark_collected(self, index_name: str, page: int, hits_count: int = 0):
        self._conn.execute(
            "INSERT OR REPLACE INTO collected_pages VALUES (?, ?, ?, ?)",
            (index_name, page, datetime.utcnow().isoformat(), hits_count),
        )
        self._conn.commit()

    def get_progress(self, index_name: str) -> dict:
        # Return collection progress
        ...

    def close(self):
        if self._conn:
            self._conn.close()
```

### src/collector.py - Data Collection

```python
"""Phase 1: Collect data from API."""

from dataclasses import dataclass
from pathlib import Path
from tqdm import tqdm

from core.io import create_store
from .checkpoint import Checkpoint

@dataclass
class CollectorResult:
    index_name: str
    total_hits: int
    pages_collected: int
    hits_collected: int

async def collect_index(
    index_name: str,
    store,
    checkpoint: Checkpoint,
    client,
    config,
    dry_run: bool = False,
) -> CollectorResult:
    """Collect all pages from an index with checkpoint resume."""

    progress = checkpoint.get_progress(index_name)
    if progress.get("is_complete"):
        return CollectorResult(...)  # Already done

    page = 0
    while page < total_pages:
        if checkpoint.is_collected(index_name, page):
            page += 1
            continue

        # Fetch page
        response = await client.search(index_name, page)

        # Store results
        store.put(f"{index_name}/page_{page:04d}.json", response)
        checkpoint.mark_collected(index_name, page, len(response["hits"]))

        page += 1

    return CollectorResult(...)

async def run_collect_phase(output_dir: Path, config, fresh: bool = False):
    """Run collection for all configured indices."""
    checkpoint = Checkpoint(output_dir / "checkpoint.db")
    if fresh:
        checkpoint.clear()

    for index_name in config.indices:
        store = create_store(str(output_dir / "raw" / f"{index_name.lower()}.db"))
        await collect_index(index_name, store, checkpoint, ...)
        store.close()

    checkpoint.close()
```

### src/mapper.py - Normalization

```python
"""Phase 3: Normalize data to Ideon schema."""

from core.mapper import normalize_zip_code, normalize_phone
from core.io import create_store, JSONLWriter

def map_record(record: dict, source_index: str) -> dict:
    """Map API record to Ideon schema."""

    # Determine provider type
    provider_type = "individual"
    if "Facilities" in source_index:
        provider_type = "organization"

    # Map NPI based on provider type
    if provider_type == "organization":
        npi = record.get("npiTypeII")
    else:
        npi = record.get("npi") or record.get("objectID")

    return {
        "networks": [{"name": NETWORK_NAME, "tier": None}],
        "provider": {
            "unparsed_name": record.get("displayName", ""),
            "provider_type": provider_type,
            "npi": npi if is_valid_npi(npi) else None,
            ...
        },
        "addresses": [map_address(loc) for loc in record.get("locations", [])],
        "specialties": [...],
        ...
    }

async def run_normalize_phase(output_dir: Path, curr_date: str):
    """Normalize collected data to Ideon schema."""

    # Read from raw stores, deduplicate by NPI, write to JSONL
    providers_by_npi = {}

    for index_name in indices:
        store = create_store(str(output_dir / "raw" / f"{index_name.lower()}.db"))
        for key, page_data in store:
            for hit in page_data.get("hits", []):
                mapped = map_record(hit, index_name)
                npi = mapped["provider"]["npi"]
                if npi:
                    providers_by_npi[npi] = mapped
        store.close()

    output_file = output_dir / "processed" / f"slug-{curr_date}.jsonl"
    with JSONLWriter(str(output_file)) as writer:
        for record in providers_by_npi.values():
            writer.write(record)
```

### pipeline.py - Phase Orchestration

```python
"""Phase orchestration for scraper pipeline."""

from pathlib import Path
from core.qa import validate, sample, generate_debug_reports

async def run_phase_4(output_dir: Path, curr_date: str, prev_date: str | None):
    """Phase 4: QA validation."""
    output_file = output_dir / "processed" / f"slug-{curr_date}.jsonl"
    result = validate(str(output_file))
    return {"validation": result}

async def run_phase_5(output_dir: Path, curr_date: str, config):
    """Phase 5: Generate samples and debug reports."""
    output_file = output_dir / "processed" / f"slug-{curr_date}.jsonl"
    processed_dir = output_dir / "processed"

    # Generate samples
    sample(str(output_file), output_dir=str(processed_dir), count=config.sample_count)

    # Generate debug reports
    generate_debug_reports(
        jsonl_path=str(output_file),
        output_dir=str(processed_dir),
        curr_date=curr_date,
    )

async def run_pipeline(curr_date: str, prev_date: str | None, phases: list[int], ...):
    """Run the scraper pipeline."""
    output_dir = Path(__file__).parent / curr_date

    if 1 in phases:
        await run_phase_1(output_dir, config, fresh, dry_run)
    if 3 in phases:
        await run_phase_3(output_dir, curr_date)
    if 4 in phases:
        await run_phase_4(output_dir, curr_date, prev_date)
    if 5 in phases:
        await run_phase_5(output_dir, curr_date, config)
```

## Key Design Decisions

### Failure & Recovery

| Decision | Choice |
|----------|--------|
| Failure recovery | **Mandatory checkpointing** - all collectors must implement resume |
| Checkpoint format | **SQLite** - inside date folder (20260114/checkpoint.db) |
| Resume behavior | **Auto-resume default** - always resume if checkpoint exists, `--fresh` to override |

### Validation & Error Handling

| Decision | Choice |
|----------|--------|
| Phase 3 validation failure | **Halt phase** - stop immediately on schema error |
| Debug mode | **--dry-run flag** - show what would happen without executing |
| Config validation | **Strict Pydantic** - full validation at load, fail fast |

### Standards & Interfaces

| Decision | Choice |
|----------|--------|
| CLI framework | **Typer** - always use Typer for CLI args |
| Logging | **Use core.logging** - mandatory Loguru-based logging |
| Progress reporting | **tqdm** - with nested bars for phases |
| Retry strategy | **tenacity** - 3 retries, exponential backoff |

### NPI Mapping

| Decision | Choice |
|----------|--------|
| Individual providers | Use `npi` field, fallback to `objectID` |
| Organizations | Use `npiTypeII` field |
| Invalid NPI | Include record with `npi: null` |

## Core Module Dependencies

| Module | Purpose | Usage |
|--------|---------|-------|
| `core.logging` | Loguru-based logging | `setup_logging()`, `logger` |
| `core.io` | DataStore abstraction | `create_store()`, `JSONLWriter` |
| `core.mapper` | Normalization utilities | `normalize_zip_code()`, `normalize_phone()` |
| `core.qa` | Validation & reporting | `validate()`, `sample()`, `generate_debug_reports()` |

## .gitignore Template

```gitignore
20*
.env
__pycache__/
*.pyc
.DS_Store
```

## Migration Checklist

For each audiobee_* project:

1. **Create directory structure**: `src/`, `archive/`
2. **Create `config.yaml`** with project configuration
3. **Create `src/checkpoint.py`** with SQLite checkpoint
4. **Create `src/collector.py`** with mandatory checkpointing
5. **Create `src/mapper.py`** if custom mapping needed
6. **Create `pipeline.py`** with phase orchestration
7. **Create `run.py`** with Typer CLI
8. **Create `pyproject.toml`** with dependencies
9. **Create `CLAUDE.md`** with project documentation
10. **Create `.gitignore`** for output dirs
11. **Move legacy files** to `archive/`
12. **Test**:
    - `python run.py validate`
    - `python run.py run --curr YYYYMMDD --dry-run`
    - `python run.py run --curr YYYYMMDD`
    - Kill mid-run, verify resume works
    - `python run.py metrics`

## See Also

- `audiobee_peak/` - Reference implementation
- `audiobee_peak/CLAUDE.md` - Full project documentation
- `healthsparq/CLAUDE.md` - HealthSparq library pattern
- `core/io/CLAUDE.md` - DataStore abstraction
- `core/qa/CLAUDE.md` - QA module documentation
- `core/logging/CLAUDE.md` - Logging system

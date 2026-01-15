# Custom Carrier Architecture Pattern

This document defines a standardized architecture pattern for custom carrier scrapers (audiobee_* projects). All custom carriers should follow this structure for consistency.

> **Note**: This is a convention-based pattern, not a shared package. Each project has its own codebase but follows the same architecture.

## Quick Reference

| Component | Purpose |
|-----------|---------|
| `run.py` | Typer CLI entry point |
| `config.yaml` | Project configuration |
| `collector.py` | Phase 1: Data collection with checkpointing |
| `enricher.py` | Phase 2: Data enrichment (optional) |
| `mapper.py` | Custom normalization mapping (optional) |
| `pipeline.py` | Phase orchestration |

## Standard Project Structure

```
audiobee_{carrier}/
├── run.py                   # Typer CLI entry point (required)
├── config.yaml              # Project configuration (required)
├── collector.py             # Phase 1: Data collection (required)
├── enricher.py              # Phase 2: Data enrichment (optional)
├── mapper.py                # Custom normalization mapper (optional)
├── pipeline.py              # Phase orchestration (recommended)
├── utils.py                 # Project-specific utilities (optional)
├── pyproject.toml           # Dependencies with extras
├── .env                     # Secrets (gitignored)
├── data/                    # Static data (specialties, networks)
│   └── ...
└── {YYYYMMDD}/              # Output directories (auto-created)
    ├── checkpoint.db        # SQLite checkpoint for resume
    ├── metrics.json         # Phase metrics
    ├── raw/
    │   ├── collected/       # Phase 1 output
    │   └── enriched/        # Phase 2 output
    └── processed/
        └── {slug}-{date}.jsonl
```

## 5-Phase Pipeline

```
Phase 1 (Collect)     → Phase 2 (Enrich)    → Phase 3 (Normalize)
collector.py            enricher.py           core.mapper + mapper.py
PROJECT-SPECIFIC        PROJECT-SPECIFIC      SHARED + custom hooks
+ mandatory checkpoint  (optional)            Halts on validation error

Phase 4 (QA)          → Phase 5 (Report)    → Phase 6 (Recovery)
core.qa                 core.qa               Triggered by churn
SHARED                  SHARED                AUTO if providers missing
Tracks provider churn
```

| Phase | File | Responsibility | Checkpointing |
|-------|------|----------------|---------------|
| 1 | `collector.py` | Fetch raw provider data | **Mandatory** |
| 2 | `enricher.py` | Enrich with additional details | **Mandatory** if present |
| 3 | `mapper.py` + core | NPI dedup, schema mapping | N/A |
| 4 | core.qa | Validation, comparison, churn tracking | N/A |
| 5 | core.qa | Excel reports, samples, metrics CLI | N/A |
| 6 | project-specific | Recovery of missing providers | N/A |

## CLI Interface

```bash
# Basic run (auto-resumes from checkpoint)
python run.py run --curr 20260114

# Fresh run (ignore checkpoint)
python run.py run --curr 20260114 --fresh

# With previous date (enables comparison + recovery)
python run.py run --curr 20260114 --prev 20260107

# Phase control
python run.py run --curr 20260114 --phase 1        # Phase 1 only
python run.py run --curr 20260114 --phase 1-3      # Phases 1-3
python run.py run --curr 20260114 --phase 1,3,5    # Specific phases
python run.py run --curr 20260114 --from-phase 3   # From phase 3 onwards
python run.py run --curr 20260114 --skip-phase 2   # Skip phase 2

# QA and reporting
python run.py run --curr 20260114 --qa             # Include QA phase
python run.py run --curr 20260114 --report         # Include report phase

# Debug mode (verbose logging + bypass validation halt)
python run.py run --curr 20260114 --debug

# View metrics
python run.py metrics                              # Latest run
python run.py metrics --date 20260114              # Specific date

# Validation
python run.py validate
```

## Configuration (config.yaml)

```yaml
project:
  name: "Harvard Pilgrim"
  slug: "harvard_pilgrim"
  version: "1.0"

site:
  base_url: "https://api.harvardpilgrim.org"
  auth_type: oauth  # none, cookie, bearer, oauth, basic

coverage:
  states: [MA, ME, NH, CT]

# Carrier-specific configuration (nested allowed)
carrier_config:
  oauth:
    client_id: "${HPHC_CLIENT_ID}"
    client_secret: "${HPHC_CLIENT_SECRET}"
    scopes: ["read:providers"]
  custom_headers:
    X-Api-Version: "2.0"

phases:
  collect: true
  enrich: false
  custom_mapper: true
  normalize_input: collected  # or 'enriched' if Phase 2 runs

concurrency:
  max_workers: 50
  batch_size: 1000

output:
  storage_backend: sqlite
  separate_by_product: false
  phase1_output: collected
  phase2_output: enriched

session:
  browser_type: null  # camoufox, playwright, patchright, null for API-only
  proxy_types: [smartproxy_session]
  timeout_ms: 30000

# Optional sanity thresholds for QA
thresholds:
  min_providers: 10000
  max_providers: 500000
  max_churn_percent: 10
```

## Key Design Decisions

### Failure & Recovery

| Decision | Choice |
|----------|--------|
| Failure recovery | **Mandatory checkpointing** - all collectors must implement resume |
| Checkpoint format | **SQLite** - inside date folder (20260114/checkpoint.db) |
| Resume behavior | **Auto-resume default** - always resume if checkpoint exists, `--fresh` to override |
| Provider churn | **Always trigger recovery** - any missing providers attempt recovery |

### Validation & Error Handling

| Decision | Choice |
|----------|--------|
| Phase 3 validation failure | **Halt phase** - stop immediately on schema error |
| Debug mode | **Full debug mode** - `--debug` enables verbose logging + validation bypass |
| Config validation | **Strict Pydantic** - full validation at load, fail fast |
| Phase 3 input path | **Strict validation** - fail if input path empty or missing |

### Standards & Interfaces

| Decision | Choice |
|----------|--------|
| Anti-bot integration | **Standard interface** in `core.antibot` (Capsolver) |
| Logging | **Use core.logging** - mandatory, flexible format |
| Progress reporting | **Mandatory tqdm** from `core.progress` with nested bars |
| Retry strategy | **Standard in core.session** - 5 retries, 500ms base, exponential backoff |
| Metrics | **Mandatory** - write to metrics.json + CLI summary command |

### Configuration

| Decision | Choice |
|----------|--------|
| Storage keys | **Flexible keys** - project decides, document in config |
| Config extension | **carrier_config section** - explicit section, allows nesting |
| Secrets | **.env file support** - check .env, ../.env, ~/.env in order |
| Sanity thresholds | **Optional** - can define in config, Phase 4 uses if present |

### Technical Requirements

| Decision | Choice |
|----------|--------|
| Python version | **3.12+ required** |
| Project dependencies | **pyproject.toml extras** - grouped by feature + carrier bundles |
| Concurrency model | **Project implements** - each collector decides |
| Date semantics | **Single date only** - one run per date |

## Core Module Dependencies

| Module | Purpose | Status |
|--------|---------|--------|
| `core.logging` | Loguru-based logging with trace_id | ✅ Available |
| `core.io` | DataStore abstraction (SQLite/JSON/JSONL) | ✅ Available |
| `core.session` | Browser/HTTP session with retry | ✅ Available |
| `core.mapper` | NPI dedup, schema validation | ✅ Available |
| `core.qa` | Validation, comparison, reporting | ✅ Available |
| `core.progress` | Nested tqdm progress bars | ✅ Available |
| `core.antibot` | reCAPTCHA solving (Capsolver) | ✅ Available |

## Usage Examples

### Importing Core Modules

```python
# Progress bars
from core.progress import create_progress_bar, tqdm_logging

with tqdm_logging():
    for state in create_progress_bar(states, desc="States", position=0):
        for county in create_progress_bar(counties, desc="Counties", position=1, leave=False):
            process(state, county)

# CAPTCHA solving
from core.antibot import create_solver

solver = create_solver()
result = await solver.solve_recaptcha_v2(
    site_key="6Le-xxx",
    page_url="https://example.com",
)
token = result.token

# Logging
from core.logging import logger, setup_logging, set_trace_id

setup_logging(project_name="harvard_pilgrim", run_id="20260114")
set_trace_id(f"provider_{npi}")
logger.info("Processing provider")

# Storage
from core.io import create_store, BackendType

store = create_store("raw_data.db", backend=BackendType.SQLITE)
store.put("provider/123.json", {"npi": "123", ...})
```

### Checkpointing Pattern

```python
class Checkpoint:
    """SQLite-based checkpoint for resume capability."""

    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(db_path)
        self._init_tables()

    def _init_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS collected_ids (
                record_id TEXT PRIMARY KEY,
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def is_collected(self, record_id: str) -> bool:
        cur = self.conn.execute(
            "SELECT 1 FROM collected_ids WHERE record_id = ?", (record_id,)
        )
        return cur.fetchone() is not None

    def mark_collected(self, record_id: str):
        self.conn.execute(
            "INSERT OR REPLACE INTO collected_ids (record_id) VALUES (?)",
            (record_id,)
        )
        self.conn.commit()
```

## Migration Checklist

For each audiobee_* project:

1. **Create `config.yaml`** with strict Pydantic schema
2. **Create `collector.py`** with mandatory checkpointing
3. **Create `pipeline.py`** with phase orchestration
4. **Create `run.py`** with Typer CLI
5. **Create `pyproject.toml`** with extras
6. **Delete legacy files**: config.py, index_*.py, run_all.py
7. **Test**:
   - `python run.py validate`
   - `python run.py run --curr YYYYMMDD --dry-run`
   - Kill mid-run, verify resume with `--curr` (same date)
   - `python run.py metrics`

## See Also

- `healthsparq/CLAUDE.md` - Reference implementation for 6-phase pipeline
- `core/progress/CLAUDE.md` - Progress bar documentation
- `core/antibot/CLAUDE.md` - CAPTCHA solving documentation
- `core/io/CLAUDE.md` - DataStore abstraction
- `core/logging/CLAUDE.md` - Logging system

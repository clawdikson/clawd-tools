# Ideon Scraping Project

## AI Helpers

**Issue Tracking**: Use **Beads** (bd) for AI-native issue tracking. Break tasks into small components and delegate to subagents.

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

See @AGENTS.md for session completion workflow.

**Git Commits**: Use [Conventional Commits](https://www.conventionalcommits.org/):

| Type       | Description                         |
| ---------- | ----------------------------------- |
| `feat`     | New feature                         |
| `fix`      | Bug fix                             |
| `docs`     | Documentation only                  |
| `refactor` | Code restructuring (no feature/fix) |
| `perf`     | Performance improvement             |
| `test`     | Adding/fixing tests                 |
| `chore`    | Maintenance                         |

---

## Overview

**~86 web scrapers** extracting provider directory data from insurance carrier websites. Extracts NPIs, names, specialties, locations, and network affiliations for healthcare data aggregation.

**Execution Model**: Manual runs as needed (not automated/scheduled).

---

## Project Structure

```
scraping/
├── audiobee_*/              # ~86 individual scraper projects
│   ├── config.py            # Configuration (URLs, params, network IDs)
│   ├── index_1.py           # Phase 1: Search/Discovery
│   ├── index_2.py           # Phase 2: Detail extraction
│   ├── index_3.py           # Phase 3: Data mapping/normalization
│   └── run_all.py           # Orchestrator script
│
├── healthsparq/             # HealthSparq library v2.0 (23 projects)
│   ├── cli.py               # python -m healthsparq run <project>
│   ├── api.py               # run_scraper_sync(), ScraperResult
│   ├── configs/             # Project YAML files
│   └── CLAUDE.md            # Full documentation
│
├── core/                    # Shared package v3.0 (git submodule)
│   ├── io/                  # DataStore abstraction + SQLiteFS/JSONL
│   ├── session/             # Browser/HTTP session management
│   ├── mapper/              # Provider data normalization
│   ├── qa/                  # QA utilities (validation, comparison)
│   ├── logging/             # Loguru-based logging
│   └── CLAUDE.md            # Full documentation
│
├── tools/                   # Execution and automation tools
│   ├── run_parallel.py      # Parallel scraper execution
│   ├── upload_to_drive.py   # Google Drive uploader
│   ├── xlsx_to_clickup.py   # Report screenshots + email/ClickUp
│   ├── s3_uploader.py       # S3 uploads with presigned URLs
│   └── README.md            # Tools documentation
│
├── docs/                    # Documentation
│   ├── onboarding/          # Core guides (INDEX.md, ARCHITECTURE.md)
│   ├── extra/               # Advanced (PLAN.md, SCALABILITY.md)
│   └── CHANGELOG.md         # Recent enhancements
│
└── .beads/                  # Issue tracking database
```

## Site Type Architecture

| Type                  | Projects | Pattern                     | Tech                |
| --------------------- | -------- | --------------------------- | ------------------- |
| **Carrier**           | 32       | config.py → index_1/2/3.py  | REST APIs, httpx    |
| **HealthSparq**       | 23       | `python -m healthsparq run` | Browser auth + HTTP |
| **Sapphire**          | 14       | providerfinderonline.com    | Faceted search API  |
| **Anthem**            | 3        | Brand-specific URLs         | Complex hierarchies |
| **HealthTrioConnect** | 2        | Node.js + Python            | Browser automation  |
| **Werally**           | 3        | UHC Platform                | Grid search         |
| **Provider Lenz**     | 1        | Anti-bot                    | Captcha solving     |

---

## Essential Commands

### Running Scrapers

```bash
# Standard scraper
cd audiobee_bcbs_il
python run_all.py # Or: python index_1.py && python index_2.py && python index_3.py

# HealthSparq projects
python -m healthsparq list
python -m healthsparq run medica_sg --curr 20251226 --prev 20251110

# Parallel execution
python tools/run_parallel.py --list projects/api.txt --workers 8 --curr 20251210
```

### QA & Validation

```bash
# Use core/qa module (100x faster validation)
python -m core.qa validate providers.jsonl
python -m core.qa compare --curr 20251227 --prev 20251126
python -m core.qa report project_name --curr 20251227
```

### Upload & Distribution

```bash
# Google Drive upload
python tools/upload_to_drive.py audiobee_bcbs_il

# Email report with S3 upload
python tools/xlsx_to_clickup.py email audiobee_bcbs_il --to recipient@example.com

# ClickUp upload
python tools/xlsx_to_clickup.py run audiobee_bcbs_il --task CU12345
```

---

## Code Conventions

### Pipeline Architecture

```
Phase 1 (index_1.py): Discovery → {date}/raw/search_results/
Phase 2 (index_2.py): Details → {date}/raw/provider_details/
Phase 3 (index_3.py): Normalize → {date}/processed/
```

### Configuration Pattern

```python
PREV_DATE = "20251010"
CURR_DATE = "20251110"
PROJECT_NAME = "audiobee_*"

DIRS = {
    "raw": os.path.join(CURR_DATE, "raw"),
    "processed": os.path.join(CURR_DATE, "processed"),
}
```

### Output Schema

```json
{
  "npi": "1234567890",
  "first_name": "John",
  "last_name": "Smith",
  "specialty": "Family Medicine",
  "city": "Chicago",
  "state": "IL",
  "zip": "60601"
}
```

### Import Pattern

```python
try:
    from core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
```

---

## Key Libraries

### healthsparq/ - Library v2.0

```python
from healthsparq import load_config, run_scraper_sync, default_mapper

config = load_config("christus_health_plan")
result = run_scraper_sync(config, "20251227", mapper=my_mapper)
```

See `healthsparq/CLAUDE.md` for full documentation.

### core/ - Shared Package v3.0

```python
# DataStore abstraction
from core.io import create_store
store = create_store("raw_data.db")  # Auto-detects SQLite
store.put("provider/123.json", data)

# Session management
from core.session import ResilientBrowserSession
async with ResilientBrowserSession() as session:
    await session.login(url)

# Logging
from core.logging import logger, setup_logging
setup_logging(project_name="audiobee_bcbs_il", run_id="20251227")
```

See `core/CLAUDE.md` for full documentation.

---

## Developer Notes

1. **Dates**: Always update `PREV_DATE`/`CURR_DATE` in config.py before runs
2. **Prefer core/**: Use core implementations over reinventing
3. **Validation**: Run QA before completing runs
4. **Issue Tracking**: Use `bd` for multi-session work (not TodoWrite)
5. **SQLite**: Use `core/io/sqlite_fs.py` for 15x faster writes
6. **Credentials**: Never commit credential files (already in .gitignore)

---

## Documentation

| Topic             | Location                                  |
| ----------------- | ----------------------------------------- |
| Architecture      | `docs/onboarding/ARCHITECTURE.md`         |
| Pipeline details  | `docs/onboarding/PIPELINE.md`             |
| Platform patterns | `docs/onboarding/SITE_TYPES_REFERENCE.md` |
| Troubleshooting   | `docs/onboarding/TROUBLESHOOTING.md`      |
| Scaling plan      | `docs/extra/PLAN.md`                      |
| Recent changes    | `docs/CHANGELOG.md`                       |
| Tools setup       | `tools/README.md`                         |

---

## Subdirectory Contexts

Auto-load when accessing:

- `healthsparq/CLAUDE.md` - HealthSparq library v2.0
- `core/CLAUDE.md` - Shared utilities v3.0

## Essential Rules

1. Always update dates in config.py before runs
2. Prefer `core/` implementations over reinventing
3. Run QA validation before completing runs
4. Use `bd` for issue tracking with detailed descriptions
5. Delegate tasks to subagents with sufficient context

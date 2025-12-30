# Ideon Scraping Project

**~86 web scrapers** extracting provider directory data from insurance carrier websites.

## Issue Tracking (Beads)

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

See @AGENTS.md for session completion workflow.

## Quick Reference

| Site Type   | Projects | Run Command                                                   |
| ----------- | -------- | ------------------------------------------------------------- |
| Carrier     | 32       | `python index_1.py && python index_2.py && python index_3.py` |
| HealthSparq | 23       | `python -m healthsparq run <project> --curr YYYYMMDD`         |
| Sapphire    | 14       | `python run_all.py`                                           |
| Anthem      | 3        | `python run_all.py`                                           |
| Other       | 14       | Check project's `run_all.py` or `CLAUDE.md`                   |

| Key File     | Purpose                            |
| ------------ | ---------------------------------- |
| `config.py`  | URLs, params, PREV_DATE, CURR_DATE |
| `index_1.py` | Phase 1: Search/discovery          |
| `index_2.py` | Phase 2: Detail extraction         |
| `index_3.py` | Phase 3: Normalization             |
| `run_all.py` | Pipeline orchestrator              |

## Build Commands

```bash
# Submodule setup
./scripts/clone-submodules.sh

# Run scraper (standard pattern)
cd audiobee_<project>
# Update PREV_DATE/CURR_DATE in config.py
python run_all.py  # Or index_1.py → index_2.py → index_3.py

# HealthSparq projects
python -m healthsparq list
python -m healthsparq run medica_sg --curr 20251226 --prev 20251126

# Parallel execution
python tools/run_parallel.py --list projects/api.txt --workers 8 --curr 20251210

# Validation
python -m core.qa validate providers.jsonl
python -m core.qa compare --curr 20251227 --prev 20251126
```

## Pipeline Architecture

```
Phase 1 (index_1.py): Search/Discovery → {date}/raw/search_results/
Phase 2 (index_2.py): Detail Extraction → {date}/raw/provider_details/
Phase 3 (index_3.py): Normalization → {date}/processed/providers.jsonl
```

## Output Schema

```json
{
  "npi": "1234567890",
  "first_name": "John",
  "last_name": "Smith",
  "specialty": "Family Medicine",
  "address_line_1": "123 Main St",
  "city": "Chicago",
  "state": "IL",
  "zip": "60601",
  "phone": "312-555-0100",
  "network_id": "210002020",
  "accepting_new_patients": true
}
```

## Git Commits

Use [Conventional Commits](https://www.conventionalcommits.org/):

```bash
feat(scraper): add retry logic for rate-limited requests
fix(index_2): handle missing NPI in provider response
refactor(config): extract URL building to helper function
```

## Developer Notes

1. Always update `PREV_DATE`/`CURR_DATE` in config.py before runs
2. Prefer `core/` implementations over reinventing
3. Run validation (`python -m core.qa validate`) before completing runs
4. Use `bd` for issue tracking (not TodoWrite for multi-session work)
5. NPI-based deduplication is standard across all projects
6. SQLite storage (`core/io/sqlite_fs.py`) provides 15x faster writes

## Detailed Documentation

| Topic                  | Location                             |
| ---------------------- | ------------------------------------ |
| Project structure      | `docs/PROJECT_STRUCTURE.md`          |
| Architecture           | `docs/onboarding/ARCHITECTURE.md`    |
| Pipeline details       | `docs/onboarding/PIPELINE.md`        |
| Site-type patterns     | `docs/by-site-type/`                 |
| Troubleshooting        | `docs/onboarding/TROUBLESHOOTING.md` |
| Recent enhancements    | `docs/CHANGELOG.md`                  |
| Infrastructure scaling | `docs/extra/PLAN.md`                 |

## Subdirectory Contexts (Auto-load)

- `healthsparq/CLAUDE.md` - HealthSparq library v2.0 (23 projects)
- `core/CLAUDE.md` - Shared utilities v3.0 (logging, I/O, session, mapper, QA)
- `output_generator/CLAUDE.md` - Legacy QA (deprecated, use core/qa)

## Architectural Plans (In Progress)

| Plan                                               | Status | Description                                                                                                       |
| -------------------------------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------- |
| `plans/feat-sapphire-package.md`                   | Draft  | Consolidate 15 Sapphire/ProviderFinderOnline projects into `sapphire/` library following healthsparq architecture |
| `plans/feat-unified-scraping-framework.md`         | Draft  | Unified framework for all 94 scrapers with monorepo dependency management, YAML configs, and CLI interface        |
| `plans/refactor-sapphire-healthsparq-alignment.md` | Draft  | Align sapphire/ architecture with healthsparq/ patterns for consistency                                           |

**Sapphire Package** (Planned):

- 15 Sapphire projects → `sapphire/` library (similar to healthsparq/)
- YAML configuration, 5-phase pipeline (Discovery, Details, Normalize, QA, Report)
- Typer CLI: `python -m sapphire run <project> --curr YYYYMMDD`
- Browser queue session management (Camoufox/Playwright/Patchright)
- Geographic facet-based discovery with dual geo-coverage strategy

**Unified Framework** (Long-term):

- All 94 scrapers → `ideon/` framework with platform libraries
- Single virtualenv, shared dependencies via `uv` workspaces
- Platform abstraction: `ideon/platforms/{healthsparq,sapphire,carrier,anthem}/`
- Unified CLI: `python -m ideon run <project> --curr YYYYMMDD`
- Middleware: retry, rate-limit, proxy rotation, circuit breaker
- Monitoring: Prometheus metrics, structured JSON logs

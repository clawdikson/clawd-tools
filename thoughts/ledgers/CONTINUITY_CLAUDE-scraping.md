# Session: scraping

Updated: 2026-01-27T20:53:04.967Z

## Goal

Multi-purpose work on scraping monorepo:

1. Add new features to scraping infrastructure
2. Fix bugs and maintain existing scrapers
3. Refactor and improve architecture

Success criteria:

- Features work reliably across all platform types (healthsparq, sapphire)
- Bug fixes validated with tests
- Architectural improvements maintain backward compatibility
- All changes follow conventional commits pattern

## Constraints

- **Tech Stack**: Python 3.10+, uv package manager, Pydantic v2
- **Browser Automation**: Patchright (Playwright fork), Camoufox
- **HTTP Client**: httpx, curl-cffi
- **Storage**: SQLite (primary), JSONL, JSON Files via DataStore abstraction
- **Config**: Pydantic Settings with SCRAPER\_\* environment variables
- **CLI**: Typer (ALWAYS use Typer for CLI args)
- **Logging**: Loguru with structured logging
- **Package Manager**: uv (always use `.venv/bin/python` from base folder)
- **Framework**: Multi-platform architecture (core, healthsparq, sapphire)
- **Testing**: pytest with async support, coverage tracking
- **Build**: `uv sync` for dependencies
- **Test**: `.venv/bin/pytest -v`
- **Type Check**: `.venv/bin/mypy core/ healthsparq/ sapphire/`
- **Lint**: ruff (configured in pyproject.toml)
- **Commit Pattern**: Conventional Commits (feat/fix/refactor with scope)

### Architecture Patterns

- **Phase-based pipelines**:
  - HealthSparq (6 phases): Search → Details → Normalize → QA → Report → Recovery
  - Sapphire (5 phases): Discovery → Details → Normalize → QA → Report
- **DataStore abstraction**: Interchangeable SQLite/JSONL/JSON backends (15x faster writes with SQLite)
- **Multi-provider proxy**: Round-robin distribution via PROXY_TYPES env var (smartproxy_session, dataimpulse_rotating)
- **Pydantic Settings**: Site-type inheritance with SCRAPER\_\* environment variables
- **Structured logging**: Loguru with context preservation across async operations

### Key Documentation

- Main: `/Users/dikson/Work/ideon_scraping/scraping/CLAUDE.md`
- Core: `/Users/dikson/Work/ideon_scraping/scraping/core/CLAUDE.md`
- HealthSparq: `/Users/dikson/Work/ideon_scraping/scraping/healthsparq/CLAUDE.md`
- Sapphire: `/Users/dikson/Work/ideon_scraping/scraping/sapphire/CLAUDE.md`
- Module-specific: `core/*/CLAUDE.md` for each subsystem

## Key Decisions

### Git Submodule Structure (2026-01-15)
Each `audiobee_*` folder is a **separate git submodule**, not just a directory. When committing changes:
- Navigate into the specific `audiobee_*` folder first
- Commit within that submodule's git context
- The parent repo only tracks submodule references
- Same applies to `core/`, `healthsparq/`, `sapphire/` - all are submodules

## State

- Now: [→] Initial exploration complete, ready for tasks
- Next: Awaiting specific feature/bug/refactor request

## Working Set

- **Base Directory**: `/Users/dikson/Work/ideon_scraping/scraping/`
- **Python Interpreter**: `.venv/bin/python`
- **Entry Points**:
  - HealthSparq CLI: `.venv/bin/python -m healthsparq run <project>`
  - Sapphire CLI: `.venv/bin/python -m sapphire run <project>`
  - QA Validation: `.venv/bin/python -m core.qa validate <file>`
- **Test Command**: `.venv/bin/pytest core/tests/ healthsparq/tests/ sapphire/tests/ -v`
- **Type Check**: `.venv/bin/mypy core/ healthsparq/ sapphire/`
- **Git Branch**: master (current)

### Key Components

- **Core Libraries**:
  - `core/config/` - Pydantic Settings with site-type inheritance
  - `core/io/` - DataStore abstraction (JSONL/SQLite/JSON Files)
  - `core/logging/` - Loguru-based structured logging
  - `core/proxy/` - Multi-provider proxy orchestration
  - `core/session/` - Browser/HTTP session management
  - `core/qa/` - Validation, comparison, sampling, reporting
- **Platform Libraries**:
  - `healthsparq/` - HealthSparq browser automation (23 projects)
  - `sapphire/` - ProviderFinderOnline API scraping (15 projects)
- **Individual Scrapers**: 87+ audiobee\_\* projects (various platforms)
- **Recent Work**: Performance optimization task in thoughts/shared/plans/, submodule updates (core, sapphire)

## Open Questions

- UNCONFIRMED: Which specific features are highest priority?
- UNCONFIRMED: Are there known bugs needing immediate attention?
- UNCONFIRMED: What architectural improvements are most valuable?

## Codebase Summary

Python-based healthcare provider scraping monorepo with 87+ scraper projects and 3 shared platform libraries. Uses phase-based pipeline architecture (Search → Details → Normalize → QA → Report) with interchangeable storage backends (SQLite/JSONL/JSON). Multi-provider proxy orchestration for reliability. Built on Playwright for browser automation (healthsparq) and aiohttp for API scraping (sapphire). Comprehensive QA validation system with comparison, sampling, and reporting capabilities. All scrapers use Pydantic Settings with site-type inheritance for configuration.

## Agent Reports

### onboard (2026-01-10T19:56:18.337Z)

- Task:
- Summary:
- Output: `.claude/cache/agents/onboard/latest-output.md`

### onboard (2026-01-10T03:35:19.530Z)

- Task:
- Summary:
- Output: `.claude/cache/agents/onboard/latest-output.md`

### onboard (2026-01-10T03:34:03.206Z)

- Task:
- Summary:
- Output: `.claude/cache/agents/onboard/latest-output.md`

### onboard (2026-01-10T03:29:41.036Z)

- Task:
- Summary:
- Output: `.claude/cache/agents/onboard/latest-output.md`

### onboard (2026-01-10T03:27:14.711Z)

- Task:
- Summary:
- Output: `.claude/cache/agents/onboard/latest-output.md`

### onboard (2026-01-10T03:16:58.046Z)

- Task:
- Summary:
- Output: `.claude/cache/agents/onboard/latest-output.md`

### onboard (2026-01-10T03:06:23.006Z)

- Task:
- Summary:
- Output: `.claude/cache/agents/onboard/latest-output.md`

### onboard (2026-01-10T03:06:09.701Z)

- Task:
- Summary:
- Output: `.claude/cache/agents/onboard/latest-output.md`

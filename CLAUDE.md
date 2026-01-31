# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Scraping monorepo for healthcare provider directory data extraction. Contains 95+ individual scraper projects and 3 shared platform libraries.

**Repository Structure:**

- `core/` - Shared utilities (config, I/O, logging, proxy, session, QA)
- `healthsparq/` - HealthSparq platform library (23 projects)
- `sapphire/` - ProviderFinderOnline platform library (15 projects)
- `audiobee_*/` - Individual scraper projects (various platforms)

## Build & Run Commands

```bash
# Install dependencies (uv recommended)
uv sync

# IMPORTANT: Always use the venv in the base folder
# All python commands should use .venv/bin/python

# Run a healthsparq project
.venv/bin/python -m healthsparq run medica_sg --curr 20251230

# Run a sapphire project
.venv/bin/python -m sapphire run molina --curr 20251230

# Run QA validation
.venv/bin/python -m core.qa validate providers.jsonl

# Run tests
.venv/bin/pytest core/tests/ healthsparq/tests/ sapphire/tests/ -v
```

## Architecture

### Platform Libraries

| Library        | Platform                       | Projects | CLAUDE.md               |
| -------------- | ------------------------------ | -------- | ----------------------- |
| `healthsparq/` | HealthSparq browser automation | 23       | `healthsparq/CLAUDE.md` |
| `sapphire/`    | ProviderFinderOnline API       | 15       | `sapphire/CLAUDE.md`    |

### Core Package Modules

| Module          | Purpose                                         | CLAUDE.md                |
| --------------- | ----------------------------------------------- | ------------------------ |
| `core/config/`  | Pydantic Settings, site-type inheritance        | `core/config/CLAUDE.md`  |
| `core/io/`      | DataStore abstraction (JSONL/SQLite/JSON Files) | `core/io/CLAUDE.md`      |
| `core/logging/` | Loguru-based structured logging                 | `core/logging/CLAUDE.md` |
| `core/proxy/`   | Multi-provider proxy orchestration              | `core/proxy/CLAUDE.md`   |
| `core/session/` | Browser/HTTP session management                 | `core/session/CLAUDE.md` |
| `core/qa/`      | Validation, comparison, sampling, reporting     | `core/qa/CLAUDE.md`      |

### Phase Pipelines

Both platform libraries use similar multi-phase pipelines:

**HealthSparq (6 phases):** Search → Details → Normalize → QA → Report → Recovery

**Sapphire (5 phases):** Discovery → Details → Normalize → QA → Report

See `healthsparq/phases/CLAUDE.md` and `sapphire/phases/CLAUDE.md` for details.

## Common Patterns

### Environment Configuration

All scrapers use `SCRAPER_*` prefix environment variables:

```bash
SCRAPER_PROJECT_NAME=audiobee_bcbs_il
SCRAPER_CURR_DATE=20251230
SCRAPER_SITE_TYPE=healthsparq
```

### Storage Backends

Three interchangeable backends via DataStore abstraction:

- **SQLite** (default): 15x faster writes, best for production
- **JSON Files**: Human-readable, best for debugging
- **JSONL**: Streaming, append-only

### Proxy Configuration

```bash
PROXY_TYPES=smartproxy_session,dataimpulse_rotating
```

Multi-provider round-robin distribution by browser ID.

## Git Commits

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(healthsparq): add retry logic for search phase
fix(core): handle missing NPI in provider response
```

## Testing

```bash
# All tests
.venv/bin/pytest -v

# Specific package
.venv/bin/pytest healthsparq/tests/ -v

# Coverage
.venv/bin/pytest --cov=core --cov=healthsparq --cov=sapphire

# Type checking
.venv/bin/mypy core/ healthsparq/ sapphire/
```

## Submodule Documentation

Each module has its own CLAUDE.md with detailed API patterns:

- `core/CLAUDE.md` - Full core package documentation
- `healthsparq/CLAUDE.md` - CLI, library API, phase details
- `sapphire/CLAUDE.md` - CLI, library API, phase details
- `core/*/CLAUDE.md` - Module-specific patterns (io, session, proxy, etc.)


## Debugging Learnings

Real debugging cases from production scraper issues. Use these patterns when diagnosing problems.

### Cross-Platform Patterns

- **Legacy code issues:** When a legacy project has bugs (false drops, missing providers, 403s), first check if it needs migration to the new codebase (`healthsparq`/`sapphire` library). Migration often resolves multiple issues at once.
- **AutoQA validation:** Always check AutoQA code against reference implementations (e.g., Baylor Scott for HealthSparq). Outdated AutoQA scripts produce false drop reports.
- **False drops triage:** When false drops are identified, verify via AutoQA files whether the root cause is scraping (missing/corrupt raw data) vs mapping (incorrect normalization or network assignment).
- **Corrupt raw files:** Empty or truncated raw files indicate scraping occurred before the page/navigation fully loaded. Look for patterns in the corrupt files (same county, same specialty) to identify the trigger.

### Carrier-Specific (Algolia / Direct API)

- **High provider counts with DRILLDOWN_FACETS:** If counts remain above 20k even after applying all `DRILLDOWN_FACETS`, switch to zip code drilldown instead of county-level queries. Use Algolia params to filter by zip within each county.
- **Navigation timing:** Corrupt/empty raw HTML files can result from scraping before navigation completes. Add a static sleep after navigation actions before extracting HTML.
- **Identifying corrupt files:** Check if corrupt files share common search parameters (same county + specialty combo) to find the root cause pattern.

### Healthsparq-Specific (Browser Automation + API)

- **NPI keyword search returning wrong data:** NPI keyword search can return provider names (labels) instead of NPI IDs. Fix: add an intermediate search function using the search results API (phase 1) with fallback params to resolve NPIs correctly.
- **Multi-NPI orgs:** For organizations with multiple NPIs, the keyword fallback search may pull the same provider under different NPIs. Deduplicate or validate against expected NPI lists.
- **Network/plan code mapping:** Mapper functions must use filename/path info for plan code extraction. A common bug (especially in bluecard_national) is the mapper returning all networks when no plan codes are passed. Always pass the file path to the mapper and post-process filenames for plan code extraction.
- **Raw cache for debugging:** Store intermediate search-by-NPI/name data in the raw cache (DB). Without this data, root cause identification for false drops is significantly harder.

### Sapphire-Specific (ProviderFinderOnline / Proxy)

- **403 request blocking:** When seeing 403 errors, check in this order: (1) Is the proxy type appropriate? Session-based proxies are not ideal for all scenarios. (2) Is the codebase legacy and needs migration?
- **Proxy configuration:** Sapphire module accepts proxy via three sources in priority order: `config.yaml` > environment variable > default session-based fallback. After migrating a legacy project, immediately verify the proxy configuration.
- **Proxy type selection:** For sites that block aggressively, prefer `dataimpulse_rotating` over session-based proxies. Session proxies maintain the same IP which makes blocking easier for the target site.

## CLI Documentation
- Always use Typer for args in CLI.
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

# Run a healthsparq project
python -m healthsparq run medica_sg --curr 20251230

# Run a sapphire project
python -m sapphire run molina --curr 20251230

# Run QA validation
python -m core.qa validate providers.jsonl

# Run tests
pytest core/tests/ healthsparq/tests/ sapphire/tests/ -v
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
pytest -v

# Specific package
pytest healthsparq/tests/ -v

# Coverage
pytest --cov=core --cov=healthsparq --cov=sapphire

# Type checking
mypy core/ healthsparq/ sapphire/
```

## Submodule Documentation

Each module has its own CLAUDE.md with detailed API patterns:

- `core/CLAUDE.md` - Full core package documentation
- `healthsparq/CLAUDE.md` - CLI, library API, phase details
- `sapphire/CLAUDE.md` - CLI, library API, phase details
- `core/*/CLAUDE.md` - Module-specific patterns (io, session, proxy, etc.)

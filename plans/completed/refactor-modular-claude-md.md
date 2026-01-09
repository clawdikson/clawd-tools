# refactor(docs): Break Down CLAUDE.md into Modular Loadable Files

## Overview

Transform the monolithic 1109-line CLAUDE.md into a modular documentation structure using Claude Code's @-import syntax. This reduces base token consumption from ~8,000 tokens to ~500 tokens (94% reduction) while maintaining full documentation accessibility on-demand.

## Problem Statement / Motivation

**Current Pain Points:**

- Root CLAUDE.md is 1109 lines (~7,000-8,000 tokens)
- Loaded with EVERY Claude Code session, consuming significant context budget
- Most sessions only need 20% of the content
- Large context reduces available tokens for actual work

**Token Economics:**
| Metric | Current | Target |
|--------|---------|--------|
| Root CLAUDE.md | ~8,000 tokens | ~500 tokens |
| Typical session (2 modules) | 8,000 tokens | 1,300 tokens |
| Worst-case (5 modules) | 8,000 tokens | 2,500 tokens |
| **Savings** | - | 70-94% |

## Proposed Solution

### Directory Structure

```
scraping/
├── CLAUDE.md                        # Slim root (~60 lines)
├── docs/
│   └── claude/                      # NEW: Modular documentation
│       ├── PROJECT_OVERVIEW.md      # Project structure, purpose
│       ├── SITE_TYPES.md            # Carrier/HealthSparq/Sapphire patterns
│       ├── BUILD_COMMANDS.md        # Running scrapers, parallel execution
│       ├── CODE_CONVENTIONS.md      # Pipeline patterns, config patterns
│       ├── SHARED_UTILITIES.md      # core/, healthsparq/ API docs
│       └── RECENT_CHANGES.md        # DataStore, Mapper, Logging features
└── CLAUDE_LEGACY.md                 # Backup of original (for rollback)
```

### Root CLAUDE.md Structure (~60 lines)

````markdown
# Ideon Scraping Project

## Quick Reference

- **Purpose**: ~86 web scrapers for provider directory data extraction
- **Execution**: Manual runs (not automated)
- **Issue Tracking**: Use `bd` (Beads) - see @AGENTS.md

## Essential Commands

```bash
bd ready                # Find available work
bd show <id>            # View issue details
bd update <id> --status in_progress
bd close <id>           # Complete work
bd sync                 # Sync with git
```
````

## Git Commits

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `refactor`: Code restructuring

## Documentation Modules

Load as needed using @path syntax:

| Module                           | Content                              | When to Load                     |
| -------------------------------- | ------------------------------------ | -------------------------------- |
| @docs/claude/PROJECT_OVERVIEW.md | Project structure, ~86 scrapers      | First time understanding project |
| @docs/claude/SITE_TYPES.md       | Carrier/HealthSparq/Sapphire         | Working on specific scraper type |
| @docs/claude/BUILD_COMMANDS.md   | Running scrapers, parallel execution | Executing or debugging runs      |
| @docs/claude/CODE_CONVENTIONS.md | Pipeline patterns, config structure  | Writing or modifying code        |
| @docs/claude/SHARED_UTILITIES.md | core/, healthsparq/ API docs         | Using shared packages            |
| @docs/claude/RECENT_CHANGES.md   | DataStore, Mapper, Logging           | Working with Dec 2025 features   |

## Subdirectory Contexts

These load automatically when accessing their directories:

- `healthsparq/CLAUDE.md` - HealthSparq library (23 projects)
- `core/CLAUDE.md` - Shared utilities v3.0
- `output_generator/CLAUDE.md` - QA utilities

## Key Rules

- Prefer `core/` implementations over reinventing
- Run `type_check.py` before completing runs
- Update PREV_DATE/CURR_DATE in config.py before runs

````

## Technical Approach

### Module Content Allocation

| Module | Source Lines | Target Lines | Content |
|--------|--------------|--------------|---------|
| `PROJECT_OVERVIEW.md` | 51-333 | ~150 | Overview, project structure, site type architecture |
| `SITE_TYPES.md` | 219-333 | ~120 | Detailed site type patterns (extracted from above) |
| `BUILD_COMMANDS.md` | 337-403 | ~70 | Build commands, parallel execution, validation |
| `CODE_CONVENTIONS.md` | 407-517 | ~120 | Pipeline, config patterns, output schema |
| `SHARED_UTILITIES.md` | 548-800 | ~250 | core/, healthsparq/, output_generator docs |
| `RECENT_CHANGES.md` | 913-1103 | ~200 | DataStore, Mapper, Logging enhancements |

### Implementation Phases

#### Phase 1: Create Module Files
**Files to create:**

##### docs/claude/PROJECT_OVERVIEW.md
```markdown
# Project Overview

## Purpose
This repository contains **~86 web scrapers** for extracting provider directory data from insurance carrier websites.

## Project Structure
[Content from lines 65-217 of current CLAUDE.md]

## Site Type Summary
- **Carrier** (32 projects): Direct REST API integration
- **HealthSparq** (23 projects): Library v2.0 with CLI + programmatic API
- **Sapphire** (14 projects): ProviderFinderOnline platform
- **Anthem** (3 projects): Wellpoint infrastructure
- **Others**: HealthTrioConnect (2), Werally (3), Provider Lenz (1)

For detailed patterns, see @docs/claude/SITE_TYPES.md
````

##### docs/claude/SITE_TYPES.md

```markdown
# Site Type Architecture

## 1. Carrier (32 projects)

[Content from lines 223-240]

## 2. HealthSparq (23 projects)

[Content from lines 244-299]

## 3. Sapphire (14 projects)

[Content from lines 303-311]

## 4. Anthem (3 projects)

[Content from lines 315-323]

## 5-7. Others

[Content from lines 325-333]
```

##### docs/claude/BUILD_COMMANDS.md

```markdown
# Build & Development Commands

## Running a Scraper

[Content from lines 341-358]

## Parallel Execution

[Content from lines 360-368]

## HealthSparq Projects

[Content from lines 370-391]

## Validating Output

[Content from lines 393-401]
```

##### docs/claude/CODE_CONVENTIONS.md

```markdown
# Code Conventions

## Pipeline Architecture (3-4 Phases)

[Content from lines 411-437]

## Configuration Pattern (config.py)

[Content from lines 439-465]

## Output Schema

[Content from lines 467-485]

## Shared Package Pattern

[Content from lines 487-516]
```

##### docs/claude/SHARED_UTILITIES.md

```markdown
# Shared Utilities

## healthsparq/ - Importable Library v2.0

[Content from lines 552-617]

## healthsparq-server (Legacy)

[Content from lines 619-633]

## output_generator

[Content from lines 635-653]

## core/ - Shared Package v3.0

[Content from lines 655-798]
```

##### docs/claude/RECENT_CHANGES.md

```markdown
# Recent Enhancements (Dec 2025)

## DataStore Abstraction Layer

[Content from lines 915-970]

## Provider Data Mapper Module

[Content from lines 974-1024]

## Comprehensive Logging Enhancement

[Content from lines 1028-1067]

## HealthSparq Library Transformation (v2.0.0)

[Content from lines 1071-1102]
```

#### Phase 2: Update Root CLAUDE.md

- Replace current content with slim ~60-line version
- Add module reference table
- Preserve essential quick-reference commands
- Keep AI Helpers section (Beads, Conventional Commits)

#### Phase 3: Create Backup and Test

- Copy current CLAUDE.md to CLAUDE_LEGACY.md
- Test @-import syntax in fresh Claude Code session
- Verify all modules load correctly
- Test navigation between modules

## Acceptance Criteria

### Functional Requirements

- [ ] Root CLAUDE.md is under 80 lines
- [ ] All 6 module files created in docs/claude/
- [ ] All content from original CLAUDE.md is preserved (no orphaned sections)
- [ ] @-import references work correctly in Claude Code
- [ ] Subdirectory CLAUDE.md files (healthsparq/, core/) still function

### Non-Functional Requirements

- [ ] Token reduction: 70%+ for typical 2-module sessions
- [ ] Module files under 300 lines each
- [ ] No circular imports between modules
- [ ] All @-paths resolve from repository root

### Quality Gates

- [ ] CLAUDE_LEGACY.md backup created
- [ ] All @-file paths validated (no broken references)
- [ ] Tested with 5 common developer questions
- [ ] Documentation navigation is intuitive (subjective review)

## Dependencies & Prerequisites

**Required:**

- Current CLAUDE.md content (already available)
- docs/ directory structure (exists)

**No blockers identified.**

## Risk Analysis & Mitigation

| Risk                                  | Probability | Impact | Mitigation                                     |
| ------------------------------------- | ----------- | ------ | ---------------------------------------------- |
| Context accumulation in long sessions | HIGH        | MEDIUM | Keep modules <300 lines; document behavior     |
| Broken @-imports after file moves     | MEDIUM      | MEDIUM | Add CI validation for @-paths (future)         |
| Developer confusion during transition | MEDIUM      | LOW    | Document in root CLAUDE.md; keep LEGACY backup |
| Circular imports between modules      | LOW         | HIGH   | No cross-references between modules            |

## Implementation Notes

### Path Resolution

Claude Code resolves @-paths relative to the file containing the reference:

- `@docs/claude/SITE_TYPES.md` in root CLAUDE.md → `/scraping/docs/claude/SITE_TYPES.md`

### Context Persistence

Imported modules persist within a session. Multi-question conversations accumulate context:

- Question 1: Root (500 tokens) + SHARED_UTILITIES (600 tokens) = 1,100 tokens
- Question 2: Still 1,100 tokens (module already loaded)
- Question 3 + BUILD_COMMANDS: 1,100 + 400 = 1,500 tokens

Worst case (5 modules): ~2,500 tokens vs. 8,000 tokens original.

### AUTO-MANAGED Sections

Current CLAUDE.md has `<!-- AUTO-MANAGED -->` markers. Decision:

- **Keep in root CLAUDE.md**: Essential commands, AI Helpers
- **Move to modules without markers**: All other content (manual maintenance)

### Rollback Procedure

If issues arise:

```bash
# Quick rollback
mv CLAUDE.md CLAUDE_MODULAR.md
mv CLAUDE_LEGACY.md CLAUDE.md
```

## MVP

### CLAUDE.md (Root - ~60 lines)

````markdown
# Ideon Scraping Project

## AI Helpers

**Issue Tracking**: This project uses **Beads** (bd) - AI-native issue tracking.

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```
````

See @AGENTS.md for session completion workflow.

**Git Commits**: Use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `refactor`: Code restructuring

## Quick Reference

- **Purpose**: ~86 web scrapers for provider directory data
- **Execution**: Manual runs (not automated)

## Documentation Modules

Load as needed using @path syntax:

| Module                           | When to Load                       |
| -------------------------------- | ---------------------------------- |
| @docs/claude/PROJECT_OVERVIEW.md | Understanding project structure    |
| @docs/claude/SITE_TYPES.md       | Working on specific scraper type   |
| @docs/claude/BUILD_COMMANDS.md   | Running or debugging scrapers      |
| @docs/claude/CODE_CONVENTIONS.md | Writing or modifying code          |
| @docs/claude/SHARED_UTILITIES.md | Using core/, healthsparq/ packages |
| @docs/claude/RECENT_CHANGES.md   | Dec 2025 feature enhancements      |

## Subdirectory Contexts

Auto-load when accessing these directories:

- `healthsparq/CLAUDE.md` - HealthSparq library v2.0
- `core/CLAUDE.md` - Shared utilities v3.0
- `output_generator/CLAUDE.md` - QA utilities

## Essential Rules

1. Always update `PREV_DATE`/`CURR_DATE` in config.py before runs
2. Prefer `core/` implementations over reinventing
3. Run `type_check.py` before completing runs
4. Use `bd` for issue tracking (not TodoWrite for multi-session work)

````

### docs/claude/PROJECT_OVERVIEW.md

```markdown
# Project Overview

## Purpose

This repository contains **~86 web scrapers** for extracting provider directory data from insurance carrier websites. Each scraper targets a specific insurance plan/carrier and extracts provider information (NPIs, names, specialties, locations, network affiliations) for healthcare data aggregation.

**Execution Model**: Manual runs as needed (not automated/scheduled).

## Project Structure

````

scraping/
├── audiobee\_\*/ # ~86 individual scraper projects
│ ├── config.py # Configuration (URLs, params, network IDs)
│ ├── index_1.py # Phase 1: Search/Discovery
│ ├── index_2.py # Phase 2: Detail extraction
│ ├── index_3.py # Phase 3: Data mapping/normalization
│ ├── run_all.py # Orchestrator script
│ └── YYYYMMDD/ # Date-versioned output directories
│
├── healthsparq/ # HealthSparq library v2.0
├── core/ # Shared package v3.0 (submodule)
├── output_generator/ # Shared QA utilities
├── tools/ # Parallel execution tools
├── docs/ # Project documentation
└── .beads/ # Issue tracking database

```

## Site Type Summary

Projects categorized by underlying platform:

| Type | Count | Pattern |
|------|-------|---------|
| Carrier | 32 | Direct REST API integration |
| HealthSparq | 23 | Library v2.0 + CLI |
| Sapphire | 14 | ProviderFinderOnline API |
| Anthem | 3 | Wellpoint infrastructure |
| HealthTrioConnect | 2 | Node.js + Python hybrid |
| Werally | 3 | UHC grid-based search |
| Provider Lenz | 1 | Anti-bot protected |

For detailed patterns, see @docs/claude/SITE_TYPES.md

## Key Files Reference

| File | Purpose |
|------|---------|
| `config.py` | Project configuration (URLs, params, dates) |
| `index_1.py` | Phase 1: Search/discovery |
| `index_2.py` | Phase 2: Detail extraction |
| `index_3.py` | Phase 3: Data normalization |
| `run_all.py` | Pipeline orchestrator |

## Coverage Types

| Type | Description | Examples |
|------|-------------|----------|
| Medicare Advantage | Senior plans (65+) | audiobee_anthem, audiobee_humana |
| Medicaid | State-funded programs | audiobee_uhc_medicaid |
| ACA | Marketplace plans | audiobee_florida_blue |
| Large Group | Employer plans | audiobee_multiplan |
```

### docs/claude/BUILD_COMMANDS.md

````markdown
# Build & Development Commands

## Running a Scraper

```bash
# 1. Navigate to project
cd audiobee_bcbs_il

# 2. Update dates in config.py
PREV_DATE = "20251010"
CURR_DATE = "20251210"

# 3. Run phases sequentially
python index_1.py # Discovery
python index_2.py # Details
python index_3.py # Normalization

# Or use orchestrator
python run_all.py
```
````

## Parallel Execution

```bash
# Run API scrapers in parallel (from list)
python tools/run_parallel.py --list projects/api.txt --workers 8 --curr 20251210 --prev 20251110

# Run scrapers by pattern
python tools/run_parallel.py --pattern "audiobee_bcbs*" --workers 8 --curr 20251210 --prev 20251110
```

## HealthSparq Projects

```bash
# Install package (one-time)
cd healthsparq && pip install -e .

# List available projects
python -m healthsparq list

# Run scraper
python -m healthsparq run medica_sg --curr 20251226 --prev 20251110

# Run specific phase only
python -m healthsparq run medica_sg --curr 20251226 --phase 1 # Search
python -m healthsparq run medica_sg --curr 20251226 --phase 2 # Details
python -m healthsparq run medica_sg --curr 20251226 --phase 3 # Normalize

# Validate configuration
python -m healthsparq validate christus_health_plan
python -m healthsparq doctor # Validate all configs
```

## Validating Output

```bash
# Check output schema compliance
python output_generator/type_check.py audiobee_bcbs_il/

# Generate diff report vs previous run
python output_generator/comparison_creator.py audiobee_bcbs_il/
```

````

## References

### Internal References
- Current CLAUDE.md: `/Users/dikson/Work/ideon_scraping/scraping/CLAUDE.md`
- Existing healthsparq/CLAUDE.md: `healthsparq/CLAUDE.md`
- Existing core/CLAUDE.md: `core/CLAUDE.md`
- docs/onboarding/INDEX.md: `docs/onboarding/INDEX.md`

### External References
- Claude Code Memory Documentation: https://code.claude.com/docs/en/memory
- Claude Code Best Practices: https://www.anthropic.com/engineering/claude-code-best-practices
- @-Import Syntax Guide: https://stevekinney.com/courses/ai-development/referencing-files-in-claude-code
- Token Optimization Strategies: https://www.humanlayer.dev/blog/writing-a-good-claude-md

### Research Observations
- #5677: output_generator config has hardcoded paths that should migrate to core config
- #5679: Validation library comparison (Pydantic vs jsonschema vs fastjsonschema)
- #5680: orjson 6x faster than standard json library

## ERD (Documentation Structure)

```mermaid
graph TD
    A[CLAUDE.md<br/>~60 lines] -->|@docs/claude/| B[PROJECT_OVERVIEW.md<br/>~150 lines]
    A -->|@docs/claude/| C[SITE_TYPES.md<br/>~120 lines]
    A -->|@docs/claude/| D[BUILD_COMMANDS.md<br/>~70 lines]
    A -->|@docs/claude/| E[CODE_CONVENTIONS.md<br/>~120 lines]
    A -->|@docs/claude/| F[SHARED_UTILITIES.md<br/>~250 lines]
    A -->|@docs/claude/| G[RECENT_CHANGES.md<br/>~200 lines]

    A -->|@AGENTS.md| H[AGENTS.md]

    B -->|links to| C
    F -->|links to| I[healthsparq/CLAUDE.md]
    F -->|links to| J[core/CLAUDE.md]

    subgraph "Auto-loaded Subdirectory Contexts"
        I
        J
        K[output_generator/CLAUDE.md]
    end

    subgraph "New docs/claude/ Directory"
        B
        C
        D
        E
        F
        G
    end
````

## Checklist

- [ ] Create docs/claude/ directory
- [ ] Write PROJECT_OVERVIEW.md (~150 lines)
- [ ] Write SITE_TYPES.md (~120 lines)
- [ ] Write BUILD_COMMANDS.md (~70 lines)
- [ ] Write CODE_CONVENTIONS.md (~120 lines)
- [ ] Write SHARED_UTILITIES.md (~250 lines)
- [ ] Write RECENT_CHANGES.md (~200 lines)
- [ ] Backup current CLAUDE.md to CLAUDE_LEGACY.md
- [ ] Replace CLAUDE.md with slim ~60-line version
- [ ] Test @-imports in fresh Claude Code session
- [ ] Verify no broken references
- [ ] Update AGENTS.md if needed

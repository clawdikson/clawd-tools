# thoughts/

Working documents, plans, research, and session state for Claude Code sessions.

## Directory Structure

```
thoughts/
├── README.md                    # This file
├── ledgers/                     # Session continuity state
│   ├── CONTINUITY_CLAUDE-*.md   # Active continuity ledger
│   └── _archive/                # Archived session ledgers
│
└── shared/                      # Shared documents across sessions
    ├── plans/                   # Implementation plans and task tracking
    ├── research/                # Codebase research and exploration
    │   └── platform-architecture/  # Modular architecture docs
    └── handoffs/                # Session handoff documents
        ├── general/             # General handoffs
        └── scraping/            # Scraping-specific handoffs
```

## Document Types

### Ledgers (`ledgers/`)

Session continuity state for resuming work across Claude Code sessions.

**Active Ledgers**:
- `CONTINUITY_CLAUDE-scraping.md` - Main scraping project ledger

**Archived** (`_archive/`):
- Old session-specific ledgers (CONTINUITY_ses_*.md)

### Plans (`shared/plans/`)

Implementation plans with task tracking.

| File | Status | Description |
|------|--------|-------------|
| `performance-optimization-task.md` | Active | Performance optimization work |
| `healthsparq-cli-enhancements.md` | Active | CLI improvements |
| `sqlitefs-explorer-tui.md` | Active | TUI explorer for SQLite storage |
| `task_plan_phase3_optimization.md` | Complete | Phase 3 SQLite NPI map |

### Research (`shared/research/`)

Codebase exploration and architecture documentation.

**Platform Architecture** (`platform-architecture/`):
- `INDEX.md` - Navigation and overview
- `01-core-package.md` - Core utilities deep dive
- `02-healthsparq.md` - HealthSparq platform
- `03-sapphire.md` - Sapphire platform
- `04-patterns.md` - Cross-cutting architecture patterns
- `05-performance.md` - Performance optimizations

### Handoffs (`shared/handoffs/`)

Session handoff documents for context transfer.

**Types**:
- `general/` - General session handoffs
- `scraping/` - Scraping-specific handoffs
- Auto-compacted handoffs follow pattern: `YYYY-MM-DD_HH-MM-SS_auto-compact.md`

## Conventions

### File Naming

| Type | Pattern | Example |
|------|---------|---------|
| Plans | `{feature}-{type}.md` | `healthsparq-cli-enhancements.md` |
| Research | `YYYY-MM-DD-{topic}.md` | `2026-01-11-explore-core.md` |
| Handoffs | `YYYY-MM-DD_HH-MM-SS_{type}.md` | `2026-01-10_19-58-05_auto-compact.md` |
| Ledgers | `CONTINUITY_{scope}.md` | `CONTINUITY_CLAUDE-scraping.md` |

### Document Lifecycle

1. **Plans**: Created when starting feature work, marked complete when done
2. **Research**: Created during exploration, archived if superseded
3. **Handoffs**: Auto-generated on session end, archived after 7 days
4. **Ledgers**: Updated per session, archived when project scope changes

## Maintenance

### Archiving Stale Documents

```bash
# Archive old session ledgers
mv thoughts/ledgers/CONTINUITY_ses_*.md thoughts/ledgers/_archive/

# Archive old handoffs (older than 7 days)
find thoughts/shared/handoffs -name "*.md" -mtime +7 -exec mv {} thoughts/shared/handoffs/_archive/ \;
```

### Cleaning Up

```bash
# Remove empty directories
find thoughts -type d -empty -delete

# Find orphaned files at root level
ls thoughts/*.md  # Should only be README.md
```

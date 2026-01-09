# Ideon Scraping Project

## AI Helpers

**Issue Tracking**: This project uses **Beads** (bd) - AI-native issue tracking that lives in the repo.

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

See @AGENTS.md for landing-the-plane checklist and session completion workflow.

**Git Commits**: Use [Conventional Commits](https://www.conventionalcommits.org/) format:

| Type       | Description                         |
| ---------- | ----------------------------------- |
| `feat`     | New feature                         |
| `fix`      | Bug fix                             |
| `docs`     | Documentation only                  |
| `refactor` | Code restructuring (no feature/fix) |
| `perf`     | Performance improvement             |
| `test`     | Adding/fixing tests                 |
| `chore`    | Maintenance (no src/test change)    |

## Quick Reference

- **Purpose**: ~86 web scrapers for provider directory data extraction
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
4. Use `bd` for issue tracking (not TodoWrite for multi-session work). Provide enough context in the description along with important information for future usage.
5. Create enough contexts in .md files and delegate tasks to subagents.

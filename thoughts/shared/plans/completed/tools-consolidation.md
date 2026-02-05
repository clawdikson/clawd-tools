# Scraping Toolkit - TUI Dashboard

## Overview

Create an interactive TUI Dashboard that consolidates all scraping operations into a unified visual interface. CLI commands available as secondary interface for automation.

**Primary**: TUI Dashboard for interactive use
**Secondary**: Minimal CLI for scripting/automation

## TUI Dashboard Layout

```
┌─ Scraping Toolkit ──────────────────────────────────────────────────────────┐
│ [F1] Projects  [F2] Active Runs  [F3] Data  [F4] Validate  [F5] Settings    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─ Projects (95) ─────────────┐  ┌─ Details ─────────────────────────────┐ │
│  │ ▸ healthsparq/ (23)         │  │ audiobee_bcbs_il                      │ │
│  │   ├─ audiobee_bcbs_il    ✓  │  │                                       │ │
│  │   ├─ audiobee_bcbs_mn    ✓  │  │ Platform: healthsparq                 │ │
│  │   ├─ audiobee_wellmark   ⚠  │  │ Last Run: 2026-01-10 (20260110)       │ │
│  │   └─ ...                    │  │ Status: Complete                      │ │
│  │ ▸ sapphire/ (15)            │  │ Records: 150,234                      │ │
│  │ ▸ standalone/ (57)          │  │                                       │ │
│  │                             │  │ [R]un  [V]alidate  [D]ata  [L]ogs     │ │
│  └─────────────────────────────┘  └───────────────────────────────────────┘ │
│                                                                             │
├─ Status ────────────────────────────────────────────────────────────────────┤
│ Proxies: SmartProxy ✓ 98%  DataImpulse ✓ 95%  │  CPU: 45%  MEM: 8.2GB      │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Screens/Tabs

### Tab 1: Projects (F1)
- Tree view of all 95+ projects by platform
- Status indicators: ✓ healthy, ⚠ warning, ✗ error
- Quick actions: Run, Validate, View Data, View Logs
- Search/filter projects

### Tab 2: Active Runs (F2)
- Live view of running scrapers (cross-terminal via shared DB)
- Progress bars, phase info, error counts
- Actions: Pause, Resume, Stop, View Logs

### Tab 3: Data Explorer (F3)
- Embed existing `sqlitefs_explorer` functionality
- Browse any project's SQLiteFS database
- JSON viewer with syntax highlighting

### Tab 4: Validate (F4)
- Environment validation results
- Security scan results
- Migration validation
- One-click fix for common issues

### Tab 5: Settings (F5)
- Proxy configuration
- Default settings
- Theme (dark/light)

## Architecture

```
tools/
├── dashboard/
│   ├── __init__.py
│   ├── __main__.py          # Entry point
│   ├── app.py               # Main Textual App
│   ├── screens/
│   │   ├── __init__.py
│   │   ├── projects.py      # Projects browser
│   │   ├── runs.py          # Active runs monitor
│   │   ├── data.py          # Data explorer (wraps sqlitefs_explorer)
│   │   ├── validate.py      # Validation tools
│   │   └── settings.py      # Settings screen
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── project_tree.py  # Project tree widget
│   │   ├── run_card.py      # Active run card
│   │   ├── status_bar.py    # Bottom status bar
│   │   └── proxy_health.py  # Proxy health indicator
│   ├── services/
│   │   ├── __init__.py
│   │   ├── registry.py      # Project registry (from project_registry.py)
│   │   ├── runner.py        # Run scrapers, track status
│   │   ├── validator.py     # Validation logic (from validate_*.py)
│   │   └── proxy_monitor.py # Proxy health checks
│   └── state/
│       ├── __init__.py
│       └── shared.py        # Cross-terminal state (SQLite-based)
├── cli/                     # Minimal CLI for automation
│   ├── __init__.py
│   ├── __main__.py
│   └── app.py               # Simple Typer CLI
├── sqlitefs_explorer/       # Existing (reuse in data screen)
└── migrate_datastore/       # Existing (integrate into CLI)
```

## Cross-Terminal State

For "Active Runs" to show scrapers running in other terminals:

```python
# tools/dashboard/state/shared.py
import sqlite3
from pathlib import Path

STATE_DB = Path.home() / ".scraping-toolkit" / "state.db"

class SharedState:
    """SQLite-based state shared across terminals."""

    def register_run(self, project: str, pid: int, phase: str):
        """Register a running scraper."""

    def update_progress(self, project: str, progress: float, records: int):
        """Update run progress."""

    def get_active_runs(self) -> list[dict]:
        """Get all active runs across terminals."""

    def heartbeat(self, project: str):
        """Update heartbeat (detect stale runs)."""
```

## Implementation Phases

### Phase 1: Core Dashboard (MVP)
1. Create `tools/dashboard/` structure
2. Implement main app with tab navigation
3. Projects screen with tree view
4. Status bar with basic info

### Phase 2: Data Integration
1. Embed sqlitefs_explorer in Data tab
2. Wire project selection → data explorer
3. Add quick data stats

### Phase 3: Validation Screen
1. Port validate_env.py logic
2. Port find_hardcoded_credentials.py logic
3. Results display with fix actions

### Phase 4: Active Runs
1. Implement shared state DB
2. Modify healthsparq/sapphire to register runs
3. Live progress display

### Phase 5: Polish
1. Settings screen
2. Proxy health monitoring
3. Keyboard shortcuts
4. Theme support

## Minimal CLI (Secondary)

For scripting/automation:

```bash
# Just the essentials
scrape run <project> [--date YYYYMMDD]
scrape validate <project>
scrape data explore <db_path>
scrape data migrate <source> --to sqlite
```

## Keybindings

| Key | Action |
|-----|--------|
| `F1-F5` | Switch tabs |
| `↑/↓` | Navigate |
| `Enter` | Select/Expand |
| `r` | Run selected project |
| `v` | Validate selected |
| `d` | Open data explorer |
| `l` | View logs |
| `/` | Search |
| `q` | Quit |
| `?` | Help |

## File Changes

| File | Action |
|------|--------|
| `tools/dashboard/` | CREATE (new package) |
| `tools/cli/` | CREATE (minimal CLI) |
| `pyproject.toml` | MODIFY (add entry points) |
| `tools/sqlitefs_explorer/` | KEEP (reuse) |
| `tools/migrate_datastore/` | KEEP (reuse) |

## Entry Points

```toml
# pyproject.toml
[project.scripts]
scrape = "tools.cli:app"
scrape-dashboard = "tools.dashboard:main"
# Or just one:
# scrape = "tools.dashboard:main"  # TUI by default
# scrape --cli = CLI mode
```

## Success Criteria

- [ ] Launch dashboard with `scrape` or `python -m tools.dashboard`
- [ ] Navigate 95+ projects in tree view
- [ ] View project details and status
- [ ] Open data explorer for any project
- [ ] Run validation from dashboard
- [ ] See active runs across terminals
- [ ] Minimal CLI works for automation

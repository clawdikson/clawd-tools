# SQLiteFS Explorer TUI - Implementation Plan

## Overview

Create a Terminal User Interface (TUI) for exploring SQLiteFS databases, providing an intuitive file-browser experience for the virtual filesystem stored in SQLite.

**Target Users**: Developers debugging scraper data, QA verifying data integrity
**Primary Use Case**: Navigate and inspect JSON data stored in SQLiteFS without manual SQL queries

## Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **TUI Framework** | Textual | Modern, async-native, rich widget library, active development |
| **JSON Display** | rich.json | Already a dependency, excellent JSON formatting |
| **Icons** | Nerd Fonts (optional) | Enhanced visual hierarchy with file/folder icons |
| **Backend** | core.io.SQLiteFS | Existing abstraction, well-tested |

**Dependency Addition**: `textual>=0.70.0` (add to pyproject.toml - mature Worker API)

## Core Features

### Phase 1: MVP (Core Navigation)

1. **Database Selection**
   - CLI argument: `sqlitefs-explorer scraper.db`
   - Recent databases list (persisted to `~/.config/sqlitefs-explorer/recent.json`)

2. **Tree Navigation** (Left Panel - 40%)
   - Virtual directory tree derived from path prefixes
   - Unlimited lazy-loading with background threads (no file count limits)
   - Virtual scrolling - only renders visible nodes
   - Loading indicator with file count during expansion
   - Keyboard: `↑/↓` navigate, `Enter` expand/collapse, `→` expand, `←` collapse

3. **File Viewer** (Right Panel - 60%)
   - JSON syntax highlighting via `rich.json.JSON`
   - Line numbers
   - Scrollable for large JSON files

4. **Status Bar** (Bottom)
   - Current path
   - File count
   - Database size
   - Last modified timestamp

### Phase 2: Enhanced Inspection

5. **Search/Filter**
   - Path pattern filter: `Ctrl+F` → fuzzy search on paths
   - JSON content search: `Ctrl+G` → search within current JSON

6. **Quick Preview**
   - Hover/select shows JSON preview in bottom panel
   - Full view on `Enter`

7. **Statistics Panel** (`Tab` to toggle)
   - File count by prefix
   - Total size by directory
   - Schema analysis (common keys across records)

### Phase 3: Power Features

8. **Multi-Database Support**
   - Tabs for multiple .db files
   - Compare mode: side-by-side diff of same path in two DBs

9. **Export**
   - `E` to export current file to disk
   - `Shift+E` to export current directory

10. **SQL Console**
    - `Ctrl+Q` opens raw SQL query panel
    - Results displayed in table widget

## Architecture

```
tools/sqlitefs_explorer/
├── __init__.py
├── __main__.py          # Entry point
├── app.py               # Main Textual App class
├── widgets/
│   ├── __init__.py
│   ├── tree.py          # VirtualFSTree widget
│   ├── viewer.py        # JSONViewer widget
│   ├── search.py        # SearchModal widget
│   ├── stats.py         # StatsPanel widget
│   └── status.py        # StatusBar widget
├── models.py            # Data classes (FileNode, SearchResult)
├── backend.py           # SQLiteFS wrapper with caching
└── config.py            # Settings (recent DBs, preferences)
```

## Key Design Decisions

### 1. Virtual Directory Tree Construction

SQLiteFS stores flat paths like `20251230/raw/search/IL_60601.json`. We need to build a tree:

```python
def build_tree(paths: list[str]) -> dict:
    """Build nested dict from flat paths."""
    root = {}
    for path in paths:
        parts = path.split('/')
        node = root
        for part in parts[:-1]:  # Directories
            node = node.setdefault(part, {})
        node[parts[-1]] = None  # File (leaf)
    return root
```

### 2. Lazy Loading Strategy (Unlimited)

For databases with any number of files - no artificial limits:
- **Initial load**: Only top-level directories (depth=1)
- **On expand**: Stream children via generator, render incrementally
- **Virtual scrolling**: Only render visible items in viewport
- **Background loading**: Use Textual's Worker API with `post_message()` for thread-safe UI updates

```python
from collections.abc import Iterator
from dataclasses import dataclass
import sqlite3
from textual.message import Message
from textual.worker import Worker, get_current_worker

@dataclass
class ChildrenLoaded(Message):
    """Posted when background loading completes."""
    prefix: str
    children: list[str]
    is_complete: bool = True

class LazyTreeBackend:
    """Thread-safe lazy-loading backend for SQLiteFS.

    IMPORTANT: Uses separate read-only connection for worker threads
    to avoid lock contention with main SQLiteFS connection.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._children_cache: dict[str, list[str]] = {}
        self._loading: set[str] = set()

    def _get_readonly_conn(self) -> sqlite3.Connection:
        """Create a new read-only connection for worker thread."""
        conn = sqlite3.connect(
            f"file:{self.db_path}?mode=ro",
            uri=True,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        return conn

    def get_children_sync(self, prefix: str) -> list[str]:
        """Get children synchronously. Safe to call from main thread."""
        if prefix not in self._children_cache:
            self._children_cache[prefix] = list(self._iter_children(prefix))
        return self._children_cache[prefix]

    def _iter_children(self, prefix: str) -> Iterator[str]:
        """Stream immediate children (files AND directories) from SQLite.

        Returns unique immediate children under prefix:
        - For "20251230/raw/": returns ["20251230/raw/search", "20251230/raw/details", ...]
        - Distinguishes directories (have children) from files (leaf nodes)
        """
        conn = self._get_readonly_conn()
        try:
            normalized = prefix.rstrip('/') + '/' if prefix else ''
            prefix_len = len(normalized)

            # Query: Get all paths under prefix, extract first path component after prefix
            # This handles both files and directories correctly
            cursor = conn.execute("""
                SELECT DISTINCT
                    CASE
                        WHEN instr(substr(path, ?), '/') > 0
                        THEN substr(path, 1, ? + instr(substr(path, ?), '/') - 1)
                        ELSE path
                    END as child_path,
                    CASE
                        WHEN instr(substr(path, ?), '/') > 0 THEN 1
                        ELSE 0
                    END as is_dir
                FROM files
                WHERE path LIKE ?
                  AND length(path) > ?
                ORDER BY is_dir DESC, child_path
            """, (prefix_len + 1, prefix_len, prefix_len + 1,
                  prefix_len + 1, f"{normalized}%", prefix_len))

            seen = set()
            for row in cursor:
                child_path = row[0]
                if child_path and child_path not in seen:
                    seen.add(child_path)
                    yield child_path
        finally:
            conn.close()

    def get_child_count(self, prefix: str) -> int:
        """Get count without loading all children."""
        conn = self._get_readonly_conn()
        try:
            normalized = prefix.rstrip('/') + '/' if prefix else ''
            pattern = f"{normalized}%"
            row = conn.execute(
                "SELECT COUNT(*) FROM files WHERE path LIKE ?", (pattern,)
            ).fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    def is_directory(self, path: str) -> bool:
        """Check if path is a directory (has children) vs file (leaf)."""
        conn = self._get_readonly_conn()
        try:
            pattern = f"{path.rstrip('/')}/%"
            row = conn.execute(
                "SELECT 1 FROM files WHERE path LIKE ? LIMIT 1", (pattern,)
            ).fetchone()
            return row is not None
        finally:
            conn.close()


# In the Tree widget, use Textual's @work decorator:
class VirtualFSTree(Tree):
    """Tree widget with background loading via Textual Workers."""

    def __init__(self, backend: LazyTreeBackend):
        super().__init__("root")
        self.backend = backend

    @work(thread=True, exclusive=True, group="tree_load")
    def load_children_async(self, prefix: str) -> None:
        """Load children in background thread. Posts message when done."""
        worker = get_current_worker()

        children = []
        for child in self.backend._iter_children(prefix):
            if worker.is_cancelled:
                return  # Respect cancellation
            children.append(child)

        # Thread-safe: post_message() is safe from worker threads
        self.post_message(ChildrenLoaded(prefix=prefix, children=children))

    def on_children_loaded(self, event: ChildrenLoaded) -> None:
        """Handle loaded children on main thread (thread-safe)."""
        # Update tree nodes here - runs on main thread
        node = self._find_node(event.prefix)
        if node:
            for child in event.children:
                node.add(child, data={"path": child})
```

**Key Features:**
- **No limits**: All files accessible, regardless of count
- **Thread-safe**: Uses Textual's `@work(thread=True)` + `post_message()` pattern
- **Separate connections**: Worker threads use read-only SQLite connections (no lock contention)
- **Cancellable**: Checks `worker.is_cancelled` for clean shutdown
- **Correct SQL**: Handles both files and directories, sorts dirs first
- **Virtual scrolling**: Textual's Tree widget only renders visible nodes

### 3. JSON Viewer Implementation

```python
from textual.widgets import Static
from rich.json import JSON

class JSONViewer(Static):
    def __init__(self, data: dict | list | None = None):
        super().__init__()
        self._data = data

    def render(self) -> RenderResult:
        if self._data is None:
            return "Select a file to view"
        return JSON.from_data(self._data, indent=2)
```

### 4. Keybindings

| Key | Action |
|-----|--------|
| `q` | Quit |
| `↑/↓` | Navigate tree |
| `Enter` | Toggle expand / View file |
| `←/→` | Collapse/Expand directory |
| `Ctrl+F` | Search paths |
| `Ctrl+G` | Search in JSON |
| `Tab` | Toggle stats panel |
| `E` | Export current file |
| `?` | Help modal |
| `r` | Refresh tree |

## Implementation Steps

### Step 1: Bootstrap (2-3 files)
1. Add `textual` to pyproject.toml
2. Create `tools/sqlitefs_explorer/__main__.py` with CLI
3. Create `tools/sqlitefs_explorer/app.py` with basic App skeleton

### Step 2: Tree Widget (1 file)
1. Implement `VirtualFSTree` extending `textual.widgets.Tree`
2. Connect to SQLiteFS backend
3. Implement lazy loading

### Step 3: Viewer Widget (1 file)
1. Implement `JSONViewer` with syntax highlighting
2. Handle large JSON (>10MB) with truncation warning
3. Add line numbers

### Step 4: Integration
1. Wire tree selection to viewer
2. Add status bar
3. Implement keybindings

### Step 5: Polish
1. Add search modal
2. Add help modal
3. Handle edge cases (empty DB, corrupted JSON)

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `pyproject.toml` | MODIFY | Add textual>=0.47.0 dependency |
| `tools/sqlitefs_explorer/__init__.py` | CREATE | Package init |
| `tools/sqlitefs_explorer/__main__.py` | CREATE | CLI entry point with Typer |
| `tools/sqlitefs_explorer/app.py` | CREATE | Main Textual App (~150 lines) |
| `tools/sqlitefs_explorer/widgets/tree.py` | CREATE | Tree widget (~100 lines) |
| `tools/sqlitefs_explorer/widgets/viewer.py` | CREATE | JSON viewer (~80 lines) |
| `tools/sqlitefs_explorer/backend.py` | CREATE | SQLiteFS wrapper (~50 lines) |

**Estimated Total**: ~450 lines of code

## Usage Preview

```bash
# Basic usage
.venv/bin/python -m tools.sqlitefs_explorer scraper.db

# With path filter
.venv/bin/python -m tools.sqlitefs_explorer scraper.db --path "20251230/raw/"

# Compare two databases
.venv/bin/python -m tools.sqlitefs_explorer scraper.db --compare scraper_prev.db
```

## Mockup

```
┌─ SQLiteFS Explorer ─────────────────────────────────────────────────────────┐
│ 📁 scraper.db                                                    [?] Help   │
├──────────────────────────┬──────────────────────────────────────────────────┤
│ 📂 20251230              │ {                                                │
│   📂 raw                 │   "npi": "1234567890",                          │
│     📂 search            │   "first_name": "John",                         │
│       📄 IL_60601.json   │   "last_name": "Smith",                         │
│       📄 IL_60602.json   │   "specialty": "Family Medicine",               │
│     📂 details           │   "locations": [                                │
│       📄 123456789...  ◀ │     {                                           │
│       📄 098765432...    │       "address_line_1": "123 Main St",          │
│   📂 processed           │       "city": "Chicago",                        │
│     📄 providers.json    │       "state": "IL",                            │
│                          │       "zip": "60601"                            │
│                          │     }                                           │
│                          │   ]                                             │
│                          │ }                                               │
├──────────────────────────┴──────────────────────────────────────────────────┤
│ Path: 20251230/raw/details/1234567890.json │ Files: 150,234 │ Size: 2.3 GB │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Large databases (>1M files) | Slow tree loading | Unlimited lazy loading with background threads + virtual scrolling |
| Very large directories (>100k children) | Memory for child list | Stream via cursor, cache on demand, show count first |
| Large JSON files (>10MB) | Memory/render issues | Truncate with "Load more" option |
| Corrupted JSON in DB | Viewer crash | Try/except with error display |
| Textual API changes | Breaking updates | Pin version, test on update |
| Background thread contention | Race conditions | Thread-safe cache with loading set guard |

## Success Criteria

- [ ] Open any SQLiteFS database file
- [ ] Navigate tree with keyboard
- [ ] View JSON with syntax highlighting
- [ ] Search paths with fuzzy matching
- [ ] Responsive with unlimited files (no artificial limits)
- [ ] Background loading keeps UI responsive during large dir expansion
- [ ] No crashes on malformed data

## Future Enhancements (Out of Scope)

- Edit mode (modify JSON in place)
- Database schema migration tool
- Integration with healthsparq/sapphire CLI
- VSCode extension

---

## Risk Mitigations (Pre-Mortem 2026-01-11)

### Tigers Addressed

1. **Threading + UI Update Pattern** (HIGH → MITIGATED)
   - **Original Risk**: Plan used raw `threading.Thread` with callback, which crashes Textual
   - **Mitigation**: Replaced with Textual's `@work(thread=True)` decorator + `post_message()` pattern
   - **Location**: Section 2 "Lazy Loading Strategy" completely rewritten

2. **SQLite Connection Thread Safety** (HIGH → MITIGATED)
   - **Original Risk**: Background threads accessing main SQLiteFS connection without locks
   - **Mitigation**: Worker threads now create separate read-only connections via `file:path?mode=ro` URI
   - **Location**: `LazyTreeBackend._get_readonly_conn()` method added

3. **Dependency Version** (MEDIUM → MITIGATED)
   - **Original Risk**: `textual>=0.47.0` too old, Worker API immature
   - **Mitigation**: Updated to `textual>=0.70.0` (stable Worker API, mature message passing)
   - **Location**: Technology Stack section

### Elephant Addressed

1. **SQL Query Logic** (MEDIUM → MITIGATED)
   - **Original Risk**: `instr(substr(...), '/')` returns 0 for leaf files, can't distinguish dirs from files
   - **Mitigation**: Rewrote SQL with CASE expression to handle both directories and files correctly
   - **Location**: `_iter_children()` method now uses proper path parsing with `is_dir` flag

### Accepted Risks

None - all identified risks mitigated.

### Pre-Mortem Details
- **Date**: 2026-01-11
- **Mode**: Deep
- **Tigers Found**: 3 (all HIGH/MEDIUM)
- **Elephants Found**: 1
- **Paper Tigers**: 2 (large JSON, corrupted data)

### References
- [Textual Workers Guide](https://textual.textualize.io/guide/workers/)
- [SQLite URI mode=ro](https://www.sqlite.org/uri.html)

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

---

## Phase 2: Enhanced Features

**Date**: 2026-01-12
**Author**: Planning Agent
**Status**: Planned

### Overview

This phase enhances the SQLiteFS Explorer TUI with metadata display, search functionality, filters, and additional features inspired by popular terminal file managers like [ranger](https://github.com/ranger/ranger), [nnn](https://github.com/jarun/nnn), [lf](https://www.ghacks.net/2021/04/13/lf-is-a-terminal-file-manager-inspired-by-ranger-with-vim-like-shortcuts/), and [yazi](https://www.x-cmd.com/install/25-ls/).

### Current State Analysis

The Phase 1 implementation includes:
- **app.py**: Main Textual App with tree/viewer split (40%/60%), StatusBar showing path/count/size
- **backend.py**: LazyTreeBackend with read-only SQLite connections, children caching
- **widgets/tree.py**: VirtualFSTree with async background loading via Workers
- **widgets/viewer.py**: JSONViewer with rich.json rendering, truncation warnings

**SQLiteFS Schema** (from `core/io/sqlite_fs.py`):
```sql
CREATE TABLE files (
    path TEXT PRIMARY KEY,
    data BLOB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Available Metadata**:
- `path`: Full virtual path
- `data`: File content (BLOB)
- `created_at`: Creation timestamp
- `updated_at`: Last modification timestamp
- File size: `length(data)`

### Feature 1: Metadata Display (Size & Dates)

#### 1.1 Schema Extension for Metadata Queries

Add new backend methods to retrieve file metadata:

```python
# backend.py additions

def get_file_metadata(self, path: str) -> dict | None:
    """Get metadata for a single file."""
    conn = self._get_readonly_conn()
    try:
        row = conn.execute("""
            SELECT
                path,
                length(data) as size,
                created_at,
                updated_at
            FROM files
            WHERE path = ?
        """, (path,)).fetchone()
        if row:
            return {
                "path": row[0],
                "size": row[1],
                "created_at": row[2],
                "updated_at": row[3],
            }
        return None
    finally:
        conn.close()

def get_children_with_metadata(self, prefix: str) -> list[dict]:
    """Get children with size and date metadata for directory listing."""
    conn = self._get_readonly_conn()
    try:
        normalized = prefix.rstrip('/') + '/' if prefix else ''
        prefix_len = len(normalized)

        # Get all files under prefix with metadata
        cursor = conn.execute("""
            SELECT
                path,
                length(data) as size,
                created_at,
                updated_at
            FROM files
            WHERE path LIKE ?
        """, (f"{normalized}%",))

        # Build children with aggregated metadata
        children = {}
        for row in cursor:
            full_path = row[0]
            relative = full_path[prefix_len:] if normalized else full_path

            # Get immediate child name
            if '/' in relative:
                child_name = relative.split('/')[0]
                child_path = f"{normalized}{child_name}" if normalized else child_name
                is_dir = True
            else:
                child_name = relative
                child_path = full_path
                is_dir = False

            if child_path not in children:
                children[child_path] = {
                    "path": child_path,
                    "name": child_name,
                    "is_dir": is_dir,
                    "size": 0,
                    "file_count": 0,
                    "newest_update": None,
                    "oldest_create": None,
                }

            # Aggregate stats
            children[child_path]["size"] += row[1] or 0
            children[child_path]["file_count"] += 1

            if row[3]:  # updated_at
                if children[child_path]["newest_update"] is None:
                    children[child_path]["newest_update"] = row[3]
                else:
                    children[child_path]["newest_update"] = max(
                        children[child_path]["newest_update"], row[3]
                    )

            if row[2]:  # created_at
                if children[child_path]["oldest_create"] is None:
                    children[child_path]["oldest_create"] = row[2]
                else:
                    children[child_path]["oldest_create"] = min(
                        children[child_path]["oldest_create"], row[2]
                    )

        # Sort: directories first, then by name
        return sorted(
            children.values(),
            key=lambda x: (not x["is_dir"], x["name"].lower())
        )
    finally:
        conn.close()
```

#### 1.2 Tree Widget Enhancement

Modify `VirtualFSTree` to display metadata alongside file names:

```python
# widgets/tree.py modifications

from dataclasses import dataclass
from textual.reactive import reactive

@dataclass
class DisplaySettings:
    """Settings for tree display."""
    show_size: bool = True
    show_date: bool = True
    date_format: str = "%Y-%m-%d %H:%M"
    size_format: str = "human"  # "human", "bytes", "kb", "mb"

class VirtualFSTree(Tree[str]):
    """Enhanced tree with metadata display."""

    display_settings: reactive[DisplaySettings] = reactive(DisplaySettings)

    def format_node_label(self, name: str, metadata: dict) -> str:
        """Format tree node label with optional metadata."""
        parts = [name]

        if self.display_settings.show_size and metadata.get("size"):
            size_str = self._format_size(metadata["size"])
            parts.append(f"[dim]{size_str}[/dim]")

        if self.display_settings.show_date and metadata.get("newest_update"):
            date_str = self._format_date(metadata["newest_update"])
            parts.append(f"[dim]{date_str}[/dim]")

        if metadata.get("is_dir") and metadata.get("file_count", 0) > 1:
            parts.append(f"[dim]({metadata['file_count']} files)[/dim]")

        return "  ".join(parts)

    def _format_size(self, size: int) -> str:
        """Format byte size to human-readable string."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"

    def _format_date(self, date_str: str) -> str:
        """Format date string for display."""
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.strftime(self.display_settings.date_format)
        except (ValueError, AttributeError):
            return date_str[:10] if date_str else ""
```

#### 1.3 Toggle Keybindings

| Key | Action |
|-----|--------|
| `s` | Toggle size display |
| `d` | Toggle date display |
| `m` | Toggle all metadata |
| `S` | Cycle size format (human/bytes/KB/MB) |

```python
# app.py additions

BINDINGS = [
    # ... existing bindings ...
    Binding("s", "toggle_size", "Toggle Size"),
    Binding("d", "toggle_date", "Toggle Date"),
    Binding("m", "toggle_metadata", "Toggle All Metadata"),
    Binding("S", "cycle_size_format", "Cycle Size Format"),
]

def action_toggle_size(self) -> None:
    """Toggle size display in tree."""
    tree = self.query_one("#tree", VirtualFSTree)
    settings = tree.display_settings
    tree.display_settings = DisplaySettings(
        show_size=not settings.show_size,
        show_date=settings.show_date,
        date_format=settings.date_format,
        size_format=settings.size_format,
    )
    tree.refresh_tree()
```

### Feature 2: Search Functionality

#### 2.1 Path Search Modal

Create a fuzzy search modal for paths using Textual's Input widget:

```python
# widgets/search.py (new file)

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Input, ListView, ListItem, Static
from textual.containers import Vertical
from dataclasses import dataclass
from textual.message import Message

@dataclass
class SearchResult:
    """A search result with path and match score."""
    path: str
    score: float
    is_dir: bool

class PathSearchModal(ModalScreen[str | None]):
    """Modal for fuzzy path search."""

    CSS = """
    PathSearchModal {
        align: center middle;
    }

    #search-container {
        width: 80%;
        height: 60%;
        background: $surface;
        border: solid $primary;
        padding: 1;
    }

    #search-input {
        dock: top;
        margin-bottom: 1;
    }

    #search-results {
        height: 1fr;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "select", "Select"),
    ]

    def __init__(self, backend, max_results: int = 100):
        super().__init__()
        self.backend = backend
        self.max_results = max_results
        self._all_paths: list[str] = []
        self._results: list[SearchResult] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="search-container"):
            yield Static("Search paths (fuzzy match):", classes="title")
            yield Input(placeholder="Type to search...", id="search-input")
            yield ListView(id="search-results")

    async def on_mount(self) -> None:
        """Load all paths for searching."""
        self._all_paths = list(self.backend.iter_all_paths())
        self.query_one("#search-input").focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Update results on input change."""
        query = event.value.lower()

        if not query:
            self._results = []
        else:
            # Fuzzy match scoring
            self._results = self._fuzzy_search(query)

        self._update_results_list()

    def _fuzzy_search(self, query: str) -> list[SearchResult]:
        """Perform fuzzy search on paths."""
        results = []

        for path in self._all_paths:
            score = self._fuzzy_score(query, path.lower())
            if score > 0:
                is_dir = self.backend.is_directory(path)
                results.append(SearchResult(path=path, score=score, is_dir=is_dir))

        # Sort by score descending, limit results
        results.sort(key=lambda r: -r.score)
        return results[:self.max_results]

    def _fuzzy_score(self, query: str, target: str) -> float:
        """Calculate fuzzy match score (0-1)."""
        # Simple substring matching with position bonus
        if query in target:
            # Exact substring match
            pos = target.index(query)
            return 1.0 - (pos / len(target)) * 0.5

        # Character-by-character fuzzy match
        query_idx = 0
        score = 0.0
        last_match_pos = -1

        for i, char in enumerate(target):
            if query_idx < len(query) and char == query[query_idx]:
                # Bonus for consecutive matches
                if last_match_pos == i - 1:
                    score += 0.2
                else:
                    score += 0.1
                last_match_pos = i
                query_idx += 1

        if query_idx == len(query):
            return score / len(query)
        return 0.0

    def _update_results_list(self) -> None:
        """Update the ListView with current results."""
        list_view = self.query_one("#search-results", ListView)
        list_view.clear()

        for result in self._results:
            icon = "📂" if result.is_dir else "📄"
            label = f"{icon} {result.path}"
            list_view.append(ListItem(Static(label), id=f"result-{hash(result.path)}"))

    def action_select(self) -> None:
        """Select current result."""
        if self._results:
            list_view = self.query_one("#search-results", ListView)
            idx = list_view.index
            if idx is not None and idx < len(self._results):
                self.dismiss(self._results[idx].path)
            elif self._results:
                self.dismiss(self._results[0].path)
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        """Cancel search."""
        self.dismiss(None)
```

#### 2.2 Content Search

Search within JSON content of files:

```python
# widgets/search.py additions

class ContentSearchModal(ModalScreen[list[str]]):
    """Modal for searching file contents."""

    def __init__(self, backend, search_type: str = "key"):
        """
        Args:
            backend: LazyTreeBackend instance
            search_type: "key" for JSON keys, "value" for values, "any" for both
        """
        super().__init__()
        self.backend = backend
        self.search_type = search_type

    def compose(self) -> ComposeResult:
        with Vertical(id="search-container"):
            yield Static(f"Search file contents ({self.search_type}):", classes="title")
            yield Input(placeholder="Search term...", id="search-input")
            yield Static("", id="search-status")
            yield ListView(id="search-results")

    @work(thread=True)
    def search_contents(self, query: str) -> None:
        """Search file contents in background."""
        worker = get_current_worker()
        results = []
        searched = 0

        for path, data in self.backend.iter_all_files():
            if worker.is_cancelled:
                return

            searched += 1
            if searched % 100 == 0:
                self.post_message(SearchProgress(searched=searched))

            try:
                content = json.loads(data.decode("utf-8"))
                if self._matches(query, content):
                    results.append(path)
                    if len(results) >= 100:
                        break
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

        self.post_message(SearchComplete(results=results, searched=searched))

    def _matches(self, query: str, obj: dict | list, depth: int = 0) -> bool:
        """Check if query matches object keys/values."""
        if depth > 10:  # Prevent infinite recursion
            return False

        query_lower = query.lower()

        if isinstance(obj, dict):
            for key, value in obj.items():
                if self.search_type in ("key", "any"):
                    if query_lower in str(key).lower():
                        return True
                if self.search_type in ("value", "any"):
                    if isinstance(value, str) and query_lower in value.lower():
                        return True
                if isinstance(value, (dict, list)):
                    if self._matches(query, value, depth + 1):
                        return True
        elif isinstance(obj, list):
            for item in obj:
                if self._matches(query, item, depth + 1):
                    return True
        elif self.search_type in ("value", "any"):
            if query_lower in str(obj).lower():
                return True

        return False
```

#### 2.3 Backend Additions for Search

```python
# backend.py additions

def iter_all_paths(self) -> Iterator[str]:
    """Iterate all file paths in database."""
    conn = self._get_readonly_conn()
    try:
        cursor = conn.execute("SELECT path FROM files ORDER BY path")
        for row in cursor:
            yield row[0]
    finally:
        conn.close()

def iter_all_files(self) -> Iterator[tuple[str, bytes]]:
    """Iterate all files with content (for content search)."""
    conn = self._get_readonly_conn()
    try:
        cursor = conn.execute("SELECT path, data FROM files")
        for row in cursor:
            yield row[0], row[1]
    finally:
        conn.close()
```

### Feature 3: Filters

#### 3.1 Filter Types

| Filter | Description | Example |
|--------|-------------|---------|
| **Extension** | Filter by file extension | `.json`, `.jsonl` |
| **Size** | Filter by file size range | `>1MB`, `<100KB`, `1MB-10MB` |
| **Date** | Filter by date range | `today`, `last7d`, `2026-01-01..2026-01-12` |
| **Path Pattern** | Glob pattern match | `**/search/*.json`, `20251230/**` |

#### 3.2 Filter Implementation

```python
# models.py (new file)

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal
import fnmatch
import re

@dataclass
class FilterConfig:
    """Configuration for file filtering."""

    # Extension filter
    extensions: list[str] = field(default_factory=list)  # e.g., [".json", ".jsonl"]

    # Size filter (in bytes)
    min_size: int | None = None
    max_size: int | None = None

    # Date filter
    date_from: datetime | None = None
    date_to: datetime | None = None
    date_field: Literal["created", "updated"] = "updated"

    # Path pattern (glob)
    path_pattern: str | None = None

    def matches(self, path: str, size: int, created: str, updated: str) -> bool:
        """Check if file matches all active filters."""
        # Extension check
        if self.extensions:
            ext = "." + path.rsplit(".", 1)[-1] if "." in path else ""
            if ext.lower() not in [e.lower() for e in self.extensions]:
                return False

        # Size check
        if self.min_size is not None and size < self.min_size:
            return False
        if self.max_size is not None and size > self.max_size:
            return False

        # Date check
        if self.date_from or self.date_to:
            date_str = updated if self.date_field == "updated" else created
            try:
                file_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                if self.date_from and file_date < self.date_from:
                    return False
                if self.date_to and file_date > self.date_to:
                    return False
            except (ValueError, AttributeError):
                return False

        # Path pattern check
        if self.path_pattern:
            if not fnmatch.fnmatch(path, self.path_pattern):
                return False

        return True

    @classmethod
    def parse_size(cls, size_str: str) -> int:
        """Parse size string like '10MB' to bytes."""
        match = re.match(r"(\d+(?:\.\d+)?)\s*(B|KB|MB|GB|TB)?", size_str, re.I)
        if not match:
            raise ValueError(f"Invalid size: {size_str}")

        value = float(match.group(1))
        unit = (match.group(2) or "B").upper()

        multipliers = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
        return int(value * multipliers[unit])

    @classmethod
    def parse_date_range(cls, date_str: str) -> tuple[datetime | None, datetime | None]:
        """Parse date range string."""
        now = datetime.now()

        if date_str == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return start, now
        elif date_str == "yesterday":
            yesterday = now - timedelta(days=1)
            start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end = yesterday.replace(hour=23, minute=59, second=59)
            return start, end
        elif date_str.startswith("last"):
            match = re.match(r"last(\d+)d", date_str)
            if match:
                days = int(match.group(1))
                start = now - timedelta(days=days)
                return start, now
        elif ".." in date_str:
            parts = date_str.split("..")
            start = datetime.fromisoformat(parts[0]) if parts[0] else None
            end = datetime.fromisoformat(parts[1]) if parts[1] else None
            return start, end

        # Single date
        date = datetime.fromisoformat(date_str)
        return date, date.replace(hour=23, minute=59, second=59)
```

#### 3.3 Filter Modal

```python
# widgets/filter.py (new file)

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Input, Select, Static, Button, Checkbox
from textual.containers import Vertical, Horizontal

class FilterModal(ModalScreen[FilterConfig | None]):
    """Modal for configuring filters."""

    CSS = """
    FilterModal {
        align: center middle;
    }

    #filter-container {
        width: 60%;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: solid $primary;
        padding: 1;
    }

    .filter-row {
        height: 3;
        margin-bottom: 1;
    }

    .filter-label {
        width: 15;
    }

    .filter-input {
        width: 1fr;
    }
    """

    def __init__(self, current_filter: FilterConfig | None = None):
        super().__init__()
        self.current_filter = current_filter or FilterConfig()

    def compose(self) -> ComposeResult:
        with Vertical(id="filter-container"):
            yield Static("Configure Filters", classes="title")

            # Extension filter
            with Horizontal(classes="filter-row"):
                yield Static("Extensions:", classes="filter-label")
                yield Input(
                    value=", ".join(self.current_filter.extensions),
                    placeholder=".json, .jsonl",
                    id="ext-input",
                    classes="filter-input"
                )

            # Size filter
            with Horizontal(classes="filter-row"):
                yield Static("Size range:", classes="filter-label")
                yield Input(
                    placeholder="e.g., 1KB-10MB",
                    id="size-input",
                    classes="filter-input"
                )

            # Date filter
            with Horizontal(classes="filter-row"):
                yield Static("Date range:", classes="filter-label")
                yield Input(
                    placeholder="today, last7d, 2026-01-01..2026-01-12",
                    id="date-input",
                    classes="filter-input"
                )

            # Path pattern
            with Horizontal(classes="filter-row"):
                yield Static("Path pattern:", classes="filter-label")
                yield Input(
                    value=self.current_filter.path_pattern or "",
                    placeholder="**/search/*.json",
                    id="pattern-input",
                    classes="filter-input"
                )

            # Buttons
            with Horizontal(classes="filter-row"):
                yield Button("Apply", variant="primary", id="apply-btn")
                yield Button("Clear", variant="warning", id="clear-btn")
                yield Button("Cancel", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "apply-btn":
            self.dismiss(self._build_filter())
        elif event.button.id == "clear-btn":
            self.dismiss(FilterConfig())
        else:
            self.dismiss(None)

    def _build_filter(self) -> FilterConfig:
        """Build FilterConfig from form inputs."""
        ext_input = self.query_one("#ext-input", Input).value
        size_input = self.query_one("#size-input", Input).value
        date_input = self.query_one("#date-input", Input).value
        pattern_input = self.query_one("#pattern-input", Input).value

        config = FilterConfig()

        # Parse extensions
        if ext_input.strip():
            config.extensions = [e.strip() for e in ext_input.split(",") if e.strip()]

        # Parse size range
        if size_input.strip():
            if "-" in size_input:
                parts = size_input.split("-")
                config.min_size = FilterConfig.parse_size(parts[0])
                config.max_size = FilterConfig.parse_size(parts[1])
            elif size_input.startswith(">"):
                config.min_size = FilterConfig.parse_size(size_input[1:])
            elif size_input.startswith("<"):
                config.max_size = FilterConfig.parse_size(size_input[1:])

        # Parse date range
        if date_input.strip():
            config.date_from, config.date_to = FilterConfig.parse_date_range(date_input)

        # Path pattern
        if pattern_input.strip():
            config.path_pattern = pattern_input.strip()

        return config
```

### Feature 4: Additional Features for Scraper Data

Based on the healthcare/provider data use case, these features are particularly useful:

#### 4.1 JSON Schema Analysis

Analyze common keys across records to understand data structure:

```python
# widgets/stats.py (new file)

from textual.app import ComposeResult
from textual.widgets import Static, DataTable
from textual.containers import Vertical
from collections import Counter

class SchemaAnalyzer:
    """Analyze JSON schema patterns across files."""

    def analyze_directory(self, backend, prefix: str, sample_size: int = 100) -> dict:
        """Analyze schema of files in directory."""
        key_counts = Counter()
        type_counts = Counter()
        value_samples = {}
        files_analyzed = 0

        for path, data in backend.iter_files_under(prefix, limit=sample_size):
            try:
                content = json.loads(data.decode("utf-8"))
                self._analyze_object(content, "", key_counts, type_counts, value_samples)
                files_analyzed += 1
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

        return {
            "files_analyzed": files_analyzed,
            "keys": dict(key_counts.most_common(50)),
            "types": dict(type_counts),
            "samples": value_samples,
        }

    def _analyze_object(self, obj, path, key_counts, type_counts, value_samples, depth=0):
        """Recursively analyze object structure."""
        if depth > 5:
            return

        if isinstance(obj, dict):
            for key, value in obj.items():
                full_path = f"{path}.{key}" if path else key
                key_counts[full_path] += 1
                type_counts[f"{full_path}:{type(value).__name__}"] += 1

                # Sample values for strings
                if isinstance(value, str) and len(value) < 100:
                    if full_path not in value_samples:
                        value_samples[full_path] = []
                    if len(value_samples[full_path]) < 5:
                        value_samples[full_path].append(value)

                self._analyze_object(value, full_path, key_counts, type_counts, value_samples, depth + 1)

        elif isinstance(obj, list) and obj:
            # Analyze first item as sample
            self._analyze_object(obj[0], f"{path}[]", key_counts, type_counts, value_samples, depth + 1)


class StatsPanel(Static):
    """Panel showing directory statistics and schema analysis."""

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Statistics", id="stats-title")
            yield DataTable(id="stats-table")
            yield Static("Schema Analysis", id="schema-title")
            yield DataTable(id="schema-table")
```

#### 4.2 Provider Data Quick Actions

Specific features for healthcare provider data:

```python
# widgets/provider_actions.py (new file)

class ProviderQuickActions:
    """Quick actions for provider data exploration."""

    @staticmethod
    def extract_npis(data: dict | list) -> list[str]:
        """Extract all NPI numbers from provider data."""
        npis = []
        if isinstance(data, dict):
            if "npi" in data:
                npis.append(str(data["npi"]))
            for value in data.values():
                npis.extend(ProviderQuickActions.extract_npis(value))
        elif isinstance(data, list):
            for item in data:
                npis.extend(ProviderQuickActions.extract_npis(item))
        return npis

    @staticmethod
    def extract_locations(data: dict | list) -> list[dict]:
        """Extract all location objects."""
        locations = []
        if isinstance(data, dict):
            if "locations" in data and isinstance(data["locations"], list):
                locations.extend(data["locations"])
            elif all(k in data for k in ["city", "state", "zip"]):
                locations.append(data)
            for value in data.values():
                locations.extend(ProviderQuickActions.extract_locations(value))
        elif isinstance(data, list):
            for item in data:
                locations.extend(ProviderQuickActions.extract_locations(item))
        return locations

    @staticmethod
    def summarize_provider(data: dict) -> dict:
        """Generate quick summary of provider record."""
        return {
            "npi": data.get("npi"),
            "name": f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
            "specialty": data.get("specialty"),
            "location_count": len(data.get("locations", [])),
            "networks": data.get("networks", []),
        }
```

#### 4.3 Data Validation Indicators

Show validation status in tree view:

```python
# widgets/tree.py additions

class ValidationIndicator:
    """Indicate validation status of files."""

    ICONS = {
        "valid": "[green]✓[/green]",
        "warning": "[yellow]⚠[/yellow]",
        "error": "[red]✗[/red]",
        "unknown": "[dim]?[/dim]",
    }

    @staticmethod
    def validate_provider(data: dict) -> tuple[str, list[str]]:
        """Quick validation of provider record."""
        issues = []

        # Required fields
        if not data.get("npi"):
            issues.append("Missing NPI")
        elif len(str(data.get("npi", ""))) != 10:
            issues.append("Invalid NPI length")

        if not data.get("first_name") and not data.get("last_name"):
            issues.append("Missing name")

        locations = data.get("locations", [])
        if not locations:
            issues.append("No locations")
        else:
            for i, loc in enumerate(locations):
                if not loc.get("state"):
                    issues.append(f"Location {i+1} missing state")
                if not loc.get("zip"):
                    issues.append(f"Location {i+1} missing zip")

        if not issues:
            return "valid", []
        elif len(issues) <= 2:
            return "warning", issues
        else:
            return "error", issues
```

### Feature 5: Enhanced Keyboard Shortcuts

#### 5.1 Complete Keybinding Reference

| Category | Key | Action | Notes |
|----------|-----|--------|-------|
| **Navigation** | `j` / `↓` | Move down | Vim-style |
| | `k` / `↑` | Move up | Vim-style |
| | `h` / `←` | Collapse / Go parent | Vim-style |
| | `l` / `→` / `Enter` | Expand / Open | Vim-style |
| | `g g` | Go to first item | Vim-style |
| | `G` | Go to last item | Vim-style |
| | `Ctrl+u` | Page up | |
| | `Ctrl+d` | Page down | |
| **Metadata** | `s` | Toggle size display | |
| | `d` | Toggle date display | |
| | `m` | Toggle all metadata | |
| | `S` | Cycle size format | B/KB/MB/GB |
| **Search** | `/` | Path search | Fuzzy match |
| | `Ctrl+f` | Path search (alt) | |
| | `Ctrl+g` | Content search | Search in JSON |
| | `n` | Next search result | |
| | `N` | Previous search result | |
| **Filter** | `f` | Open filter modal | |
| | `F` | Clear all filters | |
| **View** | `Tab` | Toggle stats panel | |
| | `v` | Toggle validation | Show ✓/⚠/✗ |
| | `p` | Toggle preview pane | Bottom preview |
| | `1` | Tree only (full width) | |
| | `2` | Split view (default) | |
| | `3` | Viewer only | |
| **Actions** | `e` | Export current file | To disk |
| | `E` | Export directory | Recursive |
| | `y` | Copy path to clipboard | |
| | `Y` | Copy content to clipboard | JSON |
| **General** | `r` | Refresh tree | |
| | `R` | Reload database | Full reload |
| | `?` | Help modal | |
| | `q` | Quit | |
| | `Ctrl+c` | Force quit | |

#### 5.2 Vim-Style Navigation Implementation

```python
# app.py modifications

BINDINGS = [
    # Vim navigation
    Binding("j", "cursor_down", "Down", show=False),
    Binding("k", "cursor_up", "Up", show=False),
    Binding("h", "collapse_or_parent", "Collapse/Parent", show=False),
    Binding("l", "expand_or_open", "Expand/Open", show=False),
    Binding("g", "await_g", "Go to...", show=False),
    Binding("G", "go_to_end", "Go to end", show=False),
    Binding("ctrl+u", "page_up", "Page up"),
    Binding("ctrl+d", "page_down", "Page down"),

    # Search
    Binding("/", "search_path", "Search"),
    Binding("ctrl+f", "search_path", "Search"),
    Binding("ctrl+g", "search_content", "Search content"),
    Binding("n", "next_result", "Next result", show=False),
    Binding("N", "prev_result", "Prev result", show=False),

    # Filter
    Binding("f", "open_filter", "Filter"),
    Binding("F", "clear_filter", "Clear filter"),

    # Metadata
    Binding("s", "toggle_size", "Toggle size"),
    Binding("d", "toggle_date", "Toggle date"),
    Binding("m", "toggle_metadata", "Toggle metadata"),

    # View
    Binding("tab", "toggle_stats", "Stats"),
    Binding("v", "toggle_validation", "Validation"),
    Binding("p", "toggle_preview", "Preview"),
    Binding("1", "view_tree_only", "Tree only", show=False),
    Binding("2", "view_split", "Split view", show=False),
    Binding("3", "view_content_only", "Content only", show=False),

    # Actions
    Binding("e", "export_file", "Export"),
    Binding("E", "export_directory", "Export dir"),
    Binding("y", "copy_path", "Copy path"),
    Binding("Y", "copy_content", "Copy content"),

    # General
    Binding("r", "refresh", "Refresh"),
    Binding("R", "reload_db", "Reload DB"),
    Binding("?", "help", "Help"),
    Binding("q", "quit", "Quit"),
]
```

### Implementation Phases

#### Phase 2A: Metadata Display (3-4 hours)
1. Add `get_file_metadata()` and `get_children_with_metadata()` to backend.py
2. Modify VirtualFSTree to use DisplaySettings reactive
3. Update node rendering to include size/date
4. Add toggle keybindings (s/d/m/S)
5. Update status bar to show current display settings

**Files Modified**:
- `backend.py` - Add metadata query methods
- `widgets/tree.py` - Add DisplaySettings, format_node_label()
- `app.py` - Add toggle actions and bindings

#### Phase 2B: Search Functionality (4-5 hours)
1. Create `widgets/search.py` with PathSearchModal
2. Add `iter_all_paths()` to backend
3. Implement fuzzy search algorithm
4. Add ContentSearchModal for JSON content search
5. Wire up `/` and `Ctrl+g` keybindings
6. Add n/N for result navigation

**Files Created**:
- `widgets/search.py` - PathSearchModal, ContentSearchModal

**Files Modified**:
- `backend.py` - Add iter_all_paths(), iter_all_files()
- `app.py` - Add search actions

#### Phase 2C: Filters (3-4 hours)
1. Create `models.py` with FilterConfig
2. Create `widgets/filter.py` with FilterModal
3. Integrate filters into tree loading
4. Add filter indicator in status bar
5. Wire up `f` and `F` keybindings

**Files Created**:
- `models.py` - FilterConfig, SearchResult
- `widgets/filter.py` - FilterModal

**Files Modified**:
- `widgets/tree.py` - Apply filters during loading
- `app.py` - Add filter actions

#### Phase 2D: Additional Features (4-5 hours)
1. Create `widgets/stats.py` with SchemaAnalyzer, StatsPanel
2. Add provider-specific quick actions
3. Implement validation indicators
4. Add Vim-style navigation
5. Implement export functionality
6. Add clipboard support

**Files Created**:
- `widgets/stats.py` - SchemaAnalyzer, StatsPanel
- `widgets/provider_actions.py` - ProviderQuickActions, ValidationIndicator

**Files Modified**:
- `app.py` - Add all remaining keybindings and actions

### Updated Architecture

```
tools/sqlitefs_explorer/
├── __init__.py
├── __main__.py              # Entry point (existing)
├── app.py                   # Main Textual App (enhanced)
├── backend.py               # SQLiteFS wrapper (enhanced)
├── models.py                # Data classes (NEW)
├── config.py                # Settings (future)
└── widgets/
    ├── __init__.py
    ├── tree.py              # VirtualFSTree (enhanced)
    ├── viewer.py            # JSONViewer (existing)
    ├── search.py            # PathSearchModal, ContentSearchModal (NEW)
    ├── filter.py            # FilterModal (NEW)
    ├── stats.py             # StatsPanel, SchemaAnalyzer (NEW)
    └── provider_actions.py  # Provider-specific utilities (NEW)
```

### Estimated Effort

| Phase | Features | Hours | LOC |
|-------|----------|-------|-----|
| 2A | Metadata Display | 3-4h | ~150 |
| 2B | Search | 4-5h | ~300 |
| 2C | Filters | 3-4h | ~200 |
| 2D | Additional Features | 4-5h | ~250 |
| **Total** | | **14-18h** | **~900 LOC** |

### Success Criteria (Phase 2)

- [ ] Toggle file size display with `s` key
- [ ] Toggle date display with `d` key
- [ ] Size shows human-readable format (KB/MB/GB)
- [ ] Date shows in configurable format
- [ ] Fuzzy path search with `/` key
- [ ] Content search with `Ctrl+g`
- [ ] Filter by extension, size, date, path pattern
- [ ] Filter modal with `f` key
- [ ] Clear filters with `F` key
- [ ] Stats panel with directory statistics
- [ ] Schema analysis for JSON structure
- [ ] Vim-style navigation (j/k/h/l/g/G)
- [ ] Export file with `e` key
- [ ] Copy path/content to clipboard
- [ ] Validation indicators for provider data

### References

- [Textual Tree Widget](https://textual.textualize.io/widgets/tree/)
- [Textual DirectoryTree](https://textual.textualize.io/widgets/directory_tree/)
- [ranger file manager](https://github.com/ranger/ranger)
- [nnn terminal file manager](https://github.com/jarun/nnn)
- [lf file manager](https://www.ghacks.net/2021/04/13/lf-is-a-terminal-file-manager-inspired-by-ranger-with-vim-like-shortcuts/)
- [Midnight Commander](https://terminaltrove.com/mc/)
- [tere terminal file explorer](https://github.com/mgunyho/tere)

"""Inline search results widget for SQLiteFS Explorer."""

import json
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Vertical, ScrollableContainer
from textual.message import Message
from textual.widgets import Input, ListView, ListItem, Static
from textual.widget import Widget
from textual.worker import get_current_worker
from textual import work

from tools.sqlitefs_explorer.widgets.search import fuzzy_score, SearchResult, content_matches


# Minimum characters before search starts
MIN_SEARCH_CHARS = 3


@dataclass
class ContentSearchComplete(Message):
    """Posted when content search completes."""
    results: list[SearchResult]
    searched: int


class SearchResultsWidget(Widget):
    """Inline search widget that replaces tree in side pane.

    Supports two search types:
    - fuzzy: Fuzzy pattern matching on file paths
    - content: Search within JSON file content (keys and values)

    Messages:
        ResultSelected: Emitted when user selects a result
        SearchCancelled: Emitted when user cancels search (Escape)
    """

    DEFAULT_CSS = """
    SearchResultsWidget {
        height: 100%;
        width: 100%;
        layout: vertical;
    }

    SearchResultsWidget #search-header {
        height: auto;
        padding: 0 1;
        margin-bottom: 1;
    }

    SearchResultsWidget #search-input {
        width: 100%;
    }

    SearchResultsWidget #search-status {
        height: 1;
        color: $text-muted;
    }

    SearchResultsWidget #results-scroll {
        height: 1fr;
    }

    SearchResultsWidget #results-list {
        height: auto;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    class ResultSelected(Message):
        """Emitted when a search result is selected."""

        def __init__(self, path: str, is_dir: bool):
            super().__init__()
            self.path = path
            self.is_dir = is_dir

    class SearchCancelled(Message):
        """Emitted when search is cancelled."""

        pass

    def __init__(self, backend, **kwargs):
        """Initialize search results widget.

        Args:
            backend: LazyTreeBackend instance for data access
            **kwargs: Additional widget arguments
        """
        super().__init__(**kwargs)
        self.backend = backend
        self._all_paths: list[str] = []
        self._results: list[SearchResult] = []
        self._search_type = "fuzzy"  # "fuzzy" or "content"
        self._searching = False

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        with Vertical(id="search-header"):
            yield Static("", id="search-label")
            yield Input(placeholder="Type to search (min 3 chars)...", id="search-input")
            yield Static("", id="search-status")
        with ScrollableContainer(id="results-scroll"):
            yield ListView(id="results-list")

    def on_mount(self) -> None:
        """Load paths on mount."""
        self._all_paths = list(self.backend.iter_all_paths())

    def set_search_type(self, search_type: str) -> None:
        """Set search type (called by app based on keybinding).

        Args:
            search_type: Either "fuzzy" or "content"
        """
        self._search_type = search_type
        label = self.query_one("#search-label", Static)
        if search_type == "fuzzy":
            label.update("[bold]Fuzzy Path Search[/bold] (/) - matches file paths")
        else:
            label.update("[bold]Content Search[/bold] (Ctrl+f) - searches JSON content")

    def focus_input(self) -> None:
        """Focus the search input."""
        self.query_one("#search-input", Input).focus()

    def clear_and_focus(self) -> None:
        """Clear search and focus input."""
        inp = self.query_one("#search-input", Input)
        inp.value = ""
        inp.focus()
        self._results = []
        self._update_results_list()
        self._update_status("")

    def _update_status(self, text: str) -> None:
        """Update status text."""
        status = self.query_one("#search-status", Static)
        status.update(text)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Update results on input change."""
        query = event.value.strip().lower()

        # Require minimum characters
        if len(query) < MIN_SEARCH_CHARS:
            self._results = []
            self._update_results_list()
            if query:
                self._update_status(f"Type {MIN_SEARCH_CHARS - len(query)} more character(s)...")
            else:
                self._update_status("")
            return

        if self._search_type == "fuzzy":
            self._update_status("Searching paths...")
            self._results = self._fuzzy_search(query)
            self._update_status(f"Found {len(self._results)} results")
            self._update_results_list()
        else:
            # Content search runs in background
            self._update_status("Searching content...")
            self._results = []
            self._update_results_list()
            self._content_search_async(query)

    def _fuzzy_search(self, query: str, limit: int = 100) -> list[SearchResult]:
        """Fuzzy search on paths.

        Args:
            query: Lowercase search query
            limit: Maximum results to return

        Returns:
            List of SearchResult sorted by score descending
        """
        results = []
        for path in self._all_paths:
            score = fuzzy_score(query, path.lower())
            if score > 0:
                is_dir = self.backend.is_directory(path)
                results.append(SearchResult(path=path, score=score, is_dir=is_dir))
        results.sort(key=lambda r: -r.score)
        return results[:limit]

    @work(thread=True, exclusive=True, group="content_search")
    def _content_search_async(self, query: str) -> None:
        """Search file contents in background thread.

        Args:
            query: Search query (lowercase)
        """
        worker = get_current_worker()
        results = []
        searched = 0
        limit = 100

        for path, data in self.backend.iter_all_files():
            if worker.is_cancelled:
                return

            searched += 1

            try:
                content = json.loads(data.decode("utf-8"))
                if content_matches(query, content, search_type="any"):
                    is_dir = False  # Files with content are never directories
                    results.append(SearchResult(path=path, score=1.0, is_dir=is_dir))
                    if len(results) >= limit:
                        break
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

        # Post results back to main thread via message (thread-safe)
        self.post_message(ContentSearchComplete(results=results, searched=searched))

    def on_content_search_complete(self, event: ContentSearchComplete) -> None:
        """Handle content search completion (on main thread)."""
        self._results = event.results
        self._update_status(f"Found {len(event.results)} in {event.searched} files")
        self._update_results_list()

    def _update_results_list(self) -> None:
        """Update the ListView with current results."""
        list_view = self.query_one("#results-list", ListView)
        list_view.clear()
        for result in self._results:
            icon = "[bold blue]D[/bold blue]" if result.is_dir else "[green]F[/green]"
            label = f"{icon} {result.path}"
            list_view.append(ListItem(Static(label), name=result.path))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle result selection."""
        if event.item and event.item.name:
            path = event.item.name
            is_dir = any(r.path == path and r.is_dir for r in self._results)
            self.post_message(self.ResultSelected(path, is_dir))

    def action_cancel(self) -> None:
        """Cancel search."""
        self.post_message(self.SearchCancelled())

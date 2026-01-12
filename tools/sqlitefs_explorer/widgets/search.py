"""Search functionality for SQLiteFS Explorer.

Contains fuzzy path search and content search algorithms.
"""

import json
from dataclasses import dataclass
from typing import Literal

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Input, ListView, ListItem, Static
from textual.containers import Vertical
from textual.message import Message
from textual.worker import get_current_worker
from textual import work


@dataclass
class SearchResult:
    """A search result with path and match score.

    Attributes:
        path: File path
        score: Match score (0-1, higher is better)
        is_dir: Whether path is a directory
    """

    path: str
    score: float
    is_dir: bool


@dataclass
class SearchProgress(Message):
    """Progress update during content search."""

    searched: int


@dataclass
class SearchComplete(Message):
    """Content search completed."""

    results: list[str]
    searched: int


def fuzzy_score(query: str, target: str) -> float:
    """Calculate fuzzy match score between query and target.

    Scoring:
    - Exact substring match at start: highest score (1.0)
    - Exact substring match later: good score (0.5-1.0)
    - Character-by-character match: lower score
    - Consecutive character matches get bonus

    Args:
        query: Search query (should be lowercase)
        target: Target string to match against (should be lowercase)

    Returns:
        Score from 0.0 to 1.0, where higher is better match
    """
    if not query or not target:
        return 0.0

    # Exact substring match - best case
    if query in target:
        pos = target.index(query)
        # Higher score for matches at start
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

    # Only return score if all query chars matched
    if query_idx == len(query):
        return score / len(query)

    return 0.0


def content_matches(
    query: str,
    obj: dict | list | str | int | float | bool | None,
    search_type: Literal["key", "value", "any"] = "any",
    depth: int = 0,
    max_depth: int = 10,
) -> bool:
    """Check if query matches object keys/values.

    Args:
        query: Search query (case-insensitive)
        obj: JSON object to search in
        search_type: "key" for keys only, "value" for values, "any" for both
        depth: Current recursion depth
        max_depth: Maximum recursion depth to prevent infinite loops

    Returns:
        True if query matches, False otherwise
    """
    if depth > max_depth:
        return False

    query_lower = query.lower()

    if isinstance(obj, dict):
        for key, value in obj.items():
            # Check key
            if search_type in ("key", "any"):
                if query_lower in str(key).lower():
                    return True

            # Check string values
            if search_type in ("value", "any"):
                if isinstance(value, str) and query_lower in value.lower():
                    return True
                # Check non-dict/list values as strings
                if not isinstance(value, (dict, list)) and value is not None:
                    if query_lower in str(value).lower():
                        return True

            # Recurse into nested structures
            if isinstance(value, (dict, list)):
                if content_matches(query, value, search_type, depth + 1, max_depth):
                    return True

    elif isinstance(obj, list):
        for item in obj:
            if content_matches(query, item, search_type, depth + 1, max_depth):
                return True

    elif search_type in ("value", "any"):
        # Check primitive values
        if obj is not None and query_lower in str(obj).lower():
            return True

    return False


class PathSearchModal(ModalScreen[str | None]):
    """Modal for fuzzy path search.

    Displays an input field and live-updating results list.
    Returns selected path or None if cancelled.
    """

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
        """Initialize path search modal.

        Args:
            backend: LazyTreeBackend instance
            max_results: Maximum number of results to show
        """
        super().__init__()
        self.backend = backend
        self.max_results = max_results
        self._all_paths: list[str] = []
        self._results: list[SearchResult] = []

    def compose(self) -> ComposeResult:
        """Compose the modal layout."""
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
            self._results = self._fuzzy_search(query)

        self._update_results_list()

    def _fuzzy_search(self, query: str) -> list[SearchResult]:
        """Perform fuzzy search on paths.

        Args:
            query: Lowercase search query

        Returns:
            List of SearchResult sorted by score descending
        """
        results = []

        for path in self._all_paths:
            score = fuzzy_score(query, path.lower())
            if score > 0:
                is_dir = self.backend.is_directory(path)
                results.append(SearchResult(path=path, score=score, is_dir=is_dir))

        # Sort by score descending, limit results
        results.sort(key=lambda r: -r.score)
        return results[: self.max_results]

    def _update_results_list(self) -> None:
        """Update the ListView with current results."""
        list_view = self.query_one("#search-results", ListView)
        list_view.clear()

        for result in self._results:
            icon = "[bold blue]D[/bold blue]" if result.is_dir else "[green]F[/green]"
            label = f"{icon} {result.path}"
            list_view.append(ListItem(Static(label)))

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


class ContentSearchModal(ModalScreen[list[str]]):
    """Modal for searching file contents.

    Searches JSON content for matching keys/values.
    Uses background worker for large databases.
    """

    CSS = """
    ContentSearchModal {
        align: center middle;
    }

    #search-container {
        width: 80%;
        height: 70%;
        background: $surface;
        border: solid $primary;
        padding: 1;
    }

    #search-input {
        dock: top;
        margin-bottom: 1;
    }

    #search-status {
        dock: top;
        height: 1;
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

    def __init__(
        self,
        backend,
        search_type: Literal["key", "value", "any"] = "any",
        max_results: int = 100,
    ):
        """Initialize content search modal.

        Args:
            backend: LazyTreeBackend instance
            search_type: "key" for JSON keys, "value" for values, "any" for both
            max_results: Maximum results to return
        """
        super().__init__()
        self.backend = backend
        self.search_type = search_type
        self.max_results = max_results
        self._results: list[str] = []

    def compose(self) -> ComposeResult:
        """Compose the modal layout."""
        with Vertical(id="search-container"):
            yield Static(
                f"Search file contents ({self.search_type}):", classes="title"
            )
            yield Input(placeholder="Search term...", id="search-input")
            yield Static("", id="search-status")
            yield ListView(id="search-results")

    async def on_mount(self) -> None:
        """Focus input on mount."""
        self.query_one("#search-input").focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Start search when Enter pressed in input."""
        query = event.value.strip()
        if query:
            status = self.query_one("#search-status", Static)
            status.update("Searching...")
            self.search_contents(query)

    @work(thread=True)
    def search_contents(self, query: str) -> None:
        """Search file contents in background.

        Args:
            query: Search query
        """
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
                if content_matches(query, content, self.search_type):
                    results.append(path)
                    if len(results) >= self.max_results:
                        break
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

        self.post_message(SearchComplete(results=results, searched=searched))

    def on_search_progress(self, event: SearchProgress) -> None:
        """Update progress status."""
        status = self.query_one("#search-status", Static)
        status.update(f"Searched {event.searched} files...")

    def on_search_complete(self, event: SearchComplete) -> None:
        """Handle search completion."""
        self._results = event.results
        status = self.query_one("#search-status", Static)
        status.update(
            f"Found {len(event.results)} matches in {event.searched} files"
        )
        self._update_results_list()

    def _update_results_list(self) -> None:
        """Update the ListView with current results."""
        list_view = self.query_one("#search-results", ListView)
        list_view.clear()

        for path in self._results:
            list_view.append(ListItem(Static(f"[green]F[/green] {path}")))

    def action_select(self) -> None:
        """Select current result."""
        if self._results:
            list_view = self.query_one("#search-results", ListView)
            idx = list_view.index
            if idx is not None and idx < len(self._results):
                self.dismiss([self._results[idx]])
            elif self._results:
                self.dismiss([self._results[0]])
        else:
            self.dismiss([])

    def action_cancel(self) -> None:
        """Cancel search."""
        self.dismiss([])

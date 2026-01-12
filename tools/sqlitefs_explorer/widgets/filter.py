"""Filter modal for SQLiteFS Explorer.

Allows filtering files by extension, size, date, and path pattern.
"""

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Input, Static, Button
from textual.containers import Vertical, Horizontal

from tools.sqlitefs_explorer.models import FilterConfig


class FilterModal(ModalScreen[FilterConfig | None]):
    """Modal for configuring file filters.

    Provides form inputs for:
    - Extensions (comma-separated)
    - Size range (e.g., "1KB-10MB", ">1MB", "<100KB")
    - Date range (e.g., "today", "last7d", "2026-01-01..2026-01-12")
    - Path pattern (glob like "**/search/*.json")

    Returns FilterConfig on Apply, FilterConfig() on Clear, None on Cancel.
    """

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

    .button-row {
        height: 3;
        margin-top: 1;
    }

    Button {
        margin-right: 1;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, current_filter: FilterConfig | None = None):
        """Initialize filter modal.

        Args:
            current_filter: Current filter configuration to pre-populate form
        """
        super().__init__()
        self.current_filter = current_filter or FilterConfig()

    def compose(self) -> ComposeResult:
        """Compose the modal layout."""
        with Vertical(id="filter-container"):
            yield Static("Configure Filters", classes="title")

            # Extension filter
            with Horizontal(classes="filter-row"):
                yield Static("Extensions:", classes="filter-label")
                yield Input(
                    value=", ".join(self.current_filter.extensions),
                    placeholder=".json, .jsonl",
                    id="ext-input",
                    classes="filter-input",
                )

            # Size filter
            with Horizontal(classes="filter-row"):
                yield Static("Size range:", classes="filter-label")
                yield Input(
                    value=self._format_size_range(),
                    placeholder="e.g., 1KB-10MB, >1MB, <100KB",
                    id="size-input",
                    classes="filter-input",
                )

            # Date filter
            with Horizontal(classes="filter-row"):
                yield Static("Date range:", classes="filter-label")
                yield Input(
                    value=self._format_date_range(),
                    placeholder="today, last7d, 2026-01-01..2026-01-12",
                    id="date-input",
                    classes="filter-input",
                )

            # Path pattern
            with Horizontal(classes="filter-row"):
                yield Static("Path pattern:", classes="filter-label")
                yield Input(
                    value=self.current_filter.path_pattern or "",
                    placeholder="**/search/*.json",
                    id="pattern-input",
                    classes="filter-input",
                )

            # Buttons
            with Horizontal(classes="button-row"):
                yield Button("Apply", variant="primary", id="apply-btn")
                yield Button("Clear", variant="warning", id="clear-btn")
                yield Button("Cancel", id="cancel-btn")

    def _format_size_range(self) -> str:
        """Format current size range for input field."""
        if self.current_filter.min_size is None and self.current_filter.max_size is None:
            return ""
        if self.current_filter.min_size is not None and self.current_filter.max_size is not None:
            return f"{self._format_size(self.current_filter.min_size)}-{self._format_size(self.current_filter.max_size)}"
        if self.current_filter.min_size is not None:
            return f">{self._format_size(self.current_filter.min_size)}"
        if self.current_filter.max_size is not None:
            return f"<{self._format_size(self.current_filter.max_size)}"
        return ""

    def _format_size(self, size: int) -> str:
        """Format size in bytes to human-readable string."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size}{unit}"
            size //= 1024
        return f"{size}TB"

    def _format_date_range(self) -> str:
        """Format current date range for input field."""
        if self.current_filter.date_from is None and self.current_filter.date_to is None:
            return ""
        parts = []
        if self.current_filter.date_from:
            parts.append(self.current_filter.date_from.strftime("%Y-%m-%d"))
        parts.append("..")
        if self.current_filter.date_to:
            parts.append(self.current_filter.date_to.strftime("%Y-%m-%d"))
        return "".join(parts)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "apply-btn":
            self.dismiss(self._build_filter())
        elif event.button.id == "clear-btn":
            self.dismiss(FilterConfig())
        else:
            self.dismiss(None)

    def _build_filter(self) -> FilterConfig:
        """Build FilterConfig from form inputs.

        Returns:
            FilterConfig with parsed values from form
        """
        ext_input = self.query_one("#ext-input", Input).value
        size_input = self.query_one("#size-input", Input).value
        date_input = self.query_one("#date-input", Input).value
        pattern_input = self.query_one("#pattern-input", Input).value

        config = FilterConfig()

        # Parse extensions
        if ext_input.strip():
            config.extensions = [
                e.strip() for e in ext_input.split(",") if e.strip()
            ]

        # Parse size range
        if size_input.strip():
            try:
                if "-" in size_input and not size_input.startswith(">") and not size_input.startswith("<"):
                    parts = size_input.split("-")
                    config.min_size = FilterConfig.parse_size(parts[0].strip())
                    config.max_size = FilterConfig.parse_size(parts[1].strip())
                elif size_input.startswith(">"):
                    config.min_size = FilterConfig.parse_size(size_input[1:].strip())
                elif size_input.startswith("<"):
                    config.max_size = FilterConfig.parse_size(size_input[1:].strip())
                else:
                    # Single value - treat as exact match (min=max)
                    size = FilterConfig.parse_size(size_input.strip())
                    config.min_size = size
                    config.max_size = size
            except ValueError:
                pass  # Ignore invalid size input

        # Parse date range
        if date_input.strip():
            try:
                config.date_from, config.date_to = FilterConfig.parse_date_range(
                    date_input.strip()
                )
            except (ValueError, IndexError):
                pass  # Ignore invalid date input

        # Path pattern
        if pattern_input.strip():
            config.path_pattern = pattern_input.strip()

        return config

    def action_cancel(self) -> None:
        """Cancel filter configuration."""
        self.dismiss(None)

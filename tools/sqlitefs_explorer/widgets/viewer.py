"""JSON Viewer widget with syntax highlighting."""

import json

from rich.text import Text
from textual.widgets import RichLog


# Size threshold for truncation warning (10MB)
TRUNCATION_THRESHOLD = 10 * 1024 * 1024


class JSONViewer(RichLog):
    """Widget for displaying JSON data with syntax highlighting.

    Uses RichLog for scrollable content display.
    Supports large JSON with optional truncation warning.

    Attributes:
        _data: The current JSON data being displayed
        _truncation_warning: Whether truncation warning is active
    """

    DEFAULT_CSS = """
    JSONViewer {
        background: $surface;
        padding: 1;
    }
    """

    def __init__(
        self,
        data: dict | list | None = None,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        """Initialize the JSON viewer.

        Args:
            data: Initial JSON data to display
            name: Widget name
            id: Widget ID
            classes: CSS classes
        """
        super().__init__(name=name, id=id, classes=classes, wrap=False, markup=False, auto_scroll=False)
        self._data: dict | list | None = data
        self._truncation_warning: bool = False
        self._error: str | None = None

    def _render_content(self) -> None:
        """Render the current data to the log."""
        self.clear()

        if self._error:
            self.write(Text(f"Error: {self._error}", style="red"))
            return

        if self._data is None:
            self.write(Text("Select a file to view its contents", style="dim"))
            return

        try:
            if self._truncation_warning:
                self.write(Text(
                    "Warning: Large JSON file. Display may be truncated.\n",
                    style="yellow bold",
                ))

            # Use plain JSON string to avoid markup issues with HTML in values
            json_str = json.dumps(self._data, indent=2, ensure_ascii=False)
            self.write(json_str)
        except Exception as e:
            self.write(Text(f"Error rendering JSON: {e}", style="red"))

    def set_data(
        self,
        data: dict | list | None,
        *,
        warn_truncation: bool = False,
    ) -> None:
        """Set the JSON data to display.

        Args:
            data: JSON data (dict or list)
            warn_truncation: Check if data is large and set warning flag
        """
        self._data = data
        self._error = None

        if warn_truncation and data is not None:
            try:
                serialized = json.dumps(data)
                self._truncation_warning = len(serialized) > TRUNCATION_THRESHOLD
            except (TypeError, ValueError):
                self._truncation_warning = False
        else:
            self._truncation_warning = False

        self._render_content()

    def set_error(self, error: str) -> None:
        """Set an error message to display.

        Args:
            error: Error message string
        """
        self._data = None
        self._error = error
        self._truncation_warning = False
        self._render_content()

    def on_mount(self) -> None:
        """Initialize content on mount."""
        self._render_content()

"""JSON Viewer widget with syntax highlighting."""

from typing import Any

from rich.json import JSON
from rich.text import Text
from textual.widgets import Static


# Size threshold for truncation warning (10MB)
TRUNCATION_THRESHOLD = 10 * 1024 * 1024


class JSONViewer(Static):
    """Widget for displaying JSON data with syntax highlighting.

    Uses rich.json.JSON for rendering with automatic formatting.
    Supports large JSON with optional truncation warning.

    Attributes:
        _data: The current JSON data being displayed
        _truncation_warning: Whether truncation warning is active
    """

    DEFAULT_CSS = """
    JSONViewer {
        background: $surface;
        padding: 1;
        overflow-y: auto;
        overflow-x: auto;
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
        super().__init__(name=name, id=id, classes=classes)
        self._data: dict | list | None = data
        self._truncation_warning: bool = False
        self._error: str | None = None

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
            # Estimate size by checking string representation length
            try:
                import json
                serialized = json.dumps(data)
                self._truncation_warning = len(serialized) > TRUNCATION_THRESHOLD
            except (TypeError, ValueError):
                self._truncation_warning = False
        else:
            self._truncation_warning = False

        self.refresh()

    def set_error(self, error: str) -> None:
        """Set an error message to display.

        Args:
            error: Error message string
        """
        self._data = None
        self._error = error
        self._truncation_warning = False
        self.refresh()

    def clear(self) -> None:
        """Clear the viewer."""
        self._data = None
        self._error = None
        self._truncation_warning = False
        self.refresh()

    def render(self) -> Any:
        """Render the JSON data.

        Returns:
            Rich renderable object
        """
        if self._error:
            return Text(f"Error: {self._error}", style="red")

        if self._data is None:
            return Text("Select a file to view its contents", style="dim")

        try:
            content = JSON.from_data(self._data, indent=2)
            if self._truncation_warning:
                warning = Text(
                    "Warning: Large JSON file. Display may be truncated.\n\n",
                    style="yellow bold",
                )
                return warning + content
            return content
        except Exception as e:
            return Text(f"Error rendering JSON: {e}", style="red")

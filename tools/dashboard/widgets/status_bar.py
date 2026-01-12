"""Status bar widget - displays system status at bottom of screen.

Shows proxy health, CPU/memory usage, and current context.
"""

from textual.widgets import Static


class StatusBar(Static):
    """Bottom status bar showing system information.

    Displays:
    - Proxy status and health
    - System metrics (CPU, memory)
    - Current context (selected project, etc.)
    """

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        dock: bottom;
        background: $primary-darken-2;
        color: $text;
        padding: 0 1;
    }
    """

    def __init__(
        self,
        *args,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        """Initialize the status bar."""
        super().__init__(name=name, id=id, classes=classes)
        self._context = ""
        self._proxy_status = "Unknown"

    def set_context(self, context: str) -> None:
        """Set the current context display.

        Args:
            context: Context string to display
        """
        self._context = context
        self._refresh()

    def set_proxy_status(self, status: str) -> None:
        """Set proxy status display.

        Args:
            status: Proxy status string
        """
        self._proxy_status = status
        self._refresh()

    def _refresh(self) -> None:
        """Refresh the status bar content."""
        content = f"Proxy: {self._proxy_status}"
        if self._context:
            content += f" | {self._context}"
        self.update(content)

    def render(self) -> str:
        """Render the status bar."""
        content = f"Proxy: {self._proxy_status}"
        if self._context:
            content += f" | {self._context}"
        return content

"""Settings screen - configure dashboard options.

Displays proxy configuration and other settings
with option to modify theme.
"""

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Static, Switch, Label


class SettingsScreen(Static):
    """Settings configuration screen.

    Shows:
    - Proxy configuration (read from environment)
    - Theme toggle (dark/light)
    - Other dashboard preferences
    """

    DEFAULT_CSS = """
    SettingsScreen {
        height: 100%;
        padding: 1;
    }

    .settings-section {
        margin-bottom: 2;
        padding: 1;
        border: solid $primary-darken-2;
    }

    .settings-title {
        text-style: bold;
        margin-bottom: 1;
    }

    .setting-row {
        layout: horizontal;
        height: auto;
        margin-bottom: 1;
    }

    .setting-label {
        width: 30;
    }

    .setting-value {
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the settings screen layout."""
        with VerticalScroll():
            # Proxy Configuration Section
            with Vertical(classes="settings-section"):
                yield Static("Proxy Configuration", classes="settings-title")
                yield Static(id="proxy-info")

            # Theme Section
            with Vertical(classes="settings-section"):
                yield Static("Appearance", classes="settings-title")
                yield Static("Dark Mode: (built-in)", classes="setting-row")

            # Dashboard Info Section
            with Vertical(classes="settings-section"):
                yield Static("Dashboard Info", classes="settings-title")
                yield Static(id="dashboard-info")

    def on_mount(self) -> None:
        """Load settings on mount."""
        self._load_proxy_info()
        self._load_dashboard_info()

    def _load_proxy_info(self) -> None:
        """Load and display proxy configuration."""
        import os

        proxy_types = os.environ.get("PROXY_TYPES", "none")
        smartproxy_host = os.environ.get("SMARTPROXY_HOST", "(not set)")
        dataimpulse_host = os.environ.get("DATAIMPULSE_PROXY_HOST", "(not set)")

        info_lines = [
            f"Active Types: {proxy_types}",
            f"SmartProxy Host: {smartproxy_host}",
            f"DataImpulse Host: {dataimpulse_host}",
        ]

        proxy_info = self.query_one("#proxy-info", Static)
        proxy_info.update("\n".join(info_lines))

    def _load_dashboard_info(self) -> None:
        """Load and display dashboard info."""
        from tools.dashboard import __version__
        from tools.dashboard.services.state import DEFAULT_STATE_DB

        info_lines = [
            f"Version: {__version__}",
            f"State DB: {DEFAULT_STATE_DB}",
        ]

        dashboard_info = self.query_one("#dashboard-info", Static)
        dashboard_info.update("\n".join(info_lines))

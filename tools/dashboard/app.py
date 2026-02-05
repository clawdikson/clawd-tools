"""Main Textual App for Scraping Toolkit Dashboard.

Provides a tabbed interface for:
- Projects browser
- Active runs monitor
- Data explorer
- Validation tools
- Settings
"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, TabbedContent, TabPane

from tools.dashboard.screens.data import DataScreen
from tools.dashboard.screens.projects import ProjectsScreen
from tools.dashboard.screens.runs import RunsScreen
from tools.dashboard.screens.settings import SettingsScreen
from tools.dashboard.screens.validate import ValidateScreen


class DashboardApp(App[None]):
    """Scraping Toolkit TUI Dashboard.

    A unified interface for managing scraping projects with:
    - Project browser with tree view
    - Active runs monitor
    - Data explorer (SQLiteFS)
    - Validation tools
    - Settings management

    Attributes:
        TITLE: Application title
        CSS_PATH: Path to CSS styles
        BINDINGS: Key bindings
    """

    TITLE = "Scraping Toolkit"
    CSS_PATH = "styles.tcss"

    BINDINGS = [
        Binding("f1", "switch_tab('projects')", "Projects"),
        Binding("f2", "switch_tab('runs')", "Active Runs"),
        Binding("f3", "switch_tab('data')", "Data"),
        Binding("f4", "switch_tab('validate')", "Validate"),
        Binding("f5", "switch_tab('settings')", "Settings"),
        Binding("q", "quit", "Quit"),
        Binding("?", "help", "Help"),
    ]

    CSS = """
    Screen {
        layout: vertical;
    }

    #main-tabs {
        height: 1fr;
    }

    TabPane {
        padding: 0;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the dashboard layout."""
        yield Header()

        with TabbedContent(id="main-tabs"):
            with TabPane("Projects", id="projects"):
                yield ProjectsScreen()
            with TabPane("Active Runs", id="runs"):
                yield RunsScreen()
            with TabPane("Data", id="data"):
                yield DataScreen()
            with TabPane("Validate", id="validate"):
                yield ValidateScreen()
            with TabPane("Settings", id="settings"):
                yield SettingsScreen()

        yield Footer()

    def action_switch_tab(self, tab_id: str) -> None:
        """Switch to a specific tab.

        Args:
            tab_id: ID of the tab to switch to
        """
        tabs = self.query_one("#main-tabs", TabbedContent)
        tabs.active = tab_id

    def action_help(self) -> None:
        """Show help information."""
        self.notify("Help: F1-F5 to switch tabs, q to quit")

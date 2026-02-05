"""Dashboard screens.

Each screen represents a tab in the dashboard:
- ProjectsScreen: Browse and manage projects
- RunsScreen: Monitor active scraper runs
- DataScreen: Explore SQLiteFS databases
- ValidateScreen: Run validation checks
- SettingsScreen: Configure dashboard settings
"""

from tools.dashboard.screens.data import DataScreen
from tools.dashboard.screens.projects import ProjectsScreen
from tools.dashboard.screens.runs import RunsScreen
from tools.dashboard.screens.settings import SettingsScreen
from tools.dashboard.screens.validate import ValidateScreen

__all__ = [
    "DataScreen",
    "ProjectsScreen",
    "RunsScreen",
    "SettingsScreen",
    "ValidateScreen",
]

"""Dashboard widgets.

Custom widgets for the dashboard:
- ProjectTree: Tree view of projects grouped by platform
- ProjectDetails: Project information and actions panel
- RunCard: Active run status card
- StatusBar: Bottom status bar
"""

from tools.dashboard.widgets.project_details import ProjectDetails
from tools.dashboard.widgets.project_tree import ProjectTree
from tools.dashboard.widgets.run_card import RunCard
from tools.dashboard.widgets.status_bar import StatusBar

__all__ = [
    "ProjectDetails",
    "ProjectTree",
    "RunCard",
    "StatusBar",
]

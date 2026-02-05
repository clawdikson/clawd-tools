"""Active runs screen - monitor running scrapers.

Shows all active scraper runs across terminals with progress,
phase information, and record counts.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Static

from tools.dashboard.widgets.run_card import RunCard
from tools.dashboard.services.state import SharedState


class RunsScreen(Container):
    """Active runs monitor screen.

    Shows cards for each active scraper run with:
    - Project name
    - Current phase
    - Progress bar
    - Records processed
    - Duration

    Auto-refreshes every 2 seconds using set_interval.
    """

    DEFAULT_CSS = """
    RunsScreen {
        height: 1fr;
        width: 1fr;
        padding: 1;
    }

    #runs-container {
        height: 100%;
        width: 100%;
    }

    .no-runs-message {
        text-align: center;
        color: $text-muted;
        padding: 4;
    }
    """

    def __init__(self, *args, **kwargs):
        """Initialize the runs screen."""
        super().__init__(*args, **kwargs)
        self._state = SharedState()
        self._refresh_timer = None

    def compose(self) -> ComposeResult:
        """Compose the runs screen layout."""
        with VerticalScroll(id="runs-container"):
            # Will be populated by refresh_runs
            yield Static("Loading active runs...", classes="no-runs-message")

    def on_mount(self) -> None:
        """Start refresh timer when mounted."""
        self.refresh_runs()
        self._refresh_timer = self.set_interval(2.0, self.refresh_runs)

    def on_unmount(self) -> None:
        """Stop refresh timer when unmounted."""
        if self._refresh_timer is not None:
            self._refresh_timer.stop()

    def refresh_runs(self) -> None:
        """Refresh the list of active runs."""
        container = self.query_one("#runs-container")
        container.remove_children()

        runs = self._state.get_active_runs()

        if not runs:
            container.mount(
                Static("No active runs", classes="no-runs-message")
            )
            return

        for run in runs:
            card = RunCard(
                run_id=run["id"],
                project=run["project"],
                phase=run.get("phase", ""),
                progress=run.get("progress", 0.0),
                records=run.get("records", 0),
                started_at=run.get("started_at", 0),
            )
            container.mount(card)

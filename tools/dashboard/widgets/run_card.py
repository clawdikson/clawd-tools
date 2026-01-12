"""Run card widget - displays status of a running scraper.

Shows progress, phase, records, and duration for a single active run.
"""

import time

from textual.app import ComposeResult
from textual.widgets import Static, ProgressBar


class RunCard(Static):
    """Card widget showing a running scraper's status.

    Displays:
    - Project name
    - Current phase
    - Progress bar
    - Records processed
    - Duration

    Attributes:
        run_id: ID of the run in shared state
        project: Project name
        phase: Current phase name
        progress: Progress as 0.0-1.0
        records: Records processed
        started_at: Start timestamp
    """

    DEFAULT_CSS = """
    RunCard {
        height: auto;
        margin-bottom: 1;
        padding: 1;
        border: solid $primary-darken-2;
        background: $surface;
    }

    RunCard .card-title {
        text-style: bold;
        margin-bottom: 1;
    }

    RunCard .card-phase {
        color: $text-muted;
    }

    RunCard .card-stats {
        margin-top: 1;
    }

    RunCard ProgressBar {
        margin-top: 1;
        height: 1;
    }
    """

    def __init__(
        self,
        run_id: int,
        project: str,
        phase: str = "",
        progress: float = 0.0,
        records: int = 0,
        started_at: float = 0.0,
        *args,
        **kwargs,
    ):
        """Initialize the run card.

        Args:
            run_id: Run ID from shared state
            project: Project name
            phase: Current phase name
            progress: Progress as 0.0-1.0
            records: Records processed
            started_at: Start timestamp
        """
        super().__init__(*args, **kwargs)
        self.run_id = run_id
        self.project = project
        self.phase = phase
        self.progress = progress
        self.records = records
        self.started_at = started_at

    def compose(self) -> ComposeResult:
        """Compose the card layout."""
        yield Static(self.project, classes="card-title")
        yield Static(f"Phase: {self.phase or 'Starting...'}", classes="card-phase")
        yield ProgressBar(total=100, show_eta=False)
        yield Static(self._format_stats(), classes="card-stats")

    def on_mount(self) -> None:
        """Update progress bar on mount."""
        progress_bar = self.query_one(ProgressBar)
        progress_bar.update(progress=int(self.progress * 100))

    def _format_stats(self) -> str:
        """Format the stats line."""
        duration = self._format_duration()
        return f"Records: {self.records:,} | Duration: {duration}"

    def _format_duration(self) -> str:
        """Format duration as HH:MM:SS."""
        if not self.started_at:
            return "00:00:00"

        elapsed = int(time.time() - self.started_at)
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def update_progress(
        self,
        phase: str,
        progress: float,
        records: int,
    ) -> None:
        """Update the card with new progress.

        Args:
            phase: Current phase name
            progress: Progress as 0.0-1.0
            records: Records processed
        """
        self.phase = phase
        self.progress = progress
        self.records = records

        phase_widget = self.query_one(".card-phase", Static)
        phase_widget.update(f"Phase: {phase}")

        progress_bar = self.query_one(ProgressBar)
        progress_bar.update(progress=int(progress * 100))

        stats_widget = self.query_one(".card-stats", Static)
        stats_widget.update(self._format_stats())

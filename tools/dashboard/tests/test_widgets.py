"""Tests for dashboard widgets.

Tests that widgets:
1. Extend correct base classes (Container/Vertical, not Static when composing children)
2. Properly compose child widgets
3. Handle events correctly
"""

from __future__ import annotations

import pytest
from textual.containers import Container, Vertical
from textual.widgets import Static, Tree


class TestWidgetBaseClasses:
    """Test that widgets extend the correct base class.

    CRITICAL: Widgets that compose multiple children must extend
    Container or Vertical, not Static. This was a bug in RunCard.
    """

    def test_run_card_extends_vertical(self):
        """RunCard must extend Vertical, not Static.

        RunCard composes multiple children (title, phase, progress bar, stats).
        Static doesn't propagate layout to children, causing broken rendering.
        """
        from tools.dashboard.widgets.run_card import RunCard

        assert issubclass(RunCard, Vertical), (
            "RunCard must extend Vertical, not Static. "
            "Static doesn't propagate layout to children."
        )
        assert not issubclass(RunCard, Static) or issubclass(Static, Container), (
            "RunCard should not directly extend Static when it composes children."
        )

    def test_project_tree_extends_tree(self):
        """ProjectTree should extend Tree."""
        from tools.dashboard.widgets.project_tree import ProjectTree

        assert issubclass(ProjectTree, Tree)

    def test_database_tree_extends_tree(self):
        """DatabaseTree should extend Tree."""
        from tools.dashboard.widgets.database_tree import DatabaseTree

        assert issubclass(DatabaseTree, Tree)


class TestRunCard:
    """Test RunCard widget functionality."""

    def test_run_card_composition(self):
        """Test RunCard composes expected children."""
        from tools.dashboard.widgets.run_card import RunCard
        from textual.widgets import ProgressBar

        card = RunCard(
            run_id=1,
            project="audiobee_test",
            phase="search",
            progress=0.5,
            records=100,
            started_at=0.0,
        )

        composed = list(card.compose())

        # Should have 4 children: title, phase, progress bar, stats
        assert len(composed) == 4

        # Check for progress bar
        has_progress_bar = any(isinstance(w, ProgressBar) for w in composed)
        assert has_progress_bar, "RunCard should have a ProgressBar"

    def test_run_card_stores_attributes(self):
        """Test RunCard stores all attributes correctly."""
        from tools.dashboard.widgets.run_card import RunCard

        card = RunCard(
            run_id=42,
            project="audiobee_test",
            phase="details",
            progress=0.75,
            records=250,
            started_at=1000.0,
        )

        assert card.run_id == 42
        assert card.project == "audiobee_test"
        assert card.phase == "details"
        assert card.progress == 0.75
        assert card.records == 250
        assert card.started_at == 1000.0

    def test_run_card_format_duration(self):
        """Test duration formatting."""
        import time
        from tools.dashboard.widgets.run_card import RunCard

        # Create card started 1 hour, 30 minutes, 45 seconds ago
        started = time.time() - (1 * 3600 + 30 * 60 + 45)
        card = RunCard(
            run_id=1,
            project="test",
            started_at=started,
        )

        duration = card._format_duration()
        assert duration == "01:30:45"

    def test_run_card_format_duration_zero(self):
        """Test duration formatting with no start time."""
        from tools.dashboard.widgets.run_card import RunCard

        card = RunCard(run_id=1, project="test", started_at=0.0)
        duration = card._format_duration()
        assert duration == "00:00:00"


class TestProjectTree:
    """Test ProjectTree widget functionality."""

    def test_project_tree_has_status_icons(self):
        """Test ProjectTree defines status icons."""
        from tools.dashboard.widgets.project_tree import ProjectTree

        assert hasattr(ProjectTree, "STATUS_ICONS")
        assert "healthy" in ProjectTree.STATUS_ICONS
        assert "warning" in ProjectTree.STATUS_ICONS
        assert "error" in ProjectTree.STATUS_ICONS

    def test_project_tree_has_bindings(self):
        """Test ProjectTree defines key bindings."""
        from tools.dashboard.widgets.project_tree import ProjectTree

        assert hasattr(ProjectTree, "BINDINGS")
        # Should have bindings for r, v, d, l
        binding_keys = [b[0] if isinstance(b, tuple) else b.key for b in ProjectTree.BINDINGS]
        assert "r" in binding_keys  # Run
        assert "v" in binding_keys  # Validate
        assert "d" in binding_keys  # Data
        assert "l" in binding_keys  # Logs


class TestDatabaseTree:
    """Test DatabaseTree widget functionality."""

    def test_database_tree_date_pattern(self):
        """Test DATE_PATTERN matches expected format."""
        from tools.dashboard.widgets.database_tree import DatabaseTree

        # Should match YYYYMMDD starting with 20
        assert DatabaseTree.DATE_PATTERN.match("20260110")
        assert DatabaseTree.DATE_PATTERN.match("20251231")

        # Should not match invalid dates
        assert not DatabaseTree.DATE_PATTERN.match("19990101")  # Starts with 19
        assert not DatabaseTree.DATE_PATTERN.match("2026011")  # Too short
        assert not DatabaseTree.DATE_PATTERN.match("202601101")  # Too long
        assert not DatabaseTree.DATE_PATTERN.match("not_a_date")

    def test_database_tree_has_cache(self):
        """Test DatabaseTree instance has cache for SQLiteFS validation."""
        from tools.dashboard.widgets.database_tree import DatabaseTree

        tree = DatabaseTree()
        assert hasattr(tree, "_db_cache")
        assert isinstance(tree._db_cache, dict)


class TestProjectSelectedMessage:
    """Test ProjectSelected message."""

    def test_project_selected_message_attributes(self):
        """Test ProjectSelected stores project correctly."""
        from tools.dashboard.widgets.project_tree import ProjectSelected
        from tools.dashboard.services.registry import Project
        from pathlib import Path

        project = Project(
            name="audiobee_test",
            path=Path("/tmp/audiobee_test"),
            platform="healthsparq",
            last_run="20260110",
            has_env=True,
            status="healthy",
        )

        message = ProjectSelected(project)
        assert message.project is project
        assert message.project.name == "audiobee_test"


class TestDatabaseSelectedMessage:
    """Test DatabaseSelected message."""

    def test_database_selected_message_attributes(self):
        """Test DatabaseSelected stores all attributes correctly."""
        from tools.dashboard.widgets.database_tree import DatabaseSelected
        from pathlib import Path

        db_path = Path("/tmp/audiobee_test/20260110/providers.db")

        message = DatabaseSelected(
            db_path=db_path,
            project_name="audiobee_test",
            run_date="20260110",
        )

        assert message.db_path == db_path
        assert message.project_name == "audiobee_test"
        assert message.run_date == "20260110"

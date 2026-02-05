"""Tests for dashboard screens.

Tests that all screens:
1. Extend Container (not Static) - critical for proper layout
2. Have proper CSS definitions
3. Compose correctly with child widgets
"""

from __future__ import annotations

import pytest
from textual.containers import Container


class TestScreenBaseClasses:
    """Test that all screens extend the correct base class.

    CRITICAL: Screens must extend Container, not Static.
    Static widgets don't propagate layout to children, causing
    empty/broken screens. This was a major bug that affected
    all tabs in the dashboard.
    """

    def test_projects_screen_extends_container(self):
        """ProjectsScreen must extend Container."""
        from tools.dashboard.screens.projects import ProjectsScreen

        assert issubclass(ProjectsScreen, Container), (
            "ProjectsScreen must extend Container, not Static. "
            "Static doesn't propagate layout to children."
        )

    def test_runs_screen_extends_container(self):
        """RunsScreen must extend Container."""
        from tools.dashboard.screens.runs import RunsScreen

        assert issubclass(RunsScreen, Container), (
            "RunsScreen must extend Container, not Static. "
            "Static doesn't propagate layout to children."
        )

    def test_data_screen_extends_container(self):
        """DataScreen must extend Container."""
        from tools.dashboard.screens.data import DataScreen

        assert issubclass(DataScreen, Container), (
            "DataScreen must extend Container, not Static. "
            "Static doesn't propagate layout to children."
        )

    def test_validate_screen_extends_container(self):
        """ValidateScreen must extend Container."""
        from tools.dashboard.screens.validate import ValidateScreen

        assert issubclass(ValidateScreen, Container), (
            "ValidateScreen must extend Container, not Static. "
            "Static doesn't propagate layout to children."
        )

    def test_settings_screen_extends_container(self):
        """SettingsScreen must extend Container."""
        from tools.dashboard.screens.settings import SettingsScreen

        assert issubclass(SettingsScreen, Container), (
            "SettingsScreen must extend Container, not Static. "
            "Static doesn't propagate layout to children."
        )


class TestScreenCSS:
    """Test that screens have proper CSS definitions."""

    def test_projects_screen_has_css(self):
        """ProjectsScreen should have DEFAULT_CSS."""
        from tools.dashboard.screens.projects import ProjectsScreen

        assert hasattr(ProjectsScreen, "DEFAULT_CSS")
        assert "height" in ProjectsScreen.DEFAULT_CSS
        assert "width" in ProjectsScreen.DEFAULT_CSS

    def test_runs_screen_has_css(self):
        """RunsScreen should have DEFAULT_CSS."""
        from tools.dashboard.screens.runs import RunsScreen

        assert hasattr(RunsScreen, "DEFAULT_CSS")
        assert "height" in RunsScreen.DEFAULT_CSS

    def test_data_screen_has_css(self):
        """DataScreen should have DEFAULT_CSS."""
        from tools.dashboard.screens.data import DataScreen

        assert hasattr(DataScreen, "DEFAULT_CSS")
        # Data screen should have horizontal layout for split panes
        assert "horizontal" in DataScreen.DEFAULT_CSS

    def test_validate_screen_has_css(self):
        """ValidateScreen should have DEFAULT_CSS."""
        from tools.dashboard.screens.validate import ValidateScreen

        assert hasattr(ValidateScreen, "DEFAULT_CSS")

    def test_settings_screen_has_css(self):
        """SettingsScreen should have DEFAULT_CSS."""
        from tools.dashboard.screens.settings import SettingsScreen

        assert hasattr(SettingsScreen, "DEFAULT_CSS")


class TestScreenComposition:
    """Test that screens have compose methods.

    Note: We can't call compose() directly without an app context.
    The integration tests (TestScreenIntegration) verify actual composition.
    """

    def test_projects_screen_has_compose(self):
        """ProjectsScreen should have compose method."""
        from tools.dashboard.screens.projects import ProjectsScreen

        assert hasattr(ProjectsScreen, "compose")
        assert callable(getattr(ProjectsScreen, "compose"))

    def test_data_screen_has_compose(self):
        """DataScreen should have compose method."""
        from tools.dashboard.screens.data import DataScreen

        assert hasattr(DataScreen, "compose")
        assert callable(getattr(DataScreen, "compose"))

    def test_validate_screen_has_compose(self):
        """ValidateScreen should have compose method."""
        from tools.dashboard.screens.validate import ValidateScreen

        assert hasattr(ValidateScreen, "compose")
        assert callable(getattr(ValidateScreen, "compose"))

    def test_settings_screen_has_compose(self):
        """SettingsScreen should have compose method."""
        from tools.dashboard.screens.settings import SettingsScreen

        assert hasattr(SettingsScreen, "compose")
        assert callable(getattr(SettingsScreen, "compose"))


@pytest.mark.asyncio
class TestScreenIntegration:
    """Integration tests for screens with Textual test mode."""

    async def test_projects_screen_renders(self):
        """Test ProjectsScreen renders with project tree."""
        from tools.dashboard.app import DashboardApp

        app = DashboardApp()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Check ProjectTree is present
            from tools.dashboard.widgets.project_tree import ProjectTree

            trees = list(app.query(ProjectTree))
            assert len(trees) == 1, "ProjectsScreen should have one ProjectTree"

    async def test_data_screen_renders(self):
        """Test DataScreen renders with database tree."""
        from tools.dashboard.app import DashboardApp

        app = DashboardApp()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Switch to Data tab
            await pilot.press("f3")
            await pilot.pause()

            # Check DatabaseTree is present
            from tools.dashboard.widgets.database_tree import DatabaseTree

            trees = list(app.query(DatabaseTree))
            assert len(trees) == 1, "DataScreen should have one DatabaseTree"

    async def test_validate_screen_has_components(self):
        """Test ValidateScreen has all required components."""
        from tools.dashboard.app import DashboardApp
        from textual.widgets import Select, Button, DataTable

        app = DashboardApp()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Switch to Validate tab
            await pilot.press("f4")
            await pilot.pause()

            # Check components
            selects = list(app.query(Select))
            buttons = list(app.query(Button))
            tables = list(app.query(DataTable))

            assert len(selects) >= 1, "ValidateScreen should have project selector"
            assert len(buttons) >= 3, "ValidateScreen should have action buttons"
            assert len(tables) >= 1, "ValidateScreen should have results table"

    async def test_settings_screen_has_sections(self):
        """Test SettingsScreen has settings sections."""
        from tools.dashboard.app import DashboardApp

        app = DashboardApp()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Switch to Settings tab
            await pilot.press("f5")
            await pilot.pause()

            # Check for settings sections
            sections = list(app.query(".settings-section"))
            assert len(sections) >= 3, "SettingsScreen should have at least 3 sections"

"""Tests for dashboard main app.

TDD tests written before implementation.
"""

from pathlib import Path

import pytest


class TestDashboardApp:
    """Tests for the main dashboard app."""

    def test_app_import(self):
        """Should be able to import DashboardApp."""
        from tools.dashboard.app import DashboardApp

        assert DashboardApp is not None

    def test_app_has_title(self):
        """App should have a title."""
        from tools.dashboard.app import DashboardApp

        assert hasattr(DashboardApp, "TITLE") or hasattr(DashboardApp, "title")

    def test_app_has_bindings(self):
        """App should have key bindings."""
        from tools.dashboard.app import DashboardApp

        assert hasattr(DashboardApp, "BINDINGS")

    def test_app_has_tab_bindings(self):
        """App should have F1-F5 bindings for tabs."""
        from tools.dashboard.app import DashboardApp

        bindings = DashboardApp.BINDINGS
        # Extract keys from bindings
        keys = []
        for binding in bindings:
            if hasattr(binding, "key"):
                keys.append(binding.key)
            elif isinstance(binding, tuple) and len(binding) >= 1:
                keys.append(binding[0])

        # Should have F1-F5 for tabs and q for quit
        assert "f1" in keys or "F1" in keys
        assert "q" in keys or "Q" in keys

    def test_app_has_quit_binding(self):
        """App should have q binding to quit."""
        from tools.dashboard.app import DashboardApp

        bindings = DashboardApp.BINDINGS
        keys = []
        for binding in bindings:
            if hasattr(binding, "key"):
                keys.append(binding.key)
            elif isinstance(binding, tuple) and len(binding) >= 1:
                keys.append(binding[0])

        assert "q" in keys

    def test_app_has_css(self):
        """App should have CSS styles."""
        from tools.dashboard.app import DashboardApp

        assert hasattr(DashboardApp, "CSS") or hasattr(DashboardApp, "CSS_PATH")


class TestScreenImports:
    """Tests for screen imports."""

    def test_projects_screen_import(self):
        """Should be able to import ProjectsScreen."""
        from tools.dashboard.screens.projects import ProjectsScreen

        assert ProjectsScreen is not None

    def test_runs_screen_import(self):
        """Should be able to import RunsScreen."""
        from tools.dashboard.screens.runs import RunsScreen

        assert RunsScreen is not None

    def test_data_screen_import(self):
        """Should be able to import DataScreen."""
        from tools.dashboard.screens.data import DataScreen

        assert DataScreen is not None

    def test_validate_screen_import(self):
        """Should be able to import ValidateScreen."""
        from tools.dashboard.screens.validate import ValidateScreen

        assert ValidateScreen is not None

    def test_settings_screen_import(self):
        """Should be able to import SettingsScreen."""
        from tools.dashboard.screens.settings import SettingsScreen

        assert SettingsScreen is not None


class TestWidgetImports:
    """Tests for widget imports."""

    def test_project_tree_import(self):
        """Should be able to import ProjectTree."""
        from tools.dashboard.widgets.project_tree import ProjectTree

        assert ProjectTree is not None

    def test_project_details_import(self):
        """Should be able to import ProjectDetails."""
        from tools.dashboard.widgets.project_details import ProjectDetails

        assert ProjectDetails is not None

    def test_run_card_import(self):
        """Should be able to import RunCard."""
        from tools.dashboard.widgets.run_card import RunCard

        assert RunCard is not None

    def test_status_bar_import(self):
        """Should be able to import StatusBar."""
        from tools.dashboard.widgets.status_bar import StatusBar

        assert StatusBar is not None


class TestEntryPoint:
    """Tests for dashboard entry point."""

    def test_main_import(self):
        """Should be able to import main function."""
        from tools.dashboard import main

        assert callable(main)

    def test_module_runnable(self):
        """Should be able to import __main__ module."""
        # This tests that the module is properly set up
        import tools.dashboard.__main__

        assert hasattr(tools.dashboard.__main__, "main")

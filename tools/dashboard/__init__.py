"""Scraping Toolkit TUI Dashboard.

A unified terminal interface for managing scraping projects.

Usage:
    python -m tools.dashboard

Features:
    - Project browser with tree view
    - Active runs monitor
    - Data explorer (SQLiteFS)
    - Validation tools
    - Settings management
"""

from tools.dashboard.app import DashboardApp


def main() -> None:
    """Run the dashboard application."""
    app = DashboardApp()
    app.run()


__all__ = ["DashboardApp", "main"]
__version__ = "0.1.0"

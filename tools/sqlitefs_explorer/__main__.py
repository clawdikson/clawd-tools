"""CLI entry point for SQLiteFS Explorer.

Usage:
    python -m tools.sqlitefs_explorer <db_path>
"""

from pathlib import Path

import typer

app = typer.Typer(
    name="sqlitefs-explorer",
    help="SQLiteFS Explorer - Terminal UI for exploring SQLiteFS databases",
    add_completion=False,
)


@app.command()
def main(
    db_path: Path = typer.Argument(
        ...,
        help="Path to SQLiteFS database file (.db)",
        exists=False,  # We do our own validation for better error messages
    ),
) -> None:
    """Launch SQLiteFS Explorer TUI.

    Provides a terminal-based file browser for SQLiteFS databases
    with tree navigation and JSON viewer.

    Args:
        db_path: Path to the SQLite database file
    """
    # Validate file exists
    if not db_path.exists():
        typer.echo(f"Error: Database file not found: {db_path}", err=True)
        raise typer.Exit(1)

    # Validate it's a file, not a directory
    if not db_path.is_file():
        typer.echo(f"Error: Path is not a file: {db_path}", err=True)
        raise typer.Exit(1)

    # Import here to avoid slow startup for --help
    from tools.sqlitefs_explorer.app import SQLiteFSExplorerApp

    try:
        app_instance = SQLiteFSExplorerApp(db_path=str(db_path))
        app_instance.run()
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()

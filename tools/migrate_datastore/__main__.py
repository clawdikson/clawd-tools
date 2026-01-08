#!/usr/bin/env python3
"""Entry point for running as module: python -m tools.migrate_datastore"""

from .cli import app

if __name__ == "__main__":
    app()

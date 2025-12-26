"""
HealthSparq CLI entry point.

Enables running the package as a module:
    python -m healthsparq
    python -m healthsparq --help
"""

from healthsparq.cli import app

if __name__ == "__main__":
    app()

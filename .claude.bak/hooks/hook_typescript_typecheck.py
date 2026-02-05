#!/usr/bin/env python3
"""
PostToolUse hook: Run TypeScript type check after writing .ts/.tsx files.

Runs `tsc --noEmit` in the frontend project to catch type errors early.
Provides feedback to Claude if type errors are found.
"""
import json
import subprocess
import sys
from pathlib import Path


def find_frontend_root(file_path: str) -> Path | None:
    """Find the automation-webapp-fe directory containing the file."""
    path = Path(file_path).resolve()
    while path != path.parent:
        if path.name == "automation-webapp-fe":
            return path
        path = path.parent
    return None


def main():
    try:
        data = json.load(sys.stdin)

        # Get file path from tool input
        file_path = data.get("tool_input", {}).get("file_path", "")

        # Only process TypeScript files
        if not file_path.endswith((".ts", ".tsx")):
            sys.exit(0)

        # Only process files in the frontend project
        frontend_root = find_frontend_root(file_path)
        if not frontend_root:
            sys.exit(0)

        # Check if file exists
        if not Path(file_path).exists():
            sys.exit(0)

        # Run TypeScript type check
        result = subprocess.run(
            ["npx", "tsc", "--noEmit"],
            cwd=frontend_root,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            # Extract error summary
            errors = result.stdout or result.stderr
            error_lines = errors.strip().split("\n")

            # Count errors
            error_count = sum(1 for line in error_lines if ": error TS" in line)

            # Provide feedback to Claude (stdout goes to context)
            print(f"TypeScript type check found {error_count} error(s):")
            print("")

            # Show first 20 error lines to avoid flooding
            for line in error_lines[:20]:
                print(line)

            if len(error_lines) > 20:
                print(f"... and {len(error_lines) - 20} more lines")

            print("")
            print("Please fix these type errors before continuing.")

    except subprocess.TimeoutExpired:
        print("TypeScript check timed out (>60s)")
    except FileNotFoundError:
        # npx/tsc not available - silent exit
        pass
    except Exception:
        # Never fail Claude Code operations
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Hook: Orchestrator Skill Reminder
Event: UserPromptSubmit
Adds a reminder to use the orchestrator skill for task routing.
"""

import json
import sys


def main():
    # Read hook input from stdin
    json.load(sys.stdin)

    # Output the reminder message
    result = {
        "continue": True,
        "message": "**Reminder:** Use the orchestrator skill for this if possible."
    }

    print(json.dumps(result))


if __name__ == "__main__":
    main()

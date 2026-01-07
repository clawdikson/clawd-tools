#!/usr/bin/env python3
"""
PreToolUse Hook: Subagent Context Injection

This hook intercepts Task tool calls and injects instructions for the subagent
to read context files from .claude/contexts/subagent/ directory.

The main agent writes context files before spawning subagents, and this hook
automatically appends read instructions to the subagent's prompt.
"""

import json
import sys
import os
from pathlib import Path


def get_context_dir() -> Path:
    """Get the subagent context directory."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    return Path(project_dir) / ".claude" / "contexts" / "subagent"


def get_context_files() -> list[tuple[str, str]]:
    """Get all context files with their contents."""
    context_dir = get_context_dir()
    files = []

    if not context_dir.exists():
        return files

    for file_path in context_dir.glob("*.md"):
        try:
            content = file_path.read_text(encoding="utf-8")
            files.append((file_path.name, content))
        except Exception:
            continue

    return files


def build_context_injection(context_files: list[tuple[str, str]]) -> str:
    """Build the context injection text to prepend to subagent prompt."""
    if not context_files:
        return ""

    injection = "\n\n---\n## 📋 INJECTED CONTEXT FROM MAIN AGENT\n\n"
    injection += "The main agent has provided the following context for this task:\n\n"

    for filename, content in context_files:
        injection += f"### Context: {filename}\n\n{content}\n\n"

    injection += "---\n\n"
    injection += "**IMPORTANT**: After completing your task, if you discover any important "
    injection += "findings, insights, or information the main agent should know, write them to:\n"
    injection += f"`.claude/contexts/subagent-findings/<descriptive-name>.md`\n\n"
    injection += "---\n\n"

    return injection


def main():
    """Main hook entry point."""
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)

        # Only process Task tool calls
        tool_name = input_data.get("tool_name", "")
        if tool_name != "Task":
            sys.exit(0)

        # Get context files
        context_files = get_context_files()

        if not context_files:
            # No context files, pass through unchanged
            sys.exit(0)

        # Build context injection
        context_injection = build_context_injection(context_files)

        # Get current tool input
        tool_input = input_data.get("tool_input", {})
        current_prompt = tool_input.get("prompt", "")

        # Prepend context to prompt
        enhanced_prompt = context_injection + current_prompt

        # Return updated input
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "updatedInput": {
                    **tool_input,
                    "prompt": enhanced_prompt
                }
            }
        }

        print(json.dumps(output))
        sys.exit(0)

    except json.JSONDecodeError:
        # Invalid JSON input, let it pass through
        sys.exit(0)
    except Exception as e:
        # Log error but don't block the tool
        print(json.dumps({
            "systemMessage": f"⚠️ Subagent context injection warning: {str(e)}"
        }))
        sys.exit(0)


if __name__ == "__main__":
    main()

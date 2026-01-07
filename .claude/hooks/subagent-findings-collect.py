#!/usr/bin/env python3
"""
SubagentStop Hook: Findings Collection and Cleanup

This hook runs when a subagent completes and:
1. Reads any findings files from .claude/contexts/subagent-findings/
2. Injects the findings into the main agent's context
3. Cleans up both context and findings files
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime


def get_project_dir() -> Path:
    """Get the project directory."""
    return Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))


def get_context_dir() -> Path:
    """Get the subagent context directory."""
    return get_project_dir() / ".claude" / "contexts" / "subagent"


def get_findings_dir() -> Path:
    """Get the subagent findings directory."""
    return get_project_dir() / ".claude" / "contexts" / "subagent-findings"


def read_findings() -> list[tuple[str, str]]:
    """Read all findings files."""
    findings_dir = get_findings_dir()
    findings = []

    if not findings_dir.exists():
        return findings

    for file_path in findings_dir.glob("*.md"):
        try:
            content = file_path.read_text(encoding="utf-8")
            findings.append((file_path.name, content))
        except Exception:
            continue

    return findings


def cleanup_files():
    """Clean up context and findings files."""
    context_dir = get_context_dir()
    findings_dir = get_findings_dir()

    cleaned = []

    # Clean up context files
    if context_dir.exists():
        for file_path in context_dir.glob("*.md"):
            try:
                file_path.unlink()
                cleaned.append(f"context/{file_path.name}")
            except Exception:
                pass

    # Clean up findings files
    if findings_dir.exists():
        for file_path in findings_dir.glob("*.md"):
            try:
                file_path.unlink()
                cleaned.append(f"findings/{file_path.name}")
            except Exception:
                pass

    return cleaned


def build_findings_context(findings: list[tuple[str, str]]) -> str:
    """Build the findings context to inject into main agent."""
    if not findings:
        return ""

    context = "\n\n---\n## 📥 FINDINGS FROM SUBAGENT\n\n"
    context += f"*Collected at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"

    for filename, content in findings:
        context += f"### Finding: {filename}\n\n{content}\n\n"

    context += "---\n\n"

    return context


def main():
    """Main hook entry point."""
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)

        # Read findings
        findings = read_findings()

        # Build findings context
        findings_context = build_findings_context(findings)

        # Clean up files
        cleaned_files = cleanup_files()

        # Build output
        if findings_context:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "SubagentStop",
                    "additionalContext": findings_context
                }
            }

            if cleaned_files:
                output["systemMessage"] = f"🧹 Cleaned up {len(cleaned_files)} context files"

            print(json.dumps(output))
        elif cleaned_files:
            # No findings but did cleanup
            print(json.dumps({
                "systemMessage": f"🧹 Cleaned up {len(cleaned_files)} context files (no findings)"
            }))

        sys.exit(0)

    except json.JSONDecodeError:
        sys.exit(0)
    except Exception as e:
        print(json.dumps({
            "systemMessage": f"⚠️ Findings collection warning: {str(e)}"
        }))
        sys.exit(0)


if __name__ == "__main__":
    main()

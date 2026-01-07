#!/usr/bin/env python3
"""
UserPromptSubmit Hook: Parallel Task Analyzer

Analyzes user prompts for multi-task patterns and provides guidance on whether
tasks can be parallelized via subagents.

CONSERVATIVE BY DEFAULT: When in doubt, recommends sequential execution.
"""

import json
import re
import sys
from typing import NamedTuple


class AnalysisResult(NamedTuple):
    is_multi_task: bool
    task_count: int
    can_parallelize: bool
    reason: str
    confidence: str  # "high", "medium", "low"


# Patterns indicating multiple tasks
MULTI_TASK_PATTERNS = [
    r'\b(?:1\.|first)[^\n]*\n.*(?:2\.|second)',  # Numbered lists
    r'\b(?:and then|after that|next|finally)\b',  # Sequential language
    r'(?:^|\n)\s*[-•]\s+[^\n]+(?:\n\s*[-•]\s+[^\n]+){1,}',  # Bullet lists
    r'\b(?:also|additionally|plus|as well as)\b',  # Addition language
    r'\b(?:both|all of|each of|multiple)\b',  # Multiple items
]

# Patterns that BLOCK parallelization (sequential dependencies)
SEQUENTIAL_INDICATORS = [
    r'\bthen\b',
    r'\bafter\b',
    r'\bbefore\b',
    r'\bfirst\b.*\bthen\b',
    r'\bnext\b',
    r'\bfinally\b',
    r'\bonce\s+(?:that|this|you)\b',
    r'\bwhen\s+(?:that|this|you)\b',
    r'\bif\s+(?:that|this|it)\s+(?:works|succeeds|passes)\b',
    r'\b(?:test|verify|check)\s+(?:that|it|this)\b',
    r'\bmake\s+sure\b',
    r'\bensure\b',
    r'\bdepends?\s+on\b',
    r'\brequires?\b',
    r'\bneeds?\s+to\s+be\b',
]

# Patterns indicating shared state (database, API, files)
SHARED_STATE_INDICATORS = [
    r'\b(?:database|db|mongo|sql|postgres|mysql)\b',
    r'\b(?:api|endpoint|request|response)\b',
    r'\bsame\s+(?:file|component|module|class)\b',
    r'\b(?:update|modify|change)\s+(?:the|this|that)\b',
    r'\b(?:save|commit|push|deploy)\b',
    r'\b(?:migration|seed|fixture)\b',
]

# Patterns indicating parallelizable tasks
PARALLEL_INDICATORS = [
    r'\bindependent(?:ly)?\b',
    r'\bseparate(?:ly)?\b',
    r'\bdifferent\s+(?:files?|components?|modules?)\b',
    r'\bin\s+parallel\b',
    r'\bsimultaneous(?:ly)?\b',
    r'\bconcurrent(?:ly)?\b',
]

# File-related patterns
FILE_PATTERN = r'(?:[a-zA-Z0-9_-]+\.(?:ts|tsx|js|jsx|py|rb|go|rs|java|css|scss|html|md|json|yaml|yml))'


def count_unique_files(prompt: str) -> int:
    """Count unique file references in prompt."""
    files = re.findall(FILE_PATTERN, prompt, re.IGNORECASE)
    return len(set(files))


def has_pattern(prompt: str, patterns: list) -> bool:
    """Check if any pattern matches the prompt."""
    return any(re.search(pattern, prompt, re.IGNORECASE | re.MULTILINE) for pattern in patterns)


def count_tasks_heuristic(prompt: str) -> int:
    """Estimate number of tasks in prompt."""
    # Count numbered items
    numbered = len(re.findall(r'(?:^|\n)\s*\d+\.\s+', prompt))
    if numbered >= 2:
        return numbered

    # Count bullet points
    bullets = len(re.findall(r'(?:^|\n)\s*[-•]\s+', prompt))
    if bullets >= 2:
        return bullets

    # Count "and" separated actions
    actions = len(re.findall(r'\b(?:create|add|update|fix|implement|write|delete|remove|refactor)\b', prompt, re.IGNORECASE))
    if actions >= 2:
        return actions

    return 1


def analyze_prompt(prompt: str) -> AnalysisResult:
    """Analyze prompt for parallelization potential."""
    prompt.lower()

    # Check for multi-task indicators
    is_multi_task = has_pattern(prompt, MULTI_TASK_PATTERNS) or count_tasks_heuristic(prompt) >= 2
    task_count = count_tasks_heuristic(prompt)

    if not is_multi_task or task_count < 2:
        return AnalysisResult(
            is_multi_task=False,
            task_count=1,
            can_parallelize=False,
            reason="Single task detected",
            confidence="high"
        )

    # Check for blockers (very conservative)
    has_sequential = has_pattern(prompt, SEQUENTIAL_INDICATORS)
    has_shared_state = has_pattern(prompt, SHARED_STATE_INDICATORS)
    has_parallel_hints = has_pattern(prompt, PARALLEL_INDICATORS)

    # Count unique files - if same file mentioned, can't parallelize
    unique_files = count_unique_files(prompt)
    same_file_risk = unique_files > 0 and unique_files < task_count

    # CONSERVATIVE DECISION LOGIC
    # Only recommend parallel if:
    # 1. No sequential language
    # 2. No shared state indicators
    # 3. No same-file risk
    # 4. OR explicit parallel language

    if has_sequential:
        return AnalysisResult(
            is_multi_task=True,
            task_count=task_count,
            can_parallelize=False,
            reason="Sequential dependencies detected (then/after/before language)",
            confidence="high"
        )

    if has_shared_state:
        return AnalysisResult(
            is_multi_task=True,
            task_count=task_count,
            can_parallelize=False,
            reason="Shared state detected (database/API/same resource)",
            confidence="high"
        )

    if same_file_risk:
        return AnalysisResult(
            is_multi_task=True,
            task_count=task_count,
            can_parallelize=False,
            reason="Multiple tasks may affect same files",
            confidence="medium"
        )

    if has_parallel_hints:
        return AnalysisResult(
            is_multi_task=True,
            task_count=task_count,
            can_parallelize=True,
            reason="Tasks appear independent with parallel hints",
            confidence="medium"
        )

    # Default: uncertain = sequential (CONSERVATIVE)
    return AnalysisResult(
        is_multi_task=True,
        task_count=task_count,
        can_parallelize=False,
        reason="Unable to verify task independence - defaulting to sequential",
        confidence="low"
    )


def build_guidance(result: AnalysisResult) -> str:
    """Build guidance message for Claude."""
    if not result.is_multi_task:
        return ""

    guidance = "\n\n---\n## 🔄 Parallel Execution Analysis\n\n"
    guidance += f"**Detected tasks:** ~{result.task_count}\n"
    guidance += f"**Analysis:** {result.reason}\n"
    guidance += f"**Confidence:** {result.confidence}\n\n"

    if result.can_parallelize:
        guidance += "**Recommendation:** ✅ Consider parallel subagent execution\n\n"
        guidance += "**Before parallelizing, verify:**\n"
        guidance += "- [ ] Tasks don't edit the same files\n"
        guidance += "- [ ] No data dependencies between tasks\n"
        guidance += "- [ ] Order truly doesn't matter\n"
        guidance += "- [ ] Each task can fail independently\n\n"
        guidance += "**If ANY doubt exists, run sequentially.**\n"
    else:
        guidance += "**Recommendation:** ⚠️ Run tasks sequentially\n\n"
        guidance += "Sequential execution is safer when:\n"
        guidance += "- Dependencies might exist\n"
        guidance += "- Shared resources are involved\n"
        guidance += "- Order might matter\n"

    guidance += "\n---\n"
    return guidance


def main():
    """Main hook entry point."""
    try:
        input_data = json.load(sys.stdin)
        prompt = input_data.get("prompt", "")

        if not prompt or len(prompt) < 20:
            sys.exit(0)

        result = analyze_prompt(prompt)

        if not result.is_multi_task:
            sys.exit(0)

        guidance = build_guidance(result)

        if guidance:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": guidance
                }
            }
            print(json.dumps(output))

        sys.exit(0)

    except json.JSONDecodeError:
        sys.exit(0)
    except Exception:
        # Don't block on errors
        sys.exit(0)


if __name__ == "__main__":
    main()

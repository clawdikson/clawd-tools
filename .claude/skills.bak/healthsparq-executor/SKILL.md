---
name: healthsparq-executor
description: Execute HealthSparq singleton restructuring plan phases with Ralph Wiggum-style autonomous execution and progress tracking. Use when running restructuring phases, checking progress, or generating execution prompts.
---

# HealthSparq Restructuring Executor

A CLI tool for executing the HealthSparq singleton implementation plan using Ralph Wiggum-style autonomous execution with comprehensive progress tracking.

## When to Activate

Activate this skill when:

- Running HealthSparq restructuring phases (0-8)
- Checking progress on the singleton implementation
- Generating execution prompts for subagent delegation
- Verifying phase completion
- Resetting or managing phase states

## Quick Reference

### Check Progress

```bash
python tools/healthsparq_executor.py status
```

### Run Next Phase

```bash
python tools/healthsparq_executor.py run
```

### Run Specific Phase

```bash
python tools/healthsparq_executor.py run --phase 0
```

### Run All Phases (Full Autonomous)

```bash
python tools/healthsparq_executor.py run --all
```

### Generate Phase Prompt (Dry Run)

```bash
python tools/healthsparq_executor.py run --phase 0 --dry-run
```

### Verify Phase Completion

```bash
python tools/healthsparq_executor.py verify --phase 0
```

### Reset Phase

```bash
python tools/healthsparq_executor.py reset --phase 0 --yes
```

### View Execution Log

```bash
python tools/healthsparq_executor.py log --count 20
```

### Manually Update Criterion

```bash
python tools/healthsparq_executor.py update-criterion --phase 0 --criterion 0 --passed
```

### Mark Phase Complete

```bash
python tools/healthsparq_executor.py complete-phase --phase 0
```

## Files

| File                                                           | Purpose                 |
| -------------------------------------------------------------- | ----------------------- |
| `tools/healthsparq_executor.py`                                | Main CLI tool           |
| `docs/restructuring/healthsparq/PROGRESS.json`                 | Progress tracking state |
| `docs/restructuring/healthsparq/HEALTHSPARQ_SINGLETON_PLAN.md` | Implementation plan     |

## Phase Overview

| Phase | Name                             | Subagent               |
| ----- | -------------------------------- | ---------------------- |
| 0     | Test Infrastructure Setup        | test-automator         |
| 1     | Package Foundation               | architect-reviewer     |
| 2     | Configuration System             | code-simplifier        |
| 3     | CLI Implementation               | python-pro             |
| 4     | Core Module Migration            | refactoring-specialist |
| 5     | Phase Execution Modules          | python-pro             |
| 6     | Project Configuration Generation | general-purpose        |
| 7     | End-to-End Validation            | test-automator         |
| 8     | Documentation & Cleanup          | docs-architect         |

## Ralph Wiggum Integration

The tool generates prompts designed for Ralph Wiggum autonomous execution:

```bash
# Generate prompt and copy to clipboard
python tools/healthsparq_executor.py prompt --phase 0
```

Then execute with:

```
/ralph-loop "<generated-prompt>" --max-iterations 15
```

## Progress Tracking

Progress is tracked in `docs/restructuring/healthsparq/PROGRESS.json`:

- **Phase status**: pending, in_progress, completed, failed
- **Success criteria**: Individual criterion pass/fail tracking
- **Iterations**: Current vs max iteration count
- **Timestamps**: Started and completed times
- **Execution log**: Activity history

### Updating Progress During Execution

When executing phases, **always update PROGRESS.json**:

1. **Before starting**: Set status to "in_progress"
2. **After each criterion passes**: Update `success_criteria[n].passed = true`
3. **After each attempt**: Increment `current_iteration`
4. **On completion**: Set status to "completed"

Example update code:

```python
import json
from pathlib import Path
from datetime import datetime

progress_file = Path("docs/restructuring/healthsparq/PROGRESS.json")
progress = json.loads(progress_file.read_text())

# Update criterion
progress["phases"]["0"]["success_criteria"][0]["passed"] = True

# Update iteration
progress["phases"]["0"]["current_iteration"] += 1

# Save
progress["updated_at"] = datetime.now().isoformat()
progress_file.write_text(json.dumps(progress, indent=2))
```

## Verification Commands

Each phase has verification commands that must exit 0:

```bash
# Run all verifications for a phase
python tools/healthsparq_executor.py verify --phase 0
```

The verify command:

1. Runs each verification command
2. Updates criterion pass/fail status
3. Marks phase complete if all pass
4. Adds to execution log

## Dependencies

```bash
pip install typer rich
```

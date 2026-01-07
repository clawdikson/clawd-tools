---
name: claudemd-update-enforcement
enabled: true
event: stop
pattern: .*
---

## CLAUDE.md Documentation Maintenance Rule

When you see a "MANDATORY: CLAUDE.md Documentation Update Required" message from the Stop hook, you MUST:

1. **Immediately spawn a subagent** using the Task tool with the provided prompt
2. **Do not skip** this step or defer it
3. **Do not ask** the user for permission - this is an automated maintenance task

This ensures CLAUDE.md files stay current for future agent effectiveness.

If the hook message appears, execute the Task tool invocation before responding to the user.

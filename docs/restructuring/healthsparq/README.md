# HealthSparq Singleton Refactoring

This folder contains planning documentation for consolidating 28+ healthsparq scraper projects into a unified singleton repository.

## Quick Links

| Document                                                         | Purpose                                              |
| ---------------------------------------------------------------- | ---------------------------------------------------- |
| [HEALTHSPARQ_SINGLETON_PLAN.md](./HEALTHSPARQ_SINGLETON_PLAN.md) | Main plan with **Ralph Wiggum autonomous execution** |
| [PROJECT_CONFIG_SCHEMA.md](./PROJECT_CONFIG_SCHEMA.md)           | YAML configuration schema with Pydantic models       |
| [CLI_DESIGN.md](./CLI_DESIGN.md)                                 | Typer CLI design and usage examples                  |
| [MIGRATION_CHECKLIST.md](./MIGRATION_CHECKLIST.md)               | Per-project migration tasks and verification         |

## Summary

**Problem**: 28 separate `audiobee_*` healthsparq projects with ~95% duplicated code.

**Solution**: Single `healthsparq/` package with:

- Unified core modules (`healthspark.py`, `browser_session.py`)
- Per-project YAML configuration files
- Typer CLI for project selection (`healthsparq run <project> --curr YYYYMMDD`)
- Integration with existing `shared_package/` for session management

## Key Decisions

1. **Config Format**: YAML with Pydantic validation
2. **CLI Framework**: Typer (rich help, completion support)
3. **Session Management**: Reuse `shared_package` (BrowserSession, HttpSession)
4. **Reference Implementations**:
    - `audiobee_christus_health_plan` - Latest async patterns
    - `audiobee_bluecard_national` - shared_package integration

## Usage (Target State)

```bash
# Run full pipeline
healthsparq run christus_health_plan --curr 20251214 --prev 20251114

# Run specific phase
healthsparq run excellus --curr 20251214 --phase 1

# List projects
healthsparq list --verbose

# Validate config
healthsparq validate bluecard_national
```

## Ralph Wiggum Autonomous Execution

The plan is structured for autonomous development via Ralph Wiggum plugin:

| Phase | Goal                | Subagent                      | Iterations |
| ----- | ------------------- | ----------------------------- | ---------- |
| 0     | Test Infrastructure | `test-automator`              | 10         |
| 1     | Package Foundation  | `architect-reviewer`          | 15         |
| 2     | Config System       | `code-simplifier`             | 10         |
| 3     | CLI Implementation  | `python-pro`                  | 15         |
| 4     | Core Migration      | `refactoring-specialist`      | 20         |
| 5     | Phase Execution     | `python-pro`                  | 20         |
| 6     | Project Configs     | `Explore` + `general-purpose` | 15         |
| 7     | Validation          | `test-automator`              | 10         |
| 8     | Documentation       | `docs-architect`              | 5          |

```bash
# Execute phase-by-phase
/ralph-loop "Execute PHASE_0 of healthsparq singleton.
Follow docs/restructuring/healthsparq/HEALTHSPARQ_SINGLETON_PLAN.md.
Verify all success criteria pass.
Output PHASE_0_COMPLETE when done." --max-iterations 10
```

## Related Documentation

- [../RESTRUCTURING_PLAN.md](../RESTRUCTURING_PLAN.md) - Overall infrastructure restructuring
- [../SHARED_PACKAGE_SPEC.md](../SHARED_PACKAGE_SPEC.md) - Shared utilities specification
- [../../implementation_research/](../../implementation_research/) - Framework research

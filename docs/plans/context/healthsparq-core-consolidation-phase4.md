# Phase 4: Deprecation Layer

## Background

This phase proposes adding deprecation warnings for old import paths when utilities move to core.

**Parent Plan**: `plans/feat-healthsparq-core-consolidation.md`

## Reviewer Feedback Summary (CRITICAL)

**DHH**: "You're building an import aliasing metaprogramming layer with deprecation warnings for internal utility functions that your team uses. This is solving an imaginary problem. In Rails, we don't build deprecation frameworks for internal code. We just... change it."

**Kieran**: "These are internal functions. No external users import them. The healthsparq package is project-internal (not published to PyPI). Zero external consumers means zero need for deprecation warnings."

**Simplicity Review**: "Phase 4 - CUT ENTIRELY. Just change the imports and move on."

## Recommendation

**SKIP THIS PHASE ENTIRELY**

The deprecation layer adds complexity for no benefit because:

1. `healthsparq` is **not published to PyPI**
2. There are **no external consumers**
3. The affected functions are **internal utilities**, not public API
4. The codebase is **internally controlled**

## What Was Proposed (DON'T DO THIS)

```python
# healthsparq/phases/__init__.py
def __getattr__(name: str) -> Any:
    if name in _DEPRECATED_IMPORTS:
        new_location = _DEPRECATED_IMPORTS[name]
        warnings.warn(
            f"Importing {name} from healthsparq.phases is deprecated. "
            f"Use {new_location} instead. This will be removed in v3.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        # ... magic import resolution
```

## Why This Is Unnecessary

### Question 1: Who imports from healthsparq.phases.normalize?

**Answer**: Only internal code within the healthsparq package itself.

### Question 2: Will external projects break?

**Answer**: No. The healthsparq package is used internally. Custom mappers use the public API (`from healthsparq import default_mapper`), not internal utilities.

### Question 3: What's the cost of the deprecation layer?

- ~50 lines of `__getattr__` metaprogramming
- Documentation for migration
- "2-release transition period" tracking
- Cognitive overhead for developers

### Question 4: What's the alternative?

Just change the imports in Phase 1. If any internal code breaks, fix it in the same PR.

## The Right Approach

Instead of deprecation warnings:

1. **In Phase 1**: Change imports, delete duplicates
2. **Search for broken imports**: `grep -r "from healthsparq.phases.normalize import" .`
3. **Fix any broken imports** in the same PR
4. **Done**

## Files That Would Have Been Modified (If Proceeding)

- `healthsparq/phases/__init__.py` (NOT RECOMMENDED)
- `docs/HEALTHSPARQ_CONSOLIDATION_MIGRATION.md` (NOT RECOMMENDED)

## Estimated Effort (If Proceeding)

- 2-3 hours (metaprogramming is tricky)
- Ongoing maintenance burden

## Final Recommendation

**DO NOT IMPLEMENT THIS PHASE**

Deprecation warnings are for public APIs with external consumers. This is internal code refactoring. Just make the changes and fix any breakage in the same PR.

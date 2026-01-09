# Phase 1: Normalization Utilities Consolidation

## Background

This phase addresses duplicate utility functions between `healthsparq/phases/normalize.py` and `core/mapper/` modules. The goal is to establish `core/` as the single source of truth.

**Parent Plan**: `plans/feat-healthsparq-core-consolidation.md`

## Scope

### Functions to Import from core

| Function                | healthsparq Location        | core Location            | Action           |
| ----------------------- | --------------------------- | ------------------------ | ---------------- |
| `normalize_zip_code()`  | phases/normalize.py:75-91   | mapper/normalize.py:6-16 | Import from core |
| `deduplicate_by_npi()`  | phases/normalize.py:318-334 | mapper/dedup.py:55-77    | Import from core |
| `merge_provider_data()` | phases/normalize.py:274-315 | mapper/dedup.py:7-52     | Import as alias  |
| `MapperFunc` type       | phases/normalize.py:33      | mapper/base.py:9         | Import from core |

### Functions to Keep Local

| Function               | Reason                                                      |
| ---------------------- | ----------------------------------------------------------- |
| `clean_network_name()` | Project-specific replacement logic ("medica_sg" → "medica") |

## Implementation Steps

### Task 1.1: Import normalize_zip_code

**File**: `healthsparq/phases/normalize.py`

```python
# Add import at top of file
from core.mapper.normalize import normalize_zip_code

# Delete local implementation (lines 75-91)
```

### Task 1.2: Import MapperFunc type alias

**File**: `healthsparq/phases/normalize.py`

```python
# Add import
from core.mapper.base import MapperFunc

# Delete local definition (line 33)
```

### Task 1.3: Import deduplication functions

**File**: `healthsparq/phases/normalize.py`

```python
# Add imports
from core.mapper.dedup import (
    merge_provider_records as merge_provider_data,  # Alias for backward compat
    deduplicate_by_npi,
)

# Delete local implementations (lines 274-334)
```

### Task 1.4: Verify clean_network_name stays local

The healthsparq version has hardcoded project-specific logic:

```python
def clean_network_name(name: str) -> str:
    return (
        name.replace('"', "")
        .replace("\\", "")
        .replace("medica_sg", "medica")  # Project-specific
    )
```

**Decision**: Keep local. A wrapper around core would be MORE code than the 7-line function.

## Reviewer Feedback (Dec 2025)

### Kieran's Concerns

1. **Signature mismatch**: `deduplicate_by_npi` - core uses `.get()` (defensive), healthsparq uses `[]` (strict)
2. **Signature mismatch**: `merge_provider_records` - same `.get()` vs `[]` difference

**Action Required**: Verify behavioral equivalence before importing. May need to update core to match healthsparq's strict behavior, or add tests to prove equivalence.

### DHH's Perspective

- "Just change the imports, delete the duplicates, commit. One PR. One hour."

### Simplicity Review

- Total LOC reduction: ~75 lines removed, ~4 imports added = **-71 net**

## Acceptance Criteria

- [ ] All imports resolve without errors
- [ ] `pytest tests/` passes (99+ tests)
- [ ] Output for all 23 projects is byte-identical before/after
- [ ] No runtime behavior changes

## Files Modified

- `healthsparq/phases/normalize.py` (only file)

## Estimated Effort

- 1-2 hours implementation
- 1 hour testing/verification

## Dependencies

- `core/mapper/normalize.py` must have `normalize_zip_code`
- `core/mapper/dedup.py` must have `merge_provider_records`, `deduplicate_by_npi`
- `core/mapper/base.py` must have `MapperFunc`

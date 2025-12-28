# Phase 2: Exception Hierarchy Consolidation

## Background

This phase makes `HealthSparqError` inherit from `core.exceptions.SharedPackageError` to create a unified exception hierarchy.

**Parent Plan**: `plans/feat-healthsparq-core-consolidation.md`

## Reviewer Feedback Summary

**DHH**: "Exception inheritance tree is Java disease. When something goes wrong, you want to know what went wrong, not which level of the Linnaean taxonomy of errors it falls under."

**Kieran**: "No code anywhere catches `SharedPackageError` expecting to also catch `HealthSparqError`. This is inheritance for inheritance's sake."

**Simplicity Review**: "Keep exceptions separate. They're different domains."

## Decision Point

**CRITICAL**: Before implementing, answer these questions:

1. Does ANY code catch `SharedPackageError` and expect to also catch `HealthSparqError`?
2. Would this inheritance provide concrete value beyond "cleaner architecture"?

If both answers are "no", **SKIP THIS PHASE**.

## Scope (If Proceeding)

### Current State

**healthsparq/core/exceptions.py**:

```python
class HealthSparqError(Exception):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
```

**core/exceptions.py**:

```python
class SharedPackageError(Exception):
    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message)
        self.context = context or {}
```

### Signature Incompatibility (Kieran's Finding)

- `details` vs `context` naming mismatch
- healthsparq stores `self.message` explicitly; core does not
- Subclasses pass to `details` dict, not `context`

### Proposed Solution

```python
from core.exceptions import SharedPackageError

class HealthSparqError(SharedPackageError):
    """Base exception for all HealthSparq errors.

    Inherits from core.exceptions.SharedPackageError for unified error handling.
    """
    def __init__(self, message: str, details: dict | None = None):
        # Map details to context for parent class
        super().__init__(message, context=details)
        self.message = message  # Keep for backward compat
        self.details = details or {}  # Alias to context
```

### Exceptions to Keep Domain-Specific

These remain in healthsparq (domain-specific attributes):

- `SearchError` (search-specific context)
- `ProviderDetailError` (has `provider_id`)
- `GeocodeError` (has `location`)
- `AuthenticationError`
- `ConfigurationError`
- `FileWriteError`
- `CacheError`

## Implementation Steps

### Task 2.1: Update HealthSparqError base class

1. Add import: `from core.exceptions import SharedPackageError`
2. Change: `class HealthSparqError(Exception)` → `class HealthSparqError(SharedPackageError)`
3. Update `__init__` to pass `context=details` to parent

### Task 2.2: Update APIError to use context pattern

```python
class APIError(HealthSparqError):
    def __init__(
        self,
        message: str,
        *,
        url: str | None = None,
        status_code: int | None = None,
        response_text: str | None = None,
    ) -> None:
        details = {
            "url": url,
            "status_code": status_code,
            "response_text": response_text[:500] if response_text else None,
        }
        super().__init__(message, details=details)
        self.url = url
        self.status_code = status_code
        self.response_text = response_text
```

### Task 2.3: Add tests for exception inheritance

```python
def test_healthsparq_error_inherits_from_shared():
    from core.exceptions import SharedPackageError
    from healthsparq.core.exceptions import HealthSparqError

    error = HealthSparqError("test", details={"key": "value"})
    assert isinstance(error, SharedPackageError)
    assert error.context == {"key": "value"}
    assert error.details == {"key": "value"}  # Backward compat
```

## Acceptance Criteria

- [ ] `isinstance(HealthSparqError(), SharedPackageError)` returns True
- [ ] Existing `try/except HealthSparqError` blocks continue to work
- [ ] Exception messages remain unchanged
- [ ] `details` attribute still works (backward compat)

## Files Modified

- `healthsparq/core/exceptions.py`
- `healthsparq/tests/test_exceptions.py` (new tests)

## Risk Assessment

| Risk                            | Probability | Mitigation                             |
| ------------------------------- | ----------- | -------------------------------------- |
| Breaking existing except blocks | Low         | Test all catch patterns                |
| Context/details confusion       | Medium      | Document clearly, keep both attributes |

## Estimated Effort

- 1 hour implementation
- 30 minutes testing

## Recommendation

**Consider skipping this phase** based on reviewer consensus. The inheritance provides minimal practical value if no code catches `SharedPackageError` generically.

# Phase 3: Retry Logic Consolidation

## Background

This phase proposes creating a shared retry utility in `core/retry.py` to consolidate retry logic.

**Parent Plan**: `plans/feat-healthsparq-core-consolidation.md`

## Reviewer Feedback Summary (CRITICAL)

**DHH**: "Retry logic is different for every context. The healthsparq session needs to rotate proxies. The resilient browser session needs to recreate the browser. By trying to unify these, you're creating a least-common-denominator abstraction that doesn't serve any use case well."

**Kieran**: "The plan creates infrastructure for a problem that doesn't require it. The healthsparq retry is 38 lines of simple, readable code. The proposed replacement is more abstract, harder to test, harder to debug."

**Simplicity Review**: "Phase 3 - CUT ENTIRELY. The two retry implementations are intentionally different - one is HTTP-level retry, the other is session-level retry with recreation."

## Recommendation

**SKIP THIS PHASE ENTIRELY**

The reviewers unanimously agreed that:

1. Current implementations are **contextually appropriate**
2. A generic retry module would be **over-engineering**
3. 38 lines of simple code doesn't need abstraction

## Current Implementations Analysis

### healthsparq/core/session.py (lines 132-170)

```python
async def _request_with_retry(self, method, url: str, **kwargs):
    """Execute request with exponential backoff retry."""
    for attempt in range(self.config.max_retries):
        try:
            response = await method(url, **kwargs)
            if response.status_code in [401, 403]:
                self._initialized = False  # Session-specific
            elif response.status_code < 500:
                return response
        except Exception as e:
            last_exception = e
        sleep_time = min(self.config.backoff_factor ** attempt, self.config.max_backoff)
        await asyncio.sleep(sleep_time)
```

**Purpose**: HTTP-level retry with session invalidation on auth errors

### core/session/resilient_session.py (lines 261-314)

```python
async def _execute_with_recreation(self, operation, *args, **kwargs):
    """Execute with session recreation on failure."""
    for attempt in range(self.max_recreation_attempts):
        try:
            result = await operation(*args, **kwargs)
            if status == 429:
                await asyncio.sleep(60)  # Rate limit
            elif status in [401, 403]:
                await self._recreate_session()  # Full recreation
                await self._rotate_proxy()  # Proxy rotation
            # ...
```

**Purpose**: Session-level retry with browser recreation, proxy rotation

## Why These Should NOT Be Unified

| Aspect         | healthsparq                     | core/resilient          |
| -------------- | ------------------------------- | ----------------------- |
| Retry target   | HTTP request                    | Browser session         |
| On 401/403     | Set flag `_initialized = False` | Recreate entire session |
| On 429         | Not handled (gap)               | 60s wait                |
| Proxy rotation | Not implemented                 | Full rotation           |
| Complexity     | Simple (~38 LOC)                | Complex (~50 LOC)       |

The implementations serve **different abstraction levels**:

- `healthsparq`: Thin retry for HTTP client
- `core`: Heavy retry for browser automation

## If You Must Do Something

Instead of a full abstraction, consider:

### Option A: Add 429 handling to healthsparq (minimal change)

```python
# In healthsparq/core/session.py _request_with_retry
if response.status_code == 429:
    await asyncio.sleep(60)
    continue
```

This adds the one missing feature (rate limit handling) without abstraction overhead.

### Option B: Document the intentional differences

Add a comment explaining why the implementations differ:

```python
# NOTE: This retry logic is intentionally simpler than core/session/resilient_session.py
# because we're wrapping an HTTP client, not managing browser sessions.
# See plans/context/healthsparq-core-consolidation-phase3.md for rationale.
```

## Files That Would Have Been Modified (If Proceeding)

- `core/retry.py` (new - NOT RECOMMENDED)
- `core/session/resilient_session.py`
- `healthsparq/core/session.py`

## Estimated Effort (If Proceeding)

- 4-6 hours (abstraction is hard to get right)
- High risk of introducing bugs

## Final Recommendation

**DO NOT IMPLEMENT THIS PHASE**

Keep both implementations as-is. They work, they're readable, and they serve their respective contexts correctly.

If rate limit handling is needed in healthsparq, add 3 lines to the existing function rather than creating a new abstraction.

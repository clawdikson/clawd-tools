---
session: ses_4663
updated: 2026-01-07T19:11:01.347Z
---

# Session Summary

## Goal
Make Phase 6 (recovery.py) consistent with other phases' data storage patterns by using DataStore abstraction, and plan how recovered providers can be integrated into the final JSONL output for QA/validation/report phases.

## Constraints & Preferences
- Follow Phase 1-2 storage patterns: `DataStore.put()` / `FileWriteWorker.write()`
- Support multiple backends: SQLITE, JSONL, JSON_FILES
- Add cache checking (`store.exists()`) before fetching
- Use context manager pattern (`with create_phase_store(...)`)

## Progress
### Done
- [x] Analyzed Phase 6 vs other phases' data storage patterns - found Phase 6 used raw `open()` + `orjson.dumps()` instead of DataStore abstraction
- [x] Added imports: `StorageBackend`, `create_phase_store`, `FileWriteWorker`, `TYPE_CHECKING`, `Union`
- [x] Added `storage_backend: Optional[StorageBackend] = None` to `RecoveryConfig` dataclass
- [x] Updated `recover_provider()` function signature to accept `store: Union["DataStore", FileWriteWorker]` parameter
- [x] Added cache checking with `store.exists()` before fetching providers
- [x] Updated `run_recovery()` to use `create_phase_store()` context manager for non-JSON_FILES backends, `FileWriteWorker()` for JSON_FILES
- [x] Updated `run_recovery_sync()` to accept and pass `storage_backend` parameter
- [x] Fixed tests in `test_recovery.py` to pass mock store parameter - all 29 tests pass
- [x] Analyzed CLI pipeline flow in `healthsparq/cli.py` to understand phase sequencing

### In Progress
- [ ] Planning how recovered providers can be merged into final JSONL and re-run QA/validation/report

### Blocked
- (none)

## Key Decisions
- **Use same pattern as Phase 1-2**: DataStore abstraction for consistency, cache checking, backend flexibility
- **Naming convention**: `{plan_code}_{identifier}_recovered.json` to match Phase 2 pattern

## Next Steps
1. Create plan for merging recovered providers into final JSONL (options identified below)
2. Implement chosen merge strategy
3. Add CLI flag to trigger merge + re-QA workflow

## Critical Context
### Current Pipeline Flow
```
Phase 1 (Search) → raw/search_results/
Phase 2 (Details) → raw/provider_details/
Phase 3 (Normalize) → processed/{project}-{date}.jsonl (reads from provider_details)
Phase 4 (QA) → reads from processed JSONL
Phase 5 (Report) → reads from processed JSONL
Phase 6 (Recovery) → raw/recovered/ (reads from processed JSONL curr+prev, writes recovered JSON)
```

### The Problem
Phase 6 outputs go to `raw/recovered/` but are **never merged** into the final JSONL. QA/Report only read from normalized JSONL.

### Identified Integration Options
| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| **A** | Modify Phase 3 to read from both `provider_details/` AND `recovered/` | Single normalize step | Requires re-running full Phase 3 |
| **B** | Add append/merge step after Phase 6 | Clean separation, minimal changes | Needs deduplication logic |
| **C** | Move recovery before Phase 3 | Natural flow | Chicken-egg: need JSONL to find missing |
| **D** | New Phase 6.5: merge + re-QA | Most complete | Adds complexity |

### Key File Paths
- `healthsparq/phases/recovery.py` - Phase 6 implementation (modified)
- `healthsparq/phases/normalize.py` - Phase 3 with `iter_raw_details()` and `run_normalize()`
- `healthsparq/cli.py` - CLI orchestration
- `healthsparq/tests/test_recovery.py` - Tests (modified)

## File Operations
### Read
- `healthsparq/phases/recovery.py`
- `healthsparq/phases/search.py`
- `healthsparq/phases/details.py`
- `healthsparq/phases/normalize.py`
- `healthsparq/phases/qa.py`
- `healthsparq/phases/report.py`
- `healthsparq/cli.py`
- `healthsparq/tests/test_recovery.py`

### Modified
- `healthsparq/phases/recovery.py` - Added DataStore pattern, storage_backend, cache checking
- `healthsparq/tests/test_recovery.py` - Updated 3 tests to pass mock `store` parameter

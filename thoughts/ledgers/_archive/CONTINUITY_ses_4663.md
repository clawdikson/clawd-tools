---
session: ses_4663
updated: 2026-01-07T19:25:30.940Z
---

# Session Summary

## Goal
Implement merge functionality so recovered providers from Phase 6 can be included in Phase 3 normalization, then re-run QA/Report phases on the merged output.

## Constraints & Preferences
- Follow existing Phase 1-2 storage patterns: `DataStore.put()` / `FileWriteWorker.write()`
- Support multiple backends: SQLITE, JSONL, JSON_FILES
- Use `--include-recovered` flag to opt-in to merging (not automatic)

## Progress
### Done
- [x] Added `include_recovered: bool = False` to `NormalizeConfig` dataclass
- [x] Added `recovered_dir` property to `NormalizeConfig` (returns `raw_dir.parent / "recovered"`)
- [x] Modified `iter_raw_details()` to accept optional `recovered_dir` parameter - reads from both `provider_details/` AND `recovered/` when provided
- [x] Modified `iter_raw_details_prefetch()` similarly for SQLite backend prefetching
- [x] Updated `run_normalize()` to pass `recovered_dir` when `include_recovered=True`
- [x] Updated `run_normalize_sync()` to accept and pass `include_recovered` parameter
- [x] Added `--include-recovered` CLI flag to `healthsparq/cli.py`
- [x] Updated `healthsparq/CLAUDE.md` with merge workflow documentation
- [x] Updated `healthsparq/phases/CLAUDE.md` with Phase 3/6 data flow updates

### In Progress
- [ ] Code review of changes for usability and correctness

### Blocked
- (none)

## Key Decisions
- **Opt-in merge via flag**: User must explicitly pass `--include-recovered` rather than auto-detecting recovered/ directory - prevents accidental re-inclusion of old recovered data
- **Re-run Phase 3 approach**: Instead of creating separate merge step, modified Phase 3 to read from both directories - simpler, reuses existing deduplication logic

## Next Steps
1. Review code changes for correctness and edge cases
2. Check for any issues with the recovery→normalize→QA flow
3. Consider if any additional logging or error handling needed

## Critical Context
### Workflow After Recovery
```bash
# 1. Run recovery phase
python -m healthsparq run medica_sg --curr 20251230 --prev 20251126 --phase 6

# 2. Re-run normalize with recovered providers
python -m healthsparq run medica_sg --curr 20251230 --phase 3 --include-recovered

# 3. Re-run QA and report
python -m healthsparq run medica_sg --curr 20251230 --prev 20251126 --qa --report
```

### Directory Structure
```
{date}/raw/provider_details/  ← Phase 2 output (main)
{date}/raw/recovered/         ← Phase 6 output (recovered)
{date}/processed/{slug}.jsonl ← Phase 3 output (merged when --include-recovered)
```

### Test Results
- 29/29 recovery tests pass
- 34/36 normalize tests pass (2 pre-existing failures unrelated to changes)
  - `test_normalize_under_600_loc` - Expected, file grew from ~790 to 917 lines
  - `test_network_structure_and_sorting` - Pre-existing test issue

## File Operations
### Read
- `healthsparq/phases/recovery.py`
- `healthsparq/phases/normalize.py`
- `healthsparq/cli.py`
- `healthsparq/CLAUDE.md`
- `healthsparq/phases/CLAUDE.md`

### Modified
- `healthsparq/phases/normalize.py` - Added `include_recovered`, `recovered_dir`, updated iterators
- `healthsparq/cli.py` - Added `--include-recovered` flag, updated Phase 3 call
- `healthsparq/CLAUDE.md` - Added merge workflow documentation
- `healthsparq/phases/CLAUDE.md` - Updated Phase 3/6 sections and data flow

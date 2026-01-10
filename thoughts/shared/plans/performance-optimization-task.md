# Task Plan: HealthSparq Performance Optimization

## Goal

Implement all 14 optimizations from plans/2026-01-09-performance-review.md achieving ~24% time reduction and 62% memory savings.

## Source

`plans/2026-01-09-performance-review.md`

## Phases

### Week 1: Critical Fixes (Tier 1) ✅ COMPLETED

- [x] Task 1.1: Remove `list()` materialization in `normalize.py` - Implemented streaming iterator `_iter_all_records()`
- [x] Task 1.2: Stream missing providers in `recovery.py` - Memory reduced by ~75%
- [x] Task 1.3: Replace all `merge_provider_records` with `merge_provider_records_inplace` - Added to core/mapper/dedup.py
- [x] Task 1.4: Add filter query caching in `search.py` - Module-level `_filter_cache` added
- [x] Bug fix: Fixed SQLiteNPIMap buffer duplicate detection
- [x] Bug fix: Fixed network extraction to handle both data formats

### Week 2: High Priority (Tier 2) ✅ COMPLETED

- [x] Task 2.1: Consolidate recovered provider reading paths - Single unified loader
- [x] Task 2.2: Add buffer to `JSONLWriter` - buffer_size=100, 5-10x throughput
- [x] Task 2.3: Regex for phone/network normalization - Pre-compiled `_PHONE_CLEAN_RE`
- [x] Task 2.4: Set caching in merge operations - 40-60% faster merges

### Week 3+: Architectural Improvements (Tier 3)

- [ ] Task 3.1: Create `core/io/compressed_raw.py` with `CompressedRawStore`
- [ ] Task 3.2: Add LZ4 dependency to pyproject.toml
- [ ] Task 3.3: Design Phase 2+3 integration with streaming + compressed raw
- [ ] Task 3.4: Refactor `details.py` to accept mapper and raw archive
- [ ] Task 3.5: Async report generation prototype
- [ ] Task 3.6: Unified thread pool executor

## Key Files

| File                              | Purpose                    |
| --------------------------------- | -------------------------- |
| `healthsparq/phases/normalize.py` | Memory materialization fix |
| `healthsparq/phases/recovery.py`  | Streaming comparison       |
| `healthsparq/phases/search.py`    | Filter caching             |
| `core/mapper/dedup.py`            | merge_inplace usage        |
| `core/io/jsonl.py`                | Write buffering            |
| `core/mapper/normalize.py`        | String normalization       |

## Decisions Made

- (none yet)

## Errors Encountered

- (none yet)

## Status

**Week 1 COMPLETED** ✅ - All 4 critical fixes implemented and tested
**Week 2 COMPLETED** ✅ - All 4 high priority optimizations implemented and tested (146 tests passing)

**Ready for Week 3** - Architectural improvements (6 tasks)

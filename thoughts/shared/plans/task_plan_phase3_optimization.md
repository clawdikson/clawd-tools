# Task Plan: Phase 3 Normalization Optimization

## Goal

Optimize Phase 3 normalization for memory efficiency and processing speed by eliminating deepcopy, optimizing helpers, and implementing SQLite-backed NPI map.

## Phases

- [x] Phase 1.1: Eliminate deepcopy in core/mapper/dedup.py - add merge_provider_records_inplace()
- [x] Phase 1.2: Optimize helper functions in healthsparq/phases/normalize.py (get_network_names, get_specialties, etc.)
- [x] Phase 2.1: Create SQLiteNPIMap class in core/mapper/sqlite_npi_map.py
- [x] Phase 2.2: Add unit tests for SQLiteNPIMap (41 tests, all passing)
- [x] Phase 2.3: Integrate SQLiteNPIMap with normalize.py (opt-in via flag)
- [x] Phase 3: Validate - benchmark SQLite vs dict mode, make SQLite default

## Key Files

- `plans/2026-01-09-phase3-normalization-optimization.md` - Full implementation plan
- `core/mapper/dedup.py` - In-place merge implementation (no deepcopy)
- `healthsparq/phases/normalize.py` - Normalize phase with SQLite stage (default)
- `core/mapper/sqlite_npi_map.py` - SQLite-backed NPI map
- `scripts/benchmark_normalize.py` - Benchmark tool for comparing modes

## Decisions Made

- Use in-place mutation for merges (safe since we replace dict value)
- Store denormalized fields (provider_id, location_ids, states, provider_type, network_names) for downstream queries
- **SQLite mode is now DEFAULT** - 14% faster, 42% less memory, identical output

## Benchmark Results (Wellmark 41,565 records)

| Metric | Dict Mode | SQLite Mode | Improvement      |
| ------ | --------- | ----------- | ---------------- |
| Time   | 419.36s   | 359.12s     | **14.4% faster** |
| Memory | 490.3 MB  | 285.3 MB    | **41.8% less**   |
| Output | 41,553    | 41,553      | **Identical**    |

## Status

**ALL PHASES COMPLETE** - SQLite mode is now the default

### Completed Work:

1. `core/mapper/dedup.py` - Added `merge_provider_records_inplace()` (no deepcopy)
2. `healthsparq/phases/normalize.py` - Optimized 4 helper functions with generator comprehensions
3. `core/mapper/sqlite_npi_map.py` - 315-line SQLite-backed NPI map with query helpers
4. `core/tests/test_sqlite_npi_map.py` - 41 passing tests
5. `healthsparq/phases/normalize.py` - SQLite stage now default (`use_sqlite_stage=True`)
6. `scripts/benchmark_normalize.py` - Benchmark tool for comparing normalization modes
7. `core/logging/logger.py` - Fixed tqdm_logging cleanup error

### Usage:

```bash
# Default (SQLite mode - faster, less memory)
.venv/bin/python -m healthsparq run project --curr 20260109 --phase 3

# Legacy dict mode (if needed)
# Set use_sqlite_stage=False in NormalizeConfig
```

### Benchmark Tool:

```bash
# Compare dict vs SQLite normalization
.venv/bin/python scripts/benchmark_normalize.py --raw-dir path/to/provider_details.db --storage-backend sqlite
```

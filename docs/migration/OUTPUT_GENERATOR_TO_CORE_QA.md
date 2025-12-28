# Migration Guide: output_generator to core/qa

This guide helps migrate from the legacy `output_generator` module to the new `core/qa` module.

## Overview

The `output_generator` utilities have been migrated to `core/qa` with significant improvements:

| Feature              | output_generator       | core/qa                                |
| -------------------- | ---------------------- | -------------------------------------- |
| Schema Validation    | jsonschema (slow)      | fastjsonschema (100x faster)           |
| DataFrame Operations | pandas                 | Polars (10x faster)                    |
| File Processing      | Load entire file       | Streaming with single-pass             |
| Deduplication        | Set (unbounded memory) | BoundedSet (LRU eviction at 100k)      |
| Error Handling       | Exceptions             | QAResult pattern (structured outcomes) |
| Timeout Protection   | None                   | Configurable (default: 5 min)          |
| Logging              | print statements       | Structured loguru logging              |
| CLI                  | Individual scripts     | Unified Typer CLI                      |

## Quick Reference

| Old (output_generator)                    | New (core/qa)                     |
| ----------------------------------------- | --------------------------------- |
| `type_check.type_checker()`               | `validate(jsonl_path)`            |
| `sample_generator.sample_generator()`     | `sample(jsonl_path, count=10)`    |
| `comparison_creator.comparison_creator()` | `compare(curr_path, prev_path)`   |
| `report_generator.report_generator()`     | `report(project_name, curr_date)` |

---

## Migration Examples

### 1. Schema Validation (type_check)

#### Before (output_generator)

```python
from output_generator import type_checker

# Run validation
type_checker(
    project_name="audiobee_bcbs_il",
    curr_date="20251227",
    curr_processed_dir="20251227/processed",
    anthem_state=None,  # Optional for Anthem projects
    should_validate=True
)
# Returns: None (raises ValueError on validation errors)
# Side effects: Generates Excel reports in processed_dir
```

#### After (core/qa)

```python
from core.qa import validate, ValidationMetrics

# Run validation
result = validate("20251227/processed/audiobee_bcbs_il-20251227.jsonl")

# Check result (structured outcome)
if result.is_success:
    print(f"Valid: {result.metrics.valid_records}/{result.metrics.total_records}")
    print(f"Unique NPIs: {result.metrics.unique_npis}")
    print(f"Unique states: {result.metrics.unique_states}")
else:
    print(f"Failed: {result.message}")
    for error in result.errors[:10]:
        print(f"  - {error}")

# Access detailed metrics
metrics: ValidationMetrics = result.metrics
print(f"Networks: {metrics.unique_networks}")
print(f"Specialties: {metrics.unique_specialties}")
print(f"Elapsed: {result.outcome.elapsed_seconds:.2f}s")

# Check for warnings (e.g., duplicates, capacity limits)
for warning in result.warnings:
    print(f"Warning: {warning}")
```

#### Using the Validator Class Directly

```python
from core.qa import Validator, QASettings

settings = QASettings(
    project_name="audiobee_bcbs_il",
    curr_date="20251227",
    validate_schema=True,
    base_dir=Path("."),
)

validator = Validator(settings)
result = validator.run(deduplicate=True, timeout_seconds=600)
```

---

### 2. Sample Generation

#### Before (output_generator)

```python
from output_generator import sample_generator, compress_folder_to_7z

# Generate 10 random samples
sample_generator(
    project_name="audiobee_bcbs_il",
    curr_date="20251227",
    curr_processed_dir="20251227/processed",
    anthem_state=None
)
# Creates: project-sample-date-0.json through project-sample-date-9.json

# Compress folder separately
compress_folder_to_7z(
    folder_path="20251227/processed",
    output_path="20251227/processed/20251227.7z"
)
```

#### After (core/qa)

```python
from core.qa import sample, SamplingMetrics

# Generate samples with archive (single call)
result = sample(
    jsonl_path="20251227/processed/audiobee_bcbs_il-20251227.jsonl",
    output_dir="20251227/processed",  # Optional, defaults to parent of jsonl
    count=10,                          # Sample count (default: 10)
    archive_format="7z",               # Options: 7z, zip, tar.gz
    timeout_seconds=300                # Timeout protection
)

if result.is_success:
    print(f"Generated {result.metrics.sample_count} samples")
    print(f"From {result.metrics.total_records} total records")
    print(f"Archive: {result.output_files[-1]}")  # Archive is last file
    print(f"Archive size: {result.metrics.archive_size_bytes:,} bytes")
```

**Key Improvements:**

- Uses reservoir sampling (O(n) time, O(k) space) - no full file load
- Automatic archive creation in single call
- Timeout protection for large files

---

### 3. Comparison Analysis

#### Before (output_generator)

```python
from output_generator import comparison_creator

comparison_creator(
    project_name="audiobee_bcbs_il",
    curr_date="20251227",
    curr_processed_dir="20251227/processed",
    prev_date="20251126",
    prev_processed_dir="20251126/processed",
    anthem_state=None
)
# Returns: None
# Side effects: Generates comparison Excel reports
```

#### After (core/qa)

```python
from core.qa import compare, ComparisonMetrics

result = compare(
    curr_path="20251227/processed/debug_specialty_network.xlsx",
    prev_path="20251126/processed/debug_specialty_network.xlsx",
)

if result.is_success:
    metrics: ComparisonMetrics = result.metrics
    print(f"Current: {metrics.curr_total} records")
    print(f"Previous: {metrics.prev_total} records")
    print(f"Added: {metrics.added}")
    print(f"Removed: {metrics.removed}")

    # Per-network breakdown
    for network, changes in metrics.network_changes.items():
        print(f"  {network}: +{changes['added']} / -{changes['removed']}")

elif result.status == "skipped":
    # First run - no previous data
    print("First run: no previous data for comparison")
```

**Key Improvements:**

- Uses Polars (10x faster than pandas)
- Single-pass file reading
- Graceful first-run handling (no prev_date)
- Warning for significant drops (>10%)

---

### 4. Report Generation

#### Before (output_generator)

```python
from output_generator import report_generator

report_generator(
    project_name="audiobee_bcbs_il",
    curr_date="20251227",
    prev_date="20251126",
    req_states=["IL", "IN", "WI"],
    req_states_only=None,
    hsparq=False
)
# Returns: None
# Side effects: Generates Excel report
```

#### After (core/qa)

```python
from core.qa import report, ReportMetrics

result = report(
    project_name="audiobee_bcbs_il",
    curr_date="20251227",
    prev_date="20251126",
    states=["IL", "IN", "WI"],
)

if result.is_success:
    metrics: ReportMetrics = result.metrics
    print(f"States: {metrics.states_count}")
    print(f"In-scope states: {metrics.in_scope_states}")
    print(f"Total providers: {metrics.total_providers}")
    print(f"Change from previous: {metrics.total_change:+d}")
    print(f"Report: {result.output_files[0]}")
```

**Key Improvements:**

- Single-pass JSONL processing
- xlsxwriter streaming mode (memory-efficient)
- Cached reference data loading (ZIP to state mapping)

---

## CLI Usage

### Old (output_generator)

```bash
# Run individual scripts
cd project_dir
python output_generator/type_check.py
python output_generator/sample_generator.py
python output_generator/comparison_creator.py
python output_generator/report_generator.py

# Or use the orchestrator
python output_generator/run_all.py
```

### New (core/qa)

```bash
# Unified CLI with all commands
python -m core.qa validate providers.jsonl
python -m core.qa sample providers.jsonl --count 20 --format 7z
python -m core.qa compare --curr 20251227 --prev 20251126 --project .
python -m core.qa report audiobee_bcbs_il --curr 20251227 --prev 20251126 --states IL,TX

# With timeout protection
python -m core.qa validate providers.jsonl --timeout 600

# Show version and help
python -m core.qa version
python -m core.qa --help
```

---

## Backward Compatibility

The `output_generator` module now provides wrapper functions with deprecation warnings. Existing code continues to work during the transition period.

### Wrapper Behavior

```python
# This still works but shows DeprecationWarning
from output_generator import type_checker

type_checker(
    project_name="audiobee_bcbs_il",
    curr_date="20251227",
    curr_processed_dir="20251227/processed"
)
# DeprecationWarning: 'type_checker' is deprecated and will be removed in v4.0.
# Use 'from core.qa import validate' instead.
```

### Wrapper Functions Available

| Function                  | Deprecation Warning    | Notes                                               |
| ------------------------- | ---------------------- | --------------------------------------------------- |
| `type_checker()`          | Use `core.qa.validate` | Calls legacy implementation for full compatibility  |
| `sample_generator()`      | Use `core.qa.sample`   | Calls legacy implementation                         |
| `comparison_creator()`    | Use `core.qa.compare`  | Calls legacy implementation                         |
| `report_generator()`      | Use `core.qa.report`   | Calls legacy implementation                         |
| `compress_folder_to_7z()` | Use `core.qa.sampler`  | Calls legacy implementation                         |
| `scheduler()`             | Not migrated           | Use `output_generator.scheduler.scheduler` directly |

---

## Key Differences

### 1. Return Values

**Old:** Functions return `None` or `bool`, rely on side effects and exceptions.

**New:** All functions return `QAResult[T]` with structured outcome and typed metrics.

```python
from core.qa import QAResult, QAStatus, ValidationMetrics

result: QAResult[ValidationMetrics] = validate(path)

# Access outcome
result.is_success        # bool - True if SUCCESS or WARNING
result.status            # QAStatus enum
result.message           # Summary message
result.warnings          # List of warnings
result.errors            # List of errors
result.outcome.elapsed_seconds  # Execution time

# Access metrics (type-specific)
result.metrics.valid_records
result.metrics.unique_npis
result.metrics.networks      # dict[str, int]
result.metrics.specialties   # dict[str, int]

# Access output files
result.output_files      # List[Path]
```

### 2. Status Codes

```python
from core.qa import QAStatus

QAStatus.SUCCESS   # Operation completed successfully
QAStatus.WARNING   # Completed with warnings (e.g., duplicates found)
QAStatus.ERROR     # Operation failed
QAStatus.TIMEOUT   # Operation exceeded timeout (P0 fix)
QAStatus.SKIPPED   # Operation skipped (e.g., no prev_date for comparison)
```

### 3. Error Handling

**Old:**

```python
try:
    type_checker(...)
except ValueError as e:
    print(f"Validation failed: {e}")
```

**New:**

```python
result = validate(path)
if not result.is_success:
    if result.status == QAStatus.TIMEOUT:
        print(f"Timed out after {result.outcome.elapsed_seconds:.1f}s")
    else:
        print(f"Failed: {result.message}")
        for error in result.errors:
            print(f"  - {error}")
```

### 4. Timeout Protection

The new module includes timeout protection (default: 5 minutes) to prevent hanging on large files:

```python
from core.qa import validate, QATimeoutError

# Using convenience function
result = validate(path, timeout_seconds=600)  # 10 minute timeout

if result.status == QAStatus.TIMEOUT:
    print("Operation timed out - file may be too large")

# Using class directly with try/except
from core.qa import Validator, QASettings, run_with_timeout

validator = Validator(settings)
try:
    result = validator.run(timeout_seconds=600)
except QATimeoutError as e:
    print(f"Timed out after {e.elapsed_seconds:.1f}s")
```

### 5. Memory-Bounded Deduplication

The new module uses `BoundedSet` (LRU eviction at 100k items) to prevent memory exhaustion on large datasets:

```python
# Automatic warning when approaching capacity
result = validate(large_file)
if result.metrics.dedup_capacity_reached:
    print("Warning: Deduplication capacity reached, some duplicates may not be detected")
```

---

## Migration Checklist

1. **Update imports:**

    ```python
    # Old
    from output_generator import type_checker, sample_generator

    # New
    from core.qa import validate, sample
    ```

2. **Update function calls:** Replace positional arguments with named parameters and handle `QAResult` return values.

3. **Update error handling:** Replace try/except with `QAResult.is_success` checks.

4. **Update CLI commands:** Use `python -m core.qa` instead of individual scripts.

5. **Test thoroughly:** Run parallel validation during transition to verify identical results.

---

## Timeline

| Version | Status  | Notes                                                            |
| ------- | ------- | ---------------------------------------------------------------- |
| v3.0    | Current | Both modules available, deprecation warnings on output_generator |
| v4.0    | Planned | output_generator removed, use core/qa only                       |

---

## Additional Resources

- **Module documentation:** `core/qa/__init__.py`
- **Base types:** `core/qa/base.py` (QAResult, QAOutcome, QAStatus)
- **Configuration:** `core/qa/config.py` (QASettings)
- **Tests:** `core/qa/tests/` (pytest examples)
- **Legacy module:** `output_generator/__init__.py` (wrapper implementations)

---

## Frequently Asked Questions

### Q: Does core/qa generate the same Excel reports as output_generator?

The core/qa module generates simplified Excel reports focused on state counts and network changes. The original output_generator produces more detailed reports with additional sheets (Networks, Provider Names, NPI, Zip Code Network, etc.). During the transition period, the wrapper functions call the legacy implementations to maintain full compatibility.

### Q: What about the scheduler functionality?

The `scheduler` function is NOT migrated to core/qa. Continue using `output_generator.scheduler.scheduler` directly. This function manages scheduled execution of scraping jobs and is outside the scope of QA utilities.

### Q: Can I use both modules together?

Yes. During v3.0, both modules coexist. You can gradually migrate to core/qa while continuing to use output_generator for any functionality not yet migrated.

### Q: How do I silence deprecation warnings?

```python
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="output_generator")
```

However, we recommend migrating to core/qa before v4.0 rather than silencing warnings.

### Q: What if my project uses Anthem-specific state handling?

The core/qa module uses a unified approach. For Anthem projects, set up your paths to include state subdirectories:

```python
# Old
type_checker(..., anthem_state="TX")

# New
result = validate("20251227/processed/TX/audiobee_anthem-TX-20251227.jsonl")
```

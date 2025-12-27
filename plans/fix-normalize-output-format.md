# Plan: Fix Normalize Phase Output Format

## Problem Statement

The healthsparq library's normalize.py output format differs from the expected schema defined at `core/data/output_json_schema.json`. Additionally, `uszips.xlsx` has been moved to `core/data/` since it's needed by all projects.

## Key Issues Identified

### 1. ZIP Code Format Mismatch

- **Schema Requirement**: `"zip": {"type": "string", "pattern": "^[0-9]{5}$"}` (exactly 5 digits)
- **Current Behavior**: `normalize.py` line 128 passes through raw ZIP codes as-is
- **Problem**: HealthSparq API may return 9-digit ZIP codes (`12345-6789` or `123456789`)

**Evidence**:

```python
# normalize.py:128
zip_code = loc.get("address", {}).get("zip")
# No normalization - passed directly to output
```

### 2. uszips.xlsx Path Mismatch

- **New Location**: `core/data/uszips.xlsx` (shared across all projects)
- **Current Code**: `healthsparq/phases/search.py` looks in `healthsparq/data/uszips.xlsx`

**Evidence**:

```python
# search.py:48-53
package_data = Path(__file__).parent.parent / "data" / "uszips.xlsx"
if package_data.exists():
    self.zip_data_path = package_data
else:
    self.zip_data_path = Path("uszips.xlsx")  # Falls back to CWD
```

### 3. Output Format Differences vs Master Branch

Comparing `audiobee_medica_sg/index_3.py` (master) with `healthsparq/phases/normalize.py`:

| Feature                       | Master (index_3.py)                      | Library (normalize.py)            |
| ----------------------------- | ---------------------------------------- | --------------------------------- |
| Network name sorting          | `sorted(network_names)`                  | No sorting                        |
| Address filtering             | Filters null street_line_1/zip           | Filters null street_line_1/zip    |
| Group affiliations sorting    | `sorted(group_affiliations)`             | No sorting                        |
| Hospital affiliations sorting | `sorted(hospital_affiliations)`          | No sorting                        |
| Specialties sorting           | `sorted(specialties)`                    | No sorting                        |
| Missing v2 handling           | `raise ValueError("v2 data is missing")` | Returns empty mapped_data         |
| Network name extraction       | Nested: `subCategories` > `plans`        | Nested: `subCategories` > `plans` |

## Implementation Plan

### Phase 1: Fix ZIP Code Normalization (Priority: High)

Add ZIP code normalization helper function:

```python
def normalize_zip_code(zip_code: str | None) -> str | None:
    """Normalize ZIP code to 5 digits as per schema requirements.

    Handles formats: "12345", "12345-6789", "123456789"
    Returns None if invalid.
    """
    if zip_code is None:
        return None

    # Remove dashes and whitespace
    cleaned = zip_code.replace("-", "").replace(" ", "").strip()

    # Extract first 5 digits
    if len(cleaned) >= 5 and cleaned[:5].isdigit():
        return cleaned[:5]

    return None
```

**Files to modify**:

- `healthsparq/phases/normalize.py:128` - Apply normalization in `get_addresses()`

### Phase 2: Update uszips.xlsx Path (Priority: High)

Update search.py to look in `core/data/`:

```python
def __post_init__(self):
    if self.zip_data_path is None:
        # Priority 1: core/data directory (shared across all projects)
        core_data = Path(__file__).parent.parent.parent / "core" / "data" / "uszips.xlsx"
        if core_data.exists():
            self.zip_data_path = core_data
        else:
            # Priority 2: Package data directory (legacy)
            package_data = Path(__file__).parent.parent / "data" / "uszips.xlsx"
            if package_data.exists():
                self.zip_data_path = package_data
            else:
                # Priority 3: Current working directory
                self.zip_data_path = Path("uszips.xlsx")
```

**Files to modify**:

- `healthsparq/phases/search.py:47-53` - Update path resolution logic

### Phase 3: Add Consistent Sorting (Priority: Medium)

Match master branch sorting behavior for deterministic output:

1. **Networks**: Sort by name
2. **Addresses**: Sort by address_string
3. **Group Affiliations**: Sort by name
4. **Hospital Affiliations**: Sort by name
5. **Specialties**: Sort by name

**Files to modify**:

- `healthsparq/phases/normalize.py` - Add sorting in `map_to_schema()`

### Phase 4: Schema Validation (Priority: Low)

Add optional JSON Schema validation to normalize phase:

```python
def validate_against_schema(record: dict, schema_path: Path) -> bool:
    """Validate a mapped record against the output schema."""
    # Load schema once at module level
    # Validate each record before writing
```

**Files to modify**:

- `healthsparq/phases/normalize.py` - Add validation option
- `healthsparq/api.py` - Expose validation flag

## Test Plan

1. **Unit Tests**:
   - `test_normalize_zip_code()` - Test all ZIP formats
   - `test_uszips_path_resolution()` - Test path fallback logic

2. **Integration Tests**:
   - Run normalize phase with test data
   - Validate output against `core/data/output_json_schema.json`

3. **Comparison Test**:
   - Run both master `index_3.py` and library `normalize.py` on same data
   - Compare output structure and values

## Files to Modify

| File                                  | Changes                                   |
| ------------------------------------- | ----------------------------------------- |
| `healthsparq/phases/normalize.py`     | Add ZIP normalization, consistent sorting |
| `healthsparq/phases/search.py`        | Update uszips.xlsx path resolution        |
| `healthsparq/tests/test_normalize.py` | Add tests for ZIP normalization           |
| `healthsparq/tests/test_search.py`    | Update path tests                         |

## Risk Assessment

| Risk                             | Mitigation                                                  |
| -------------------------------- | ----------------------------------------------------------- |
| ZIP truncation loses data        | 5-digit is standard; +4 rarely needed for provider matching |
| Path change breaks existing runs | Fallback chain preserves backward compatibility             |
| Sorting changes output order     | Deterministic output improves diffing/comparison            |

## Success Criteria

1. All output ZIP codes match pattern `^[0-9]{5}$`
2. Search phase finds `uszips.xlsx` from `core/data/`
3. Output can be validated against `core/data/output_json_schema.json`
4. All existing tests pass
5. Output matches master branch format for same input data

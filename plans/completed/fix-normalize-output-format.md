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

---

## Phase 5: Core Mapper/Normalize Module (Priority: High)

Create a shared `core/mapper/` module that converts raw provider data to schema-compliant JSONL. This centralizes normalization logic for all scrapers.

### 5.1 Target Schema

The output must conform to `core/data/output_json_schema.json`:

```json
{
  "networks": [{ "name": "string", "tier": "string|null" }],
  "provider": {
    "unparsed_name": "string",
    "gender": "M|F|O|null",
    "provider_type": "individual|organization",
    "npi": "string (10 digits)|null",
    "license_number": "string|null",
    "facility_name": "string|null",
    "first_name": "string|null",
    "middle_name": "string|null",
    "last_name": "string|null",
    "title": "string|null",
    "suffix": "string|null",
    "rating": { "score": "number|null", "scale": "number|null" }
  },
  "addresses": [
    {
      "street_line_1": "string",
      "street_line_2": "string|null",
      "city": "string",
      "state": "string",
      "zip": "string (5 digits)",
      "office_name": "string|null",
      "address_string": "string",
      "phones": [{ "type": "phone|fax", "value": "string" }],
      "languages": [{ "name": "string", "type": "primary|secondary" }],
      "pcp": "boolean|null",
      "pcp_id": "string|null",
      "accepting_new_patients": "boolean|null",
      "external_id": "string|null"
    }
  ],
  "group_affiliations": [{ "name": "string" }],
  "hospital_affiliations": [{ "name": "string" }],
  "specialties": [{ "name": "string" }]
}
```

### 5.2 Module Architecture

```
core/
├── mapper/                      # NEW: Provider data normalization
│   ├── __init__.py              # Public exports
│   ├── base.py                  # Abstract BaseMapper, MapperFunc type
│   ├── schema.py                # JSON Schema validation
│   ├── normalize.py             # Shared normalization functions
│   ├── dedup.py                 # NPI-based deduplication
│   └── healthsparq.py           # HealthSparq-specific mapper
│
├── data/
│   └── output_json_schema.json  # Target schema (already exists)
```

### 5.3 Base Mapper Interface

**File**: `core/mapper/base.py`

```python
"""Base mapper interface for provider data normalization."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator

# Type alias for custom mapper functions
MapperFunc = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass
class MapperResult:
    """Result of mapping operation."""
    total_raw: int
    total_mapped: int
    total_deduplicated: int
    duplicates_merged: int
    validation_errors: int
    output_file: Path | None = None
    error: str | None = None


class BaseMapper(ABC):
    """Abstract base class for provider data mappers."""

    @abstractmethod
    def map_record(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Map a single raw record to schema format.

        Args:
            raw: Raw provider data from phase 2.

        Returns:
            Mapped record conforming to output schema.
        """
        pass

    @abstractmethod
    def load_raw_files(self, raw_dir: Path) -> Iterator[dict[str, Any]]:
        """Load raw provider data files from directory.

        Args:
            raw_dir: Directory containing raw JSON/JSONL files.

        Yields:
            Raw provider records.
        """
        pass
```

### 5.4 Shared Normalization Functions

**File**: `core/mapper/normalize.py`

```python
"""Shared normalization utilities for provider data."""

from typing import Any


def normalize_zip_code(zip_code: str | None) -> str | None:
    """Normalize ZIP code to 5 digits per schema requirement.

    Handles: "12345", "12345-6789", "123456789"
    """
    if zip_code is None:
        return None
    cleaned = zip_code.replace("-", "").replace(" ", "").strip()
    if len(cleaned) >= 5 and cleaned[:5].isdigit():
        return cleaned[:5]
    return None


def normalize_gender(gender: str | None) -> str | None:
    """Normalize gender to M/F/O or None."""
    if gender in ["M", "F", "O"]:
        return gender
    return None


def normalize_phone(phone: str | None) -> str | None:
    """Clean phone number formatting."""
    if phone is None:
        return None
    # Remove common formatting characters
    cleaned = phone.replace("-", "").replace("(", "").replace(")", "")
    cleaned = cleaned.replace(" ", "").replace(".", "")
    return cleaned if cleaned else None


def build_address_string(
    street_line_1: str,
    street_line_2: str | None,
    city: str,
    state: str,
    zip_code: str,
) -> str:
    """Build standardized address string."""
    if street_line_2:
        return f"{street_line_1}, {street_line_2}, {city}, {state} {zip_code}"
    return f"{street_line_1}, {city}, {state} {zip_code}"


def clean_network_name(name: str, replacements: dict[str, str] | None = None) -> str:
    """Clean network name by removing special characters.

    Args:
        name: Raw network name.
        replacements: Optional dict of {old: new} replacements.
    """
    cleaned = name.replace('"', "").replace("\\", "").strip()
    if replacements:
        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)
    return cleaned
```

### 5.5 JSON Schema Validation

**File**: `core/mapper/schema.py`

```python
"""JSON Schema validation for provider output."""

import json
from pathlib import Path
from typing import Any

try:
    import jsonschema
    from jsonschema import Draft7Validator
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

from core.logging import logger

# Cache schema at module level
_SCHEMA: dict | None = None
_VALIDATOR: Any = None


def load_schema(schema_path: Path | None = None) -> dict:
    """Load output JSON schema.

    Args:
        schema_path: Path to schema file. Defaults to core/data/output_json_schema.json.
    """
    global _SCHEMA
    if _SCHEMA is not None:
        return _SCHEMA

    if schema_path is None:
        schema_path = Path(__file__).parent.parent / "data" / "output_json_schema.json"

    with open(schema_path, "r") as f:
        _SCHEMA = json.load(f)

    return _SCHEMA


def get_validator() -> Any:
    """Get cached JSON Schema validator."""
    global _VALIDATOR
    if not HAS_JSONSCHEMA:
        return None
    if _VALIDATOR is None:
        schema = load_schema()
        _VALIDATOR = Draft7Validator(schema)
    return _VALIDATOR


def validate_record(record: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a mapped record against output schema.

    Returns:
        (is_valid, list of error messages)
    """
    validator = get_validator()
    if validator is None:
        logger.warning("jsonschema not installed - skipping validation")
        return True, []

    errors = []
    for error in validator.iter_errors(record):
        errors.append(f"{error.json_path}: {error.message}")

    return len(errors) == 0, errors


def validate_batch(
    records: list[dict[str, Any]],
    max_errors: int = 100,
) -> tuple[int, list[str]]:
    """Validate multiple records, stopping after max_errors.

    Returns:
        (valid_count, list of first max_errors error messages)
    """
    valid_count = 0
    all_errors = []

    for i, record in enumerate(records):
        is_valid, errors = validate_record(record)
        if is_valid:
            valid_count += 1
        else:
            for err in errors:
                if len(all_errors) < max_errors:
                    all_errors.append(f"Record {i}: {err}")

    return valid_count, all_errors
```

### 5.6 NPI-Based Deduplication

**File**: `core/mapper/dedup.py`

```python
"""NPI-based provider deduplication."""

from copy import deepcopy
from typing import Any


def merge_provider_records(
    existing: dict[str, Any],
    new: dict[str, Any],
) -> dict[str, Any]:
    """Merge two provider records with same NPI.

    Merges: networks, addresses, affiliations, specialties.
    Fills: missing license_number.
    """
    merged = deepcopy(existing)

    # Merge networks by name
    existing_networks = {n["name"] for n in merged["networks"]}
    for network in new["networks"]:
        if network["name"] not in existing_networks:
            merged["networks"].append(network)

    # Merge addresses by external_id
    existing_addr_ids = {a.get("external_id") for a in merged["addresses"]}
    for addr in new["addresses"]:
        if addr.get("external_id") not in existing_addr_ids:
            merged["addresses"].append(addr)

    # Merge group affiliations
    existing_groups = {g["name"] for g in merged["group_affiliations"]}
    for grp in new["group_affiliations"]:
        if grp["name"] not in existing_groups:
            merged["group_affiliations"].append(grp)

    # Merge hospital affiliations
    existing_hospitals = {h["name"] for h in merged["hospital_affiliations"]}
    for hosp in new["hospital_affiliations"]:
        if hosp["name"] not in existing_hospitals:
            merged["hospital_affiliations"].append(hosp)

    # Merge specialties
    existing_specs = {s["name"] for s in merged["specialties"]}
    for spec in new["specialties"]:
        if spec["name"] not in existing_specs:
            merged["specialties"].append(spec)

    # Fill missing license_number
    if merged["provider"].get("license_number") is None:
        merged["provider"]["license_number"] = new["provider"].get("license_number")

    return merged


def deduplicate_by_npi(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Deduplicate provider records by NPI.

    Returns:
        (deduplicated_records, merge_count)
    """
    npi_map: dict[str, dict[str, Any]] = {}
    no_npi_records: list[dict[str, Any]] = []
    merge_count = 0

    for record in records:
        npi = record.get("provider", {}).get("npi")
        if npi is None:
            no_npi_records.append(record)
        elif npi not in npi_map:
            npi_map[npi] = record
        else:
            npi_map[npi] = merge_provider_records(npi_map[npi], record)
            merge_count += 1

    return list(npi_map.values()) + no_npi_records, merge_count
```

### 5.7 HealthSparq Mapper Implementation

**File**: `core/mapper/healthsparq.py`

```python
"""HealthSparq-specific provider data mapper."""

from copy import deepcopy
from pathlib import Path
from typing import Any, Iterator

import orjson

from core.logging import logger
from core.mapper.base import BaseMapper, MapperResult
from core.mapper.normalize import (
    normalize_zip_code,
    normalize_gender,
    build_address_string,
    clean_network_name,
)
from core.mapper.dedup import deduplicate_by_npi
from core.mapper.schema import validate_record


class HealthSparqMapper(BaseMapper):
    """Mapper for HealthSparq provider data (v2 format)."""

    def __init__(self, network_replacements: dict[str, str] | None = None):
        """Initialize mapper.

        Args:
            network_replacements: Optional {old: new} for network name cleaning.
        """
        self.network_replacements = network_replacements or {}

    def load_raw_files(self, raw_dir: Path) -> Iterator[dict[str, Any]]:
        """Load raw JSON files from provider_details directory."""
        if not raw_dir.exists():
            return

        for file_path in raw_dir.glob("*.json"):
            try:
                with open(file_path, "rb") as f:
                    yield orjson.loads(f.read())
            except (orjson.JSONDecodeError, UnicodeDecodeError) as e:
                logger.warning(f"Skipping corrupted file {file_path}: {e}")
            except (OSError, IOError) as e:
                logger.warning(f"Unable to read file {file_path}: {e}")

    def map_record(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Map raw HealthSparq provider data to schema format."""
        mapped = {
            "networks": [],
            "provider": {},
            "addresses": [],
            "group_affiliations": [],
            "hospital_affiliations": [],
            "specialties": [],
        }

        npi = raw.get("npi")
        v2_data = raw.get("v2")

        if v2_data is None:
            return mapped

        # Merge v2 data with NPI
        data = deepcopy(v2_data)
        data["npi"] = npi

        # Flatten attributes
        for attr in data.get("attributes", []):
            data[attr.get("key")] = attr.get("value")

        mapped["networks"] = self._get_networks(data)
        mapped["provider"] = self._get_provider(data)
        mapped["addresses"] = self._get_addresses(data)
        mapped["group_affiliations"] = self._get_group_affiliations(data)
        mapped["hospital_affiliations"] = self._get_hospital_affiliations(data)
        mapped["specialties"] = self._get_specialties(data)

        return mapped

    def _get_networks(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract and sort network names."""
        network_names = set()
        for loc in data.get("locations", []):
            for attr in loc.get("attributes", []):
                loc[attr.get("key")] = attr.get("value")
            for category in loc.get("PLANS_ACCEPTED", []):
                for sub_category in category.get("subCategories", []):
                    for plan in sub_category.get("plans", []):
                        name = plan.get("name", "")
                        cleaned = clean_network_name(name, self.network_replacements)
                        if cleaned:
                            network_names.add(cleaned)
        return [{"name": n, "tier": None} for n in sorted(network_names)]

    def _get_provider(self, data: dict[str, Any]) -> dict[str, Any]:
        """Extract provider details."""
        provider_type = (
            "individual" if data.get("providerCategoryCode") == "P" else "organization"
        )

        full_name = data.get("provider", {}).get("fullName", "")
        gender = None

        if provider_type == "individual":
            full_name = " ".join(reversed(full_name.split(","))).strip()
            raw_gender = data.get("GENDER")
            gender = normalize_gender(raw_gender[0] if raw_gender else None)

        return {
            "unparsed_name": full_name,
            "gender": gender,
            "provider_type": provider_type,
            "npi": data.get("npi"),
            "license_number": data.get("licenseNumber"),
            "facility_name": full_name if provider_type == "organization" else None,
            "first_name": data.get("provider", {}).get("firstName"),
            "middle_name": data.get("provider", {}).get("middleName"),
            "last_name": data.get("provider", {}).get("lastName"),
            "title": " ".join(data.get("degreeCredentials", [])) or None,
            "suffix": data.get("provider", {}).get("suffix"),
            "rating": {"score": None, "scale": None},
        }

    def _get_addresses(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract and normalize addresses."""
        addresses = []

        for loc in data.get("locations", []):
            accepting_new_patients = False
            pcp = False

            # Check attributes for PCP and ANP flags
            for attr in loc.get("attributes", []):
                if attr.get("key") == "PLANS_ACCEPTED":
                    for plan in attr.get("value", []):
                        if plan.get("pcpEligible"):
                            pcp = True
                        label_key = plan.get("acceptingPatients", {}).get("labelKey", "")
                        if label_key in ["elevated.anp.acceptingSome", "elevated.anp.acceptingAll"]:
                            accepting_new_patients = True

            # Check elevated attributes for PCP
            for elev_attr in loc.get("elevatedAttributes", []):
                if elev_attr.get("labelKey") == "elevated.pcp.true" and elev_attr.get("style") == "success":
                    pcp = True
                    break

            # Extract address fields
            addr = loc.get("address", {})
            street_line_1 = addr.get("line1")
            street_line_2 = addr.get("line2")
            city = addr.get("city")
            state = addr.get("state")
            zip_code = normalize_zip_code(addr.get("zip"))

            # Skip invalid addresses
            if street_line_1 is None or zip_code is None:
                continue

            # Extract contact info
            phones = []
            for attr in loc.get("attributes", []):
                if attr.get("key") == "CONTACT":
                    for contact in attr.get("value", []):
                        contact_type = contact.get("type")
                        if contact_type in ["phone", "fax"]:
                            values = contact.get("values", [])
                            if values:
                                phones.append({
                                    "type": contact_type,
                                    "value": values[0].get("display", ""),
                                })

            # Extract languages
            languages = [
                {"name": lang, "type": "primary"}
                for lang in data.get("PROVIDER_LANGUAGES", loc.get("STAFF_LANGUAGES", []))
            ]

            addresses.append({
                "street_line_1": street_line_1,
                "street_line_2": street_line_2,
                "city": city,
                "state": state,
                "zip": zip_code,
                "office_name": loc.get("name"),
                "address_string": build_address_string(
                    street_line_1, street_line_2, city, state, zip_code
                ),
                "phones": phones,
                "languages": languages,
                "pcp": pcp,
                "pcp_id": loc.get("pcpId"),
                "accepting_new_patients": accepting_new_patients,
                "external_id": str(loc.get("id")) if loc.get("id") else None,
            })

        # Sort by address_string for deterministic output
        return sorted(addresses, key=lambda x: x["address_string"])

    def _get_group_affiliations(self, data: dict[str, Any]) -> list[dict[str, str]]:
        """Extract sorted group affiliations."""
        affiliations = set(x["name"] for x in data.get("GROUP_AFFILIATIONS", []))
        return [{"name": a} for a in sorted(affiliations)]

    def _get_hospital_affiliations(self, data: dict[str, Any]) -> list[dict[str, str]]:
        """Extract sorted hospital affiliations."""
        affiliations = set(x["name"] for x in data.get("HOSPITAL_AFFILIATIONS", []))

        for loc in data.get("locations", []):
            for attr in loc.get("attributes", []):
                if attr.get("name") == "Hospital Affiliation":
                    for aff in attr.get("value", []):
                        affiliations.add(aff)

        return [{"name": a} for a in sorted(affiliations)]

    def _get_specialties(self, data: dict[str, Any]) -> list[dict[str, str]]:
        """Extract sorted specialties."""
        specialties = set()
        for loc in data.get("locations", []):
            for attr in loc.get("attributes", []):
                if attr.get("key") == "SPECIALTY":
                    for spec in attr.get("value", []):
                        specialties.add(spec)
        return [{"name": s} for s in sorted(specialties)]


def run_normalize(
    raw_dir: Path,
    output_file: Path,
    mapper: HealthSparqMapper | None = None,
    validate: bool = False,
) -> MapperResult:
    """Run full normalization pipeline.

    Args:
        raw_dir: Directory containing raw JSON files.
        output_file: Path for output JSONL file.
        mapper: Optional custom mapper instance.
        validate: Whether to validate against JSON schema.

    Returns:
        MapperResult with statistics.
    """
    mapper = mapper or HealthSparqMapper()

    logger.info(f"Loading raw files from {raw_dir}")
    raw_records = list(mapper.load_raw_files(raw_dir))
    total_raw = len(raw_records)
    logger.info(f"Loaded {total_raw} raw records")

    if total_raw == 0:
        return MapperResult(
            total_raw=0, total_mapped=0, total_deduplicated=0,
            duplicates_merged=0, validation_errors=0,
        )

    # Map records
    logger.info("Mapping records to schema")
    mapped_records = []
    for record in raw_records:
        try:
            mapped = mapper.map_record(record)
            if mapped.get("provider"):
                mapped_records.append(mapped)
        except Exception as e:
            logger.warning(f"Error mapping record: {e}")

    total_mapped = len(mapped_records)
    logger.info(f"Mapped {total_mapped} records")

    # Deduplicate
    logger.info("Deduplicating by NPI")
    deduplicated, merge_count = deduplicate_by_npi(mapped_records)
    logger.info(f"Deduplicated to {len(deduplicated)} unique providers")

    # Validate if requested
    validation_errors = 0
    if validate:
        logger.info("Validating against schema")
        for record in deduplicated:
            is_valid, errors = validate_record(record)
            if not is_valid:
                validation_errors += 1
                for err in errors[:3]:  # Log first 3 errors
                    logger.warning(f"Validation error: {err}")

    # Write output
    logger.info(f"Writing output to {output_file}")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "wb") as f:
        for record in deduplicated:
            f.write(orjson.dumps(record) + b"\n")

    return MapperResult(
        total_raw=total_raw,
        total_mapped=total_mapped,
        total_deduplicated=len(deduplicated),
        duplicates_merged=merge_count,
        validation_errors=validation_errors,
        output_file=output_file,
    )
```

### 5.8 Public API Exports

**File**: `core/mapper/__init__.py`

```python
"""Provider data normalization and mapping utilities."""

from core.mapper.base import BaseMapper, MapperFunc, MapperResult
from core.mapper.normalize import (
    normalize_zip_code,
    normalize_gender,
    normalize_phone,
    build_address_string,
    clean_network_name,
)
from core.mapper.dedup import merge_provider_records, deduplicate_by_npi
from core.mapper.schema import load_schema, validate_record, validate_batch
from core.mapper.healthsparq import HealthSparqMapper, run_normalize

__all__ = [
    # Base types
    "BaseMapper",
    "MapperFunc",
    "MapperResult",
    # Normalization utilities
    "normalize_zip_code",
    "normalize_gender",
    "normalize_phone",
    "build_address_string",
    "clean_network_name",
    # Deduplication
    "merge_provider_records",
    "deduplicate_by_npi",
    # Schema validation
    "load_schema",
    "validate_record",
    "validate_batch",
    # HealthSparq implementation
    "HealthSparqMapper",
    "run_normalize",
]
```

### 5.9 Integration with healthsparq Package

After implementing `core/mapper/`, update `healthsparq/phases/normalize.py` to use shared utilities:

```python
# healthsparq/phases/normalize.py
try:
    from core.mapper import (
        normalize_zip_code,
        deduplicate_by_npi,
        validate_record,
        clean_network_name,
    )
except ImportError:
    # Fallback to local implementations
    from healthsparq.phases._normalize_utils import (
        normalize_zip_code,
        deduplicate_by_npi,
    )
```

### 5.10 Files to Create/Modify

| File                              | Action | Description                     |
| --------------------------------- | ------ | ------------------------------- |
| `core/mapper/__init__.py`         | Create | Public API exports              |
| `core/mapper/base.py`             | Create | BaseMapper ABC, MapperFunc type |
| `core/mapper/normalize.py`        | Create | Shared normalization utilities  |
| `core/mapper/schema.py`           | Create | JSON Schema validation          |
| `core/mapper/dedup.py`            | Create | NPI-based deduplication         |
| `core/mapper/healthsparq.py`      | Create | HealthSparq-specific mapper     |
| `healthsparq/phases/normalize.py` | Modify | Import from core/mapper         |
| `core/__init__.py`                | Modify | Export mapper module            |

### 5.11 Usage Examples

**CLI usage:**

```bash
# Run normalize phase with schema validation
python -c "
from pathlib import Path
from core.mapper import run_normalize, HealthSparqMapper

result = run_normalize(
    raw_dir=Path('20251227/raw/provider_details'),
    output_file=Path('20251227/processed/providers.jsonl'),
    validate=True,
)
print(f'Mapped {result.total_mapped} → {result.total_deduplicated} providers')
"
```

**Library usage:**

```python
from core.mapper import HealthSparqMapper, deduplicate_by_npi, validate_record

# Custom mapper with project-specific network replacements
mapper = HealthSparqMapper(network_replacements={"medica_sg": "medica"})

# Map single record
raw_data = {"npi": "1234567890", "v2": {...}}
mapped = mapper.map_record(raw_data)

# Validate output
is_valid, errors = validate_record(mapped)
if not is_valid:
    print(f"Validation errors: {errors}")
```

### 5.12 Test Plan

```python
# core/tests/test_mapper.py

def test_normalize_zip_code():
    """Test ZIP code normalization."""
    assert normalize_zip_code("12345") == "12345"
    assert normalize_zip_code("12345-6789") == "12345"
    assert normalize_zip_code("123456789") == "12345"
    assert normalize_zip_code(None) is None
    assert normalize_zip_code("1234") is None


def test_healthsparq_mapper():
    """Test HealthSparq provider mapping."""
    mapper = HealthSparqMapper()
    raw = {
        "npi": "1234567890",
        "v2": {
            "providerCategoryCode": "P",
            "provider": {"fullName": "Smith, John", "firstName": "John", "lastName": "Smith"},
            "attributes": [{"key": "GENDER", "value": "M"}],
            "locations": [],
        }
    }
    mapped = mapper.map_record(raw)
    assert mapped["provider"]["npi"] == "1234567890"
    assert mapped["provider"]["provider_type"] == "individual"


def test_schema_validation():
    """Test JSON Schema validation."""
    valid_record = {
        "networks": [{"name": "Network A", "tier": None}],
        "provider": {
            "unparsed_name": "John Smith",
            "gender": "M",
            "provider_type": "individual",
            "npi": "1234567890",
            "license_number": None,
            "facility_name": None,
            "first_name": "John",
            "middle_name": None,
            "last_name": "Smith",
            "title": None,
            "suffix": None,
            "rating": {"score": None, "scale": None},
        },
        "addresses": [],
        "group_affiliations": [],
        "hospital_affiliations": [],
        "specialties": [],
    }
    is_valid, errors = validate_record(valid_record)
    assert is_valid
    assert len(errors) == 0
```

---

## Updated Implementation Priority

| Phase | Priority | Description                                  | Status  |
| ----- | -------- | -------------------------------------------- | ------- |
| 1     | High     | ZIP code normalization in healthsparq        | Done    |
| 2     | High     | uszips.xlsx path resolution                  | Done    |
| 3     | Medium   | Deterministic sorting                        | Done    |
| 4     | Low      | Schema validation in healthsparq             | Pending |
| **5** | **High** | **Core mapper module with shared utilities** | **New** |

## Migration Strategy

1. **Phase 5 first**: Implement `core/mapper/` module with all shared utilities
2. **Integration**: Update `healthsparq/phases/normalize.py` to import from `core/mapper`
3. **Validation**: Add optional schema validation using `core/mapper/schema.py`
4. **Rollout**: Gradually migrate other scrapers to use `core/mapper/` utilities

## Dependencies

- `orjson` (existing) - Fast JSON serialization
- `jsonschema` (optional) - JSON Schema validation (add to requirements if needed)

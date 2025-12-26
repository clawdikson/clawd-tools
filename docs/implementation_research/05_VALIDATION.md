# Validation System Design

**Technology**: Pydantic v2 for schema validation
**Components**: RawFileValidator, ProviderRecord models, ValidationReport

---

## Current State

### Existing Validation (`output_generator/type_check.py`)

- Uses `jsonschema` library
- `SchemaValidator.validate_record()` validates records
- Validation currently **commented out** in main loop
- Schema defined as inline Python dict

### Patterns in Scrapers

| Pattern | Files | Example |
|---------|-------|---------|
| NPI regex | 5+ | `^[0-9]{10}$` |
| ZIP extraction | 10+ | `zip[:5]` |
| Encoding fallback | 3+ | UTF-8 → Windows-1252 |
| Corruption check | 2 | Delete invalid files |

---

## Implementation

### RawFileValidator

```python
# shared/validation/raw_file.py

import os
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Iterator
from pathlib import Path
import orjson


class FileStatus(Enum):
    """File validation status codes."""
    VALID = "valid"
    EMPTY = "empty"
    TOO_SMALL = "too_small"
    TOO_LARGE = "too_large"
    TRUNCATED = "truncated"
    INVALID_JSON = "invalid_json"
    ENCODING_ERROR = "encoding_error"
    MISSING = "missing"


@dataclass
class FileValidationResult:
    """Result of file validation."""
    path: str
    status: FileStatus
    size_bytes: int = 0
    error: Optional[str] = None
    encoding: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        return self.status == FileStatus.VALID


class RawFileValidator:
    """
    Validates raw JSON/JSONL files for corruption.

    Checks:
    - File exists and readable
    - Size within bounds
    - Valid JSON/JSONL structure
    - No truncation
    - Encoding detection

    Usage:
        validator = RawFileValidator(min_size=10, max_size=500_000_000)

        result = validator.validate_file("data.json")
        if not result.is_valid:
            print(f"Invalid: {result.error}")

        # Batch validation
        for result in validator.validate_directory("/raw/", "*.json"):
            if not result.is_valid:
                validator.quarantine(result.path, "/quarantine/")
    """

    def __init__(
        self,
        min_size: int = 10,
        max_size: int = 500_000_000,  # 500MB
        encodings: List[str] = None,
    ):
        self.min_size = min_size
        self.max_size = max_size
        self.encodings = encodings or ['utf-8', 'windows-1252', 'latin-1']

    def validate_file(self, filepath: str) -> FileValidationResult:
        """Validate single JSON/JSONL file."""
        path = Path(filepath)

        # Check existence
        if not path.exists():
            return FileValidationResult(
                path=filepath,
                status=FileStatus.MISSING,
                error="File not found"
            )

        # Check size
        size = path.stat().st_size

        if size == 0:
            return FileValidationResult(
                path=filepath,
                status=FileStatus.EMPTY,
                size_bytes=0,
                error="File is empty"
            )

        if size < self.min_size:
            return FileValidationResult(
                path=filepath,
                status=FileStatus.TOO_SMALL,
                size_bytes=size,
                error=f"Too small: {size} bytes"
            )

        if size > self.max_size:
            return FileValidationResult(
                path=filepath,
                status=FileStatus.TOO_LARGE,
                size_bytes=size,
                error=f"Too large: {size} bytes"
            )

        # Try encodings
        is_jsonl = filepath.endswith('.jsonl')

        for encoding in self.encodings:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    content = f.read()

                # Validate structure
                if is_jsonl:
                    for i, line in enumerate(content.strip().split('\n'), 1):
                        if line.strip():
                            try:
                                orjson.loads(line)
                            except orjson.JSONDecodeError as e:
                                return FileValidationResult(
                                    path=filepath,
                                    status=FileStatus.INVALID_JSON,
                                    size_bytes=size,
                                    encoding=encoding,
                                    error=f"Line {i}: {e}"
                                )
                else:
                    try:
                        orjson.loads(content)
                    except orjson.JSONDecodeError as e:
                        if self._is_truncated(content):
                            return FileValidationResult(
                                path=filepath,
                                status=FileStatus.TRUNCATED,
                                size_bytes=size,
                                encoding=encoding,
                                error=f"Truncated JSON: {e}"
                            )
                        return FileValidationResult(
                            path=filepath,
                            status=FileStatus.INVALID_JSON,
                            size_bytes=size,
                            encoding=encoding,
                            error=str(e)
                        )

                # Success
                return FileValidationResult(
                    path=filepath,
                    status=FileStatus.VALID,
                    size_bytes=size,
                    encoding=encoding
                )

            except UnicodeDecodeError:
                continue

        return FileValidationResult(
            path=filepath,
            status=FileStatus.ENCODING_ERROR,
            size_bytes=size,
            error=f"Failed with encodings: {self.encodings}"
        )

    def _is_truncated(self, content: str) -> bool:
        """Check if JSON appears truncated."""
        content = content.strip()
        if not content:
            return True
        # Unbalanced brackets/braces
        if content.count('{') != content.count('}'):
            return True
        if content.count('[') != content.count(']'):
            return True
        return False

    def validate_directory(
        self,
        directory: str,
        pattern: str = "*.json",
        recursive: bool = False,
    ) -> Iterator[FileValidationResult]:
        """Validate all matching files in directory."""
        path = Path(directory)
        files = path.rglob(pattern) if recursive else path.glob(pattern)
        for f in files:
            yield self.validate_file(str(f))

    def quarantine(self, filepath: str, quarantine_dir: str) -> str:
        """Move invalid file to quarantine."""
        import shutil
        from datetime import datetime

        Path(quarantine_dir).mkdir(parents=True, exist_ok=True)
        source = Path(filepath)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = Path(quarantine_dir) / f"{ts}_{source.name}"
        shutil.move(str(source), str(dest))
        return str(dest)
```

### Pydantic Schema Models

```python
# shared/validation/schema.py

import re
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


class Phone(BaseModel):
    """Phone number."""
    type: Literal["phone", "fax"]
    value: str

    @field_validator('value')
    @classmethod
    def normalize_phone(cls, v: str) -> str:
        if v is None:
            return v
        digits = re.sub(r'\D', '', v)
        if len(digits) < 10:
            raise ValueError(f"Phone too short: {v}")
        if len(digits) == 11 and digits.startswith('1'):
            return digits[1:]
        return digits


class Language(BaseModel):
    """Language with type."""
    name: str
    type: Literal["primary", "secondary"]


class Rating(BaseModel):
    """Provider rating."""
    score: Optional[float] = None
    scale: Optional[float] = None


class Address(BaseModel):
    """Provider address."""
    street_line_1: str
    street_line_2: Optional[str] = None
    city: str
    state: str = Field(..., min_length=2, max_length=2)
    zip: str = Field(..., pattern=r'^\d{5}$')
    office_name: Optional[str] = None
    address_string: str
    phones: List[Phone] = Field(default_factory=list)
    languages: List[Language] = Field(default_factory=list)
    accepting_new_patients: Optional[bool] = None

    @field_validator('state')
    @classmethod
    def validate_state(cls, v: str) -> str:
        return v.upper()

    @field_validator('zip')
    @classmethod
    def validate_zip(cls, v: str) -> str:
        digits = re.sub(r'\D', '', v)[:5]
        if len(digits) != 5:
            raise ValueError(f"Invalid ZIP: {v}")
        return digits


class Provider(BaseModel):
    """Provider information."""
    unparsed_name: str
    gender: Optional[Literal["M", "F", "O", "U"]] = None
    provider_type: Literal["individual", "organization"]
    npi: Optional[str] = Field(default=None, pattern=r'^\d{10}$')
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    facility_name: Optional[str] = None
    rating: Optional[Rating] = None

    @field_validator('npi')
    @classmethod
    def validate_npi(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        digits = re.sub(r'\D', '', str(v))
        if len(digits) != 10:
            raise ValueError(f"NPI must be 10 digits: {v}")
        return digits


class Network(BaseModel):
    """Network affiliation."""
    name: str
    tier: Optional[str] = None


class Specialty(BaseModel):
    """Medical specialty."""
    name: str


class GroupAffiliation(BaseModel):
    """Group affiliation."""
    name: str


class HospitalAffiliation(BaseModel):
    """Hospital affiliation."""
    name: str


class ProviderRecord(BaseModel):
    """
    Complete provider record matching output schema.

    Usage:
        from shared.validation import ProviderRecord, validate_record

        # Validate
        try:
            record = ProviderRecord(**data)
        except ValidationError as e:
            print(e.errors())

        # Or use function
        result = validate_record(data)
        if not result.is_valid:
            print(result.error)
    """
    networks: List[Network] = Field(default_factory=list)
    provider: Provider
    addresses: List[Address] = Field(default_factory=list)
    specialties: List[Specialty] = Field(default_factory=list)
    group_affiliations: List[GroupAffiliation] = Field(default_factory=list)
    hospital_affiliations: List[HospitalAffiliation] = Field(default_factory=list)

    def get_unique_key(self) -> str:
        """Generate deduplication key."""
        if self.provider.npi:
            return f"npi:{self.provider.npi}"
        name = self.provider.unparsed_name.lower().strip()
        zip_code = self.addresses[0].zip if self.addresses else "no_zip"
        return f"name:{name}|zip:{zip_code}"
```

### Validation Functions

```python
# shared/validation/validators.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import orjson
from pydantic import ValidationError
from .schema import ProviderRecord


@dataclass
class RecordValidationResult:
    """Result of single record validation."""
    is_valid: bool
    error: Optional[str] = None
    error_details: Optional[List[Dict]] = None
    line_number: Optional[int] = None


def validate_record(
    data: Dict[str, Any],
    line_number: Optional[int] = None,
) -> RecordValidationResult:
    """
    Validate single provider record.

    Args:
        data: Record dictionary
        line_number: Optional line number for error reporting

    Returns:
        RecordValidationResult
    """
    try:
        ProviderRecord(**data)
        return RecordValidationResult(is_valid=True, line_number=line_number)
    except ValidationError as e:
        return RecordValidationResult(
            is_valid=False,
            error=str(e),
            error_details=e.errors(),
            line_number=line_number
        )


@dataclass
class FileValidationSummary:
    """Summary of JSONL file validation."""
    filepath: str
    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    duplicate_records: int = 0
    unique_npis: Set[str] = field(default_factory=set)
    errors: List[RecordValidationResult] = field(default_factory=list)
    processing_time: float = 0.0

    @property
    def valid_percentage(self) -> float:
        if self.total_records == 0:
            return 0.0
        return (self.valid_records / self.total_records) * 100

    @property
    def is_healthy(self) -> bool:
        return self.valid_percentage >= 95.0


def validate_file(
    filepath: str,
    max_errors: int = 100,
    check_duplicates: bool = True,
    progress_callback: Optional[callable] = None,
) -> FileValidationSummary:
    """
    Validate entire JSONL file.

    Args:
        filepath: Path to JSONL file
        max_errors: Stop collecting errors after this count
        check_duplicates: Track NPI duplicates
        progress_callback: Optional callback(current, total)

    Returns:
        FileValidationSummary
    """
    import time
    start = time.time()

    summary = FileValidationSummary(filepath=filepath)
    seen_npis: Set[str] = set()

    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if progress_callback and line_num % 1000 == 0:
                progress_callback(line_num, 0)

            line = line.strip()
            if not line:
                continue

            summary.total_records += 1

            try:
                record = orjson.loads(line)
            except orjson.JSONDecodeError as e:
                summary.invalid_records += 1
                if len(summary.errors) < max_errors:
                    summary.errors.append(RecordValidationResult(
                        is_valid=False,
                        error=f"JSON error: {e}",
                        line_number=line_num
                    ))
                continue

            result = validate_record(record, line_number=line_num)

            if result.is_valid:
                summary.valid_records += 1

                if check_duplicates:
                    npi = record.get('provider', {}).get('npi')
                    if npi:
                        if npi in seen_npis:
                            summary.duplicate_records += 1
                        else:
                            seen_npis.add(npi)
                            summary.unique_npis.add(npi)
            else:
                summary.invalid_records += 1
                if len(summary.errors) < max_errors:
                    summary.errors.append(result)

    summary.processing_time = time.time() - start
    return summary
```

### ValidationReport

```python
# shared/validation/report.py

from dataclasses import dataclass, field
from typing import Dict, List, Any
from datetime import datetime
import json


@dataclass
class ValidationReport:
    """
    Comprehensive validation report.

    Usage:
        report = ValidationReport.create(
            project_name="audiobee_bcbs_il",
            run_date="20251210",
            file_results=[summary1, summary2],
        )
        report.save_json("validation_report.json")
        report.save_excel("validation_report.xlsx")
        report.print_summary()
    """
    project_name: str
    run_date: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Counts
    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    duplicate_records: int = 0
    unique_npis: int = 0

    # Errors
    error_categories: Dict[str, int] = field(default_factory=dict)
    error_samples: Dict[str, List[Dict]] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        project_name: str,
        run_date: str,
        file_results: List['FileValidationSummary'],
    ) -> 'ValidationReport':
        """Create report from validation results."""
        report = cls(project_name=project_name, run_date=run_date)

        all_npis = set()
        for summary in file_results:
            report.total_records += summary.total_records
            report.valid_records += summary.valid_records
            report.invalid_records += summary.invalid_records
            report.duplicate_records += summary.duplicate_records
            all_npis.update(summary.unique_npis)

            for error in summary.errors:
                category = cls._categorize_error(error)
                report.error_categories[category] = \
                    report.error_categories.get(category, 0) + 1

                if category not in report.error_samples:
                    report.error_samples[category] = []
                if len(report.error_samples[category]) < 5:
                    report.error_samples[category].append({
                        "line": error.line_number,
                        "error": error.error[:200] if error.error else None
                    })

        report.unique_npis = len(all_npis)
        return report

    @staticmethod
    def _categorize_error(error) -> str:
        """Categorize error for aggregation."""
        if not error.error:
            return "unknown"
        err = error.error.lower()
        if "npi" in err:
            return "invalid_npi"
        if "zip" in err:
            return "invalid_zip"
        if "phone" in err:
            return "invalid_phone"
        if "json" in err:
            return "json_parse_error"
        return "other"

    @property
    def is_healthy(self) -> bool:
        """Report healthy if >95% valid."""
        if self.total_records == 0:
            return True
        return (self.valid_records / self.total_records) >= 0.95

    @property
    def valid_percentage(self) -> float:
        if self.total_records == 0:
            return 0.0
        return (self.valid_records / self.total_records) * 100

    def save_json(self, filepath: str):
        """Save as JSON."""
        with open(filepath, 'w') as f:
            json.dump({
                "project_name": self.project_name,
                "run_date": self.run_date,
                "created_at": self.created_at,
                "is_healthy": self.is_healthy,
                "summary": {
                    "total": self.total_records,
                    "valid": self.valid_records,
                    "invalid": self.invalid_records,
                    "duplicates": self.duplicate_records,
                    "unique_npis": self.unique_npis,
                    "valid_pct": round(self.valid_percentage, 2),
                },
                "error_categories": self.error_categories,
                "error_samples": self.error_samples,
            }, f, indent=2)

    def save_excel(self, filepath: str):
        """Save as Excel with multiple sheets."""
        import pandas as pd

        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Summary
            pd.DataFrame([{
                "Project": self.project_name,
                "Date": self.run_date,
                "Total": self.total_records,
                "Valid": self.valid_records,
                "Invalid": self.invalid_records,
                "Valid %": f"{self.valid_percentage:.2f}%",
                "Status": "HEALTHY" if self.is_healthy else "NEEDS REVIEW"
            }]).to_excel(writer, sheet_name='Summary', index=False)

            # Errors
            if self.error_categories:
                pd.DataFrame([
                    {"Category": k, "Count": v}
                    for k, v in sorted(
                        self.error_categories.items(),
                        key=lambda x: -x[1]
                    )
                ]).to_excel(writer, sheet_name='Error Categories', index=False)

    def print_summary(self):
        """Print to console."""
        print(f"\n{'='*60}")
        print(f"VALIDATION: {self.project_name} ({self.run_date})")
        print(f"{'='*60}")
        print(f"Total:    {self.total_records:,}")
        print(f"Valid:    {self.valid_records:,} ({self.valid_percentage:.1f}%)")
        print(f"Invalid:  {self.invalid_records:,}")
        print(f"Dupes:    {self.duplicate_records:,}")
        print(f"NPIs:     {self.unique_npis:,}")

        if self.error_categories:
            print(f"\nErrors:")
            for cat, count in sorted(
                self.error_categories.items(),
                key=lambda x: -x[1]
            )[:5]:
                print(f"  {cat}: {count:,}")

        status = "HEALTHY" if self.is_healthy else "NEEDS REVIEW"
        print(f"\nStatus: {status}")
        print(f"{'='*60}\n")
```

---

## Usage Examples

### Raw File Validation

```python
from shared.validation import RawFileValidator

validator = RawFileValidator(min_size=50)

# Single file
result = validator.validate_file("data.json")
if not result.is_valid:
    print(f"Invalid: {result.error}")

# Directory scan
for result in validator.validate_directory("raw/", "*.json", recursive=True):
    if not result.is_valid:
        print(f"Bad file: {result.path} - {result.error}")
        validator.quarantine(result.path, "quarantine/")
```

### Record Validation

```python
from shared.validation import validate_record, ProviderRecord

# Quick validation
result = validate_record(record_dict)
if not result.is_valid:
    print(f"Error: {result.error}")

# Full parsing
try:
    record = ProviderRecord(**record_dict)
    print(f"Valid NPI: {record.provider.npi}")
except ValidationError as e:
    for err in e.errors():
        print(f"{err['loc']}: {err['msg']}")
```

### File Validation

```python
from shared.validation import validate_file, ValidationReport

summary = validate_file(
    "processed/providers.jsonl",
    check_duplicates=True
)

print(f"Valid: {summary.valid_percentage:.1f}%")
print(f"Duplicates: {summary.duplicate_records}")

# Full report
report = ValidationReport.create(
    project_name="audiobee_bcbs_il",
    run_date="20251210",
    file_results=[summary]
)
report.print_summary()
report.save_excel("validation_report.xlsx")
```

---

## Dependencies

```toml
dependencies = [
    "pydantic>=2.0.0",
    "orjson>=3.9.0",
    "openpyxl>=3.1.0",  # Excel export
    "pandas>=2.0.0",     # DataFrames
]
```

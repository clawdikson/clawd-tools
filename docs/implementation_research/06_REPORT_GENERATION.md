# Report Generation Integration

**Purpose**: Integrate shared utilities with existing output_generator/ package
**Approach**: Extend, don't replace existing functionality

---

## Existing output_generator Components

| File | Purpose | Integration Plan |
|------|---------|------------------|
| `type_check.py` | Schema validation | Enhance with Pydantic |
| `comparison_creator.py` | Diff between runs | Keep, add shared I/O |
| `report_generator.py` | Excel summaries | Extend with validation |
| `sample_generator.py` | QA samples | Keep as-is |
| `run_all.py` | Pipeline | Add shared logging |

---

## Integration Points

### 1. type_check.py Enhancement

**Current**: Uses jsonschema with inline schema
**Enhanced**: Add Pydantic as faster alternative

```python
# output_generator/type_check.py (enhanced)

# Keep existing jsonschema for backward compat
from jsonschema import validate, ValidationError as JSONSchemaError

# Add Pydantic option for speed
from shared.validation import validate_record, validate_file, ValidationReport


def type_checker(
    project_name: str,
    curr_date: str,
    curr_processed_dir: str,
    use_pydantic: bool = True,  # NEW: faster option
    anthem_state: str = None,
):
    """
    Validate provider data against schema.

    Args:
        use_pydantic: If True, use faster Pydantic validation
    """
    # Build file path
    if anthem_state:
        main_file = f"{curr_processed_dir}/{anthem_state}/{project_name}-{anthem_state}-{curr_date}.jsonl"
    else:
        main_file = f"{curr_processed_dir}/{project_name}-{curr_date}.jsonl"

    if use_pydantic:
        # NEW: Fast Pydantic validation
        summary = validate_file(main_file, check_duplicates=True)

        report = ValidationReport.create(
            project_name=project_name,
            run_date=curr_date,
            file_results=[summary]
        )
        report.print_summary()

        # Save reports
        base = main_file.replace('.jsonl', '')
        report.save_json(f"{base}_validation.json")
        report.save_excel(f"{base}_validation.xlsx")

        return report.is_healthy
    else:
        # Existing jsonschema logic
        return _legacy_validate(main_file)
```

### 2. report_generator.py Integration

**Add validation summary to Excel reports**

```python
# output_generator/report_generator.py (enhanced)

from shared.validation import ValidationReport


def generate_report(
    project_name: str,
    curr_date: str,
    processed_dir: str,
    validation_report: ValidationReport = None,  # NEW
):
    """Generate Excel report with optional validation summary."""

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Existing sheets
        create_summary_sheet(writer, data)
        create_state_counts_sheet(writer, data)
        create_specialty_sheet(writer, data)

        # NEW: Add validation sheet if provided
        if validation_report:
            create_validation_sheet(writer, validation_report)


def create_validation_sheet(writer, report: ValidationReport):
    """Add validation summary sheet."""
    pd.DataFrame([{
        "Total Records": report.total_records,
        "Valid Records": report.valid_records,
        "Invalid Records": report.invalid_records,
        "Duplicate NPIs": report.duplicate_records,
        "Unique NPIs": report.unique_npis,
        "Valid %": f"{report.valid_percentage:.2f}%",
        "Status": "PASS" if report.is_healthy else "FAIL"
    }]).to_excel(writer, sheet_name='Validation', index=False)

    # Error breakdown
    if report.error_categories:
        pd.DataFrame([
            {"Error Type": k, "Count": v}
            for k, v in report.error_categories.items()
        ]).to_excel(writer, sheet_name='Errors', index=False)
```

### 3. comparison_creator.py Integration

**Use shared I/O for consistency**

```python
# output_generator/comparison_creator.py (enhanced)

from shared.io import JSONLReader
from shared.logging import configure_logger, logger

configure_logger("comparison_creator")


def compare_runs(
    project_name: str,
    prev_date: str,
    curr_date: str,
    prev_dir: str,
    curr_dir: str,
):
    """Compare previous and current run data."""

    # Use shared reader
    prev_reader = JSONLReader(prev_dir)
    curr_reader = JSONLReader(curr_dir)

    prev_file = f"{project_name}-{prev_date}.jsonl"
    curr_file = f"{project_name}-{curr_date}.jsonl"

    # Load with progress
    logger.info(f"Loading previous data: {prev_file}")
    prev_data = {
        r.get('provider', {}).get('npi'): r
        for r in prev_reader.read_all(prev_file)
        if r.get('provider', {}).get('npi')
    }

    logger.info(f"Loading current data: {curr_file}")
    curr_data = {
        r.get('provider', {}).get('npi'): r
        for r in curr_reader.read_all(curr_file)
        if r.get('provider', {}).get('npi')
    }

    # Compare
    added = set(curr_data.keys()) - set(prev_data.keys())
    removed = set(prev_data.keys()) - set(curr_data.keys())
    common = set(curr_data.keys()) & set(prev_data.keys())

    logger.info(f"Added: {len(added)}, Removed: {len(removed)}, Common: {len(common)}")

    return {
        "added": len(added),
        "removed": len(removed),
        "common": len(common),
        "added_npis": list(added)[:100],
        "removed_npis": list(removed)[:100],
    }
```

### 4. run_all.py Integration

**Add logging and validation to pipeline**

```python
# output_generator/run_all.py (enhanced)

from shared.logging import configure_logger, logger, log_duration
from shared.validation import validate_file, ValidationReport


def run_pipeline(
    project_name: str,
    curr_date: str,
    prev_date: str,
    processed_dir: str,
):
    """Run complete QA pipeline."""

    configure_logger(project_name, log_dir=f"{curr_date}/logs")

    logger.info(f"Starting QA pipeline for {project_name}")

    # Step 1: Validate
    with log_duration("Validation"):
        main_file = f"{processed_dir}/{project_name}-{curr_date}.jsonl"
        summary = validate_file(main_file)
        report = ValidationReport.create(
            project_name, curr_date, [summary]
        )

    if not report.is_healthy:
        logger.warning(f"Validation issues: {report.invalid_records} invalid records")

    # Step 2: Compare (if previous exists)
    if os.path.exists(f"{prev_date}/processed"):
        with log_duration("Comparison"):
            comparison = compare_runs(
                project_name, prev_date, curr_date,
                f"{prev_date}/processed",
                f"{curr_date}/processed"
            )
            logger.info(f"Changes: +{comparison['added']} -{comparison['removed']}")

    # Step 3: Generate report
    with log_duration("Report generation"):
        generate_report(
            project_name, curr_date, processed_dir,
            validation_report=report
        )

    logger.info("Pipeline complete")
    return report.is_healthy
```

---

## New Unified Report Format

### Combined Report Structure

```python
# shared/validation/unified_report.py

@dataclass
class UnifiedReport:
    """
    Combined validation, comparison, and statistics report.
    """
    project_name: str
    run_date: str
    prev_date: Optional[str] = None

    # Validation
    validation: Optional[ValidationReport] = None

    # Comparison
    comparison: Optional[Dict] = None

    # Statistics
    stats: Optional[Dict] = None

    def save_all(self, output_dir: str):
        """Save all report formats."""
        base = f"{output_dir}/{self.project_name}-{self.run_date}"

        # JSON for programmatic access
        with open(f"{base}_report.json", 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

        # Excel for human review
        self.save_excel(f"{base}_report.xlsx")

        # Summary text for quick check
        with open(f"{base}_summary.txt", 'w') as f:
            f.write(self.to_text())

    def save_excel(self, filepath: str):
        """Save comprehensive Excel report."""
        import pandas as pd

        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Overview
            self._write_overview(writer)

            # Validation details
            if self.validation:
                self._write_validation(writer)

            # Comparison
            if self.comparison:
                self._write_comparison(writer)

            # Statistics
            if self.stats:
                self._write_stats(writer)

    def _write_overview(self, writer):
        pd.DataFrame([{
            "Project": self.project_name,
            "Current Date": self.run_date,
            "Previous Date": self.prev_date or "N/A",
            "Total Records": self.validation.total_records if self.validation else 0,
            "Valid %": f"{self.validation.valid_percentage:.1f}%" if self.validation else "N/A",
            "Status": "PASS" if self.is_healthy else "FAIL"
        }]).to_excel(writer, sheet_name='Overview', index=False)

    @property
    def is_healthy(self) -> bool:
        if self.validation:
            return self.validation.is_healthy
        return True
```

---

## Usage Example

### Complete Pipeline

```python
# Example: audiobee_bcbs_il/run_all.py

import config
from shared.logging import configure_logger, logger
from shared.validation import validate_file, ValidationReport
from output_generator.comparison_creator import compare_runs
from output_generator.report_generator import generate_report

def main():
    configure_logger(config.PROJECT_NAME, log_dir=f"{config.CURR_DATE}/logs")

    # Run scraping phases
    logger.info("Phase 1: Discovery")
    # ... existing index_1 logic ...

    logger.info("Phase 2: Details")
    # ... existing index_2 logic ...

    logger.info("Phase 3: Mapping")
    # ... existing index_3 logic ...

    # QA Pipeline
    logger.info("Running QA pipeline")

    main_file = f"{config.DIRS['processed']}/{config.PROJECT_NAME}-{config.CURR_DATE}.jsonl"

    # Validate
    summary = validate_file(main_file)
    report = ValidationReport.create(
        config.PROJECT_NAME,
        config.CURR_DATE,
        [summary]
    )
    report.print_summary()

    # Compare
    comparison = compare_runs(
        config.PROJECT_NAME,
        config.PREV_DATE,
        config.CURR_DATE,
        config.PREV_DIRS['processed'],
        config.DIRS['processed']
    )

    # Generate final report
    generate_report(
        config.PROJECT_NAME,
        config.CURR_DATE,
        config.DIRS['processed'],
        validation_report=report
    )

    if not report.is_healthy:
        logger.error("QA FAILED - review validation report")
        return 1

    logger.info("All phases complete")
    return 0


if __name__ == "__main__":
    exit(main())
```

---

## Benefits

1. **Consistent Logging**: All output_generator scripts use shared logger
2. **Faster Validation**: Pydantic ~5x faster than jsonschema
3. **Richer Reports**: Validation summary in Excel
4. **Better Debugging**: Structured JSON logs
5. **Backward Compatible**: Existing code unchanged unless opted in

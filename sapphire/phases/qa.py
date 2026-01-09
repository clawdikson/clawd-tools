"""
Phase 4: QA (Quality Assurance) for Sapphire scrapers.

Provides validation and comparison functionality.
"""

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from sapphire.config.schema import SapphireProjectConfig
from sapphire.core.exceptions import ValidationError


@dataclass
class QAResult:
    """Result from QA phase execution."""

    success: bool
    message: str
    data: dict = field(default_factory=dict)

    # Validation results
    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    validation_errors: list[dict] = field(default_factory=list)

    # Comparison results
    added_providers: int = 0
    removed_providers: int = 0
    changed_providers: int = 0


async def run_qa(
    config: SapphireProjectConfig,
    curr_date: str,
    prev_date: Optional[str] = None,
    run_validate: bool = True,
    run_compare: bool = True,
) -> QAResult:
    """Run QA phase for a Sapphire project.

    Args:
        config: Project configuration
        curr_date: Current date string (YYYYMMDD)
        prev_date: Previous date for comparison (optional)
        run_validate: Run schema validation
        run_compare: Run comparison with previous date

    Returns:
        QAResult with validation and comparison results
    """
    try:
        from core.qa import validate, compare
    except ImportError:
        # Fallback if core.qa not available
        return QAResult(
            success=False,
            message="core.qa module not available",
            data={"error": "core.qa import failed"},
        )

    base_dir = Path(config.output.base_dir) if config.output.base_dir else Path(".")
    curr_dir = base_dir / curr_date / "processed"
    input_file = curr_dir / "providers.jsonl"

    result = QAResult(success=True, message="QA completed")

    # Phase 4a: Validation
    if run_validate:
        if not input_file.exists():
            result.success = False
            result.message = f"Input file not found: {input_file}"
            return result

        try:
            validation_result = validate(str(input_file))
            result.total_records = validation_result.metrics.total_records
            result.valid_records = validation_result.metrics.valid_records
            result.invalid_records = validation_result.metrics.invalid_records

            if not validation_result.is_success:
                result.success = False
                result.message = f"Validation failed: {result.invalid_records} invalid records"

            result.data["validation"] = {
                "total_records": result.total_records,
                "valid_records": result.valid_records,
                "invalid_records": result.invalid_records,
            }
        except Exception as e:
            result.success = False
            result.message = f"Validation error: {e}"
            result.data["validation_error"] = str(e)

    # Phase 4b: Comparison
    if run_compare and prev_date:
        prev_dir = base_dir / prev_date / "processed"

        if not prev_dir.exists():
            result.data["comparison_skipped"] = f"Previous directory not found: {prev_dir}"
        else:
            try:
                comparison_result = compare(
                    curr_path=str(curr_dir),
                    prev_path=str(prev_dir),
                )
                result.added_providers = comparison_result.metrics.added
                result.removed_providers = comparison_result.metrics.removed
                result.changed_providers = comparison_result.metrics.changed

                result.data["comparison"] = {
                    "added": result.added_providers,
                    "removed": result.removed_providers,
                    "changed": result.changed_providers,
                }
            except Exception as e:
                result.data["comparison_error"] = str(e)

    return result


def run_qa_sync(
    config: SapphireProjectConfig,
    curr_date: str,
    prev_date: Optional[str] = None,
    run_validate: bool = True,
    run_compare: bool = True,
) -> QAResult:
    """Run QA phase synchronously."""
    return asyncio.run(
        run_qa(
            config=config,
            curr_date=curr_date,
            prev_date=prev_date,
            run_validate=run_validate,
            run_compare=run_compare,
        )
    )

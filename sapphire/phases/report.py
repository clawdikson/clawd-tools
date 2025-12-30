"""
Phase 5: Report generation for Sapphire scrapers.

Provides Excel reports and sample generation.
"""

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from sapphire.config.schema import SapphireProjectConfig


@dataclass
class ReportResult:
    """Result from report phase execution."""

    success: bool
    message: str
    data: dict = field(default_factory=dict)

    # Report outputs
    excel_file: Optional[Path] = None
    sample_file: Optional[Path] = None
    sample_count: int = 0


async def run_report(
    config: SapphireProjectConfig,
    curr_date: str,
    prev_date: Optional[str] = None,
    run_excel: bool = True,
    run_samples: bool = True,
    sample_count: int = 10,
) -> ReportResult:
    """Run report phase for a Sapphire project.

    Args:
        config: Project configuration
        curr_date: Current date string (YYYYMMDD)
        prev_date: Previous date for comparison (optional)
        run_excel: Generate Excel state reports
        run_samples: Generate sample files
        sample_count: Number of samples to generate

    Returns:
        ReportResult with generated file paths
    """
    try:
        from core.qa import report as generate_report, sample as generate_sample
    except ImportError:
        return ReportResult(
            success=False,
            message="core.qa module not available",
            data={"error": "core.qa import failed"},
        )

    base_dir = Path(config.output.base_dir) if config.output.base_dir else Path(".")
    curr_dir = base_dir / curr_date / "processed"
    input_file = curr_dir / "providers.jsonl"

    result = ReportResult(success=True, message="Report generation completed")

    if not input_file.exists():
        result.success = False
        result.message = f"Input file not found: {input_file}"
        return result

    # Phase 5a: Excel Report
    if run_excel:
        try:
            report_result = generate_report(
                project_name=config.project.slug,
                curr_date=curr_date,
                prev_date=prev_date,
            )
            if report_result.is_success:
                result.excel_file = Path(report_result.data.get("excel_file", ""))
                result.data["excel"] = {
                    "file": str(result.excel_file),
                    "states": report_result.data.get("states", []),
                }
        except Exception as e:
            result.data["excel_error"] = str(e)

    # Phase 5b: Sample Generation
    if run_samples:
        try:
            sample_result = generate_sample(
                str(input_file),
                output_dir=str(curr_dir),
                count=sample_count,
                format="jsonl",
            )
            if sample_result.is_success:
                result.sample_file = Path(sample_result.data.get("output_file", ""))
                result.sample_count = sample_result.data.get("sample_count", 0)
                result.data["samples"] = {
                    "file": str(result.sample_file),
                    "count": result.sample_count,
                }
        except Exception as e:
            result.data["sample_error"] = str(e)

    return result


def run_report_sync(
    config: SapphireProjectConfig,
    curr_date: str,
    prev_date: Optional[str] = None,
    run_excel: bool = True,
    run_samples: bool = True,
    sample_count: int = 10,
) -> ReportResult:
    """Run report phase synchronously."""
    return asyncio.run(
        run_report(
            config=config,
            curr_date=curr_date,
            prev_date=prev_date,
            run_excel=run_excel,
            run_samples=run_samples,
            sample_count=sample_count,
        )
    )

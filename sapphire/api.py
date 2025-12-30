"""
Sapphire High-Level API.

Provides programmatic access to Sapphire scrapers.

Usage:
    from sapphire import run_scraper_sync, load_config

    config = load_config("molina")
    result = run_scraper_sync(config, curr_date="20251230")
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from sapphire.config.schema import SapphireProjectConfig, StorageBackend
from sapphire.core.exceptions import SapphireError
from sapphire.core.sapphire_api import SapphireAPI

# Type alias for custom mapper function
MapperFunc = Callable[[dict], dict]


@dataclass
class PhaseResult:
    """Result from a single phase execution."""

    phase: int
    success: bool
    message: str
    data: dict = field(default_factory=dict)
    duration_seconds: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class ScraperResult:
    """Result from a complete scraper run."""

    success: bool
    providers_count: int
    error: Optional[str] = None
    phase_results: dict[int, PhaseResult] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def duration_seconds(self) -> float:
        """Total duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0


async def run_scraper_async(
    config: SapphireProjectConfig,
    curr_date: str,
    prev_date: Optional[str] = None,
    phase: Optional[int] = None,
    mapper: Optional[MapperFunc] = None,
    storage_backend: Optional[StorageBackend] = None,
    validate: bool = False,
    # Phase 4 (QA) flags
    run_qa: bool = False,
    run_validate: bool = False,
    run_compare: bool = False,
    # Phase 5 (Report) flags
    run_report: bool = False,
    run_excel: bool = False,
    run_samples: bool = False,
    sample_count: int = 10,
) -> ScraperResult:
    """Run Sapphire scraper asynchronously.

    Args:
        config: Project configuration
        curr_date: Current date string (YYYYMMDD)
        prev_date: Previous date for comparison (optional)
        phase: Specific phase to run (1-5), or None for phases 1-3
        mapper: Custom mapper function for Phase 3
        storage_backend: Override storage backend from config
        validate: Enable JSON schema validation in Phase 3
        run_qa: Run full QA phase (validation + comparison)
        run_validate: Run schema validation only (Phase 4a)
        run_compare: Run comparison only (Phase 4b)
        run_report: Generate Excel reports and samples
        run_excel: Generate Excel report only (Phase 5a)
        run_samples: Generate samples only (Phase 5b)
        sample_count: Number of samples to generate

    Returns:
        ScraperResult with phase results and provider count
    """
    started_at = datetime.now()
    phase_results: dict[int, PhaseResult] = {}
    providers_count = 0
    error_message: Optional[str] = None

    # Use config storage backend if not overridden
    backend = storage_backend or config.output.storage_backend

    # Determine base output directory
    base_dir = Path(config.output.base_dir) if config.output.base_dir else Path(".")
    output_dir = base_dir / curr_date

    # Determine which phases to run
    if phase is not None:
        phases_to_run = [phase]
    else:
        # Default: run phases 1-3
        phases_to_run = [1, 2, 3]

        # Add Phase 4 if QA flags set
        if run_qa or run_validate or run_compare:
            phases_to_run.append(4)

        # Add Phase 5 if report flags set
        if run_report or run_excel or run_samples:
            phases_to_run.append(5)

    # Create SapphireAPI instance for phases that need it
    # Use first network and empty geo as defaults (request() uses full URLs)
    default_network_id = config.networks[0].id if config.networks else ""
    api = SapphireAPI(config, default_network_id, "")

    try:
        # Phase 1: Discovery
        if 1 in phases_to_run:
            phase_start = datetime.now()
            try:
                # Import here to avoid circular imports
                from sapphire.phases.discovery import run_discovery

                result = await run_discovery(
                    config=config,
                    curr_date=curr_date,
                    api=api,
                )
                phase_results[1] = PhaseResult(
                    phase=1,
                    success=True,
                    message=f"Discovered {result.total_providers} providers",
                    data={
                        "total_providers": result.total_providers,
                        "providers_by_network": result.providers_by_network,
                        "geo_circles_queried": result.geo_circles_queried,
                    },
                    duration_seconds=(datetime.now() - phase_start).total_seconds(),
                    started_at=phase_start,
                    completed_at=datetime.now(),
                )
            except Exception as e:
                phase_results[1] = PhaseResult(
                    phase=1,
                    success=False,
                    message=str(e),
                    duration_seconds=(datetime.now() - phase_start).total_seconds(),
                    started_at=phase_start,
                    completed_at=datetime.now(),
                )
                raise

        # Phase 2: Details
        if 2 in phases_to_run:
            phase_start = datetime.now()
            try:
                from sapphire.phases.details import run_details

                result = await run_details(
                    config=config,
                    curr_date=curr_date,
                )
                phase_results[2] = PhaseResult(
                    phase=2,
                    success=True,
                    message=f"Extracted {result.successful} providers",
                    data={
                        "total_providers": result.total_providers,
                        "successful": result.successful,
                        "failed": result.failed,
                        "skipped_cached": result.skipped_cached,
                    },
                    duration_seconds=(datetime.now() - phase_start).total_seconds(),
                    started_at=phase_start,
                    completed_at=datetime.now(),
                )
            except Exception as e:
                phase_results[2] = PhaseResult(
                    phase=2,
                    success=False,
                    message=str(e),
                    duration_seconds=(datetime.now() - phase_start).total_seconds(),
                    started_at=phase_start,
                    completed_at=datetime.now(),
                )
                raise

        # Phase 3: Normalize
        if 3 in phases_to_run:
            phase_start = datetime.now()
            try:
                from sapphire.phases.normalize import run_normalize, NormalizeConfig

                normalize_config = NormalizeConfig(validate=validate)
                result = await run_normalize(
                    config=config,
                    curr_date=curr_date,
                    mapper=mapper,
                    normalize_config=normalize_config,
                )
                providers_count = result.unique_npis
                phase_results[3] = PhaseResult(
                    phase=3,
                    success=True,
                    message=f"Normalized {result.unique_npis} unique providers",
                    data={
                        "total_records": result.total_records,
                        "unique_npis": result.unique_npis,
                        "duplicates_removed": result.duplicates_removed,
                        "validation_errors": result.validation_errors,
                        "output_file": str(result.output_file),
                    },
                    duration_seconds=(datetime.now() - phase_start).total_seconds(),
                    started_at=phase_start,
                    completed_at=datetime.now(),
                )
            except Exception as e:
                phase_results[3] = PhaseResult(
                    phase=3,
                    success=False,
                    message=str(e),
                    duration_seconds=(datetime.now() - phase_start).total_seconds(),
                    started_at=phase_start,
                    completed_at=datetime.now(),
                )
                raise

        # Phase 4: QA
        if 4 in phases_to_run:
            phase_start = datetime.now()
            try:
                from sapphire.phases.qa import run_qa as run_qa_phase

                result = await run_qa_phase(
                    config=config,
                    curr_date=curr_date,
                    prev_date=prev_date,
                    run_validate=run_validate or run_qa,
                    run_compare=run_compare or run_qa,
                )
                phase_results[4] = PhaseResult(
                    phase=4,
                    success=result.success,
                    message=result.message,
                    data=result.data,
                    duration_seconds=(datetime.now() - phase_start).total_seconds(),
                    started_at=phase_start,
                    completed_at=datetime.now(),
                )
            except Exception as e:
                phase_results[4] = PhaseResult(
                    phase=4,
                    success=False,
                    message=str(e),
                    duration_seconds=(datetime.now() - phase_start).total_seconds(),
                    started_at=phase_start,
                    completed_at=datetime.now(),
                )
                # QA phase failure is not fatal
                pass

        # Phase 5: Report
        if 5 in phases_to_run:
            phase_start = datetime.now()
            try:
                from sapphire.phases.report import run_report as run_report_phase

                result = await run_report_phase(
                    config=config,
                    curr_date=curr_date,
                    prev_date=prev_date,
                    run_excel=run_excel or run_report,
                    run_samples=run_samples or run_report,
                    sample_count=sample_count,
                )
                phase_results[5] = PhaseResult(
                    phase=5,
                    success=result.success,
                    message=result.message,
                    data=result.data,
                    duration_seconds=(datetime.now() - phase_start).total_seconds(),
                    started_at=phase_start,
                    completed_at=datetime.now(),
                )
            except Exception as e:
                phase_results[5] = PhaseResult(
                    phase=5,
                    success=False,
                    message=str(e),
                    duration_seconds=(datetime.now() - phase_start).total_seconds(),
                    started_at=phase_start,
                    completed_at=datetime.now(),
                )
                # Report phase failure is not fatal
                pass

        return ScraperResult(
            success=True,
            providers_count=providers_count,
            phase_results=phase_results,
            started_at=started_at,
            completed_at=datetime.now(),
        )

    except Exception as e:
        error_message = str(e)
        return ScraperResult(
            success=False,
            providers_count=providers_count,
            error=error_message,
            phase_results=phase_results,
            started_at=started_at,
            completed_at=datetime.now(),
        )
    finally:
        await api.close()


def run_scraper_sync(
    config: SapphireProjectConfig,
    curr_date: str,
    prev_date: Optional[str] = None,
    phase: Optional[int] = None,
    mapper: Optional[MapperFunc] = None,
    storage_backend: Optional[StorageBackend] = None,
    validate: bool = False,
    run_qa: bool = False,
    run_validate: bool = False,
    run_compare: bool = False,
    run_report: bool = False,
    run_excel: bool = False,
    run_samples: bool = False,
    sample_count: int = 10,
) -> ScraperResult:
    """Run Sapphire scraper synchronously.

    See run_scraper_async for parameter documentation.
    """
    return asyncio.run(
        run_scraper_async(
            config=config,
            curr_date=curr_date,
            prev_date=prev_date,
            phase=phase,
            mapper=mapper,
            storage_backend=storage_backend,
            validate=validate,
            run_qa=run_qa,
            run_validate=run_validate,
            run_compare=run_compare,
            run_report=run_report,
            run_excel=run_excel,
            run_samples=run_samples,
            sample_count=sample_count,
        )
    )

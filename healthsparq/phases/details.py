"""Phase 2: Provider Detail Extraction module.

Fetches detailed information for providers discovered in Phase 1.
All configuration is injected - no global state.
"""

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import orjson

from healthsparq.config import HealthSparqProjectConfig
from healthsparq.core import FileWriteWorker, HealthSpark, HealthSparkConfig


@dataclass
class DetailsConfig:
    """Configuration for details phase."""

    config: HealthSparqProjectConfig
    curr_date: str
    search_results_dir: Optional[Path] = None
    output_dir: Optional[Path] = None
    max_workers: Optional[int] = None
    dry_run: bool = False

    def __post_init__(self):
        base = Path(self.curr_date)
        if self.search_results_dir is None:
            self.search_results_dir = base / "raw" / "search_results"
        if self.output_dir is None:
            self.output_dir = base / "raw" / "provider_details"
        if self.max_workers is None:
            self.max_workers = self.config.concurrency.max_workers


@dataclass
class DetailsResult:
    """Result of a detail fetch operation."""

    provider_id: str
    plan_code: str
    success: bool
    output_file: Optional[str] = None
    error: Optional[str] = None


def load_provider_ids_from_search(
    search_results_dir: Path,
    plan_code: str,
) -> list[str]:
    """Load unique provider IDs from search results.

    Args:
        search_results_dir: Directory containing search result files
        plan_code: Product code to filter by

    Returns:
        List of unique provider IDs
    """
    provider_ids = set()

    if not search_results_dir.exists():
        return []

    for file_path in search_results_dir.glob(f"{plan_code}_*.json"):
        try:
            with open(file_path, "rb") as f:
                data = orjson.loads(f.read())
            for provider in data.get("providerResults", []):
                if pid := provider.get("providerId"):
                    provider_ids.add(pid)
        except Exception:
            continue

    return list(provider_ids)


async def fetch_provider_detail(
    spark: HealthSpark,
    provider_id: str,
    plan_code: str,
) -> dict[str, Any]:
    """Fetch detailed information for a single provider.

    Args:
        spark: HealthSpark instance
        provider_id: Provider ID to fetch
        plan_code: Product code

    Returns:
        Provider detail dict
    """
    return await spark.get_provider_details(provider_id, plan_code)


async def run_details_for_plan(
    config: HealthSparqProjectConfig,
    plan_code: str,
    provider_ids: list[str],
    output_dir: Path,
    file_writer: FileWriteWorker,
    dry_run: bool = False,
) -> list[DetailsResult]:
    """Run details phase for a single plan.

    Args:
        config: Project configuration
        plan_code: Product code
        provider_ids: List of provider IDs to fetch
        output_dir: Directory for output files
        file_writer: FileWriteWorker instance
        dry_run: If True, don't execute actual fetches

    Returns:
        List of DetailsResult objects
    """
    results: list[DetailsResult] = []

    if dry_run:
        for provider_id in provider_ids:
            results.append(
                DetailsResult(
                    provider_id=provider_id,
                    plan_code=plan_code,
                    success=False,
                    error="dry_run",
                )
            )
        return results

    spark_config = HealthSparkConfig.from_project_config(config, plan_code)

    async with HealthSpark(spark_config) as spark:
        for provider_id in provider_ids:
            try:
                detail = await fetch_provider_detail(spark, provider_id, plan_code)

                output_file = output_dir / f"{plan_code}_{provider_id}.json"
                file_writer.write(output_file, detail)

                results.append(
                    DetailsResult(
                        provider_id=provider_id,
                        plan_code=plan_code,
                        success=True,
                        output_file=str(output_file),
                    )
                )
            except Exception as e:
                results.append(
                    DetailsResult(
                        provider_id=provider_id,
                        plan_code=plan_code,
                        success=False,
                        error=str(e),
                    )
                )

    return results


async def run_details(
    details_config: DetailsConfig,
) -> dict[str, list[DetailsResult]]:
    """Run the details phase for all plans.

    Args:
        details_config: DetailsConfig with project settings

    Returns:
        Dict mapping plan codes to their detail results
    """
    config = details_config.config
    search_dir = Path(details_config.search_results_dir)
    output_dir = Path(details_config.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    all_results: dict[str, list[DetailsResult]] = {}

    with FileWriteWorker() as file_writer:
        for plan in config.plans:
            if not plan.enabled:
                continue

            provider_ids = load_provider_ids_from_search(
                search_dir, plan.product_code
            )

            results = await run_details_for_plan(
                config=config,
                plan_code=plan.product_code,
                provider_ids=provider_ids,
                output_dir=output_dir,
                file_writer=file_writer,
                dry_run=details_config.dry_run,
            )
            all_results[plan.product_code] = results

    return all_results


def run_details_sync(
    config: HealthSparqProjectConfig,
    curr_date: str,
    dry_run: bool = False,
) -> dict[str, list[DetailsResult]]:
    """Synchronous wrapper for run_details.

    Args:
        config: Project configuration
        curr_date: Current date string (YYYYMMDD)
        dry_run: If True, don't execute actual fetches

    Returns:
        Dict mapping plan codes to their detail results
    """
    details_config = DetailsConfig(
        config=config,
        curr_date=curr_date,
        dry_run=dry_run,
    )
    return asyncio.run(run_details(details_config))

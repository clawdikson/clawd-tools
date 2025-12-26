"""Phase 1: Search/Discovery module with adaptive pagination.

Searches HealthSparq provider directories by location with:
- Adaptive pagination based on result count
- Specialty filter drilling for large result sets
- ZIP code fallback when filters are exhausted
- Language filter fallback as last resort

All configuration is injected - no global state.
"""

import asyncio
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from healthsparq.config import HealthSparqProjectConfig
from healthsparq.core import FileWriteWorker, HealthSpark, HealthSparkConfig


@dataclass
class SearchConfig:
    """Configuration for search phase."""

    config: HealthSparqProjectConfig
    curr_date: str
    output_dir: Optional[Path] = None
    max_workers: Optional[int] = None
    dry_run: bool = False
    zip_data_path: Optional[Path] = None

    def __post_init__(self):
        if self.output_dir is None:
            self.output_dir = Path(self.curr_date) / "raw" / "search_results"
        if self.max_workers is None:
            self.max_workers = self.config.concurrency.max_workers
        if self.zip_data_path is None:
            # Look for uszips.xlsx in package data directory
            package_data = Path(__file__).parent.parent / "data" / "uszips.xlsx"
            if package_data.exists():
                self.zip_data_path = package_data
            else:
                self.zip_data_path = Path("uszips.xlsx")


@dataclass
class SearchResult:
    """Result of a search operation."""

    location: str
    plan_code: str
    provider_count: int
    total_results: int
    output_file: Optional[str] = None
    error: Optional[str] = None
    filters_used: list[str] = field(default_factory=list)
    drilling_required: bool = False


@dataclass
class CountySearchResult:
    """Result of searching a county."""

    state: str
    county: str
    plan_code: str
    total_providers_found: int
    searches_performed: int
    filters_drilled: int
    zip_codes_searched: int
    errors: list[str] = field(default_factory=list)


def get_file_name(
    state: str,
    county: str,
    filters: list[str],
    page: int,
    sort: str,
    zip_code: Optional[str] = None,
) -> str:
    """Generate unique filename for search results."""
    parts = [state, f"{county}_County", "_".join(filters) if filters else "all", str(page), sort]
    if zip_code:
        parts.insert(3, zip_code)
    file_name = "-".join(parts).replace(":", "_").replace("/", "_") + ".json"
    return file_name


def get_location_string(state: str, county: str) -> str:
    """Generate location string for county search."""
    # Louisiana uses Parish instead of County
    suffix = "Parish" if state == "LA" else "County"
    return f"{county} {suffix}, {state}"


async def fetch_search_results(
    spark: HealthSpark,
    plan: dict[str, str],
    state: str,
    county: str,
    filters: list[str],
    page: int,
    page_size: int,
    sort: str,
    output_dir: Path,
    file_writer: FileWriteWorker,
    zip_row: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Fetch search results for a specific location/filter combination.

    Args:
        spark: HealthSpark API wrapper
        plan: Plan configuration dict
        state: State code
        county: County name
        filters: Active filter keys
        page: Page number
        page_size: Results per page
        sort: Sort order
        output_dir: Output directory
        file_writer: FileWriteWorker for async writes
        zip_row: Optional ZIP code row for location-specific search

    Returns:
        Search response dict
    """
    # Build location string
    if zip_row is not None:
        full_zip = str(zip_row.get("zip", "")).zfill(5)
        city = zip_row.get("city", "")
        location = f"{city}, {state} {full_zip}"
        location_details = {"zip": full_zip, "locationType": "POSTAL_CODE"}
    else:
        location = get_location_string(state, county)
        location_details = None

    # Generate output file path
    zip_code = str(zip_row.get("zip", "")).zfill(5) if zip_row else None
    file_name = get_file_name(state, county, filters, page, sort, zip_code)
    plan_folder = f"{plan['insurerCode']}_{plan['brandCode']}_{plan['productCode']}"
    output_folder = output_dir / plan_folder
    os.makedirs(output_folder, exist_ok=True)
    file_path = output_folder / file_name

    # Check cache
    if file_path.exists():
        try:
            import orjson
            with open(file_path, "rb") as f:
                data = orjson.loads(f.read())
            if "providerResults" in data:
                return data
        except Exception:
            os.remove(file_path)

    # Fetch from API
    response = await spark.search_with_params(
        location=location,
        page=page,
        page_size=page_size,
        sort=sort,
        filters=filters,
        location_details=location_details,
    )

    # Add metadata and write
    response["_metadata"] = {"output_file_path": str(file_path)}
    file_writer.write(file_path, response)

    return response


async def fetch_filter_results(
    spark: HealthSpark,
    plan: dict[str, str],
    state: str,
    county: str,
    filters: list[str],
    pagination_config: "PaginationConfig",
    output_dir: Path,
    file_writer: FileWriteWorker,
    search_others: bool = False,
) -> tuple[bool, int]:
    """Fetch results with adaptive pagination strategy.

    Uses configurable thresholds to determine when to:
    - Fetch additional pages
    - Switch to reverse sort order
    - Apply extended sort types

    Args:
        spark: HealthSpark API wrapper
        plan: Plan configuration
        state: State code
        county: County name
        filters: Active filters
        pagination_config: Pagination thresholds
        output_dir: Output directory
        file_writer: FileWriteWorker
        search_others: Whether to use extended sort types

    Returns:
        Tuple of (fetch_completed, total_results)
    """
    from healthsparq.config.schema import PaginationConfig

    # Get page/size from config
    page_sizes = pagination_config.page_sizes
    first_page, first_size = page_sizes[0] if page_sizes else (1, 200)
    second_page, second_size = page_sizes[1] if len(page_sizes) > 1 else (3, 100)

    # Fetch first page
    first_response = await fetch_search_results(
        spark, plan, state, county, filters,
        first_page, first_size, "NAME_ASC",
        output_dir, file_writer
    )
    total_results = first_response.get("totalNumberOfResults", 0)

    # Adaptive pagination based on thresholds
    if total_results > pagination_config.threshold_second_page:
        await fetch_search_results(
            spark, plan, state, county, filters,
            second_page, second_size, "NAME_ASC",
            output_dir, file_writer
        )

    if total_results > pagination_config.threshold_reverse_sort:
        await fetch_search_results(
            spark, plan, state, county, filters,
            first_page, first_size, "NAME_DESC",
            output_dir, file_writer
        )

    if total_results > pagination_config.threshold_reverse_second:
        await fetch_search_results(
            spark, plan, state, county, filters,
            second_page, second_size, "NAME_DESC",
            output_dir, file_writer
        )

    # Check if within acceptable limit
    if total_results <= pagination_config.threshold_max_per_filter:
        return True, total_results

    # If search_others is set, try all sort types
    if search_others:
        for sort_type in pagination_config.sort_types:
            if sort_type not in ["NAME_ASC", "NAME_DESC"]:
                await fetch_search_results(
                    spark, plan, state, county, filters,
                    first_page, first_size, sort_type,
                    output_dir, file_writer
                )
                await fetch_search_results(
                    spark, plan, state, county, filters,
                    second_page, second_size, sort_type,
                    output_dir, file_writer
                )

    return False, total_results


async def get_available_filters(
    spark: HealthSpark,
    state: str,
    county: str,
    filters: list[str],
    filter_type: str = "Specialty",
) -> list[dict[str, Any]]:
    """Get available filters for a location.

    Args:
        spark: HealthSpark API wrapper
        state: State code
        county: County name
        filters: Current active filters
        filter_type: Filter category to extract

    Returns:
        List of filter option dicts with 'key' field
    """
    location = get_location_string(state, county)

    try:
        filter_response = await spark.get_search_filters(
            location=location,
            filters=filters,
        )
    except Exception:
        return []

    categories = filter_response.get("categories", [])
    matching = [c for c in categories if c.get("name") == filter_type]

    if not matching:
        return []

    return matching[0].get("filters", [])


async def process_specialty_drilling(
    spark: HealthSpark,
    plan: dict[str, str],
    state: str,
    county: str,
    base_filters: list[str],
    pagination_config: "PaginationConfig",
    output_dir: Path,
    file_writer: FileWriteWorker,
    zip_rows: Optional[list[dict[str, Any]]] = None,
) -> int:
    """Drill down using specialty filters when results exceed threshold.

    Implements the full legacy drilling strategy:
    1. Try specialty filters
    2. If still exceeding threshold, drill by ZIP code with DISTANCE sort
    3. If gaps remain (> 10 providers), try language filters

    Args:
        spark: HealthSpark API wrapper
        plan: Plan configuration
        state: State code
        county: County name
        base_filters: Current filter set
        pagination_config: Pagination config
        output_dir: Output directory
        file_writer: FileWriteWorker
        zip_rows: Optional ZIP code rows for location fallback

    Returns:
        Number of specialty filters processed
    """
    specialty_filters = await get_available_filters(
        spark, state, county, base_filters, "Specialty"
    )

    filters_processed = 0

    for specialty in specialty_filters:
        specialty_key = specialty.get("key", "")
        if not specialty_key:
            continue

        new_filters = base_filters + [specialty_key]
        completed, total = await fetch_filter_results(
            spark, plan, state, county, new_filters,
            pagination_config, output_dir, file_writer
        )
        filters_processed += 1

        # If still too many results, drill down to ZIP codes
        if not completed and zip_rows:
            page_sizes = pagination_config.page_sizes
            for zip_row in zip_rows:
                for page, size in page_sizes:
                    await fetch_search_results(
                        spark, plan, state, county, new_filters,
                        page, size, "DISTANCE",
                        output_dir, file_writer, zip_row
                    )

            # Language filter fallback - try when ZIP drilling may have gaps
            # Legacy behavior: also try NAME_ASC and NAME_DESC for ZIP searches
            # then add language filters if still potentially missing providers
            language_filters = await get_available_filters(
                spark, state, county, new_filters, "Languages Spoken by Provider"
            )

            if language_filters:
                # Try additional sort types for ZIP searches
                for zip_row in zip_rows:
                    for sort_type in ["NAME_ASC", "NAME_DESC"]:
                        for page, size in page_sizes:
                            await fetch_search_results(
                                spark, plan, state, county, new_filters,
                                page, size, sort_type,
                                output_dir, file_writer, zip_row
                            )

                # Try each language filter
                for lang_filter in language_filters:
                    lang_key = lang_filter.get("key", "")
                    if lang_key:
                        await fetch_filter_results(
                            spark, plan, state, county,
                            new_filters + [lang_key],
                            pagination_config, output_dir, file_writer
                        )

    return filters_processed


async def process_county(
    spark: HealthSpark,
    plan: dict[str, str],
    state: str,
    county: str,
    filter_config: "FilterConfig",
    pagination_config: "PaginationConfig",
    output_dir: Path,
    file_writer: FileWriteWorker,
    zip_rows: Optional[list[dict[str, Any]]] = None,
) -> CountySearchResult:
    """Process all providers in a county with adaptive drilling.

    Args:
        spark: HealthSpark API wrapper
        plan: Plan configuration
        state: State code
        county: County name
        filter_config: Filter configuration
        pagination_config: Pagination config
        output_dir: Output directory
        file_writer: FileWriteWorker
        zip_rows: ZIP code rows for this county

    Returns:
        CountySearchResult with statistics
    """
    from healthsparq.config.schema import FilterConfig

    result = CountySearchResult(
        state=state,
        county=county,
        plan_code=plan.get("productCode", ""),
        total_providers_found=0,
        searches_performed=0,
        filters_drilled=0,
        zip_codes_searched=0,
    )

    try:
        # First try without filters
        completed, total = await fetch_filter_results(
            spark, plan, state, county, [],
            pagination_config, output_dir, file_writer
        )
        result.searches_performed += 1
        result.total_providers_found = total

        if completed:
            return result

        # Drill down by organization filter
        for org_filter in filter_config.org_filter_keys:
            org_completed, org_total = await fetch_filter_results(
                spark, plan, state, county, [org_filter],
                pagination_config, output_dir, file_writer
            )
            result.searches_performed += 1

            if org_completed:
                continue

            # For individual provider types, add gender drilling
            if org_filter in filter_config.individual_filter_keys:
                for gender_filter in filter_config.gender_filter_keys:
                    gender_completed, _ = await fetch_filter_results(
                        spark, plan, state, county, [org_filter, gender_filter],
                        pagination_config, output_dir, file_writer,
                        search_others=True
                    )
                    result.searches_performed += 1

                    if not gender_completed:
                        # Drill to specialties with gender
                        drilled = await process_specialty_drilling(
                            spark, plan, state, county,
                            [org_filter, gender_filter],
                            pagination_config, output_dir, file_writer, zip_rows
                        )
                        result.filters_drilled += drilled

                # Also try specialty drilling with just org filter
                drilled = await process_specialty_drilling(
                    spark, plan, state, county, [org_filter],
                    pagination_config, output_dir, file_writer, zip_rows
                )
                result.filters_drilled += drilled
            else:
                # For non-individual types, just specialty drilling
                drilled = await process_specialty_drilling(
                    spark, plan, state, county, [org_filter],
                    pagination_config, output_dir, file_writer, zip_rows
                )
                result.filters_drilled += drilled

    except Exception as e:
        result.errors.append(str(e))

    return result


def load_zip_data(zip_path: Path, states: list[str]) -> dict[str, dict[str, list[dict]]]:
    """Load ZIP code data organized by state and county.

    Args:
        zip_path: Path to uszips.xlsx
        states: List of state codes to load

    Returns:
        Dict of {state: {county: [zip_rows]}}
    """
    if not zip_path.exists():
        return {}

    df = pd.read_excel(zip_path)
    result: dict[str, dict[str, list[dict]]] = {}

    for state in states:
        state_df = df[df["state_id"] == state]
        result[state] = {}
        for county in state_df["county_name"].unique():
            county_df = state_df[state_df["county_name"] == county]
            result[state][county] = county_df.to_dict("records")

    return result


async def run_search_for_plan(
    config: HealthSparqProjectConfig,
    plan_code: str,
    output_dir: Path,
    file_writer: FileWriteWorker,
    zip_data: dict[str, dict[str, list[dict]]],
    dry_run: bool = False,
) -> list[CountySearchResult]:
    """Run search phase for a single plan across all states/counties.

    Args:
        config: Project configuration
        plan_code: Product code to search
        output_dir: Output directory
        file_writer: FileWriteWorker
        zip_data: ZIP code data by state/county
        dry_run: If True, don't execute actual searches

    Returns:
        List of CountySearchResult objects
    """
    results: list[CountySearchResult] = []

    # Find plan config
    plan_config = None
    for p in config.plans:
        if p.product_code == plan_code:
            plan_config = p
            break

    if plan_config is None:
        return results

    # Build plan dict for API calls
    plan = {
        "insurerCode": plan_config.insurer_code or config.site.insurer_code,
        "brandCode": plan_config.brand_code or config.site.brand_code,
        "productCode": plan_code,
    }

    # Determine states to process
    if plan_config.state:
        states = [plan_config.state]
    else:
        states = config.coverage.states

    if dry_run:
        for state in states:
            counties = list(zip_data.get(state, {}).keys())
            for county in counties[:3]:  # Just first 3 for dry run
                results.append(CountySearchResult(
                    state=state,
                    county=county,
                    plan_code=plan_code,
                    total_providers_found=0,
                    searches_performed=0,
                    filters_drilled=0,
                    zip_codes_searched=0,
                    errors=["dry_run"],
                ))
        return results

    # Create HealthSpark instance
    spark_config = HealthSparkConfig.from_project_config(config, plan_code)

    async with HealthSpark(spark_config) as spark:
        for state in states:
            state_counties = zip_data.get(state, {})
            counties = sorted(state_counties.keys())

            for county in counties:
                zip_rows = state_counties.get(county, [])
                county_result = await process_county(
                    spark, plan, state, county,
                    config.filters, config.pagination,
                    output_dir, file_writer, zip_rows
                )
                results.append(county_result)

    return results


async def run_search(
    search_config: SearchConfig,
) -> dict[str, list[CountySearchResult]]:
    """Run the search phase for all plans.

    Args:
        search_config: SearchConfig with project settings

    Returns:
        Dict mapping plan codes to their county search results
    """
    config = search_config.config
    output_dir = Path(search_config.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Load ZIP data
    zip_data = load_zip_data(search_config.zip_data_path, config.coverage.states)

    all_results: dict[str, list[CountySearchResult]] = {}

    with FileWriteWorker() as file_writer:
        for plan in config.plans:
            if not plan.enabled:
                continue

            results = await run_search_for_plan(
                config=config,
                plan_code=plan.product_code,
                output_dir=output_dir,
                file_writer=file_writer,
                zip_data=zip_data,
                dry_run=search_config.dry_run,
            )
            all_results[plan.product_code] = results

    return all_results


def run_search_sync(
    config: HealthSparqProjectConfig,
    curr_date: str,
    dry_run: bool = False,
) -> dict[str, list[CountySearchResult]]:
    """Synchronous wrapper for run_search.

    Args:
        config: Project configuration
        curr_date: Current date string (YYYYMMDD)
        dry_run: If True, don't execute actual searches

    Returns:
        Dict mapping plan codes to their county search results
    """
    search_config = SearchConfig(
        config=config,
        curr_date=curr_date,
        dry_run=dry_run,
    )
    return asyncio.run(run_search(search_config))

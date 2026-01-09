# Sapphire Improvements Implementation Plan

**Created**: 2025-01-07
**Updated**: 2025-01-07 (Oracle review incorporated)
**Status**: Ready for Implementation
**Goal**: Align Sapphire architecture with HealthSparq patterns, add missing features (Recovery phase), and unify shared components

## Executive Summary

Sapphire (ProviderFinderOnline platform library) is missing Phase 6 (Recovery) and has minor inconsistencies with HealthSparq patterns. This plan prioritizes high-impact fixes with minimal code churn.

**Key Decision**: Recovery uses **NPI-based facet search** (not Oracle's "re-discovery widening" suggestion) per user preference.

## Priority Matrix

| Priority | Fix | Effort | Impact |
|----------|-----|--------|--------|
| **P1** | Add Sapphire Phase 6 Recovery | Medium | Critical - enables NPI backfill |
| **P2** | Add `--strict` flag to Sapphire CLI | Quick | Consistency with HealthSparq |
| **P3** | Add `--recovery` flag to Sapphire CLI | Quick | Enables new Phase 6 |
| **P4** | Update phases/__init__.py exports | Quick | Exposes Recovery phase |
| **P5** | Add timing to HealthSparq PhaseResult | Quick | Consistency with Sapphire |
| **P6** | Fix Sapphire unused storage_backend | Quick | Wire parameter properly |
| **P7** | Thin HealthSparq CLI | Short | Remove orchestration duplication |
| **P8** | Deprecate HealthSparq FileWriteWorker | Medium | Use DataStore consistently |

## Oracle Review Findings (2025-01-07)

### Issues Identified
1. **Duplicated orchestration in HealthSparq** - cli.py runs phases directly while api.py also orchestrates
2. **PhaseResult inconsistency** - Sapphire has timing fields, HealthSparq doesn't
3. **Sapphire unused parameters** - storage_backend accepted but not wired
4. **Different storage APIs** - HealthSparq returns DataStore directly; Sapphire uses contextmanager
5. **Missing Sapphire features** - No --strict, --recover, --include-recovered

### Rejected Suggestions
- **"Re-discovery widening" for recovery** - User explicitly prefers NPI-based facet search

---

## P1: Add Sapphire Phase 6 Recovery (CRITICAL)

### Overview
Recovery phase finds providers that exist in previous run but are missing from current run, then attempts to re-fetch them using NPI-based search via the facets API.

### Reference Implementation
File: `audiobee_bcbs_mt/compare_and_download_old_npi_4.py`

### Algorithm
```
1. Load current NPIs from {curr}/processed/{project}-{date}.jsonl
2. Load previous NPIs from {prev}/processed/{project}-{date}.jsonl
3. Find missing: missing_npis = {npi: networks for npi in prev if npi not in curr}
4. For each missing NPI + network:
   a. Query facets API with fulltext=npi, radius=3500, network_id=X
   b. Extract provider_ids from response
   c. Fetch all details (summary, locations, affiliations, networks_accepted)
   d. Update provider_ids_network_map.json
5. Tag recovered files with _missing suffix
```

### Implementation

#### File: `sapphire/phases/recovery.py` (NEW)

```python
"""Phase 6: Recovery module for Sapphire.

Recovers missing providers by comparing current and previous runs,
then re-fetching providers via NPI-based facet search.
"""

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import orjson
from tqdm import tqdm

from sapphire.config.schema import SapphireProjectConfig, StorageBackend
from sapphire.core.sapphire_api import SapphireAPI

try:
    from core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from core.io.base import DataStore


@dataclass
class MissingProvider:
    """A provider missing from current run."""
    npi: str
    networks: list[dict[str, Any]]  # [{id: X, name: Y}, ...]
    
    @property
    def network_ids(self) -> list[str]:
        """Get network IDs for this provider."""
        ids = []
        for net in self.networks:
            if "id" in net:
                ids.append(str(net["id"]))
            elif "network_id" in net:
                ids.append(str(net["network_id"]))
        return ids


@dataclass
class RecoveryConfig:
    """Configuration for recovery phase."""
    config: SapphireProjectConfig
    curr_date: str
    prev_date: str
    output_dir: Path | None = None
    max_concurrent: int = 5
    batch_size: int = 50
    dry_run: bool = False
    search_radius: int = 3500  # Wide radius for NPI search
    storage_backend: StorageBackend | None = None

    def __post_init__(self):
        if self.output_dir is None:
            if self.config.output.base_dir:
                self.output_dir = Path(self.config.output.base_dir)
            else:
                self.output_dir = Path(".")
        if self.storage_backend is None:
            self.storage_backend = self.config.output.storage_backend


@dataclass
class RecoveryResult:
    """Result from a single provider recovery attempt."""
    npi: str
    network_id: str
    success: bool
    provider_ids: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass 
class RecoveryPhaseResult:
    """Result of recovery phase execution."""
    success: bool
    message: str
    missing_count: int = 0
    searched_count: int = 0
    recovered_count: int = 0
    failed_count: int = 0
    data: dict[str, Any] = field(default_factory=dict)


def load_npis_from_jsonl(file_path: Path) -> dict[str, list[dict]]:
    """Load NPIs and their network data from JSONL file.
    
    Returns:
        Dict mapping NPI to list of network dicts
    """
    npis: dict[str, list[dict]] = {}
    if not file_path.exists():
        return npis
    
    with open(file_path, "rb") as f:
        for line in f:
            try:
                record = orjson.loads(line)
                provider = record.get("provider", {})
                npi = provider.get("npi")
                if npi:
                    networks = record.get("networks", [])
                    npis[npi] = networks
            except (orjson.JSONDecodeError, KeyError):
                continue
    return npis


def find_missing_providers(
    curr_file: Path,
    prev_file: Path,
) -> list[MissingProvider]:
    """Find providers in previous that are missing from current.
    
    Args:
        curr_file: Current run's processed JSONL
        prev_file: Previous run's processed JSONL
        
    Returns:
        List of MissingProvider objects
    """
    curr_npis = set(load_npis_from_jsonl(curr_file).keys())
    prev_data = load_npis_from_jsonl(prev_file)
    
    missing = []
    for npi, networks in prev_data.items():
        if npi not in curr_npis:
            missing.append(MissingProvider(npi=npi, networks=networks))
    
    return missing


async def search_npi_via_facets(
    api: SapphireAPI,
    npi: str,
    network_id: str,
    geo_location: str,
    radius: int = 3500,
) -> list[str]:
    """Search for provider IDs by NPI using facets API.
    
    Args:
        api: SapphireAPI instance
        npi: NPI to search for
        network_id: Network ID to search within
        geo_location: Geo coordinates string
        radius: Search radius in miles (default 3500 = nationwide)
        
    Returns:
        List of provider_ids found
    """
    params = {
        "fulltext": str(npi),
        "network_id": network_id,
        "geo_location": geo_location,
        "radius": str(radius),
        "page": "1",
        "sort": "distance asc",
        "facet[provider_id[value]]": "true",
        "facet[provider_id[limit]]": "-1",
    }
    
    try:
        response = await api.facets(**params)
        if not isinstance(response, dict):
            return []
        
        provider_ids = []
        facets_provider_ids = response.get("facets", {}).get("provider_id", [])
        
        if isinstance(facets_provider_ids, list):
            for item in facets_provider_ids:
                if isinstance(item, dict):
                    val = item.get("value") or item.get("id") or item.get("provider_id")
                    if val is not None:
                        provider_ids.append(str(val))
                elif item is not None:
                    provider_ids.append(str(item))
        
        return sorted(set(provider_ids))
    except Exception as e:
        logger.warning(f"Facet search failed for NPI {npi}, network {network_id}: {e}")
        return []


async def fetch_provider_details(
    api: SapphireAPI,
    provider_id: str,
    network_id: str,
    geo_location: str,
) -> dict[str, Any] | None:
    """Fetch all detail endpoints for a provider.
    
    Args:
        api: SapphireAPI instance
        provider_id: Provider ID to fetch
        network_id: Network ID context
        geo_location: Geo coordinates string
        
    Returns:
        Combined provider data dict or None on failure
    """
    try:
        # Fetch summary (primary endpoint)
        summary = await api.summary(
            provider_id=provider_id,
            network_id=network_id,
            geo_location=geo_location,
        )
        
        if not isinstance(summary, dict) or "providers" not in summary:
            return None
        
        # Extract location_id for additional endpoints
        providers = summary.get("providers", [])
        if not providers:
            return None
        
        provider_data = providers[0]
        location_id = provider_data.get("location_id")
        
        result = {"summary": summary}
        
        if location_id:
            # Fetch additional endpoints in parallel
            locations_task = api.locations(
                provider_id=provider_id,
                location_id=str(location_id),
            )
            affiliations_task = api.affiliations(
                provider_id=provider_id,
                location_id=str(location_id),
            )
            networks_task = api.networks_accepted(
                provider_id=provider_id,
                location_id=str(location_id),
            )
            
            locations, affiliations, networks_accepted = await asyncio.gather(
                locations_task, affiliations_task, networks_task,
                return_exceptions=True,
            )
            
            if isinstance(locations, dict):
                result["locations"] = locations
            if isinstance(affiliations, dict):
                result["affiliations"] = affiliations
            if isinstance(networks_accepted, dict):
                result["networks_accepted"] = networks_accepted
        
        return result
        
    except Exception as e:
        logger.warning(f"Failed to fetch details for provider {provider_id}: {e}")
        return None


async def recover_provider(
    api: SapphireAPI,
    provider: MissingProvider,
    geo_location: str,
    output_dir: Path,
    search_radius: int = 3500,
) -> list[RecoveryResult]:
    """Attempt to recover a single missing provider across all its networks.
    
    Args:
        api: SapphireAPI instance
        provider: MissingProvider to recover
        geo_location: Geo coordinates for search
        output_dir: Directory for output files
        search_radius: Search radius in miles
        
    Returns:
        List of RecoveryResult for each network attempted
    """
    results = []
    
    for network_id in provider.network_ids:
        try:
            # Search for provider IDs by NPI
            provider_ids = await search_npi_via_facets(
                api=api,
                npi=provider.npi,
                network_id=network_id,
                geo_location=geo_location,
                radius=search_radius,
            )
            
            if not provider_ids:
                results.append(RecoveryResult(
                    npi=provider.npi,
                    network_id=network_id,
                    success=False,
                    error="No provider IDs found via facet search",
                ))
                continue
            
            # Save search results
            search_output = output_dir / "search_results" / f"{network_id}_{provider.npi}.json"
            search_output.parent.mkdir(parents=True, exist_ok=True)
            
            search_data = {
                "npi": provider.npi,
                "network_id": network_id,
                "provider_ids": provider_ids,
            }
            with open(search_output, "wb") as f:
                f.write(orjson.dumps(search_data))
            
            # Fetch details for each provider_id
            for pid in provider_ids:
                details = await fetch_provider_details(
                    api=api,
                    provider_id=pid,
                    network_id=network_id,
                    geo_location=geo_location,
                )
                
                if details:
                    # Save with _missing tag
                    detail_output = output_dir / "provider_details" / f"{pid}_missing.json"
                    detail_output.parent.mkdir(parents=True, exist_ok=True)
                    with open(detail_output, "wb") as f:
                        f.write(orjson.dumps(details))
            
            results.append(RecoveryResult(
                npi=provider.npi,
                network_id=network_id,
                success=True,
                provider_ids=provider_ids,
            ))
            
        except Exception as e:
            results.append(RecoveryResult(
                npi=provider.npi,
                network_id=network_id,
                success=False,
                error=str(e),
            ))
    
    return results


async def run_recovery(recovery_config: RecoveryConfig) -> RecoveryPhaseResult:
    """Run the recovery phase.
    
    Args:
        recovery_config: RecoveryConfig with settings
        
    Returns:
        RecoveryPhaseResult with recovery statistics
    """
    config = recovery_config.config
    curr_date = recovery_config.curr_date
    prev_date = recovery_config.prev_date
    output_dir = recovery_config.output_dir
    
    logger.info("=" * 70)
    logger.info("RECOVERY PHASE STARTED")
    logger.info("=" * 70)
    logger.info(f"Current date: {curr_date}")
    logger.info(f"Previous date: {prev_date}")
    
    # Get file paths
    project_slug = config.project.slug
    curr_file = (
        output_dir / curr_date / config.output.processed_subdir
        / f"{project_slug}-{curr_date}.jsonl"
    )
    prev_file = (
        output_dir / prev_date / config.output.processed_subdir
        / f"{project_slug}-{prev_date}.jsonl"
    )
    
    if not curr_file.exists():
        return RecoveryPhaseResult(
            success=False,
            message=f"Current file not found: {curr_file}",
        )
    
    if not prev_file.exists():
        return RecoveryPhaseResult(
            success=False,
            message=f"Previous file not found: {prev_file}",
        )
    
    # Find missing providers
    missing = find_missing_providers(curr_file, prev_file)
    logger.info(f"Found {len(missing)} missing providers")
    
    if not missing:
        return RecoveryPhaseResult(
            success=True,
            message="No missing providers to recover",
            missing_count=0,
        )
    
    if recovery_config.dry_run:
        return RecoveryPhaseResult(
            success=True,
            message=f"Dry run: would recover {len(missing)} providers",
            missing_count=len(missing),
        )
    
    # Create output directory for recovered data
    recovered_dir = output_dir / curr_date / config.output.raw_subdir / "recovered"
    recovered_dir.mkdir(parents=True, exist_ok=True)
    
    # Get geo location from config (use first geo code or default)
    geo_location = "39.8283,-98.5795"  # Default: geographic center of US
    if config.geo_codes:
        first_geo = config.geo_codes[0]
        geo_location = f"{first_geo.lat},{first_geo.lng}"
    
    # Initialize API
    default_network_id = config.networks[0].id if config.networks else ""
    api = SapphireAPI(config, default_network_id, geo_location)
    
    results: list[RecoveryResult] = []
    
    try:
        semaphore = asyncio.Semaphore(recovery_config.max_concurrent)
        
        async def bounded_recover(provider: MissingProvider):
            async with semaphore:
                return await recover_provider(
                    api=api,
                    provider=provider,
                    geo_location=geo_location,
                    output_dir=recovered_dir,
                    search_radius=recovery_config.search_radius,
                )
        
        # Process in batches with progress bar
        batch_size = recovery_config.batch_size
        with tqdm(
            total=len(missing),
            desc="Phase 6: Recovery",
            unit="provider",
            leave=True,
        ) as pbar:
            for i in range(0, len(missing), batch_size):
                batch = missing[i:i + batch_size]
                batch_tasks = [bounded_recover(p) for p in batch]
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, list):
                        results.extend(result)
                    elif isinstance(result, Exception):
                        logger.warning(f"Recovery batch error: {result}")
                    pbar.update(1)
    
    finally:
        await api.close()
    
    # Update provider_ids_network_map.json with recovered provider IDs
    provider_map_path = output_dir / curr_date / config.output.raw_subdir / "provider_ids_network_map.json"
    provider_network_map: dict[str, list[str]] = {}
    
    if provider_map_path.exists():
        with open(provider_map_path, "rb") as f:
            provider_network_map = orjson.loads(f.read())
    
    for result in results:
        if result.success:
            for pid in result.provider_ids:
                if pid not in provider_network_map:
                    provider_network_map[pid] = []
                if result.network_id not in provider_network_map[pid]:
                    provider_network_map[pid].append(result.network_id)
    
    with open(provider_map_path, "wb") as f:
        f.write(orjson.dumps(provider_network_map))
    
    # Calculate statistics
    recovered = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    
    logger.info("=" * 70)
    logger.info(f"RECOVERY PHASE COMPLETED: {recovered} recovered, {failed} failed")
    logger.info("=" * 70)
    
    return RecoveryPhaseResult(
        success=True,
        message=f"Recovery complete: {recovered}/{len(results)} network searches successful",
        missing_count=len(missing),
        searched_count=len(results),
        recovered_count=recovered,
        failed_count=failed,
        data={
            "recovered_dir": str(recovered_dir),
            "provider_map_updated": str(provider_map_path),
        },
    )


def run_recovery_sync(
    config: SapphireProjectConfig,
    curr_date: str,
    prev_date: str,
    output_dir: Path | None = None,
    dry_run: bool = False,
    storage_backend: StorageBackend | None = None,
) -> RecoveryPhaseResult:
    """Synchronous wrapper for run_recovery.
    
    Args:
        config: Project configuration
        curr_date: Current date string (YYYYMMDD)
        prev_date: Previous date string (YYYYMMDD)
        output_dir: Output directory (optional)
        dry_run: If True, show what would be done without executing
        storage_backend: Override storage backend (default: from config)
        
    Returns:
        RecoveryPhaseResult with recovery statistics
    """
    recovery_config = RecoveryConfig(
        config=config,
        curr_date=curr_date,
        prev_date=prev_date,
        output_dir=output_dir,
        dry_run=dry_run,
        storage_backend=storage_backend,
    )
    return asyncio.run(run_recovery(recovery_config))
```

### Required Changes

#### 1. Update `sapphire/core/sapphire_api.py`

Add missing API methods if not present:

```python
async def facets(self, **params) -> dict:
    """Query facets endpoint."""
    url = self._build_url("facets", params)
    return await self.request(url)

async def summary(self, provider_id: str, network_id: str, geo_location: str) -> dict:
    """Get provider summary."""
    params = {
        "provider_id": provider_id,
        "network_id": network_id,
        "geo_location": geo_location,
    }
    url = self._build_url("summary", params)
    return await self.request(url)

async def locations(self, provider_id: str, location_id: str) -> dict:
    """Get provider locations."""
    params = {"provider_id": provider_id, "location_id": location_id}
    url = self._build_url("locations", params)
    return await self.request(url)

async def affiliations(self, provider_id: str, location_id: str) -> dict:
    """Get provider affiliations."""
    params = {"provider_id": provider_id, "location_id": location_id}
    url = self._build_url("affiliations", params)
    return await self.request(url)

async def networks_accepted(self, provider_id: str, location_id: str) -> dict:
    """Get networks accepted by provider."""
    params = {"provider_id": provider_id, "location_id": location_id}
    url = self._build_url("networks_accepted", params)
    return await self.request(url)
```

#### 2. Update `sapphire/phases/__init__.py`

```python
"""Sapphire pipeline phases.

Phase 1 (Discovery): Geographic provider ID discovery via facet queries
Phase 2 (Details): Provider detail extraction (summary, locations, affiliations, networks)
Phase 3 (Normalize): Normalization with mapper injection, NPI deduplication
Phase 4 (QA): Schema validation + comparison with previous run
Phase 5 (Report): Excel reports + sample generation
Phase 6 (Recovery): Missing provider recovery via NPI-based facet search
"""

# ... existing imports ...

from sapphire.phases.recovery import (
    RecoveryConfig,
    RecoveryPhaseResult,
    MissingProvider,
    run_recovery,
    run_recovery_sync,
    find_missing_providers,
)

__all__ = [
    # ... existing exports ...
    # Phase 6: Recovery
    "RecoveryConfig",
    "RecoveryPhaseResult",
    "MissingProvider",
    "run_recovery",
    "run_recovery_sync",
    "find_missing_providers",
]
```

---

## P2: Add `--strict` Flag to Sapphire CLI

### Purpose
Match HealthSparq CLI behavior for strict validation mode.

### Change: `sapphire/cli.py`

```python
@app.command()
def run(
    # ... existing params ...
    strict: bool = typer.Option(
        False, "--strict", help="Enable strict validation (fail on warnings)"
    ),
) -> None:
```

Pass to `run_scraper_sync`:
```python
result = run_scraper_sync(
    # ... existing params ...
    strict=strict,
)
```

### Change: `sapphire/api.py`

Add `strict` parameter to `run_scraper_async` and `run_scraper_sync`:

```python
async def run_scraper_async(
    # ... existing params ...
    strict: bool = False,
) -> ScraperResult:
```

---

## P3: Add `--recovery` Flag to Sapphire CLI

### Purpose
Enable Phase 6 Recovery from CLI.

### Change: `sapphire/cli.py`

```python
@app.command()
def run(
    # ... existing params ...
    recovery: bool = typer.Option(
        False, "--recovery", "-r", help="Run recovery phase (requires --prev)"
    ),
) -> None:
    # ... existing validation ...
    
    # Validate recovery requires prev
    if recovery and not prev:
        typer.echo("Error: --recovery requires --prev", err=True)
        raise typer.Exit(2)
```

Pass to `run_scraper_sync`:
```python
result = run_scraper_sync(
    # ... existing params ...
    run_recovery=recovery,
)
```

### Change: `sapphire/api.py`

Add Phase 6 handling:

```python
async def run_scraper_async(
    # ... existing params ...
    run_recovery: bool = False,
) -> ScraperResult:
    # ... existing code ...
    
    # Determine which phases to run
    if phase is not None:
        phases_to_run = [phase]
    else:
        phases_to_run = [1, 2, 3]
        # ... existing phase 4/5 logic ...
        
        # Add Phase 6 if recovery flag set
        if run_recovery:
            if not prev_date:
                raise ValueError("Recovery phase requires prev_date")
            phases_to_run.append(6)
    
    # ... existing phase 1-5 code ...
    
    # Phase 6: Recovery
    if 6 in phases_to_run:
        phase_start = datetime.now()
        try:
            from sapphire.phases.recovery import RecoveryConfig, run_recovery as run_recovery_phase
            
            recovery_config = RecoveryConfig(
                config=config,
                curr_date=curr_date,
                prev_date=prev_date,
            )
            result = await run_recovery_phase(recovery_config)
            phase_results[6] = PhaseResult(
                phase=6,
                success=result.success,
                message=result.message,
                data={
                    "missing_count": result.missing_count,
                    "recovered_count": result.recovered_count,
                    "failed_count": result.failed_count,
                },
                duration_seconds=(datetime.now() - phase_start).total_seconds(),
                started_at=phase_start,
                completed_at=datetime.now(),
            )
        except Exception as e:
            phase_results[6] = PhaseResult(
                phase=6,
                success=False,
                message=str(e),
                duration_seconds=(datetime.now() - phase_start).total_seconds(),
                started_at=phase_start,
                completed_at=datetime.now(),
            )
            # Recovery failure is not fatal
            pass
```

---

## Implementation Order

1. **Create `sapphire/phases/recovery.py`** - New file with recovery logic
2. **Update `sapphire/core/sapphire_api.py`** - Add missing API methods (if needed)
3. **Update `sapphire/phases/__init__.py`** - Export recovery module
4. **Update `sapphire/api.py`** - Add Phase 6 handling and `run_recovery` param
5. **Update `sapphire/cli.py`** - Add `--recovery` and `--strict` flags
6. **Add tests** - `sapphire/tests/test_recovery.py`

---

## Testing Checklist

- [ ] Unit test: `find_missing_providers()` correctly identifies missing NPIs
- [ ] Unit test: `search_npi_via_facets()` parses facet response correctly
- [ ] Unit test: `fetch_provider_details()` combines all endpoints
- [ ] Integration test: Full recovery flow with mock API
- [ ] CLI test: `--recovery` requires `--prev`
- [ ] CLI test: `--strict` flag passes through

---

## Rollback Plan

All changes are additive (new file + minor edits). Rollback:
1. Delete `sapphire/phases/recovery.py`
2. Revert changes to `__init__.py`, `api.py`, `cli.py`

---

## Dependencies

- No new external dependencies required
- Uses existing: `orjson`, `tqdm`, `asyncio`

---

## Estimated Effort

| Task | Time |
|------|------|
| Create recovery.py | 2-3 hours |
| Update sapphire_api.py | 30 min |
| Update __init__.py | 10 min |
| Update api.py | 30 min |
| Update cli.py | 20 min |
| Write tests | 1-2 hours |
| **Total** | **4-6 hours** |

---

## P5: Add Timing to HealthSparq PhaseResult (QUICK)

### Problem
Sapphire's `PhaseResult` has `duration_seconds`, `started_at`, `completed_at` fields, but HealthSparq's doesn't.

### Current State

**Sapphire** (`sapphire/api.py:27`):
```python
@dataclass
class PhaseResult:
    phase: int
    success: bool
    message: str
    data: dict = field(default_factory=dict)
    duration_seconds: float = 0.0        # <-- Has timing
    started_at: datetime | None = None   # <-- Has timing
    completed_at: datetime | None = None # <-- Has timing
```

**HealthSparq** (`healthsparq/api.py:25`):
```python
@dataclass
class PhaseResult:
    phase: int
    success: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    # No timing fields!
```

### Change: `healthsparq/api.py`

```python
from datetime import datetime

@dataclass
class PhaseResult:
    """Result from a single phase execution."""
    phase: int
    success: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0
    started_at: datetime | None = None
    completed_at: datetime | None = None
```

Then update each phase block to capture timing:
```python
# Phase 1: Search
if phase is None or phase == 1:
    phase_start = datetime.now()
    try:
        results = run_search_sync(...)
        phase_results[1] = PhaseResult(
            phase=1,
            success=True,
            message=f"Search complete: {total_providers} providers found",
            data={"total_providers": total_providers},
            duration_seconds=(datetime.now() - phase_start).total_seconds(),
            started_at=phase_start,
            completed_at=datetime.now(),
        )
    except Exception as e:
        phase_results[1] = PhaseResult(
            phase=1,
            success=False,
            message=f"Search failed: {e}",
            duration_seconds=(datetime.now() - phase_start).total_seconds(),
            started_at=phase_start,
            completed_at=datetime.now(),
        )
```

---

## P6: Fix Sapphire Unused storage_backend Parameter (QUICK)

### Problem
`sapphire/api.py` accepts `storage_backend` parameter but doesn't use it (line 64, 102-106):

```python
async def run_scraper_async(
    ...
    storage_backend: StorageBackend | None = None,  # Accepted
    ...
):
    # Use config storage backend if not overridden
    # <-- Comment says it should be used, but it's not!
    
    base_dir = Path(config.output.base_dir) if config.output.base_dir else Path(".")
    base_dir / curr_date  # This line does nothing! Computed but not assigned
```

### Change: `sapphire/api.py`

```python
async def run_scraper_async(
    ...
    storage_backend: StorageBackend | None = None,
    ...
):
    # Use config storage backend if not overridden
    effective_backend = storage_backend or config.output.storage_backend
    
    # Pass to phases that support it
    # (Most phases already accept storage_backend parameter)
```

---

## P7: Thin HealthSparq CLI (SHORT)

### Problem
HealthSparq CLI (`healthsparq/cli.py`) has some direct phase execution code instead of fully delegating to `api.py`. This creates drift risk.

### Current State
HealthSparq CLI already delegates to `run_scraper_sync()` in api.py (good!), but we should verify no redundant orchestration exists.

### Action
Review `healthsparq/cli.py` and ensure ALL phase execution goes through `api.py`. The CLI should only:
1. Parse arguments
2. Load config
3. Call `run_scraper_sync()`
4. Display results

**Note**: After review, HealthSparq CLI appears to already follow this pattern correctly. This item may be a false positive from Oracle.

---

## P8: Deprecate HealthSparq FileWriteWorker (MEDIUM - DEFERRED)

### Problem
HealthSparq uses `FileWriteWorker` for some file operations instead of `DataStore` consistently.

### Current Usage
- `healthsparq/phases/recovery.py:251` - Uses `FileWriteWorker` as fallback
- `healthsparq/core/__init__.py` - Exports `FileWriteWorker`

### Recommendation
**Defer this change** - FileWriteWorker provides async file writing which DataStore doesn't have. The current hybrid approach (DataStore for structured data, FileWriteWorker for raw output) may be intentional.

### Future Action
If consolidation is desired:
1. Add async write support to DataStore
2. Migrate FileWriteWorker usages
3. Deprecate FileWriteWorker

---

## Updated Implementation Order

### Phase A: Sapphire Core (P1-P4)
1. Create `sapphire/phases/recovery.py` (P1)
2. Update `sapphire/core/sapphire_api.py` - Add missing API methods (P1)
3. Update `sapphire/phases/__init__.py` - Export recovery (P4)
4. Update `sapphire/api.py` - Add Phase 6 + fix storage_backend (P1, P6)
5. Update `sapphire/cli.py` - Add --recovery and --strict flags (P2, P3)

### Phase B: HealthSparq Alignment (P5, P7)
6. Update `healthsparq/api.py` - Add timing to PhaseResult (P5)
7. Verify HealthSparq CLI delegation (P7)

### Phase C: Tests
8. Add `sapphire/tests/test_recovery.py`
9. Add timing tests for HealthSparq

### Phase D: Deferred (P8)
10. FileWriteWorker deprecation (future)

---

## Updated Effort Estimate

| Task | Time | Priority |
|------|------|----------|
| Create sapphire/phases/recovery.py | 2-3 hours | P1 |
| Update sapphire/core/sapphire_api.py | 30 min | P1 |
| Update sapphire/phases/__init__.py | 10 min | P4 |
| Update sapphire/api.py (Phase 6 + storage fix) | 45 min | P1, P6 |
| Update sapphire/cli.py (--recovery, --strict) | 30 min | P2, P3 |
| Update healthsparq/api.py (timing) | 30 min | P5 |
| Verify healthsparq/cli.py | 15 min | P7 |
| Write tests | 1-2 hours | - |
| **Total** | **6-8 hours** | - |

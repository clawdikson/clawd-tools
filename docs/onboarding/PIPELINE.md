# Pipeline Architecture Deep Dive

> **Complete Reference for Scraper Execution Phases and Data Flow**

## Overview

Every scraper project follows a standardized pipeline architecture consisting of 3-4 sequential phases. This document provides exhaustive detail on each phase, including code patterns, data formats, and execution strategies.

---

## Pipeline Phases Summary

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           PIPELINE EXECUTION FLOW                                 │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │  Phase 0    │    │  Phase 1    │    │  Phase 2    │    │  Phase 3    │        │
│  │  (Setup)    │───▶│ (Discovery) │───▶│ (Extract)   │───▶│ (Normalize) │        │
│  │  Optional   │    │  Required   │    │  Required   │    │  Required   │        │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘        │
│        │                  │                  │                  │                 │
│        ▼                  ▼                  ▼                  ▼                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │ provider_   │    │  search_    │    │ provider_   │    │  project-   │        │
│  │ ids.json    │    │  results/   │    │ details/    │    │ YYYYMMDD    │        │
│  │             │    │  *.json     │    │  *.json     │    │ .jsonl      │        │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘        │
│                                                                                   │
│  ──────────────────────────────────────────────────────────────────────────────  │
│                                                                                   │
│                           QA PHASES (Post-Processing)                            │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │  Compare    │    │  Type       │    │  Sample     │    │  Report     │        │
│  │  Old NPI    │───▶│  Check      │───▶│  Generate   │───▶│  Generate   │        │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘        │
│        │                  │                  │                  │                 │
│        ▼                  ▼                  ▼                  ▼                 │
│  [NPI Recovery]    [Schema Valid]    [10 Samples]       [Excel Report]          │
│                                                                                   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 0: Setup & ID Discovery (Optional)

**Purpose**: Pre-fetch provider IDs or set up search parameters before main discovery.

### When Used
- Sapphire projects with faceted search endpoints
- Projects requiring network-to-provider mapping
- Large datasets where upfront ID discovery is more efficient

### Implementation Pattern

```python
# index_0.py - Typical Structure

import os
import orjson
import config
from pathlib import Path

def main():
    """
    Phase 0: Discover all provider IDs via faceted search.

    This phase queries the API for all provider IDs within each network,
    creating a comprehensive mapping for subsequent phases.
    """

    # Prepare output directory
    os.makedirs(config.DIRS["raw"], exist_ok=True)

    # Load network definitions
    with open("data/networks.json", "r") as f:
        networks = orjson.loads(f.read())["networks"]

    provider_id_map = {}  # {provider_id: [network_names]}

    for network in tqdm(networks, desc="Fetching networks"):
        # Query faceted endpoint with unlimited provider ID limit
        params = {
            **config.COMMON_PARAMS,
            "network_id": network["id"],
            "facet[provider_id[limit]]": "-1",  # Get ALL IDs
        }

        response = httpx.get(config.BASE_URLS["facets"], params=params)
        facets = response.json()

        # Extract provider IDs from facet response
        for facet in facets.get("facets", {}).get("provider_id", []):
            pid = str(facet["value"])
            if pid not in provider_id_map:
                provider_id_map[pid] = []
            provider_id_map[pid].append(network["name"])

    # Write consolidated mapping
    output_path = Path(config.DIRS["raw"]) / "all_provider_ids.json"
    with open(output_path, "wb") as f:
        f.write(orjson.dumps(provider_id_map))

    print(f"Discovered {len(provider_id_map)} unique provider IDs")

if __name__ == "__main__":
    main()
```

### Output Format

```json
{
  "f1000637491": ["PPO Network", "HMO Network"],
  "f1000637492": ["PPO Network"],
  "f1000637493": ["Medicare Advantage", "HMO Network"]
}
```

### Projects Using Phase 0
- `audiobee_bcbs_il` (Sapphire)
- `audiobee_multiplan` (Carrier)
- `audiobee_molina` (Sapphire)
- `audiobee_uhc_medicaid` (Werally)

---

## Phase 1: Discovery/Search

**Purpose**: Execute paginated searches to identify all provider IDs and their locations.

### Core Responsibilities
1. Load search parameters (ZIP codes, specialties, networks)
2. Execute paginated searches across all parameter combinations
3. Cache raw API responses to disk
4. Extract unique provider/location IDs for Phase 2

### Implementation Patterns by Site Type

#### Pattern A: Healthsparq (Browser + County Grid)

```python
# index_1.py - Healthsparq Pattern

import os
import config
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

class HealthsparqSearcher:
    """
    County-by-county search with progressive filter narrowing.

    When results exceed 600 (API limit), recursively applies filters:
    1. Organization type (FAC, GRP, OTHR, SUP, PHARM, DNTL)
    2. Gender (M, F, U)
    3. Specialty (recursive expansion)
    """

    MAX_RESULTS = 600
    SORT_TYPES = ["BEST_MATCH", "DISTANCE", "NAME_ASC", "NAME_DESC"]

    def __init__(self, healthspark_client):
        self.client = healthspark_client
        self.results_dir = config.DIRS["search_results"]
        os.makedirs(self.results_dir, exist_ok=True)

    def search_county(self, county: str, filters: list = None) -> list:
        """
        Search a single county with optional filters.
        Returns list of provider IDs discovered.
        """
        filters = filters or []
        all_ids = set()

        for sort_type in self.SORT_TYPES:
            for page in [1, 3]:  # Capture beginning and middle of results
                results = self.client.search(
                    county=county,
                    filters=filters,
                    sort=sort_type,
                    page=page,
                    limit=200 if page == 1 else 100
                )

                # Cache results
                filename = f"{county}-{page}-{sort_type}.json"
                self._save_results(filename, results)

                # Check if we need to narrow search
                if results.get("totalCount", 0) > self.MAX_RESULTS:
                    # Recursively narrow with additional filters
                    for narrow_filter in config.ORG_FILTERS:
                        sub_ids = self.search_county(
                            county,
                            filters + [narrow_filter]
                        )
                        all_ids.update(sub_ids)
                else:
                    # Extract provider IDs
                    for provider in results.get("providers", []):
                        all_ids.add(provider["id"])

        return list(all_ids)

    def run(self):
        """Execute search across all counties."""
        counties = self._load_counties()
        all_provider_ids = set()

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(self.search_county, county): county
                for county in counties
            }

            for future in tqdm(as_completed(futures), total=len(counties)):
                county = futures[future]
                try:
                    ids = future.result()
                    all_provider_ids.update(ids)
                except Exception as e:
                    print(f"Error on {county}: {e}")

        print(f"Discovered {len(all_provider_ids)} unique providers")
        return all_provider_ids
```

#### Pattern B: Sapphire (Async + Stealth Browser)

```python
# index_1.py - Sapphire Pattern

import asyncio
import aiofiles
import orjson
from camoufox.async_api import AsyncCamoufox
from tenacity import AsyncRetrying, stop_after_attempt

class SapphireSearcher:
    """
    Async provider search using stealth browser with proxy rotation.

    Fetches provider summary + locations + affiliations + networks
    concurrently for each discovered provider ID.
    """

    BATCH_SIZE = 1000

    async def fetch_provider(self, provider_id: str, network_id: str, browser):
        """Fetch all data for a single provider."""
        results = {}

        # Fetch summary
        async for attempt in AsyncRetrying(stop=stop_after_attempt(2)):
            with attempt:
                url = config.BASE_URLS["summary"].format(
                    provider_id=provider_id,
                    network_id=network_id
                )
                response = await browser.fetch(url, timeout=120000)
                results["summary"] = await response.json()

        # Extract location IDs
        location_ids = [
            loc["location_id"]
            for loc in results["summary"].get("providers", [{}])[0].get("locations", [])
        ]

        # Fetch locations, affiliations, networks in parallel
        async def fetch_location_data(loc_id):
            location_results = {}

            for endpoint in ["affiliations", "locations", "networks"]:
                url = config.BASE_URLS[endpoint].format(
                    provider_id=provider_id,
                    location_id=loc_id
                )
                response = await browser.fetch(url, timeout=60000)
                location_results[endpoint] = await response.json()

            return loc_id, location_results

        # Concurrent location fetching
        tasks = [fetch_location_data(loc_id) for loc_id in location_ids]
        location_data = await asyncio.gather(*tasks)

        results["locations"] = dict(location_data)
        return results

    async def run(self):
        """Main execution loop."""
        # Load provider IDs from Phase 0
        with open(config.DIRS["raw"] + "/all_provider_ids.json", "rb") as f:
            provider_map = orjson.loads(f.read())

        provider_ids = list(provider_map.keys())

        async with AsyncCamoufox(proxy=config.PROXY_URL) as browser:
            for batch_start in range(0, len(provider_ids), self.BATCH_SIZE):
                batch = provider_ids[batch_start:batch_start + self.BATCH_SIZE]

                tasks = [
                    self.fetch_provider(pid, network, browser)
                    for pid in batch
                    for network in provider_map[pid][:1]  # First network only
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Save results
                for pid, result in zip(batch, results):
                    if isinstance(result, Exception):
                        await self._save_missing(pid)
                    else:
                        await self._save_result(pid, result)
```

#### Pattern C: Carrier (Geographic Grid Search)

```python
# index_1.py - Carrier Pattern

import httpx
import config
from concurrent.futures import ThreadPoolExecutor

class CarrierSearcher:
    """
    Specialty-by-specialty search with geographic center point.

    Uses fixed ZIP code (US center) with large radius for national coverage.
    """

    def __init__(self):
        self.client = httpx.Client(headers=config.HEADERS, timeout=30)
        self.results_dir = config.DIRS["search_results"]

    def search_specialty(self, specialty: dict) -> list:
        """Search all providers for a single specialty."""
        all_results = []
        page = 1
        total_pages = None

        while total_pages is None or page <= total_pages:
            payload = {
                **config.BASE_PAYLOAD,
                "searchValue": specialty["name"],
                "searchDisplayString": specialty["display"],
                "searchType": specialty["type"],
                "pageNumber": page,
            }

            response = self.client.post(
                config.BASE_SEARCH_URL,
                json=payload
            )
            data = response.json()

            # Cache raw response
            filename = f"{specialty['name']}_{page}.json"
            self._save_result(filename, data)

            # Update pagination
            if total_pages is None:
                total_pages = data.get("totalMatchingPages", 1)

            all_results.extend(data.get("providerResults", []))
            page += 1

        return all_results

    def run(self):
        """Execute search across all specialties."""
        with open("data/specialties.json", "r") as f:
            specialties = orjson.loads(f.read())["search_specialties"]

        all_providers = {}

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(self.search_specialty, spec)
                for spec in specialties
            ]

            for future in tqdm(futures):
                results = future.result()
                for provider in results:
                    npi = provider.get("npi")
                    if npi:
                        all_providers[npi] = provider

        # Save consolidated NPI list
        with open(config.DIRS["raw"] + "/npi_list.json", "wb") as f:
            f.write(orjson.dumps(all_providers))

        print(f"Discovered {len(all_providers)} unique NPIs")
```

### Output Structure

```
YYYYMMDD/raw/search_results/
├── {plan_code}/
│   ├── {county}-1-BEST_MATCH.json      # Page 1, best match sort
│   ├── {county}-1-NAME_ASC.json        # Page 1, alphabetical
│   ├── {county}-3-NAME_ASC.json        # Page 3, alphabetical
│   ├── {county}-filters.json           # Applied filter metadata
│   └── ...
├── US/
│   ├── Primary_Care_1.json             # Specialty search page 1
│   ├── Primary_Care_2.json             # Specialty search page 2
│   └── ...
└── all_provider_ids.json               # Consolidated ID mapping
```

---

## Phase 2: Detail Extraction

**Purpose**: Fetch detailed provider information for each discovered provider ID.

### Core Responsibilities
1. Load discovered IDs from Phase 1
2. Fetch individual provider details via API
3. Handle rate limiting and retries
4. Cache detailed responses to disk

### Implementation Patterns

#### Pattern A: Healthsparq (V1 + V2 Dual Endpoints)

```python
# index_2.py - Healthsparq Pattern

import os
from filelock import FileLock
from concurrent.futures import ThreadPoolExecutor, as_completed
import config

class HealthsparqDetailFetcher:
    """
    Fetch provider details from both V1 and V2 endpoints.

    V2 endpoint provides enhanced data (specialties, languages).
    Uses file locking for thread-safe writes.
    """

    def __init__(self, healthspark_client):
        self.client = healthspark_client
        self.details_dir = config.DIRS["provider_details"]
        os.makedirs(self.details_dir, exist_ok=True)

    def fetch_provider_details(self, provider_id: str, plan: dict) -> dict:
        """Fetch V1 and V2 details for a single provider."""
        output_path = f"{self.details_dir}/{provider_id}_{plan['productCode']}.json"
        lock_path = f"{output_path}.lock"

        with FileLock(lock_path):
            # Skip if already fetched
            if os.path.exists(output_path):
                with open(output_path, "r") as f:
                    existing = orjson.loads(f.read())
                    if existing.get("v2") and existing.get("status") != 404:
                        return existing

            # Fetch V1 endpoint
            result_v1 = self.client.get_provider_details(
                provider_id=provider_id,
                **plan
            )

            # Fetch V2 endpoint
            result_v2 = self.client.get_provider_details_v2(
                provider_id=provider_id,
                **plan
            )

            # Merge results
            result_v1["v2"] = result_v2

            # Save to disk
            with open(output_path, "wb") as f:
                f.write(orjson.dumps(result_v1))

            return result_v1

    def run(self):
        """Fetch details for all discovered providers."""
        # Aggregate all provider IDs from search results
        provider_ids = self._load_provider_ids()

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(self.fetch_provider_details, pid, plan)
                for pid in provider_ids
                for plan in config.PLANS
            ]

            for future in tqdm(as_completed(futures), total=len(futures)):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error: {e}")
```

#### Pattern B: Carrier (Alternate ID Lookup)

```python
# index_2.py - Carrier Pattern

class CarrierDetailFetcher:
    """
    Fetch provider details using alternate ID (MP3ID or CREDID).

    Uses ID from Phase 1 search results to query detail endpoint.
    """

    def fetch_provider_details(self, npi: str, data: dict) -> dict:
        """Fetch details for a single NPI."""
        output_path = f"{self.details_dir}/{npi}.json"

        if os.path.exists(output_path):
            return  # Already fetched

        # Determine which alternate ID to use
        req_key = "MP3ID" if "MP3ID" in data else "CREDID"

        payload = {
            "alternateIDNumber": data[req_key],
            "alternateIDType": req_key,
            "language": "en"
        }

        response = self.client.post(
            config.BASE_URLS["details"],
            json=payload
        )

        result = response.json()

        with open(output_path, "wb") as f:
            f.write(orjson.dumps(result))

        return result
```

### Output Structure

```
YYYYMMDD/raw/provider_details/
├── f1000637491.json                    # Individual provider details
├── f1000637491_missing.json            # Provider not found (tagged)
├── provider_details_mapping_batch_1.json  # Batched details (Healthsparq)
├── provider_details_mapping_batch_2.json
└── ...

YYYYMMDD/raw/locations/
├── f1000637491_2400049931.json         # Provider + location combo

YYYYMMDD/raw/affiliations/
├── f1000637491_2400049931.json         # Hospital/group affiliations

YYYYMMDD/raw/networks/
├── f1000637491_2400049931.json         # Network eligibility
```

---

## Phase 3: Normalization

**Purpose**: Transform raw API responses into standardized output schema with NPI-based deduplication.

### Core Responsibilities
1. Load all raw data from Phases 1-2
2. Map fields to standard output schema
3. Deduplicate by NPI (merge duplicate records)
4. Write final JSONL output

### Deduplication Strategy

```python
# NPI-Based Deduplication Logic

def deduplicate_by_npi(items: list) -> list:
    """
    Merge multiple records with the same NPI into a single record.

    Consolidation rules:
    - networks: Merge all unique network names
    - addresses: Merge all unique addresses (by external_id)
    - specialties: Merge all unique specialty names
    - group_affiliations: Merge all unique group names
    - hospital_affiliations: Merge all unique hospital names
    """
    npi_payload = {}  # {npi: merged_record}
    no_npi_records = []

    for item in items:
        npi = item["provider"]["npi"]

        if npi is None:
            no_npi_records.append(item)
            continue

        if npi not in npi_payload:
            npi_payload[npi] = item
        else:
            # Merge into existing record
            existing = npi_payload[npi]

            # Merge networks (dedupe by name)
            existing_networks = {n["name"]: n for n in existing["networks"]}
            for network in item["networks"]:
                existing_networks[network["name"]] = network
            existing["networks"] = list(existing_networks.values())

            # Merge addresses (dedupe by external_id)
            existing_addrs = {a["external_id"]: a for a in existing["addresses"]}
            for addr in item["addresses"]:
                if addr["external_id"] not in existing_addrs:
                    existing_addrs[addr["external_id"]] = addr
            existing["addresses"] = list(existing_addrs.values())

            # Merge specialties (dedupe by name)
            existing_specs = {s["name"]: s for s in existing["specialties"]}
            for spec in item["specialties"]:
                existing_specs[spec["name"]] = spec
            existing["specialties"] = list(existing_specs.values())

            # Merge affiliations (dedupe by name)
            for affil_type in ["group_affiliations", "hospital_affiliations"]:
                existing_affils = {a["name"]: a for a in existing[affil_type]}
                for affil in item[affil_type]:
                    existing_affils[affil["name"]] = affil
                existing[affil_type] = list(existing_affils.values())

    # Return deduplicated records + records without NPI
    return list(npi_payload.values()) + no_npi_records
```

### Field Mapping

```python
# Standard field mapping from raw API response

def map_provider(raw: dict) -> dict:
    """Map raw provider data to standard schema."""

    # Provider type classification
    provider_type = "individual" if raw.get("provider_type") == "P" else "organization"

    # Name parsing
    name_parts = parse_name(raw.get("name", ""))

    # NPI extraction
    npi = None
    for identifier in raw.get("identifiers", []):
        if identifier.get("type_code") == "NPI":
            npi = identifier.get("value")
            break

    return {
        "provider": {
            "unparsed_name": raw.get("name"),
            "provider_type": provider_type,
            "npi": npi,
            "first_name": name_parts.get("first"),
            "middle_name": name_parts.get("middle"),
            "last_name": name_parts.get("last"),
            "title": name_parts.get("title"),
            "suffix": name_parts.get("suffix"),
            "gender": map_gender(raw.get("gender")),
            "facility_name": raw.get("facility_name") if provider_type == "organization" else None,
            "license_number": None,
            "rating": {"scale": None, "score": None}
        }
    }

def map_address(raw_location: dict) -> dict:
    """Map raw location to standard address schema."""
    return {
        "street_line_1": raw_location.get("addr_line1"),
        "street_line_2": raw_location.get("addr_line2"),
        "city": raw_location.get("city"),
        "state": raw_location.get("state"),
        "zip": raw_location.get("postal_code", "")[:5],  # First 5 digits
        "office_name": raw_location.get("office_name"),
        "address_string": format_address_string(raw_location),
        "phones": map_phones(raw_location),
        "languages": map_languages(raw_location.get("languages", [])),
        "pcp": raw_location.get("is_pcp", False),
        "pcp_id": raw_location.get("pcp_id"),
        "accepting_new_patients": raw_location.get("accepting_new_patients") == "Y",
        "external_id": str(raw_location.get("location_id"))
    }
```

### Three-Pass Processing Pattern

```python
# index_3.py - Complete Normalization Flow

def normalize_all():
    """
    Three-pass normalization process.

    Pass 1: Load and normalize all provider records
    Pass 2: Merge duplicates by NPI
    Pass 3: Handle missing/incomplete records
    """

    # === PASS 1: Initial normalization ===
    print("Pass 1: Loading and normalizing...")

    all_items = []
    details_dir = Path(config.DIRS["provider_details"])

    for detail_file in tqdm(details_dir.glob("*.json")):
        if "_missing" in detail_file.name:
            continue  # Handle in Pass 3

        with open(detail_file, "rb") as f:
            raw = orjson.loads(f.read())

        # Map to standard schema
        item = {
            "networks": map_networks(raw),
            "provider": map_provider(raw),
            "addresses": [map_address(loc) for loc in raw.get("locations", [])],
            "specialties": map_specialties(raw),
            "group_affiliations": map_groups(raw),
            "hospital_affiliations": map_hospitals(raw),
        }

        all_items.append(item)

    print(f"Pass 1 complete: {len(all_items)} records")

    # === PASS 2: NPI deduplication ===
    print("Pass 2: Deduplicating by NPI...")

    deduplicated = deduplicate_by_npi(all_items)

    print(f"Pass 2 complete: {len(deduplicated)} unique records")

    # === PASS 3: Handle missing records ===
    print("Pass 3: Processing missing records...")

    for missing_file in details_dir.glob("*_missing.json"):
        with open(missing_file, "rb") as f:
            raw = orjson.loads(f.read())

        # Add minimal record if NPI is available
        if raw.get("npi"):
            item = create_minimal_record(raw)
            deduplicated.append(item)

    print(f"Pass 3 complete: {len(deduplicated)} total records")

    # === Write output ===
    output_path = Path(config.DIRS["processed"]) / f"{config.PROJECT_NAME}-{config.CURR_DATE}.jsonl"

    with open(output_path, "wb") as f:
        for item in deduplicated:
            f.write(orjson.dumps(item))
            f.write(b"\n")

    print(f"Output written: {output_path}")
```

### Output Format

```jsonl
{"networks":[{"name":"PPO","tier":null}],"provider":{"npi":"1234567890",...},"addresses":[...],...}
{"networks":[{"name":"HMO","tier":null}],"provider":{"npi":"0987654321",...},"addresses":[...],...}
```

---

## Pipeline Orchestration (run_all.py)

### Standard Orchestrator Pattern

```python
#!/usr/bin/env python3
"""
run_all.py - Pipeline Orchestrator

Executes all phases sequentially with error handling and progress tracking.
"""

import subprocess
import sys
import os
import traceback
import config

# Import QA utilities
workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from output_generator import (
    type_checker,
    sample_generator,
    compress_folder_to_7z,
    comparison_creator,
    report_generator,
    scheduler
)

# Task sequence
TASKS = [
    "compare_and_download_old_npi_4.py",  # NPI recovery from previous run
    "delete_extra_files",                  # Cleanup intermediate files
    "index_1.py",                          # Phase 1: Discovery
    "index_2.py",                          # Phase 2: Extraction
    "index_3.py",                          # Phase 3: Normalization
    "generate_all_qa_files",               # QA suite
]

def main():
    """Execute pipeline tasks sequentially."""

    for i, task in enumerate(TASKS, 1):
        print(f"\n📋 Task {i}/{len(TASKS)}: {task}")

        try:
            if task.endswith(".py"):
                # Execute Python script
                result = subprocess.run(
                    [sys.executable, task],
                    text=True,
                    check=False
                )

                if result.returncode != 0:
                    raise subprocess.CalledProcessError(result.returncode, task)

                print(f"✅ Success: {task}")

            elif task == "delete_extra_files":
                # Cleanup intermediate files
                cleanup_files = [
                    "provider_ids.json",
                    "mapped_payload.jsonl",
                    "processed_files.txt"
                ]

                for filename in cleanup_files:
                    path = os.path.join(config.DIRS["raw"], filename)
                    if os.path.exists(path):
                        os.remove(path)
                        print(f"🗑️ Deleted: {path}")

                print("✅ Success: delete_extra_files")

            elif task == "generate_all_qa_files":
                # Execute QA suite
                type_checker(
                    config.PROJECT_NAME,
                    config.CURR_DATE,
                    config.DIRS["processed"]
                )

                sample_generator(
                    config.PROJECT_NAME,
                    config.CURR_DATE,
                    config.DIRS["processed"]
                )

                comparison_creator(
                    config.PROJECT_NAME,
                    config.CURR_DATE,
                    config.DIRS["processed"],
                    config.PREV_DATE,
                    config.PREV_DIRS["processed"]
                )

                compress_folder_to_7z(
                    config.DIRS["processed"],
                    os.path.join(config.CURR_DATE, f"{config.CURR_DATE}.7z")
                )

                report_generator(
                    config.PROJECT_NAME,
                    config.CURR_DATE,
                    config.PREV_DATE,
                    config.REQ_STATES,
                    config.REQ_STATES_ONLY
                )

                print("✅ Success: generate_all_qa_files")

        except Exception as e:
            traceback.print_exc()
            print(f"❌ Failed: {task} - {e}")
            print(f"🛑 PIPELINE STOPPED - Task {i}/{len(TASKS)} failed")
            sys.exit(1)

    print("\n" + "=" * 50)
    print("🎉 PIPELINE COMPLETE")
    print("=" * 50)

if __name__ == "__main__":
    main()
```

### Orchestrator Variations

| Pattern | Usage | Projects |
|---------|-------|----------|
| **TASKS List** | Declarative task sequence | 63% of projects |
| **files List** | Helper function execution | 33% of projects |
| **Minimal** | Direct sequential execution | 4% of projects |

---

## Error Handling & Recovery

### Retry Logic

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError))
)
def fetch_with_retry(url: str, params: dict) -> dict:
    """Fetch URL with automatic retry on transient failures."""
    response = httpx.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()
```

### Recovery from Partial Runs

The pipeline caches intermediate results to disk, enabling recovery:

1. **Phase 1 Recovery**: Search results are cached individually; restart skips completed searches
2. **Phase 2 Recovery**: Detail files are checked for existence; restart skips fetched providers
3. **Phase 3 Recovery**: Reads all available raw files; can be re-run after fixing issues

```python
# Example: Skip already-fetched providers
output_path = f"{details_dir}/{provider_id}.json"
if os.path.exists(output_path):
    print(f"Skipping {provider_id} (already fetched)")
    continue
```

---

## QA Suite Integration

### Post-Processing Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          QA SUITE EXECUTION                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌───────────────────┐                                                  │
│  │   type_check.py   │                                                  │
│  │                   │                                                  │
│  │  • Schema valid.  │───▶ Excel report (13 sheets)                    │
│  │  • Deduplication  │     ├── Networks                                │
│  │  • Text sanitize  │     ├── Provider Names                          │
│  │                   │     ├── NPI List                                 │
│  └─────────┬─────────┘     ├── Zip Codes                               │
│            │               ├── Addresses                                │
│            ▼               ├── Phones                                   │
│  ┌───────────────────┐     ├── Languages                               │
│  │ sample_generator  │     ├── Groups                                  │
│  │                   │     ├── Hospitals                               │
│  │  • 10 random JSON │     └── Specialties                             │
│  │  • QA validation  │                                                  │
│  └─────────┬─────────┘                                                  │
│            │                                                             │
│            ▼                                                             │
│  ┌───────────────────┐                                                  │
│  │comparison_creator │                                                  │
│  │                   │                                                  │
│  │  • Diff analysis  │───▶ Changes report                              │
│  │  • New/dropped    │     ├── New items                               │
│  │  • Count changes  │     ├── Dropped items                           │
│  └─────────┬─────────┘     └── Count changes                           │
│            │                                                             │
│            ▼                                                             │
│  ┌───────────────────┐                                                  │
│  │ report_generator  │                                                  │
│  │                   │                                                  │
│  │  • Statistics     │───▶ Summary Excel                               │
│  │  • State counts   │     ├── In-scope/Out-scope                      │
│  │  • NPI analysis   │     ├── NPI drop analysis                       │
│  └─────────┬─────────┘     └── Per-state counts                        │
│            │                                                             │
│            ▼                                                             │
│  ┌───────────────────┐                                                  │
│  │compress_to_7z     │───▶ project-YYYYMMDD.7z                         │
│  └───────────────────┘                                                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Performance Optimization

### Parallelization Strategies

| Component | Strategy | Max Workers |
|-----------|----------|-------------|
| Phase 1 Search | ThreadPoolExecutor | 10 |
| Phase 2 Details | ThreadPoolExecutor/Async | 10 |
| Phase 3 Normalize | Single-threaded | 1 |
| QA Suite | Single-threaded | 1 |

### Memory Management

```python
# Chunked file processing for large datasets
def process_jsonl_in_chunks(filepath: str, chunk_size: int = 10000):
    """Process large JSONL files in memory-efficient chunks."""
    chunk = []

    with open(filepath, "r") as f:
        for line in f:
            chunk.append(orjson.loads(line))

            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []

    if chunk:  # Remaining items
        yield chunk
```

---

## References

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture overview
- [SITE_TYPES.md](./SITE_TYPES.md) - Site-type specific implementations
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Debugging guide

---

*Last Updated: December 2024*

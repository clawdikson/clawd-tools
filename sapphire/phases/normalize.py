"""Phase 3: Data Normalization for Sapphire package.

Maps raw Sapphire API response data to Ideon output schema and deduplicates by NPI.
All configuration is injected - no global state.

Supports custom mapper injection for project-specific normalization logic.

Storage backends for input:
- JSON_FILES (default): Individual JSON files on disk
- SQLITE: SQLite database (faster for large datasets)
- JSONL: Line-delimited JSON file
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator, Literal, Optional

import orjson

from sapphire.config.schema import SapphireProjectConfig, StorageBackend
from sapphire.core.exceptions import StorageError
from sapphire.core.storage import create_phase_store, get_output_path
from sapphire.mappers import MapperFunc, get_mapper

# Use core package logger if available, fallback to stdlib
try:
    from core.logging import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

# Import from core package for normalization utilities
try:
    from core.mapper.normalize import (
        build_address_string,
        clean_network_name,
        normalize_gender,
        normalize_phone,
        normalize_zip_code,
    )
except ImportError:
    # Fallback implementations
    def normalize_zip_code(zip_code: str | None) -> str | None:
        if zip_code is None:
            return None
        cleaned = zip_code.replace("-", "").replace(" ", "").strip()
        if len(cleaned) >= 5 and cleaned[:5].isdigit():
            return cleaned[:5]
        return None

    def normalize_gender(gender: str | None) -> str | None:
        if gender in ["M", "F", "O"]:
            return gender
        return None

    def normalize_phone(phone: str | None) -> str | None:
        if phone is None:
            return None
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
        if street_line_2:
            return f"{street_line_1}, {street_line_2}, {city}, {state} {zip_code}"
        return f"{street_line_1}, {city}, {state} {zip_code}"

    def clean_network_name(name: str, replacements: dict[str, str] | None = None) -> str:
        cleaned = name.replace('"', "").replace("\\", "").strip()
        if replacements:
            for old, new in replacements.items():
                cleaned = cleaned.replace(old, new)
        return cleaned


# Import from core package for deduplication
try:
    from core.mapper.dedup import deduplicate_by_npi, merge_provider_records
except ImportError:
    # Fallback implementation
    from copy import deepcopy

    def merge_provider_records(
        existing: dict[str, Any],
        new: dict[str, Any],
    ) -> dict[str, Any]:
        merged = deepcopy(existing)
        existing_networks = {n["name"] for n in merged.get("networks", [])}
        for network in new.get("networks", []):
            if network["name"] not in existing_networks:
                merged["networks"].append(network)
        existing_addr_ids = {a.get("external_id") for a in merged.get("addresses", [])}
        for addr in new.get("addresses", []):
            if addr.get("external_id") not in existing_addr_ids:
                merged["addresses"].append(addr)
        existing_groups = {g["name"] for g in merged.get("group_affiliations", [])}
        for grp in new.get("group_affiliations", []):
            if grp["name"] not in existing_groups:
                merged["group_affiliations"].append(grp)
        existing_hospitals = {h["name"] for h in merged.get("hospital_affiliations", [])}
        for hosp in new.get("hospital_affiliations", []):
            if hosp["name"] not in existing_hospitals:
                merged["hospital_affiliations"].append(hosp)
        existing_specs = {s["name"] for s in merged.get("specialties", [])}
        for spec in new.get("specialties", []):
            if spec["name"] not in existing_specs:
                merged["specialties"].append(spec)
        if merged.get("provider", {}).get("license_number") is None:
            merged["provider"]["license_number"] = new.get("provider", {}).get(
                "license_number"
            )
        return merged

    def deduplicate_by_npi(
        records: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], int]:
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


# Import BoundedSet for memory-safe deduplication (optional enhancement)
try:
    from core.io import BoundedSet
except ImportError:
    # Fallback: use regular set
    BoundedSet = set  # type: ignore

# Optional JSON Schema validation
try:
    from core.mapper.schema import validate_record
except ImportError:
    validate_record = None


# -----------------------------------------------------------------------------
# Configuration and Result Dataclasses
# -----------------------------------------------------------------------------


@dataclass
class NormalizeConfig:
    """Configuration for the normalize phase."""

    validate: bool = False
    """Enable optional JSON schema validation (log errors, don't fail)."""

    deduplicate: bool = True
    """Enable NPI-based deduplication."""

    output_format: Literal["jsonl", "json"] = "jsonl"
    """Output file format."""


@dataclass
class NormalizeResult:
    """Result of normalization operation."""

    total_records: int
    """Total raw records processed."""

    unique_npis: int
    """Number of unique NPI records after deduplication."""

    duplicates_removed: int
    """Number of duplicate NPI records merged."""

    validation_errors: int = 0
    """Number of records with validation errors (if validate=True)."""

    output_file: Optional[Path] = None
    """Path to the output file."""

    error: Optional[str] = None
    """Error message if normalization failed."""


# -----------------------------------------------------------------------------
# Default Sapphire Mapper
# -----------------------------------------------------------------------------


def _format_address(data: dict[str, Any]) -> dict[str, Any]:
    """Format a single address from Sapphire raw data.

    Based on BCBS IL pattern: _format_address function.
    """
    # Extract PCP identifiers
    pcp_id_list = [
        x for x in data.get("identifiers", []) if x.get("type_code") in ["PID", "PCP"]
    ]

    # Normalize ZIP to 5 digits
    raw_zip = data.get("postal_code") or data.get("zip")
    zip_code = normalize_zip_code(raw_zip)

    street_line_1 = data.get("addr_line1") or data.get("address_line_1")
    street_line_2 = data.get("addr_line2") or data.get("address_line_2")
    city = data.get("city")
    state = data.get("state")

    # Build address string
    address_string = ""
    if street_line_1 and city and state and zip_code:
        address_string = build_address_string(
            street_line_1, street_line_2, city, state, zip_code
        )

    # Format phones
    phones: list[dict[str, str]] = []
    phone = data.get("phone")
    if phone:
        phones.append({"type": "phone", "value": normalize_phone(phone) or phone})
    fax = data.get("fax")
    if fax:
        phones.append({"type": "fax", "value": normalize_phone(fax) or fax})

    # Format languages
    languages = [
        {"name": lang, "type": "primary"} for lang in (data.get("languages") or [])
    ]

    # Determine accepting_new_patients
    accepting_raw = data.get("accepting_new_patients")
    if isinstance(accepting_raw, bool):
        accepting_new_patients = accepting_raw
    elif isinstance(accepting_raw, str):
        accepting_new_patients = accepting_raw.upper() in ["Y", "YES", "TRUE", "1"]
    else:
        accepting_new_patients = False

    return {
        "street_line_1": street_line_1,
        "street_line_2": street_line_2 if street_line_2 else None,
        "city": city,
        "state": state,
        "zip": zip_code,
        "office_name": data.get("location_name") or data.get("office_name"),
        "address_string": address_string,
        "phones": phones,
        "languages": languages,
        "pcp": data.get("is_pcp") or len(pcp_id_list) > 0,
        "pcp_id": None if len(pcp_id_list) == 0 else pcp_id_list[0].get("value"),
        "accepting_new_patients": accepting_new_patients,
        "external_id": (
            str(data.get("location_id")) if data.get("location_id") else None
        ),
    }


def default_sapphire_mapper(data: dict[str, Any]) -> dict[str, Any]:
    """Map raw Sapphire API response to Ideon output schema.

    Takes raw provider data from Phase 2 and returns normalized Ideon format with:
    - networks: list[{"name": str, "tier": None}]
    - provider: {"npi", "first_name", "last_name", "gender", "provider_type", etc.}
    - addresses: list with phones, languages, accepting_new_patients
    - group_affiliations: list[{"name": str}]
    - hospital_affiliations: list[{"name": str}]
    - specialties: list[{"name": str}]

    Based on BCBS IL map_json_to_ideon_format pattern.

    Args:
        data: Raw provider data from Sapphire API (Phase 2 output).

    Returns:
        Normalized provider record conforming to Ideon output schema.
    """
    # Determine provider type
    provider_type_raw = data.get("provider_type")
    if provider_type_raw == "P":
        provider_type = "individual"
    elif provider_type_raw == "O":
        provider_type = "organization"
    else:
        # Infer from other fields
        provider_type = (
            "individual" if data.get("first_name") or data.get("last_name") else "organization"
        )

    name = data.get("name") or data.get("full_name") or ""
    npi = data.get("npi") or data.get("npi_identifier")

    # Extract networks (from network map or inline)
    networks: list[dict[str, Any]] = []
    raw_networks = data.get("networks") or data.get("network_ids") or []
    if isinstance(raw_networks, list):
        for network in raw_networks:
            if isinstance(network, str):
                cleaned = clean_network_name(network)
                if cleaned:
                    networks.append({"name": cleaned, "tier": None})
            elif isinstance(network, dict):
                network_name = network.get("name") or network.get("id") or ""
                cleaned = clean_network_name(network_name)
                if cleaned:
                    networks.append({"name": cleaned, "tier": network.get("tier")})

    # Deduplicate and sort networks by name
    unique_networks = {n["name"]: n for n in networks if n["name"]}
    networks = sorted(unique_networks.values(), key=lambda x: x["name"])

    # Extract gender
    gender = normalize_gender(data.get("gender"))

    # Build provider object
    provider = {
        "unparsed_name": name,
        "gender": gender,
        "provider_type": provider_type,
        "npi": npi,
        "license_number": data.get("license_number"),
        "facility_name": name if provider_type == "organization" else None,
        "first_name": data.get("first_name") if provider_type == "individual" else None,
        "middle_name": data.get("middle_name") if provider_type == "individual" else None,
        "last_name": data.get("last_name") if provider_type == "individual" else None,
        "title": " ".join(x for x in data.get("degree_types", []) if x),
        "suffix": data.get("suffix"),
        "rating": {
            "score": data.get("rating_score"),
            "scale": data.get("rating_scale"),
        },
    }

    # Extract addresses (primary and other locations)
    addresses: list[dict[str, Any]] = []

    # Primary address
    if data.get("addr_line1") or data.get("address_line_1"):
        addresses.append(_format_address(data))

    # Other locations
    for location in data.get("other_provider_locations", []):
        addresses.append(_format_address(location))

    # Locations array (alternative format)
    for location in data.get("locations", []):
        addresses.append(_format_address(location))

    # Filter out addresses without required fields
    addresses = [
        addr for addr in addresses if addr.get("street_line_1") and addr.get("zip")
    ]

    # Extract affiliations from inline data or affiliations response
    group_affiliations_raw = data.get("group_affiliations", [])
    group_names = set()
    for aff in group_affiliations_raw:
        name_val = aff.get("name") if isinstance(aff, dict) else aff
        if name_val:
            group_names.add(name_val)
    group_affiliations = [{"name": name} for name in sorted(group_names)]

    hospital_affiliations_raw = data.get("hospital_affiliations", [])
    hospital_names = set()
    for aff in hospital_affiliations_raw:
        name_val = aff.get("name") if isinstance(aff, dict) else aff
        if name_val:
            hospital_names.add(name_val)
    hospital_affiliations = [{"name": name} for name in sorted(hospital_names)]

    # Extract specialties
    specialties_raw = set()
    primary_specialty = data.get("primary_specialty")
    if primary_specialty:
        specialties_raw.add(primary_specialty)
    for spec in data.get("additional_specialties", []):
        if spec:
            specialties_raw.add(spec)
    relevant_specialty = data.get("relevant_specialty")
    if relevant_specialty:
        specialties_raw.add(relevant_specialty)
    specialties = [{"name": spec} for spec in sorted(specialties_raw)]

    return {
        "networks": networks,
        "provider": provider,
        "addresses": addresses,
        "group_affiliations": group_affiliations,
        "hospital_affiliations": hospital_affiliations,
        "specialties": specialties,
    }


# -----------------------------------------------------------------------------
# Raw Data Loading
# -----------------------------------------------------------------------------


def load_raw_records(
    raw_dir: Path,
    storage_backend: StorageBackend = StorageBackend.JSON_FILES,
) -> Iterator[dict[str, Any]]:
    """Load raw provider records from Phase 2 output.

    Supports multiple storage backends:
    - JSON_FILES: Individual JSON files in directory
    - SQLITE: SQLite database
    - JSONL: Line-delimited JSON file

    Args:
        raw_dir: Path to raw data directory or store
        storage_backend: Storage backend type

    Yields:
        Raw provider records
    """
    # Use DataStore for SQLITE and JSONL backends
    if storage_backend in (StorageBackend.SQLITE, StorageBackend.JSONL):
        try:
            with create_phase_store(
                raw_dir.parent.parent,  # Go up from raw/provider_details to base
                phase_name="provider_details",
                storage_backend=storage_backend,
                read_only=True,
            ) as store:
                for path, record in store.iter_results():
                    yield record
        except StorageError as e:
            logger.error(f"Failed to load from store: {e}")
            return
        return

    # Default: Load from filesystem (JSON files)
    if not raw_dir.exists():
        logger.warning(f"Raw directory does not exist: {raw_dir}")
        return

    json_files = list(raw_dir.glob("*.json"))
    if not json_files:
        logger.warning(f"No JSON files found in: {raw_dir}")
        return

    logger.info(f"Loading {len(json_files)} raw provider files from {raw_dir}")

    for file_path in json_files:
        try:
            with open(file_path, "rb") as f:
                data = orjson.loads(f.read())
            yield data
        except (orjson.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(f"Skipping corrupted file {file_path}: {e}")
            continue
        except (OSError, IOError) as e:
            logger.warning(f"Unable to read file {file_path}: {e}")
            continue


# -----------------------------------------------------------------------------
# Main Normalization Functions
# -----------------------------------------------------------------------------


async def run_normalize(
    config: SapphireProjectConfig,
    curr_date: str,
    mapper: MapperFunc | None = None,
    normalize_config: NormalizeConfig | None = None,
) -> NormalizeResult:
    """Run the normalization phase (async entry point).

    Args:
        config: Sapphire project configuration.
        curr_date: Current date string (YYYYMMDD).
        mapper: Optional custom mapper function. If not provided, uses
                default_sapphire_mapper. Projects can register custom mappers
                via sapphire.mappers.register_mapper().
        normalize_config: Optional normalization configuration.

    Returns:
        NormalizeResult with statistics and output file path.
    """
    # Use sync implementation (no async I/O needed for file operations)
    return run_normalize_sync(config, curr_date, mapper, normalize_config)


def run_normalize_sync(
    config: SapphireProjectConfig,
    curr_date: str,
    mapper: MapperFunc | None = None,
    normalize_config: NormalizeConfig | None = None,
) -> NormalizeResult:
    """Run the normalization phase (synchronous entry point).

    Args:
        config: Sapphire project configuration.
        curr_date: Current date string (YYYYMMDD).
        mapper: Optional custom mapper function. If not provided:
                1. Checks for registered mapper via get_mapper(project_slug)
                2. Falls back to default_sapphire_mapper
        normalize_config: Optional normalization configuration.

    Returns:
        NormalizeResult with statistics and output file path.
    """
    if normalize_config is None:
        normalize_config = NormalizeConfig()

    # Resolve mapper: explicit > registered > default
    if mapper is None:
        mapper = get_mapper(config.project.slug)
    if mapper is None:
        mapper = default_sapphire_mapper

    mapper_name = getattr(mapper, "__name__", "custom_mapper")

    # Setup paths
    base_dir = Path(config.output.base_dir) if config.output.base_dir else Path(".")
    raw_dir = base_dir / curr_date / config.output.raw_subdir / "provider_details"
    output_dir = base_dir / curr_date / config.output.processed_subdir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine output filename
    if normalize_config.output_format == "jsonl":
        output_file = output_dir / f"{config.project.slug}-{curr_date}.jsonl"
    else:
        output_file = output_dir / f"{config.project.slug}-{curr_date}.json"

    logger.info("=" * 70)
    logger.info("SAPPHIRE NORMALIZATION STARTED")
    logger.info("=" * 70)
    logger.info(f"Project: {config.project.name}")
    logger.info(f"Mapper: {mapper_name}")
    logger.info(f"Raw dir: {raw_dir}")
    logger.info(f"Output: {output_file}")
    logger.info(f"Validation: {'enabled' if normalize_config.validate else 'disabled'}")
    logger.info(f"Deduplication: {'enabled' if normalize_config.deduplicate else 'disabled'}")

    try:
        # Stage 1: Load and map raw data
        logger.info("Stage 1: Loading and mapping raw provider data")
        mapped_records: list[dict[str, Any]] = []
        total_raw = 0
        mapping_errors = 0
        validation_error_count = 0

        for raw_record in load_raw_records(raw_dir, config.output.storage_backend):
            total_raw += 1
            try:
                mapped = mapper(raw_record)
                # Skip empty or invalid records
                if not mapped.get("provider"):
                    continue
                # Skip records without name
                if not mapped["provider"].get("unparsed_name") and not mapped["provider"].get("npi"):
                    continue
                mapped_records.append(mapped)
            except Exception as e:
                mapping_errors += 1
                if mapping_errors <= 10:  # Limit log spam
                    logger.warning(f"Error mapping record: {e}")
                continue

        logger.info(f"Loaded {total_raw} raw records")
        logger.info(f"Mapped {len(mapped_records)} records successfully")
        if mapping_errors > 0:
            logger.warning(f"Failed to map {mapping_errors} records")

        if len(mapped_records) == 0:
            logger.warning("No records to process after mapping")
            return NormalizeResult(
                total_records=total_raw,
                unique_npis=0,
                duplicates_removed=0,
                output_file=None,
            )

        # Stage 2: Optional validation
        if normalize_config.validate:
            if validate_record is None:
                logger.warning(
                    "Validation requested but core.mapper.schema not available. "
                    "Install jsonschema package."
                )
            else:
                logger.info("Stage 2: Validating mapped records against schema")
                for i, record in enumerate(mapped_records):
                    is_valid, errors = validate_record(record)
                    if not is_valid:
                        validation_error_count += 1
                        npi = record.get("provider", {}).get("npi", "unknown")
                        if validation_error_count <= 20:  # Limit log output
                            logger.warning(
                                f"Validation errors for NPI {npi}: "
                                f"{'; '.join(errors[:3])}"
                            )
                logger.info(
                    f"Validation complete: {len(mapped_records) - validation_error_count} valid, "
                    f"{validation_error_count} with errors"
                )

        # Stage 3: Deduplication by NPI
        if normalize_config.deduplicate:
            logger.info("Stage 3: Deduplicating by NPI")
            deduplicated, merge_count = deduplicate_by_npi(mapped_records)
            logger.info(f"Consolidated to {len(deduplicated)} unique providers")
            logger.info(f"Merged {merge_count} duplicate records")
        else:
            deduplicated = mapped_records
            merge_count = 0
            logger.info("Stage 3: Deduplication disabled, skipping")

        # Stage 4: Write output
        logger.info("Stage 4: Writing output file")
        write_errors = 0

        if normalize_config.output_format == "jsonl":
            with open(output_file, "wb") as f:
                for record in deduplicated:
                    try:
                        f.write(orjson.dumps(record) + b"\n")
                    except Exception as e:
                        write_errors += 1
                        logger.error(f"Error writing record: {e}")
                        continue
        else:
            # JSON format (single array)
            try:
                with open(output_file, "wb") as f:
                    f.write(orjson.dumps(deduplicated, option=orjson.OPT_INDENT_2))
            except Exception as e:
                logger.error(f"Error writing JSON output: {e}")
                return NormalizeResult(
                    total_records=total_raw,
                    unique_npis=0,
                    duplicates_removed=0,
                    error=str(e),
                )

        if write_errors > 0:
            logger.warning(f"Failed to write {write_errors} records")

        logger.info(f"Successfully wrote {len(deduplicated)} records to {output_file}")
        logger.info("=" * 70)
        logger.info("SAPPHIRE NORMALIZATION COMPLETED SUCCESSFULLY")
        logger.info("=" * 70)

        return NormalizeResult(
            total_records=total_raw,
            unique_npis=len(deduplicated),
            duplicates_removed=merge_count,
            validation_errors=validation_error_count,
            output_file=output_file,
        )

    except Exception as e:
        logger.critical(f"FATAL ERROR: {e}")
        logger.exception("Full traceback:")
        return NormalizeResult(
            total_records=0,
            unique_npis=0,
            duplicates_removed=0,
            error=str(e),
        )


# Export default mapper for projects to extend
__all__ = [
    "NormalizeConfig",
    "NormalizeResult",
    "default_sapphire_mapper",
    "run_normalize",
    "run_normalize_sync",
]

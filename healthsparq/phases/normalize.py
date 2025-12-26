"""Phase 3: Data Normalization module.

Maps raw provider data to standard schema and deduplicates by NPI.
All configuration is injected - no global state.
"""

import os
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import orjson

from healthsparq.config import HealthSparqProjectConfig


@dataclass
class NormalizeConfig:
    """Configuration for normalize phase."""

    config: HealthSparqProjectConfig
    curr_date: str
    raw_dir: Optional[Path] = None
    output_dir: Optional[Path] = None

    def __post_init__(self):
        base = Path(self.curr_date)
        if self.raw_dir is None:
            self.raw_dir = base / "raw" / "provider_details"
        if self.output_dir is None:
            self.output_dir = base / "processed"


@dataclass
class NormalizeResult:
    """Result of normalization operation."""

    total_raw: int
    total_normalized: int
    duplicates_merged: int
    output_file: Optional[str] = None
    error: Optional[str] = None


def get_network_names(data: dict[str, Any]) -> list[dict[str, Any]]:
    network_names = set()
    for loc in data.get("locations", []):
        for attr in loc.get("attributes", []):
            loc[attr.get("key")] = attr.get("value")
        for category in loc.get("PLANS_ACCEPTED", []):
            for sub_category in category.get("subCategories", []):
                for plan in sub_category.get("plans", []):
                    network_names.add(f"{plan.get('name', '')}")
    return [{"name": network, "tier": None} for network in network_names]


def get_provider_data(data: dict[str, Any]) -> dict[str, Any]:
    provider_type = (
        "individual" if data.get("providerCategoryCode", "") == "P" else "organization"
    )
    gender = None
    prov_name = data.get("provider", {}).get("fullName", "")
    if provider_type == "individual":
        prov_name = " ".join(reversed(prov_name.split(","))).strip()
        gender = data.get("GENDER")[0] if data.get("GENDER") is not None else None
        if gender not in ["M", "F", "O"]:
            gender = None
    return {
        "unparsed_name": prov_name,
        "gender": gender,
        "provider_type": provider_type,
        "npi": data.get("npi", None),
        "license_number": data.get("licenseNumber", None),
        "facility_name": prov_name if provider_type == "organization" else None,
        "first_name": data.get("provider", {}).get("firstName", None),
        "middle_name": data.get("provider", {}).get("middleName", None),
        "last_name": data.get("provider", {}).get("lastName", None),
        "title": " ".join(data.get("degreeCredentials", [])),
        "suffix": data.get("provider", {}).get("suffix", None),
        "rating": {"scale": None, "score": None},
    }


def get_addresses(data: dict[str, Any]) -> list[dict[str, Any]]:
    addresses = []
    for loc in data.get("locations", []):
        accepting_new_patients = False
        pcp = False
        for attribute in loc.get("attributes", []):
            if attribute.get("key") == "PLANS_ACCEPTED":
                for plan in attribute.get("value", []):
                    if plan.get("pcpEligible"):
                        pcp = True
                    if plan.get("acceptingPatients", {}).get("labelKey", "") in [
                        "elevated.anp.acceptingSome",
                        "elevated.anp.acceptingAll",
                    ]:
                        accepting_new_patients = True
        street_line_1 = loc.get("address", {}).get("line1")
        street_line_2 = loc.get("address", {}).get("line2")
        city = loc.get("address", {}).get("city")
        state = loc.get("address", {}).get("state")
        zip_code = loc.get("address", {}).get("zip")

        for elevAttr in loc.get("elevatedAttributes", []):
            if (
                elevAttr.get("labelKey") == "elevated.pcp.true"
                and elevAttr.get("style") == "success"
            ):
                pcp = True
                break

        contact = {}
        for attribute in loc.get("attributes", []):
            if attribute.get("key") == "CONTACT":
                for contact_info in attribute.get("value", []):
                    values = contact_info.get("values", [])
                    if values:
                        contact[contact_info.get("type")] = values[0].get("display")

        if street_line_1 is not None and zip_code is not None:
            addresses.append(
                {
                    "street_line_1": street_line_1,
                    "street_line_2": street_line_2,
                    "city": city,
                    "state": state,
                    "zip": zip_code,
                    "office_name": loc.get("name"),
                    "address_string": (
                        f"{street_line_1}, {city}, {state} {zip_code}"
                        if street_line_2 is None
                        else f"{street_line_1}, {street_line_2}, {city}, {state} {zip_code}"
                    ),
                    "phones": [
                        {"type": contact_info, "value": value}
                        for contact_info, value in contact.items()
                        if contact_info in ["phone", "fax"]
                    ],
                    "languages": [
                        {"name": lang, "type": "primary"}
                        for lang in data.get(
                            "PROVIDER_LANGUAGES", loc.get("STAFF_LANGUAGES", [])
                        )
                    ],
                    "pcp": pcp,
                    "pcp_id": loc.get("pcpId", None),
                    "accepting_new_patients": accepting_new_patients,
                    "external_id": str(loc.get("id")),
                }
            )
    return addresses


def get_group_affiliations(data: dict[str, Any]) -> list[dict[str, str]]:
    group_affiliations = list(
        set([x["name"] for x in data.get("GROUP_AFFILIATIONS", [])])
    )
    return [{"name": affiliation} for affiliation in group_affiliations]


def get_hospital_affiliations(data: dict[str, Any]) -> list[dict[str, str]]:
    hospital_affiliations = set(
        [x["name"] for x in data.get("HOSPITAL_AFFILIATIONS", [])]
    )
    for loc in data.get("locations", []):
        for attr in loc.get("attributes", []):
            if attr.get("name") == "Hospital Affiliation":
                for affiliation in attr.get("value", []):
                    hospital_affiliations.add(affiliation)
    return [{"name": affiliation} for affiliation in hospital_affiliations]


def get_specialties(data: dict[str, Any]) -> list[dict[str, str]]:
    specialties = set()
    for loc in data.get("locations", []):
        for attr in loc.get("attributes", []):
            if attr.get("key") == "SPECIALTY":
                for specialty in attr.get("value", []):
                    specialties.add(specialty)
    return [{"name": specialty} for specialty in specialties]


def map_to_schema(data: dict[str, Any]) -> dict[str, Any]:
    """Map raw provider data to standard schema."""
    mapped_data = {
        "networks": [],
        "provider": {},
        "addresses": [],
        "group_affiliations": [],
        "hospital_affiliations": [],
        "specialties": [],
    }

    npi = data.get("npi")

    if data.get("v2") is not None:
        v2_data = data.get("v2")
        data = deepcopy(v2_data)
        data["npi"] = npi
        for attr in data.get("attributes", []):
            data[attr.get("key")] = attr.get("value")
    else:
        # Return empty if no v2 data
        return mapped_data

    mapped_data["networks"] = get_network_names(data)
    mapped_data["provider"] = get_provider_data(data)
    mapped_data["addresses"] = get_addresses(data)
    mapped_data["group_affiliations"] = get_group_affiliations(data)
    mapped_data["hospital_affiliations"] = get_hospital_affiliations(data)
    mapped_data["specialties"] = get_specialties(data)

    return mapped_data


def merge_provider_data(existing: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Merge two provider records with same NPI."""
    merged = deepcopy(existing)

    # Merge networks
    existing_network_names = {n["name"] for n in merged["networks"]}
    for network in new["networks"]:
        if network["name"] not in existing_network_names:
            merged["networks"].append(network)

    # Merge addresses by external_id
    existing_addr_ids = {a["external_id"] for a in merged["addresses"]}
    for addr in new["addresses"]:
        if addr["external_id"] not in existing_addr_ids:
            merged["addresses"].append(addr)

    # Merge group affiliations
    existing_groups = {g["name"] for g in merged["group_affiliations"]}
    for grp in new["group_affiliations"]:
        if grp["name"] not in existing_groups:
            merged["group_affiliations"].append(grp)

    # Merge hospital affiliations
    existing_hospitals = {h["name"] for h in merged["hospital_affiliations"]}
    for hosp in new["hospital_affiliations"]:
        if hosp["name"] not in existing_hospitals:
            merged["hospital_affiliations"].append(hosp)

    # Merge specialties
    existing_specs = {s["name"] for s in merged["specialties"]}
    for spec in new["specialties"]:
        if spec["name"] not in existing_specs:
            merged["specialties"].append(spec)

    # Fill in missing provider data
    if (
        merged["provider"]["license_number"] is None
        and new["provider"]["license_number"] is not None
    ):
        merged["provider"]["license_number"] = new["provider"]["license_number"]

    return merged


def deduplicate_by_npi(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Deduplicate provider records by NPI, returning (records, merge_count)."""
    npi_map: dict[str, dict[str, Any]] = {}
    no_npi_records: list[dict[str, Any]] = []
    merge_count = 0

    for record in records:
        npi = record["provider"].get("npi")
        if npi is None:
            no_npi_records.append(record)
        elif npi not in npi_map:
            npi_map[npi] = record
        else:
            npi_map[npi] = merge_provider_data(npi_map[npi], record)
            merge_count += 1

    return list(npi_map.values()) + no_npi_records, merge_count


def load_raw_details(raw_dir: Path) -> list[dict[str, Any]]:
    """Load raw provider detail JSON files from directory."""
    records = []
    if not raw_dir.exists():
        return records

    for file_path in raw_dir.glob("*.json"):
        try:
            with open(file_path, "rb") as f:
                data = orjson.loads(f.read())
            records.append(data)
        except Exception:
            continue

    return records


def run_normalize(normalize_config: NormalizeConfig) -> NormalizeResult:
    """Run the normalize phase."""
    config = normalize_config.config
    raw_dir = Path(normalize_config.raw_dir)
    output_dir = Path(normalize_config.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Load raw data
        raw_records = load_raw_details(raw_dir)
        total_raw = len(raw_records)

        # Map to schema
        mapped_records = []
        for record in raw_records:
            mapped = map_to_schema(record)
            if mapped["provider"]:
                mapped_records.append(mapped)

        # Deduplicate by NPI
        deduplicated, merge_count = deduplicate_by_npi(mapped_records)

        # Write output
        output_file = (
            output_dir / f"{config.project.slug}-{normalize_config.curr_date}.jsonl"
        )
        with open(output_file, "wb") as f:
            for record in deduplicated:
                f.write(orjson.dumps(record) + b"\n")

        return NormalizeResult(
            total_raw=total_raw,
            total_normalized=len(deduplicated),
            duplicates_merged=merge_count,
            output_file=str(output_file),
        )

    except Exception as e:
        return NormalizeResult(
            total_raw=0,
            total_normalized=0,
            duplicates_merged=0,
            error=str(e),
        )


def run_normalize_sync(config: HealthSparqProjectConfig, curr_date: str) -> NormalizeResult:
    """Synchronous wrapper for run_normalize."""
    normalize_config = NormalizeConfig(
        config=config,
        curr_date=curr_date,
    )
    return run_normalize(normalize_config)

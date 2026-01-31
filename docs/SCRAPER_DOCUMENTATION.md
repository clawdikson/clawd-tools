# Baylor Scott & White Scraper Documentation

## Overview

| Field | Value |
|-------|-------|
| Project Name | `audiobee_baylor_scott_white` |
| State Coverage | TX (primary), LA, AR, OK, KS, CO, NM, MS |
| Lines of Business | Commercial, Medicaid |
| Update Frequency | Monthly |
| Site Type | Direct API (carrier site) |

---

## Pipeline Steps

```
0_get_plans.py          → Fetch plan/network configs
        ↓
search_1-v4.py          → Search all ZIP/specialty combinations
        ↓
get_provider_details_2.py → Fetch individual provider details
        ↓
3_map_json_to_ideon_format.py → Map to Ideon JSONL format
        ↓
generate_qa_files       → Type check, samples, comparison
        ↓
21_get_dropped_npis.py  → Recover dropped NPIs from previous run
        ↓
3_map_json_to_ideon_format.py → Re-map with recovered providers
        ↓
generate_all_qa_files   → Final QA + compress + report
```

Run complete pipeline: `python run_all.py`

---

## API Details

### Base URL
```
https://portal.swhp.org
```

### Search Endpoint

**POST** `/api/v1/DoctorSearch/GetDoctorList`

**Request Payload:**
```json
{
  "networkCode": "PHCS_SA",
  "wholeNamePrefix": "",
  "zipOrCity": "76104",
  "longitude": "-97.4104811",
  "latitude": "33.2867818",
  "stateCode": "TX",
  "maxFetch": 300,
  "specialty": "'Family Medicine'",
  "maxDistance": 100
}
```

| Parameter | Description |
|-----------|-------------|
| `networkCode` | Network code (BSWPLUS_HMO, BSWPLUS_PPO, PHCS_SA, etc.) |
| `wholeNamePrefix` | Name or NPI search term |
| `zipOrCity` | ZIP code filter (optional if using coordinates) |
| `longitude/latitude` | Coordinate-based search (alternative to ZIP) |
| `stateCode` | State filter (TX) |
| `maxFetch` | Max results per request (300) |
| `specialty` | Specialty filter, single-quoted (e.g., `'Family Medicine'`) |
| `maxDistance` | Search radius in miles |

**Response Structure:**
```json
{
  "tier1_Doctor_List": [
    {
      "npiId": "1234567890",
      "providerId": "ABC123",
      "fullName": "John Smith MD",
      "tableCode": "...",
      "addresses": [...],
      "specialties": [...],
      "distance": 5.2
    }
  ],
  "tier2_Doctor_List": [...]
}
```

### Details Endpoint

**GET** `/api/v2/DoctorSearch/GetProviderDetail`

**Query Parameters:**
```
?address=
&limitation=
&networkCode=*
&npi_id={npi}
&origin_latitude=
&origin_longitude=
&primary_specialty=
&provider_id={providerId}
&tableCode=*
```

**Response includes:**
- Full provider info (name, NPI, gender, degree)
- All addresses with phones, lat/lng
- All network affiliations
- Specialties list
- Languages, PCP status, accepting new patients
- Group and hospital affiliations

---

## Search Strategy

The scraper uses a **3-phase coverage strategy** to ensure complete provider discovery:

### Phase 1: Low-Count Specialties
- State-wide search (no ZIP/coordinate filter)
- Specialties with fewer providers are searched across all of Texas
- Example: Pediatric Cardiology, Neurological Surgery

### Phase 2: Low-Count ZIPs
- All specialties searched in sparse/rural areas
- ZIPs with historically low provider counts
- Searches without specialty filter to get all providers

### Phase 3: High-Count ZIPs + Specialties
- Dense urban area and common specialty combinations
- ZIP codes like Dallas, Houston, Austin metro areas
- Combined with high-volume specialties (Family Medicine, Internal Medicine)

**Deduplication:** NPIs collected across all searches are merged in the mapping phase.

---

## Networks

### Commercial Networks

| Code | Description |
|------|-------------|
| `BSWPLUS_HMO` | BSW Plus HMO-Group |
| `BSWPLUS_HMO_INDV` | BSW Plus HMO-Individual/Family |
| `BSWPLUS_PPO` | BSW Plus PPO-Group |
| `BSWPLUS_PPO_INDV` | BSW Plus PPO-Individual/Family |
| `BSWPLUS_ACCESS` | BSW Access PPO |
| `PHCS_SA` | PHCS/Capital RX - PPO Network - Out-of-Area |

### Medicaid Networks

| Code | Description |
|------|-------------|
| `RSM` | RightCare STAR Medicaid Network |

---

## Mapping (Normalization)

**Input:** Search JSON files from `{CURR_DATE}/raw/search/`

**Output:** `{PROJECT_NAME}-{CURR_DATE}.jsonl`

### Ideon Format Fields

```json
{
  "networks": [{"name": "Commercial - BSW Plus HMO-Group", "tier": null}],
  "provider": {
    "unparsed_name": "John Smith",
    "first_name": "John",
    "middle_name": null,
    "last_name": "Smith",
    "npi": "1234567890",
    "gender": "M",
    "title": "MD",
    "provider_type": "individual",
    "facility_name": null,
    "license_number": null
  },
  "addresses": [{
    "street_line_1": "123 Main St",
    "city": "Dallas",
    "state": "TX",
    "zip": "75201",
    "phones": [{"type": "phone", "value": "214-555-1234"}],
    "languages": [{"name": "English", "type": "primary"}],
    "pcp": true,
    "accepting_new_patients": true
  }],
  "specialties": [{"name": "Family Medicine"}],
  "group_affiliations": [{"name": "BSW Medical Group"}],
  "hospital_affiliations": [{"name": "Baylor University Medical Center"}]
}
```

### NPI Merge Logic

Records with the same NPI are merged:
- Networks combined (deduplicated by name)
- Addresses combined (deduplicated by address_string)
- Specialties, group affiliations, hospital affiliations combined

Providers without NPI are written to a separate file and appended at the end.

---

## AutoQA: Compare and Download Dropped NPIs

### Workflow (`21_get_dropped_npis.py`)

1. **Load Current Run:** Read NPIs from `{CURR_DATE}/processed/*.jsonl`
2. **Load Previous Run:** Read NPIs from `{PREV_DATE}/processed/*.jsonl`
3. **Calculate Dropped:** `dropped_npis = prev_providers - curr_providers`
4. **Recovery Process:**
   - For each dropped NPI, search the API
   - Try multiple networks: BSWPLUS_HMO, BSWPLUS_PPO, PHCS_SA
   - If found, fetch provider details
   - Save as `{providerId}_missing.json`
5. **Re-map:** Run mapping again to include recovered providers

### Search Strategy for Dropped NPIs

| Network | Search Method |
|---------|---------------|
| BSW networks | Search by NPI in `wholeNamePrefix` |
| PHCS_SA | Search by provider name (NPI search doesn't work) |

---

## Directory Structure

```
audiobee_baylor_scott_white/
├── config.py                     # Configuration (dates, workers, coordinates)
├── run_all.py                    # Main pipeline runner
├── 0_get_plans.py               # Fetch plan configs
├── search_1-v4.py               # Search phase
├── get_provider_details_2.py    # Details phase
├── 3_map_json_to_ideon_format.py # Mapping phase
├── 21_get_dropped_npis.py       # AutoQA recovery
├── api_client.py                # API helper functions
├── data/
│   ├── plans/                   # Plan/network JSON configs
│   │   ├── Commercial.json
│   │   ├── Medicaid.json
│   │   └── Medicare.json
│   ├── specialties.json         # Specialty list
│   ├── low_count_specialties.json
│   └── high_count_zips.json
├── {CURR_DATE}/
│   ├── raw/
│   │   ├── search/              # Search JSON results
│   │   └── providers/           # Provider details JSON
│   └── processed/               # Final JSONL output
│       ├── {PROJECT}-{DATE}.jsonl
│       ├── {PROJECT}-comparison-{DATE}.xlsx
│       └── {PROJECT}-sample-{DATE}.xlsx
└── {PREV_DATE}/                 # Previous run for comparison
```

---

## Configuration (`config.py`)

```python
PREV_DATE = "20250910"           # Previous run date
CURR_DATE = "20251210"           # Current run date
PROJECT_NAME = "audiobee_baylor_scott_white"
MAX_WORKERS = 25                 # Concurrent requests

# States to include in output
REQ_STATES = ["TX", "LA", "AR", "OK", "KS", "CO", "NM", "MS"]
```

### Geographic Coordinates

14 strategic coordinates cover Texas for coordinate-based searches:
- Amarillo area (zip_1)
- Houston area (zip_2)
- Lubbock area (zip_3)
- El Paso area (zip_4)
- And 10 more covering the state

---

## Proxy Configuration

### Primary: SmartProxy
```python
def get_proxy_url(session_id="session_1", lifetime=1):
    return f"http://smart-{user}_area-US_life-{lifetime}_session-{session_id}:{pass}@us.smartproxy.net:3120"
```

### Fallback: DataImpulse
```python
PROXY_URL = "http://{user}:{pass}@gw.dataimpulse.com:823"
```

### Session Management

The `ProxySessionManager` class:
- Maintains pool of proxy session IDs
- Tracks blocked IDs (HTTP 204 = proxy blocked)
- Auto-generates replacement sessions when blocked
- Uses `curl_cffi` for browser impersonation (chrome136)

---

## Running the Scraper

### Full Pipeline
```bash
cd audiobee_baylor_scott_white
python run_all.py
```

### Individual Steps
```bash
python 0_get_plans.py              # Fetch plans (rarely needed)
python search_1-v4.py              # Run searches
python get_provider_details_2.py   # Get details
python 3_map_json_to_ideon_format.py  # Map to JSONL
python 21_get_dropped_npis.py      # Recover dropped NPIs
```

### Before Running

1. Update `CURR_DATE` and `PREV_DATE` in `config.py`
2. Ensure previous run data exists in `{PREV_DATE}/processed/`
3. Check proxy credentials are valid

### Output

Final file: `{CURR_DATE}/processed/audiobee_baylor_scott_white-{CURR_DATE}.jsonl`

---

## QA Functions

Called automatically by `run_all.py`:

| Function | Description |
|----------|-------------|
| `type_checker` | Validates data types in JSONL |
| `sample_generator` | Creates Excel samples for manual review |
| `comparison_creator` | Generates comparison with previous run |
| `compress_folder_to_7z` | Archives processed folder |
| `report_generator` | Creates summary report |

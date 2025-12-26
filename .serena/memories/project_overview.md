# Ideon Scraping Project Overview

## Purpose
This is a **monorepo containing 95+ web scrapers** for extracting provider directory data from insurance carrier websites. Each scraper targets a specific insurance plan/carrier and extracts provider information (NPIs, names, specialties, locations, network affiliations) for healthcare data aggregation and compliance reporting.

## Project Structure

```
scraping/
├── audiobee_*/              # 95+ individual scraper projects (main content)
│   ├── config.py            # Configuration (URLs, params, network IDs, dates)
│   ├── index_1.py           # Phase 1: Search/Discovery
│   ├── index_2.py           # Phase 2: Detail extraction
│   ├── index_3.py           # Phase 3: Data mapping/normalization
│   ├── run_all.py           # Orchestrator script
│   └── YYYYMMDD/            # Date-versioned output directories
│       ├── raw/             # Raw API responses (JSON/JSONL)
│       └── processed/       # Normalized output files
├── healthsparq-server/      # Node.js browser automation server (port 1018)
├── output_generator/        # Shared QA utilities (validation, reports, comparison)
├── docs/                    # Project documentation
├── data/                    # Shared reference data (specialties, ZIP codes)
└── PLAN.md                  # Infrastructure scaling plan
```

## Site Types (7 Categories)

| Type | Count | Tech | Examples |
|------|-------|------|----------|
| Carrier | 35 | Direct REST API (httpx/requests) | audiobee_bcbs_ma, audiobee_florida_blue |
| Healthsparq | 24 | Browser automation via healthsparq-server | audiobee_mvp_health, audiobee_medica |
| Sapphire | 15 | ProviderFinderOnline API | audiobee_bcbs_il, audiobee_molina |
| Anthem | 4 | Multi-phase with Camoufox | audiobee_anthem, audiobee_amerigroup |
| HealthTrioConnect | 2 | Node.js + Python hybrid | audiobee_jefferson_health |
| Werally | 2 | UHC platform, grid search | audiobee_uhc_medicaid |
| Provider Lenz | 1 | Anti-bot + captcha solving | audiobee_elderplan |

## Pipeline Architecture

Each scraper follows a 3-4 phase pattern:
1. **Phase 1 (index_1.py)**: Discovery - paginated searches, cache raw responses
2. **Phase 2 (index_2.py)**: Detail extraction - fetch individual records
3. **Phase 3 (index_3.py)**: Normalization - map to standard schema, dedupe by NPI
4. **Orchestrator (run_all.py)**: Sequential phase execution

## Output Schema

All scrapers produce normalized JSONL with fields: npi, first_name, last_name, specialty, address_line_1, city, state, zip, phone, network_id, accepting_new_patients

## Execution Model
- **Manual runs** as needed (not automated/scheduled)
- **Parallel execution** using `tools/run_parallel.py` for API-type scrapers
- **Date versioning** via PREV_DATE/CURR_DATE in config.py

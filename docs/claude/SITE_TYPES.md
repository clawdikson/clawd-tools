# Site Type Architecture

Projects are categorized by the underlying provider directory platform.

## 1. Carrier (32 projects)

**Direct API Integration** - REST APIs with minimal browser automation

```
Examples: audiobee_florida_blue, audiobee_multiplan, audiobee_harvard_pilgrim
Pattern:  config.py -> index_1.py (search) -> index_2.py (details) -> index_3.py (map)
Tech:     httpx/requests, async pagination, NPI-based deduplication
```

**Characteristics**:

- Direct REST API calls (JSON responses)
- API keys/headers in config.py
- Geographic grid search (lat/lng + radius)
- Network ID-based plan filtering

## 2. HealthSparq (23 projects)

**Importable Library v2.0** - Standalone package with CLI + library interface

```
Examples: medica_sg, christus_health_plan, excellus
Pattern:  python -m healthsparq run <project> --curr YYYYMMDD (CLI)
          from healthsparq import run_scraper_sync (library)
Tech:     ResilientBrowserSession (core/session), async HealthSpark API wrapper
```

**Characteristics**:

- Dual interface: CLI tool + importable library with custom mapper injection
- Uses `core/session.ResilientBrowserSession` for authentication
- Two-step session pattern: browser auth -> fast HTTP API calls
- Configuration-driven via YAML files in `healthsparq/configs/`
- Three-phase pipeline: search -> details -> normalize (customizable via MapperFunc)
- Project scaffolding templates in `healthsparq/templates/`

**Architecture**:

- `healthsparq/api.py`: High-level API (`run_scraper_sync`, `ScraperResult`)
- `healthsparq/phases/normalize.py`: Supports custom mapper injection (`MapperFunc`)
- `healthsparq/templates/`: Project scaffolding (run.py, mapper.py, .env.example)
- `healthsparq/core/exceptions.py`: Structured exception hierarchy
- Public API exports: `run_scraper`, `default_mapper`, `load_config`, `MapperFunc`

**CLI Usage**:

```bash
python -m healthsparq list                          # List 23 available projects
python -m healthsparq validate christus_health_plan # Validate config
python -m healthsparq run christus_health_plan --curr 20251226 --prev 20251126
python -m healthsparq run medica_sg --curr 20251226 --phase 1  # Run specific phase
python -m healthsparq run medica_sg --curr 20251226 --validate # Enable schema validation
python -m healthsparq doctor                                   # Validate all configs
```

**Library Usage**:

```python
from healthsparq import load_config, run_scraper_sync, default_mapper

# Use default mapper
config = load_config("christus_health_plan")
result = run_scraper_sync(config, "20251227")

# Use custom mapper
def my_mapper(raw: dict) -> dict:
    result = default_mapper(raw)
    # Add custom logic here
    return result

result = run_scraper_sync(config, "20251227", mapper=my_mapper)

# Enable JSON schema validation
result = run_scraper_sync(config, "20251227", validate=True)
validation_errors = result.phase_results[3].data.get("validation_errors", 0)
```

## 3. Sapphire (14 projects)

**ProviderFinderOnline Platform** - Standardized API structure

```
Examples: audiobee_bcbs_il, audiobee_molina, audiobee_bcbs_la
Pattern:  config.py -> faceted search -> provider details -> location enrichment
Tech:     providerfinderonline.com API, network_id filtering
```

**Characteristics**:

- Standardized providerfinderonline.com API endpoints
- Faceted search with specialty/location filters
- Location enrichment for complete address data
- Network ID-based filtering

## 4. Anthem (3 projects)

**Wellpoint Infrastructure** - Multi-phase with intelligent filtering

```
Examples: audiobee_anthem, audiobee_amerigroup, audiobee_healthy_blue
Pattern:  search -> filter -> details -> affiliations -> networks
Tech:     Brand-specific URLs, complex network hierarchies
```

**Characteristics**:

- Brand-specific URL configurations
- Complex network hierarchy navigation
- Multi-phase data extraction (affiliations, networks)
- Intelligent filtering for data refinement

## 5. HealthTrioConnect (2 projects)

**Node.js + Python Hybrid** - Browser automation with Python processing

**Characteristics**:

- Node.js for browser automation (Puppeteer/Playwright)
- Python for data processing and normalization
- Cross-language coordination required

## 6. Werally (3 projects)

**UHC Platform** - Grid-based geographic search

**Characteristics**:

- UnitedHealthcare platform integration
- Grid-based geographic search patterns
- Systematic coverage of service areas

## 7. Provider Lenz (1 project)

**Anti-Bot Protected** - Requires captcha solving

**Characteristics**:

- Advanced anti-bot protection
- Captcha solving integration required
- Rate limiting considerations

# Project Overview

This repository contains **~86 web scrapers** for extracting provider directory data from insurance carrier websites. Each scraper targets a specific insurance plan/carrier and extracts provider information (NPIs, names, specialties, locations, network affiliations) for healthcare data aggregation.

**Purpose**: Collect and standardize provider network data from insurance carrier directories for downstream analytics and compliance reporting.

**Execution Model**: Manual runs as needed (not automated/scheduled).

---

## Project Structure

```
scraping/
├── audiobee_*/              # ~86 individual scraper projects
│   ├── config.py            # Configuration (URLs, params, network IDs)
│   ├── index_1.py           # Phase 1: Search/Discovery
│   ├── index_2.py           # Phase 2: Detail extraction
│   ├── index_3.py           # Phase 3: Data mapping/normalization
│   ├── run_all.py           # Orchestrator script
│   ├── shared_package/      # Optional: Local shared utilities
│   ├── YYYYMMDD/            # Date-versioned output directories
│   │   ├── raw/             # Raw API responses (JSON/JSONL)
│   │   └── processed/       # Normalized output files
│   └── CLAUDE.md            # Project-specific metadata (if present)
│
├── healthsparq/             # HealthSparq library v2.0 (importable + CLI)
│   ├── __init__.py          # Public API exports
│   ├── cli.py               # Typer-based CLI commands
│   ├── api.py               # High-level scraper API
│   ├── configs/             # Project YAML files (23 projects)
│   ├── core/                # Core scraping logic
│   ├── phases/              # Execution phases
│   ├── templates/           # Project scaffolding templates
│   └── tests/               # Test suite (99+ tests)
│
├── core/                    # Shared package v3.0 (git submodule)
│   ├── config/              # Pydantic Settings-based configuration
│   ├── io/                  # DataStore abstraction + SQLiteFS/JSONL
│   ├── logging/             # Loguru-based logging
│   ├── validation/          # Pydantic models for provider data
│   ├── proxy/               # Multi-provider proxy orchestration
│   ├── session/             # Browser/HTTP session management
│   └── mapper/              # Provider data normalization
│
├── output_generator/        # Shared QA utilities
│   ├── type_check.py        # Output schema validation
│   ├── sample_generator.py  # Sample data extraction
│   ├── comparison_creator.py # Cross-run diff analysis
│   └── report_generator.py  # Excel report generation
│
├── tools/                   # Execution and automation tools
│   └── run_parallel.py      # Parallel scraper execution
│
├── projects/                # Project categorization
│   └── api.txt              # API-type scrapers (37 projects)
│
├── docs/                    # Project documentation
│   ├── onboarding/          # Core technical guides
│   ├── extra/               # Advanced reference docs
│   └── implementation_research/  # Shared utilities research
│
├── data/                    # Shared reference data
│   ├── specialties.json     # Specialty code mappings
│   └── us_zip_fips_county.xlsx  # Geographic reference
│
├── todos/                   # Task tracking (completed P1 issues)
│
├── .beads/                  # Beads issue tracking (AI-native)
│
└── AGENTS.md                # Agent workflow instructions
```

---

## Site Type Summary

Projects are categorized by the underlying provider directory platform:

| Site Type         | Projects | Description                           | Technology                               |
| ----------------- | -------- | ------------------------------------- | ---------------------------------------- |
| Carrier           | 32       | Direct REST API integration           | httpx/requests, async pagination         |
| HealthSparq       | 23       | Importable library v2.0 + CLI         | ResilientBrowserSession, YAML config     |
| Sapphire          | 14       | ProviderFinderOnline platform         | providerfinderonline.com API             |
| Anthem            | 3        | Wellpoint infrastructure, multi-phase | Brand-specific URLs, network hierarchies |
| HealthTrioConnect | 2        | Node.js + Python hybrid               | Browser automation + Python              |
| Werally           | 3        | UHC platform, grid-based search       | Geographic grid search                   |
| Provider Lenz     | 1        | Anti-bot protected                    | Captcha solving required                 |

For detailed patterns, see @docs/claude/SITE_TYPES.md

---

## Key Files Reference

| File         | Purpose                                          |
| ------------ | ------------------------------------------------ |
| `config.py`  | Project configuration (URLs, params, dates)      |
| `index_1.py` | Phase 1: Search/discovery                        |
| `index_2.py` | Phase 2: Detail extraction                       |
| `index_3.py` | Phase 3: Data normalization                      |
| `run_all.py` | Pipeline orchestrator                            |
| `PLAN.md`    | Infrastructure scaling implementation plan       |
| `CLAUDE.md`  | Project metadata (site type, coverage, approval) |

---

## Coverage Types

| Type                   | Description           | Example Projects                           |
| ---------------------- | --------------------- | ------------------------------------------ |
| **Medicare Advantage** | Senior plans (65+)    | audiobee_anthem, audiobee_humana           |
| **Medicaid**           | State-funded programs | audiobee_uhc_medicaid, audiobee_amerigroup |
| **ACA**                | Marketplace plans     | audiobee_florida_blue, audiobee_bcbs_il    |
| **Large Group**        | Employer plans        | audiobee_multiplan                         |

---

## Documentation Organization

Documentation is organized by audience and complexity level:

### Core Technical Guides (docs/onboarding/)

Start here for essential project knowledge:

- **INDEX.md** - Documentation navigation hub with role-based guidance
- **ARCHITECTURE.md** - Complete system architecture with diagrams
- **PIPELINE.md** - Detailed pipeline phase specifications
- **SITE_TYPES_REFERENCE.md** - Platform-specific implementation patterns
- **DEVELOPER_GUIDE.md** - Complete onboarding guide for new developers
- **TROUBLESHOOTING.md** - Diagnostic flowcharts and problem resolution
- **GLOSSARY.md** - Healthcare and technical terminology reference
- **IMPROVEMENTS.md** - Prioritized code improvement recommendations (P0-P3)

### Advanced Reference (docs/extra/)

For experienced developers and technical leadership:

- **EXPERT_REVIEW.md** - Review summary from 27 domain experts
- **PLAN.md** - Infrastructure scaling plan (95 to 190 scrapers)
- **SCALABILITY_BEST_PRACTICES.md** - Parallel execution patterns
- **SHARED_UTILS_IMPLEMENTATION.md** - Shared utilities framework design

### Documentation by Role

| Role                   | Recommended Path                                                                           |
| ---------------------- | ------------------------------------------------------------------------------------------ |
| New Developers         | GLOSSARY.md -> ARCHITECTURE.md -> DEVELOPER_GUIDE.md -> TROUBLESHOOTING.md                 |
| Experienced Developers | PIPELINE.md -> SITE_TYPES_REFERENCE.md -> IMPROVEMENTS.md -> SCALABILITY_BEST_PRACTICES.md |
| Technical Leadership   | ARCHITECTURE.md -> EXPERT_REVIEW.md -> implementation_research/ -> PLAN.md                 |
| Operations             | TROUBLESHOOTING.md -> DEVELOPER_GUIDE.md -> quick-reference.md                             |

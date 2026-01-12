# Project Structure

Detailed project structure for the Ideon Scraping repository.

```
scraping/
├── audiobee_*/              # ~86 individual scraper projects
│   ├── config.py            # Configuration (URLs, params, network IDs)
│   ├── index_1.py           # Phase 1: Search/Discovery
│   ├── index_2.py           # Phase 2: Detail extraction
│   ├── index_3.py           # Phase 3: Data mapping/normalization
│   ├── run_all.py           # Orchestrator script
│   ├── shared_package/      # Optional: Local shared utilities (session management)
│   │   ├── session/         # BrowserSession, ResilientBrowserSession (Patchright/curl_cffi)
│   │   ├── config.py        # Proxy configuration with dotenv
│   │   └── localdataclass/  # Response objects
│   ├── YYYYMMDD/            # Date-versioned output directories
│   │   ├── raw/             # Raw API responses (JSON/JSONL)
│   │   └── processed/       # Normalized output files
│   └── CLAUDE.md            # Project-specific metadata (if present)
│
├── audiobee_anthem_new/     # Advanced Anthem scraper with alternative architectures
│   ├── task_server/         # Two-process architecture (FastAPI + browser pool)
│   ├── browser/             # Camoufox browser automation with request interception
│   ├── single_process_implementation/  # Alternative unified architecture
│   │   ├── unified_scraper.py          # Main entry point (asyncio.Queue)
│   │   ├── provider_searcher.py        # Provider search logic
│   │   ├── state_processor.py          # State processing
│   │   ├── injection_unified.html      # JS injection (page.expose_function)
│   │   └── src/                        # Shared utilities
│   ├── ANTHEM_IMPROVEMENT.md           # Architectural analysis
│   └── SINGLE_PROCESS_PLAN.md          # Single-process implementation plan
│
├── healthsparq/             # HealthSparq library v2.0 (importable + CLI + project templates)
│   ├── __init__.py          # Public API exports (run_scraper_sync, default_mapper, load_config)
│   ├── __main__.py          # CLI entry point (python -m healthsparq)
│   ├── cli.py               # Typer-based CLI commands (list, validate, run, doctor)
│   ├── api.py               # High-level scraper API (run_scraper_sync, ScraperResult)
│   ├── config/              # Configuration system
│   │   ├── schema.py        # Pydantic models for project configuration
│   │   └── loader.py        # YAML configuration loading with validation
│   ├── configs/             # Project YAML files (23 HealthSparq projects)
│   │   ├── _base.yaml       # Shared defaults for all projects
│   │   ├── christus_health_plan.yaml
│   │   ├── medica_sg.yaml
│   │   └── ...              # 20+ additional project configs
│   ├── core/                # Core scraping logic
│   │   ├── __init__.py      # Core module exports
│   │   ├── healthspark.py   # HealthSpark API wrapper (async context manager)
│   │   ├── session.py       # Session management (browser auth + HTTP)
│   │   ├── exceptions.py    # Custom exception hierarchy
│   │   └── file_writer.py   # Async file writing with worker pool
│   ├── phases/              # Execution phases (search, details, normalize)
│   │   └── normalize.py     # Supports custom mapper injection via MapperFunc
│   ├── templates/           # Project scaffolding templates
│   │   ├── run.py.template          # Typer CLI importing healthsparq library
│   │   ├── mapper.py.template       # Custom mapper extending default_mapper()
│   │   ├── pyproject.toml.template  # Python packaging with uv editable dependency support
│   │   ├── requirements.txt.template # Pip-based dependency management
│   │   ├── .env.example             # Environment config template
│   │   ├── .gitignore.template      # Output directory ignores
│   │   └── README.md.template       # Usage instructions with uv installation guide
│   ├── tests/               # Test suite (99+ tests)
│   ├── CLAUDE.md            # Package documentation and conventions
│   ├── README.md            # Package documentation
│   └── pyproject.toml       # Python package metadata (v2.0.0)
│
├── healthsparq-server/      # Legacy browser automation server (deprecated - use healthsparq package instead)
│   ├── server.js            # Node.js/Puppeteer server (port 1018)
│   └── CLAUDE.md            # Server documentation
│
├── output_generator/        # Legacy QA utilities (deprecated - use core/qa instead)
│   └── CLAUDE.md            # Migration documentation
│
├── tools/                   # Execution and automation tools
│   └── run_parallel.py      # Parallel scraper execution with retry logic
│
├── scripts/                 # Development and setup scripts
│   ├── clone-submodules.sh  # Submodule management (init/update/fresh/shallow/standalone)
│   ├── sync-submodules.sh   # Sync submodules to recorded SHAs
│   └── bump-submodules.sh   # Bump submodules to explicit tags/branches
│
├── projects/                # Project categorization for parallel execution
│   └── api.txt              # API-type scrapers (37 Carrier projects)
│
├── core/                    # Shared package v3.0 (git submodule, formerly shared_package/)
│   ├── config/              # Pydantic Settings-based configuration
│   ├── io/                  # DataStore abstraction + SQLiteFS/JSONL utilities
│   │   ├── base.py          # DataStore Protocol + BackendType enum
│   │   ├── factory.py       # create_store() factory with auto-detection
│   │   ├── json_files.py    # JSONFileStore - individual JSON files
│   │   ├── jsonl.py         # JSONLStore wrapper + JSONL I/O with BoundedSet deduplication
│   │   ├── sqlite_fs.py     # SQLiteStore wrapper + SQLiteFS virtual filesystem (15x faster)
│   │   └── SQLITE_FS.md     # SQLiteFS usage documentation
│   ├── logging/             # Loguru-based logging
│   ├── validation/          # Pydantic models for provider data
│   ├── proxy/               # Multi-provider proxy orchestration
│   ├── session/             # Browser/HTTP session management
│   ├── mapper/              # Provider data normalization and mapping
│   │   ├── base.py          # BaseMapper ABC, MapperResult, MapperFunc type
│   │   ├── normalize.py     # Normalization utilities (ZIP, phone, address, gender)
│   │   ├── dedup.py         # NPI-based deduplication with record merging
│   │   ├── schema.py        # JSON Schema validation
│   │   ├── healthsparq.py   # HealthSparq mapper (v2 format, 23 projects)
│   │   ├── carrier.py       # Carrier mapper base (custom API structures)
│   │   └── README.md        # Mapper usage documentation
│   ├── qa/                  # QA utilities v1.0 (migrated from output_generator)
│   │   ├── __init__.py      # Public API: validate, compare, sample, report, generate_debug_reports
│   │   ├── __main__.py      # CLI entry point
│   │   ├── base.py          # QAResult, QAOutcome, QAStatus, exception hierarchy
│   │   ├── config.py        # QASettings (Pydantic Settings)
│   │   ├── validator.py     # Schema validation with fastjsonschema (100x faster)
│   │   ├── comparison.py    # Cross-run diff analysis with Polars (10x faster)
│   │   ├── sampler.py       # Reservoir sampling with archive creation
│   │   ├── reporter.py      # Excel state reports with xlsxwriter streaming
│   │   ├── statistics.py    # State-level provider counts
│   │   ├── debug_reports.py # Debug Excel report generation (12 sheets + specialty pivot)
│   │   ├── cli.py           # Typer CLI framework
│   │   └── README.md        # QA module documentation
│   ├── data/                # Shared reference data with cached loading
│   │   ├── __init__.py      # Public exports for data loaders
│   │   ├── loader.py        # @cache decorators for lazy-loaded data
│   │   ├── output_json_schema.json  # Provider output schema
│   │   ├── uszips.xlsx      # ZIP-to-state mapping
│   │   └── us_states_coordinates.json  # State geographic data
│   ├── tests/test_mapper.py # Mapper test suite
│   └── CLAUDE.md            # Package documentation
│
├── docs/                    # Project documentation
│   ├── onboarding/          # Core technical guides
│   │   ├── INDEX.md         # Documentation navigation hub
│   │   ├── ARCHITECTURE.md  # Complete system architecture
│   │   ├── PIPELINE.md      # Pipeline phase specifications
│   │   ├── SITE_TYPES_REFERENCE.md  # Platform-specific patterns
│   │   ├── DEVELOPER_GUIDE.md       # Onboarding guide
│   │   ├── TROUBLESHOOTING.md       # Diagnostic procedures
│   │   ├── GLOSSARY.md      # Healthcare/technical terminology
│   │   └── IMPROVEMENTS.md  # Code improvement recommendations (P0-P3)
│   ├── extra/               # Advanced reference docs
│   │   ├── EXPERT_REVIEW.md # 27-expert review summary
│   │   ├── PLAN.md          # Infrastructure scaling plan
│   │   ├── SCALABILITY_BEST_PRACTICES.md  # Parallel execution patterns
│   │   └── SHARED_UTILS_IMPLEMENTATION.md # Shared utilities design
│   ├── implementation_research/  # Shared utilities research
│   ├── restructuring/       # SQLite migration documentation
│   │   └── SQLITE_STORAGE_STRATEGY.md     # SQLite technical rationale
│   ├── CHANGELOG.md         # Recent enhancements and implementation details
│   ├── PROJECT_STRUCTURE.md # This file
│   ├── README.md            # Main documentation hub
│   ├── site-type-mapping.md # Projects by infrastructure type
│   └── quick-reference.md   # Common operations guide
│
├── data/                    # Shared reference data
│   ├── specialties.json     # Specialty code mappings
│   └── us_zip_fips_county.xlsx  # Geographic reference
│
├── todos/                   # Task tracking (P1 issues completed)
│   ├── 003-completed-p1-sqlite-commit-per-write.md
│   ├── 006-completed-p1-jsonl-append-quadratic.md
│   ├── 007-completed-p1-sync-io-in-async.md
│   └── 008-completed-p1-missing-context-manager.md
│
├── .beads/                  # Beads issue tracking (AI-native, git-synced)
│   ├── README.md            # Beads introduction and quick start
│   ├── config.yaml          # Beads configuration
│   ├── issues.jsonl         # Issue database (git-tracked with custom merge driver)
│   └── .gitignore           # Beads-specific ignores
│
├── AGENTS.md                # Agent workflow instructions (landing-the-plane checklist)
└── .gitattributes           # Custom merge driver for .beads/issues.jsonl
```

## Site Type Summary

| Type              | Projects | Description                             |
| ----------------- | -------- | --------------------------------------- |
| Carrier           | 32       | Direct REST API integration             |
| HealthSparq       | 23       | Unified library (python -m healthsparq) |
| Sapphire          | 14       | ProviderFinderOnline platform           |
| Anthem            | 3        | Wellpoint infrastructure, multi-phase   |
| HealthTrioConnect | 2        | Node.js + Python hybrid                 |
| Werally           | 3        | UHC platform, grid-based search         |
| Provider Lenz     | 1        | Anti-bot protected, requires captcha    |

See `docs/by-site-type/` for detailed platform-specific patterns.

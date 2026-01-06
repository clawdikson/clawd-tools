# Ideon Scraping

Healthcare provider directory scraping system with ~86 web scrapers for extracting provider data from insurance carrier websites.

## Overview

This repository extracts provider information (NPIs, names, specialties, locations, network affiliations) from insurance carrier directories for healthcare data aggregation and compliance reporting.

**Execution Model**: Manual runs as needed (not automated/scheduled).

## Quick Start

```bash
# Clone repository with submodules
git clone --recurse-submodules https://bitbucket.org/productaudiobee/scraping-base.git
cd scraping

# Install dependencies (choose one)
uv pip install -e .          # Recommended (fastest)
pip install -e .             # Standard pip

# Copy environment template and configure
cp .env.example .env
# Edit .env with your proxy credentials

# Run a scraper
cd audiobee_bcbs_il
python run_all.py            # Run all phases
# Or run phases individually:
python index_1.py            # Phase 1: Search/Discovery
python index_2.py            # Phase 2: Detail extraction
python index_3.py            # Phase 3: Normalization
```

## Project Structure

```
scraping/
├── audiobee_*/          # ~86 individual scraper projects
├── healthsparq/         # HealthSparq library v2.0 (23 projects)
├── core/                # Shared utilities (git submodule)
├── tools/               # Execution and automation tools
├── docs/                # Documentation
└── .beads/              # AI-native issue tracking
```

## Running HealthSparq Scrapers

```bash
# List available projects
python -m healthsparq list

# Run a scraper
python -m healthsparq run medica_sg --curr 20251226 --prev 20251110

# Validate configuration
python -m healthsparq validate christus_health_plan
python -m healthsparq doctor    # Validate all configs
```

## Running Scrapers in Parallel

```bash
# Run API scrapers in parallel
python tools/run_parallel.py --list projects/api.txt --workers 8 --curr 20251210 --prev 20251110

# Run scrapers by pattern
python tools/run_parallel.py --pattern "audiobee_bcbs*" --workers 8 --curr 20251210 --prev 20251110
```

## Validating Output

```bash
# Validate output schema (100x faster with fastjsonschema)
python -m core.qa validate audiobee_bcbs_il/20251227/processed/providers.jsonl

# Compare runs (10x faster with Polars)
python -m core.qa compare --curr 20251227 --prev 20251126 --project audiobee_bcbs_il

# Generate samples
python -m core.qa sample audiobee_bcbs_il/20251227/processed/providers.jsonl --count 10
```

## Uploading Results

```bash
# Upload to Google Drive
python tools/upload_to_drive.py audiobee_bcbs_il

# Send email report with S3 upload
python tools/xlsx_to_clickup.py email audiobee_bcbs_il --to recipient@example.com
```

## Development

### Submodule Setup

```bash
# Standard init/update
./scripts/clone-submodules.sh

# Fresh clone (removes existing)
./scripts/clone-submodules.sh --fresh
```

### Running Tests

```bash
# Run all tests
pytest healthsparq/tests/ -v

# Run with coverage
pytest healthsparq/tests/ --cov=healthsparq --cov-report=html
```

### Code Quality

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Type check
mypy healthsparq/
```

## Issue Tracking

This project uses [Beads](https://github.com/Dicklesworthstone/beads_viewer) for AI-native issue tracking:

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

## Documentation

- [CLAUDE.md](CLAUDE.md) - Comprehensive project documentation for AI agents
- [AGENTS.md](AGENTS.md) - Agent workflow instructions
- [docs/onboarding/](docs/onboarding/) - Developer onboarding guides
- [CODE_STYLE.md](CODE_STYLE.md) - Coding conventions

## License

Proprietary - Audiobee/Ideon

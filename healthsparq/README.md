# HealthSparq Unified Scraper

A unified singleton scraper for all HealthSparq-based provider directories. Replaces 23 individual `audiobee_*` projects with a single, configuration-driven implementation.

## Quick Start

```bash
# List available projects
python -m healthsparq list

# Validate a configuration
python -m healthsparq validate christus_health_plan

# Run a scraper (dry-run first)
python -m healthsparq run christus_health_plan --curr 20251226 --dry-run

# Run for real (requires healthsparq-server)
python -m healthsparq run christus_health_plan --curr 20251226 --prev 20251126
```

## Prerequisites

1. **healthsparq-server**: Browser automation server (Node.js/Puppeteer)

   ```bash
   cd healthsparq-server
   PORT=1018 npm start
   ```

2. **Python dependencies**: Install via requirements
   ```bash
   pip install typer pydantic pyyaml orjson httpx
   ```

## CLI Commands

### `list` - Show available projects

```bash
python -m healthsparq list
python -m healthsparq list --count # Just show count
```

### `validate` - Validate configuration

```bash
python -m healthsparq validate christus_health_plan
python -m healthsparq validate medica_sg
```

### `run` - Execute scraper

```bash
# Required: --curr (current date)
python -m healthsparq run christus_health_plan --curr 20251226

# Optional: --prev (previous date for comparison)
python -m healthsparq run christus_health_plan --curr 20251226 --prev 20251126

# Run specific phase only
python -m healthsparq run christus_health_plan --curr 20251226 --phase 1 # Search only
python -m healthsparq run christus_health_plan --curr 20251226 --phase 2 # Details only
python -m healthsparq run christus_health_plan --curr 20251226 --phase 3 # Normalize only

# Dry run (show what would execute)
python -m healthsparq run christus_health_plan --curr 20251226 --dry-run
```

### `doctor` - Health checks

```bash
python -m healthsparq doctor
```

## Project Structure

```
healthsparq/
├── __init__.py          # Package entry, version
├── __main__.py          # CLI entry point
├── cli.py               # Typer CLI commands
├── config/              # Configuration system
│   ├── schema.py        # Pydantic models
│   └── loader.py        # YAML loading
├── configs/             # Project YAML files (23 projects)
│   ├── _base.yaml       # Shared defaults
│   ├── christus_health_plan.yaml
│   ├── medica_sg.yaml
│   └── ...
├── core/                # Core scraping logic
│   ├── healthspark.py   # Main HealthSpark class
│   ├── session.py       # HTTP session management
│   └── file_writer.py   # Async file writing
├── phases/              # Execution phases
│   ├── search.py        # Phase 1: Provider search
│   ├── details.py       # Phase 2: Detail extraction
│   └── normalize.py     # Phase 3: Data normalization
├── tests/               # Test suite (99 tests)
└── utils/               # Shared utilities
```

## Configuration

Each project has a YAML configuration file in `healthsparq/configs/`:

```yaml
project:
  name: Christus Health Plan
  slug: christus_health_plan
  description: Medicare Advantage and ACA plans for LA, NM, TX

site:
  domain: christushealthplan.healthsparq.com
  brand_code: CHRISTUS
  insurer_code: CHRISTUS_I
  api_version: v4

plans:
  - product_code: MA
    name: Medicare Advantage
  - product_code: HIX
    name: Health Insurance Exchange (ACA)

coverage:
  states:
    - LA
    - NM
    - TX

concurrency:
  max_workers: 25
  max_browsers: 25
```

## Available Projects (23)

| Project                        | Domain                                    | States            | Coverage    |
| ------------------------------ | ----------------------------------------- | ----------------- | ----------- |
| alliance_trilogy               | web.healthsparq.com                       | WI,MN,IL,IA,MI    | MA          |
| amerihealth_administrators_pa  | ibx.healthsparq.com                       | PA,NJ             | -           |
| amerihealth_caritas_vip_de     | amerihealthcaritasvipcare.healthsparq.com | DE,FL,PA          | Medicaid    |
| amerihealth_nj                 | web.healthsparq.com                       | NJ,DE,PA          | -           |
| asuris_northwest               | web.healthsparq.com                       | WA,OR,ID,UT       | -           |
| capital_blue                   | capitalbluecross.healthsparq.com          | PA + 7            | ACA         |
| christus_health_plan           | christushealthplan.healthsparq.com        | LA,NM,TX          | MA, ACA     |
| excellus                       | excellusbcbs.healthsparq.com              | NY                | -           |
| first_choice_sc                | selecthealthofsc.healthsparq.com          | SC                | Medicaid    |
| health_plan_nv_medicaid        | hsprov.healthsparq.com                    | NV                | Medicaid    |
| highmark_wholecare             | hmwholecare.healthsparq.com               | PA                | Medicaid    |
| hma                            | web.healthsparq.com                       | WA,OR             | Large Group |
| ibx                            | ibxweb.healthsparq.com                    | PA                | Commercial  |
| maine_community_health_options | healthoptions.healthsparq.com             | ME                | ACA         |
| medica                         | medica.healthsparq.com                    | IA,MN,ND,NE,SD,WI | ACA         |
| medica_sg                      | medica.healthsparq.com                    | WI,MN,ND,SD,IA,NE | ACA         |
| medical_mutual                 | medmutual.healthsparq.com                 | OH                | -           |
| mvp_health                     | mvp.healthsparq.com                       | NY,VT             | ACA         |
| quartz                         | quartz.healthsparq.com                    | WI,MN,IL,IA       | ACA         |
| sentara                        | sentarahealthplans.healthsparq.com        | VA,NC             | MA          |
| tufts_health_plans             | point32health.healthsparq.com             | MA,NH,RI          | -           |
| wellmark                       | web.healthsparq.com                       | IA,SD             | ACA         |
| wellmark_medicare              | web.healthsparq.com                       | IA,SD             | MA          |

## Output

Output is written to `{curr_date}/processed/`:

```
20251226/
├── raw/
│   ├── search_results/     # Phase 1 output
│   └── provider_details/   # Phase 2 output
└── processed/              # Phase 3 output (final)
    └── providers.jsonl     # Normalized provider data
```

## Testing

```bash
# Run all tests
pytest healthsparq/tests/ -v

# Run specific test file
pytest healthsparq/tests/test_config.py -v

# Run with coverage
pytest healthsparq/tests/ --cov=healthsparq
```

## Comparing Outputs

Compare singleton output with legacy output:

```bash
python healthsparq/tests/compare_outputs.py \
  --legacy audiobee_christus_health_plan/20251226/processed \
  --singleton healthsparq/output/christus_health_plan/20251226/processed \
  --threshold 0.99
```

## Migration from Legacy

The following legacy projects are now handled by this singleton:

- `audiobee_alliance_trilogy` → `healthsparq run alliance_trilogy`
- `audiobee_amerihealth_*` → `healthsparq run amerihealth_*`
- `audiobee_christus_health_plan` → `healthsparq run christus_health_plan`
- ... (see full list above)

**Note**: `audiobee_mass_gen` is NOT a HealthSparq project (uses vitalschoice.com) and is not included.

## Development

```bash
# Install dev dependencies
pip install pytest pytest-cov pytest-asyncio

# Run tests
pytest healthsparq/tests/ -v

# Validate all configs
for cfg in healthsparq/configs/*.yaml; do
  python -m healthsparq validate $(basename $cfg .yaml) || exit 1
done
```

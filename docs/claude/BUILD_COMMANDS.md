# Build & Development Commands

Quick reference for running scrapers, parallel execution, and output validation.

## Running a Scraper

```bash
# 1. Navigate to project
cd audiobee_bcbs_il

# 2. Update dates in config.py
PREV_DATE = "20251010"
CURR_DATE = "20251210"

# 3. Run phases sequentially
python index_1.py # Discovery
python index_2.py # Details
python index_3.py # Normalization

# Or use orchestrator
python run_all.py
```

## Parallel Execution

```bash
# Run API scrapers in parallel (from list)
python tools/run_parallel.py --list projects/api.txt --workers 8 --curr 20251210 --prev 20251110

# Run scrapers by pattern
python tools/run_parallel.py --pattern "audiobee_bcbs*" --workers 8 --curr 20251210 --prev 20251110
```

## HealthSparq Projects

```bash
# Install package (one-time)
cd healthsparq && pip install -e .

# List available projects
python -m healthsparq list

# Run scraper
python -m healthsparq run medica_sg --curr 20251226 --prev 20251110

# Run specific phase only
python -m healthsparq run medica_sg --curr 20251226 --phase 1 # Search
python -m healthsparq run medica_sg --curr 20251226 --phase 2 # Details
python -m healthsparq run medica_sg --curr 20251226 --phase 3 # Normalize

# Validate configuration
python -m healthsparq validate christus_health_plan
python -m healthsparq doctor # Validate all configs
```

## Validating Output

```bash
# Check output schema compliance
python output_generator/type_check.py audiobee_bcbs_il/

# Generate diff report vs previous run
python output_generator/comparison_creator.py audiobee_bcbs_il/
```

## Quick Reference

| Command                        | Purpose                          |
| ------------------------------ | -------------------------------- |
| `python index_1.py`            | Phase 1: Discovery/search        |
| `python index_2.py`            | Phase 2: Detail extraction       |
| `python index_3.py`            | Phase 3: Data normalization      |
| `python run_all.py`            | Run all phases sequentially      |
| `python -m healthsparq list`   | List HealthSparq projects        |
| `python -m healthsparq doctor` | Validate all HealthSparq configs |

## See Also

- [PIPELINE.md](../onboarding/PIPELINE.md) - Detailed pipeline phase specifications
- [SITE_TYPES_REFERENCE.md](../onboarding/SITE_TYPES_REFERENCE.md) - Platform-specific patterns
- [TROUBLESHOOTING.md](../onboarding/TROUBLESHOOTING.md) - Diagnostic procedures

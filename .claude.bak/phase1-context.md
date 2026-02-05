# Phase 1 Context: Foundation for core/qa Migration

## Overview

This phase creates the foundation for migrating output_generator utilities to core/qa module.

## Key Directories

- Source: `/Users/dikson/Work/ideon_scraping/scraping/output_generator/`
- Target Data: `/Users/dikson/Work/ideon_scraping/scraping/core/data/`
- Target QA: `/Users/dikson/Work/ideon_scraping/scraping/core/qa/` (new)

## Existing Files in core/data/

- `output_json_schema.json` - Already exists
- `uszips.xlsx` - Already exists

## Files to Copy

- `output_generator/states_coordinates.json` -> `core/data/us_states_coordinates.json`

## Files to Create

### core/data/**init**.py

Public API: get_schema, get_state_coordinates, get_zip_to_state, get_specialties, clear_caches

### core/data/loader.py

Cached reference data loading with @cache decorators for:

- get_schema() - loads output_json_schema.json
- get_state_coordinates() - loads us_states_coordinates.json
- get_zip_to_state() - loads uszips.xlsx (pandas)
- get_specialties() - loads us_specialties.json (optional)
- clear_caches() - clears all caches

### core/qa/**init**.py

Public API exports for QA module

### core/qa/base.py

- QAStatus enum (SUCCESS, WARNING, ERROR, TIMEOUT, SKIPPED)
- QAOutcome dataclass (status, message, warnings, errors, elapsed_seconds)
- QAResult[T] generic dataclass (outcome, metrics, output_files)
- QAError base exception
- ValidationError, ComparisonError, ConfigurationError, QATimeoutError exceptions
- QAToolProtocol
- run_with_timeout helper
- DEFAULT_TIMEOUT_SECONDS = 300

### core/qa/config.py

- QASettings (Pydantic BaseSettings)
- load_qa_config factory function
- load_from_legacy_config adapter

## Design Patterns

- Use `from __future__ import annotations`
- Use functools.cache for caching
- Use orjson for JSON parsing
- Use try/except import pattern for core.logging fallback
- Align with existing core/ patterns (Protocol, Pydantic Settings)

## Reference Files

See plan at: /Users/dikson/Work/ideon_scraping/scraping/plans/feat-output-generator-to-core-qa-migration.md

# Implementation Plan

**Approach**: Phased rollout with backward compatibility
**Total Effort**: ~2-3 weeks for core, ongoing for migration

---

## Phase 0: Foundation (Days 1-2)

### Goal: Create package structure and security fixes

#### Tasks

1. **Create shared/ package structure**
   ```bash
   mkdir -p scraping/shared/{config,io,logging,validation}
   touch scraping/shared/__init__.py
   touch scraping/shared/{config,io,logging,validation}/__init__.py
   ```

2. **Create pyproject.toml**
   ```toml
   # scraping/shared/pyproject.toml
   [project]
   name = "shared"
   version = "0.1.0"
   requires-python = ">=3.12"

   dependencies = [
       "pydantic>=2.0.0",
       "pydantic-settings>=2.0.0",
       "python-dotenv>=1.0.0",
       "orjson>=3.9.0",
       "loguru>=0.7.0",
       "openpyxl>=3.1.0",
       "pandas>=2.0.0",
   ]
   ```

3. **Create .env.template (SECURITY)**
   ```bash
   # Move all hardcoded API keys to this template
   # See 02_CONFIG_SYSTEM.md for full template
   ```

4. **Create .gitignore update**
   ```
   .env
   *.env
   .env.*
   !.env.template
   ```

#### Deliverables
- [ ] `shared/` directory structure
- [ ] `shared/pyproject.toml`
- [ ] `.env.template` with all API keys placeholder
- [ ] Updated `.gitignore`

---

## Phase 1: Configuration System (Days 3-5)

### Goal: BaseConfig with Pydantic Settings

#### Tasks

1. **Implement BaseConfig**
   - Copy from `02_CONFIG_SYSTEM.md`
   - File: `shared/config/base.py`

2. **Implement Site-Type Configs**
   - `shared/config/sapphire.py`
   - `shared/config/healthsparq.py`
   - `shared/config/carrier.py`
   - `shared/config/anthem.py`

3. **Implement Factory Function**
   - `shared/config/factory.py`
   - `load_config()` function

4. **Test with One Project Per Type**
   - Sapphire: `audiobee_bcbs_il`
   - Healthsparq: `audiobee_mvp_health`
   - Carrier: `audiobee_florida_blue`
   - Anthem: `audiobee_amerigroup`

#### Test Commands
```bash
# Test config loading
cd audiobee_bcbs_il
python -c "from shared.config import load_config; c = load_config('sapphire', 'audiobee_bcbs_il'); print(c.dirs)"
```

#### Deliverables
- [ ] `shared/config/base.py`
- [ ] `shared/config/sapphire.py`
- [ ] `shared/config/healthsparq.py`
- [ ] `shared/config/carrier.py`
- [ ] `shared/config/anthem.py`
- [ ] `shared/config/factory.py`
- [ ] `shared/config/__init__.py`
- [ ] Tests pass for 4 representative projects

---

## Phase 2: Logging (Days 6-7)

### Goal: Centralized logger with print() compatibility

#### Tasks

1. **Implement ScraperLogger**
   - Copy from `04_LOGGING.md`
   - File: `shared/logging/logger.py`

2. **Add Context Managers**
   - `log_duration()`
   - `ProgressLogger`

3. **Test print() Capture**
   - `PrintCapture.install()` compatibility

#### Test Commands
```bash
# Test logging
python -c "
from shared.logging import configure_logger, logger
configure_logger('test')
logger.info('Hello')
"
```

#### Deliverables
- [ ] `shared/logging/logger.py`
- [ ] `shared/logging/__init__.py`
- [ ] Documentation in docstrings

---

## Phase 3: File I/O (Days 8-10)

### Goal: Thread-safe JSON/JSONL utilities

#### Tasks

1. **Implement JSONLReader**
   - Copy from `03_FILE_UTILITIES.md`
   - Streaming, filtering, batching

2. **Implement JSONLWriter**
   - Thread-safe with buffering
   - NPI deduplication support

3. **Implement Utilities**
   - `atomic_write()`
   - `JSONCache`
   - `FileIndex`

#### Test Commands
```bash
# Test reading
python -c "
from shared.io import JSONLReader
r = JSONLReader('audiobee_bcbs_il/20251210/processed')
print(sum(1 for _ in r.read_all('audiobee_bcbs_il-20251210.jsonl')))
"

# Test writing
python -c "
from shared.io import JSONLWriter
w = JSONLWriter('/tmp/test')
w.write({'test': 1}, 'test.jsonl')
w.close()
"
```

#### Deliverables
- [ ] `shared/io/jsonl.py`
- [ ] `shared/io/file_manager.py`
- [ ] `shared/io/__init__.py`

---

## Phase 4: Validation (Days 11-14)

### Goal: Raw file and schema validation

#### Tasks

1. **Implement RawFileValidator**
   - Corruption detection
   - Encoding handling
   - Quarantine function

2. **Implement Pydantic Models**
   - `ProviderRecord`
   - All nested models (Address, Phone, etc.)

3. **Implement validate_file()**
   - File-level validation
   - Duplicate detection

4. **Implement ValidationReport**
   - JSON + Excel export
   - Console summary

#### Test Commands
```bash
# Test validation
python -c "
from shared.validation import validate_file
s = validate_file('audiobee_bcbs_il/20251210/processed/audiobee_bcbs_il-20251210.jsonl')
print(f'Valid: {s.valid_percentage:.1f}%')
"
```

#### Deliverables
- [ ] `shared/validation/raw_file.py`
- [ ] `shared/validation/schema.py`
- [ ] `shared/validation/validators.py`
- [ ] `shared/validation/report.py`
- [ ] `shared/validation/__init__.py`

---

## Phase 5: Integration (Days 15-17)

### Goal: Connect to output_generator

#### Tasks

1. **Enhance type_check.py**
   - Add Pydantic option
   - Keep jsonschema for compatibility

2. **Enhance report_generator.py**
   - Add validation sheet
   - Use shared logging

3. **Update run_all.py**
   - Add logging
   - Integrate validation

#### Deliverables
- [ ] Updated `output_generator/type_check.py`
- [ ] Updated `output_generator/report_generator.py`
- [ ] Updated `output_generator/run_all.py`

---

## Phase 6: Migration (Ongoing)

### Goal: Migrate scrapers to shared utilities

#### Priority Order

| Priority | Projects | Criteria |
|----------|----------|----------|
| High | New scrapers | Start fresh |
| High | Security issues | Hardcoded API keys |
| Medium | Frequent updates | Most maintained |
| Low | Legacy stable | Working, rarely touched |

#### Migration Checklist Per Project

```markdown
- [ ] Create .env from API keys in config.py
- [ ] Update config.py to use load_config()
- [ ] Keep backward compat exports (DIRS, PREV_DATE, etc.)
- [ ] Add logging to run_all.py
- [ ] Test full pipeline
- [ ] Remove hardcoded secrets from config.py
```

#### Example Migration (audiobee_bcbs_il)

**Before config.py:**
```python
PREV_DATE = "20251110"
CURR_DATE = "20251210"
PROJECT_NAME = "audiobee_bcbs_il"
# ... 100+ lines ...
HEADERS = {"x-api-key": "hardcoded-key"}  # SECURITY ISSUE
```

**After config.py:**
```python
from shared.config import load_config

_config = load_config(
    "sapphire", "audiobee_bcbs_il",
    network_id="210002020",
    geo_coords="39.883875,-88.834467",
    req_states=["IL"],
)

# Backward compat
PREV_DATE = _config.prev_date
CURR_DATE = _config.curr_date
PROJECT_NAME = _config.project_name
DIRS = _config.dirs

_config.setup_directories()
config = _config
```

**New .env:**
```bash
PREV_DATE=20251110
CURR_DATE=20251210
SAPPHIRE_API_KEY=03220e47-16eb-44d3-b1ca-4e3641973a97
```

---

## Quick Wins Summary

| Item | Effort | Impact | Do First? |
|------|--------|--------|-----------|
| .env.template | 1 hour | High (security) | YES |
| Move 15 API keys to .env | 2 hours | High (security) | YES |
| BaseConfig class | 4 hours | High | YES |
| Logger setup | 2 hours | Medium | YES |
| JSONLWriter | 4 hours | High | NO (phase 3) |
| Full validation | 8 hours | High | NO (phase 4) |

---

## Success Criteria

### Phase 0-1
- [ ] No API keys in git-tracked files
- [ ] Config loads from .env
- [ ] Backward compat maintained

### Phase 2-3
- [ ] Logger working with file output
- [ ] JSONLWriter thread-safe
- [ ] No data loss on crash (atomic writes)

### Phase 4-5
- [ ] Validation catches bad data
- [ ] Reports generated automatically
- [ ] output_generator enhanced

### Phase 6
- [ ] 50% of projects migrated within 2 months
- [ ] All new projects use shared utilities
- [ ] Zero hardcoded secrets

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing code | Backward compat exports |
| Learning curve | Clear documentation |
| Migration effort | Make it optional |
| Performance regression | Benchmark before/after |

---

## File Checklist

```
shared/
├── __init__.py                  # [ ]
├── pyproject.toml               # [ ]
├── config/
│   ├── __init__.py              # [ ]
│   ├── base.py                  # [ ]
│   ├── sapphire.py              # [ ]
│   ├── healthsparq.py           # [ ]
│   ├── carrier.py               # [ ]
│   ├── anthem.py                # [ ]
│   └── factory.py               # [ ]
├── io/
│   ├── __init__.py              # [ ]
│   ├── jsonl.py                 # [ ]
│   └── file_manager.py          # [ ]
├── logging/
│   ├── __init__.py              # [ ]
│   └── logger.py                # [ ]
└── validation/
    ├── __init__.py              # [ ]
    ├── raw_file.py              # [ ]
    ├── schema.py                # [ ]
    ├── validators.py            # [ ]
    └── report.py                # [ ]
```

---

## Command Reference

```bash
# Install shared package in development mode
cd scraping/shared
pip install -e .

# Run tests
pytest shared/tests/

# Type check
mypy shared/ --ignore-missing-imports

# Format code
ruff format shared/
ruff check shared/ --fix
```

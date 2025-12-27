# Code Improvement Recommendations

> **Strategic Enhancements for Scalability, Maintainability, and Reliability**

## Quick Start: What to Do First

1. **Secret Management** (P0) - Move API keys from `config.py` to environment variables
2. **Centralized Logging** (P0) - Replace print statements with structured logging
3. **Error Recovery** (P0) - Add checkpoints to resume failed runs

For **parallel execution and scaling**, see [PLAN.md](../PLAN.md).

---

## Priority Levels

| Priority | Description | When to Address |
|----------|-------------|-----------------|
| **P0** | Critical - Security/reliability risks | Before next production run |
| **P1** | High - Major efficiency gains | After P0 items complete |
| **P2** | Medium - Quality improvements | During normal maintenance |
| **P3** | Low - Nice-to-have enhancements | As time permits |

---

## P0: Critical Improvements

### 1. Secret Management

**Current State:**
- API keys hardcoded in `config.py` files
- Proxy credentials embedded in source code
- VPN credentials in `healthsparq-server`

**Problem:**
- Security risk if code is shared or leaked
- Difficult to rotate credentials
- No audit trail for credential access

**Recommendation:**

```python
# Before (INSECURE)
HEADERS = {
    "X-API-Key": "03220e47-16eb-44d3-b1ca-4e3641973a97"
}

# After (SECURE)
import os
from dotenv import load_dotenv

load_dotenv()

HEADERS = {
    "X-API-Key": os.environ.get("BCBS_IL_API_KEY")
}
```

**Implementation Steps:**
1. Create `.env.template` with required variables
2. Add `.env` to `.gitignore`
3. Update all `config.py` files to use `os.environ`
4. Document required environment variables
5. Consider using AWS Secrets Manager for production

**Effort:** Low | **Impact:** High

---

### 2. Centralized Logging

**Current State:**
- Print statements for output
- No structured logging
- No log aggregation
- Difficult to debug production issues

**Recommendation:**

```python
# Create shared logging configuration
# /shared/logging_config.py

import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "project": getattr(record, "project", "unknown"),
            "phase": getattr(record, "phase", "unknown"),
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

def setup_logging(project_name: str, log_file: str = None):
    logger = logging.getLogger(project_name)
    logger.setLevel(logging.INFO)

    # Console handler
    console = logging.StreamHandler()
    console.setFormatter(JSONFormatter())
    logger.addHandler(console)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)

    return logger

# Usage in scraper
logger = setup_logging("audiobee_bcbs_il", "run.log")
logger.info("Starting Phase 1", extra={"phase": "discovery"})
```

**Effort:** Medium | **Impact:** High

---

### 3. Error Recovery Checkpoints

**Current State:**
- Pipeline restarts from beginning on failure
- No checkpoint/resume capability
- Wasted time re-fetching cached data

**Recommendation:**

```python
# Implement checkpoint system
# /shared/checkpoint.py

import json
from pathlib import Path
from datetime import datetime

class Checkpoint:
    def __init__(self, project_name: str, run_date: str):
        self.checkpoint_file = Path(f"{run_date}/.checkpoint.json")
        self.state = self._load()

    def _load(self) -> dict:
        if self.checkpoint_file.exists():
            return json.loads(self.checkpoint_file.read_text())
        return {"phase": None, "progress": {}, "completed": []}

    def save(self):
        self.checkpoint_file.write_text(json.dumps(self.state, indent=2))

    def mark_phase_start(self, phase: str):
        self.state["phase"] = phase
        self.state["progress"][phase] = {"started": datetime.utcnow().isoformat()}
        self.save()

    def mark_phase_complete(self, phase: str):
        self.state["completed"].append(phase)
        self.state["progress"][phase]["completed"] = datetime.utcnow().isoformat()
        self.save()

    def is_phase_complete(self, phase: str) -> bool:
        return phase in self.state["completed"]

    def get_processed_ids(self, phase: str) -> set:
        return set(self.state["progress"].get(phase, {}).get("processed_ids", []))

    def add_processed_id(self, phase: str, id: str):
        if phase not in self.state["progress"]:
            self.state["progress"][phase] = {"processed_ids": []}
        self.state["progress"][phase]["processed_ids"].append(id)
        # Save every 100 items
        if len(self.state["progress"][phase]["processed_ids"]) % 100 == 0:
            self.save()

# Usage in run_all.py
checkpoint = Checkpoint(config.PROJECT_NAME, config.CURR_DATE)

for task in TASKS:
    if checkpoint.is_phase_complete(task):
        print(f"Skipping {task} (already complete)")
        continue

    checkpoint.mark_phase_start(task)
    run_task(task)
    checkpoint.mark_phase_complete(task)
```

**Effort:** Medium | **Impact:** High

---

## P1: High Priority Improvements

### 4. Configuration Inheritance

**Current State:**
- Each project has independent `config.py`
- Duplicate configuration across projects
- Inconsistent patterns

**Recommendation:**

```python
# /shared/base_config.py

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class BaseConfig:
    # Required
    project_name: str
    prev_date: str
    curr_date: str
    req_states: List[str]

    # Optional with defaults
    req_states_only: List[str] = field(default_factory=list)

    # Computed
    @property
    def dirs(self) -> Dict[str, str]:
        return {
            "raw": os.path.join(self.curr_date, "raw"),
            "search_results": os.path.join(self.curr_date, "raw", "search_results"),
            "provider_details": os.path.join(self.curr_date, "raw", "provider_details"),
            "processed": os.path.join(self.curr_date, "processed"),
        }

    @property
    def prev_dirs(self) -> Dict[str, str]:
        return {
            "raw": os.path.join(self.prev_date, "raw"),
            "search_results": os.path.join(self.prev_date, "raw", "search_results"),
            "provider_details": os.path.join(self.prev_date, "raw", "provider_details"),
            "processed": os.path.join(self.prev_date, "processed"),
        }

    def setup_directories(self):
        for dir_path in self.dirs.values():
            os.makedirs(dir_path, exist_ok=True)

@dataclass
class SapphireConfig(BaseConfig):
    """Configuration for Sapphire-type projects."""
    domain: str = ""
    network_id: str = ""
    api_key: str = ""

    @property
    def base_urls(self) -> Dict[str, str]:
        return {
            "summary": f"https://{self.domain}/api/providers/summary.json",
            "facets": f"https://{self.domain}/api/providers/facets.json",
            "affiliations": f"https://{self.domain}/api/providers/{{provider_id}}/locations/{{location_id}}/affiliations.json",
        }

# Usage in project config.py
from shared.base_config import SapphireConfig

config = SapphireConfig(
    project_name="audiobee_bcbs_il",
    prev_date=os.environ.get("PREV_DATE", "20251010"),
    curr_date=os.environ.get("CURR_DATE", "20251110"),
    req_states=["IL"],
    domain="my.providerfinderonline.com",
    network_id="210002020",
    api_key=os.environ.get("BCBS_IL_API_KEY"),
)
config.setup_directories()
```

**Effort:** Medium | **Impact:** High

---

### 5. Retry and Circuit Breaker Pattern

**Current State:**
- Basic retry logic in some projects
- No circuit breaker for failing APIs
- Wastes time on permanently failed endpoints

**Recommendation:**

```python
# /shared/resilience.py

import time
from functools import wraps
from enum import Enum
from datetime import datetime, timedelta

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout):
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.half_open_max_calls

        return False

    def record_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self.failure_count = 0

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

def with_circuit_breaker(circuit: CircuitBreaker):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not circuit.can_execute():
                raise Exception("Circuit breaker is open")

            try:
                result = func(*args, **kwargs)
                circuit.record_success()
                return result
            except Exception as e:
                circuit.record_failure()
                raise

        return wrapper
    return decorator

# Usage
api_circuit = CircuitBreaker(failure_threshold=5, recovery_timeout=300)

@with_circuit_breaker(api_circuit)
def fetch_provider(provider_id: str):
    response = httpx.get(f"{BASE_URL}/{provider_id}")
    response.raise_for_status()
    return response.json()
```

**Effort:** Medium | **Impact:** High

---

### 6. Parallel Execution Framework

> **Note:** Full implementation details are in [PLAN.md](../PLAN.md).

**Current State:**
- Sequential scraper execution
- Underutilized CPU/memory resources
- Long total run times (~48 hours for 95 scrapers)

**Solution:** See [PLAN.md](../PLAN.md) for:
- Local parallel execution (8-10 scrapers per PC)
- AWS EC2 burst capacity for overflow
- Static project assignment across 3 PCs

**Target:** ~6-8 hours for 190 scrapers

**Effort:** Medium | **Impact:** High

---

## P2: Medium Priority Improvements

### 7. Metrics and Monitoring

**Current State:**
- No metrics collection
- No dashboards
- Manual monitoring required

**Recommendation:**

```python
# /shared/metrics.py

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, List
from datetime import datetime
import json

@dataclass
class RunMetrics:
    project_name: str
    run_date: str
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: datetime = None

    # Counters
    providers_discovered: int = 0
    providers_fetched: int = 0
    providers_normalized: int = 0
    providers_output: int = 0

    # Errors
    errors: List[Dict] = field(default_factory=list)

    # Performance
    phase_durations: Dict[str, float] = field(default_factory=dict)

    # HTTP stats
    requests_made: int = 0
    requests_failed: int = 0
    bytes_downloaded: int = 0

    @contextmanager
    def time_phase(self, phase_name: str):
        start = time.time()
        yield
        duration = time.time() - start
        self.phase_durations[phase_name] = duration

    def record_error(self, phase: str, error: str, context: dict = None):
        self.errors.append({
            "timestamp": datetime.utcnow().isoformat(),
            "phase": phase,
            "error": error,
            "context": context or {}
        })

    def finalize(self):
        self.end_time = datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "run_date": self.run_date,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": (self.end_time - self.start_time).total_seconds() if self.end_time else None,
            "providers": {
                "discovered": self.providers_discovered,
                "fetched": self.providers_fetched,
                "normalized": self.providers_normalized,
                "output": self.providers_output,
            },
            "errors": self.errors,
            "phase_durations": self.phase_durations,
            "http": {
                "requests_made": self.requests_made,
                "requests_failed": self.requests_failed,
                "bytes_downloaded": self.bytes_downloaded,
            }
        }

    def save(self, filepath: str):
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

# Usage
metrics = RunMetrics(project_name="audiobee_bcbs_il", run_date="20251110")

with metrics.time_phase("discovery"):
    # Phase 1 code
    metrics.providers_discovered = 10000

with metrics.time_phase("extraction"):
    # Phase 2 code
    metrics.providers_fetched = 9500

metrics.finalize()
metrics.save(f"{config.CURR_DATE}/metrics.json")
```

**Effort:** Medium | **Impact:** Medium

---

### 8. Data Validation Framework

**Current State:**
- Validation only at output stage
- No intermediate validation
- Issues discovered late

**Recommendation:**

```python
# /shared/validation.py

from pydantic import BaseModel, validator, ValidationError
from typing import List, Optional
import re

class Phone(BaseModel):
    type: str
    value: str

    @validator("type")
    def validate_type(cls, v):
        if v not in ["phone", "fax"]:
            raise ValueError(f"Invalid phone type: {v}")
        return v

    @validator("value")
    def validate_value(cls, v):
        digits = re.sub(r'[^0-9]', '', v)
        if len(digits) < 10:
            raise ValueError(f"Phone too short: {v}")
        return digits

class Address(BaseModel):
    street_line_1: str
    street_line_2: Optional[str] = None
    city: str
    state: str
    zip: str
    phones: List[Phone] = []

    @validator("state")
    def validate_state(cls, v):
        if not re.match(r'^[A-Z]{2}$', v):
            raise ValueError(f"Invalid state: {v}")
        return v

    @validator("zip")
    def validate_zip(cls, v):
        if not re.match(r'^\d{5}$', v):
            raise ValueError(f"Invalid ZIP: {v}")
        return v

class Provider(BaseModel):
    npi: Optional[str] = None
    unparsed_name: str
    provider_type: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    @validator("npi")
    def validate_npi(cls, v):
        if v and not re.match(r'^\d{10}$', v):
            raise ValueError(f"Invalid NPI: {v}")
        return v

    @validator("provider_type")
    def validate_type(cls, v):
        if v not in ["individual", "organization"]:
            raise ValueError(f"Invalid provider_type: {v}")
        return v

class ProviderRecord(BaseModel):
    networks: List[dict]
    provider: Provider
    addresses: List[Address]
    specialties: List[dict] = []
    group_affiliations: List[dict] = []
    hospital_affiliations: List[dict] = []

# Usage
def validate_record(data: dict) -> tuple[bool, Optional[str]]:
    try:
        ProviderRecord(**data)
        return True, None
    except ValidationError as e:
        return False, str(e)

# Validate before writing
valid, error = validate_record(record)
if not valid:
    logger.error(f"Validation failed: {error}")
    continue
```

**Effort:** Medium | **Impact:** Medium

---

### 9. Testing Framework

**Current State:**
- No automated tests
- Manual validation only
- Regression risk on changes

**Recommendation:**

```python
# /tests/test_normalization.py
import pytest
from shared.validation import validate_record

class TestProviderValidation:
    def test_valid_provider(self):
        data = {
            "networks": [{"name": "PPO", "tier": None}],
            "provider": {"npi": "1234567890", "unparsed_name": "John Smith MD", "provider_type": "individual"},
            "addresses": [{"street_line_1": "123 Main St", "city": "Chicago", "state": "IL", "zip": "60601"}],
        }
        valid, error = validate_record(data)
        assert valid, f"Should be valid: {error}"

    def test_invalid_npi(self):
        data = {"networks": [], "provider": {"npi": "123", "unparsed_name": "Test", "provider_type": "individual"}, "addresses": []}
        valid, error = validate_record(data)
        assert not valid and "Invalid NPI" in error

# Run: pytest tests/ -v
```

**Effort:** Medium | **Impact:** Medium

---

## P3: Lower Priority Improvements

### 10. Documentation Generator

**Recommendation:** Auto-generate project documentation from CLAUDE.md files.

### 11. Output Format Flexibility

**Recommendation:** Support multiple output formats (JSONL, Parquet, CSV).

### 12. API Versioning

**Recommendation:** Version internal APIs for backward compatibility.

### 13. Container Support

**Recommendation:** Dockerize scrapers for consistent deployment.

---

## Implementation Checklist

### Phase 1: Critical Security (P0)
- [ ] Implement secret management (.env files)
- [ ] Update all config.py files to use `os.environ`
- [ ] Document required environment variables
- [ ] Add `.env.template` and update `.gitignore`

### Phase 2: Reliability (P0-P1)
- [ ] Add centralized logging with JSON format
- [ ] Implement checkpoint/resume system
- [ ] Add retry logic with circuit breaker pattern

### Phase 3: Scalability (P1)
- [ ] Apply configuration inheritance (base classes)
- [ ] Set up parallel execution per [PLAN.md](../PLAN.md)
- [ ] Add metrics collection

### Phase 4: Quality (P2)
- [ ] Implement Pydantic validation
- [ ] Add unit tests for normalization logic
- [ ] Set up CI/CD pipeline

---

## Architecture Evolution

```
Current State                    Target State
─────────────────────           ─────────────────────
95 Independent Scrapers    →    Unified Framework with shared modules
Hardcoded Credentials      →    Environment Variables (.env)
Print Statements           →    Structured JSON Logging
No Checkpoints             →    Resume-capable Pipelines
Sequential Execution       →    Parallel Execution (see PLAN.md)
Manual Validation          →    Pydantic + Automated Testing
No Metrics                 →    Full Observability (metrics.json)
```

---

## Summary Table

| # | Improvement | Priority | Effort | Impact | Status |
|---|-------------|----------|--------|--------|--------|
| 1 | Secret Management (.env) | P0 | Low | High | Pending |
| 2 | Centralized Logging | P0 | Medium | High | Pending |
| 3 | Error Recovery Checkpoints | P0 | Medium | High | Pending |
| 4 | Configuration Inheritance | P1 | Medium | High | Pending |
| 5 | Retry/Circuit Breaker | P1 | Medium | High | Pending |
| 6 | Parallel Execution | P1 | Medium | High | See PLAN.md |
| 7 | Metrics & Monitoring | P2 | Medium | Medium | Pending |
| 8 | Data Validation (Pydantic) | P2 | Medium | Medium | Pending |
| 9 | Testing Framework | P2 | Medium | Medium | Pending |
| 10-13 | P3 Items (Docs, Formats, etc.) | P3 | High | Medium | Backlog |

---

## References

- [Large-Scale Web Scraping Guide](https://crawlbase.com/blog/large-scale-web-scraping/)
- [ETL Best Practices](https://www.getdbt.com/blog/etl-pipeline-best-practices)
- [Anti-Detection Techniques](https://brightdata.com/blog/how-tos/avoid-bot-detection-with-playwright-stealth)
- [PLAN.md](../PLAN.md) - Infrastructure scaling plan

---

*Last Updated: December 2024*

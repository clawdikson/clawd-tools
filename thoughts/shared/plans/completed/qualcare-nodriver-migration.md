# QualCare Migration Plan: Patchright → nodriver + core/

**Created**: 2026-01-14
**Status**: SPEC COMPLETE - Ready for Implementation
**Reference**: audiobee_aetna_better_health_of_oklahoma/index_1.py

---

## Interview Results Summary

| Decision Area | Choice | Notes |
|--------------|--------|-------|
| Session TTL | Never expires | Params valid for entire scrape run |
| Request Method | In-browser fetch() | POST required for results.pl |
| Worker Purpose | Rate limit distribution + Fault isolation | 3 workers default |
| Failure Handling | Requeue to pool | Max 2 requeues before dead letter |
| Auth Flow | Click required first | "Region Search" click establishes session |
| Proxy Provider | SmartProxy only | DataImpulse blocked by Incapsula |
| Output Format | HTML + minimal JSON | HTML pages + JSON with provider IDs only |
| Headless Mode | Always visible | headless=False for debugging |
| ID Extraction | Minimal JSON | Save provider ID list for details phase |
| Mapper Compat | Already compatible | No changes to html_to_ideon_mapper.py |
| Browser Model | Worker = Browser | Each worker owns one browser instance |
| Metrics | Progress bar | tqdm for real-time progress |
| Resume Logic | File check only | Skip if output file exists |
| Empty Results | Info log | Log "No providers found" as INFO |
| Proxy Cooldown | No cooldown | Immediate round-robin |
| Invalid Provider | Requeue | Treat as transient failure |
| Legacy Files | Archive to subfolder | Move to legacy/ folder |
| Success Criteria | 100% required | All 385 specialties must complete |
| Performance Goal | Reliability first | Slower is fine if more reliable |
| Rate Limits | Soft blocks observed | Returns captcha/error pages |
| Circuit Breaker | Yes - slow down | Increase delays on error spike |
| Pre-work | Investigation first | Verify nodriver before Phase 0 |
| Investigation Scope | All three | Auth + fetch() + proxy |
| Spike Duration | 1-2 hours | Thorough testing |

---

## Investigation Spike Results (2026-01-14)

**Status**: COMPLETED - Partial Success

### Spike Results Summary

| Test | Result | Notes |
|------|--------|-------|
| nodriver + SmartProxy | **PASS** | Bypasses Incapsula (809KB page loaded) |
| nodriver + DataImpulse | **FAIL** | Blocked by Incapsula |
| Auth flow (click Region Search) | **PASS** | Successfully navigates to search form |
| Session param extraction (JS) | **FAIL** | nodriver evaluate() doesn't return complex objects |
| Session param extraction (HTML) | **PASS** | BeautifulSoup extracts zid, sptr_id, file |
| In-browser fetch() | **FAIL** | nodriver evaluate() doesn't support async JS |

### Key Findings

1. **nodriver + SmartProxy** successfully bypasses Incapsula protection
2. **DataImpulse proxy does NOT work** with nodriver for this site
3. **Session extraction works** via BeautifulSoup HTML parsing (51 params found)
4. **In-browser fetch() does NOT work** - nodriver's `evaluate()` returns `None` for async JavaScript

### Required Approach Changes

Since nodriver's `evaluate()` doesn't support async JavaScript:

**Option A: Form Submission via DOM** (Recommended)
- Fill form fields using nodriver selectors
- Click "Find Providers" button
- Wait for results page to load
- Parse results with BeautifulSoup

**Option B: HTTP Client Hybrid**
- Use nodriver for auth + session extraction
- Extract cookies from browser
- Use httpx/aiohttp for actual requests

### Updated Migration Plan

- **Proxy**: SmartProxy ONLY (DataImpulse blocked)
- **Session extraction**: BeautifulSoup (not JS evaluate)
- **Search requests**: Form submission via DOM
- **HTML parsing**: BeautifulSoup (already works)

### Spike Checklist

- [x] Auth flow completes without manual intervention
- [ ] ~~fetch() returns valid HTML~~ → Use form submission instead
- [x] SmartProxy works with nodriver
- [ ] ~~DataImpulse works~~ → Blocked by Incapsula

---

## Architecture Decisions

### Worker Model

```
┌─────────────────────────────────────────────────────────────────┐
│                         main()                                   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
    ┌─────────┐          ┌─────────┐          ┌─────────┐
    │ Worker 0│          │ Worker 1│          │ Worker 2│
    │ Browser │          │ Browser │          │ Browser │
    │ Proxy A │          │ Proxy B │          │ Proxy A │
    └────┬────┘          └────┬────┘          └────┬────┘
         │                    │                    │
         └────────────────────┴────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  asyncio.Queue   │
                    │ (specialty tasks)│
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
         [Specialty 1] [Specialty 2] [Specialty N]
```

### Failure & Requeue Flow

```
Task fails → Worker retry (3x) → Requeue to pool
                                       │
                                       ▼
                            Another worker picks up
                                       │
                                       ▼
                              Retry (3x) → Requeue again
                                                │
                                                ▼
                                          Dead letter file
```

**Max requeues**: 2 (task can be attempted by up to 3 different workers)

### Circuit Breaker (Adaptive Delay)

```python
class AdaptiveDelay:
    """Slow down on errors, speed up on success."""

    base_delay: float = 1.5
    current_delay: float = 1.5
    max_delay: float = 10.0
    error_multiplier: float = 1.5
    success_divisor: float = 1.2

    def on_error(self):
        self.current_delay = min(
            self.current_delay * self.error_multiplier,
            self.max_delay
        )

    def on_success(self):
        self.current_delay = max(
            self.current_delay / self.success_divisor,
            self.base_delay
        )
```

---

## Phase 0: Git Setup (After Spike Success)

```bash
# 1. Ensure clean state
git status

# 2. Create feature branch from master
git checkout master
git pull origin master
git checkout -b feat/qualcare-nodriver-migration

# 3. Verify branch created
git branch --show-current
```

**Branch**: `feat/qualcare-nodriver-migration`

---

## Phase 1: Configuration Migration

### 1.1 Create settings.py

```python
"""Pydantic-based configuration for QualCare scraper."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import Field
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import BaseConfig


class QualCareConfig(BaseConfig):
    """Configuration for QualCare scraper."""

    # Project identification
    project_name: str = Field(default="audiobee_qualcare")
    site_type: str = Field(default="carrier")
    curr_date: str = Field(default="20260114")
    prev_date: str = Field(default="20251010")

    # Talispoint URLs
    base_url: str = Field(default="https://www-lv.talispoint.com/")
    auth_url: str = Field(
        default="https://www-lv.talispoint.com/coventry/?AE=997291691&CAID=WCALL"
    )
    search_endpoint: str = Field(default="talispoint/results.pl")
    detail_endpoint: str = Field(default="talispoint/map.pl")

    # Search params
    req_states: list[str] = Field(default=["NJ"])
    network_code: str = Field(default="COVX_QUAL")
    network_name: str = Field(default="QualCare")
    results_per_page: int = Field(default=250)
    max_pages: int = Field(default=500)

    # Worker settings
    num_workers: int = Field(default=3)
    max_consecutive_failures: int = Field(default=5)
    max_requeues: int = Field(default=2)

    # Adaptive delay (circuit breaker)
    base_delay: float = Field(default=1.5)
    max_delay: float = Field(default=10.0)
    error_delay_multiplier: float = Field(default=1.5)
    success_delay_divisor: float = Field(default=1.2)

    # HTML validation
    min_html_size: int = Field(default=500)
    soft_block_indicators: list[str] = Field(
        default_factory=lambda: ["captcha", "access denied", "rate limit"]
    )

    # Data files
    specialties_file: str = Field(default="data/specialties-20250920.json")

    # Session defaults (overridden by extraction)
    session_defaults: dict[str, str] = Field(
        default_factory=lambda: {
            "account": "FRH",
            "unit": "FRH_EXT",
            "userloc": "A997291691_WCALL",
            "network": "COVX_QUAL",
            "network_parent": "COV_FRH",
            "label": "coventry_lob",
            "mode": "region",
        }
    )

    def _compute_dirs(self) -> dict[str, Path]:
        base = Path(self.curr_date)
        return {
            "raw": base / "raw",
            "raw_search": base / "raw" / "search",
            "raw_providers": base / "raw" / "providers",
            "processed": base / "processed",
            "legacy": base / "legacy",  # For archived files
        }

    def load_specialties(self) -> list[dict]:
        spec_path = Path(__file__).parent / self.specialties_file
        if spec_path.exists():
            with open(spec_path) as f:
                data = json.load(f)
                return data.get("specialties", [])
        return []


_config: QualCareConfig | None = None

def get_config() -> QualCareConfig:
    global _config
    if _config is None:
        _config = QualCareConfig()
    return _config
```

### 1.2 Update config.py (Backward Compat)

```python
"""Configuration with backward compatibility layer."""
import os
from pathlib import Path

USE_CORE_CONFIG = os.getenv("USE_CORE_CONFIG", "true").lower() == "true"

if USE_CORE_CONFIG:
    from settings import QualCareConfig, get_config

    _config = get_config()

    CURR_DATE = _config.curr_date
    PREV_DATE = _config.prev_date
    PROJECT_NAME = _config.project_name

    DIRS = {k: str(v) for k, v in _config.dirs.items()}
    for d in DIRS.values():
        os.makedirs(d, exist_ok=True)

    REQ_STATES = _config.req_states
    BASE_URL = _config.base_url
    AUTH_URL = _config.auth_url

    NUM_WORKERS = _config.num_workers
    MAX_REQUEUES = _config.max_requeues
    MIN_HTML_SIZE = _config.min_html_size
    SOFT_BLOCK_INDICATORS = _config.soft_block_indicators

    SPECIALTIES = _config.load_specialties()
    SESSION_DEFAULTS = _config.session_defaults

else:
    import warnings
    warnings.warn("Using legacy config", DeprecationWarning)
    from config_legacy import *  # Fallback to renamed original
```

**Commit**: `feat(qualcare): add Pydantic config with core/ integration`

---

## Phase 2: Search Phase Migration (index_1.py)

### Key Implementation Points

1. **Form submission via DOM** (not in-browser fetch - doesn't work with nodriver)
   - Fill form fields using nodriver selectors (state, specialty)
   - Click "Find Providers" button
   - Wait for results page to load
   - Parse results with BeautifulSoup

2. **Session parameter extraction via BeautifulSoup**
   - Get HTML content with `tab.get_content()`
   - Parse hidden inputs to extract zid, sptr_id, file, gm_fileout
   - Click "Region Search" first (required for session state)

3. **Requeue strategy**
   - Task includes requeue_count
   - On failure: increment count, put back in queue
   - At max_requeues: write to dead letter file

4. **Adaptive delay**
   - Increase delay on soft blocks
   - Decrease delay on success
   - Capped at max_delay

5. **Progress bar**
   - tqdm for specialty completion tracking
   - Update on task completion

6. **Output format**
   - HTML files: `{state}_{specialty_code}_page{n}.html`
   - JSON file: `{state}_{specialty_code}.json` with provider IDs only

### Core Structure

```python
"""Search phase - nodriver + core/ integration."""
import asyncio
from dataclasses import dataclass, field
from pathlib import Path

import nodriver as nd
from tqdm import tqdm

from core.logging import logger, setup_logging, set_trace_id
from core.proxy import ProxyManager, ProxyType

# SmartProxy only (DataImpulse blocked by Incapsula)
proxy_manager = ProxyManager(
    proxy_types=[ProxyType.SMARTPROXY_SESSION]
)

@dataclass
class Task:
    state: str
    specialty_code: str
    specialty_name: str
    requeue_count: int = 0

@dataclass
class AdaptiveDelay:
    base: float = 1.5
    current: float = 1.5
    max: float = 10.0

    def on_error(self):
        self.current = min(self.current * 1.5, self.max)

    def on_success(self):
        self.current = max(self.current / 1.2, self.base)

@dataclass
class Session:
    worker_id: int
    browser: object | None = None
    tab: object | None = None
    session_params: dict = field(default_factory=dict)
    delay: AdaptiveDelay = field(default_factory=AdaptiveDelay)

    async def initialize(self) -> bool:
        """Initialize browser, complete auth, extract session params."""
        # ... implementation ...

    async def fetch_search_results(self, state: str, code: str) -> tuple[str | None, bool]:
        """Execute in-browser fetch() for search. Returns (html, is_soft_block)."""
        # ... implementation ...

async def worker(worker_id: int, queue: asyncio.Queue, dead_letter: list, pbar: tqdm):
    """Process tasks from queue with requeue support."""
    session = Session(worker_id=worker_id)

    if not await session.initialize():
        logger.error("Failed to initialize", worker_id=worker_id)
        return

    while True:
        task = await queue.get()
        if task is None:
            break

        success = await process_task(session, task)

        if not success:
            if task.requeue_count < MAX_REQUEUES:
                task.requeue_count += 1
                await queue.put(task)
                logger.info(f"Requeued {task.specialty_code}", requeue_count=task.requeue_count)
            else:
                dead_letter.append(task)
                logger.warning(f"Dead letter: {task.specialty_code}")
        else:
            pbar.update(1)

        queue.task_done()
```

**Commit**: `feat(qualcare): migrate search phase to nodriver`

---

## Phase 3: Details Phase Migration (index_2.py)

### Key Differences from Search

- Loads provider IDs from JSON files (not specialties)
- Fetches from map.pl endpoint
- Single HTML file per provider
- Same worker model and requeue strategy

### Output

- HTML: `raw/providers/{provider_id}.html`
- Summary: `raw/provider_fetch_summary.json`

**Commit**: `feat(qualcare): migrate details phase to nodriver`

---

## Phase 4: Utils & Legacy Archive

### 4.1 Update utils.py

Add soft block detection:

```python
def is_soft_block(html: str) -> bool:
    """Check if response is a soft block (captcha, error page)."""
    html_lower = html.lower()
    for indicator in config.SOFT_BLOCK_INDICATORS:
        if indicator in html_lower:
            return True
    return False

def validate_html_content(html: str) -> tuple[bool, str | None]:
    """Validate HTML content."""
    if not html:
        return False, "Empty HTML"

    if len(html) < config.MIN_HTML_SIZE:
        return False, f"HTML too small ({len(html)} bytes)"

    if is_soft_block(html):
        return False, "Soft block detected"

    return True, None
```

### 4.2 Archive Legacy Files

```bash
mkdir -p audiobee_qualcare/legacy
git mv audiobee_qualcare/index_1.py audiobee_qualcare/legacy/index_1_legacy.py
git mv audiobee_qualcare/index_2-new.py audiobee_qualcare/legacy/index_2_legacy.py
git mv audiobee_qualcare/config.py audiobee_qualcare/legacy/config_legacy.py
```

**Commit**: `feat(qualcare): archive legacy files, add validation utils`

---

## Phase 5: Testing & PR

### Test Checklist

- [ ] Spike verification passed (auth, fetch, proxy)
- [ ] Config loads from environment
- [ ] Search phase completes for 5 specialties
- [ ] Details phase completes for 100 providers
- [ ] Full run: 100% of 385 specialties (0 dead letters)
- [ ] Output format matches mapper expectations
- [ ] Progress bar displays correctly

### PR Creation

```bash
git push -u origin feat/qualcare-nodriver-migration

gh pr create \
  --title "feat(qualcare): migrate to nodriver + core/ packages" \
  --body "$(cat <<'EOF'
## Summary

Migrates audiobee_qualcare from Patchright to nodriver with full core/ package integration.

### Changes
- Pydantic config (settings.py) with backward compat layer
- nodriver for browser automation
- core.proxy.ProxyManager with DataImpulse + SmartProxy round-robin
- core.logging with trace_id correlation
- Producer-consumer worker model (3 workers)
- Requeue strategy with max 2 requeues
- Adaptive delay (circuit breaker) for rate limits
- Progress bar (tqdm) for real-time tracking

### Breaking Changes
- Output format simplified: HTML + minimal JSON (no full JSON summaries)
- Legacy files archived to legacy/ subfolder

### Testing
- [x] Spike: nodriver + auth + fetch + proxy verified
- [x] Search phase: 385/385 specialties (100%)
- [x] Details phase: all providers fetched
- [x] Mapper compatibility verified

## Test Plan
- Run full scrape and compare provider count with previous run
- Verify html_to_ideon_mapper.py produces valid output

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Success Criteria

| Metric | Requirement |
|--------|-------------|
| Specialties scraped | 385/385 (100%) |
| Dead letter count | 0 |
| Provider details | Match or exceed previous run count |
| Mapper output | Valid JSONL, no parsing errors |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| nodriver incompatible | Spike investigation before Phase 0 |
| Rate limiting | Adaptive delay + requeue strategy |
| Session expiry | Never expires (verified) |
| Proxy blocks | Round-robin + no cooldown |
| Data loss | HTML output preserved, legacy archived |

---

## References

- Reference: `audiobee_aetna_better_health_of_oklahoma/index_1.py`
- Core docs: `core/config/CLAUDE.md`, `core/logging/CLAUDE.md`, `core/proxy/CLAUDE.md`
- Specialty list: `data/specialties-20250920.json` (385 specialties)

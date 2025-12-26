# HealthSparq Singleton Repository Plan

## Executive Summary

Consolidate 25 healthsparq scraper projects into a single, unified repository with project-specific configuration files and CLI-based project selection. This eliminates ~95% code duplication while maintaining per-project customization.

**Current State**: 25 separate `audiobee_*` folders with nearly identical code (healthspark.py, browser*session.py, index*\*.py)

**Target State**: Single `healthsparq/` package with YAML configs per project, Typer CLI for selection

---

## ⚠️ Key Decisions (Post-Review)

Based on 20-agent comprehensive review conducted 2025-12-26:

| Decision                       | Resolution                           | Rationale                          |
| ------------------------------ | ------------------------------------ | ---------------------------------- |
| **Project Count**              | 25 projects (not 28)                 | Codebase validation confirmed 25   |
| **Reference Implementation**   | `audiobee_bluecard_national` (async) | Most complete async implementation |
| **Config Format**              | YAML + Pydantic                      | Better UX for 25+ project configs  |
| **Dates Handling**             | CLI args only (`--curr`, `--prev`)   | Unanimous agent consensus          |
| **shared_package Integration** | MANDATORY                            | Already exists and mature          |
| **Phase Count**                | 6 phases (merged from 9)             | Reduced complexity                 |
| **Session Management**         | Pure Python (shared_package)         | No Node.js server dependency       |

---

## Ralph Wiggum Autonomous Execution

This plan is structured for autonomous execution via the Ralph Wiggum plugin. Each phase has:

- **Binary success criteria** - Programmatically verifiable completion
- **Verification commands** - Commands that return exit code 0 on success
- **Subagent delegation** - Tasks delegated to specialized agents
- **Iteration limits** - Safety bounds per phase

### CLI Executor Tool

A dedicated CLI tool manages execution and progress tracking:

```bash
# Check current progress
uv run tools/healthsparq_executor.py status

# Run next pending phase (generates prompt)
uv run tools/healthsparq_executor.py run

# Run specific phase
uv run tools/healthsparq_executor.py run --phase 0

# Run all phases (full autonomous)
uv run tools/healthsparq_executor.py run --all

# Dry-run to see generated prompt
uv run tools/healthsparq_executor.py run --phase 0 --dry-run

# Verify phase completion
uv run tools/healthsparq_executor.py verify --phase 0

# Reset progress
uv run tools/healthsparq_executor.py reset --phase 0 --yes
```

### Execution Pattern

```bash
# Generate prompt for a phase
uv run tools/healthsparq_executor.py prompt --phase 0

# Then execute with Ralph Wiggum
/ralph-loop "<generated-prompt>" --max-iterations 15
```

---

## Progress Tracker (Revised: 6 Phases)

| Phase | Goal                       | Status      | Subagent                      | Iterations |
| ----- | -------------------------- | ----------- | ----------------------------- | ---------- |
| 0     | Test & Package Foundation  | [ ] Pending | `architect-reviewer`          | 15         |
| 1     | Config System + CLI        | [ ] Pending | `python-pro`                  | 15         |
| 2     | Core Module Migration      | [ ] Pending | `refactoring-specialist`      | 20         |
| 3     | Phase Execution Modules    | [ ] Pending | `python-pro`                  | 20         |
| 4     | Project Configs (25 YAML)  | [ ] Pending | `Explore` + `general-purpose` | 15         |
| 5     | Validation & Documentation | [ ] Pending | `test-automator` + `docs`     | 10         |

**Note**: Phases consolidated from original 9 to 6 based on agent review recommendations.

---

## PHASE 0: Test Infrastructure Setup

**Goal**: Establish test framework before any refactoring

**Subagent**: `test-automator`

### Tasks

1. Create `healthsparq/tests/` directory structure
2. Add pytest configuration to pyproject.toml
3. Create test fixtures for mock API responses
4. Write baseline tests for reference implementation

### Deliverables

```
healthsparq/
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # pytest fixtures
│   ├── fixtures/
│   │   ├── mock_search_response.json
│   │   └── mock_provider_detail.json
│   └── test_placeholder.py      # Ensures pytest runs
└── pyproject.toml               # pytest config added
```

### Verification Commands

```bash
# All must return exit code 0
python -c "import pytest; print('pytest available')"
pytest healthsparq/tests/ --collect-only # Collects tests without errors
ls healthsparq/tests/conftest.py         # Fixtures file exists
```

### Success Criteria

- [ ] `pytest healthsparq/tests/ --collect-only` exits 0
- [ ] `healthsparq/tests/conftest.py` exists with fixtures
- [ ] `healthsparq/tests/fixtures/` contains mock JSON files

### Ralph Loop Command

```bash
/ralph-loop "Create test infrastructure for healthsparq package.
1. Create healthsparq/tests/ with conftest.py and fixtures/
2. Add pytest to pyproject.toml
3. Create mock JSON fixtures from audiobee_bluecard_national responses (async reference)
4. Verify: pytest healthsparq/tests/ --collect-only exits 0
Output PHASE_0_COMPLETE when done." --max-iterations 10
```

---

## PHASE 1: Package Foundation

**Goal**: Create base package structure with proper Python packaging

**Subagent**: `architect-reviewer`

### Tasks

1. Create `healthsparq/` package directory structure
2. Create `__init__.py` files with proper exports
3. Add package to pyproject.toml with dependencies
4. Verify package imports work

### Deliverables

```
healthsparq/
├── __init__.py                  # Package root with version
├── __main__.py                  # Enable python -m healthsparq
├── core/
│   ├── __init__.py
│   └── .gitkeep
├── phases/
│   ├── __init__.py
│   └── .gitkeep
├── utils/
│   ├── __init__.py
│   └── .gitkeep
├── configs/
│   └── .gitkeep
└── tests/                       # From Phase 0
```

### Verification Commands

```bash
# All must return exit code 0
python -c "import healthsparq; print(healthsparq.__version__)"
python -c "from healthsparq.core import *"
python -c "from healthsparq.phases import *"
python -c "from healthsparq.utils import *"
ls healthsparq/__main__.py
```

### Success Criteria

- [ ] `python -c "import healthsparq"` exits 0
- [ ] All subpackage imports work without error
- [ ] `__version__` defined in `__init__.py`
- [ ] `__main__.py` exists for CLI entry

### Ralph Loop Command

```bash
/ralph-loop "Create healthsparq package foundation.
1. Create directory structure with __init__.py files
2. Add to pyproject.toml with dependencies
3. Create __main__.py for CLI entry
4. Verify: python -c 'import healthsparq' exits 0
Output PHASE_1_COMPLETE when done." --max-iterations 15
```

---

## PHASE 2: Configuration System

**Goal**: Implement YAML config loading with Pydantic validation

**Subagent**: `code-simplifier`

### Tasks

1. Create Pydantic models in `healthsparq/config/schema.py`
2. Create config loader in `healthsparq/config/loader.py`
3. Create `_base.yaml` with defaults
4. Create first project config from audiobee_christus_health_plan

### Deliverables

```
healthsparq/
├── config/
│   ├── __init__.py
│   ├── schema.py                # Pydantic models
│   └── loader.py                # YAML loading logic
├── configs/
│   ├── _base.yaml               # Shared defaults
│   └── christus_health_plan.yaml
└── tests/
    └── test_config.py           # Config validation tests
```

### Verification Commands

```bash
# All must return exit code 0
python -c "from healthsparq.config import load_config; c = load_config('christus_health_plan'); print(c.project.name)"
python -c "from healthsparq.config.schema import HealthSparqProjectConfig"
pytest healthsparq/tests/test_config.py -v
ls healthsparq/configs/christus_health_plan.yaml
```

### Success Criteria

- [ ] `load_config('christus_health_plan')` returns valid config
- [ ] Pydantic validates all required fields
- [ ] `pytest healthsparq/tests/test_config.py` passes
- [ ] Config matches legacy audiobee_christus_health_plan/config.py values

### Ralph Loop Command

```bash
/ralph-loop "Implement healthsparq configuration system.
1. Create Pydantic models matching PROJECT_CONFIG_SCHEMA.md
2. Create YAML loader with inheritance from _base.yaml
3. Create christus_health_plan.yaml from legacy config.py
4. Write tests in test_config.py
5. Verify: pytest healthsparq/tests/test_config.py exits 0
Output PHASE_2_COMPLETE when done." --max-iterations 10
```

---

## PHASE 3: CLI Implementation

**Goal**: Implement Typer CLI with all commands

**Subagent**: `python-pro`

### Tasks

1. Create `healthsparq/cli.py` with Typer app
2. Implement `run`, `list`, `validate`, `init` commands
3. Wire CLI to `__main__.py`
4. Add shell completion support

### Deliverables

```
healthsparq/
├── cli.py                       # Typer CLI implementation
├── __main__.py                  # Updated: from .cli import app; app()
└── tests/
    └── test_cli.py              # CLI tests
```

### Verification Commands

```bash
# All must return exit code 0
python -m healthsparq --help
python -m healthsparq list
python -m healthsparq validate christus_health_plan
python -m healthsparq run christus_health_plan --curr 20251226 --dry-run
pytest healthsparq/tests/test_cli.py -v
```

### Success Criteria

- [ ] `python -m healthsparq --help` shows all commands
- [ ] `python -m healthsparq list` shows available projects
- [ ] `python -m healthsparq validate christus_health_plan` exits 0
- [ ] `--dry-run` flag works without executing scraper
- [ ] `pytest healthsparq/tests/test_cli.py` passes

### Ralph Loop Command

```bash
/ralph-loop "Implement healthsparq Typer CLI.
1. Create cli.py following CLI_DESIGN.md specification
2. Implement run, list, validate, init commands
3. Wire to __main__.py
4. Write CLI tests
5. Verify: python -m healthsparq --help exits 0
Output PHASE_3_COMPLETE when done." --max-iterations 15
```

---

## PHASE 2: Core Module Migration

**Goal**: Extract unified healthspark.py from reference implementation (async)

**Subagent**: `refactoring-specialist`

**Reference**: `audiobee_bluecard_national` (async architecture, most complete implementation)

### Tasks

1. Create `healthsparq/core/healthspark.py` from **audiobee_bluecard_national** (async reference)
2. Create `healthsparq/core/session.py` integrating **shared_package** (MANDATORY)
3. Create `healthsparq/core/file_writer.py` using FileWriteWorker pattern
4. Parameterize all hardcoded values to use config
5. Add healthsparq-server health check before execution

### Deliverables

```
healthsparq/
├── core/
│   ├── __init__.py              # Exports: HealthSpark, HealthSparkConfig
│   ├── healthspark.py           # Unified API wrapper (~400 LOC)
│   ├── session.py               # Session management (~100 LOC)
│   └── file_writer.py           # FileWriteWorker (~150 LOC)
└── tests/
    ├── test_healthspark.py      # Unit tests
    └── test_session.py          # Session tests
```

### Verification Commands

```bash
# All must return exit code 0
python -c "from healthsparq.core import HealthSpark, HealthSparkConfig"
python -c "from healthsparq.core.session import create_session"
python -c "from healthsparq.core.file_writer import FileWriteWorker"
pytest healthsparq/tests/test_healthspark.py -v
wc -l healthsparq/core/healthspark.py | awk '{if($1<600) exit 0; else exit 1}'
```

### Success Criteria

- [ ] `HealthSpark` class instantiates with config
- [ ] All imports resolve without error
- [ ] `healthspark.py` under 600 LOC (extracted from 1100 LOC)
- [ ] No hardcoded domains, plan codes, or states
- [ ] `pytest healthsparq/tests/test_healthspark.py` passes

### Ralph Loop Command

```bash
/ralph-loop "Migrate core healthspark module.
1. Extract HealthSpark class from audiobee_christus_health_plan/healthspark.py
2. Parameterize all config: domain, brand_code, insurer_code, plans
3. Integrate with shared_package session management
4. Create FileWriteWorker for async file output
5. Write unit tests with mocked HTTP responses
6. Target: healthspark.py under 600 LOC
7. Verify: pytest healthsparq/tests/test_healthspark.py exits 0
Output PHASE_4_COMPLETE when done." --max-iterations 20
```

---

## PHASE 5: Phase Execution Modules

**Goal**: Implement search, details, and normalize phases

**Subagent**: `python-pro`

### Tasks

1. Create `healthsparq/phases/search.py` from index_1_async.py
2. Create `healthsparq/phases/details.py` from index_2.py
3. Create `healthsparq/phases/normalize.py` from index_3.py
4. Wire phases to CLI run command

### Deliverables

```
healthsparq/
├── phases/
│   ├── __init__.py              # Exports: run_search, run_details, run_normalize
│   ├── search.py                # Phase 1 (~300 LOC)
│   ├── details.py               # Phase 2 (~200 LOC)
│   └── normalize.py             # Phase 3 (~200 LOC)
├── utils/
│   ├── geocode.py               # Geocoding utilities
│   └── filters.py               # Filter strategies
└── tests/
    ├── test_search.py
    ├── test_details.py
    └── test_normalize.py
```

### Verification Commands

```bash
# All must return exit code 0
python -c "from healthsparq.phases import run_search, run_details, run_normalize"
pytest healthsparq/tests/test_search.py -v
pytest healthsparq/tests/test_details.py -v
pytest healthsparq/tests/test_normalize.py -v
wc -l healthsparq/phases/search.py | awk '{if($1<400) exit 0; else exit 1}'
```

### Success Criteria

- [ ] All phase functions importable
- [ ] Each phase under 400 LOC
- [ ] Phase functions accept config as parameter (no globals)
- [ ] Tests pass for each phase
- [ ] CLI `--phase 1|2|3` option works

### Ralph Loop Command

```bash
/ralph-loop "Implement phase execution modules.
1. Extract search logic from audiobee_bluecard_national/index_1_async.py (async reference)
2. Extract details logic from audiobee_bluecard_national/index_2.py
3. Extract normalize logic from index_3.py
4. Wire to CLI run command with --phase option
5. Integrate shared_package session management
6. Target: each phase under 400 LOC
7. Verify: pytest healthsparq/tests/test_*.py exits 0
Output PHASE_3_COMPLETE when done." --max-iterations 20
```

---

## PHASE 4: Project Configuration Generation

**Goal**: Create YAML configs for all 25 healthsparq projects

**Subagent**: `Explore` (discovery) + `general-purpose` (generation)

### Tasks

1. Identify all healthsparq projects via pattern matching
2. Extract config values from each legacy config.py
3. Generate YAML config for each project
4. Validate all configs load correctly

### Subagent Delegation

```
Task 1: Explore agent discovers all audiobee_* projects with healthspark patterns
Task 2: general-purpose agent extracts config values per project
Task 3: general-purpose agent generates YAML configs in batch
```

### Deliverables

```
healthsparq/
└── configs/
    ├── _base.yaml
    ├── bluecard_national.yaml       # Reference implementation
    ├── christus_health_plan.yaml
    ├── excellus.yaml
    ├── ibx.yaml
    ├── mvp_health.yaml
    ├── medica.yaml
    ├── ... (19 more configs)
    └── PROJECT_LIST.md              # Generated project inventory (25 total)
```

### Verification Commands

```bash
# All must return exit code 0
python -m healthsparq list --count # Returns 25
python -m healthsparq doctor       # Health check passes
for cfg in healthsparq/configs/*.yaml; do python -m healthsparq validate $(basename $cfg .yaml) || exit 1; done
```

### Success Criteria

- [ ] 25 YAML configs created (one per healthsparq project)
- [ ] All configs pass validation
- [ ] `python -m healthsparq list` shows 25 projects
- [ ] Each config matches legacy config.py values
- [ ] PlanConfig includes: insurerCode, brandCode, productCode, state (per data integrity review)

### Ralph Loop Command

```bash
/ralph-loop "Generate project configurations for all 25 healthsparq projects.
1. Find all audiobee_* folders with healthspark.py patterns
2. Extract: domain, brand_code, insurer_code, plans (with insurerCode/brandCode/state), coverage states
3. Generate YAML config for each project following PROJECT_CONFIG_SCHEMA.md
4. Validate all configs load correctly
5. Verify: python -m healthsparq list --count returns 25
Output PHASE_4_COMPLETE when done." --max-iterations 15
```

---

## PHASE 7: End-to-End Validation

**Goal**: Verify singleton produces identical output to legacy scrapers

**Subagent**: `test-automator`

### Tasks

1. Run legacy scraper for test project (dry-run or limited)
2. Run singleton scraper with same parameters
3. Compare outputs for data equivalence
4. Create regression test suite

### Verification Commands

```bash
# Comparison script (to be created)
python healthsparq/tests/compare_outputs.py \
  --legacy audiobee_christus_health_plan/20251226/processed \
  --singleton healthsparq/output/christus_health_plan/20251226/processed \
  --threshold 0.99

# Must exit 0 if outputs match within threshold
```

### Success Criteria

- [ ] Output structure matches (same fields, same format)
- [ ] Provider counts within 1% (timing variations)
- [ ] NPI deduplication works correctly
- [ ] All phases execute without error
- [ ] Regression tests pass

### Ralph Loop Command

```bash
/ralph-loop "Validate healthsparq singleton against legacy.
1. Create comparison test script
2. Run both legacy and singleton for christus_health_plan
3. Compare outputs with diff analysis
4. Create regression test capturing comparison
5. Verify: comparison script exits 0 with 99% match
Output PHASE_7_COMPLETE when done." --max-iterations 10
```

---

## PHASE 8: Documentation & Cleanup

**Goal**: Complete documentation and deprecate legacy folders

**Subagent**: `docs-architect`

### Tasks

1. Update README.md with singleton usage
2. Add deprecation notices to legacy CLAUDE.md files
3. Update docs/site-type-mapping.md
4. Create healthsparq/README.md

### Deliverables

```
healthsparq/
├── README.md                    # Package documentation
└── docs/
    └── USAGE.md                 # Detailed usage guide

# Legacy updates
audiobee_*/CLAUDE.md             # Add: "DEPRECATED - Use healthsparq run <slug>"
```

### Verification Commands

```bash
# All must return exit code 0
ls healthsparq/README.md
grep -l "DEPRECATED" audiobee_christus_health_plan/CLAUDE.md
cat healthsparq/README.md | grep -q "healthsparq run"
```

### Success Criteria

- [ ] `healthsparq/README.md` exists with usage examples
- [ ] Legacy CLAUDE.md files have deprecation notice
- [ ] Main docs updated to reference singleton
- [ ] No broken internal links

### Ralph Loop Command

```bash
/ralph-loop "Complete healthsparq documentation.
1. Create healthsparq/README.md with installation and usage
2. Add deprecation notices to legacy CLAUDE.md files
3. Update main project documentation
4. Verify: README.md exists and contains usage examples
Output PHASE_8_COMPLETE when done." --max-iterations 5
```

---

## Subagent Delegation Summary

| Phase | Primary Subagent              | Delegation Rationale                      |
| ----- | ----------------------------- | ----------------------------------------- |
| 0     | `test-automator`              | Test framework setup, fixtures            |
| 1     | `architect-reviewer`          | Package structure, architectural patterns |
| 2     | `code-simplifier`             | Clean config schema, no over-engineering  |
| 3     | `python-pro`                  | Typer CLI, async patterns                 |
| 4     | `refactoring-specialist`      | Code extraction, safe transformations     |
| 5     | `python-pro`                  | Async execution, Python best practices    |
| 6     | `Explore` + `general-purpose` | Discovery + batch generation              |
| 7     | `test-automator`              | Validation suite, regression tests        |
| 8     | `docs-architect`              | Technical documentation                   |

### Subagent Invocation Pattern

```python
# In orchestrator or Ralph loop
from claude_code import Task

# Phase 0 example
await Task(
    description="Setup test infrastructure",
    prompt="""Create test infrastructure for healthsparq:
    1. Create healthsparq/tests/ with conftest.py
    2. Add mock fixtures from audiobee_christus_health_plan
    3. Verify pytest collects tests successfully""",
    subagent_type="test-automator"
)

# Phase 6 example - parallel discovery + generation
results = await asyncio.gather(
    Task(
        description="Discover healthsparq projects",
        prompt="Find all audiobee_* folders with healthspark patterns",
        subagent_type="Explore"
    ),
    Task(
        description="Generate project configs",
        prompt="Generate YAML configs from discovered project list",
        subagent_type="general-purpose"
    )
)
```

---

## Full Autonomous Execution

### Option 1: Phase-by-Phase (Recommended)

```bash
# Generate and execute each phase prompt
for phase in 0 1 2 3 4 5 6 7 8; do
  # Generate prompt
  uv run tools/healthsparq_executor.py prompt --phase $phase

  # Execute with Ralph Wiggum (copy the generated prompt)
  # /ralph-loop "<prompt>" --max-iterations 20

  # Verify completion
  uv run tools/healthsparq_executor.py verify --phase $phase
done
```

### Option 2: Full Pipeline (Advanced)

```bash
# Generate full execution prompt
uv run tools/healthsparq_executor.py run --all --dry-run

# Execute with Ralph Wiggum (copy the generated prompt)
# /ralph-loop "<prompt>" --max-iterations 100
```

### Option 3: Interactive Execution

```bash
# Run next pending phase (shows prompt to execute)
uv run tools/healthsparq_executor.py run

# Check status at any time
uv run tools/healthsparq_executor.py status

# View execution log
uv run tools/healthsparq_executor.py log
```

---

## Architecture Reference

### Directory Structure (Final)

```
scraping/
├── healthsparq/                    # Singleton package
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── schema.py
│   │   └── loader.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── healthspark.py
│   │   ├── session.py
│   │   └── file_writer.py
│   ├── phases/
│   │   ├── __init__.py
│   │   ├── search.py
│   │   ├── details.py
│   │   └── normalize.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── geocode.py
│   │   └── filters.py
│   ├── configs/
│   │   ├── _base.yaml
│   │   └── *.yaml (25 projects)
│   └── tests/
│       ├── conftest.py
│       ├── fixtures/
│       └── test_*.py
│
├── shared_package/                 # Reused session management
└── audiobee_*/                     # Legacy (deprecated)
```

---

## Session Management (Pure Python - No Server Dependency)

Based on `audiobee_bluecard_national` reference implementation, healthsparq uses **pure Python** session management without requiring the Node.js healthsparq-server.

### Architecture Pattern

```python
# healthsparq/core/session.py
from shared_package.session import HttpSession, ResilientBrowserSession
from shared_package.proxy import ProxyType

class HealthSparkSession:
    """
    Two-phase session: Browser for auth, HttpSession for API calls.

    Pattern from audiobee_bluecard_national/healthspark.py:
    1. Use ResilientBrowserSession ONLY for initial login
    2. Extract cookies/user-agent from browser
    3. Create lightweight HttpSession with extracted auth
    4. Close browser (no longer needed)
    """

    def __init__(self, proxy_type: ProxyType = ProxyType.DECODO_DC_STATIC):
        self._session: HttpSession | None = None
        self._browser_session = ResilientBrowserSession(proxy_types=[proxy_type])
        self._session_lock = asyncio.Lock()

    async def ensure_session(self, auth_url: str) -> HttpSession:
        """Initialize session with browser-based auth extraction."""
        async with self._session_lock:
            if self._session is None:
                # Phase 1: Browser login (one-time)
                await self._browser_session.login(auth_url)

                # Phase 2: Extract auth from browser
                cookies = await self._browser_session.get_cookies()
                user_agent = await self._browser_session.get_user_agent()

                # Phase 3: Create native HTTP session
                self._session = HttpSession()
                await self._session.initialize_from_browser(cookies, user_agent)

                # Phase 4: Close browser (no longer needed)
                await self._browser_session.close()
                self._browser_session = None

        return self._session

    async def close(self):
        """Cleanup resources."""
        if self._session:
            await self._session.close()
            self._session = None
```

### Benefits Over healthsparq-server

| Aspect               | Node.js Server     | Pure Python                               |
| -------------------- | ------------------ | ----------------------------------------- |
| **Dependencies**     | Node.js + npm      | Python only                               |
| **Deployment**       | 2 processes        | 1 process                                 |
| **Port conflicts**   | Port 1018 required | No ports                                  |
| **Auth handling**    | HTTP API           | Direct method calls                       |
| **Session recovery** | Manual restart     | Auto-recreate via ResilientBrowserSession |

### Session Recovery (Built-in)

`ResilientBrowserSession` from shared_package handles automatic session recreation on:

- 401/403 (auth failures)
- 429 (rate limiting)
- Browser crashes
- Proxy failures

```python
# Example from audiobee_bluecard_national/healthspark.py
# Auto-retry with session refresh on auth errors
if response.status_code in [401, 403]:
    self._session = None  # Force session refresh on next attempt
```

---

## CLI Enhancements (Post-Review)

Based on agent-native review, add these CLI commands:

### Priority 1: Required for Agent Operations

```bash
# Health check command (agent-friendly)
healthsparq doctor
# Output:
# Package:     [OK] healthsparq v1.0.0
# Sessions:    [OK] shared_package.session available
# Proxies:     [OK] DECODO_DC_STATIC configured
# Configs:     [OK] 25 projects loaded
# Tests:       [OK] 47 tests collected
# Exit code: 0

# Machine-readable status
healthsparq status --json
# {"jobs": [{"project": "excellus", "phase": "search", "progress": 45, "pid": 12345}]}

# Job cancellation (for stuck jobs)
healthsparq cancel <project>

# Project count verification
healthsparq list --count
# 25
```

### Priority 2: Enhanced Validation

```bash
# Output validation after scrape
healthsparq audit YYYYMMDD < project > --curr
# Runs type_check.py + schema validation + record count checks

# Simulate with mock responses
healthsparq run YYYYMMDD --simulate < project > --curr
```

### Exit Codes (Extended)

| Code | Meaning                               |
| ---- | ------------------------------------- |
| 0    | Success                               |
| 1    | Configuration error                   |
| 2    | Runtime error (all phases failed)     |
| 3    | Network/API error                     |
| 4    | Validation failure                    |
| 5    | Partial success (some plans failed)   |
| 6    | Timeout exceeded                      |
| 7    | Cancelled by user/agent               |
| 8    | Session/browser initialization failed |

---

## Data Integrity Requirements (Post-Review)

Based on data-integrity-guardian review:

### PlanConfig Schema (COMPLETE)

```python
class PlanConfig(BaseModel):
    """Plan configuration - includes ALL required API fields."""
    product_code: str = Field(..., description="HealthSparq product code")
    name: str = Field(..., description="Human-readable plan name")
    insurer_code: str = Field(..., description="API insurer code")
    brand_code: str = Field(..., description="API brand code")
    state: Optional[str] = Field(default=None, description="State-specific plan")
    enabled: bool = Field(default=True)
```

### DIRS Type Safety

```python
# Backward-compatible export (strings, not Paths)
DIRS = {k: str(v) for k, v in _config.dirs.items()}
```

---

## Project List (Validated: 25 Projects)

```
1. audiobee_alliance_trilogy
2. audiobee_amerihealth_administrators_pa
3. audiobee_amerihealth_caritas_fl
4. audiobee_amerihealth_caritas_vip_de
5. audiobee_amerihealth_nj
6. audiobee_asuris_northwest
7. audiobee_bluecard_national (ASYNC REFERENCE)
8. audiobee_capital_blue
9. audiobee_christus_health_plan
10. audiobee_excellus
11. audiobee_first_choice_sc
12. audiobee_health_plan_nv_medicaid
13. audiobee_highmark_wholecare
14. audiobee_hma
15. audiobee_ibx
16. audiobee_maine_community_health_options
17. audiobee_medica
18. audiobee_medica_sg
19. audiobee_medical_mutual
20. audiobee_mvp_health
21. audiobee_quartz
22. audiobee_sentara
23. audiobee_tufts_health_plans
24. audiobee_wellmark
25. audiobee_wellmark_medicare
```

---

## Outstanding Recommendations (From Agent Reviews)

Based on the 20-agent review, these items should be addressed during implementation:

### P0: Critical for Phase 4

**Automated Config Extraction Script** (Legacy Migration #870)

```python
# healthsparq/utils/migrate_config.py
"""Extract config values from legacy config.py files to YAML."""
import ast
import yaml
from pathlib import Path

def extract_legacy_config(project_path: Path) -> dict:
    """Parse legacy config.py and extract structured values."""
    config_py = project_path / "config.py"
    if not config_py.exists():
        raise FileNotFoundError(f"No config.py in {project_path}")

    tree = ast.parse(config_py.read_text())
    config = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name = target.id
                    if name == "PLANS":
                        config["plans"] = ast.literal_eval(compile(
                            ast.Expression(node.value), "<string>", "eval"))
                    elif name == "REQ_STATES":
                        config["states"] = ast.literal_eval(compile(
                            ast.Expression(node.value), "<string>", "eval"))
    return config

def generate_yaml_config(legacy_config: dict, project_slug: str) -> str:
    """Generate YAML config from extracted legacy values."""
    yaml_config = {
        "project": {"name": f"audiobee_{project_slug}", "slug": project_slug},
        "site": {
            "domain": f"{project_slug}.healthsparq.com",  # May need manual correction
            "brand_code": legacy_config.get("plans", [{}])[0].get("brandCode", "UNKNOWN"),
            "insurer_code": legacy_config.get("plans", [{}])[0].get("insurerCode", "UNKNOWN"),
        },
        "plans": [
            {"product_code": p.get("productCode"), "name": p.get("productCode", "").replace("_", " ").title()}
            for p in legacy_config.get("plans", [])
        ],
        "coverage": {"states": legacy_config.get("states", [])},
    }
    return yaml.dump(yaml_config, default_flow_style=False, sort_keys=False)
```

### P1: Before Phase 1 Completion

**Register HealthsparqConfig in shared_package** (Pattern Consistency #855)

```python
# shared_package/config/__init__.py (updated)
from .base import BaseConfig
from .healthsparq import HealthsparqConfig
from .sapphire import SapphireConfig

CONFIG_REGISTRY = {
    "healthsparq": HealthsparqConfig,
    "sapphire": SapphireConfig,
    # ... other site types
}

def load_config(site_type: str, project_name: str) -> BaseConfig:
    """Unified factory for all site types."""
    config_class = CONFIG_REGISTRY.get(site_type)
    if config_class is None:
        raise ValueError(f"Unknown site type: {site_type}")
    return config_class(project_name=project_name)
```

### P1: Test Strategy Enhancement (Testing Strategy #859)

**Multi-Project Fixtures** - Create fixtures from 3 representative projects:

1. `audiobee_bluecard_national` - National coverage, async (51 states)
2. `audiobee_christus_health_plan` - Multi-state regional (LA, NM, TX)
3. `audiobee_excellus` - Single-state (NY only)

```
healthsparq/tests/fixtures/
├── bluecard_national/
│   ├── mock_search_response.json
│   └── mock_provider_detail.json
├── christus_health_plan/
│   ├── mock_search_response.json
│   └── mock_provider_detail.json
└── excellus/
    ├── mock_search_response.json
    └── mock_provider_detail.json
```

### P2: Operational Runbooks (Spec Completeness #876)

Create `healthsparq/docs/OPERATIONS.md` covering:

1. **New Project Onboarding** - Step-by-step for adding new healthsparq carriers
2. **Debugging Failed Scrapes** - Log analysis, common error patterns
3. **Output Comparison Guide** - Interpreting diff results, acceptable variance
4. **Rate Limiting Recovery** - 429 handling, backoff strategies
5. **healthsparq-server Issues** - Server restart, health check failures

### P3: Checkpoint/Resume Capability (Workflow Patterns #868)

```python
# healthsparq/core/checkpoint.py
"""Enable mid-phase recovery for long-running scrapes."""
import json
from pathlib import Path

class PhaseCheckpoint:
    def __init__(self, project: str, phase: int, date: str):
        self.checkpoint_file = Path(f"{date}/checkpoints/{project}_phase{phase}.json")

    def save(self, state: dict) -> None:
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        self.checkpoint_file.write_text(json.dumps(state))

    def load(self) -> dict | None:
        if self.checkpoint_file.exists():
            return json.loads(self.checkpoint_file.read_text())
        return None

    def clear(self) -> None:
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
```

---

## Related Documents

- [PROJECT_CONFIG_SCHEMA.md](./PROJECT_CONFIG_SCHEMA.md) - YAML schema with Pydantic models
- [CLI_DESIGN.md](./CLI_DESIGN.md) - Full CLI specification
- [MIGRATION_CHECKLIST.md](./MIGRATION_CHECKLIST.md) - Per-project migration tasks
- [../SHARED_PACKAGE_SPEC.md](../SHARED_PACKAGE_SPEC.md) - Shared utilities specification
- [../ENV_MANAGEMENT_GUIDE.md](../ENV_MANAGEMENT_GUIDE.md) - Environment variable management

# Unified Scraping Framework

## Overview

Transform 94 isolated web scrapers into a unified framework with centralized configuration, shared dependencies, and consistent operational patterns. The goal is to reduce maintenance burden from ~100+ isolated projects to a single, scalable framework supporting all platform types.

## Problem Statement

### Current Pain Points

| Issue                              | Impact                                                          | Evidence                                                        |
| ---------------------------------- | --------------------------------------------------------------- | --------------------------------------------------------------- |
| **Fragmented Configuration**       | Manual `PREV_DATE`/`CURR_DATE` updates required before each run | 32 carrier projects use Python `config.py` with hardcoded dates |
| **Isolated Virtual Environments**  | 22+ separate `.venv/` directories with dependency duplication   | ~2GB disk space waste, version drift between projects           |
| **Inconsistent Project Structure** | Different patterns across platform types                        | `index_*.py` vs `run_all.py` vs library-based                   |
| **Mixed Concurrency Models**       | ThreadPoolExecutor, async/await, worker queues                  | Hard to tune performance, debugging complexity                  |
| **No Unified CLI**                 | Different invocation patterns per project type                  | Ops team needs to know 7 different patterns                     |
| **No Centralized Monitoring**      | Ad-hoc logging, no metrics aggregation                          | Failures discovered late, no trend visibility                   |

### Current State Diagram

```mermaid
graph TB
    subgraph "Current: Isolated Projects"
        A1[audiobee_bcbs_il<br/>config.py + index_*.py<br/>.venv/]
        A2[audiobee_medica_sg<br/>config.yaml<br/>uses healthsparq lib]
        A3[audiobee_sapphire_1<br/>config.py + run_all.py<br/>.venv/]
        A4[audiobee_anthem_1<br/>config.py + custom scripts<br/>.venv/]

        C[core/ submodule]
        H[healthsparq/ library]

        A1 -->|imports| C
        A2 -->|imports| H
        H -->|imports| C
        A3 -->|imports| C
        A4 -->|imports| C
    end
```

### Target State Diagram

```mermaid
graph TB
    subgraph "Target: Unified Framework"
        CLI["python -m ideon run &lt;project&gt;<br/>--curr YYYYMMDD"]

        subgraph "ideon/ Framework"
            CORE[core/<br/>Config, I/O, Session, QA]
            PLATFORMS["platforms/<br/>healthsparq/ sapphire/<br/>carrier/ anthem/"]
            CONFIGS[configs/<br/>94 YAML files]
        end

        CLI --> CORE
        CLI --> PLATFORMS
        CLI --> CONFIGS
        PLATFORMS --> CORE
    end
```

## Proposed Solution

### Architecture

```
ideon_scraping/
├── ideon/                          # New unified framework
│   ├── __init__.py                 # Public API
│   ├── cli.py                      # Typer CLI entry point
│   ├── config/                     # Pydantic config system
│   │   ├── base.py                 # BaseScraperConfig
│   │   ├── schema_v1.py            # Config schema version 1
│   │   └── loader.py               # YAML → Pydantic loader
│   ├── platforms/                  # Platform-specific libraries
│   │   ├── base.py                 # AbstractPlatform contract
│   │   ├── healthsparq/            # Existing healthsparq/ migrated
│   │   ├── sapphire/               # New: ProviderFinderOnline
│   │   ├── carrier/                # New: Direct API scrapers
│   │   └── anthem/                 # New: Wellpoint multi-phase
│   ├── middleware/                 # Cross-cutting concerns
│   │   ├── retry.py                # Retry with exponential backoff
│   │   ├── proxy.py                # Proxy rotation
│   │   ├── rate_limit.py           # Rate limiting
│   │   └── circuit_breaker.py      # Circuit breaker pattern
│   ├── runners/                    # Execution engines
│   │   ├── single.py               # Single project runner
│   │   └── bulk.py                 # Parallel multi-project runner
│   └── monitoring/                 # Observability
│       ├── metrics.py              # Prometheus metrics
│       └── logging.py              # Structured logging
├── configs/                        # All project configs (YAML)
│   ├── healthsparq/                # 23 configs
│   ├── sapphire/                   # 14 configs
│   ├── carrier/                    # 32 configs
│   └── anthem/                     # 3 configs + others
├── core/                           # Existing shared utilities
├── scripts/                        # Migration tools
│   └── migrate_to_yaml.py          # config.py → config.yaml converter
├── pyproject.toml                  # Monorepo dependencies with uv
├── uv.lock                         # Single dependency lock file
└── .env.example                    # Environment template
```

### CLI Interface

```bash
# Run single project
python -m ideon run medica_sg --curr 20251230

# Run single project with explicit prev date
python -m ideon run medica_sg --curr 20251230 --prev 20251130

# Dry run (validate config + test connectivity)
python -m ideon run medica_sg --curr 20251230 --dry-run

# Run with debug logging
python -m ideon run medica_sg --curr 20251230 --debug

# List all projects
python -m ideon list
python -m ideon list --platform healthsparq --format json

# Validate config without running
python -m ideon validate medica_sg

# Run bulk (parallel execution)
python -m ideon run-bulk --platform healthsparq --workers 8 --curr 20251230
python -m ideon run-bulk --projects projects/priority.txt --workers 4 --curr 20251230

# Migration helper
python -m ideon migrate audiobee_bcbs_il --output configs/carrier/bcbs_il.yaml

# QA validation
python -m ideon qa validate medica_sg --curr 20251230
python -m ideon qa compare medica_sg --curr 20251230 --prev 20251130
```

### Configuration Schema (v1)

```yaml
# configs/healthsparq/medica_sg.yaml
schema_version: 1

project:
  name: Medica Small Group
  slug: medica_sg
  platform: healthsparq
  description: Medica Small Group provider directory

site:
  domain: providers.medica.com
  brand_code: MEDICA
  api_version: v2

plans:
  - product_code: SG
    name: Small Group PPO
    network_id: "210001010"
  - product_code: MA
    name: Medicare Advantage
    network_id: "210001020"

coverage:
  states: [MN, WI, ND, SD]
  # OR geographic search
  search_grid:
    type: zip_codes
    source: data/zip_codes_midwest.csv

extraction:
  phases: [search, details, normalize]
  # OR custom phases
  # phases: [search, details, affiliations, normalize]

concurrency:
  max_workers: 25
  request_delay: 0.5
  batch_size: 100

retry:
  max_attempts: 3
  backoff: exponential
  base_delay: 1.0
  respect_retry_after: true

browser:
  backend: patchright # playwright | patchright | camoufox
  headless: true
  timeout: 30000

output:
  format: jsonl # jsonl | parquet | csv
  compression: null # zstd | gzip | null

# Secrets loaded from environment: MEDICA_SG_API_KEY, etc.
```

### Platform Base Class Contract

```python
# ideon/platforms/base.py
from abc import ABC, abstractmethod
from typing import Iterator, AsyncIterator
from dataclasses import dataclass
from ideon.config import BaseScraperConfig

@dataclass
class SearchResult:
    """Result from Phase 1 search."""
    provider_id: str
    npi: str | None
    name: str
    metadata: dict

@dataclass
class ProviderDetail:
    """Result from Phase 2 detail extraction."""
    provider_id: str
    raw_data: dict

@dataclass
class NormalizedProvider:
    """Final normalized provider record."""
    npi: str
    first_name: str
    last_name: str
    specialty: str
    # ... full schema

class AbstractPlatform(ABC):
    """Base class for all platform implementations."""

    def __init__(self, config: BaseScraperConfig):
        self.config = config

    @abstractmethod
    async def search(self) -> AsyncIterator[SearchResult]:
        """Phase 1: Discover providers."""
        ...

    @abstractmethod
    async def extract(self, result: SearchResult) -> ProviderDetail:
        """Phase 2: Extract provider details."""
        ...

    @abstractmethod
    def normalize(self, detail: ProviderDetail) -> NormalizedProvider:
        """Phase 3: Normalize to output schema."""
        ...

    # Optional hooks (default implementations provided)
    async def setup(self) -> None:
        """Called before pipeline starts."""
        pass

    async def teardown(self) -> None:
        """Called after pipeline completes."""
        pass

    def on_error(self, error: Exception, context: dict) -> None:
        """Called on each error for custom handling."""
        pass
```

### Middleware Chain

```python
# ideon/middleware/base.py
from typing import Callable, Awaitable, TypeVar

T = TypeVar('T')

class Middleware:
    """Base middleware class."""

    async def __call__(
        self,
        handler: Callable[..., Awaitable[T]],
        *args,
        **kwargs
    ) -> T:
        return await handler(*args, **kwargs)

class MiddlewareChain:
    """Composable middleware chain."""

    def __init__(self, middlewares: list[Middleware]):
        self.middlewares = middlewares

    def wrap(self, handler: Callable) -> Callable:
        for middleware in reversed(self.middlewares):
            handler = middleware(handler)
        return handler

# Example: Retry + RateLimit + Proxy
chain = MiddlewareChain([
    RetryMiddleware(max_attempts=3, backoff=exponential_backoff),
    RateLimitMiddleware(requests_per_second=2),
    ProxyMiddleware(rotation_strategy="round_robin"),
])

@chain.wrap
async def fetch_provider(url: str) -> dict:
    ...
```

## Technical Considerations

### Architecture Impacts

1. **Monorepo Dependency Management**
   - Use `uv` workspaces with shared `pyproject.toml`
   - Platform-specific optional dependencies: `uv pip install -e ".[healthsparq]"`
   - Single `uv.lock` at repository root

2. **Browser Backend Coexistence**
   - All three backends (Playwright, Patchright, Camoufox) installed in single virtualenv
   - Backend selection via config: `browser.backend: patchright`
   - Lazy loading to avoid import overhead

3. **Config Schema Evolution**
   - Schema version field: `schema_version: 1`
   - Backward compatibility: Framework supports N-1 versions
   - Migration scripts for breaking changes

### Performance Implications

| Metric                      | Current              | Target          | Improvement        |
| --------------------------- | -------------------- | --------------- | ------------------ |
| Dependency install time     | 22 × 2min = 44min    | 1 × 3min = 3min | **93% faster**     |
| Disk space (venvs)          | ~2.2GB               | ~100MB          | **95% smaller**    |
| Config update overhead      | Manual editing       | CLI-driven      | **100% automated** |
| Parallel execution overhead | Manual orchestration | Built-in runner | **Simplified ops** |

### Security Considerations

1. **Secrets Management**
   - Environment variables with project prefix: `MEDICA_SG_API_KEY`
   - `.env` files per environment (`.env.development`, `.env.production`)
   - No secrets in YAML configs (validated by pre-commit hook)

2. **Proxy Credentials**
   - Proxy URLs from environment: `PROXY_URLS=["http://proxy1:8080"]`
   - Support for authenticated proxies: `http://user:pass@proxy:8080`

## Acceptance Criteria

### Functional Requirements

- [ ] `python -m ideon run <project> --curr YYYYMMDD` works for all 94 projects
- [ ] `python -m ideon list` shows all projects with platform, status, last run
- [ ] `python -m ideon validate <project>` validates config without running
- [ ] `python -m ideon run-bulk` executes multiple projects in parallel
- [ ] `python -m ideon migrate <legacy_project>` converts config.py to YAML
- [ ] Date auto-calculation: `--curr` without `--prev` infers from cadence config
- [ ] Dry run mode: `--dry-run` validates config and tests connectivity
- [ ] Debug mode: `--debug` enables verbose logging

### Non-Functional Requirements

- [ ] Single virtualenv for all 94 projects (no per-project venvs)
- [ ] Config validation fails fast (before any network requests)
- [ ] Prometheus metrics exported at `/metrics` endpoint
- [ ] Structured JSON logs with correlation IDs
- [ ] Migration script converts 80%+ of legacy configs automatically

### Quality Gates

- [ ] All existing tests pass after migration
- [ ] Output equivalence: Unified framework produces identical output to legacy
- [ ] Performance regression: No more than 10% slowdown vs legacy
- [ ] Test coverage: >80% for new ideon/ code

## Success Metrics

| Metric                         | Current State             | Target          | Measurement Method |
| ------------------------------ | ------------------------- | --------------- | ------------------ |
| Time to add new scraper        | 2-4 hours                 | 30 min          | Stopwatch          |
| Config update time             | 5-10 min (manual editing) | 1 min (CLI)     | Stopwatch          |
| Dependency update time         | 22 × venvs × 2min         | 1 × venv × 3min | CI timing          |
| Mean time to detect failure    | Hours (manual monitoring) | <5 min (alerts) | Prometheus         |
| Cross-project code duplication | ~40%                      | <10%            | CodeClimate        |

## Dependencies & Prerequisites

### Internal Dependencies

- `core/` package (already exists, v3.0)
- `healthsparq/` library (already exists, v2.0) - will be migrated under `ideon/platforms/`
- Existing project configs (94 projects across 7 platform types)

### External Dependencies

```toml
# pyproject.toml additions
[project.dependencies]
typer = ">=0.9.0"
pydantic = ">=2.0.1,<3.0.0"
pydantic-settings = ">=2.0.0,<3.0.0"
prometheus-client = ">=0.19.0"

[project.optional-dependencies]
healthsparq = ["httpx>=0.27.0", "curl-cffi>=0.7.0"]
sapphire = ["httpx>=0.27.0"]
carrier = ["httpx>=0.27.0", "curl-cffi>=0.7.0"]
browser = ["playwright>=1.55.0", "patchright>=1.0.0", "camoufox[geoip]>=0.4.11"]
```

### Blockers

1. **Question: Dependency Conflicts** - Need to verify `uv` can resolve healthsparq and sapphire requirements in single virtualenv
2. **Question: Browser Backend Coexistence** - Need to test Playwright + Patchright + Camoufox in same env
3. **Question: Migration Validation** - Need to define "output equivalence" criteria (NPI-based diff? Fuzzy match?)

## Risk Analysis & Mitigation

| Risk                                        | Probability | Impact | Mitigation                                                  |
| ------------------------------------------- | ----------- | ------ | ----------------------------------------------------------- |
| Dependency conflicts prevent monorepo       | Medium      | High   | Test with `uv` early; fallback to per-platform extras       |
| Migration breaks existing scrapers          | Medium      | High   | Keep legacy code during transition; run parallel validation |
| Performance regression in unified framework | Low         | Medium | Benchmark before/after; optimize hot paths                  |
| New platform type doesn't fit abstraction   | Low         | Medium | Design extensible base class with optional hooks            |
| Ops team rejects new CLI patterns           | Low         | Low    | Document migration guide; provide cheat sheet               |

## Implementation Phases

### Phase 1: Foundation (Estimated: 1 week)

**Goal**: Establish framework skeleton and prove dependency management works

- [ ] Create `ideon/` package structure
- [ ] Implement `BaseScraperConfig` with Pydantic
- [ ] Implement `AbstractPlatform` base class
- [ ] Set up monorepo `pyproject.toml` with optional dependencies
- [ ] Test `uv` dependency resolution with all platform requirements
- [ ] Basic CLI skeleton (`run`, `list`, `validate` subcommands)

**Files to create:**

- `ideon/__init__.py`
- `ideon/cli.py`
- `ideon/config/base.py`
- `ideon/config/loader.py`
- `ideon/platforms/base.py`
- `pyproject.toml` (update)

### Phase 2: HealthSparq Migration (Estimated: 3-4 days)

**Goal**: Migrate existing healthsparq/ library to unified framework

- [ ] Move `healthsparq/` code under `ideon/platforms/healthsparq/`
- [ ] Adapt to `AbstractPlatform` interface
- [ ] Migrate 23 configs from `healthsparq/configs/` to `configs/healthsparq/`
- [ ] Validate output equivalence for 3 representative projects
- [ ] Update imports in any external code

**Files to modify:**

- `healthsparq/` → `ideon/platforms/healthsparq/`
- `healthsparq/configs/*.yaml` → `configs/healthsparq/*.yaml`

### Phase 3: Sapphire Platform (Estimated: 3-4 days)

**Goal**: Create sapphire platform library from existing patterns

- [ ] Analyze existing 14 sapphire projects for common patterns
- [ ] Implement `ideon/platforms/sapphire/` with shared logic
- [ ] Create config schema for sapphire projects
- [ ] Migrate 14 projects to YAML configs
- [ ] Build migration script for sapphire `config.py` → YAML

**Files to create:**

- `ideon/platforms/sapphire/__init__.py`
- `ideon/platforms/sapphire/api.py`
- `ideon/platforms/sapphire/search.py`
- `ideon/platforms/sapphire/details.py`
- `ideon/platforms/sapphire/normalize.py`
- `configs/sapphire/*.yaml` (14 files)

### Phase 4: Carrier Platform (Estimated: 5-7 days)

**Goal**: Create carrier platform library for direct API scrapers

- [ ] Analyze existing 32 carrier projects for common patterns
- [ ] Identify sub-categories within carrier (REST API, GraphQL, etc.)
- [ ] Implement `ideon/platforms/carrier/` with extensible base
- [ ] Create config schema for carrier projects
- [ ] Migrate 32 projects to YAML configs
- [ ] Build migration script for carrier `config.py` → YAML

**Files to create:**

- `ideon/platforms/carrier/__init__.py`
- `ideon/platforms/carrier/base.py`
- `ideon/platforms/carrier/rest_api.py`
- `ideon/platforms/carrier/geographic_grid.py`
- `configs/carrier/*.yaml` (32 files)

### Phase 5: Middleware & Monitoring (Estimated: 3-4 days)

**Goal**: Implement cross-cutting concerns

- [ ] Implement `RetryMiddleware` with exponential backoff
- [ ] Implement `RateLimitMiddleware` with configurable rate
- [ ] Implement `ProxyMiddleware` with rotation strategies
- [ ] Implement `CircuitBreakerMiddleware`
- [ ] Add Prometheus metrics (success rate, duration, provider count)
- [ ] Add structured JSON logging with correlation IDs

**Files to create:**

- `ideon/middleware/retry.py`
- `ideon/middleware/rate_limit.py`
- `ideon/middleware/proxy.py`
- `ideon/middleware/circuit_breaker.py`
- `ideon/monitoring/metrics.py`
- `ideon/monitoring/logging.py`

### Phase 6: Remaining Platforms (Estimated: 3-4 days)

**Goal**: Migrate Anthem, HealthTrioConnect, Werally, Provider Lenz

- [ ] Implement `ideon/platforms/anthem/`
- [ ] Implement `ideon/platforms/healthtrioconnect/` (Node.js hybrid)
- [ ] Implement `ideon/platforms/werally/`
- [ ] Implement `ideon/platforms/providerlenz/`
- [ ] Migrate remaining ~12 projects to YAML configs

**Files to create:**

- `ideon/platforms/anthem/`
- `ideon/platforms/healthtrioconnect/`
- `ideon/platforms/werally/`
- `ideon/platforms/providerlenz/`
- `configs/anthem/*.yaml`, `configs/werally/*.yaml`, etc.

### Phase 7: Bulk Runner & QA (Estimated: 2-3 days)

**Goal**: Implement parallel execution and QA integration

- [ ] Implement `python -m ideon run-bulk` with worker pool
- [ ] Implement `python -m ideon qa validate` subcommand
- [ ] Implement `python -m ideon qa compare` subcommand
- [ ] Add resource limits (max memory, max file handles)
- [ ] Add progress reporting for bulk runs

**Files to create:**

- `ideon/runners/bulk.py`
- `ideon/cli_qa.py`

### Phase 8: Documentation & Cleanup (Estimated: 2-3 days)

**Goal**: Complete migration and document everything

- [ ] Write developer guide: "Adding Your First Scraper"
- [ ] Write ops runbook: "Running Scrapers in Production"
- [ ] Write migration guide: "Converting Legacy Projects"
- [ ] Update `CLAUDE.md` with unified patterns
- [ ] Remove legacy `shared_package/` references
- [ ] Archive old virtualenvs
- [ ] Create Grafana dashboard template

**Files to create/update:**

- `docs/guides/adding-scraper.md`
- `docs/guides/running-production.md`
- `docs/guides/migration.md`
- `monitoring/grafana-dashboard.json`
- `CLAUDE.md` (update)

## Alternative Approaches Considered

### Option A: Scrapy-Based Framework

**Approach**: Rebuild all scrapers as Scrapy spiders

**Pros:**

- Battle-tested framework with large community
- Built-in scheduling, pipelines, middleware
- Extensive documentation

**Cons:**

- Requires complete rewrite of all 94 scrapers
- Scrapy's Twisted-based async doesn't play well with Playwright
- Overkill for simple API scrapers
- Learning curve for team

**Decision**: Rejected - Too high migration cost, poor browser automation fit

### Option B: Keep Isolated Projects with Shared CLI

**Approach**: Create CLI that orchestrates existing isolated projects

**Pros:**

- No code changes to existing scrapers
- Lower risk migration
- Quick to implement

**Cons:**

- Doesn't solve dependency duplication
- Doesn't standardize configuration
- Maintenance burden remains high

**Decision**: Rejected - Doesn't address root causes

### Option C: Proposed Unified Framework (Selected)

**Approach**: Migrate to unified framework with platform libraries

**Pros:**

- Solves all pain points (config, deps, structure, monitoring)
- Builds on successful HealthSparq pattern
- Incremental migration possible
- Single dependency management

**Cons:**

- Moderate migration effort
- Risk of breaking existing scrapers during transition

**Decision**: Selected - Best balance of effort vs. benefit

## Future Considerations

### Extensibility

- Plugin system for custom platforms
- Hook system for pre/post processing
- Support for new data sources (not just provider directories)

### Long-Term Vision

- Web dashboard for scraper management
- Automated scheduling (cron → Kubernetes CronJob)
- Multi-tenant support (multiple clients, isolated data)
- ML-powered anomaly detection for data quality

## Documentation Plan

| Document         | Location                            | Status    |
| ---------------- | ----------------------------------- | --------- |
| Developer Guide  | `docs/guides/adding-scraper.md`     | To create |
| Ops Runbook      | `docs/guides/running-production.md` | To create |
| Migration Guide  | `docs/guides/migration.md`          | To create |
| API Reference    | Auto-generated from docstrings      | To create |
| CLAUDE.md Update | `CLAUDE.md`                         | To update |

## References & Research

### Internal References

- HealthSparq library pattern: `healthsparq/CLAUDE.md`
- Core utilities documentation: `core/CLAUDE.md`
- Existing architecture: `docs/onboarding/ARCHITECTURE.md`
- Project structure: `docs/PROJECT_STRUCTURE.md`

### External References

- [Scrapy Architecture](https://docs.scrapy.org/en/latest/topics/architecture.html) - Pipeline and middleware patterns
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) - Configuration management
- [Polars User Guide](https://docs.pola.rs/) - Data processing patterns
- [Patchright vs Playwright](https://dev.to/claudeprime/patchright-vs-playwright-when-to-use-the-stealth-browser-fork-382a) - Browser backend selection
- [Async Python 2025 Patterns](https://medium.com/@hadiyolworld007/async-python-2025-fast-safe-and-under-control-ee2c0e2b2bf6) - Concurrency patterns

### Related Work

- HealthSparq unification (completed): Successfully unified 23 projects
- Datastore abstraction (completed): `core/io/` with multiple backends
- Browser backend selection (completed): `core/session/browser_session.py`

---

## Open Questions

### Priority 1: Critical (Blocks Implementation)

1. **Config Schema Versioning**: How do we handle YAML config schema evolution without breaking existing scrapers?
   - Recommendation: Use `schema_version: 1` field, support N-1 backward compatibility

2. **Secrets Management**: Where do API keys, OAuth tokens, and proxy credentials live?
   - Recommendation: Environment variables with project prefix (`MEDICA_SG_API_KEY`)

3. **Date Auto-Calculation Logic**: When `--curr` without `--prev`, how is previous date inferred?
   - Recommendation: Per-project `cadence` config (daily/weekly/monthly)

4. **Migration Validation Strategy**: How do we prove unified framework output matches legacy?
   - Recommendation: NPI-based diff tool with fuzzy matching for non-NPI providers

### Priority 2: Important

5. **Retry Policy Configurability**: Can retry logic be customized per-project?
   - Recommendation: YAML config `retry: {max_attempts, backoff, base_delay}`

6. **Metrics Granularity**: What Prometheus labels? Per-project? Per-phase?
   - Recommendation: `{project, platform, phase, status}`, aggregated at batch level

7. **Config Inheritance**: Can YAML configs inherit from base configs?
   - Recommendation: Support `extends: platforms/healthsparq/base.yaml`

---

_Generated with Claude Code - 2025-12-30_

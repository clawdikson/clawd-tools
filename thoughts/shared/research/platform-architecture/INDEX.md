---
date: 2026-01-11
type: research-index
scope: platform-architecture
commit: 4b76867
---

# Platform Architecture Research Index

Central navigation for platform library documentation.

## Quick Links

| Document | Focus | When to Read |
|----------|-------|--------------|
| [Core Package](./01-core-package.md) | Shared utilities | Understanding foundation |
| [HealthSparq](./02-healthsparq.md) | HealthSparq platform | Working on HealthSparq projects |
| [Sapphire](./03-sapphire.md) | Sapphire platform | Working on Sapphire projects |
| [Patterns](./04-patterns.md) | Cross-cutting patterns | Learning architecture decisions |
| [Performance](./05-performance.md) | Optimizations | Debugging slowness, scaling |

## Architecture Overview

```
scraping/
├── core/                    # [01-core-package.md]
│   ├── config/              # Pydantic Settings, site-type registry
│   ├── io/                  # DataStore (JSONL/JSON/SQLite)
│   ├── session/             # Browser/HTTP management
│   ├── proxy/               # Multi-provider proxies
│   ├── logging/             # Loguru structured logging
│   ├── qa/                  # Validation, comparison
│   └── mapper/              # Normalization, dedup
│
├── healthsparq/             # [02-healthsparq.md]
│   ├── config/              # 23 YAML configs
│   ├── core/                # HealthSpark API
│   ├── phases/              # 6-phase pipeline
│   └── cli.py               # Typer CLI
│
├── sapphire/                # [03-sapphire.md]
│   ├── config/              # 15 YAML configs
│   ├── core/                # SapphireAPI
│   ├── phases/              # 5-phase pipeline
│   └── cli.py               # Typer CLI
│
└── audiobee_*/              # Individual projects
```

## Dependency Flow

```
audiobee_* projects
      │
      ├─► healthsparq/  ──┬─► core/
      │                   │
      └─► sapphire/  ─────┘
```

Both platform libraries depend on `core/` for:
- Configuration loading
- Storage abstractions
- Session management
- Normalization utilities
- QA/validation

## Key Concepts

### 1. Zero Global State

All configuration injected via Pydantic Settings. No globals.

**See**: [04-patterns.md#zero-global-state](./04-patterns.md#1-zero-global-state)

### 2. Protocol-Based Abstractions

DataStore, MapperFunc enable swappable implementations.

**See**: [04-patterns.md#protocol-abstractions](./04-patterns.md#2-protocol-based-abstractions)

### 3. Dual Interface

Both platforms work as CLI and importable library.

**See**: [04-patterns.md#dual-interface](./04-patterns.md#6-dual-cli--library-interface)

### 4. Phase Pipelines

| Phase | HealthSparq | Sapphire |
|-------|-------------|----------|
| 1 | Search | Discovery |
| 2 | Details | Details |
| 3 | Normalize | Normalize |
| 4 | QA | QA |
| 5 | Report | Report |
| 6 | Recovery | - |

**See**: [02-healthsparq.md#phases](./02-healthsparq.md#phase-pipeline) and [03-sapphire.md#phases](./03-sapphire.md#phase-pipeline)

## Common Tasks

### Adding a New HealthSparq Project

1. Create `healthsparq/configs/{slug}.yaml`
2. Optionally create custom mapper in `audiobee_{slug}/mapper.py`
3. Use `create_project_cli()` for thin wrapper

**See**: [02-healthsparq.md#adding-projects](./02-healthsparq.md#adding-a-new-project)

### Adding a New Sapphire Project

1. Create `sapphire/configs/{slug}.yaml`
2. Register custom mapper via `register_mapper()`
3. Use CLI or library interface

**See**: [03-sapphire.md#adding-projects](./03-sapphire.md#adding-a-new-project)

### Debugging Performance Issues

1. Check storage backend (`--storage sqlite` for large datasets)
2. Review BoundedSet size for deduplication
3. Consider HTTP session transfer instead of browser-only

**See**: [05-performance.md](./05-performance.md)

### Understanding Session Flow

1. Browser login for anti-bot
2. Cookie extraction
3. HTTP session for fast API calls

**See**: [01-core-package.md#session](./01-core-package.md#session-management)

## Open Questions

| Question | Status | Document |
|----------|--------|----------|
| Recovery phase for Sapphire? | Open | [03-sapphire.md](./03-sapphire.md) |
| Mapper pattern convergence? | Open | [04-patterns.md](./04-patterns.md) |
| Browser backend defaults? | Open | [01-core-package.md](./01-core-package.md) |

## Document Maintenance

When updating:
1. Update the specific document
2. Update this INDEX if adding new sections/concepts
3. Update cross-references if renaming sections

**Last Updated**: 2026-01-11

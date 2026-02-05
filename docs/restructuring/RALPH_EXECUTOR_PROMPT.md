# Ralph Wiggum Executor Prompt - Shared Package v3.0 Implementation

## Context

You are implementing the **Shared Package v3.0** based on the YAGNI-simplified plan. The following components have already been completed:

**✅ COMPLETED (v3.0 core)**:

- `pyproject.toml` with pydantic>=2.0.1
- `exceptions.py` with 4-class hierarchy (SharedPackageError, SessionError, ProxyError, ConfigError)
- `config/` module with simple CONFIG_TYPES dict (no registry pattern)
- `config/factory.py` without @overload decorators
- All site configs (sapphire, healthsparq, carrier, anthem) as simple classes

**❌ REMOVED (YAGNI - not needed)**:

- AsyncJSONL classes (all scrapers use sync I/O)
- TaskQueue module (use asyncio.Queue + tenacity)
- ErrorAggregation system (duplicates loguru)
- @with_timing decorator (use inline perf_counter)
- 13 additional exception classes (use Python built-ins)

## Your Mission

Implement the **remaining phases** from the Shared Package Implementation Plan v3.0, executing each phase autonomously in Ralph Wiggum style:

1. **Read the phase specification** from `docs/restructuring/SHARED_PACKAGE_IMPLEMENTATION_PLAN.md`
2. **Check what exists** in the current shared_package/
3. **Implement missing components** following v3.0 YAGNI principles
4. **Test your implementation** with verification commands
5. **Update progress tracker** in `docs/restructuring/SHARED_PACKAGE_PROGRESS.json`
6. **Commit your work** with clear messages
7. **Move to next phase** automatically

## Phase Execution Order (v3.0 Adjusted)

Execute in this order, skipping removed components:

### Phase 1: Package Infrastructure (P0) - PARTIALLY COMPLETE

**Status**: pyproject.toml ✅, py.typed ❌, **init**.py ❌

**Remaining Tasks**:

- [ ] Create `shared_package/py.typed` (PEP 561 type checking marker)
- [ ] Update `shared_package/__init__.py` with version, public API exports
- [ ] Verify flat layout configuration in pyproject.toml

**Skip**: None

**Verification**:

```bash
test -f shared_package/py.typed
python3 -c "from shared_package import __version__; print(f'Version: {__version__}')"
```

---

### Phase 2: Configuration System (P0) - PARTIALLY COMPLETE

**Status**: Core config ✅, ProxySettings ❌, BaseConfig needs review ❌

**Remaining Tasks**:

- [ ] Review `config/base.py` - ensure TYPE_CHECKING guards, model_post_init for directory creation
- [ ] Update `config/proxy.py` - ensure ALL credential fields use SecretStr
- [ ] Verify factory.py raises ConfigError correctly
- [ ] Ensure all site configs inherit from BaseConfig properly

**Skip**: ConfigRegistry, @overload decorators (already removed)

**Verification**:

```bash
python3 -c "from shared_package.config import ProxySettings; import inspect; fields = inspect.signature(ProxySettings).parameters; print('ProxySettings fields:', list(fields.keys()))"
python3 -c "from shared_package.config import load_config; config = load_config('sapphire', 'test_project'); print('✓ Factory works')"
```

---

### Phase 3: File I/O Utilities (P1) - NOT STARTED

**Status**: Sync JSONLWriter/Reader needed ✅, AsyncJSONL removed ❌, BoundedSet needed ✅

**Remaining Tasks**:

- [ ] Create `shared_package/io/` directory
- [ ] Implement `io/jsonl.py` with JSONLWriter (BoundedSet for \_seen_keys with LRU eviction, default 100k)
- [ ] Implement `io/jsonl.py` with JSONLReader
- [ ] Create `io/__init__.py` exports (no AsyncJSONL)
- [ ] Add BoundedSet class with LRU eviction to prevent memory exhaustion

**Skip**: AsyncJSONL classes (removed in v3.0)

**Verification**:

```bash
python3 -c "from shared_package.io import JSONLWriter, JSONLReader; print('✓ JSONL utilities available')"
python3 -c "from shared_package.io.jsonl import BoundedSet; s = BoundedSet(max_size=3); [s.add(i) for i in range(5)]; assert len(s) == 3; print('✓ BoundedSet works')"
```

---

### Phase 4: Logging System (P1) - NOT STARTED

**Status**: Loguru-based logger needed ✅, No custom decorators ✅

**Remaining Tasks**:

- [ ] Create `shared_package/logging/` directory
- [ ] Implement `logging/logger.py` with setup_logging(project_name, run_id, log_dir)
- [ ] Add InterceptHandler for stdlib logging compatibility
- [ ] Rich format with project_name, trace_id (ContextVar), run_id, elapsed time
- [ ] Use enqueue=True for async-safe file handlers
- [ ] Create `logging/__init__.py` exports

**Skip**: @with_timing decorator, error aggregation (removed in v3.0)

**Verification**:

```bash
python3 -c "from shared_package.logging import setup_logging, logger; setup_logging('test_project', 'test_run'); logger.info('Test log'); print('✓ Logger works')"
```

---

### Phase 5: Validation Models (P2) - NOT STARTED

**Status**: Provider/Location models needed ✅, TaskQueue removed ❌

**Remaining Tasks**:

- [ ] Create `shared_package/validation/` directory
- [ ] Implement `validation/models.py` with Provider Pydantic model
- [ ] Implement `validation/models.py` with Location Pydantic model
- [ ] Create `validation/__init__.py` exports

**Skip**: TaskQueue module (removed in v3.0 - use asyncio.Queue directly)

**Verification**:

```bash
python3 -c "from shared_package.validation import Provider, Location; p = Provider(npi='1234567890', first_name='John', last_name='Smith'); print('✓ Validation models work')"
```

---

### Phase 6: Environment Setup (P0) - NOT STARTED

**Status**: .env.example needed ✅, validate_env.py needed ✅

**Remaining Tasks**:

- [ ] Create comprehensive `.env.example` with all proxy provider variables
- [ ] Document each variable with comments
- [ ] Create `tools/validate_env.py` for production environment validation
- [ ] Add validation for required vs optional variables by site type

**Skip**: None

**Verification**:

```bash
test -f shared_package/.env.example
python3 tools/validate_env.py --project test_project --site-type sapphire
```

---

### Phase 7: Backward Compatibility (P1) - NOT STARTED

**Status**: Deprecation shims needed ✅

**Remaining Tasks**:

- [ ] Update `shared_package/config.py` backward compat layer
- [ ] Add deprecation warnings for old import paths
- [ ] Ensure Response dataclass migrations work
- [ ] Test that existing projects can import without breaking

**Skip**: Function exports (\_get_headers) - projects define these locally

**Verification**:

```bash
python3 -c "from shared_package.config import CONFIG; print('✓ Backward compat works (with warnings)')" 2>&1 | grep -i deprecat
```

---

### Phase 8: Testing & Documentation (P1) - NOT STARTED

**Status**: Test infrastructure needed ✅

**Remaining Tasks**:

- [ ] Create `shared_package/tests/` directory
- [ ] Implement `tests/conftest.py` with mock fixtures (mock_playwright, mock_proxy_config)
- [ ] Write unit tests for config system
- [ ] Write unit tests for JSONL I/O with BoundedSet
- [ ] Write tests for validation models
- [ ] Write integration tests for logger
- [ ] Update CLAUDE.md with v3.0 architecture

**Skip**: Concurrency stress tests for removed components (TaskQueue, AsyncJSONL)

**Verification**:

```bash
pytest shared_package/tests/ -v --tb=short
```

---

### Phase 9: Migration Tooling (P0) - NOT STARTED

**Status**: Migration scripts needed ✅

**Remaining Tasks**:

- [ ] Create `tools/validate_migration.py` - compare outputs before/after migration
- [ ] Create `tools/rollback_migration.py` - safe rollback script
- [ ] Create `tools/find_hardcoded_credentials.py` - security scanner
- [ ] Document migration procedure in tools/README.md

**Skip**: None

**Verification**:

```bash
python3 tools/validate_migration.py --project audiobee_bcbs_il --prev 20251010 --curr 20251210
python3 tools/find_hardcoded_credentials.py shared_package/
```

---

## Execution Instructions

For each phase:

1. **Navigate to phase in plan**: Read the detailed specification
2. **Check current state**: Use `ls`, `rg`, `Read` to see what exists
3. **Implement missing components**: Follow v3.0 YAGNI principles strictly
4. **Test implementation**: Run verification commands
5. **Update progress tracker**: Mark tasks complete in SHARED_PACKAGE_PROGRESS.json
6. **Commit work**: Clear commit message with 🤖 Claude Code attribution
7. **Report completion**: Show verification results
8. **Continue to next phase**: No breaks, keep going

## YAGNI Principles (Mandatory)

**Always remember**:

- ❌ Do NOT implement AsyncJSONL (removed)
- ❌ Do NOT implement TaskQueue (removed)
- ❌ Do NOT implement error aggregation (removed)
- ❌ Do NOT implement @with_timing (removed)
- ❌ Do NOT create complex exception hierarchies (4 classes only)
- ❌ Do NOT use registry patterns (simple dicts only)
- ❌ Do NOT add @overload decorators (documentation theater)

**Do implement**:

- ✅ SecretStr for ALL credentials
- ✅ TYPE_CHECKING guards to prevent circular imports
- ✅ BoundedSet with LRU for memory-bounded deduplication
- ✅ Sync JSONL I/O (works in async contexts)
- ✅ Rich logging with loguru (project_name, trace_id, elapsed)
- ✅ Comprehensive .env.example documentation
- ✅ Migration tooling for safe rollout

## Success Criteria

After completing all phases:

1. ✅ All verification commands pass
2. ✅ Progress tracker shows all phases "completed"
3. ✅ No AsyncJSONL, TaskQueue, error aggregation, or @with_timing code exists
4. ✅ pytest runs successfully with >80% coverage
5. ✅ All credentials use SecretStr
6. ✅ tools/validate_env.py validates environments correctly
7. ✅ Migration tooling ready for production use

## Ralph Wiggum Style

Execute with:

- 🚀 **Autonomous momentum** - Don't wait for approval between phases
- 🎯 **Focus on verification** - Every task must have passing tests
- 📝 **Clear progress updates** - Update tracker after each phase
- 🔄 **Continuous commits** - Commit after each phase completion
- 🧠 **YAGNI enforcement** - Skip removed components, no over-engineering
- 🐛 **Fix as you go** - If tests fail, fix immediately before proceeding

## Start Command

Execute this task using:

```
/spawn healthsparq-executor --phases 1-9 --progress-tracker docs/restructuring/SHARED_PACKAGE_PROGRESS.json --plan docs/restructuring/SHARED_PACKAGE_IMPLEMENTATION_PLAN.md
```

Or manually start with Phase 1 and work through sequentially.

---

**GO RALPH GO!** 🚀

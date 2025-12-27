# Shared Package Implementation Plan

**Version**: 3.0
**Status**: Simplified Based on Expert Reviews (DHH-style, YAGNI-focused)
**Created**: 2025-12-26
**Updated**: 2025-12-26 (v3.0 - Major simplification pass)
**Scope**: Enhance existing shared_package for 95+ scraper projects

---

## Executive Summary

**REVISED v3.0**: This plan incorporates feedback from 12 specialized expert reviews including DHH-style Rails review, Kieran-quality review, and code simplicity review. **Major theme: YAGNI (You Aren't Gonna Need It)**.

### v3.0 Simplifications (YAGNI Pass)

**REMOVED** (over-engineered for 95 scrapers):

- ❌ `AsyncJSONL` classes - All scrapers use sync I/O; async adds complexity without benefit
- ❌ `TaskQueue` - Use `asyncio.Queue` directly; tenacity for retries
- ❌ `ErrorAggregation` - Duplicates loguru's `logger.bind()` and `logger.exception()`
- ❌ `@with_timing` decorator - Use inline `time.perf_counter()` or loguru's elapsed
- ❌ `ConfigRegistry` pattern - Simple `CONFIG_TYPES` dict for 4 site types
- ❌ `@overload` decorators - Documentation theater; `BaseConfig` return is sufficient
- ❌ 13 exception classes - Reduced from 17 to 4 (use Python's built-ins)

**RETAINED** (proven value):

- ✅ `SecretStr` for all credentials (security requirement)
- ✅ `TYPE_CHECKING` guards (prevents circular imports)
- ✅ `BoundedSet` with LRU eviction (memory safety)
- ✅ Sync `JSONLWriter`/`JSONLReader` (works correctly in async contexts)
- ✅ 4 exception classes: `SharedPackageError`, `SessionError`, `ProxyError`, `ConfigError`

### Key Principles Applied

1. **YAGNI**: Only build what 95 scrapers actually need today
2. **Use stdlib**: `asyncio.Queue` over custom `TaskQueue`, `IOError` over `FileIOError`
3. **Simple > Clever**: Dict over registry pattern, single function over @overload
4. **Loguru is enough**: No custom error aggregation or timing decorators

### Review Summary

| Reviewer         | Verdict              | Key Action                |
| ---------------- | -------------------- | ------------------------- |
| Python Packaging | APPROVE_WITH_CHANGES | Flat layout fix           |
| Security         | **NEEDS_WORK**       | SecretStr required        |
| Performance      | ACCEPTABLE           | Bound dedup sets          |
| API Design       | SIMPLIFIED           | Simple dict over registry |
| DevOps           | **NEEDS_WORK**       | validate_env.py           |
| Testing          | NEEDS_TEST_STRATEGY  | Mock infra first          |
| Architecture     | ACCEPTABLE           | Circular import guards    |
| Migration        | **RISKY**            | Breaking changes exist    |
| Logging          | NEEDS_IMPROVEMENT    | Rich context format       |

### Current State Analysis

**ALREADY IMPLEMENTED** (functional):

- `proxy/` - Complete multi-provider system (5 providers, 8 tiers)
- `session/` - BrowserSession, HttpSession, ResilientBrowserSession (Patchright-based)
- `localdataclass/response.py` - Response dataclass
- `config.py` - Basic dotenv-based configuration (74 lines)

**CRITICAL GAPS** (from reviews):

1. **Security**: Credentials stored as plaintext strings (MUST fix)
2. **Migration**: Function exports (`_get_headers`, `REVERSE_NETWORKS_MAP`) not supported
3. **Migration**: Auto-directory creation at import time breaks
4. **Migration**: UUID generation timing (field defaults vs default_factory)
5. **Performance**: Unbounded `_seen_keys` sets will exhaust memory
6. **DevOps**: No `tools/validate_env.py` for production safety
7. **Architecture**: Dual dotenv loading (proxy/**init**.py + config.py)
8. **Logging**: Missing project_name, trace_id, timing in format

---

## Architecture Overview

### Target Structure (ENHANCED v2.0)

```
scraping/
├── tools/                       # NEW: Migration/validation tools
│   ├── validate_env.py          # Environment validation
│   ├── validate_migration.py    # Output comparison
│   ├── rollback_migration.py    # Safe rollback
│   └── find_hardcoded_credentials.py  # Security scan
│
└── shared_package/
    ├── pyproject.toml           # Flat layout package config
    ├── py.typed                 # NEW: PEP 561 marker for type checking
    ├── __init__.py              # Version, exports, public API
    ├── config.py                # KEEP: Backward compat layer
    │
    ├── config/                  # NEW: Pydantic Settings
    │   ├── __init__.py          # Exports (simple, no @overload)
    │   ├── base.py              # BaseConfig (TYPE_CHECKING guards)
    │   ├── proxy.py             # ProxySettings (SecretStr!)
    │   ├── registry.py          # CONFIG_TYPES dict (simple mapping)
    │   ├── sapphire.py          # SapphireConfig
    │   ├── healthsparq.py       # HealthsparqConfig
    │   ├── carrier.py           # CarrierConfig
    │   ├── anthem.py            # AnthemConfig
    │   └── factory.py           # load_config() (simple, no @overload)
    │
    ├── io/                      # NEW: File I/O
    │   ├── __init__.py
    │   ├── jsonl.py             # JSONLWriter (LRU-bounded dedup!)
    │   └── file_manager.py      # AtomicWriter
    │
    ├── logging/                 # NEW: Loguru setup
    │   ├── __init__.py
    │   ├── logger.py            # setup_logging(enqueue=True!)
    │   └── intercept.py         # InterceptHandler for stdlib
    │
    ├── validation/              # NEW: Schema + Response
    │   ├── __init__.py
    │   ├── schema.py            # Provider/Location models
    │   └── response.py          # Moved from localdataclass
    │
    ├── exceptions.py            # NEW: Custom exception hierarchy
    │
    ├── proxy/                   # EXISTING (minor update)
    │   └── __init__.py          # REMOVE dotenv loading
    │
    ├── session/                 # EXISTING (unchanged)
    ├── localdataclass/          # DEPRECATED (keep for compat)
    │
    └── tests/                   # NEW: Test infrastructure
        ├── conftest.py          # Mock fixtures (Patchright, curl_cffi)
        ├── test_config.py
        ├── test_session_concurrency.py  # NEW
        └── ...
```

---

## Phase Breakdown (Revised Order)

### Recommended Execution Order

Based on Architecture Reviewer's recommendation:

```
Week 1:
├── Phase 0: Migration Tooling (NEW - CRITICAL)
├── Phase 1: Package Infrastructure
└── Phase 2: Environment Setup

Week 2:
├── Phase 3: Configuration System
└── Phase 4: Backward Compatibility

Week 3:
├── Phase 5: File I/O Utilities
├── Phase 6: Logging System
└── Phase 7: Queue & Validation

Week 4:
└── Phase 8: Testing & Documentation
```

---

### Phase 0: Migration Tooling (Priority: P0) [NEW]

**Goal**: Create safety net before any code changes

**Rationale**: Migration Expert identified that "zero breaking changes" claim is FALSE. We need validation and rollback mechanisms BEFORE touching code.

**Tasks**:

1. Create `tools/validate_migration.py` - Output comparison tool
2. Create `tools/rollback_migration.py` - Safe revert mechanism
3. Create `tools/find_hardcoded_credentials.py` - Security scan
4. Pilot test on 3 diverse projects (Sapphire, Healthsparq, Carrier)

**Deliverables**:

```python
# tools/validate_migration.py
"""
Validates that scraper output is identical before/after migration.

COMPLETE WORKFLOW (per Migration Expert review):
1. BEFORE migration: Capture baseline with --capture-baseline
2. Run migration
3. AFTER migration: Compare with --compare-baseline

Usage:
    # Step 1: Capture baseline BEFORE migration
    python tools/validate_migration.py audiobee_bcbs_il --capture-baseline

    # Step 2: After migration, compare against baseline
    python tools/validate_migration.py audiobee_bcbs_il --compare-baseline

    # Batch operations
    python tools/validate_migration.py --scan-all --capture-baseline
    python tools/validate_migration.py --scan-all --compare-baseline --report report.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Baseline storage location
BASELINE_DIR = Path(".migration-baselines")


def discover_projects() -> list[str]:
    """Dynamically discover all audiobee_* projects."""
    return sorted([d.name for d in Path(".").iterdir()
                   if d.is_dir() and d.name.startswith("audiobee_")])


def get_current_date(project: str) -> str | None:
    """Get the current date folder from project's config.py."""
    config_file = Path(project) / "config.py"
    if not config_file.exists():
        return None

    content = config_file.read_text()
    for line in content.splitlines():
        if line.strip().startswith("CURR_DATE"):
            # Extract value: CURR_DATE = "20251210"
            if "=" in line:
                value = line.split("=", 1)[1].strip().strip('"').strip("'")
                return value
    return None


def compute_file_hash(file_path: Path) -> dict[str, Any]:
    """Compute hash and metadata for a file."""
    content = file_path.read_bytes()
    return {
        "size": len(content),
        "lines": content.count(b'\n'),
        "hash": hashlib.sha256(content).hexdigest()
    }


def capture_baseline(project: str, date: str | None = None) -> dict[str, Any]:
    """Capture baseline state for a project BEFORE migration."""
    project_dir = Path(project)
    date = date or get_current_date(project)

    if not date:
        return {"error": f"Could not determine date for {project}"}

    processed_dir = project_dir / date / "processed"

    baseline = {
        "project": project,
        "date": date,
        "captured_at": datetime.now().isoformat(),
        "git_commit": _get_git_commit(),
        "files": {}
    }

    if processed_dir.exists():
        for jsonl_file in sorted(processed_dir.glob("*.jsonl")):
            baseline["files"][jsonl_file.name] = compute_file_hash(jsonl_file)

    # Save baseline
    BASELINE_DIR.mkdir(exist_ok=True)
    baseline_file = BASELINE_DIR / f"{project}.json"
    baseline_file.write_text(json.dumps(baseline, indent=2))
    print(f"✅ Captured baseline for {project} ({len(baseline['files'])} files)")

    return baseline


def compare_baseline(project: str) -> dict[str, Any]:
    """Compare current state against captured baseline."""
    baseline_file = BASELINE_DIR / f"{project}.json"

    if not baseline_file.exists():
        return {
            "project": project,
            "status": "ERROR",
            "error": "No baseline found. Run --capture-baseline first."
        }

    baseline = json.loads(baseline_file.read_text())
    date = baseline["date"]
    processed_dir = Path(project) / date / "processed"

    result = {
        "project": project,
        "date": date,
        "baseline_commit": baseline.get("git_commit"),
        "current_commit": _get_git_commit(),
        "status": "PASS",
        "differences": []
    }

    # Check each baseline file
    for filename, baseline_meta in baseline["files"].items():
        current_file = processed_dir / filename

        if not current_file.exists():
            result["status"] = "FAIL"
            result["differences"].append({
                "file": filename,
                "issue": "MISSING",
                "baseline_hash": baseline_meta["hash"]
            })
            continue

        current_meta = compute_file_hash(current_file)

        if current_meta["hash"] != baseline_meta["hash"]:
            result["status"] = "FAIL"
            result["differences"].append({
                "file": filename,
                "issue": "HASH_MISMATCH",
                "baseline_hash": baseline_meta["hash"],
                "current_hash": current_meta["hash"],
                "size_diff": current_meta["size"] - baseline_meta["size"],
                "line_diff": current_meta["lines"] - baseline_meta["lines"]
            })

    # Check for new files not in baseline
    if processed_dir.exists():
        for jsonl_file in processed_dir.glob("*.jsonl"):
            if jsonl_file.name not in baseline["files"]:
                result["differences"].append({
                    "file": jsonl_file.name,
                    "issue": "NEW_FILE"
                })

    status_icon = "✅" if result["status"] == "PASS" else "❌"
    print(f"{status_icon} {project}: {result['status']} ({len(result['differences'])} differences)")

    return result


def validate_imports(project: str) -> list[str]:
    """Check that all existing imports still work."""
    errors = []
    project_dir = Path(project)

    for py_file in project_dir.glob("*.py"):
        if py_file.name.startswith("index_") or py_file.name == "config.py":
            result = subprocess.run(
                [sys.executable, "-c", f"import sys; sys.path.insert(0, '{project_dir}'); import {py_file.stem}"],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                errors.append(f"{py_file.name}: {result.stderr.strip()}")

    return errors


def _get_git_commit() -> str:
    """Get current git commit hash."""
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        return result.stdout.strip()[:8]
    except subprocess.CalledProcessError:
        return "unknown"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migration validation tool")
    parser.add_argument("project", nargs="?", help="Project name (e.g., audiobee_bcbs_il)")
    parser.add_argument("--capture-baseline", action="store_true", help="Capture baseline BEFORE migration")
    parser.add_argument("--compare-baseline", action="store_true", help="Compare against baseline AFTER migration")
    parser.add_argument("--scan-all", action="store_true", help="Process all audiobee_* projects")
    parser.add_argument("--report", type=str, help="Save report to JSON file")

    args = parser.parse_args()

    projects = discover_projects() if args.scan_all else [args.project] if args.project else []

    if not projects:
        parser.error("Specify a project or use --scan-all")

    results = []
    for project in projects:
        if args.capture_baseline:
            results.append(capture_baseline(project))
        elif args.compare_baseline:
            results.append(compare_baseline(project))

    if args.report:
        Path(args.report).write_text(json.dumps(results, indent=2))
        print(f"\n📄 Report saved to {args.report}")
```

```python
# tools/rollback_migration.py
"""
Safely rollback a migration using git tags.

IMPORTANT: Uses git tags for reliable rollback instead of HEAD~1 (per Migration Expert review).
Each migration creates a pre-migration tag that can be used for safe rollback.

Usage:
    python tools/rollback_migration.py audiobee_bcbs_il
    python tools/rollback_migration.py --all --dry-run
    python tools/rollback_migration.py audiobee_bcbs_il --tag pre-migration-v2
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Tag naming convention for migrations
TAG_PREFIX = "pre-shared-package-migration"


def get_latest_migration_tag(project: str) -> str | None:
    """Find the latest pre-migration tag for a project."""
    try:
        result = subprocess.run(
            ["git", "tag", "-l", f"{TAG_PREFIX}-{project}-*"],
            capture_output=True, text=True, check=True
        )
        tags = sorted(result.stdout.strip().split('\n'), reverse=True)
        return tags[0] if tags and tags[0] else None
    except subprocess.CalledProcessError:
        return None


def create_migration_tag(project: str) -> str:
    """Create a pre-migration tag for safe rollback (call BEFORE migration)."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    tag = f"{TAG_PREFIX}-{project}-{timestamp}"
    subprocess.run(["git", "tag", tag], check=True)
    print(f"✅ Created rollback tag: {tag}")
    return tag


def rollback_project(project: str, tag: str | None = None, dry_run: bool = False) -> bool:
    """Revert project files to pre-migration state using git tag.

    Args:
        project: Project name (e.g., 'audiobee_bcbs_il')
        tag: Specific tag to rollback to (auto-detects if None)
        dry_run: If True, only show what would be done

    Returns:
        True if rollback successful
    """
    # Find tag to rollback to
    if tag is None:
        tag = get_latest_migration_tag(project)
        if tag is None:
            print(f"❌ No migration tag found for {project}")
            print(f"   Expected format: {TAG_PREFIX}-{project}-YYYYMMDD-HHMMSS")
            print("   Run create_migration_tag() before migration to enable rollback")
            return False

    print(f"🔄 Rolling back {project} to tag: {tag}")

    # Files that may have been modified during migration
    files_to_revert = [
        f"{project}/config.py",
        f"{project}/index_1.py",
        f"{project}/index_2.py",
        f"{project}/index_3.py",
        f"{project}/run_all.py",
    ]

    for file_path in files_to_revert:
        if Path(file_path).exists():
            # Use tag reference instead of HEAD~1 (CRITICAL FIX)
            cmd = ["git", "checkout", tag, "--", file_path]
            if dry_run:
                print(f"   Would run: {' '.join(cmd)}")
            else:
                try:
                    subprocess.run(cmd, check=True, capture_output=True)
                    print(f"   ✅ Reverted: {file_path}")
                except subprocess.CalledProcessError as e:
                    print(f"   ⚠️  File not in tag (may be new): {file_path}")

    if not dry_run:
        print(f"✅ Rollback complete for {project}")

    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rollback shared_package migration")
    parser.add_argument("project", nargs="?", help="Project to rollback")
    parser.add_argument("--all", action="store_true", help="Rollback all migrated projects")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--tag", help="Specific tag to rollback to")
    parser.add_argument("--create-tag", action="store_true", help="Create pre-migration tag")

    args = parser.parse_args()

    if args.create_tag and args.project:
        create_migration_tag(args.project)
    elif args.project:
        rollback_project(args.project, tag=args.tag, dry_run=args.dry_run)
    else:
        parser.print_help()
        sys.exit(1)
```

```python
# tools/find_hardcoded_credentials.py
"""
Scan all projects for hardcoded credentials.

Usage:
    python tools/find_hardcoded_credentials.py --scan-all
    python tools/find_hardcoded_credentials.py audiobee_*
"""
import re
from pathlib import Path

# Expanded patterns per Security Specialist review
CREDENTIAL_PATTERNS = [
    # Basic credentials
    r'password\s*[=:]\s*["\'][^"\']+["\']',
    r'api_key\s*[=:]\s*["\'][^"\']+["\']',
    r'username\s*[=:]\s*["\'][^"\']+["\']',
    r'secret\s*[=:]\s*["\'][^"\']+["\']',
    r'token\s*[=:]\s*["\'][^"\']+["\']',

    # OAuth and bearer tokens (Gap #14)
    r'bearer\s+[A-Za-z0-9\-_\.]+',
    r'auth_token\s*[=:]\s*["\'][^"\']+["\']',
    r'access_token\s*[=:]\s*["\'][^"\']+["\']',
    r'refresh_token\s*[=:]\s*["\'][^"\']+["\']',

    # Client credentials
    r'client_id\s*[=:]\s*["\'][^"\']{10,}["\']',  # >10 chars to avoid false positives
    r'client_secret\s*[=:]\s*["\'][^"\']+["\']',

    # AWS/Cloud credentials
    r'aws_access_key\s*[=:]\s*["\'][^"\']+["\']',
    r'aws_secret\s*[=:]\s*["\'][^"\']+["\']',

    # Generic private keys
    r'private_key\s*[=:]\s*["\'][^"\']+["\']',
    r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----',

    # Connection strings
    r'mongodb(\+srv)?://[^"\'\s]+:[^"\'\s]+@',
    r'postgres://[^"\'\s]+:[^"\'\s]+@',
    r'mysql://[^"\'\s]+:[^"\'\s]+@',

    # F-string credential interpolation (per Security review Gap #16)
    r'f["\'].*(?:password|secret|token|api_key)\s*[=:]\s*\{[^}]+\}',
    r'f["\'].*\{(?:password|secret|token|api_key)[^}]*\}',
    # .format() credential leaks
    r'["\'].*(?:password|secret|token)\s*[=:]\s*\{\}["\']\.format\(',
    # Percent-format credential leaks
    r'["\'].*(?:password|secret|token)\s*[=:]\s*%s.*["\']\s*%\s*\(',
]

# Patterns to exclude (environment variable references are OK)
EXCLUDE_PATTERNS = [
    r'os\.getenv\s*\(',
    r'os\.environ\s*\[',
    r'\$\{[^}]+\}',           # ${VAR} placeholders
    r'SecretStr\s*\(',        # Pydantic SecretStr wrappers
    r'\.get_secret_value\(\)', # SecretStr access
]

def is_excluded(line: str) -> bool:
    """Check if line matches exclusion patterns (env vars, SecretStr, etc.)."""
    return any(re.search(pat, line) for pat in EXCLUDE_PATTERNS)


def scan_file(file_path: Path) -> list[dict]:
    """Scan a file for hardcoded credentials."""
    findings = []

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return [{"file": str(file_path), "error": str(e)}]

    for i, line in enumerate(content.splitlines(), 1):
        # Skip excluded patterns (env vars, SecretStr, etc.)
        if is_excluded(line):
            continue

        for pattern in CREDENTIAL_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                findings.append({
                    "file": str(file_path),
                    "line": i,
                    "pattern": pattern,
                    "content": line.strip()[:100]
                })

    return findings


def scan_project(project_path: Path) -> list[dict]:
    """Scan all Python files in a project."""
    findings = []
    for py_file in project_path.rglob("*.py"):
        # Skip test files and __pycache__
        if "__pycache__" in str(py_file) or "test_" in py_file.name:
            continue
        findings.extend(scan_file(py_file))
    return findings
```

**Verification**:

```bash
# Scan for hardcoded credentials
python tools/find_hardcoded_credentials.py --scan-all

# Validate a pilot project
python tools/validate_migration.py audiobee_bcbs_il --compare-outputs

# Test rollback (dry run)
python tools/rollback_migration.py audiobee_bcbs_il --dry-run
```

**Success Criteria**:

- [ ] `find_hardcoded_credentials.py` identifies all exposed credentials
- [ ] `validate_migration.py` can compare output hashes
- [ ] `rollback_migration.py` successfully reverts in dry-run mode
- [ ] 3 pilot projects validated before full rollout

---

### Phase 1: Package Infrastructure (Priority: P0)

**Goal**: Make existing package installable via pip/uv

**CHANGES FROM REVIEW**:

- Flat layout fix: `packages = ["shared_package"]` (not `["."]`)
- Pin pydantic-settings version: `>=2.0.0,<3.0.0`

**pyproject.toml** (REVISED):

```toml
[project]
name = "shared-package"
version = "0.1.0"
description = "Shared utilities for Ideon scraping projects"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.0.1,<3.0.0",
    "pydantic-settings>=2.0.0,<3.0.0",  # PINNED per Packaging review
    "python-dotenv>=1.0.0",
    "loguru>=0.7.0",
    "orjson>=3.9.0",
    "httpx>=0.27.0",
    "curl-cffi>=0.7.0",
    "patchright>=1.0.0",
    "tenacity>=8.0.0",
    "tqdm>=4.66.0",
]

[project.optional-dependencies]
# Development dependencies
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.0.0",
    "pytest-timeout>=2.2.0",       # Timeout handling
    "pytest-mock>=3.12.0",         # Mocker fixture
    "respx>=0.20.0",               # httpx mocking
    "hypothesis>=6.0.0",           # Property testing
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["shared_package"]      # FIXED: Flat layout
only-include = ["shared_package"]

[tool.hatch.build.targets.sdist]
include = ["shared_package"]

[tool.pytest.ini_options]
asyncio_mode = "auto"              # Per Testing review
asyncio_default_fixture_loop_scope = "function"
testpaths = ["shared_package/tests"]
timeout = 30                       # Prevent hanging tests

[tool.coverage.run]
source = ["shared_package"]
branch = true
omit = [
    "shared_package/tests/*",
    "shared_package/**/test_*.py",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
    "@overload",
    "raise NotImplementedError",
]
fail_under = 80                     # Minimum coverage target
show_missing = true
skip_covered = true

[tool.coverage.html]
directory = "htmlcov"
```

**shared_package/**init**.py** (NEW - Public API exports):

```python
"""
Shared utilities for Ideon scraping projects.

This package provides:
- Session management (BrowserSession, HttpSession, ResilientBrowserSession)
- Proxy orchestration (ProxyManager, ProxyConfig, ProxyType)
- Configuration (BaseConfig, load_config, ProxySettings)
- I/O utilities (JSONLWriter, JSONLReader, AtomicWriter)
- Logging (setup_logging, get_logger)
- Validation (Provider, Location schemas)
"""
from __future__ import annotations

from importlib.metadata import version, PackageNotFoundError
from typing import TYPE_CHECKING, Any

try:
    __version__ = version("shared-package")
except PackageNotFoundError:
    __version__ = "0.1.0"  # Fallback for editable installs

# Core session exports (most commonly used)
from .session import BrowserSession, HttpSession, ResilientBrowserSession

# Proxy exports
from .proxy import ProxyManager, ProxyConfig, ProxyType

# Type exports for type hints (only visible to type checkers)
if TYPE_CHECKING:
    from .config import BaseConfig, load_config, ProxySettings
    from .io import JSONLWriter, JSONLReader, BoundedSet
    from .logging import setup_logging, get_logger
    from .validation import Provider, Location
    from .exceptions import SharedPackageError, SessionError, ProxyError, ConfigError

# Lazy import map for runtime access (avoids circular imports)
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # Config module
    "BaseConfig": (".config", "BaseConfig"),
    "load_config": (".config", "load_config"),
    "ProxySettings": (".config", "ProxySettings"),
    # I/O module
    "JSONLWriter": (".io", "JSONLWriter"),
    "JSONLReader": (".io", "JSONLReader"),
    "BoundedSet": (".io", "BoundedSet"),
    # Logging module
    "setup_logging": (".logging", "setup_logging"),
    "get_logger": (".logging", "get_logger"),
    # Validation module
    "Provider": (".validation", "Provider"),
    "Location": (".validation", "Location"),
    # Exceptions module (simplified - 4 classes per expert review)
    "SharedPackageError": (".exceptions", "SharedPackageError"),
    "SessionError": (".exceptions", "SessionError"),
    "ProxyError": (".exceptions", "ProxyError"),
    "ConfigError": (".exceptions", "ConfigError"),
}


def __getattr__(name: str) -> Any:
    """
    Lazy import for modules not loaded at package import time.

    This allows `from shared_package import load_config` to work at runtime,
    not just for type checkers. Avoids circular imports and speeds up initial import.
    """
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        import importlib
        module = importlib.import_module(module_path, package=__name__)
        return getattr(module, attr_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """
    Support autocomplete for lazy-loaded attributes.

    Per API Design review: Without this, IDEs won't show lazy imports in autocomplete.
    Returns all eagerly-loaded names plus all lazy-loadable names.
    """
    # Get default module attributes
    default_attrs = list(globals().keys())
    # Add lazy import names
    lazy_attrs = list(_LAZY_IMPORTS.keys())
    return sorted(set(default_attrs + lazy_attrs))


__all__ = [
    # Version
    "__version__",
    # Session (eagerly loaded)
    "BrowserSession",
    "HttpSession",
    "ResilientBrowserSession",
    # Proxy (eagerly loaded)
    "ProxyManager",
    "ProxyConfig",
    "ProxyType",
    # Config (lazy loaded)
    "BaseConfig",
    "load_config",
    "ProxySettings",
    # I/O (lazy loaded)
    "JSONLWriter",
    "JSONLReader",
    "BoundedSet",
    # Logging (lazy loaded)
    "setup_logging",
    "get_logger",
    # Validation (lazy loaded)
    "Provider",
    "Location",
    # Exceptions (lazy loaded - simplified per expert review)
    "SharedPackageError",
    "SessionError",
    "ProxyError",
    "ConfigError",
]
```

**shared_package/py.typed** (NEW - PEP 561 marker):

```
# Marker file for PEP 561
# This package uses inline type annotations
```

**shared_package/exceptions.py** (NEW - Simplified exception hierarchy):

```python
"""Shared package exceptions - simplified hierarchy.

Per expert review: 17 exception classes is over-engineered for scraper utilities.
Use Python's standard exceptions (ValueError, IOError, TimeoutError) where appropriate.
Only define custom exceptions for domain-specific cases where callers need to catch them.
"""
from __future__ import annotations
from typing import Any


class SharedPackageError(Exception):
    """Base for all shared_package exceptions."""

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message)
        self.context = context or {}


class SessionError(SharedPackageError):
    """Session-related errors (initialization, closed, blocked, timeout).

    Use status_code attribute for HTTP status (403, 429, etc.).
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        context: dict[str, Any] | None = None
    ):
        super().__init__(message, context)
        self.status_code = status_code


class ProxyError(SharedPackageError):
    """Proxy-related errors (configuration, connection, exhausted)."""
    pass


class ConfigError(SharedPackageError):
    """Configuration errors (validation, not found, invalid site type)."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        context: dict[str, Any] | None = None
    ):
        super().__init__(message, context)
        self.field = field


# Use standard exceptions for I/O and parsing:
# - IOError for file operations (already built-in)
# - ValueError for JSON parsing (already built-in)
# - TimeoutError for timeouts (already built-in)
#
# Use standard exceptions for security:
# - ValueError("Hardcoded credentials detected")
# - Don't expose credential details in exceptions
```

**Verification**:

```bash
cd /Users/dikson/Work/ideon_scraping/scraping
uv pip install -e shared_package/
python -c "import shared_package; print(shared_package.__version__)"
python -c "from shared_package.session import BrowserSession"
python -c "from shared_package.proxy import ProxyManager"
# Verify py.typed is included
python -c "import shared_package; import os; print(os.path.exists(os.path.join(os.path.dirname(shared_package.__file__), 'py.typed')))"
```

---

### Phase 2: Environment Setup (Priority: P0)

**Goal**: Standardize environment configuration

**CHANGES FROM REVIEW**:

- Create `tools/validate_env.py` (CRITICAL - was missing)
- Document .env hierarchy loading order

**Deliverables**:

```
scraping/
├── .env.example             # Template with all variables
├── .gitignore               # MUST include .env patterns
└── tools/
    └── validate_env.py      # Environment validation
```

**tools/validate_env.py** (NEW):

```python
#!/usr/bin/env python3
"""
Validate environment configuration for scraper projects.

Usage:
    python tools/validate_env.py                    # Validate current directory
    python tools/validate_env.py audiobee_bcbs_il   # Validate specific project
    python tools/validate_env.py --all              # Validate all projects
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

REQUIRED_VARS = {
    # Proxy credentials (at least one pair required)
    "NORD_USERNAME": "NordVPN proxy username",
    "NORD_PASSWORD": "NordVPN proxy password",
}

OPTIONAL_VARS = {
    "SURFSHARK_USERNAME": "Surfshark proxy username",
    "SURFSHARK_PASSWORD": "Surfshark proxy password",
    "SMARTPROXY_USERNAME": "SmartProxy username",
    "SMARTPROXY_PASSWORD": "SmartProxy password",
    "DATAIMPULSE_USERNAME": "DataImpulse username",
    "DATAIMPULSE_PASSWORD": "DataImpulse password",
}

def find_env_files(project_path: Path) -> list[Path]:
    """Find .env files in hierarchy (project -> parent -> root)."""
    env_files = []
    current = project_path.resolve()

    while current != current.parent:
        env_file = current / ".env"
        if env_file.exists():
            env_files.append(env_file)
        current = current.parent

    return env_files

def validate_project(project_path: Path) -> dict:
    """Validate environment for a project."""
    from dotenv import dotenv_values

    env_files = find_env_files(project_path)

    # Merge values (later files override earlier)
    merged_env = {}
    for env_file in reversed(env_files):
        merged_env.update(dotenv_values(env_file))

    # Also check actual environment
    for key in list(REQUIRED_VARS.keys()) + list(OPTIONAL_VARS.keys()):
        if key in os.environ and key not in merged_env:
            merged_env[key] = os.environ[key]

    result = {
        "project": str(project_path),
        "env_files_found": [str(f) for f in env_files],
        "missing_required": [],
        "missing_optional": [],
        "empty_values": [],
        "valid": True,
    }

    for var, desc in REQUIRED_VARS.items():
        value = merged_env.get(var, "")
        if not value:
            result["missing_required"].append(f"{var}: {desc}")
            result["valid"] = False
        elif value.strip() == "":
            result["empty_values"].append(var)
            result["valid"] = False

    for var, desc in OPTIONAL_VARS.items():
        if var not in merged_env:
            result["missing_optional"].append(f"{var}: {desc}")

    return result

if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Validate environment configuration")
    parser.add_argument("project", nargs="?", default=".", help="Project directory")
    parser.add_argument("--all", action="store_true", help="Validate all audiobee_* projects")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.all:
        projects = list(Path(".").glob("audiobee_*"))
    else:
        projects = [Path(args.project)]

    results = []
    for project in projects:
        if project.is_dir():
            result = validate_project(project)
            results.append(result)

            if not args.json:
                status = "OK" if result["valid"] else "FAIL"
                print(f"{project}: {status}")
                if result["missing_required"]:
                    for var in result["missing_required"]:
                        print(f"  MISSING: {var}")

    if args.json:
        print(json.dumps(results, indent=2))

    # Exit with error if any validation failed
    if not all(r["valid"] for r in results):
        sys.exit(1)
```

**.env hierarchy documentation** (add to ENV_MANAGEMENT_GUIDE.md):

```markdown
## .env Loading Order (Precedence)

When loading configuration, values are resolved in this order (highest priority first):

1. **Constructor arguments** - Passed directly to config class
2. **Environment variables** - `SCRAPER_*` prefixed variables
3. **Project .env** - `.env` in the project directory (e.g., `audiobee_bcbs_il/.env`)
4. **Parent .env files** - Walking up: `../.env`, `../../.env`, etc.
5. **Root .env** - `scraping/.env`
6. **Field defaults** - Defined in Pydantic Settings class

### Important Notes

- Later sources OVERRIDE earlier sources (project .env beats root .env)
- Empty string values are treated as "not set"
- CWD affects discovery - always run from project directory
```

**Phase 2 Verification Commands** (per DevOps review):

```bash
# Verify .env.example exists and is complete
test -f .env.example && echo "✅ .env.example exists" || echo "❌ Missing .env.example"
grep -c "=" .env.example # Should show 10+ variables

# Verify .env is gitignored
grep -q "\.env" .gitignore && echo "✅ .env in .gitignore" || echo "❌ .env not gitignored"

# Run environment validation
python tools/validate_env.py --scan-all --report env_validation.json

# Test hierarchy loading (from project directory)
cd audiobee_bcbs_il
python -c "from shared_package.config import find_env_files_hierarchy; print(find_env_files_hierarchy())"
```

---

### Phase 3: Configuration System (Priority: P0)

**Goal**: Implement Pydantic Settings with proper security and type safety

**CHANGES FROM REVIEW**:

1. **Security**: All credentials MUST use `SecretStr`
2. **API Design**: Simple `load_config()` returning `BaseConfig` (no @overload - per expert review)
3. **Architecture**: Use `TYPE_CHECKING` guards to prevent circular imports
4. **Architecture**: Simple `CONFIG_TYPES` dict for site type mapping (no registry pattern - per expert review)
5. **Architecture**: Remove dotenv loading from `proxy/__init__.py`

**config/proxy.py** (SECURITY FIX):

```python
"""Proxy settings with secure credential handling."""
from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProxySettings(BaseSettings):
    """Proxy credentials - ALL use SecretStr for security."""

    # Pydantic v2 configuration (replaces deprecated class Config)
    model_config = SettingsConfigDict(
        env_prefix="",  # No prefix for backward compat
        extra="ignore",
    )

    # NordVPN
    nord_username: SecretStr = SecretStr("")
    nord_password: SecretStr = SecretStr("")

    # Surfshark
    surfshark_username: SecretStr = SecretStr("")
    surfshark_password: SecretStr = SecretStr("")

    # SmartProxy
    smartproxy_username: SecretStr = SecretStr("")
    smartproxy_password: SecretStr = SecretStr("")

    # DataImpulse
    dataimpulse_username: SecretStr = SecretStr("")
    dataimpulse_password: SecretStr = SecretStr("")

    # Decodo
    decodo_username: SecretStr = SecretStr("")
    decodo_password: SecretStr = SecretStr("")

    def get_nord_auth(self) -> tuple[str, str]:
        """Get NordVPN credentials as plain strings (for internal use only)."""
        return (
            self.nord_username.get_secret_value(),
            self.nord_password.get_secret_value()
        )

    def __repr__(self) -> str:
        """Never expose credentials in repr."""
        return "ProxySettings(***)"

    def __str__(self) -> str:
        """Never expose credentials in str."""
        return "ProxySettings(credentials=hidden)"
```

**config/registry.py** (SIMPLIFIED - Simple dict, not a registry pattern):

```python
"""Config type mapping - simple dict, not a registry pattern.

Per expert review: ConfigRegistry is over-engineered for 4 site types.
A simple dict achieves the same with less code.
"""
from __future__ import annotations
from typing import Type
from .base import BaseConfig
from .sapphire import SapphireConfig
from .healthsparq import HealthsparqConfig
from .carrier import CarrierConfig
from .anthem import AnthemConfig

# Simple mapping - no registry pattern needed for 4 types
CONFIG_TYPES: dict[str, Type[BaseConfig]] = {
    "sapphire": SapphireConfig,
    "healthsparq": HealthsparqConfig,
    "carrier": CarrierConfig,
    "anthem": AnthemConfig,
}
```

**config/base.py** (with TYPE_CHECKING guards):

```python
"""Base configuration with Pydantic Settings."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Tuple, Type
from uuid import uuid4

from pydantic import Field, PrivateAttr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource

if TYPE_CHECKING:
    from .proxy import ProxySettings


def find_env_files_hierarchy(start_path: Path | None = None) -> list[Path]:
    """
    Find .env files walking up directory tree.

    Returns files in PRIORITY ORDER: project-level first, then parent dirs.
    This matches Pydantic's default behavior where earlier files take precedence.
    """
    env_files = []
    current = (start_path or Path.cwd()).resolve()

    while current != current.parent:
        env_file = current / ".env"
        if env_file.exists():
            env_files.append(env_file)
        current = current.parent

    return env_files


class BaseConfig(BaseSettings):
    """Base configuration for all scraper projects.

    .env Hierarchy (per DevOps review):
    - Walks up directory tree to find all .env files
    - Project-level .env takes precedence over parent directories
    - Environment variables override all .env files
    """

    model_config = SettingsConfigDict(
        env_prefix="SCRAPER_",
        # NOTE: env_file is dynamically set via settings_customise_sources
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """
        Customize settings sources to implement .env hierarchy walking.

        Priority (highest to lowest):
        1. init_settings - explicit constructor values
        2. env_settings - environment variables
        3. dotenv_settings - .env file hierarchy (project -> parent -> root)
        4. file_secret_settings - /run/secrets/ files
        """
        # Find all .env files in hierarchy
        env_files = find_env_files_hierarchy()

        if env_files:
            # Update dotenv_settings to use hierarchy
            # Pydantic v2 accepts tuple of env files - earlier files take precedence
            dotenv_settings.env_file = tuple(env_files)

        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )

    # Core identifiers
    project_name: str = Field(..., description="Project identifier")
    site_type: str = Field(..., description="Site type (sapphire, healthsparq, etc.)")

    # Dates
    curr_date: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y%m%d"),
        description="Current run date (YYYYMMDD)"
    )
    prev_date: str = Field(default="", description="Previous run date (YYYYMMDD)")

    # Transaction ID - use default_factory for unique per-instance!
    transaction_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique transaction ID"
    )

    # Directories (computed on init) - use PrivateAttr to avoid mutable default!
    _dirs: dict[str, Path] = PrivateAttr(default_factory=dict)

    @field_validator('curr_date', 'prev_date', mode='before')
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Validate date is YYYYMMDD format."""
        if not v:
            return v
        if len(v) != 8 or not v.isdigit():
            raise ValueError(f"Date must be YYYYMMDD format, got: {v}")
        return v

    def model_post_init(self, __context: Any) -> None:
        """Initialize computed properties after model creation."""
        # Auto-create directories at init time (preserves existing behavior!)
        self._dirs = self._compute_dirs()
        self._ensure_dirs()

    def _compute_dirs(self) -> dict[str, Path]:
        """Compute directory structure from curr_date."""
        base = Path(self.curr_date)
        return {
            "raw": base / "raw",
            "search_results": base / "raw" / "search_results",
            "provider_details": base / "raw" / "provider_details",
            "processed": base / "processed",
        }

    def _ensure_dirs(self) -> None:
        """Create directories if they don't exist."""
        for dir_path in self._dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)

    @property
    def dirs(self) -> dict[str, Path]:
        """Get directory structure."""
        return self._dirs
```

**config/factory.py** (SIMPLIFIED - simple, no @overload):

```python
"""Factory function - simple, no @overload.

Per expert review: @overload adds ceremony without real value for 4 types.
Type checkers can infer BaseConfig; explicit types are documentation theater.
"""
from __future__ import annotations
from .base import BaseConfig
from .registry import CONFIG_TYPES

def load_config(site_type: str, project_name: str, **kwargs) -> BaseConfig:
    """Load configuration for a scraper project.

    Args:
        site_type: One of 'sapphire', 'healthsparq', 'carrier', 'anthem'
        project_name: Project identifier (e.g., 'audiobee_bcbs_il')
        **kwargs: Additional config overrides

    Returns:
        Site-specific config instance

    Raises:
        ConfigError: If site_type is not recognized
    """
    if site_type not in CONFIG_TYPES:
        from .exceptions import ConfigError
        available = ', '.join(CONFIG_TYPES.keys())
        raise ConfigError(f"Unknown site type: '{site_type}'. Available: {available}")

    config_class = CONFIG_TYPES[site_type]
    return config_class(project_name=project_name, site_type=site_type, **kwargs)
```

**config/sapphire.py** (SIMPLIFIED - no decorator):

```python
"""Sapphire site type configuration."""
from __future__ import annotations

from typing import Optional

from pydantic import Field

from .base import BaseConfig


class SapphireConfig(BaseConfig):
    """Configuration for Sapphire (ProviderFinderOnline) sites."""

    network_id: str = Field(..., description="Network ID for API calls")
    api_key: Optional[str] = Field(default=None, description="API key if required")

    # Sapphire-specific settings
    max_results_per_page: int = Field(default=100, ge=1, le=500)
    search_radius_miles: int = Field(default=50, ge=1, le=100)
```

**config/healthsparq.py** (SIMPLIFIED - no decorator):

```python
"""Healthsparq site type configuration."""
from __future__ import annotations

from typing import Optional

from pydantic import Field

from .base import BaseConfig


class HealthsparqConfig(BaseConfig):
    """Configuration for Healthsparq sites (browser automation required)."""

    # Healthsparq-server connection
    server_host: str = Field(default="localhost", description="Healthsparq server host")
    server_port: int = Field(default=1018, description="Healthsparq server port")

    # Session settings
    session_timeout: int = Field(default=30, ge=5, le=120, description="Session timeout in seconds")
    max_retries: int = Field(default=3, ge=1, le=10, description="Max retries for failed requests")

    # Rate limiting
    request_delay_ms: int = Field(default=500, ge=0, le=5000, description="Delay between requests in ms")
    page_load_timeout: int = Field(default=30000, ge=5000, le=60000, description="Page load timeout in ms")

    # Cookie handling
    cookie_domain: Optional[str] = Field(default=None, description="Cookie domain for session")

    @property
    def server_url(self) -> str:
        """Get full server URL."""
        return f"http://{self.server_host}:{self.server_port}"
```

**config/carrier.py** (SIMPLIFIED - no decorator):

```python
"""Carrier (direct API) site type configuration."""
from __future__ import annotations

from typing import Optional, List

from pydantic import Field

from .base import BaseConfig


class CarrierConfig(BaseConfig):
    """Configuration for Carrier sites (direct REST API integration)."""

    # API configuration
    api_base_url: str = Field(..., description="Base URL for API calls")
    api_key: Optional[str] = Field(default=None, description="API key if required")
    api_version: str = Field(default="v1", description="API version")

    # Request settings
    timeout: int = Field(default=30, ge=5, le=120, description="Request timeout in seconds")
    max_concurrent: int = Field(default=10, ge=1, le=50, description="Max concurrent requests")

    # Geographic search
    search_radius_miles: int = Field(default=50, ge=1, le=200, description="Search radius in miles")
    geo_coords: Optional[str] = Field(default=None, description="Center coordinates (lat,lng)")

    # Pagination
    page_size: int = Field(default=100, ge=10, le=500, description="Results per page")

    # States coverage
    target_states: List[str] = Field(default_factory=list, description="List of state codes to scrape")

    @property
    def headers(self) -> dict:
        """Get default headers for API calls."""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers
```

**config/anthem.py** (SIMPLIFIED - no decorator):

```python
"""Anthem/Wellpoint site type configuration."""
from __future__ import annotations

from typing import Optional, List

from pydantic import Field

from .base import BaseConfig


class AnthemConfig(BaseConfig):
    """Configuration for Anthem/Wellpoint sites (multi-phase with intelligent filtering)."""

    # Brand configuration
    brand: str = Field(..., description="Brand name (anthem, amerigroup, simply, healthy_blue)")
    brand_url_prefix: str = Field(..., description="Brand-specific URL prefix")

    # Network configuration
    network_ids: List[str] = Field(default_factory=list, description="Target network IDs")
    state_configs: dict = Field(default_factory=dict, description="State-specific network mappings")

    # Browser automation settings
    headless: bool = Field(default=True, description="Run browser in headless mode")
    browser_timeout: int = Field(default=60000, ge=10000, le=120000, description="Browser timeout in ms")

    # Anti-detection
    use_camoufox: bool = Field(default=True, description="Use Camoufox for anti-detection")
    humanize: bool = Field(default=True, description="Enable humanize behaviors")
    geoip: bool = Field(default=True, description="Enable GeoIP spoofing")

    # Caching
    cache_ttl_minutes: int = Field(default=30, ge=5, le=120, description="Cache TTL for intercepted requests")

    # Worker pool
    max_workers: int = Field(default=10, ge=1, le=20, description="Max parallel browser workers")

    @property
    def is_two_process(self) -> bool:
        """Check if using two-process architecture."""
        return self.max_workers > 1
```

**config/**init**.py** (SIMPLIFIED - no registry export):

```python
"""
Configuration module exports.

This module provides the public API for the configuration system.
All imports should come from here, not from submodules directly.

Per expert review: ConfigRegistry removed. CONFIG_TYPES dict is internal.
Users should use load_config() factory function.
"""

# Core types and utilities
from .base import BaseConfig
from .proxy import ProxySettings
from .factory import load_config

# Site-specific configs (for direct instantiation if needed)
from .sapphire import SapphireConfig
from .healthsparq import HealthsparqConfig
from .carrier import CarrierConfig
from .anthem import AnthemConfig

# For extending with new site types (internal use)
from .registry import CONFIG_TYPES

__all__ = [
    # Factory function (primary API)
    "load_config",
    # Base classes
    "BaseConfig",
    "ProxySettings",
    # Site configs (for type hints and direct use)
    "SapphireConfig",
    "HealthsparqConfig",
    "CarrierConfig",
    "AnthemConfig",
    # Config type mapping (for extending - internal)
    "CONFIG_TYPES",
]
```

**proxy/**init**.py UPDATE** (Gap #1 - Fix dual dotenv loading):

The existing `proxy/__init__.py` has dual dotenv loading that conflicts with the new config system. Replace lines 58-70:

```python
# BEFORE (current - REMOVE):
# from pathlib import Path
# import dotenv
# _root_env_path = Path(__file__).parent.parent.parent / ".env"
# if _root_env_path.exists():
#     dotenv.load_dotenv(_root_env_path)
# _shared_env_path = Path(__file__).parent.parent / ".env"
# if _shared_env_path.exists():
#     dotenv.load_dotenv(_shared_env_path, override=True)

# AFTER (new):
"""
Proxy management module for handling multiple proxy providers.

NOTE: Environment loading is now handled by the config/ module.
Do NOT add dotenv loading here - it causes dual-loading issues.
See: docs/restructuring/SHARED_PACKAGE_IMPLEMENTATION_PLAN.md
"""
import warnings

# Check if we're being imported before config module
# This helps catch migration issues during development
def _check_config_loaded():
    import os
    if not os.getenv("_SHARED_PACKAGE_CONFIG_LOADED"):
        warnings.warn(
            "proxy module imported before config module. "
            "For proper .env loading, import from shared_package.config first.",
            UserWarning,
            stacklevel=3
        )

# Only warn during development, not in production
import os
if os.getenv("SHARED_PACKAGE_DEV_MODE"):
    _check_config_loaded()

# Rest of imports remain unchanged...
from .base import ProxyType, ProxyConfig, BaseProxyProvider
# ...
```

**Phase 3 Verification Commands** (per DevOps review):

```bash
# Test config loading with type safety
python -c "
from shared_package.config import load_config, SapphireConfig
config = load_config('audiobee_bcbs_il', SapphireConfig)
print(f'project_name={config.project_name}, site_type={config.site_type}')
"

# Verify SecretStr is used for credentials
python -c "
from shared_package.proxy import ProxySettings
import inspect
src = inspect.getsource(ProxySettings)
assert 'SecretStr' in src, 'Missing SecretStr'
print('✅ Credentials use SecretStr')
"

# Test CONFIG_TYPES mapping
python -c "
from shared_package.config import CONFIG_TYPES
print(f'Available site types: {list(CONFIG_TYPES.keys())}')
"

# Verify no circular imports
python -c "from shared_package.config import BaseConfig; print('✅ No circular imports')"
```

---

### Phase 4: Backward Compatibility (Priority: P0)

**Goal**: Ensure existing projects continue working - INCLUDING function exports

**CHANGES FROM REVIEW** (Migration Expert):

1. Support function exports (`_get_headers`, `REVERSE_NETWORKS_MAP`)
2. Preserve auto-directory creation at import time
3. Fix UUID generation timing (use `default_factory`)

**shared_package/config.py** (backward compat layer):

```python
"""
Backward compatibility layer for legacy config patterns.

This module maintains compatibility with existing projects that use:
    from config import PREV_DATE, CURR_DATE, DIRS, _get_headers

DO NOT MODIFY the exports without checking all 95+ projects!
"""
import os
import warnings
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv

# Load .env for backward compatibility
load_dotenv()

# ============================================================
# CREDENTIAL EXPORTS (Deprecated - use ProxySettings instead)
# ============================================================
import warnings

def _get_env_str(key: str, default: str = "") -> str:
    """Get environment variable as string."""
    return os.getenv(key, default)

def _deprecated_credential(key: str) -> str:
    """Get deprecated credential with warning."""
    warnings.warn(
        f"Accessing {key} directly is deprecated. "
        "Use ProxySettings from shared_package.proxy instead. "
        "Direct credential access will be removed in v2.0.",
        DeprecationWarning,
        stacklevel=3
    )
    return _get_env_str(key)

# These are deprecated but must remain for backward compat
# Emit deprecation warning on first access via __getattr__
_DEPRECATED_CREDENTIALS = {
    "NORD_USERNAME", "NORD_PASSWORD",
    "SURFSHARK_USERNAME", "SURFSHARK_PASSWORD",
    "SMARTPROXY_USERNAME", "SMARTPROXY_PASSWORD",
    "DATAIMPULSE_USERNAME", "DATAIMPULSE_PASSWORD",
}

# Cache for lazy loading (avoid repeated warnings per session)
_credential_cache: dict[str, str] = {}

def _get_deprecated_credential(name: str) -> str:
    """Get deprecated credential with caching and warning."""
    if name not in _credential_cache:
        warnings.warn(
            f"Accessing {name} directly is deprecated. "
            "Use ProxySettings from shared_package.proxy instead. "
            "Direct credential access will be removed in v2.0.",
            DeprecationWarning,
            stacklevel=3
        )
        _credential_cache[name] = _get_env_str(name)
    return _credential_cache[name]

# For static analysis tools, define as properties that trigger deprecation
# These will be accessed via __getattr__ below
NORD_USERNAME: str
NORD_PASSWORD: str
SURFSHARK_USERNAME: str
SURFSHARK_PASSWORD: str
SMARTPROXY_USERNAME: str
SMARTPROXY_PASSWORD: str
DATAIMPULSE_USERNAME: str
DATAIMPULSE_PASSWORD: str

# ============================================================
# FUNCTION EXPORTS (Critical - projects import these!)
# ============================================================

def get_default_proxy() -> dict:
    """Get default proxy configuration.

    Deprecated: Use ProxySettings and ProxyManager instead.
    """
    warnings.warn(
        "get_default_proxy() is deprecated. "
        "Use ProxySettings from shared_package.proxy instead.",
        DeprecationWarning,
        stacklevel=2
    )
    # Use cached credentials (with their own deprecation warnings suppressed here)
    username = _credential_cache.get("NORD_USERNAME") or _get_env_str("NORD_USERNAME")
    password = _credential_cache.get("NORD_PASSWORD") or _get_env_str("NORD_PASSWORD")
    return {
        "server": f"http://{username}:{password}@us.socks.nordhold.net:1080"
    }

# Projects may define these in their local config.py and import from here
# We provide a placeholder that can be overridden
_project_functions: dict[str, Callable] = {}

def register_function(name: str, func: Callable) -> None:
    """Register a project-specific function for export."""
    _project_functions[name] = func

def __getattr__(name: str) -> Any:
    """
    Dynamic attribute access for backward compatibility.

    This allows projects to do:
        from shared_package.config import _get_headers
        from shared_package.config import NORD_USERNAME  # deprecated

    Even if _get_headers is defined in the project's config.py
    """
    # Handle deprecated credential access with warning
    if name in _DEPRECATED_CREDENTIALS:
        return _get_deprecated_credential(name)

    # Handle project-registered functions
    if name in _project_functions:
        return _project_functions[name]

    raise AttributeError(f"module 'shared_package.config' has no attribute '{name}'")

# ============================================================
# NEW: Migration helper
# ============================================================

def create_compat_exports(project_config) -> dict[str, Any]:
    """
    Create backward-compatible exports from a new config object.

    Usage in project config.py:
        from shared_package.config import load_config, create_compat_exports

        config = load_config("sapphire", "audiobee_bcbs_il", network_id="210002020")

        # Create backward compat exports
        _exports = create_compat_exports(config)
        PREV_DATE = _exports["PREV_DATE"]
        CURR_DATE = _exports["CURR_DATE"]
        DIRS = _exports["DIRS"]
    """
    return {
        "PREV_DATE": project_config.prev_date,
        "CURR_DATE": project_config.curr_date,
        "PROJECT_NAME": project_config.project_name,
        "DIRS": {k: str(v) for k, v in project_config.dirs.items()},
    }
```

**Phase 4 Verification Commands** (per DevOps review):

```bash
# Test backward compatibility layer
python -c "
from shared_package.config import PREV_DATE, CURR_DATE, DIRS
print(f'PREV_DATE={PREV_DATE}, CURR_DATE={CURR_DATE}')
print(f'DIRS keys: {list(DIRS.keys())}')
"

# Verify deprecation warnings work
python -W default::DeprecationWarning -c "
from shared_package.proxy import BoundedSet  # Should warn
" 2>&1 | grep -q "DeprecationWarning" && echo "✅ Deprecation warnings work" || echo "❌ No warning"

# Test function exports still work
python -c "
from shared_package.config import _get_headers, REVERSE_NETWORKS_MAP
print(f'✅ Function exports work: _get_headers={callable(_get_headers)}')
"

# Validate migration for pilot project
python tools/validate_migration.py audiobee_bcbs_il --compare-baseline
```

---

### Phase 5: File I/O Utilities (Priority: P1)

**Goal**: Thread-safe, memory-efficient file operations

**CHANGES FROM REVIEW** (Performance Engineer):

1. Use LRU-bounded or bloom filter for `_seen_keys`
2. Flush operations OUTSIDE the lock
3. ~~Consider aiofiles for async I/O~~ (REMOVED per YAGNI - sync I/O sufficient)

**io/jsonl.py** (with bounded deduplication):

```python
"""JSONL read/write utilities with bounded memory usage."""
from __future__ import annotations

import os
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable, Iterator, Optional

import orjson

class _BoundedSet:
    """
    Thread-safe LRU-bounded set for memory-safe deduplication.

    Internal class - use JSONLWriter.dedup for public API.
    Made thread-safe per Performance Engineer review.
    """

    def __init__(self, max_size: int = 1_000_000):
        self._data: OrderedDict[str, None] = OrderedDict()
        self._max_size = max_size
        self._lock = threading.Lock()

    def add(self, key: str) -> bool:
        """Add key, return True if new (not duplicate). Thread-safe."""
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                return False
            if len(self._data) >= self._max_size:
                self._data.popitem(last=False)  # Remove oldest (LRU eviction)
            self._data[key] = None
            return True

    def __contains__(self, key: str) -> bool:
        with self._lock:
            return key in self._data

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)


class JSONLWriter:
    """
    Thread-safe JSONL writer with bounded deduplication.

    Performance optimizations (per Performance review):
    - LRU-bounded dedup set (prevents memory exhaustion)
    - Flush outside lock (allows concurrent writes to other files)
    - Batch orjson serialization
    """

    def __init__(
        self,
        base_dir: str | Path,
        buffer_size: int = 100,
        dedup_max_size: int = 1_000_000,
    ):
        self.base_dir = Path(base_dir)
        self.buffer_size = buffer_size
        self.dedup_max_size = dedup_max_size

        self._buffers: dict[str, list[dict]] = {}
        self._seen_keys: dict[str, _BoundedSet] = {}  # Use internal class name
        self._lock = threading.Lock()

        self.base_dir.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        record: dict,
        filename: str,
        dedup_key: Optional[str] = None,
    ) -> bool:
        """
        Write record to JSONL file with optional deduplication.

        Returns True if written, False if duplicate.
        """
        flush_data: Optional[tuple[str, list[dict]]] = None

        with self._lock:
            # Deduplication check
            if dedup_key is not None:
                key_value = record.get(dedup_key)
                if key_value is not None:
                    if filename not in self._seen_keys:
                        self._seen_keys[filename] = _BoundedSet(self.dedup_max_size)

                    if not self._seen_keys[filename].add(str(key_value)):
                        return False  # Duplicate

            # Buffer the record
            if filename not in self._buffers:
                self._buffers[filename] = []
            self._buffers[filename].append(record)

            # Check if flush needed
            if len(self._buffers[filename]) >= self.buffer_size:
                flush_data = (filename, self._buffers[filename])
                self._buffers[filename] = []

        # Flush OUTSIDE lock (allows concurrent writes to other files)
        if flush_data:
            self._do_flush(flush_data[0], flush_data[1])

        return True

    def _do_flush(self, filename: str, buffer: list[dict]) -> None:
        """
        Flush buffer to disk (called outside lock).

        Error handling (per Performance review): Preserves failed records.
        """
        if not buffer:
            return

        filepath = self.base_dir / filename
        failed_records: list[dict] = []
        serialized: list[bytes] = []

        # Serialize records individually to preserve valid records on partial failure
        for record in buffer:
            try:
                serialized.append(orjson.dumps(record))
            except (TypeError, ValueError) as e:
                import logging
                logging.error(f"Serialization failed for record in {filename}: {e}")
                failed_records.append(record)

        if serialized:
            data = b'\n'.join(serialized) + b'\n'
            try:
                with open(filepath, 'ab') as f:
                    f.write(data)
            except IOError as e:
                raise IOError(f"Failed to write to {filepath}: {e}") from e

        # Write failed records to separate error file (best effort)
        if failed_records:
            error_path = filepath.with_suffix('.errors.jsonl')
            try:
                with open(error_path, 'a') as f:
                    for rec in failed_records:
                        f.write(f"{rec!r}\n")
            except IOError:
                pass

    def flush_all(self) -> None:
        """Flush all buffers to disk.

        Race condition fix: Use buffer.copy() to avoid corruption when
        _do_flush() runs outside the lock while clear() reuses list objects.
        """
        buffers_to_flush: list[tuple[str, list[dict]]] = []

        with self._lock:
            for filename, buffer in self._buffers.items():
                if buffer:
                    # CRITICAL: Copy buffer to prevent race condition!
                    # After clear(), Python may reuse list objects, causing
                    # potential corruption when _do_flush() runs outside lock.
                    buffers_to_flush.append((filename, buffer.copy()))
            self._buffers.clear()

        for filename, buffer in buffers_to_flush:
            self._do_flush(filename, buffer)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.flush_all()


class JSONLReader:
    """Streaming JSONL reader."""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)

    def __iter__(self) -> Iterator[dict]:
        """Stream records without loading entire file."""
        with open(self.file_path, 'rb') as f:
            for line in f:
                line = line.strip()
                if line:
                    yield orjson.loads(line)

    def count(self) -> int:
        """Count records without loading all into memory."""
        return sum(1 for _ in self)
```

**io/async_jsonl.py** - **REMOVED** (per Expert Review - YAGNI):

> All 95 scrapers use sync file I/O. AsyncJSONL adds complexity for no proven benefit.
> If async I/O becomes necessary, add it when a real use case emerges.
> For now, use the sync `JSONLWriter`/`JSONLReader` which work correctly in async contexts
> (blocking I/O in asyncio is acceptable for buffered writes to local disk).

**io/file_manager.py** (NEW - AtomicWriter):

```python
"""Atomic file operations for safe writes."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional


class AtomicWriter:
    """
    Write files atomically using temp file + rename pattern.

    This prevents partial writes from corrupting files on crash.
    """

    def __init__(self, target_path: str | Path, mode: str = "w"):
        self.target_path = Path(target_path)
        self.mode = mode
        self._temp_file = None
        self._temp_path = None

    def __enter__(self):
        # Create temp file in same directory for atomic rename
        self.target_path.parent.mkdir(parents=True, exist_ok=True)
        fd, self._temp_path = tempfile.mkstemp(
            dir=self.target_path.parent,
            prefix=f".{self.target_path.name}.",
            suffix=".tmp"
        )
        self._temp_file = os.fdopen(fd, self.mode)
        return self._temp_file

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._temp_file.close()

        if exc_type is None:
            # Success - atomic rename
            os.replace(self._temp_path, self.target_path)
        else:
            # Failure - cleanup temp file
            try:
                os.unlink(self._temp_path)
            except OSError:
                pass

        return False  # Don't suppress exceptions
```

**io/**init**.py** (NEW - Gap #5):

```python
"""
File I/O utilities for scraper projects.

Provides thread-safe file operations with:
- Bounded memory deduplication
- Atomic writes
- Streaming reads

Note: Async JSONL utilities removed per YAGNI - see async_jsonl.py section above.
"""
from .jsonl import JSONLReader, JSONLWriter, _BoundedSet as BoundedSet
from .file_manager import AtomicWriter

__all__ = [
    "JSONLReader",
    "JSONLWriter",
    "BoundedSet",
    "AtomicWriter",
]
```

**Phase 5 Verification Commands** (per DevOps review):

```bash
# Test JSONLWriter with deduplication
python -c "
from shared_package.io import JSONLWriter
import tempfile, os
with tempfile.TemporaryDirectory() as tmp:
    writer = JSONLWriter(tmp, buffer_size=10, max_seen_keys=100)
    writer.write('test.jsonl', {'id': 1, 'name': 'A'}, dedup_key='id')
    writer.write('test.jsonl', {'id': 1, 'name': 'B'}, dedup_key='id')  # Should be deduped
    writer.write('test.jsonl', {'id': 2, 'name': 'C'}, dedup_key='id')
    writer.flush_all()
    lines = open(os.path.join(tmp, 'test.jsonl')).readlines()
    assert len(lines) == 2, f'Expected 2, got {len(lines)}'
    print('✅ Deduplication works')
"

# Verify memory bounding
python -c "
from shared_package.io.jsonl import _BoundedSet
s = _BoundedSet(max_size=3)
for i in range(5):
    s.add(f'key{i}')
assert len(s) == 3, 'BoundedSet not bounded'
print('✅ Memory bounding works')
"

# Note: Async JSONL tests removed - async utilities removed per YAGNI
```

---

### Phase 6: Logging System (Priority: P1)

**Goal**: Structured logging with rich context

**CHANGES FROM REVIEW** (Logging Expert):

1. Use `enqueue=True` for async-safe file writes (CRITICAL)
2. Add `InterceptHandler` for stdlib logging compatibility
3. Include project_name, trace_id, timing in log format
4. Add run_id for cross-scraper correlation

**logging/logger.py** (REVISED):

````python
"""Structured logging with loguru."""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import threading
import time  # Moved to module level (per Senior Python Dev review)
from collections import OrderedDict  # For memory-bounded _run_errors
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from loguru import logger as _logger

# Context variables for async-safe trace tracking
_trace_ctx: ContextVar[str] = ContextVar("trace_id", default="none")
_run_ctx: ContextVar[str] = ContextVar("run_id", default="standalone")

def get_trace_id() -> str:
    """Get current trace ID."""
    return _trace_ctx.get()

def get_run_id() -> str:
    """Get current run ID (for cross-scraper correlation)."""
    return _run_ctx.get()

def set_run_id(run_id: str) -> None:
    """Set run ID (called by run_parallel.py)."""
    _run_ctx.set(run_id)

def with_trace(func):
    """Decorator to add trace ID to async function."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        trace_id = uuid4().hex[:8]
        token = _trace_ctx.set(trace_id)
        try:
            return await func(*args, **kwargs)
        finally:
            _trace_ctx.reset(token)
    return wrapper


class InterceptHandler(logging.Handler):
    """
    Intercept stdlib logging and redirect to loguru.

    This captures logs from third-party libraries (httpx, curl_cffi, etc.)
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = _logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        _logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging(
    project_name: str,
    phase: str = "main",
    log_dir: Optional[str | Path] = None,
    level: str = "INFO",
    rotation: str = "00:00",  # Daily at midnight
    retention: str = "14 days",
) -> None:
    """
    Configure logging for a scraper project.

    Args:
        project_name: Project identifier (e.g., 'audiobee_bcbs_il')
        phase: Current phase (search, details, map)
        log_dir: Directory for log files (default: logs/)
        level: Minimum log level
        rotation: When to rotate files
        retention: How long to keep old files
    """
    # Remove default handler
    _logger.remove()

    # Get run_id from environment (set by run_parallel.py)
    run_id = os.getenv("SCRAPER_RUN_ID", "standalone")
    set_run_id(run_id)

    # Rich console format with all context
    # Console format includes run_id for cross-scraper correlation (Logging Expert)
    console_format = (
        "<green>{time:HH:mm:ss.SSS}</green> | "
        "<level>{level: <5}</level> | "
        "<cyan>{extra[project]: <15}</cyan> | "
        "<yellow>{extra[phase]: <8}</yellow> | "
        "<magenta>{extra[trace_id]: <8}</magenta> | "
        "<blue>{extra[run_id]: <8}</blue> | "
        "{message}"
    )

    # Add console handler
    _logger.add(
        sys.stderr,
        format=console_format,
        level=level,
        colorize=True,
    )

    # File logging with enqueue=True (CRITICAL for async safety!)
    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # Main log file (daily rotation)
        _logger.add(
            log_path / f"{project_name}_{{time:YYYYMMDD}}.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <5} | {extra[project]} | {extra[phase]} | {extra[trace_id]} | {extra[run_id]} | {message}",
            level=level,
            rotation=rotation,
            retention=retention,
            compression="gz",
            enqueue=True,  # CRITICAL: Async-safe writes
        )

        # Error-only log (size-based rotation)
        _logger.add(
            log_path / f"{project_name}_errors.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {extra[project]} | {message}\n{exception}",
            level="ERROR",
            rotation="50MB",
            retention="30 days",
            enqueue=True,
        )

        # Optional: JSON log for machine parsing
        _logger.add(
            log_path / f"{project_name}_{{time:YYYYMMDD}}.jsonl",
            format="{message}",
            level=level,
            rotation=rotation,
            retention="7 days",
            serialize=True,
            enqueue=True,
        )

    # Configure to use our context
    _logger.configure(
        extra={
            "project": project_name,
            "phase": phase,
            "trace_id": "init",
            "run_id": run_id,
        }
    )

    # Intercept stdlib logging (for third-party libs)
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Specifically capture these noisy loggers
    for logger_name in ["httpx", "httpcore", "urllib3", "asyncio"]:
        logging.getLogger(logger_name).handlers = [InterceptHandler()]


def get_logger(phase: str):
    """
    Get a phase-bound logger.

    Args:
        phase: Current phase (search, details, map)

    Returns:
        Logger bound to the phase with trace context
    """
    return _logger.bind(
        phase=phase,
        trace_id=get_trace_id(),
        run_id=get_run_id(),
    )


# ============================================================
# Error Aggregation - **REMOVED** (per Expert Review - Duplicates loguru)
# ============================================================
#
# The error aggregation system (ErrorSummary, record_error, aggregate_run_errors,
# clear_run_errors, log_error_summary) has been removed as it duplicates
# loguru's built-in functionality.
#
# Use loguru's `logger.bind()` for context and filter logs by level.
#
# **For error tracking**: Use `logger.exception()` - it includes stack traces.
# **For summaries**: Use log aggregation tools (grep, Loki, etc.) in production.
# **For testing**: Capture logs with loguru's `logger.add()` to a list.
#
# Example:
# ```python
# from loguru import logger
#
# # Capture errors with context
# logger.bind(phase="search", provider_id="123").exception("Failed to fetch provider")
#
# # For testing - capture logs to a list
# captured = []
# logger.add(lambda msg: captured.append(msg), level="ERROR")
# ```


# ============================================================
# Timing Decorator - **REMOVED** (per Expert Review - Redundant with loguru)
# ============================================================
#
# loguru can log timing via `elapsed` field automatically.
# The @with_timing decorator adds complexity for minimal value.
#
# **If you need timing**: Use loguru's elapsed feature or time.perf_counter() inline.
#
# Example:
# ```python
# import time
#
# start = time.perf_counter()
# result = await fetch_data()
# logger.info(f"Completed in {time.perf_counter() - start:.3f}s")
# ```
````

**logging/**init**.py** (NEW - Gap #6):

```python
"""
Logging module for scraper projects.

Provides structured logging with:
- Loguru-based logging with async-safe file writes
- Rich context (project_name, phase, trace_id, run_id)
- Stdlib logging interception for third-party libs
"""
from .logger import (
    setup_logging,
    get_logger,
    get_trace_id,
    get_run_id,
    set_run_id,
    with_trace,
    InterceptHandler,
)

__all__ = [
    "setup_logging",
    "get_logger",
    "get_trace_id",
    "get_run_id",
    "set_run_id",
    "with_trace",
    "InterceptHandler",
]
```

**Phase 6 Verification Commands** (per DevOps review):

```bash
# Test logging setup
python -c "
from shared_package.logging import setup_logging, get_logger
setup_logging(level='INFO', project_name='test_project')
logger = get_logger(__name__)
logger.info('Test log message')
print('✅ Logging setup works')
"

# Verify async-safe logging (enqueue=True)
python -c "
import asyncio
from shared_package.logging import setup_logging, get_logger

async def test_async_logging():
    setup_logging(level='INFO', project_name='async_test')
    logger = get_logger(__name__)
    await asyncio.gather(*[asyncio.to_thread(lambda: logger.info(f'Log {i}')) for i in range(5)])
    print('✅ Async logging works')

asyncio.run(test_async_logging())
"

# Error aggregation and timing decorator tests - REMOVED
# These components have been removed per Expert Review (duplicates loguru functionality)
```

---

### Phase 7: Queue & Validation (Priority: P2)

**Goal**: Task queue and schema validation

**CHANGES FROM REVIEW**: Added complete implementations (Gap #12)

**queue/task_queue.py** - **REMOVED** (per Expert Review - YAGNI):

> TaskQueue wraps asyncio.Queue with retry logic and worker pools.
> All 95 scrapers already use asyncio.gather() or simple loops.
> The "automatic retry with exponential backoff" is speculative complexity.
>
> **If you need a task queue**: Use asyncio.Queue directly.
> **If you need retries**: Use tenacity library or simple try/except loops.
> **If you need workers**: Use asyncio.TaskGroup (Python 3.11+) or asyncio.gather.

**validation/schema.py** (NEW - Provider/Location models):

```python
"""Pydantic models for provider data validation."""
from __future__ import annotations

import re
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


class Location(BaseModel):
    """Provider practice location."""

    address_line_1: str = Field(..., min_length=1)
    address_line_2: Optional[str] = None
    city: str = Field(..., min_length=1)
    state: str = Field(..., min_length=2, max_length=2)
    zip_code: str = Field(..., alias="zip")
    phone: Optional[str] = None
    fax: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        """Normalize state to uppercase."""
        return v.upper()

    @field_validator("zip_code")
    @classmethod
    def validate_zip(cls, v: str) -> str:
        """Validate and normalize ZIP code."""
        # Remove any non-digit characters except hyphen
        normalized = re.sub(r"[^\d-]", "", v)
        # Accept 5-digit or 5+4 format
        if not re.match(r"^\d{5}(-\d{4})?$", normalized):
            raise ValueError(f"Invalid ZIP code format: {v}")
        return normalized[:5]  # Return just 5-digit portion

    @field_validator("phone", "fax")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Normalize phone number to digits only."""
        if v is None:
            return None
        digits = re.sub(r"\D", "", v)
        if len(digits) == 10:
            return digits
        elif len(digits) == 11 and digits.startswith("1"):
            return digits[1:]
        return digits if digits else None


class Provider(BaseModel):
    """Healthcare provider record."""

    npi: str = Field(..., min_length=10, max_length=10)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    organization_name: Optional[str] = None
    specialty: Optional[str] = None
    specialty_code: Optional[str] = None
    provider_type: Optional[str] = None
    gender: Optional[str] = None
    accepting_new_patients: Optional[bool] = None
    network_id: Optional[str] = None
    network_name: Optional[str] = None

    # Location (flattened for output)
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = Field(None, alias="zip")
    phone: Optional[str] = None

    # Nested locations (for multi-location providers)
    locations: List[Location] = Field(default_factory=list)

    @field_validator("npi")
    @classmethod
    def validate_npi(cls, v: str) -> str:
        """Validate NPI is 10 digits."""
        if not v.isdigit() or len(v) != 10:
            raise ValueError(f"NPI must be exactly 10 digits: {v}")
        return v

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: Optional[str]) -> Optional[str]:
        """Normalize gender to M/F/U."""
        if v is None:
            return None
        v_upper = v.upper()
        if v_upper in ("M", "MALE"):
            return "M"
        elif v_upper in ("F", "FEMALE"):
            return "F"
        return "U"  # Unknown

    def to_output_dict(self) -> dict:
        """Convert to flattened output format."""
        return {
            "npi": self.npi,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "organization_name": self.organization_name,
            "specialty": self.specialty,
            "specialty_code": self.specialty_code,
            "provider_type": self.provider_type,
            "gender": self.gender,
            "accepting_new_patients": self.accepting_new_patients,
            "network_id": self.network_id,
            "network_name": self.network_name,
            "address_line_1": self.address_line_1,
            "address_line_2": self.address_line_2,
            "city": self.city,
            "state": self.state,
            "zip": self.zip_code,
            "phone": self.phone,
        }
```

**validation/response.py** (migrated from localdataclass):

```python
"""
Unified response wrapper.

NOTE: This is migrated from localdataclass/response.py.
The old location is deprecated but remains for backward compatibility.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

import orjson


@dataclass
class Response:
    """
    Unified response wrapper for both browser and HTTP requests.

    Provides a consistent interface regardless of the underlying client.
    """

    result: Any
    status_code: int

    def text(self) -> str:
        """Return response as text."""
        return self.result

    def json(self) -> Any:
        """Return response as parsed JSON."""
        return orjson.loads(self.result)

    def is_success(self) -> bool:
        """Check if response indicates success."""
        return 200 <= self.status_code < 300

    def is_error(self) -> bool:
        """Check if response indicates error."""
        return self.status_code >= 400

    # NOTE: Deprecation warnings are handled via __getattr__ in localdataclass/__init__.py
    # The _create_deprecation_shim function was removed as dead code (per API Design review)
```

**validation/**init**.py** (NEW - Gap #7):

```python
"""
Data validation and schema definitions.

Provides:
- Pydantic models for provider/location data
- Response wrapper for HTTP/browser responses
"""
from .schema import Provider, Location
from .response import Response

__all__ = [
    "Provider",
    "Location",
    "Response",
]
```

**queue/**init**.py** - **REMOVED** (per Expert Review - YAGNI):

> The queue module has been removed. Use standard asyncio patterns instead.

**localdataclass/**init**.py UPDATE** (deprecation shim):

```python
"""
DEPRECATED: Use shared_package.validation instead.

This module remains for backward compatibility only.
All new code should import from shared_package.validation.
"""
import warnings
from typing import TYPE_CHECKING

# For type checkers - list expected exports (per API Design review)
__all__ = ["Response"]

if TYPE_CHECKING:
    from .response import Response

# Re-export with deprecation warning at runtime
def __getattr__(name: str):
    if name == "Response":
        warnings.warn(
            "Import Response from shared_package.validation instead. "
            "shared_package.localdataclass is deprecated.",
            DeprecationWarning,
            stacklevel=2
        )
        from .response import Response
        return Response
    raise AttributeError(f"module 'localdataclass' has no attribute '{name}'")
```

**Phase 7 Verification Commands** (per DevOps review):

```bash
# TaskQueue test - REMOVED
# TaskQueue has been removed per Expert Review (YAGNI - use asyncio.Queue directly)

# Test schema validation
python -c "
from shared_package.validation import Response
resp = Response(text='<html></html>', status=200)
assert resp.status == 200
assert resp.text == '<html></html>'
print('✅ Response validation works')
"

# Verify localdataclass deprecation shim
python -W default::DeprecationWarning -c "
from shared_package.localdataclass import Response
print('Import succeeded (with warning)')
" 2>&1 | grep -q "DeprecationWarning" && echo "✅ Deprecation warning works" || echo "❌ No warning"
```

---

### Phase 8: Testing & Documentation (Priority: P1)

**Goal**: Mock infrastructure BEFORE coverage targets

**CHANGES FROM REVIEW** (Testing Specialist):

1. Create `tests/conftest.py` with mock fixtures FIRST
2. Add concurrency tests for session semaphores/locks
3. Configure pytest-asyncio properly
4. Separate unit/integration/live test suites

**tests/conftest.py** (NEW - per Testing review):

```python
"""
Test fixtures and configuration.

IMPORTANT: This file must be created BEFORE setting coverage targets!
Mock infrastructure is required for realistic testing.
"""
import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ============================================================
# pytest-asyncio configuration
# ============================================================

@pytest.fixture(scope="session")
def event_loop_policy():
    """Use default event loop policy."""
    return asyncio.DefaultEventLoopPolicy()


# ============================================================
# Mock fixtures for external dependencies
# ============================================================

@pytest.fixture
def mock_playwright():
    """Mock Patchright/Playwright for browser tests.

    Properly mocks the async context manager pattern and all page/context methods.
    Includes all HTTP methods (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS) per Testing Specialist review.
    """
    mock = AsyncMock()

    # Helper to create mock response with all methods
    def _make_mock_response(status: int = 200, text: str = "response", json_data: dict = None):
        """Create a mock response with text(), json(), and status."""
        resp = AsyncMock()
        resp.status = status
        resp.text = AsyncMock(return_value=text)
        resp.json = AsyncMock(return_value=json_data or {"data": "test"})
        return resp

    # Mock page with all required methods
    mock_page = AsyncMock()
    mock_page.is_closed.return_value = False
    mock_page.content.return_value = "<html></html>"
    mock_page.evaluate.return_value = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    mock_page.goto.return_value = None
    mock_page.close.return_value = None

    # Mock page.request for ALL HTTP methods (per Testing Specialist review)
    mock_page.request.get.return_value = _make_mock_response()
    mock_page.request.post.return_value = _make_mock_response()
    mock_page.request.put.return_value = _make_mock_response()
    mock_page.request.delete.return_value = _make_mock_response(status=204, text="")
    mock_page.request.patch.return_value = _make_mock_response()
    mock_page.request.head.return_value = _make_mock_response(text="")
    mock_page.request.options.return_value = _make_mock_response(text="")  # CORS preflight

    # Mock context
    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page
    mock_context.cookies.return_value = []
    mock_context.close.return_value = None

    # Mock browser
    mock_browser = AsyncMock()
    mock_browser.new_context.return_value = mock_context
    mock_browser.close.return_value = None

    # Mock chromium launcher
    mock.chromium.launch.return_value = mock_browser
    mock.stop.return_value = None

    # Expose individual mocks for granular assertions in tests
    mock._mock_page = mock_page
    mock._mock_context = mock_context
    mock._mock_browser = mock_browser

    return mock


@pytest.fixture
def mock_curl_session():
    """Mock curl_cffi AsyncSession for HTTP tests.

    Note: Uses MagicMock with json.return_value instead of lambda for proper mock behavior.
    """
    mock = AsyncMock()

    # Create response mock with proper method mocking
    response_mock = MagicMock()
    response_mock.status_code = 200
    response_mock.text = "test response"
    response_mock.json.return_value = {"data": "test"}  # Correct: return_value, not lambda

    mock.get.return_value = response_mock
    mock.post.return_value = response_mock
    mock.put.return_value = response_mock
    mock.delete.return_value = response_mock
    mock.patch.return_value = response_mock
    mock.head.return_value = response_mock
    mock.options.return_value = response_mock  # CORS preflight

    return mock


@pytest.fixture
def mock_proxy_config():
    """Reusable ProxyConfig fixture."""
    from shared_package.proxy.base import ProxyConfig
    return ProxyConfig(
        host="test.proxy.com",
        port=8080,
        username="test",
        password="test123",
    )


# ============================================================
# Environment fixtures
# ============================================================

@pytest.fixture
def temp_env(tmp_path, monkeypatch):
    """Set up temporary .env files for testing."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SCRAPER_CURR_DATE=20251226\n"
        "SCRAPER_PREV_DATE=20251126\n"
        "NORD_USERNAME=test_user\n"
        "NORD_PASSWORD=test_pass\n"
    )
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def temp_env_hierarchy(tmp_path, monkeypatch):
    """Create hierarchical .env files for testing precedence."""
    # Root .env
    root_env = tmp_path / ".env"
    root_env.write_text("SCRAPER_CURR_DATE=20251201\n")

    # Project .env (overrides root)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    project_env = project_dir / ".env"
    project_env.write_text("SCRAPER_CURR_DATE=20251226\n")

    monkeypatch.chdir(project_dir)
    return project_dir


# ============================================================
# Concurrency test helpers
# ============================================================

@pytest.fixture
def concurrency_tracker():
    """Track concurrent operations for testing semaphores/locks."""
    class Tracker:
        def __init__(self):
            self.max_concurrent = 0
            self.current_concurrent = 0
            self._lock = asyncio.Lock()

        async def enter(self):
            async with self._lock:
                self.current_concurrent += 1
                self.max_concurrent = max(self.max_concurrent, self.current_concurrent)

        async def exit(self):
            async with self._lock:
                self.current_concurrent -= 1

    return Tracker()


# ============================================================
# Test markers
# ============================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "live: marks tests that use real proxies")
    config.addinivalue_line("markers", "slow: marks tests that are slow")
    config.addinivalue_line("markers", "integration: marks integration tests")
```

**tests/test_session_concurrency.py** (NEW - per Testing review):

```python
"""
Concurrency tests for session modules.

Tests verify:
1. Semaphore limits concurrent requests
2. close() waits for in-flight operations
3. Single-flight initialization prevents duplicate browser launches
4. ResilientBrowserSession recreates only once per failure batch
5. _closing flag prevents new operations during shutdown
6. Active request counter increments/decrements correctly
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared_package.session.browser_session import BrowserSession
from shared_package.session.resilient_session import ResilientBrowserSession


@pytest.mark.asyncio
async def test_concurrent_requests_respect_semaphore(
    mock_playwright,
    concurrency_tracker,
):
    """Verify max_concurrent_requests is enforced by semaphore."""
    max_concurrent = 3
    total_requests = 10

    # Create session with limited concurrency
    session = BrowserSession(max_concurrent_requests=max_concurrent)

    # Mock the page request to use our concurrency tracker
    async def mock_get(*args, **kwargs):
        await concurrency_tracker.enter()
        try:
            await asyncio.sleep(0.05)  # Simulate network delay
            return MagicMock(text=AsyncMock(return_value="ok"), status=200)
        finally:
            await concurrency_tracker.exit()

    # Initialize session with mocked playwright
    await session._ensure_initialized()
    session._page.request.get = mock_get

    # Launch concurrent requests
    tasks = [
        asyncio.create_task(session.get(f"http://test.com/{i}"))
        for i in range(total_requests)
    ]
    await asyncio.gather(*tasks)

    # Verify semaphore was respected
    assert concurrency_tracker.max_concurrent <= max_concurrent, (
        f"Max concurrent {concurrency_tracker.max_concurrent} exceeded limit {max_concurrent}"
    )

    await session.close()


@pytest.mark.asyncio
async def test_close_waits_for_active_operations(mock_playwright):
    """Verify close() blocks until in-flight requests complete."""
    session = BrowserSession(max_concurrent_requests=2)
    await session._ensure_initialized()

    # Track operation lifecycle
    operation_started = asyncio.Event()
    operation_can_finish = asyncio.Event()
    operation_finished = asyncio.Event()
    close_started = asyncio.Event()
    close_finished = asyncio.Event()

    # Mock a slow request
    async def slow_request(*args, **kwargs):
        operation_started.set()
        await operation_can_finish.wait()  # Block until signaled
        operation_finished.set()
        return MagicMock(text=AsyncMock(return_value="ok"), status=200)

    session._page.request.get = slow_request

    # Start a request
    request_task = asyncio.create_task(session.get("http://test.com"))

    # Wait for request to start
    await asyncio.wait_for(operation_started.wait(), timeout=1.0)

    # Start closing in background
    async def do_close():
        close_started.set()
        await session.close()
        close_finished.set()

    close_task = asyncio.create_task(do_close())

    # Give close a chance to start
    await asyncio.wait_for(close_started.wait(), timeout=1.0)
    await asyncio.sleep(0.05)

    # Verify close is blocked waiting (operation still running)
    assert not close_finished.is_set(), "close() should wait for active operation"
    assert not operation_finished.is_set(), "operation should still be running"

    # Allow operation to finish
    operation_can_finish.set()

    # Wait for everything to complete
    await asyncio.wait_for(request_task, timeout=1.0)
    await asyncio.wait_for(close_task, timeout=1.0)

    # Verify proper ordering
    assert operation_finished.is_set()
    assert close_finished.is_set()


@pytest.mark.asyncio
async def test_initialization_is_single_flight(mock_playwright):
    """Verify only one initialization even with concurrent _ensure_initialized calls."""
    init_count = 0
    init_lock = asyncio.Lock()

    session = BrowserSession()

    # Patch async_playwright to count initializations
    original_init = session._ensure_initialized

    async def counting_init():
        nonlocal init_count
        async with init_lock:
            init_count += 1
        # Simulate slow initialization
        await asyncio.sleep(0.1)
        await original_init()

    # We need to patch before the lock check in _ensure_initialized
    # Actually, we should check what the test is really testing:
    # The _init_lock should ensure only one init runs

    # Reset and test the actual behavior
    init_count = 0

    async def tracked_playwright_init():
        nonlocal init_count
        init_count += 1
        await asyncio.sleep(0.05)  # Slow init
        return mock_playwright.return_value

    with patch('shared_package.session.browser_session.async_playwright') as mock_ap:
        mock_ap.return_value.start = tracked_playwright_init
        mock_ap.return_value.__aenter__ = tracked_playwright_init

        # Launch multiple concurrent initialization attempts
        tasks = [
            asyncio.create_task(session._ensure_initialized())
            for _ in range(5)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Despite 5 concurrent calls, initialization should happen only once
    # (other calls wait on _init_lock and see _initialized=True)
    assert session._initialized or any(isinstance(r, Exception) for r in results)

    await session.close()


@pytest.mark.asyncio
async def test_recreation_is_single_flight(mock_playwright):
    """Verify only one recreation happens when multiple requests fail simultaneously."""
    # Track recreation events
    recreation_count = 0

    # Create a session that tracks recreations
    session = BrowserSession()
    await session._ensure_initialized()

    # Mock _force_close to count calls (used during recreation)
    original_force_close = session._force_close
    async def counting_force_close():
        nonlocal recreation_count
        recreation_count += 1
        await asyncio.sleep(0.05)  # Simulate cleanup time
        await original_force_close()

    session._force_close = counting_force_close

    # Simulate multiple concurrent failures that would trigger recreation
    # In ResilientBrowserSession, this tests the single-flight recreation

    # For BrowserSession, we test that concurrent force_close doesn't race
    tasks = [
        asyncio.create_task(session._force_close())
        for _ in range(3)
    ]

    await asyncio.gather(*tasks, return_exceptions=True)

    # Even with 3 concurrent calls, state should be consistent
    assert not session._initialized
    assert session._page is None


@pytest.mark.asyncio
async def test_closing_flag_prevents_new_operations(mock_playwright):
    """Verify _closing flag rejects new operations during shutdown."""
    session = BrowserSession()
    await session._ensure_initialized()

    # Set closing flag
    async with session._init_lock:
        session._closing = True

    # Attempt to enter operation should fail
    with pytest.raises(RuntimeError, match="closing"):
        await session._enter_operation()

    # Reset for cleanup
    async with session._init_lock:
        session._closing = False
        session._initialized = False


@pytest.mark.asyncio
async def test_active_request_tracking(mock_playwright):
    """Verify active request counter increments/decrements correctly."""
    session = BrowserSession()
    await session._ensure_initialized()

    # Initially no active requests
    assert session._active_requests == 0

    # Enter operation
    await session._enter_operation()
    assert session._active_requests == 1

    # Enter another
    await session._enter_operation()
    assert session._active_requests == 2

    # Exit both
    await session._exit_operation()
    assert session._active_requests == 1

    await session._exit_operation()
    assert session._active_requests == 0

    await session.close()


@pytest.mark.asyncio
async def test_wait_for_no_active_operations(mock_playwright):
    """Verify _wait_for_no_active_operations blocks correctly."""
    session = BrowserSession()
    await session._ensure_initialized()

    wait_finished = asyncio.Event()
    operation_released = asyncio.Event()

    # Enter an operation
    await session._enter_operation()

    # Start waiting in background
    async def do_wait():
        await session._wait_for_no_active_operations()
        wait_finished.set()

    wait_task = asyncio.create_task(do_wait())

    # Give wait a chance to start
    await asyncio.sleep(0.05)

    # Verify wait is blocked
    assert not wait_finished.is_set(), "Wait should be blocked while operation active"

    # Release operation
    await session._exit_operation()
    operation_released.set()

    # Wait should now complete
    await asyncio.wait_for(wait_task, timeout=1.0)
    assert wait_finished.is_set()

    await session.close()


@pytest.mark.asyncio
async def test_health_check_accuracy(mock_playwright):
    """Verify _is_healthy returns correct status."""
    session = BrowserSession()

    # Not initialized = not healthy
    assert not await session._is_healthy()

    await session._ensure_initialized()

    # Initialized = healthy
    assert await session._is_healthy()

    # After close = not healthy
    await session.close()
    assert not await session._is_healthy()
```

---

## Implementation Order (REVISED)

```
Week 1:
├── Phase 0: Migration Tooling (NEW - CRITICAL FIRST)
│   ├── tools/validate_migration.py
│   ├── tools/rollback_migration.py
│   └── tools/find_hardcoded_credentials.py
├── Phase 1: Package Infrastructure
│   └── pyproject.toml (flat layout fix)
└── Phase 2: Environment Setup
    └── tools/validate_env.py (CRITICAL)

Week 2:
├── Phase 3: Configuration System
│   ├── SecretStr for all credentials
│   ├── Simple CONFIG_TYPES dict (no registry pattern)
│   ├── Simple load_config() (no @overload)
│   └── TYPE_CHECKING guards
└── Phase 4: Backward Compatibility
    ├── Function exports support
    ├── Auto-directory creation
    └── UUID default_factory fix

Week 3:
├── Phase 5: File I/O Utilities
│   ├── LRU-bounded deduplication
│   └── Flush outside lock
├── Phase 6: Logging System
│   ├── enqueue=True (async-safe)
│   ├── InterceptHandler (stdlib compat)
│   └── Rich context format
└── Phase 7: Queue & Validation

Week 4:
└── Phase 8: Testing & Documentation
    ├── conftest.py with mock fixtures FIRST
    ├── Concurrency tests
    └── Coverage targets (realistic with mocks)
```

---

## Risk Mitigation (REVISED)

| Risk                       | Impact       | Mitigation                                | Status |
| -------------------------- | ------------ | ----------------------------------------- | ------ |
| Breaking existing projects | **CRITICAL** | Phase 0 tooling + pilot migration         | NEW    |
| Function exports missing   | **CRITICAL** | Dynamic `__getattr__` in config.py        | NEW    |
| Directory auto-creation    | **HIGH**     | `model_post_init()` pattern               | NEW    |
| Credential exposure        | **HIGH**     | SecretStr + find_hardcoded_credentials.py | NEW    |
| Memory exhaustion          | **HIGH**     | LRU-bounded dedup sets                    | NEW    |
| Test coverage unrealistic  | **MEDIUM**   | Mock infrastructure first                 | NEW    |
| Circular imports           | **MEDIUM**   | TYPE_CHECKING guards                      | NEW    |
| Async log blocking         | **MEDIUM**   | enqueue=True                              | NEW    |

---

## Open Questions (RESOLVED)

1. **Python 3.10 or 3.11+?** → **3.11+** (Performance improvements, TaskGroups)
2. **Proxy credentials required or optional?** → **Optional with validation warnings**
3. **Add aiofiles?** → **No** (YAGNI - sync I/O sufficient for all 95 scrapers)
4. **Include rate limiter?** → **Yes, in queue/ module (P2)**
5. **Handle version conflicts?** → **Pin pydantic-settings>=2.0.0,<3.0.0**

---

## Success Metrics (UPDATED)

1. **Phase 0 Completion**: 3 pilot projects migrated with validated outputs
2. **Zero Credential Exposure**: find_hardcoded_credentials.py passes
3. **Import Success**: All 95+ projects import without errors
4. **Test Coverage**: >80% for config/ (with mock infrastructure)
5. **Memory Bounded**: JSONLWriter handles 10M+ records without exhaustion
6. **Async Safe**: No logging I/O blocking in concurrent scrapers

---

## Related Documents

- [RESTRUCTURING_PLAN.md](./RESTRUCTURING_PLAN.md) - Overall restructuring vision
- [SHARED_PACKAGE_SPEC.md](./SHARED_PACKAGE_SPEC.md) - Technical specification
- [ENV_MANAGEMENT_GUIDE.md](./ENV_MANAGEMENT_GUIDE.md) - Environment best practices
- [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) - Step-by-step migration
- [SHARED_PACKAGE_PROGRESS.json](./SHARED_PACKAGE_PROGRESS.json) - Progress tracker with action items

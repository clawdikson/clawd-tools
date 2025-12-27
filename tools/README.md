# Migration & Validation Tools

Tools for shared_package v3.0 migration, validation, and security scanning.

## Overview

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `validate_env.py` | Validate .env configuration | Before running scrapers, after env changes |
| `validate_migration.py` | Compare migration outputs | After migrating project to v3.0 |
| `rollback_migration.py` | Safely rollback submodule | If migration issues detected |
| `find_hardcoded_credentials.py` | Security scan for credentials | Before commits, periodically |

---

## validate_env.py

Validate environment variable configuration for scrapers.

### Usage

```bash
# Validate single project
python tools/validate_env.py --project audiobee_bcbs_il --site-type sapphire

# Validate all .env files in subdirectories
python tools/validate_env.py --check-all

# Validate specific .env file
python tools/validate_env.py --env-file audiobee_bcbs_il/.env --site-type sapphire
```

### What It Checks

- **Required Variables**: SCRAPER_PROJECT_NAME, SCRAPER_SITE_TYPE for each site type
- **Proxy Configuration**: Validates PROXY_TYPES and required credentials per provider
- **Date Formats**: SCRAPER_CURR_DATE and SCRAPER_PREV_DATE must be YYYYMMDD
- **Security**: Confirms credentials are set (without exposing values)

### Example Output

```
Validating audiobee_bcbs_il/.env...
  ✓ NORD_USERNAME is set (value hidden for security)
  ✓ NORD_PASSWORD is set (value hidden for security)
  ✓ PROXY_TYPES is set (value hidden for security)
✓ Environment configuration is valid!
```

---

## validate_migration.py

Compare scraper outputs before and after v3.0 migration to ensure data consistency.

### Usage

```bash
# Validate single project migration
python tools/validate_migration.py audiobee_bcbs_il --prev 20251110 --curr 20251210

# Validate all projects
python tools/validate_migration.py --all --prev 20251110 --curr 20251210
```

### What It Checks

- **Record Counts**: Current vs previous run (±5% threshold)
- **Schema Validation**: NPI format, required fields, state/ZIP validation
- **Deduplication**: No duplicate NPIs in output
- **Data Quality**: Provider names, location data completeness

### Example Output

```
Validating audiobee_bcbs_il...
  Loading previous run: audiobee_bcbs_il/20251110/processed/providers.jsonl
  Loading current run: audiobee_bcbs_il/20251210/processed/providers.jsonl
  Previous count: 12453
  Current count:  12501
  Validating 12501 records...
  ✓ Valid

✓ Migration validation passed!
```

### When to Use

- After migrating a project to v3.0 config/logging/io systems
- Before committing migration changes
- When debugging scraper output discrepancies

---

## rollback_migration.py

Safely rollback shared_package submodule to previous commit if issues detected.

### Usage

```bash
# List recent commits
python tools/rollback_migration.py --list-commits

# Dry run (preview changes)
python tools/rollback_migration.py --dry-run

# Rollback to specific commit
python tools/rollback_migration.py --commit abc1234 --dry-run
python tools/rollback_migration.py --commit abc1234 --execute

# Rollback to previous commit
python tools/rollback_migration.py --execute
```

### What It Does

1. Checks git status (must be clean)
2. Identifies target commit (previous or specified)
3. Checks out target commit in shared_package submodule
4. Updates parent repo submodule reference
5. Prompts for confirmation (unless --dry-run)

### Example Output

```
Using previous commit: d0c81bcb - Phase 8: Testing & Documentation complete

⚠️  WARNING: This will rollback shared_package to d0c81bcb
Continue? (yes/no): yes

Rolling back shared_package...
  Current commit: 49b3b521
  Target commit:  d0c81bcb
  Executing rollback...

✓ Rollback successful! Commit changes with: git commit -m 'Rollback shared_package to d0c81bcb'
```

### When to Use

- Migration validation failures
- Breaking changes discovered after migration
- Need to revert to stable version
- Testing migration procedures

---

## find_hardcoded_credentials.py

Scan codebase for accidentally hardcoded credentials (security scanner).

### Usage

```bash
# Scan specific directory
python tools/find_hardcoded_credentials.py shared_package/

# Scan with verbose output
python tools/find_hardcoded_credentials.py shared_package/ --verbose

# Scan all files (not just code)
python tools/find_hardcoded_credentials.py . --all
```

### What It Detects

- **API Keys**: api_key, apikey, api_secret patterns
- **Passwords**: password, passwd, pwd assignments
- **Tokens**: token, auth_token, access_token, bearer tokens
- **Cloud Credentials**: AWS access keys, secret keys
- **Database URLs**: Passwords in connection strings
- **Private Keys**: PEM format private keys

### Safe Patterns (Excluded)

- `os.getenv()`, `os.environ[]` - Environment variable loading
- `config.`, `settings.` - Configuration object access
- `SecretStr()` - Pydantic SecretStr wrappers
- `#` comments, docstrings
- `.env.example` files with placeholder values

### Example Output

```
Scanning shared_package/ for hardcoded credentials...

✗ Found 2 potential credential(s) in 1 file(s):

shared_package/config.py:
  - Password: 1 occurrence(s)
  - API Key: 1 occurrence(s)

Run with --verbose to see all findings
```

### When to Use

- **Before every commit** (add to pre-commit hook)
- After adding new scraper projects
- Periodic security audits
- Before code reviews

---

## Migration Procedure

### Pre-Migration

1. **Validate Current State**
   ```bash
   python tools/validate_env.py --check-all
   python tools/find_hardcoded_credentials.py shared_package/
   ```

2. **Backup Current Output**
   ```bash
   # Run scraper with current v2.0 code
   cd audiobee_bcbs_il
   python run_all.py  # Outputs to CURR_DATE directory
   ```

### Migration

3. **Update shared_package Submodule**
   ```bash
   cd shared_package
   git pull origin master
   cd ..
   git add shared_package
   git commit -m "Update shared_package to v3.0"
   ```

4. **Update Project Code**
   - Replace old imports with v3.0 equivalents
   - Update configuration loading
   - Migrate to new logging system
   - Use new validation models

### Post-Migration

5. **Test Migration**
   ```bash
   # Run scraper with v3.0 code
   cd audiobee_bcbs_il
   python run_all.py

   # Validate outputs match
   cd ..
   python tools/validate_migration.py audiobee_bcbs_il --prev 20251110 --curr 20251210
   ```

6. **Rollback if Needed**
   ```bash
   # If validation fails
   python tools/rollback_migration.py --list-commits
   python tools/rollback_migration.py --commit <previous> --execute
   ```

7. **Security Scan**
   ```bash
   python tools/find_hardcoded_credentials.py audiobee_bcbs_il/
   ```

---

## Integration with Git Hooks

### Pre-Commit Hook

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash

echo "Running security scan..."
python tools/find_hardcoded_credentials.py shared_package/

if [ $? -ne 0 ]; then
    echo "❌ Hardcoded credentials detected! Commit aborted."
    exit 1
fi

echo "✓ Security scan passed"
```

### Pre-Push Hook

Add to `.git/hooks/pre-push`:

```bash
#!/bin/bash

echo "Validating environment configuration..."
python tools/validate_env.py --check-all

if [ $? -ne 0 ]; then
    echo "❌ Environment validation failed! Push aborted."
    exit 1
fi

echo "✓ Environment validation passed"
```

---

## Troubleshooting

### validate_env.py

**Error**: "Missing required variable for sapphire: SCRAPER_PROJECT_NAME"
- **Fix**: Add `SCRAPER_PROJECT_NAME=your_project` to .env file

**Error**: "Invalid SCRAPER_SITE_TYPE: unknown"
- **Fix**: Use one of: sapphire, healthsparq, carrier, anthem

**Error**: "SCRAPER_CURR_DATE must be YYYYMMDD format"
- **Fix**: Use format like 20251226 (not 2025-12-26)

### validate_migration.py

**Error**: "Count difference: 12.3% (threshold: 5%)"
- **Investigate**: Significant data loss or duplication
- **Check**: NPI deduplication settings, API pagination

**Error**: "Record 123: Invalid NPI format"
- **Fix**: Ensure NPI extraction produces 10-digit strings
- **Check**: Data mapping in index_3.py

### rollback_migration.py

**Error**: "Repository has uncommitted changes"
- **Fix**: Commit or stash changes first: `git stash`

**Error**: "Failed to checkout <commit>"
- **Fix**: Verify commit hash is valid: `git log`

### find_hardcoded_credentials.py

**False Positive**: Detects `.env.example` placeholder
- **Normal**: .env.example is meant to show format
- **Action**: Ensure no real credentials in .env.example

**False Positive**: Detects `password = os.getenv("PASSWORD")`
- **Normal**: This is safe (loading from environment)
- **Action**: Pattern should be excluded (safe)

---

## Best Practices

1. **Always run validation before committing migrations**
2. **Use --dry-run first for rollbacks**
3. **Keep security scans in CI/CD pipeline**
4. **Document migration outcomes in git commit messages**
5. **Test migration on one project before scaling**
6. **Backup outputs before major changes**

## See Also

- **shared_package/CLAUDE.md**: v3.0 architecture documentation
- **docs/restructuring/SHARED_PACKAGE_IMPLEMENTATION_PLAN.md**: Full implementation plan
- **docs/restructuring/RALPH_EXECUTOR_PROMPT.md**: Phase-by-phase execution guide

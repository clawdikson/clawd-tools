# Submodule Policy

This repo keeps shared libraries as git submodules. To avoid churn and merge
conflicts, treat submodules as pinned dependencies rather than moving targets.

## Principles

- **Pin to tags or stable branches**. Avoid tracking `master`/`main` directly.
- **Update submodule SHAs only in dedicated bump commits**.
- **Never reference local-only commits**. Submodule commits must be pushed.

## Common workflows

### Sync to recorded SHAs

```bash
./scripts/sync-submodules.sh
```

This checks out submodules at the exact SHAs recorded in the parent repo.

### Pull latest from parent repo

```bash
./scripts/pull.sh
```

This pulls the parent repo and then syncs submodules to recorded SHAs.

### Bump submodules to a release

```bash
./scripts/bump-submodules.sh --core v3.2.1 --healthsparq v2.0.4
git commit -m "chore: bump submodules"
```

Use release tags (preferred) or a configured stable branch.

## Checks

Pre-commit hooks enforce submodule hygiene:

- clean working trees
- allowed refs (branch or tag)
- pushed commits on `origin` (pre-push)

Install hooks:

```bash
uv pip install pre-commit
pre-commit install
pre-commit install --hook-type pre-push
```

Strict tag-only policy:

```bash
export SUBMODULE_REQUIRE_TAG=1
```

## Conflict guidance

If two branches bump submodules, prefer the **newer tag** and re-run tests.

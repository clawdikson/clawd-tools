#!/usr/bin/env bash
#
# Fail if any submodule has uncommitted changes.
#
# Env:
#   ALLOW_MISSING_SUBMODULES=1  Allow missing submodule directories

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

if [[ ! -f "$REPO_ROOT/.gitmodules" ]]; then
    exit 0
fi

missing=()
dirty=()

while read -r key path; do
    name="${key#submodule.}"
    name="${name%.path}"

    if [[ ! -d "$REPO_ROOT/$path/.git" ]]; then
        missing+=("$name")
        continue
    fi

    status=$(git -C "$REPO_ROOT/$path" status --porcelain)
    if [[ -n "$status" ]]; then
        dirty+=("$name")
    fi
done < <(git config -f "$REPO_ROOT/.gitmodules" --get-regexp '^submodule\..*\.path$')

if [[ ${#missing[@]} -gt 0 && "${ALLOW_MISSING_SUBMODULES:-0}" != "1" ]]; then
    echo "Missing submodules (not initialized):"
    printf '  - %s\n' "${missing[@]}"
    echo "Run: git submodule update --init --recursive"
    exit 1
fi

if [[ ${#dirty[@]} -gt 0 ]]; then
    echo "Submodules have local changes:"
    printf '  - %s\n' "${dirty[@]}"
    echo "Commit/stash changes or run scripts/sync-submodules.sh --force"
    exit 1
fi

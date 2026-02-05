#!/usr/bin/env bash
#
# Ensure each submodule HEAD exists on the remote (branch or tag).
#
# Env:
#   SUBMODULE_REMOTE=origin
#   ALLOW_MISSING_SUBMODULES=1
#
# Options:
#   --skip-fetch  Do not fetch remote refs before checking

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

remote="${SUBMODULE_REMOTE:-origin}"
skip_fetch=false

for arg in "$@"; do
    case "$arg" in
        --skip-fetch) skip_fetch=true ;;
        --help|-h)
            sed -n '1,40p' "$0"
            exit 0
            ;;
    esac
done

if [[ ! -f "$REPO_ROOT/.gitmodules" ]]; then
    exit 0
fi

missing=()
missing_remote=()

while read -r key path; do
    name="${key#submodule.}"
    name="${name%.path}"

    if [[ ! -d "$REPO_ROOT/$path/.git" ]]; then
        missing+=("$name")
        continue
    fi

    if [[ "$skip_fetch" == false ]]; then
        git -C "$REPO_ROOT/$path" fetch "$remote" --tags --quiet
    fi

    sha=$(git -C "$REPO_ROOT/$path" rev-parse HEAD)
    if git -C "$REPO_ROOT/$path" tag --points-at "$sha" | grep -q .; then
        continue
    fi

    if git -C "$REPO_ROOT/$path" branch -r --contains "$sha" | grep -q "${remote}/"; then
        continue
    fi

    missing_remote+=("$name")
done < <(git config -f "$REPO_ROOT/.gitmodules" --get-regexp '^submodule\..*\.path$')

if [[ ${#missing[@]} -gt 0 && "${ALLOW_MISSING_SUBMODULES:-0}" != "1" ]]; then
    echo "Missing submodules (not initialized):"
    printf '  - %s\n' "${missing[@]}"
    echo "Run: git submodule update --init --recursive"
    exit 1
fi

if [[ ${#missing_remote[@]} -gt 0 ]]; then
    echo "Submodule commits not found on remote '$remote':"
    printf '  - %s\n' "${missing_remote[@]}"
    echo "Push the submodule commits or retarget to a published tag."
    exit 1
fi

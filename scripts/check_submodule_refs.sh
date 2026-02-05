#!/usr/bin/env bash
#
# Ensure submodules are on an allowed branch or an exact tag.
#
# Env:
#   SUBMODULE_ALLOWED_BRANCHES="master main stable release"
#   SUBMODULE_REQUIRE_TAG=1
#   ALLOW_MISSING_SUBMODULES=1
#
# Options:
#   --require-tag  Enforce exact tag checkouts only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

require_tag=false
for arg in "$@"; do
    case "$arg" in
        --require-tag) require_tag=true ;;
        --help|-h)
            sed -n '1,40p' "$0"
            exit 0
            ;;
    esac
done

if [[ "${SUBMODULE_REQUIRE_TAG:-0}" == "1" ]]; then
    require_tag=true
fi

allowed_branches="${SUBMODULE_ALLOWED_BRANCHES:-master main stable release}"

if [[ ! -f "$REPO_ROOT/.gitmodules" ]]; then
    exit 0
fi

missing=()
violations=()

while read -r key path; do
    name="${key#submodule.}"
    name="${name%.path}"

    if [[ ! -d "$REPO_ROOT/$path/.git" ]]; then
        missing+=("$name")
        continue
    fi

    if git -C "$REPO_ROOT/$path" describe --tags --exact-match >/dev/null 2>&1; then
        continue
    fi

    if [[ "$require_tag" == true ]]; then
        violations+=("$name (detached or branch without tag)")
        continue
    fi

    branch=$(git -C "$REPO_ROOT/$path" rev-parse --abbrev-ref HEAD)
    if [[ "$branch" == "HEAD" ]]; then
        violations+=("$name (detached without tag)")
        continue
    fi

    configured_branch=$(git config -f "$REPO_ROOT/.gitmodules" "submodule.${name}.branch" || true)
    allowed="$allowed_branches"
    if [[ -n "$configured_branch" ]]; then
        allowed="$configured_branch $allowed"
    fi

    if [[ " $allowed " != *" $branch "* ]]; then
        violations+=("$name (branch $branch)")
    fi
done < <(git config -f "$REPO_ROOT/.gitmodules" --get-regexp '^submodule\..*\.path$')

if [[ ${#missing[@]} -gt 0 && "${ALLOW_MISSING_SUBMODULES:-0}" != "1" ]]; then
    echo "Missing submodules (not initialized):"
    printf '  - %s\n' "${missing[@]}"
    echo "Run: git submodule update --init --recursive"
    exit 1
fi

if [[ ${#violations[@]} -gt 0 ]]; then
    echo "Submodules not on allowed refs:"
    printf '  - %s\n' "${violations[@]}"
    echo "Use scripts/bump-submodules.sh to pin to a tag or configured branch."
    exit 1
fi

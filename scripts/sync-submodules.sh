#!/usr/bin/env bash
#
# Sync submodules to the SHAs recorded in the parent repo.
# Run from repo root: ./scripts/sync-submodules.sh
#
# Use scripts/bump-submodules.sh to move submodules to new refs.
#
# Options:
#   --force    Discard local changes in submodules before syncing
#   --pull     Also pull the main repo first (no remote submodule auto-advance)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
GRAY='\033[0;90m'
NC='\033[0m'

# Parse arguments
FORCE=false
PULL=false

for arg in "$@"; do
    case $arg in
        --force) FORCE=true ;;
        --pull) PULL=true ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --force    Discard local changes in submodules before syncing"
            echo "  --pull     Also pull the main repo first"
            echo "  --help     Show this help message"
            exit 0
            ;;
    esac
done

echo -e "${CYAN}=== Submodule Sync Script ===${NC}"
echo -e "${GRAY}Repo root: $REPO_ROOT${NC}"

cd "$REPO_ROOT"

# Optionally pull main repo first
if [[ "$PULL" == true ]]; then
    echo -e "\n${YELLOW}Pulling main repository...${NC}"
    git pull --recurse-submodules=on-demand
fi

if [[ ! -f "$REPO_ROOT/.gitmodules" ]]; then
    echo -e "${YELLOW}No .gitmodules file found. Nothing to sync.${NC}"
    exit 0
fi

list_submodules() {
    git config -f "$REPO_ROOT/.gitmodules" --get-regexp '^submodule\..*\.path$' | while read -r key path; do
        name="${key#submodule.}"
        name="${name%.path}"
        echo "$name|$path"
    done
}

dirty_submodules=()
missing_submodules=()

while IFS='|' read -r name path; do
    if [[ -z "$path" ]]; then
        continue
    fi

    if [[ ! -d "$REPO_ROOT/$path" ]]; then
        missing_submodules+=("$path")
        continue
    fi

    status=$(git -C "$REPO_ROOT/$path" status --porcelain)
    if [[ -n "$status" ]]; then
        if [[ "$FORCE" == true ]]; then
            echo -e "${YELLOW}[$name] Discarding local changes...${NC}"
            git -C "$REPO_ROOT/$path" reset --hard
        else
            dirty_submodules+=("$name")
        fi
    fi
done < <(list_submodules)

if [[ ${#dirty_submodules[@]} -gt 0 ]]; then
    echo -e "${RED}Submodules have local changes:${NC}"
    printf '  - %s\n' "${dirty_submodules[@]}"
    echo -e "${YELLOW}Commit, stash, or re-run with --force to discard changes.${NC}"
    exit 1
fi

if [[ ${#missing_submodules[@]} -gt 0 ]]; then
    echo -e "${YELLOW}Initializing missing submodules:${NC}"
    printf '  - %s\n' "${missing_submodules[@]}"
fi

echo -e "\n${CYAN}Syncing submodules to recorded SHAs...${NC}"
git submodule update --init --recursive

echo -e "\n${CYAN}=== Sync Complete ===${NC}"
git submodule status

echo -e "\n${GRAY}To reinstall packages, run:${NC}"
echo "  uv pip install -e ./core -e ./healthsparq --force-reinstall --no-deps"

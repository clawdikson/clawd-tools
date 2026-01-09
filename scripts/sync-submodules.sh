#!/usr/bin/env bash
#
# Sync all submodules to their remote master branches
# Run from repo root: ./scripts/sync-submodules.sh
#
# This script handles the common "commits don't follow merge-base" conflict
# by resetting submodules to origin/master.
#
# Options:
#   --force    Reset even if there are local changes
#   --pull     Also pull the main repo first

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
            echo "  --force    Reset even if there are local changes"
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
    git fetch origin

    # Check if we're in a merge conflict state
    if [[ -f ".git/MERGE_HEAD" ]]; then
        echo -e "${YELLOW}Merge in progress, will resolve submodule conflicts...${NC}"
    fi
fi

# List of submodules to sync
submodules=("core" "healthsparq" "sapphire" "output_generator")

for submodule in "${submodules[@]}"; do
    submodule_path="$REPO_ROOT/$submodule"

    if [[ ! -d "$submodule_path" ]]; then
        echo -e "\n${GRAY}[$submodule] Not found, skipping...${NC}"
        continue
    fi

    echo -e "\n${CYAN}[$submodule] Syncing...${NC}"

    cd "$submodule_path"

    # Check for local changes
    status=$(git status --porcelain)
    if [[ -n "$status" && "$FORCE" != true ]]; then
        echo -e "  ${YELLOW}WARNING: Local changes detected. Use --force to override.${NC}"
        echo -e "  ${GRAY}$status${NC}"
        cd "$REPO_ROOT"
        continue
    fi

    # Fetch and reset to origin/master
    echo -e "  ${GRAY}Fetching origin...${NC}"
    git fetch origin

    echo -e "  ${GRAY}Resetting to origin/master...${NC}"
    git reset --hard origin/master

    current_commit=$(git rev-parse --short HEAD)
    echo -e "  ${GREEN}Now at: $current_commit${NC}"

    cd "$REPO_ROOT"
done

# Stage all submodule changes
echo -e "\n${YELLOW}Staging submodule updates...${NC}"
for submodule in "${submodules[@]}"; do
    if [[ -d "$submodule" ]]; then
        git add "$submodule" 2>/dev/null || true
    fi
done

# Check if we need to complete a merge
if [[ -f ".git/MERGE_HEAD" ]]; then
    echo -e "\n${YELLOW}Completing merge...${NC}"

    # Stage any other conflicted files (accept theirs for non-submodule conflicts)
    conflicts=$(git diff --name-only --diff-filter=U 2>/dev/null || true)
    if [[ -n "$conflicts" ]]; then
        echo -e "  ${GRAY}Resolving file conflicts...${NC}"
        while IFS= read -r file; do
            # Check if file is not a submodule
            is_submodule=false
            for sub in "${submodules[@]}"; do
                if [[ "$file" == "$sub" ]]; then
                    is_submodule=true
                    break
                fi
            done

            if [[ "$is_submodule" != true ]]; then
                git checkout --theirs "$file" 2>/dev/null || true
                git add "$file"
            fi
        done <<< "$conflicts"
    fi

    # Complete the merge
    git commit -m "chore: merge remote changes and sync submodules"
    echo -e "${GREEN}Merge completed!${NC}"
fi

echo -e "\n${CYAN}=== Sync Complete ===${NC}"
git status --short

echo -e "\n${GRAY}To reinstall packages, run:${NC}"
echo "  uv pip install -e ./core -e ./healthsparq --force-reinstall --no-deps"

#!/usr/bin/env bash
#
# Pull repository and sync all submodules
# Run from repo root: ./scripts/pull.sh
#
# This script handles the common submodule conflicts automatically.
#
# Options:
#   --reinstall    Also reinstall packages after pull

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
REINSTALL=false
for arg in "$@"; do
    case $arg in
        --reinstall) REINSTALL=true ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --reinstall  Also reinstall packages after pull"
            echo "  --help       Show this help message"
            exit 0
            ;;
    esac
done

cd "$REPO_ROOT"

echo -e "${CYAN}=== Git Pull with Submodules ===${NC}"

# Step 1: Fetch everything
echo -e "\n${YELLOW}[1/4] Fetching all remotes...${NC}"
git fetch --all --recurse-submodules

# Step 2: Update submodules to remote first (prevents conflicts)
echo -e "\n${YELLOW}[2/4] Updating submodules to origin/master...${NC}"
submodules=("core" "healthsparq" "sapphire" "output_generator")

for sub in "${submodules[@]}"; do
    if [[ -d "$sub" ]]; then
        (
            cd "$sub"
            git fetch origin 2>/dev/null || true
            git reset --hard origin/master 2>/dev/null || true
            commit=$(git rev-parse --short HEAD)
            echo -e "  ${GRAY}$sub -> $commit${NC}"
        )
    fi
done

# Step 3: Pull main repo (should be clean now)
echo -e "\n${YELLOW}[3/4] Pulling main repository...${NC}"
if ! git pull --no-recurse-submodules; then
    # If pull failed, we might have a merge in progress
    if [[ -f ".git/MERGE_HEAD" ]]; then
        echo -e "  ${YELLOW}Resolving merge...${NC}"

        # Stage submodules
        for sub in "${submodules[@]}"; do
            if [[ -d "$sub" ]]; then
                git add "$sub" 2>/dev/null || true
            fi
        done

        # Check for remaining conflicts
        conflicts=$(git diff --name-only --diff-filter=U 2>/dev/null || true)
        if [[ -n "$conflicts" ]]; then
            echo -e "  ${RED}Remaining conflicts:${NC}"
            echo -e "  ${RED}$conflicts${NC}"
            echo -e "\n  ${YELLOW}Please resolve manually, then run:${NC}"
            echo "  git add <files>"
            echo "  git commit"
            exit 1
        fi

        # Complete merge
        git commit -m "chore: merge remote changes"
        echo -e "  ${GREEN}Merge completed!${NC}"
    else
        echo -e "  ${RED}Pull failed!${NC}"
        exit 1
    fi
fi

# Step 4: Final submodule sync (in case pull updated pointers)
echo -e "\n${YELLOW}[4/4] Final submodule sync...${NC}"
git submodule update --init --recursive

echo -e "\n${GREEN}=== Pull Complete ===${NC}"
git log --oneline -3
echo ""

# Optionally reinstall packages
if [[ "$REINSTALL" == true ]]; then
    echo -e "${YELLOW}Reinstalling packages...${NC}"
    uv pip install -e ./core -e ./healthsparq --force-reinstall --no-deps
fi

echo -e "\n${GRAY}Done! To reinstall packages:${NC}"
echo "  ./scripts/reinstall_packages.sh"

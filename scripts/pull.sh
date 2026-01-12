#!/usr/bin/env bash
#
# Pull repository and sync submodules to recorded SHAs
# Run from repo root: ./scripts/pull.sh
#
# This script avoids auto-advancing submodules to remote branches.
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
echo -e "\n${YELLOW}[1/3] Fetching all remotes...${NC}"
git fetch --all --recurse-submodules=on-demand

# Step 2: Pull main repo (no auto-advance of submodules)
echo -e "\n${YELLOW}[2/3] Pulling main repository...${NC}"
if ! git pull --recurse-submodules=on-demand; then
    if [[ -f ".git/MERGE_HEAD" ]]; then
        echo -e "  ${RED}Merge in progress. Resolve conflicts, then run:${NC}"
        echo "  git add <files>"
        echo "  git commit"
        exit 1
    fi

    echo -e "  ${RED}Pull failed!${NC}"
    exit 1
fi

# Step 3: Sync submodules to recorded SHAs
echo -e "\n${YELLOW}[3/3] Syncing submodules...${NC}"
"$SCRIPT_DIR/sync-submodules.sh"

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

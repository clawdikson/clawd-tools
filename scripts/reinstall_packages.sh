#!/usr/bin/env bash
#
# Reinstall core and healthsparq packages with latest changes
# Run from repo root: ./scripts/reinstall_packages.sh
#
# Options:
#   --sync    Also sync submodules to origin/master first
#   --all     Install all local packages (including sapphire)

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
SYNC=false
ALL=false

for arg in "$@"; do
    case $arg in
        --sync) SYNC=true ;;
        --all) ALL=true ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --sync    Also sync submodules to origin/master first"
            echo "  --all     Install all local packages (including sapphire)"
            echo "  --help    Show this help message"
            exit 0
            ;;
    esac
done

cd "$REPO_ROOT"

# Optionally sync submodules first
if [[ "$SYNC" == true ]]; then
    echo -e "${YELLOW}Syncing submodules first...${NC}"
    "$SCRIPT_DIR/sync-submodules.sh"
    echo ""
fi

echo -e "${CYAN}=== Reinstalling Packages ===${NC}"

# Build package list
packages=("./core" "./healthsparq")
if [[ "$ALL" == true ]]; then
    packages+=("./sapphire" "./output_generator")
fi

# Build install arguments
install_args=()
for pkg in "${packages[@]}"; do
    install_args+=("-e" "$pkg")
done

echo -e "${GRAY}Installing: ${packages[*]}${NC}"

if ! uv pip install "${install_args[@]}" --force-reinstall --no-deps; then
    echo -e "${RED}Failed to install packages${NC}"
    exit 1
fi

echo -e "\n${GREEN}Packages reinstalled successfully!${NC}"
echo ""
echo -e "${GRAY}Installed packages:${NC}"
uv pip list | grep -E "^(core|healthsparq|sapphire|output)" || true

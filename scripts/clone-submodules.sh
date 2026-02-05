#!/usr/bin/env bash
#
# Clone submodules helper script
# Dynamically parses .gitmodules and clones/updates submodules
#
# Usage:
#   ./scripts/clone-submodules.sh          # Standard submodule init/update
#   ./scripts/clone-submodules.sh --fresh  # Fresh clone (removes existing)
#   ./scripts/clone-submodules.sh --shallow # Shallow clone (faster)
#   ./scripts/clone-submodules.sh --standalone # Clone as separate repos (not submodules)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
GITMODULES="$ROOT_DIR/.gitmodules"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
FRESH=false
SHALLOW=false
STANDALONE=false

for arg in "$@"; do
    case $arg in
        --fresh) FRESH=true ;;
        --shallow) SHALLOW=true ;;
        --standalone) STANDALONE=true ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --fresh      Remove existing submodule dirs before cloning"
            echo "  --shallow    Use shallow clones (depth=1) for faster setup"
            echo "  --standalone Clone as separate git repos instead of submodules"
            echo "  --help       Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $arg${NC}"
            exit 1
            ;;
    esac
done

# Check .gitmodules exists
if [[ ! -f "$GITMODULES" ]]; then
    echo -e "${RED}Error: .gitmodules not found at $GITMODULES${NC}"
    exit 1
fi

# Parse .gitmodules dynamically
# Returns: "path|url" pairs
parse_gitmodules() {
    local current_path=""
    local current_url=""

    while IFS= read -r line || [[ -n "$line" ]]; do
        # Trim whitespace
        line="${line#"${line%%[![:space:]]*}"}"
        line="${line%"${line##*[![:space:]]}"}"

        if [[ "$line" =~ ^path[[:space:]]*=[[:space:]]*(.+)$ ]]; then
            current_path="${BASH_REMATCH[1]}"
        elif [[ "$line" =~ ^url[[:space:]]*=[[:space:]]*(.+)$ ]]; then
            current_url="${BASH_REMATCH[1]}"
        fi

        # Output when we have both path and url
        if [[ -n "$current_path" && -n "$current_url" ]]; then
            echo "$current_path|$current_url"
            current_path=""
            current_url=""
        fi
    done < "$GITMODULES"
}

# Count and process submodules
cd "$ROOT_DIR"
submodule_count=$(parse_gitmodules | wc -l | tr -d ' ')
echo -e "${GREEN}Found $submodule_count submodules in .gitmodules${NC}"
echo ""

parse_gitmodules | while IFS='|' read -r path url; do
    full_path="$ROOT_DIR/$path"

    echo -e "${YELLOW}Processing: $path${NC}"
    echo "  URL: $url"

    # Handle fresh clone
    if [[ "$FRESH" == true && -d "$full_path" ]]; then
        echo "  Removing existing directory..."
        rm -rf "$full_path"
    fi

    if [[ "$STANDALONE" == true ]]; then
        # Clone as separate repository
        if [[ -d "$full_path/.git" ]]; then
            echo -e "  ${GREEN}Already exists, pulling latest...${NC}"
            (cd "$full_path" && git pull --rebase)
        elif [[ -d "$full_path" ]]; then
            echo -e "  ${YELLOW}Directory exists but not a git repo, skipping${NC}"
        else
            echo "  Cloning as standalone repo..."
            if [[ "$SHALLOW" == true ]]; then
                git clone --depth 1 "$url" "$path"
            else
                git clone "$url" "$path"
            fi
        fi
    else
        # Use git submodule commands
        if [[ "$SHALLOW" == true ]]; then
            echo "  Initializing with shallow clone..."
            git submodule update --init --depth 1 "$path"
        else
            echo "  Initializing submodule..."
            git submodule update --init "$path"
        fi
    fi

    # Verify
    if [[ -d "$full_path" ]]; then
        echo -e "  ${GREEN}OK${NC}"
    else
        echo -e "  ${RED}FAILED${NC}"
    fi
    echo ""
done

echo -e "${GREEN}Done!${NC}"

# Show status
echo ""
echo "Submodule status:"
git submodule status

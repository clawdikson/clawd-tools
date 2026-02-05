#!/usr/bin/env bash
#
# Bump submodules to explicit refs (tags or branches).
# Run from repo root: ./scripts/bump-submodules.sh --core v3.2.1
#
# Examples:
#   ./scripts/bump-submodules.sh --core v3.2.1 --healthsparq v2.0.4
#   ./scripts/bump-submodules.sh --all v2025.01.15
#
# Options:
#   --all <ref>              Apply the same ref to all submodules
#   --core <ref>             Update core submodule
#   --healthsparq <ref>      Update healthsparq submodule
#   --sapphire <ref>         Update sapphire submodule
#   --output_generator <ref> Update output_generator submodule
#   --help                   Show this help

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

if [[ ! -f "$REPO_ROOT/.gitmodules" ]]; then
    echo "Error: .gitmodules not found in $REPO_ROOT"
    exit 1
fi

declare -A sub_paths=()
while read -r key path; do
    name="${key#submodule.}"
    name="${name%.path}"
    sub_paths["$name"]="$path"
done < <(git config -f "$REPO_ROOT/.gitmodules" --get-regexp '^submodule\..*\.path$')

declare -A refs=()
all_ref=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --all)
            all_ref="${2:-}"
            shift 2
            ;;
        --core|--healthsparq|--sapphire|--output_generator)
            name="${1#--}"
            ref="${2:-}"
            if [[ -z "$ref" ]]; then
                echo "Error: Missing ref for $1"
                exit 1
            fi
            refs["$name"]="$ref"
            shift 2
            ;;
        --help|-h)
            sed -n '1,40p' "$0"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

if [[ -n "$all_ref" ]]; then
    for name in "${!sub_paths[@]}"; do
        refs["$name"]="$all_ref"
    done
fi

if [[ ${#refs[@]} -eq 0 ]]; then
    echo "Error: No submodules specified."
    echo "Run with --help for usage."
    exit 1
fi

cd "$REPO_ROOT"

for name in "${!refs[@]}"; do
    path="${sub_paths[$name]:-}"
    ref="${refs[$name]}"

    if [[ -z "$path" ]]; then
        echo "Error: Submodule '$name' not found in .gitmodules"
        exit 1
    fi

    if [[ ! -d "$path/.git" ]]; then
        echo "Error: Submodule '$name' is not initialized at $path"
        exit 1
    fi

    status=$(git -C "$path" status --porcelain)
    if [[ -n "$status" ]]; then
        echo "Error: Submodule '$name' has local changes. Commit or stash first."
        exit 1
    fi

    echo "==> $name: fetching refs..."
    git -C "$path" fetch --tags origin

    if ! git -C "$path" rev-parse --verify "${ref}^{commit}" >/dev/null 2>&1; then
        echo "Error: Ref '$ref' not found in '$name'"
        exit 1
    fi

    echo "==> $name: checking out $ref"
    git -C "$path" checkout "$ref"

    commit=$(git -C "$path" rev-parse --short HEAD)
    echo "==> $name: now at $commit"

    git add "$path"
done

echo ""
echo "Submodule pointers updated and staged."
echo "Review with: git status --short"
echo "Commit with: git commit -m \"chore: bump submodules\""

#!/bin/bash
# Resolves hook path from monorepo root regardless of current working directory
# Usage: resolve-hook.sh <hook_name.py>
set -e

HOOK="$1"

# Priority: git superproject (monorepo root) > git toplevel > CLAUDE_PROJECT_DIR
find_monorepo_root() {
    # Check if we're in a git submodule and get the parent repo root
    local superproject
    superproject=$(git rev-parse --show-superproject-working-tree 2>/dev/null)
    if [[ -n "$superproject" ]]; then
        echo "$superproject"
        return
    fi

    # Fallback to git toplevel (handles non-submodule case)
    local toplevel
    toplevel=$(git rev-parse --show-toplevel 2>/dev/null)
    if [[ -n "$toplevel" ]]; then
        echo "$toplevel"
        return
    fi

    # Final fallback to CLAUDE_PROJECT_DIR
    echo "${CLAUDE_PROJECT_DIR:-.}"
}

ROOT="$(find_monorepo_root)"
HOOK_PATH="$ROOT/.claude/hooks/$HOOK"

if [[ -f "$HOOK_PATH" ]]; then
    cat | exec "$HOOK_PATH"
else
    # Hook not found - continue silently
    echo '{"result":"continue"}'
fi

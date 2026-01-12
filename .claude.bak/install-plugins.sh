#!/bin/bash
# Install missing plugins for this project
# Run this script inside the project directory

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
echo "Installing plugins for: $PROJECT_DIR"
echo ""

# Plugins to install
PLUGINS=(
    "hookify@claude-plugins-official"
    "typescript-lsp@claude-plugins-official"
    "claude-mem@thedotmack"
    "serena@claude-plugins-official"
    "compound-engineering@every-marketplace"
    "playwright-skill@playwright-skill"
    "frontend-design@claude-code-plugins"
    "beads@beads-marketplace"
)

echo "Run these commands in a Claude Code session:"
echo ""
for plugin in "${PLUGINS[@]}"; do
    echo "/plugin install $plugin"
done
echo ""
echo "Or copy this one-liner:"
echo ""
echo -n "/plugin install "
echo "${PLUGINS[*]}" | tr ' ' ' && /plugin install '

#!/bin/bash

# Sync debugging knowledge base from ClickUp
# This script handles the MECHANICAL part only (fetch + diff)
# The actual AI rewriting should be done by a separate cron job agent

set -euo pipefail

# Source environment variables
source ~/.clawdbot/.env

# ClickUp API configuration
CLICKUP_WORKSPACE_ID="9017490901"
CLICKUP_DOC_ID="8cqqzen-4197"
CLICKUP_API_URL="https://api.clickup.com/api/v3/workspaces/${CLICKUP_WORKSPACE_ID}/docs/${CLICKUP_DOC_ID}/pages"

# File paths
INDEX_FILE="docs/debugging/index.json"
TEMP_FILE="/tmp/clickup_pages_$(date +%s).json"

# Function to log messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >&2
}

# Function to extract leaf pages from nested JSON
extract_leaf_pages() {
    local json_file="$1"
    python3 -c "
import json
import sys

def extract_leaf_pages(pages, current_path=[]):
    leaf_pages = []
    
    for page in pages:
        new_path = current_path + [page['name']]
        
        if page.get('pages'):
            leaf_pages.extend(extract_leaf_pages(page['pages'], new_path))
        elif page.get('content') and page['content'].strip():
            leaf_pages.append({
                'id': page['id'],
                'name': page['name'],
                'content': page['content'],
                'path': new_path,
                'date_updated': page['date_updated'],
                'path_str': '/'.join(new_path[1:])  # Skip root
            })
    
    return leaf_pages

with open('$json_file', 'r') as f:
    data = json.load(f)

leaf_pages = extract_leaf_pages(data)
json.dump(leaf_pages, sys.stdout, indent=2)
"
}

# Function to get existing entries from index
get_existing_entries() {
    if [[ -f "$INDEX_FILE" ]]; then
        python3 -c "
import json
import sys
try:
    with open('$INDEX_FILE', 'r') as f:
        index = json.load(f)
    existing = {}
    for entry in index.get('entries', []):
        existing[entry['clickup_page_id']] = entry['clickup_date_updated']
    json.dump(existing, sys.stdout)
except Exception as e:
    print('{}', file=sys.stderr)
    sys.exit(1)
"
    else
        echo "{}"
    fi
}

# Main function
main() {
    log "Starting ClickUp debugging KB sync check"
    
    # Fetch current ClickUp pages
    log "Fetching ClickUp pages..."
    if ! curl -s "$CLICKUP_API_URL" \
         -H "Authorization: $CLICKUP_API_TOKEN" \
         -o "$TEMP_FILE"; then
        log "ERROR: Failed to fetch ClickUp pages"
        exit 1
    fi
    
    # Validate JSON response
    if ! python3 -c "import json; json.load(open('$TEMP_FILE'))" 2>/dev/null; then
        log "ERROR: Invalid JSON response from ClickUp API"
        cat "$TEMP_FILE" >&2
        rm -f "$TEMP_FILE"
        exit 1
    fi
    
    # Extract leaf pages
    log "Extracting leaf pages..."
    LEAF_PAGES=$(extract_leaf_pages "$TEMP_FILE")
    
    # Get existing entries
    log "Loading existing index..."
    EXISTING_ENTRIES=$(get_existing_entries)
    
    # Find new or updated entries
    log "Comparing with existing entries..."
    NEW_ENTRIES=$(echo "$LEAF_PAGES" | python3 -c "
import json
import sys

existing = json.loads('''$EXISTING_ENTRIES''')
leaf_pages = json.load(sys.stdin)

new_or_updated = []
for page in leaf_pages:
    page_id = page['id']
    date_updated = page['date_updated']
    
    if page_id not in existing or existing[page_id] != date_updated:
        new_or_updated.append(page)

print(f'Found {len(new_or_updated)} new or updated entries', file=sys.stderr)
json.dump(new_or_updated, sys.stdout, indent=2)
")
    
    # Output results
    echo "$NEW_ENTRIES"
    
    # Cleanup
    rm -f "$TEMP_FILE"
    
    # Exit with status code indicating if there are changes
    CHANGE_COUNT=$(echo "$NEW_ENTRIES" | python3 -c "import json, sys; print(len(json.load(sys.stdin)))")
    if [[ "$CHANGE_COUNT" -gt 0 ]]; then
        log "Found $CHANGE_COUNT new/updated entries"
        exit 1  # Exit code 1 indicates changes found
    else
        log "No changes found"
        exit 0  # Exit code 0 indicates no changes
    fi
}

# Handle arguments
case "${1:-check}" in
    "check")
        main
        ;;
    "help"|"--help"|"-h")
        cat << EOF
Usage: $0 [check|help]

Sync debugging knowledge base from ClickUp (mechanical check only).

Commands:
  check     Check for new/updated entries and output JSON (default)
  help      Show this help message

Environment variables required:
  CLICKUP_API_TOKEN  - ClickUp API token

Output:
  - JSON array of new/updated entries to stdout
  - Log messages to stderr
  - Exit code 0: no changes, 1: changes found, 2: error

Example:
  $0 check | jq '.[] | .path_str'
EOF
        exit 0
        ;;
    *)
        log "ERROR: Unknown command '$1'"
        log "Use '$0 help' for usage information"
        exit 2
        ;;
esac
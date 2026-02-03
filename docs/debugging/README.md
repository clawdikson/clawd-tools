# Scraping Debugging Knowledge Base

This knowledge base contains AI-rewritten debugging learnings from scraping operations, automatically synced from our ClickUp documentation. It's designed to help developers quickly find solutions to common scraping issues and help AI agents provide better debugging assistance.

## 📂 Structure

```
docs/debugging/
├── README.md              # This file
├── index.json            # Machine-readable index for AI agents
├── healthsparq/          # Healthsparq site type
│   ├── audiobee_maine_community_health_options/
│   └── audiobee_bluecard_national/
├── carrier/              # Carrier site type
│   ├── audiobee_devoted_health/
│   ├── audiobee_mainecare/
│   └── audiobee_firstcare_health/
└── sapphire/             # Sapphire site type
    ├── audiobee_molina/
    └── audiobee_braven_health/
```

Each organization contains dated debugging entries (YYYY-MM-DD.md) with structured solutions.

## 🔍 How to Search and Browse

### For Developers

**By Site Type:**
```bash
# Find all healthsparq issues
find docs/debugging/healthsparq -name "*.md"

# Find all carrier issues
find docs/debugging/carrier -name "*.md"
```

**By Error Type:**
```bash
# Search for NPI-related issues
grep -r "npi" docs/debugging/ --include="*.md"

# Search for 403/blocking issues
grep -r "403\|blocking" docs/debugging/ --include="*.md"

# Search for false drops
grep -r "false.drop\|missing.providers" docs/debugging/ --include="*.md"
```

**By Organization:**
```bash
# Find all issues for a specific organization
ls docs/debugging/*/audiobee_maine_community_health_options/
```

**By Date Range:**
```bash
# Find recent issues (last 7 days)
find docs/debugging -name "2026-01-*.md" | sort
```

### Using the Claude Command

Use the `/search-debugging` slash command in Claude Code:
```
/search-debugging NPI matching issues
/search-debugging 403 blocking healthsparq
/search-debugging missing providers devoted health
```

## 🤖 For AI Agents

**Primary Interface:** Always read `index.json` first for efficient lookup:

```python
import json

# Load the index
with open('docs/debugging/index.json') as f:
    index = json.load(f)

# Find entries by criteria
npi_issues = [e for e in index['entries'] if 'npi-matching' in e['tags']]
blocking_issues = [e for e in index['entries'] if 'request-blocking' in e['tags']]
recent_issues = [e for e in index['entries'] if e['date'] >= '2026-01-26']
```

**Search Strategy:**
1. Query `index.json` by tags, site_type, organization, or error_type
2. Read matching markdown files for detailed solutions
3. Prioritize recent entries for current issues
4. Look for patterns across similar error types

## 📋 Entry Format

Each debugging entry follows this structure:

```yaml
---
site_type: healthsparq
organization: audiobee_maine_community_health_options
date: 2026-01-26
error_type: "False NPI drop"
clickup_page_id: 8cqqzen-3657
synced_at: 2026-02-03T01:53:48.668816Z
tags: ['healthsparq', 'false-drops', 'search', 'auto-qa', 'npi-matching']
---
```

**Sections:**
- **Error** — Clear problem statement
- **Root Cause** — Technical explanation
- **Fix** — Solution with code references
- **Debugging Process** — Step-by-step diagnosis
- **Key Takeaway** — Main lesson learned
- **Additional Notes** — Extra context

## 🏷️ Tag System

**Error Types:**
- `request-blocking` — 403 errors, IP blocks, anti-bot measures
- `npi-matching` — NPI search and matching issues
- `false-drops` — Missing providers, incorrect filtering
- `data-mapping` — Data transformation and mapping errors
- `caching` — Cache-related issues
- `deprecated-code` — Legacy code problems
- `auto-qa` — AutoQA script issues
- `proxy` — Proxy configuration problems
- `search` — Search API and algorithm issues

**Site Types:**
- `healthsparq` — Healthsparq platform sites
- `carrier` — Insurance carrier sites  
- `sapphire` — Sapphire platform sites

## 🔄 Auto-Sync Process

This knowledge base is automatically synchronized from ClickUp:

1. **Daily Sync** — Cron job checks for new ClickUp entries
2. **Change Detection** — Compares `clickup_date_updated` timestamps
3. **AI Rewriting** — New content is cleaned and restructured
4. **Index Update** — `index.json` is updated with new entries
5. **Git Commit** — Changes are automatically committed

**Sync Scripts:**
- `scripts/sync-debugging-kb.sh` — Shell script for basic sync
- `scripts/sync-debugging-kb-full.py` — Python script with full functionality

## 🎯 Best Practices

**For Contributors:**
- Keep ClickUp entries detailed and factual
- Include specific error messages and steps
- Reference code files and line numbers when possible
- Add screenshots for UI-related issues

**For Searchers:**
- Start with tags and error types for broad categories
- Use specific site names for organization-focused searches
- Check recent entries first for similar current issues
- Read the full debugging process for complex problems

## 📊 Statistics

- **Total Entries:** Check `index.json` → `total_entries`
- **Last Synced:** Check `index.json` → `last_synced`
- **Coverage:** 3 site types, 8 organizations
- **Date Range:** 2026-01-26 to present

---

*This knowledge base is automatically maintained. For questions or issues with the sync process, contact the development team.*
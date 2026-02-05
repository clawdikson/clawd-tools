# Search and Filter Guide

Learn how to quickly find projects using various search methods.

## Using Command Line Tools

### Search by State

Find all projects serving a specific state:
```bash
grep -r "State Coverage.*CA" .
```

Or use the CSV directly:
```bash
grep "CA" "Rates Quotation Reports.csv"
```

### Search by Coverage Type

Find Medicare Advantage projects:
```bash
grep -r "Medicare Advantage" docs/
```

Find Medicaid projects:
```bash
grep -r "Medicaid" docs/
```

### Search by Site Type

Find all Healthsparq projects:
```bash
grep -r "Site Type.*Healthsparq" .
```

Or browse the category page:
```bash
cat docs/by-site-type/healthsparq.md
```

### Search by Project Name

Find a specific project:
```bash
find . -name "*anthem*" -type d
```

Or search in documentation:
```bash
grep -i "anthem" docs/project-links.md
```

## Using the Documentation

### Browse by Category

1. Open [site-type-mapping.md](./site-type-mapping.md)
2. Find your site type section
3. Browse projects in that category

### Use Quick Reference

1. Open [quick-reference.md](./quick-reference.md)
2. Check summary tables
3. Find projects by stats

### Alphabetical Listing

1. Open [project-links.md](./project-links.md)
2. Browse A-Z listing
3. Click direct links to CLAUDE.md

## Search Patterns

### Find Projects by Multiple Criteria

**Example**: Find Medicaid projects in California
```bash
grep "CA" "Rates Quotation Reports.csv" | grep "Medicaid"
```

**Example**: Find Healthsparq ACA projects
```bash
cat docs/by-site-type/healthsparq.md | grep -A 5 "ACA"
```

### Find Recently Approved Projects

```bash
grep "2024-12\|2025" "Rates Quotation Reports.csv"
```

### Find Monthly vs Quarterly Projects

```bash
grep "Monthly" "Rates Quotation Reports.csv" | wc -l
grep "Quarterly" "Rates Quotation Reports.csv" | wc -l
```

## Advanced Searches

### Using grep with Regular Expressions

Find projects in multiple states:
```bash
grep -E "(CA|NY|TX)" docs/project-links.md
```

Find all Blue Cross Blue Shield projects:
```bash
grep -i "bcbs\|blue cross\|blue shield" docs/project-links.md
```

### Using find Command

Find all CLAUDE.md files:
```bash
find . -name "CLAUDE.md" -type f
```

Find projects without CLAUDE.md:
```bash
for dir in audiobee_*/; do
    if [ ! -f "$dir/CLAUDE.md" ]; then
        echo "$dir"
    fi
done
```

### Using CSV Tools

If you have `csvkit` installed:
```bash
csvgrep -c "State" -m "CA" "Rates Quotation Reports.csv"
csvstat "Rates Quotation Reports.csv"
```

## Claude Code Search

Within Claude Code, you can search using:

### Glob Pattern
```
**/*anthem*/CLAUDE.md
```

### Grep Search
```
pattern: "Medicare Advantage"
glob: "*.md"
```

## Common Search Tasks

### Task: Find all projects for a new state

1. Search CSV: `grep "STATE_CODE" "Rates Quotation Reports.csv"`
2. Check documentation: `grep "STATE_CODE" docs/quick-reference.md`

### Task: Find similar projects for reference

1. Identify site type: Check project's CLAUDE.md
2. Browse category: `cat docs/by-site-type/SITE_TYPE.md`
3. Review similar projects' code

### Task: Find projects needing updates

1. Check approval dates: `grep "2024" docs/site-type-mapping.md`
2. Filter by frequency: `grep "Monthly" docs/project-links.md`

### Task: Find projects by provider name

1. Search in docs: `grep -i "PROVIDER_NAME" docs/project-links.md`
2. Check CSV: `grep -i "PROVIDER_NAME" "Rates Quotation Reports.csv"`

## Tips

- Use `-i` flag for case-insensitive searches
- Use `-r` flag for recursive directory searches
- Use `-l` flag to show only filenames
- Use `-A 5` to show 5 lines after match
- Use `-B 5` to show 5 lines before match
- Combine flags: `grep -irl "pattern" .`

## Quick Reference Table

| What to Find | Where to Look | Command |
|--------------|---------------|---------|
| By state | CSV or quick-reference.md | `grep "STATE" "Rates Quotation Reports.csv"` |
| By coverage | quick-reference.md | `grep "Coverage" docs/quick-reference.md` |
| By site type | by-site-type/ directory | `cat docs/by-site-type/TYPE.md` |
| By name | project-links.md | `grep -i "NAME" docs/project-links.md` |
| By approval date | site-type-mapping.md | `grep "2024-" docs/site-type-mapping.md` |
| All metadata | CLAUDE.md files | `cat PROJECT/CLAUDE.md` |

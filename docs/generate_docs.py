#!/usr/bin/env python3
"""
Documentation Generator for Ideon Scraping Projects
Generates comprehensive documentation structure from CSV data.
"""

import csv
from collections import defaultdict
from pathlib import Path

# Base paths
BASE_DIR = Path("/Users/dikson/Work/ideon_scraping/scraping")
CSV_PATH = BASE_DIR / "Rates Quotation Reports.csv"
DOCS_DIR = BASE_DIR / "docs"
SITE_TYPE_DIR = DOCS_DIR / "by-site-type"


def parse_csv() -> list[dict]:
    """Parse the CSV file and return list of project data."""
    projects = []

    with open(CSV_PATH, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip the totals row
            if row['Name'] == 'Totals:':
                continue

            # Clean and normalize the project slug
            project_slug = row['Project Name'].strip()
            if not project_slug or project_slug == '-':
                continue

            projects.append({
                'name': row['Name'].strip(),
                'project_slug': project_slug,
                'frequency': row['FrequencyAllMonthlyQuarterly'].strip(),
                'state': row['State'].strip(),
                'coverage': row['Line of Coverage(s)'].strip(),
                'site_type': row['Site Type'].strip(),
                'approval_status': row['Approval StatusAllApprovedCancelledRate RequestRate Submitted'].strip(),
                'approval_date': row['Approval Date'].strip(),
            })

    return projects


def group_by_site_type(projects: list[dict]) -> dict[str, list[dict]]:
    """Group projects by site type."""
    grouped = defaultdict(list)

    for project in projects:
        site_type = project['site_type'] if project['site_type'] and project['site_type'] != '-' else 'Other'
        grouped[site_type].append(project)

    # Sort each group alphabetically by name
    for site_type in grouped:
        grouped[site_type].sort(key=lambda x: x['name'])

    return dict(grouped)


def create_project_claude_md(project: dict) -> str:
    """Generate CLAUDE.md content for a project."""
    content = f"""# {project['name']}

## Project Metadata

- **Project Name**: {project['name']}
- **Project Slug**: `{project['project_slug']}`
- **State Coverage**: {project['state']}
- **Line of Coverage**: {project['coverage']}
- **Site Type**: {project['site_type']}
- **Approval Status**: {project['approval_status']}
- **Approval Date**: {project['approval_date']}
- **Update Frequency**: {project['frequency']}

---

"""
    return content


def update_or_create_project_docs(projects: list[dict]):
    """Create or update CLAUDE.md files in each project directory."""
    created = 0
    updated = 0
    skipped = 0

    for project in projects:
        project_dir = BASE_DIR / project['project_slug']

        if not project_dir.exists():
            print(f"⚠️  Directory not found: {project['project_slug']}")
            skipped += 1
            continue

        claude_md_path = project_dir / "CLAUDE.md"
        metadata_content = create_project_claude_md(project)

        if claude_md_path.exists():
            # Read existing content
            with open(claude_md_path, encoding='utf-8') as f:
                existing_content = f.read()

            # Check if metadata already exists
            if '## Project Metadata' in existing_content:
                # Replace existing metadata section
                parts = existing_content.split('---', 2)
                if len(parts) >= 2:
                    # Keep content after the first metadata section
                    new_content = metadata_content + '---'.join(parts[2:])
                else:
                    new_content = metadata_content + existing_content
            else:
                # Prepend metadata to existing content
                new_content = metadata_content + existing_content

            with open(claude_md_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            updated += 1
            print(f"✓ Updated: {project['project_slug']}/CLAUDE.md")
        else:
            # Create new file
            with open(claude_md_path, 'w', encoding='utf-8') as f:
                f.write(metadata_content)

            created += 1
            print(f"✓ Created: {project['project_slug']}/CLAUDE.md")

    return created, updated, skipped


def create_site_type_mapping(grouped_projects: dict[str, list[dict]]):
    """Create site-type-mapping.md with grouped projects."""
    content = """# Site Type Mapping

This document organizes all scraping projects by their site type, making it easy to find projects that share similar infrastructure or access patterns.

## Overview

"""

    # Add statistics
    content += "### Statistics\n\n"
    sorted_types = sorted(grouped_projects.items(), key=lambda x: len(x[1]), reverse=True)

    for site_type, projects in sorted_types:
        content += f"- **{site_type}**: {len(projects)} projects\n"

    content += f"\n**Total Projects**: {sum(len(p) for p in grouped_projects.values())}\n\n"
    content += "---\n\n"

    # Add detailed sections for each site type
    for site_type, projects in sorted_types:
        content += f"## {site_type}\n\n"
        content += f"**Count**: {len(projects)} projects\n\n"

        for project in projects:
            content += f"### {project['name']}\n"
            content += f"- **Project**: `{project['project_slug']}`\n"
            content += f"- **States**: {project['state']}\n"
            content += f"- **Coverage**: {project['coverage']}\n"
            content += f"- **Status**: {project['approval_status']}\n"
            content += f"- **Documentation**: [CLAUDE.md](../{project['project_slug']}/CLAUDE.md)\n"
            content += "\n"

        content += "---\n\n"

    with open(DOCS_DIR / "site-type-mapping.md", 'w', encoding='utf-8') as f:
        f.write(content)

    print("✓ Created: docs/site-type-mapping.md")


def create_master_readme(projects: list[dict], grouped_projects: dict[str, list[dict]]):
    """Create master README.md for docs folder."""
    content = """# Ideon Scraping Projects Documentation

Welcome to the comprehensive documentation hub for all Ideon scraping projects. This documentation system provides organized access to metadata, configuration details, and implementation notes for 84+ insurance provider scraping projects.

## Quick Navigation

### Documentation Resources
- [**Site Type Mapping**](./site-type-mapping.md) - Projects organized by infrastructure type
- [**Quick Reference**](./quick-reference.md) - Summary tables and statistics
- [**Search Guide**](./search-guide.md) - How to find and filter projects
- [**Project Links**](./project-links.md) - Complete alphabetical listing

### Browse by Site Type
"""

    # Add links to category pages
    sorted_types = sorted(grouped_projects.items(), key=lambda x: len(x[1]), reverse=True)
    for site_type, site_projects in sorted_types:
        safe_name = site_type.lower().replace(' ', '-').replace('/', '-')
        content += f"- [{site_type}](./by-site-type/{safe_name}.md) ({len(site_projects)} projects)\n"

    content += f"""

## Project Statistics

- **Total Projects**: {len(projects)}
- **Site Types**: {len(grouped_projects)}
- **States Covered**: Multiple (see individual projects)
- **Coverage Types**: Medicare Advantage, Medicaid, ACA, Large Group

## Project Structure

Each project follows a standardized structure:
```
project_name/
├── CLAUDE.md              # Project documentation with metadata
├── index_1.py            # Phase 1: Provider search
├── index_2.py            # Phase 2: Detail extraction
├── index_3.py            # Phase 3: Data mapping
├── config.py             # Project configuration
├── .env                  # Environment variables
└── data/                 # Output directory
```

## Getting Started

1. **Find a project**: Use [Search Guide](./search-guide.md) or browse [Site Type Mapping](./site-type-mapping.md)
2. **Read documentation**: Each project has a CLAUDE.md file with complete metadata
3. **Check configuration**: Review `.env` and `config.py` in the project directory
4. **Run scraper**: Follow instructions in project's CLAUDE.md

## Coverage Types

- **ACA**: Affordable Care Act (marketplace plans)
- **Medicare Advantage**: Medicare Part C plans
- **Medicaid**: State-administered healthcare programs
- **Large Group**: Employer-sponsored insurance plans

## Site Types

Different infrastructure platforms used by insurance providers:
- **Healthsparq**: Provider directory platform
- **Carrier**: Direct carrier websites
- **Anthem**: Anthem-specific infrastructure
- **Sapphire**: Sapphire Digital platform
- **Provider Lenz**: Provider search platform
- **HealthTrioConnect**: Health management platform
- **Werally**: Provider network platform

## Maintenance

This documentation is generated from `Rates Quotation Reports.csv`. To update:
```bash
cd docs
python generate_docs.py
```

## Contributing

When adding or modifying projects:
1. Update the CSV file with project metadata
2. Run the documentation generator
3. Verify CLAUDE.md files are created/updated
4. Commit changes to the repository
"""

    with open(DOCS_DIR / "README.md", 'w', encoding='utf-8') as f:
        f.write(content)

    print("✓ Created: docs/README.md")


def create_quick_reference(projects: list[dict], grouped_projects: dict[str, list[dict]]):
    """Create quick-reference.md with summary tables."""
    content = """# Quick Reference

Fast lookup tables and statistics for all scraping projects.

## By Site Type

| Site Type | Project Count | Examples |
|-----------|---------------|----------|
"""

    sorted_types = sorted(grouped_projects.items(), key=lambda x: len(x[1]), reverse=True)
    for site_type, site_projects in sorted_types:
        examples = ', '.join([p['name'] for p in site_projects[:3]])
        if len(site_projects) > 3:
            examples += f", ... (+{len(site_projects) - 3} more)"
        content += f"| {site_type} | {len(site_projects)} | {examples} |\n"

    content += "\n## By Coverage Type\n\n"

    # Group by coverage
    coverage_groups = defaultdict(list)
    for project in projects:
        coverages = [c.strip() for c in project['coverage'].split(',') if c.strip() and c.strip() != '-']
        for coverage in coverages:
            coverage_groups[coverage].append(project)

    content += "| Coverage Type | Project Count |\n"
    content += "|---------------|---------------|\n"

    for coverage in sorted(coverage_groups.keys(), key=lambda x: len(coverage_groups[x]), reverse=True):
        content += f"| {coverage} | {len(coverage_groups[coverage])} |\n"

    content += "\n## By State Coverage\n\n"

    # Group by state
    state_groups = defaultdict(list)
    for project in projects:
        states = [s.strip() for s in project['state'].replace(' and ', ', ').split(',') if s.strip() and s.strip() != '-']
        for state in states:
            state_groups[state].append(project)

    content += "| State | Project Count |\n"
    content += "|-------|---------------|\n"

    # Show top 20 states
    sorted_states = sorted(state_groups.items(), key=lambda x: len(x[1]), reverse=True)[:20]
    for state, state_projects in sorted_states:
        content += f"| {state} | {len(state_projects)} |\n"

    if len(state_groups) > 20:
        content += f"\n*Showing top 20 of {len(state_groups)} states/regions*\n"

    content += "\n## By Approval Status\n\n"

    status_groups = defaultdict(list)
    for project in projects:
        status = project['approval_status'] if project['approval_status'] else 'Unknown'
        status_groups[status].append(project)

    content += "| Status | Count |\n"
    content += "|--------|-------|\n"

    for status in sorted(status_groups.keys()):
        content += f"| {status} | {len(status_groups[status])} |\n"

    content += "\n## Update Frequency\n\n"

    freq_groups = defaultdict(list)
    for project in projects:
        freq = project['frequency'] if project['frequency'] and project['frequency'] != '-' else 'Not specified'
        freq_groups[freq].append(project)

    content += "| Frequency | Count |\n"
    content += "|-----------|-------|\n"

    for freq in sorted(freq_groups.keys()):
        content += f"| {freq} | {len(freq_groups[freq])} |\n"

    content += f"""

## Summary Statistics

- **Total Projects**: {len(projects)}
- **Unique Site Types**: {len(grouped_projects)}
- **Unique Coverage Types**: {len(coverage_groups)}
- **States/Regions Covered**: {len(state_groups)}
- **Approved Projects**: {len(status_groups.get('Approved', []))}

## Most Common Patterns

### Top 5 States by Project Count
"""

    for i, (state, state_projects) in enumerate(sorted_states[:5], 1):
        content += f"{i}. **{state}**: {len(state_projects)} projects\n"

    content += "\n### Top 5 Coverage Types\n"

    sorted_coverage = sorted(coverage_groups.items(), key=lambda x: len(x[1]), reverse=True)[:5]
    for i, (coverage, cov_projects) in enumerate(sorted_coverage, 1):
        content += f"{i}. **{coverage}**: {len(cov_projects)} projects\n"

    with open(DOCS_DIR / "quick-reference.md", 'w', encoding='utf-8') as f:
        f.write(content)

    print("✓ Created: docs/quick-reference.md")


def create_search_guide(projects: list[dict]):
    """Create search-guide.md with filtering instructions."""
    content = """# Search and Filter Guide

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
grep "2024-12\\|2025" "Rates Quotation Reports.csv"
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
grep -i "bcbs\\|blue cross\\|blue shield" docs/project-links.md
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
"""

    with open(DOCS_DIR / "search-guide.md", 'w', encoding='utf-8') as f:
        f.write(content)

    print("✓ Created: docs/search-guide.md")


def create_category_pages(grouped_projects: dict[str, list[dict]]):
    """Create individual category pages in by-site-type/ directory."""
    for site_type, projects in grouped_projects.items():
        safe_name = site_type.lower().replace(' ', '-').replace('/', '-')

        content = f"""# {site_type} Projects

{len(projects)} projects using {site_type} infrastructure.

## Projects

"""

        for project in projects:
            content += f"""### {project['name']}

**Project Slug**: `{project['project_slug']}`

**Metadata**:
- States: {project['state']}
- Coverage: {project['coverage']}
- Status: {project['approval_status']}
- Approval Date: {project['approval_date']}
- Frequency: {project['frequency']}

**Links**:
- [Project Directory](../../{project['project_slug']}/)
- [CLAUDE.md](../../{project['project_slug']}/CLAUDE.md)

---

"""

        with open(SITE_TYPE_DIR / f"{safe_name}.md", 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✓ Created: docs/by-site-type/{safe_name}.md")


def create_project_links(projects: list[dict]):
    """Create project-links.md with alphabetical listing."""
    content = """# All Projects - Alphabetical

Complete alphabetical listing of all scraping projects with direct links to documentation.

"""

    # Sort projects alphabetically by name
    sorted_projects = sorted(projects, key=lambda x: x['name'])

    # Group by first letter
    current_letter = ''
    for project in sorted_projects:
        first_letter = project['name'][0].upper()

        if first_letter != current_letter:
            current_letter = first_letter
            content += f"\n## {current_letter}\n\n"

        content += f"### {project['name']}\n"
        content += f"- **Slug**: `{project['project_slug']}`\n"
        content += f"- **State**: {project['state']}\n"
        content += f"- **Coverage**: {project['coverage']}\n"
        content += f"- **Site Type**: {project['site_type']}\n"
        content += f"- **Docs**: [CLAUDE.md](../{project['project_slug']}/CLAUDE.md)\n"
        content += "\n"

    with open(DOCS_DIR / "project-links.md", 'w', encoding='utf-8') as f:
        f.write(content)

    print("✓ Created: docs/project-links.md")


def main():
    """Main execution function."""
    print("\n" + "="*60)
    print("Ideon Scraping Projects - Documentation Generator")
    print("="*60 + "\n")

    # Parse CSV
    print("📊 Parsing CSV file...")
    projects = parse_csv()
    print(f"✓ Found {len(projects)} projects\n")

    # Group by site type
    print("📁 Grouping projects by site type...")
    grouped_projects = group_by_site_type(projects)
    print(f"✓ Grouped into {len(grouped_projects)} site types\n")

    # Create/update project CLAUDE.md files
    print("📝 Creating/updating project CLAUDE.md files...")
    created, updated, skipped = update_or_create_project_docs(projects)
    print(f"✓ Created: {created}, Updated: {updated}, Skipped: {skipped}\n")

    # Create documentation files
    print("📚 Creating documentation files...")
    create_site_type_mapping(grouped_projects)
    create_master_readme(projects, grouped_projects)
    create_quick_reference(projects, grouped_projects)
    create_search_guide(projects)
    create_category_pages(grouped_projects)
    create_project_links(projects)

    print("\n" + "="*60)
    print("✅ Documentation generation complete!")
    print("="*60)
    print("\nGenerated files:")
    print("  - docs/README.md")
    print("  - docs/site-type-mapping.md")
    print("  - docs/quick-reference.md")
    print("  - docs/search-guide.md")
    print("  - docs/project-links.md")
    print(f"  - docs/by-site-type/*.md ({len(grouped_projects)} files)")
    print(f"  - {created + updated} project CLAUDE.md files")
    print("\n📖 Start here: docs/README.md\n")


if __name__ == "__main__":
    main()

# Documentation Maintenance Guide

This guide explains how the `docs/` directory is organized, which files are auto-generated, and how to safely extend the documentation set.

## Directory Layout

```
docs/
├── README.md                 # Entry point / navigation hub (manual)
├── MAINTENANCE.md            # This guide (manual)
├── site-type-mapping.md      # Generated from CSV
├── quick-reference.md        # Generated summary table
├── project-links.md          # Generated alphabetical index
├── search-guide.md           # Generated usage notes
├── by-site-type/             # Generated per site-type listings
├── architecture/             # Manual architecture runbooks (e.g., Healthsparq)
├── generate_docs.py          # Generator script for CSV-derived docs
└── templates/                # Markdown templates for common doc types
```

### Generated vs. Manual

| Location | Ownership | Notes |
| --- | --- | --- |
| `site-type-mapping.md`, `quick-reference.md`, `project-links.md`, `search-guide.md` | **Generated** | Created by `generate_docs.py` from `Rates Quotation Reports.csv`. Re-run the script whenever the CSV changes. Avoid manual edits—they will be overwritten. |
| `by-site-type/*.md` | **Generated** | One file per site type. Also managed by `generate_docs.py`; manual edits will be lost on regeneration. |
| `architecture/*.md`, `README.md`, `MAINTENANCE.md`, `templates/` | **Manual** | Curated documentation. Edit directly or add new files as needed. |

## Regenerating CSV-Based Docs

Run the generator whenever metadata changes in `Rates Quotation Reports.csv`:

```bash
cd docs
python3 generate_docs.py
```

The script will:

- Regenerate the aggregated docs listed above.
- Ensure each project directory contains up-to-date metadata in `CLAUDE.md` (existing non-metadata sections are preserved).
- Report any missing project directories.

## Adding Manual Documentation

1. Pick an appropriate location:
   - **Architecture guides** → `docs/architecture/<topic>.md`
   - **Style guides / templates** → `docs/templates/`
   - **One-off references** → create a subfolder if multiple files are expected; otherwise keep at the root with a descriptive name.
2. Update `docs/README.md` with a link to the new resource so it appears in the navigation list.
3. If the doc applies to a specific site type, consider linking it from the relevant generated page (e.g., `docs/by-site-type/healthsparq.md`). Keep the link stable so the generator doesn’t overwrite it; use blockquotes or comments if needed.

### Template Usage

`docs/templates/` contains starter files for common documentation patterns. Copy a template, rename it, then fill out the placeholders.

## Conventions

- Markdown format (`.md`) for all docs.
- Use relative links (`../path/file.md`) so the docs remain portable.
- Keep headings concise; limit depth to three levels (`###`).
- Prefer lowercase filenames with hyphens.
- When adding large code snippets, wrap them in fenced code blocks with an info string (language hint).

## Cross-Referencing Project Docs

- Each scraper directory maintains a `CLAUDE.md` (metadata + run notes) and optionally a `README.md` (deep dive).
- When making architectural updates or runbook changes, update both the project doc and any relevant shared doc under `docs/architecture/`.
- If you add a new site type, update the generator (`generate_docs.py`) to produce the additional listing if required.

## Quality Checklist

- [ ] Run the generator after updating the CSV.
- [ ] Verify new manual docs are linked from `docs/README.md`.
- [ ] Validate relative links by opening the markdown files locally (or via markdown preview).
- [ ] Keep doc filenames unique to avoid confusion between manual and generated content.
- [ ] Review doc changes alongside code updates to ensure instructions match actual behavior.

Maintaining a clear separation between generated and manual content keeps the documentation predictable and easy to extend. Use this guide as a reference before modifying or adding files under `docs/`.

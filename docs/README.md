# Ideon Scraping Projects Documentation

Welcome to the comprehensive documentation hub for all Ideon scraping projects. This documentation system provides organized access to metadata, configuration details, and implementation notes for 84+ insurance provider scraping projects.

## Quick Navigation

### Documentation Resources
- [**Site Type Mapping**](./site-type-mapping.md) - Projects organized by infrastructure type
- [**Quick Reference**](./quick-reference.md) - Summary tables and statistics
- [**Search Guide**](./search-guide.md) - How to find and filter projects
- [**Project Links**](./project-links.md) - Complete alphabetical listing
- [**Healthsparq Architecture**](./architecture/healthsparq.md) - Deep dive into Healthsparq project structure and runbook
- [**Docs Maintenance Guide**](./MAINTENANCE.md) - Ownership, conventions, and regeneration steps

### Browse by Site Type
- [Carrier](./by-site-type/carrier.md) (35 projects)
- [Healthsparq](./by-site-type/healthsparq.md) (24 projects)
- [Sapphire](./by-site-type/sapphire.md) (15 projects)
- [Anthem](./by-site-type/anthem.md) (4 projects)
- [HealthTrioConnect](./by-site-type/healthtrioconnect.md) (2 projects)
- [Werally](./by-site-type/werally.md) (2 projects)
- [Provider Lenz](./by-site-type/provider-lenz.md) (1 projects)


## Project Statistics

- **Total Projects**: 83
- **Site Types**: 7
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

Most reference docs are generated from `Rates Quotation Reports.csv`. To refresh them:
```bash
cd docs
python3 generate_docs.py
```

For doc ownership, templates, and conventions, see [Docs Maintenance Guide](./MAINTENANCE.md).

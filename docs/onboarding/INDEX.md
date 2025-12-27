# Ideon Scraping Documentation Index

> **Complete Documentation Suite for Provider Directory Data Extraction Infrastructure**

---

## Quick Navigation

| I need to... | Go to... |
|--------------|----------|
| Understand the overall system | [ARCHITECTURE.md](#architecture) |
| Learn how pipelines work | [PIPELINE.md](#pipeline) |
| Implement a specific site type | [SITE_TYPES_REFERENCE.md](#site-types) |
| Start developing | [DEVELOPER_GUIDE.md](#developer-guide) |
| Debug an issue | [TROUBLESHOOTING.md](#troubleshooting) |
| Improve the codebase | [IMPROVEMENTS.md](#improvements) |
| Look up terminology | [GLOSSARY.md](#glossary) |
| Review expert feedback | [EXPERT_REVIEW.md](#expert-review) |

---

## Documentation Suite

### Core Documentation

<a name="architecture"></a>
#### [ARCHITECTURE.md](./ARCHITECTURE.md)
**System Architecture Overview**

Comprehensive guide to the infrastructure design, covering:
- System architecture diagrams
- 7 platform types (Carrier, Healthsparq, Sapphire, Anthem, etc.)
- Data flow architecture
- Directory structures
- Output schema specification
- Shared infrastructure (healthsparq-server, output_generator)
- Concurrency models
- Performance characteristics

**Best for:** Understanding the big picture, system design decisions, component relationships.

---

<a name="pipeline"></a>
#### [PIPELINE.md](./PIPELINE.md)
**Pipeline Architecture Deep Dive**

Detailed documentation of the extraction pipeline:
- Phase 0: Setup & ID Discovery
- Phase 1: Discovery/Search
- Phase 2: Detail Extraction
- Phase 3: Normalization
- Pipeline orchestration (run_all.py)
- Deduplication strategies
- Error handling patterns
- QA suite integration
- Performance optimization

**Best for:** Implementing or modifying pipeline phases, understanding data transformation.

---

<a name="site-types"></a>
#### [SITE_TYPES_REFERENCE.md](./SITE_TYPES_REFERENCE.md)
**Site Type Technical Reference**

Platform-specific implementation details:
- Carrier type (35 projects) - Direct REST APIs
- Healthsparq type (24 projects) - Browser automation
- Sapphire type (15 projects) - ProviderFinderOnline
- Anthem type (4 projects) - Wellpoint infrastructure
- HealthTrioConnect (2 projects) - Node.js + Python hybrid
- Werally type (2 projects) - UHC geographic search
- Provider Lenz (1 project) - Anti-bot protected

Includes API endpoints, authentication patterns, and code examples for each.

**Best for:** Creating new scrapers, understanding platform-specific requirements.

---

<a name="developer-guide"></a>
#### [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md)
**Developer Onboarding Guide**

Complete guide for new developers:
- Prerequisites and setup
- Quick start guide
- Project structure deep dive
- Common tasks and workflows
- Creating new scrapers
- Debugging guide
- Best practices
- Testing checklist

**Best for:** New team members, first-time contributors, refresher on workflows.

---

<a name="troubleshooting"></a>
#### [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
**Troubleshooting Guide**

Problem resolution reference:
- Diagnostic flowchart
- Connection issues (timeouts, SSL, server)
- Authentication errors (401, 403)
- Rate limiting (429, anti-bot)
- Data issues (empty output, duplicates)
- Schema validation errors
- Performance issues
- Pipeline recovery
- Log analysis patterns

**Best for:** Debugging failures, resolving common issues, production incident response.

---

<a name="improvements"></a>
#### [IMPROVEMENTS.md](./IMPROVEMENTS.md)
**Code Improvement Recommendations**

Strategic enhancement plan:
- P0: Critical (secret management, logging, checkpoints)
- P1: High (config inheritance, retry patterns, parallelization)
- P2: Medium (metrics, validation, testing)
- P3: Lower (container support, API versioning)
- Implementation roadmap
- Architecture evolution plan

**Best for:** Technical leadership, roadmap planning, infrastructure investment decisions.

---

### Reference Documentation

<a name="glossary"></a>
#### [GLOSSARY.md](./GLOSSARY.md)
**Terminology Reference**

Definitions for:
- Healthcare terms (NPI, provider, network, specialty)
- Insurance coverage types (Medicare, Medicaid, ACA)
- Platform terms (Healthsparq, Sapphire, Werally)
- Technical terms (scraper, pipeline, deduplication)
- API terms (REST, endpoint, pagination)
- Common abbreviations

**Best for:** New team members, non-technical stakeholders, quick lookups.

---

<a name="expert-review"></a>
#### [EXPERT_REVIEW.md](./EXPERT_REVIEW.md)
**Expert Review Summary**

Review by 27 domain experts covering:
- Document-by-document assessments
- Strengths and improvement recommendations
- Cross-document findings
- Consolidated recommendations
- Final quality scores

**Best for:** Understanding documentation quality, identifying improvement priorities.

---

### Existing Documentation

#### [README.md](./README.md)
Project overview and documentation hub.

#### [site-type-mapping.md](./site-type-mapping.md)
Complete project listing organized by site type.

#### [project-links.md](./project-links.md)
Comprehensive project index with links.

#### [quick-reference.md](./quick-reference.md)
Common operations cheatsheet.

#### [search-guide.md](./search-guide.md)
Finding projects and code patterns.

#### [MAINTENANCE.md](./MAINTENANCE.md)
Maintenance and update procedures.

---

## Documentation by Role

### New Developer
1. Start with [GLOSSARY.md](./GLOSSARY.md) for terminology
2. Read [ARCHITECTURE.md](./ARCHITECTURE.md) for system overview
3. Follow [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) for setup
4. Keep [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) handy

### Experienced Developer
1. [PIPELINE.md](./PIPELINE.md) for implementation details
2. [SITE_TYPES_REFERENCE.md](./SITE_TYPES_REFERENCE.md) for platform specifics
3. [IMPROVEMENTS.md](./IMPROVEMENTS.md) for enhancement ideas

### Technical Lead
1. [ARCHITECTURE.md](./ARCHITECTURE.md) for design decisions
2. [IMPROVEMENTS.md](./IMPROVEMENTS.md) for roadmap planning
3. [EXPERT_REVIEW.md](./EXPERT_REVIEW.md) for quality assessment

### Operations/DevOps
1. [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for incident response
2. [PIPELINE.md](./PIPELINE.md) for orchestration details
3. [IMPROVEMENTS.md](./IMPROVEMENTS.md) for monitoring recommendations

---

## Documentation Statistics

| Document | Lines | Words | Last Updated |
|----------|-------|-------|--------------|
| ARCHITECTURE.md | ~800 | ~4,500 | Dec 2024 |
| PIPELINE.md | ~1,100 | ~6,000 | Dec 2024 |
| SITE_TYPES_REFERENCE.md | ~900 | ~5,000 | Dec 2024 |
| DEVELOPER_GUIDE.md | ~700 | ~3,500 | Dec 2024 |
| TROUBLESHOOTING.md | ~800 | ~4,000 | Dec 2024 |
| IMPROVEMENTS.md | ~700 | ~3,500 | Dec 2024 |
| GLOSSARY.md | ~300 | ~1,500 | Dec 2024 |
| EXPERT_REVIEW.md | ~500 | ~3,000 | Dec 2024 |

**Total:** ~5,800 lines, ~31,000 words

---

## Quick Commands

```bash
# View all documentation
ls -la /Users/dikson/Work/ideon_scraping/scraping/docs/

# Search documentation
grep -r "pattern" docs/

# Run a scraper
cd audiobee_bcbs_il && python run_all.py

# Start Healthsparq server
cd healthsparq-server && npm start

# Validate output
python output_generator/type_check.py audiobee_*/
```

---

## Feedback

To suggest improvements to this documentation:
1. Review [EXPERT_REVIEW.md](./EXPERT_REVIEW.md) for existing recommendations
2. Add issues or suggestions following the existing format
3. Update the relevant document
4. Update this index if adding new documents

---

*Documentation Version: 1.0.0 | Last Updated: December 2024*

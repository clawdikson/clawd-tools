# Development Learning Tracker

**Command:** `dev-learn` (or `dl` when symlinked)

Systematically capture, organize, and search technical learnings from daily development work. Perfect for CTOs and senior developers who encounter new technologies, patterns, and solutions frequently but want to build a searchable knowledge base instead of losing insights.

## Core Philosophy

Transform daily development work into systematic learning. Instead of letting valuable insights slip away, capture them immediately and build a searchable knowledge repository that grows with your career.

## Key Features

- **Lightning-fast capture** - `dev-learn add "insight"` in seconds
- **Smart categorization** - 11 development-focused categories
- **Powerful search** - Find learnings by content, category, or tags
- **NST timezone aware** - All timestamps in Newfoundland local time
- **Rich tagging system** - Organize learnings with custom tags
- **Analytics dashboard** - Track learning patterns and trends
- **Daily review** - See today's captured learnings
- **Persistent storage** - JSON-based local storage, maintains history indefinitely

## Perfect for Dikson Because

- **Aligns with "1% better daily"** - Quantifies incremental learning growth
- **Supports CTO role** - Systematically captures technical leadership insights
- **Builds searchable knowledge base** - No more losing valuable insights
- **Zero-friction workflow** - Terminal-native, fits development environment
- **Learning-focused lifestyle** - Supports goal of daily learning and passive knowledge
- **Memory enhancement** - Externalizes and organizes technical insights

## Installation

```bash
# Make system-wide command (optional)
sudo ln -sf /home/azureuser/clawd/tools/dev-learn /usr/local/bin/dl
```

## Quick Start

```bash
# Add your first learning
dev-learn add "React useCallback only recreates function when dependencies change"

# Add with category and tags
dev-learn add "Redis pipelining reduces network roundtrips" --category performance --tags redis,optimization

# Review today's learnings
dev-learn today

# Search for specific topics
dev-learn search "react"

# See learning statistics
dev-learn stats
```

## Commands

### `add` - Capture New Learning
```bash
# Basic capture
dev-learn add "Learning description"

# With category
dev-learn add "TypeScript union types improve type safety" --category language

# With tags
dev-learn add "GraphQL reduces overfetching" --tags graphql,api,performance

# Category + tags
dev-learn add "Docker multi-stage builds reduce image size" --category tool --tags docker,optimization
```

### `list` - View Learnings
```bash
# Recent learnings (default: 10)
dev-learn list

# More results
dev-learn list --limit 20

# Filter by category
dev-learn list --category architecture

# Filter by tag
dev-learn list --tag react

# Filter by date
dev-learn list --date 2026-02-01
```

### `search` - Find Learnings
```bash
# Search content
dev-learn search "typescript"

# Search across content, categories, and tags
dev-learn search "performance"
```

### `today` - Daily Review
```bash
# Show today's learnings
dev-learn today
```

### `stats` - Analytics
```bash
# Learning statistics and trends
dev-learn stats
```

### `categories` - Reference
```bash
# List available categories with descriptions
dev-learn categories
```

## Categories

| Category | Description | Examples |
|----------|-------------|----------|
| **language** | Programming language features, syntax, idioms | TypeScript generics, Python asyncio, Rust ownership |
| **framework** | Framework/library patterns, best practices | React hooks patterns, Express middleware, Vue composition |
| **architecture** | System design insights, patterns, trade-offs | Microservices communication, Database sharding, Event sourcing |
| **tool** | Development tools, utilities, configurations | Docker optimizations, Git workflows, IDE shortcuts |
| **debugging** | Problem-solving techniques, troubleshooting | Memory leak detection, Performance profiling, Error handling |
| **performance** | Optimization techniques, profiling insights | Query optimization, Caching strategies, Load balancing |
| **security** | Security best practices, vulnerabilities | Input validation, JWT security, HTTPS configurations |
| **workflow** | Development process improvements | CI/CD optimizations, Code review processes, Testing strategies |
| **pattern** | Design patterns, coding patterns | Observer pattern, Factory pattern, Command pattern |
| **concept** | General programming concepts, algorithms | Big O notation, Functional programming, Data structures |
| **other** | Miscellaneous learnings | Industry insights, Career advice, Technology trends |

## Tags

Use tags to create cross-cutting organization:

```bash
# Technology tags
--tags react,vue,angular          # Frontend frameworks
--tags node,python,rust           # Languages/runtimes  
--tags mongodb,postgresql,redis   # Databases
--tags aws,docker,kubernetes      # Infrastructure

# Concept tags
--tags performance,security,testing
--tags api,database,frontend,backend
--tags patterns,architecture,debugging

# Project tags
--tags beena,audiobee,personal
--tags migration,refactoring,feature
```

## Usage Patterns

### Daily Capture Workflow
```bash
# During development, capture insights immediately
dev-learn add "NextJS getServerSideProps runs on every request" --category framework --tags nextjs,ssr

# End of day review
dev-learn today
```

### Weekly Review
```bash
# Review recent learnings
dev-learn list --limit 20

# Check learning statistics
dev-learn stats

# Search for specific topics you're working on
dev-learn search "authentication"
```

### Research and Reference
```bash
# Before starting new project, search existing learnings
dev-learn search "react authentication"
dev-learn search "database migration"

# When encountering similar problems
dev-learn search "performance"
dev-learn list --category debugging
```

## Data Storage

- **Location:** `~/.dev-learn/`
- **Learnings:** `~/.dev-learn/learnings.json`
- **Config:** `~/.dev-learn/config.json`
- **Format:** Human-readable JSON
- **Backup:** Standard file backup (no database dependencies)

## Sample Learning Entry

```json
{
  "id": "lj8x9k2m1",
  "learning": "React useCallback only recreates function when dependencies change, preventing unnecessary child re-renders",
  "category": "framework",
  "tags": ["react", "optimization", "hooks"],
  "timestamp": "2026-02-02 03:30:45",
  "date": "2026-02-02"
}
```

## Integration Ideas

### Morning Routine
```bash
# Add to HEARTBEAT.md for periodic review
echo "dev-learn today" >> /home/azureuser/clawd/HEARTBEAT.md
```

### Git Hooks
```bash
# Post-commit hook to capture learnings
#!/bin/sh
echo "What did you learn from this commit?"
read learning
if [ -n "$learning" ]; then
  dev-learn add "$learning" --category workflow --tags git,commit
fi
```

### Alfred/Raycast Integration
```bash
# Quick learning capture from anywhere
dev-learn add "{query}"
```

## Why This Tool Matters

As a CTO, Dikson encounters dozens of technical insights weekly:
- New API patterns while building features
- Performance optimizations during debugging
- Architecture decisions during system design
- Tool configurations during development setup
- Framework patterns while learning new technologies

Without systematic capture, these insights are lost. This tool transforms daily development work into accumulating wisdom, creating a personal technical knowledge base that compounds over time.

**Before:** "I remember learning something about React optimization, but can't recall the details"

**After:** `dev-learn search "react optimization"` → Instant access to specific insights with context and timestamps

## Impact Potential

- **Accelerated learning** - Making insights visible encourages more deliberate learning
- **Knowledge retention** - External memory prevents losing valuable discoveries  
- **Pattern recognition** - Search reveals connections across different learnings
- **Team knowledge sharing** - Export learnings for team documentation
- **Career growth** - Documented expertise demonstrates continuous learning
- **Problem solving** - Searchable solutions for recurring challenges

Perfect complement to Dikson's productivity system, supporting his goal of daily learning while building a career-spanning knowledge repository.
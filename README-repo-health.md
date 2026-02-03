# Repository Health Scanner

**Command:** `repo-health` / `rh`  
**Purpose:** Comprehensive health analysis for git repositories  
**Perfect for:** CTOs, tech leads, developers managing multiple projects

## Overview

Repository Health Scanner analyzes git repositories across 7 key dimensions to provide actionable insights into code quality, project maintenance, and technical debt. It's designed specifically for developers like Dikson who manage multiple repositories and need quick visibility into project health.

## Why This Tool Matters

**For CTOs & Tech Leads:**
- **Multi-repo visibility** — Scan all projects instantly instead of checking each manually
- **Technical debt detection** — Identify repositories that need attention before they become problems
- **Team best practices** — Ensure consistent standards across all projects
- **Quick health checks** — Get objective data for project prioritization and resource allocation

**For Dikson's Workflow:**
- **Perfect for SCRAP project** — Monitor 114+ scraper repositories for consistency
- **Monorepo health** — Track main Audio Bee repository health over time
- **IRAP project monitoring** — Ensure project quality standards are maintained
- **Morning routine integration** — Quick scan of active projects during standup preparation

## Health Dimensions

The scanner evaluates repositories across 7 critical areas:

### 1. 🔄 Git Status
- **What it checks:** Working directory cleanliness, staged/unstaged changes
- **Why it matters:** Clean repos indicate good development hygiene
- **Scoring:** 10 points for clean, deductions for excessive uncommitted work

### 2. 📅 Recent Activity  
- **What it checks:** Last commit timing, commit frequency (7d/30d)
- **Why it matters:** Active repositories are healthier, abandoned repos accumulate debt
- **Scoring:** Recent activity = full points, months old = warnings, year+ = fail

### 3. 🌿 Branch Health
- **What it checks:** Current branch, local branch count, sync status
- **Why it matters:** Too many branches indicate poor cleanup, wrong branch = workflow issues
- **Scoring:** Main branches good, excessive local branches trigger warnings

### 4. 🔍 Code Quality
- **What it checks:** Linting tools, test scripts, large files, code quality configs
- **Why it matters:** Quality tools prevent bugs, large files slow repos
- **Scoring:** Presence of ESLint/tests/configs = points, issues = deductions

### 5. 📚 Documentation
- **What it checks:** README presence, CHANGELOG, CONTRIBUTING, docs folder
- **Why it matters:** Good docs improve maintainability and team onboarding
- **Scoring:** README required, additional docs boost score

### 6. 📦 Dependencies
- **What it checks:** Package.json health, dependency count, lock files
- **Why it matters:** Lock files ensure reproducible builds, too many deps = complexity
- **Scoring:** Lock files required, excessive dependencies = warnings

### 7. 🔒 Security
- **What it checks:** Sensitive files in git, .gitignore presence
- **Why it matters:** Accidentally committed secrets = security vulnerabilities
- **Scoring:** Tracked sensitive files = fail, missing .gitignore = warning

## Installation & Setup

```bash
# Make available system-wide
sudo ln -sf /home/azureuser/clawd/tools/repo-health /usr/local/bin/repo-health

# Create short alias
sudo ln -sf /usr/local/bin/repo-health /usr/local/bin/rh
```

## Usage Examples

### Basic Usage
```bash
# Scan current repository
repo-health

# Scan specific repository
repo-health /path/to/project

# Scan multiple repositories
repo-health ~/projects/repo1 ~/projects/repo2

# Use short alias
rh .
```

### CTO Workflow Examples
```bash
# Morning health check - scan all active projects
rh ~/beena-monorepo ~/irap-project ~/scraping-base

# SCRAP project audit - check scraper health
rh ~/bitbucket/audiobee_*

# Pre-release check - ensure main projects are healthy
rh ~/beena-monorepo ~/irap-project

# Team review preparation - scan all team repositories
find ~/projects -name ".git" -type d | sed 's/.git//' | xargs rh
```

### Output Interpretation

```
🏥 Repository Health Scanner
Scanning 1 repository...

🔍 Scanning: beena-monorepo
Path: /home/azureuser/beena-monorepo

✅ Git Status: Clean working directory
⚠️ Recent Activity: Last commit 3 days ago (2 commits in 7d, 8 in 30d)
✅ Branch Health: On 'main' (3 local branches)
⚠️ Code Quality: No test scripts found
✅ Documentation: Good coverage (README, CHANGELOG, CONTRIBUTING)
✅ Dependencies: 45 deps, lock file present
✅ Security: No obvious security issues

📊 HEALTH SCORE: 82% (Grade B)
Status: Healthy | Issues: 0 | Warnings: 2 | Scan time: 156ms
```

### Health Grades

- **A (90-100%)** — Excellent, production ready
- **B (80-89%)** — Good, minor improvements needed  
- **C (70-79%)** — Fair, some issues to address
- **D (60-69%)** — Poor, significant issues
- **F (<60%)** — Failing, major problems

## Integration Ideas

### Morning Routine
Add to your daily startup script:
```bash
echo "🏥 Repository Health Check"
rh ~/beena-monorepo ~/irap-project ~/scraping-base
```

### Git Hooks
Pre-push hook to check repository health:
```bash
#!/bin/bash
score=$(rh . | grep "HEALTH SCORE" | grep -o '[0-9]\+%' | grep -o '[0-9]\+')
if [ "$score" -lt 70 ]; then
  echo "⚠️ Repository health score too low ($score%). Consider improving before push."
  exit 1
fi
```

### Cron Job Monitoring
Weekly health reports:
```bash
# Add to crontab: 0 9 * * 1 /usr/local/bin/weekly-health-report
#!/bin/bash
echo "Weekly Repository Health Report - $(date)" > /tmp/health-report.txt
rh ~/projects/* >> /tmp/health-report.txt
# Send report via email or Slack
```

## Advanced Usage

### Filtering Results
```bash
# Only show repositories with issues
rh ~/projects/* | grep -A 5 -B 5 "Grade [CDF]"

# Count healthy vs unhealthy repositories
rh ~/projects/* | grep "HEALTH SCORE" | wc -l
```

### Performance Monitoring
The tool includes scan time metrics for performance tracking:
```bash
# Time multiple scans to track performance
for repo in ~/projects/*; do
  echo "Scanning $repo..."
  time rh "$repo" > /dev/null
done
```

## Interpreting Results

### Common Issues & Solutions

**Git Status Issues:**
- Many uncommitted changes → Review and commit pending work
- Large staging area → Break changes into smaller commits

**Activity Warnings:**
- No recent commits → Check if repository is still active
- Too frequent commits → Consider if commits are too granular

**Code Quality Problems:**
- No linting → Add ESLint/Prettier configuration
- No tests → Add basic test setup (Jest/Mocha)
- Large files → Use Git LFS for binary assets

**Documentation Issues:**
- Missing README → Create basic project documentation
- No CHANGELOG → Start tracking version changes

**Security Problems:**
- Sensitive files tracked → Remove and add to .gitignore
- Missing .gitignore → Create appropriate ignore rules

## Why Perfect for Dikson

**Aligns with 1% Better Daily:**
- **Quantified improvement** — Health scores track project quality over time
- **Proactive maintenance** — Catch issues before they become problems  
- **Consistent standards** — Ensure all projects follow best practices

**Supports CTO Role:**
- **Portfolio visibility** — Understand health across all projects instantly
- **Team leadership** — Set and maintain consistent quality standards
- **Resource planning** — Identify which projects need attention/refactoring
- **Client confidence** — Demonstrate professional development practices

**Fits Development Workflow:**
- **Terminal native** — No context switching to web dashboards
- **Fast execution** — Scan multiple repos in seconds
- **Actionable output** — Clear problems with obvious solutions
- **Automation ready** — Easy to integrate into existing scripts/workflows

## File Structure

```
tools/
├── repo-health              # Main executable
└── README-repo-health.md    # This documentation

# After system installation:
/usr/local/bin/
├── repo-health -> /home/azureuser/clawd/tools/repo-health
└── rh -> repo-health        # Short alias
```

## Technical Notes

- **Language:** Node.js (JavaScript)
- **Dependencies:** None (uses built-in modules only)
- **Platform:** Linux/macOS (uses shell commands)
- **Performance:** ~100-200ms per repository
- **Output:** ANSI colors + Unicode icons for rich terminal display

## Roadmap

Potential future enhancements:
- **JSON output** for integration with other tools
- **Custom check configuration** via .repo-health.json
- **Historical tracking** to monitor health trends over time
- **Team dashboard** with aggregated metrics
- **Integration with ClickUp** for automatic task creation on health issues

---

*Built during overnight coding session for productive CTO workflow optimization.*
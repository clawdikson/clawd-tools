# Daily Standup Generator

A CLI tool that automatically generates daily standup summaries from your git commits.

## What it does

- Scans git repositories for commits in the last 24 hours (configurable)
- Categorizes commits by type (features, fixes, improvements, etc.)
- Generates a clean markdown summary perfect for daily check-ins
- Supports multiple repositories and various output formats

## Installation

The script is already in `/home/azureuser/clawd/tools/standup-gen` and executable.

Add to your shell profile for global access:
```bash
echo 'export PATH="$PATH:/home/azureuser/clawd/tools"' >> ~/.bashrc
source ~/.bashrc
```

## Usage

```bash
# Basic usage (current directory)
standup-gen

# Look back 48 hours instead of 24
standup-gen --hours 48

# Check multiple repositories
standup-gen --repos /path/to/monorepo,/path/to/frontend

# Save to file
standup-gen --save

# Copy to clipboard
standup-gen --copy

# Combined options
standup-gen --hours 48 --repos /home/azureuser/beena-monorepo --save
```

## Example Output

```markdown
## Daily Standup - 1/29/2025

**Yesterday I worked on:**
- monorepo: 5 commits

**Features:**
- Add user authentication flow (a1b2c3d)
- Implement email validation (e4f5g6h)

**Fixes:**
- Fix memory leak in worker process (i7j8k9l)
- Resolve CORS issue for API endpoints (m1n2o3p)

**Improvements:**
- Refactor database connection pooling (q4r5s6t)

**Today I plan to:**
- [Add your priorities here]

**Blockers:**
- None
```

## Why this helps

- **Saves time**: No more manually reviewing git logs
- **Improves communication**: Clean, categorized summaries
- **Shows impact**: Quantifies your daily output
- **Consistency**: Standard format for all standups
- **Context switching**: Quick mental recap of yesterday's work

## Workflow Integration

1. **Morning routine**: Run `standup-gen` first thing
2. **Add priorities**: Fill in "Today I plan to" section
3. **Share/save**: Copy to Slack, save to notes, or use in meetings
4. **Multiple repos**: Use with monorepo and any side projects

Perfect for Dikson's focus on productivity and clear communication.
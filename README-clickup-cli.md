# ClickUp CLI (`cu`) 

**Zero-friction task management from terminal**

Streamline your ClickUp workflow without leaving the command line. Perfect for developers who live in terminal but need quick task management.

## Why This Matters

- **Context switching kills productivity** - stay in terminal instead of opening web apps
- **Quick capture prevents lost tasks** - `cu add "fix bug"` in 2 seconds vs opening browser, finding project, creating task
- **Daily overview builds awareness** - see overdue items and today's priorities at a glance
- **CTO workflow optimization** - manage technical tasks and team items from development environment

## Installation

```bash
# Already executable, just create system-wide alias
sudo ln -sf /home/azureuser/clawd/tools/clickup-cli /usr/local/bin/cu
```

## Setup (One-time)

```bash
cu setup
```
- Get API token from: https://app.clickup.com/settings/apps
- Token is stored securely in `.clickup-config.json`
- Auto-detects your workspace (9017490901) 

## Core Commands

### Quick Task Creation
```bash
# Basic task
cu add "Review API documentation"

# With description
cu add "Fix payment timeout" "Investigate 30s timeout in Stripe integration"

# With priority (urgent/high/normal/low)
cu add "Deploy hotfix" "Critical memory leak patch" urgent
```

### List & Filter Tasks
```bash
# Open tasks (default)
cu list

# Overdue tasks (past due date)
cu list overdue

# Today's tasks (due today)
cu list today

# Aliases work too
cu ls overdue
```

### Task Management
```bash
# Mark task complete
cu done 123456

# Daily overview (today + overdue)
cu daily

# Show all commands
cu help
```

## Daily Workflow Integration

### Morning Routine
```bash
cu daily  # See what's due today and what's overdue
```

### During Development
```bash
# Quick task capture without losing focus
cu add "TODO: Refactor auth middleware"
cu add "BUG: Email validation regex" "Allows invalid domains" high
```

### Evening Review
```bash
cu list today    # See what's left
cu done 123456   # Mark completed items
```

## Smart Features

- **NST timezone aware** - all dates/times in Newfoundland time
- **Priority indicators** - visual priority markers in output
- **Rich task details** - status, due dates, assignees in list view
- **Auto-completion detection** - finds appropriate "done" status for your workspace
- **Error handling** - clear error messages with action suggestions

## Configuration

Config stored in: `/home/azureuser/clawd/tools/.clickup-config.json`

```json
{
  "token": "pk_...",
  "workspace": "9017490901",
  "defaultList": null,
  "timezone": "America/St_Johns"
}
```

## Perfect for Dikson's Workflow

- **Aligns with "1% better daily"** - reduces friction for task management
- **Supports CTO responsibilities** - quick technical task creation and tracking
- **Terminal-native** - fits existing development workflow
- **ClickUp integration** - works with existing workspace and projects
- **NST timezone** - all dates/times in local Newfoundland time
- **Context-aware priorities** - urgent/high for critical items, normal for routine tasks

## Usage Patterns

### Project Work
```bash
# During code review
cu add "Fix type definitions in user service" "Missing types for UserPreferences"

# After finding bugs
cu add "Memory leak in data sync" "Process memory grows 10MB/hour" urgent

# Planning features
cu add "Design API rate limiting" "Research Redis vs in-memory solutions"
```

### Team Management
```bash
# Delegate tasks
cu add "Review Ayush's PR #234" "Frontend changes for email templates"

# Follow-ups
cu add "Schedule IRAP milestone review" "Prepare Q1 progress report"
```

### Daily Tracking
```bash
# Morning planning
cu daily | head -20  # Top priority items

# End of day
cu ls today | grep -c "Open"  # Count remaining tasks
```

## Troubleshooting

### Token Issues
- Regenerate token in ClickUp settings if API calls fail
- Run `cu setup` again to reconfigure

### No Lists Found
- Ensure you have at least one Space and List in your workspace
- Check permissions on API token (needs task read/write access)

### Timezone Issues
- All dates displayed in NST/NDT (Newfoundland time)
- Due date comparisons account for local timezone

## API Limits
- ClickUp API rate limit: 100 requests/minute
- CLI caches configuration to minimize API calls
- Batch operations where possible

## Security
- API token stored locally in config file (not committed to git)
- No sensitive data transmitted beyond ClickUp API requirements
- Uses HTTPS for all API communication
# Time Tracker CLI (`tt`)

Lightning-fast time tracking for productivity analysis and project management.

## Installation

```bash
# Create system-wide command
sudo ln -sf /home/azureuser/clawd/tools/time-tracker /usr/local/bin/tt

# Test installation
tt --help
```

## Quick Start

```bash
# Start tracking development work
tt start development "API optimization work"

# Check current session
tt status

# Stop session with notes
tt stop "Reduced API response time by 40%"

# Quick log for completed work
tt log meetings 30 "Team standup"

# Today's summary
tt today
```

## Core Features

### **Session Management**
- **Real-time tracking** - Start/stop sessions with live duration
- **Quick logging** - Retroactively log completed work sessions
- **Smart validation** - Prevents overlapping sessions, validates projects

### **Project Organization**
- **Pre-configured projects** - Development, meetings, planning, admin, general
- **Custom projects** - Add unlimited project categories with colors
- **Visual distinction** - Color-coded output for instant recognition

### **Time Analytics**
- **Period analysis** - Daily, weekly, monthly time breakdowns
- **Project distribution** - See where time actually goes with percentages
- **Session patterns** - Average session length and productivity insights
- **NST timezone** - All timestamps in Newfoundland local time

### **Reporting & Search**
- **Recent activity** - List sessions from last N days
- **Summary views** - Today and weekly overviews
- **Project filtering** - Focus on specific work categories
- **Historical data** - All sessions preserved with searchable history

## Commands Reference

### Session Tracking
```bash
# Start new session
tt start <project> [description]
tt start development "Bug fixing in payment service"

# Stop current session
tt stop [notes]
tt stop "Fixed timeout issue, deployed to staging"

# Check what's currently running
tt status

# Retroactively log completed work
tt log <project> <minutes> [description]
tt log meetings 45 "Quarterly planning session"
```

### Time Analysis
```bash
# Today's breakdown
tt today

# Weekly summary (default)
tt stats
tt stats week

# Monthly analysis
tt stats month

# Custom period
tt list 14        # Last 14 days of sessions
```

### Project Management
```bash
# List all available projects
tt projects

# Add new project
tt project add research "R&D Work" purple
tt project add client "Client Calls" green
```

## Default Projects

- **`general`** - General work tasks
- **`meetings`** - All meeting types
- **`development`** - Coding, debugging, technical work
- **`planning`** - Strategy, architecture, project planning  
- **`admin`** - Administrative tasks, emails, paperwork

## Usage Patterns

### **Daily CTO Workflow**
```bash
# Morning planning session
tt start planning "Daily priorities and team check-ins"

# Switch to development work
tt stop "Reviewed sprint goals"
tt start development "Architecture review for microservices"

# Meeting time
tt stop "Documented service boundaries"
tt start meetings "1-on-1 with senior engineers"

# End of day summary
tt today
```

### **Project Time Analysis**
```bash
# See where time went this week
tt stats week

# Focus on recent development sessions
tt list 5

# Track specific project categories
tt stats month    # Shows all projects with percentages
```

### **Quick Session Logging**
```bash
# Log work that already happened
tt log development 90 "Fixed critical security vulnerability"
tt log meetings 60 "Architecture decision meeting"
tt log admin 20 "Code review and PR feedback"
```

## Data Storage

- **Location**: `~/.time-tracking/`
- **Format**: JSON (human-readable, backup-friendly)
- **Files**:
  - `sessions.json` - All tracking sessions with timestamps
  - `projects.json` - Project definitions and colors

## Terminal Integration

- **Color-coded output** - Projects have distinct colors for visual parsing
- **Duration formatting** - Smart time display (45m, 2h 30m)
- **NST timestamps** - All times shown in Newfoundland timezone
- **Zero context switching** - Stay in terminal for all time tracking

## Why Use Time Tracker?

### **For CTOs & Engineering Leaders**
- **Visibility into time allocation** - Understand balance between coding, meetings, strategic work
- **Objective productivity data** - Replace gut feelings with actual time metrics
- **Meeting overhead analysis** - Quantify time spent in meetings vs hands-on work
- **Project time estimation** - Historical data improves future planning accuracy

### **For Personal Productivity**
- **1% better daily principle** - Make time visible to optimize it
- **Habit formation** - Consistent tracking reveals productivity patterns
- **Focus improvement** - Active tracking increases awareness of time usage
- **Work-life balance** - See actual vs perceived time allocation

### **Terminal-Native Workflow**
- **2-second session start** vs multi-step app interfaces
- **No context switching** - Stay in development environment
- **Keyboard-driven** - Perfect for developers and power users
- **Lightweight** - Minimal resource usage, instant response

## Example Output

```
🎯 Started tracking:
   Development - API optimization work
   Started: 2026-02-09 09:15

📊 Time statistics for this week:
Total time: 32h 45m
Sessions: 47

Time by project:
● Development
  18h 30m (56.5%) • 25 sessions

● Meetings  
  9h 15m (28.2%) • 12 sessions

● Planning & Strategy
  3h 45m (11.5%) • 6 sessions

● Administrative
  1h 15m (3.8%) • 4 sessions

Average session: 41m
```

## Integration Ideas

- **Daily reviews** - `tt today` in morning routine
- **Weekly analysis** - `tt stats week` for time allocation optimization
- **Project reporting** - Export data for time-based billing or team reports
- **Productivity experiments** - Track impact of different working patterns
- **Meeting overhead monitoring** - Set targets for meeting vs hands-on time ratios

Transform time from invisible resource into visible, optimizable data that supports better decision-making and productivity improvement.
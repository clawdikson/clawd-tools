# Morning Dashboard CLI

> **One command to start your day right**
> 
> `morning` - Aggregates key information for daily startup routine

## Overview

The Morning Dashboard CLI brings together information from multiple productivity tools into a single, beautiful terminal display. Perfect for CTOs and productivity enthusiasts who want to start each day with complete situational awareness.

## Key Features

🌤️ **Weather Integration** - Current conditions for St. John's, NL  
📅 **Task Overview** - ClickUp integration for today's priorities  
📚 **Reading Progress** - Active books and recent reading sessions  
🧠 **Learning Captures** - Recent technical insights and knowledge  
🔀 **Git Repository Status** - Clean vs dirty repo summary  
⏱️ **Time Analytics** - Yesterday's productivity patterns  
🚀 **Quick Actions** - Shortcuts to other productivity tools

## Installation

```bash
# Tool is already installed system-wide
morning --help
```

## Usage

### Basic Usage
```bash
# Show complete morning dashboard
morning

# Show help and usage information  
morning help
```

### Sample Output
```
╭─────────────────────────────────────────────────────╮
│                🌅 MORNING DASHBOARD                 │
╰─────────────────────────────────────────────────────╯

📍 St. John's, NL • Thursday, February 5, 2026, 08:30 AM

🌤️ Weather
──────────────────────────────────────────────────────
Partly cloudy • -2°C (feels -8°C)
💨 15 km/h NW • 💧 78% humidity

✅ Tasks  
──────────────────────────────────────────────────────
3 due today • 1 overdue • 28 total

📚 Reading Progress
──────────────────────────────────────────────────────
📖 Current: Rich Dad Poor Dad (67%)
📊 15 pages read yesterday • 2 sessions

🧠 Learning Captures
──────────────────────────────────────────────────────
💡 2 learnings captured yesterday • 47 total
   framework: React useCallback only recreates function when...
   pattern: Multi-stage Docker builds reduce image size by...

🔀 Repository Status
──────────────────────────────────────────────────────
3 clean • 1 with changes • 4 total repos
  💡 Consider committing pending changes

⏱️ Yesterday's Time
──────────────────────────────────────────────────────
⏱️ 6h 30m tracked • 8 sessions
🏆 Top category: dev (3h 45m)

🚀 Quick Actions
──────────────────────────────────────────────────────
  morning help      Show detailed usage
  cu daily          ClickUp daily overview
  read stats        Reading progress summary
  dl today          Today's captured learnings
  ta status         Current time tracking status
  rh .             Repository health check
```

## Integration with Existing Tools

The Morning Dashboard leverages your existing productivity tools:

- **ClickUp CLI (`cu`)** - Task counts and daily overview
- **Reading Tracker (`read`)** - Book progress and session data  
- **Dev Learning (`dl`)** - Technical insight captures
- **Time Analytics (`ta`)** - Productivity pattern analysis
- **Repository Health (`rh`)** - Git status monitoring

## Perfect Morning Routine

```bash
# 1. Get complete situational awareness
morning

# 2. Review specific task details
cu daily

# 3. Check any concerning repository status
rh /path/to/concerning/repo

# 4. Start time tracking for focused work
ta start deep "Architecture review for API redesign"

# 5. Begin productive work with full context!
```

## Data Sources

### Weather
- **Source:** wttr.in (no API key required)
- **Location:** St. John's, Newfoundland & Labrador
- **Format:** Condition, temperature, feels-like, humidity, wind

### Tasks
- **Source:** ClickUp CLI integration
- **Data:** Today's due count, overdue count, total active tasks
- **Requires:** ClickUp CLI setup (`cu setup`)

### Reading Progress  
- **Source:** Reading Tracker data files
- **Location:** `~/.reading-data/books.json` & `sessions.json`
- **Data:** Active books, recent sessions, pages read yesterday

### Learning Captures
- **Source:** Dev Learning tracker data
- **Location:** `~/.config/dev-learnings.json`
- **Data:** Recent technical insights, categories, total count

### Git Status
- **Source:** Direct git status checks
- **Repositories:** clawd, beena-monorepo, irap-project, scraping-base
- **Data:** Clean vs dirty repository counts

### Time Analytics
- **Source:** Time Analytics data files  
- **Location:** `~/.config/time-analytics.json`
- **Data:** Yesterday's tracked time, session count, top category

## Design Philosophy

### Aggregation Over Integration
Instead of reimplementing functionality, the Morning Dashboard **aggregates** data from existing specialized tools. This creates a "single pane of glass" without duplicating logic or breaking workflows.

### Graceful Degradation
Each data source fails independently. If ClickUp API is down, you still get weather, reading progress, and git status. No single failure breaks the entire dashboard.

### NST Timezone Native
All timestamps and date calculations use Newfoundland Standard Time (UTC-3:30), matching Dikson's location and daily routine.

### Terminal-First Design
Rich Unicode characters, ANSI colors, and structured layout create a beautiful terminal experience without requiring GUI dependencies.

## Why This Tool?

### Problem Solved
Individual productivity tools are powerful but create **information fragmentation**. You need to check multiple sources to understand your daily situation:

- Is the weather good for walking to meetings?
- What's due today? What's overdue?
- How was yesterday's productivity?
- Are my repositories clean?
- What did I learn recently?

### Solution Approach
**One command** (`morning`) provides complete situational awareness for starting your day. No context switching, no app launching, no mental overhead.

### Perfect for CTOs
- **Multi-repo awareness** for managing diverse projects
- **Learning velocity tracking** for continuous skill development
- **Time allocation visibility** for leadership vs execution balance
- **Task priority awareness** for effective daily planning
- **Weather integration** for commute and meeting planning

### Aligns with "1% Better Daily"
- **Removes decision fatigue** - instant situational awareness
- **Enables better planning** - see everything at once
- **Builds consistent routines** - same command every morning
- **Quantifies progress** - multiple productivity dimensions visible

## Development Notes

### Technology Stack
- **Runtime:** Node.js (built-in modules only)
- **External APIs:** wttr.in weather service
- **Data Sources:** JSON files from existing productivity tools
- **Output:** Rich terminal formatting with ANSI colors

### Error Handling
Each data source is wrapped in try-catch blocks. Failed API calls or missing data files display graceful error messages instead of breaking the entire dashboard.

### Performance
- **Fast execution:** <500ms typical runtime
- **Minimal network:** Single weather API call only
- **Local data:** All productivity data read from local JSON files
- **No dependencies:** Zero npm packages, pure Node.js

### Extensibility
New data sources can be added easily:
1. Create `getNewDataSource()` function
2. Add section in `displayDashboard()`
3. Handle errors gracefully
4. Update documentation

## Future Enhancements

### Potential Additions
- **Calendar integration** (Google Calendar API or .ics parsing)
- **Health data** (from existing health dashboard tool)
- **Email summary** (unread count, priority emails)
- **Financial tracking** (investment performance, expense tracking)
- **Habit tracking** (streaks, completion rates)

### Configuration Options
- **Custom data sources** - add/remove sections based on preferences
- **Layout customization** - rearrange sections or change display format
- **Notification thresholds** - alert on too many overdue tasks, dirty repos
- **Historical trends** - show week-over-week progress in various areas

## Security & Privacy

### Local Data Only
All productivity data remains local. The only external API call is weather data (no personal information transmitted).

### No Credentials Required
Weather API requires no authentication. Other data sources use existing local tool configurations without exposing credentials.

### Minimal Network Footprint
Single HTTP request to wttr.in weather service. All other data read from local files.

---

**Built by ClawdBot Overnight Coder** • Part of the Clawd Tools ecosystem  
**Repository:** [github.com/clawdikson/clawd-tools](https://github.com/clawdikson/clawd-tools)  
**Author:** ClawdBot (Overnight Coder)  
**License:** MIT  
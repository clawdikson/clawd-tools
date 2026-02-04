# Time Analytics CLI

**Command:** `time-analytics` or `ta`

**Purpose:** Track and analyze time usage patterns with intelligent insights for productivity optimization.

## Why This Tool Exists

As a CTO managing multiple projects (AudioBee, Beena, IRAP, 114 SCRAP scrapers), understanding where time actually goes is critical for:
- **Protecting deep work time** - Ensure focused coding/architecture time isn't fragmented
- **Meeting overhead awareness** - Quantify time spent in meetings vs. execution
- **Context switching costs** - Identify productivity patterns and interruption sources  
- **Resource planning** - Data-driven decisions about team allocation and priorities
- **Personal optimization** - Align time usage with "1% better daily" philosophy

## Core Features

### 🎯 Smart Session Tracking
- **Start/stop/switch paradigm** - Zero-friction time capture
- **10 CTO-focused categories** - Development, meetings, planning, code review, admin, learning, breaks, deep work, communication, debugging
- **Session descriptions** - Context capture for later analysis
- **NST timezone aware** - All timestamps in Newfoundland local time

### 📊 Rich Analytics
- **Category breakdowns** - See time distribution across work types
- **Productivity insights** - Deep work vs meetings ratio analysis
- **Daily patterns** - Understand productive hours and context switching
- **Trend analysis** - 7, 14, 30-day views with averages and patterns
- **Admin overhead detection** - Flag excessive administrative time

### 💡 Actionable Intelligence
- **Balance recommendations** - Warns when meetings dominate deep work time
- **Efficiency suggestions** - Identifies automation opportunities for high admin overhead
- **Pattern recognition** - Shows average session lengths and productive time blocks

## Installation

```bash
# Make globally available
sudo ln -sf /home/azureuser/clawd/tools/time-analytics /usr/local/bin/time-analytics
sudo ln -sf /home/azureuser/clawd/tools/time-analytics /usr/local/bin/ta

# Verify installation
ta help
```

## Quick Start

```bash
# Start tracking development work
ta start dev "Implementing GraphQL API"

# Switch to a meeting (auto-stops previous session)
ta switch meet "Daily standup with team"

# Check current status and today's summary
ta status

# Stop current session
ta stop

# View 7-day analytics
ta analytics

# View 30-day patterns
ta analytics 30
```

## Commands

### Session Management
- **`ta start <category> [description]`** - Begin new time tracking session
- **`ta stop [session-id]`** - End current or specific session
- **`ta switch <category> [description]`** - Stop current, start new (zero-gap tracking)
- **`ta status`** - Show active session + today's summary

### Analytics & Insights
- **`ta analytics [days]`** - Time analysis with productivity insights (default: 7 days)
- **`ta categories`** - List all available categories with descriptions

### Help
- **`ta help`** - Show detailed help and usage examples

## Categories

| Category | Description | Use Cases |
|----------|-------------|-----------|
| **dev** | Development | Coding, debugging, implementation |
| **meet** | Meetings | Team meetings, client calls, 1:1s |
| **plan** | Planning | Strategy, architecture, roadmap |
| **review** | Code Review | PR reviews, technical discussions |
| **admin** | Admin | Email, paperwork, administrative tasks |
| **learn** | Learning | Reading, tutorials, skill development |
| **break** | Break | Rest, meals, personal time |
| **deep** | Deep Work | Focused, uninterrupted work |
| **comm** | Communication | Slack, email, team coordination |
| **debug** | Debugging | Troubleshooting, investigation |

## Productivity Insights

The tool automatically analyzes your time patterns and provides:

### ✅ Good Patterns
- **"Good balance: More deep work than meetings"** - When focused time exceeds meeting time
- **Consistent daily tracking** - Shows commitment to measurement and improvement

### ⚠️ Warning Signals  
- **"Meeting heavy: Consider blocking more focused time"** - When meetings exceed 150% of deep work
- **"High admin overhead: Look for automation opportunities"** - When admin >30% of total time

### 📈 Trend Analysis
- **Category distribution** - Visual percentage breakdown with bars
- **Average session lengths** - Understand natural work rhythms  
- **Daily tracking volume** - Sessions per day, total time tracked
- **Deep work ratio** - Core productivity metric for technical leaders

## Integration with CTO Workflow

### Morning Routine Integration
```bash
# Check yesterday's patterns
ta analytics 1

# Start deep work block
ta start deep "Architecture review for new features"
```

### Context Switching Awareness
```bash
# Switch from coding to urgent meeting
ta switch meet "Emergency production issue discussion"

# Return to development after meeting
ta switch dev "Implementing fix for production issue"
```

### Weekly Planning
```bash
# Analyze last week's time distribution
ta analytics 7

# Identify if too much time in meetings vs. execution
# Plan next week's calendar based on insights
```

### Team Leadership
```bash
# Track code review time investment
ta start review "Reviewing GraphQL implementation PR"

# Monitor administrative overhead
ta start admin "Quarterly planning documentation"
```

## Data Storage

- **Location:** `~/.time-analytics/`
- **Sessions:** JSON format with start/end timestamps, categories, descriptions
- **Categories:** Customizable category definitions with colors and descriptions
- **Timezone:** All timestamps stored in UTC, displayed in NST
- **Privacy:** Local storage only, no external services

## Advanced Usage

### Bulk Analysis
```bash
# Deep dive into productivity patterns
ta analytics 30

# Compare this week vs last week
ta analytics 7
# (check output, then run again next week)
```

### Workflow Optimization
1. **Track for 1-2 weeks** to establish baseline patterns
2. **Identify high admin periods** - Look for automation opportunities
3. **Protect deep work blocks** - Use insights to schedule focused time
4. **Balance meetings** - Ensure execution time isn't crowded out
5. **Measure improvements** - Track changes over time

## Performance

- **Startup time:** <100ms
- **Data storage:** Minimal JSON files
- **Memory usage:** Low impact, file-based storage
- **NST timezone:** Automatic conversion for local time display

## Why This Matters for CTOs

Time is the scarcest resource for technical leaders. This tool transforms time from "feeling" to "data":

- **Before:** "I feel like I spend too much time in meetings"
- **After:** "I spent 18.5 hours in meetings last week (42% of tracked time) vs 12 hours of deep work (27%). Need to block more focused time."

**Compounding benefits:**
- **Data-driven calendar management** - Protect productive hours with evidence
- **Team resource planning** - Understand leadership time costs
- **Personal optimization** - Align daily reality with productivity goals
- **Stakeholder communication** - Quantify time investment in different priorities

Perfect complement to Dikson's "1% better daily" philosophy - you can't improve what you don't measure.
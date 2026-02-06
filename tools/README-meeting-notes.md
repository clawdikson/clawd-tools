# Meeting Notes Manager (mn)

Zero-friction meeting capture and organization designed for productivity-focused CTOs and tech leaders.

## Why This Tool Exists

**Problem**: Context switching between terminal/IDE and note-taking apps breaks flow state during technical discussions. Traditional meeting tools are heavy, slow, and don't integrate with developer workflows.

**Solution**: Terminal-native meeting management that captures insights instantly without leaving your development environment.

## Perfect For

- **CTOs and Tech Leaders** - Quick capture during technical discussions
- **Daily Standups** - Structured notes with action item tracking  
- **Architecture Reviews** - Searchable technical decision history
- **1-on-1s** - Consistent format with follow-up tracking
- **Sprint Planning** - Action items linked to meeting context

## Installation

```bash
# Make system-wide command
sudo ln -sf /home/azureuser/clawd/tools/meeting-notes /usr/local/bin/mn

# Test installation
mn help
```

## Quick Start

```bash
# Start new meeting (interactive mode)
mn new
# Type: "Sprint Planning"
# Add notes line by line
# Press Ctrl+D when done

# Quick meeting creation
mn new "Daily Standup"

# Add notes to existing meeting
mn add abc123 "API performance improved 40%"
mn add abc123 "Memory usage stable after optimization"

# Add action items
mn action abc123 "John to update API docs by Friday"
mn action abc123 "Review monitoring alerts setup"

# Daily workflow
mn list today          # See today's meetings
mn actions              # Check pending action items
mn search "API"         # Find API-related discussions
```

## Core Commands

### Meeting Management
```bash
mn new [title]          # Create new meeting
mn list [filter]        # List meetings (today/week/month/all)  
mn show <meeting-id>    # Show full meeting details
mn export <meeting-id>  # Export to markdown file
```

### Content Capture  
```bash
mn add <meeting-id> <note>      # Add note to meeting
mn action <meeting-id> <item>   # Add action item
mn complete <action-id>         # Mark action complete
```

### Discovery & Analysis
```bash
mn search <query>       # Search all meeting content
mn actions              # Show all pending action items
mn stats                # Meeting and productivity statistics
```

## Real-World Usage Patterns

### Daily Standup Flow
```bash
# Monday morning
mn new "Daily Standup - Feb 6"
mn add def456 "Weekend deploy successful - 99.9% uptime"
mn add def456 "Performance metrics show 15% improvement"
mn action def456 "Review new monitoring dashboard with team"

# Later in the day
mn complete xyz789      # Mark action complete
```

### Architecture Review
```bash
mn new "API Rate Limiting Design Review"
mn add ghi789 "Current: In-memory counter, resets on restart"
mn add ghi789 "Proposal: Redis-based sliding window"
mn add ghi789 "Concerns: Redis dependency, network latency"
mn action ghi789 "Sarah to benchmark Redis vs in-memory performance"
mn action ghi789 "Create POC implementation by next week"

# Search later
mn search "rate limiting"  # Finds this discussion
```

### Follow-up Management
```bash
# Check what needs attention
mn actions

# See recent meetings
mn list week

# Export for sharing
mn export abc123        # Creates markdown file
```

## Data Storage

**Location**: `~/.meeting-notes/`
- `meetings.json` - Meeting data and metadata
- `notes/` - Individual meeting note files (future expansion)

**Format**: Human-readable JSON for easy backup and migration

**Timezone**: All timestamps in NST (Newfoundland Standard Time) for Dikson's local context

## Key Features

### 🚀 **Zero Friction Capture**
- 2-second note capture: `mn add abc123 "insight"`
- No app switching, stays in terminal workflow
- Interactive or quick command-line modes

### 🔍 **Powerful Search**  
- Full-text search across all meetings, notes, and action items
- Highlighted results with meeting context
- Find technical decisions months later

### ✅ **Action Item Tracking**
- Add action items with meeting context
- Track completion status and dates  
- Overview of all pending actions across meetings

### 📊 **Analytics & Insights**
- Meeting frequency and patterns
- Note capture trends
- Action item completion rates
- Productivity metrics over time

### 🎯 **NST Timezone Native**
- All timestamps in Newfoundland local time
- Perfect for Dikson's location and schedule
- Consistent time handling across all features

### 📝 **Export & Sharing**
- Export meetings to clean markdown format
- Shareable format for team communication
- Preserves timestamps and action item status

## Command Aliases

**Common shortcuts:**
- `create`, `start` → `new`
- `ls` → `list`  
- `find` → `search`
- `todo`, `task` → `action`
- `done` → `complete`

## Integration Ideas

**Git Integration**: Link commits to meeting discussions
```bash
# After meeting about API refactor
git commit -m "Implement rate limiting (per meeting abc123)"
```

**Calendar Integration**: Auto-create meetings from calendar events
**Slack Integration**: Share action items with team channels
**Daily Reports**: Generate summary emails of completed actions

## Why This Improves Productivity

### **Before**: 
- Context switching to note apps breaks flow
- Meeting insights scattered across tools  
- Action items forgotten or lost
- No searchable meeting history
- Heavy meeting software for simple capture

### **After**:
- Instant capture without leaving terminal
- Searchable knowledge base of all meetings  
- Systematic action item tracking
- Historical context for technical decisions
- Lightweight, fast, integrated workflow

### **Compound Benefits**:
- **Memory augmentation** - External storage of meeting insights
- **Pattern recognition** - Search reveals recurring themes/issues
- **Accountability** - Action item tracking drives completion  
- **Team alignment** - Shareable meeting exports
- **Knowledge preservation** - Technical decisions preserved over time

## Perfect Fit for Dikson

- **CTO Role**: Technical leadership discussions require systematic capture
- **1% Better Daily**: Quantifiable meeting productivity improvements
- **Terminal Workflow**: Integrates seamlessly with development environment  
- **NST Timezone**: All timestamps match local time automatically
- **Productivity Focus**: Eliminates friction, maximizes capture efficiency
- **Learning Mindset**: Builds searchable repository of insights and decisions

This tool transforms meetings from time-lost to knowledge-gained, with zero workflow disruption.
# Meeting Notes CLI

Lightning-fast meeting note capture and organization from the terminal. Designed for CTOs and team leads who need systematic meeting management without context switching.

## Why This Tool?

**Before:** Scattered notes across apps, lost action items, forgotten decisions  
**After:** Systematic capture, searchable history, tracked follow-ups

Perfect for leadership roles requiring:
- Multiple daily meetings with different teams
- Action item accountability and tracking
- Decision documentation and recall
- Meeting pattern analysis and improvement

## Quick Start

```bash
# Create a new meeting
meeting-notes create "Weekly Team Standup" --type standup --attendees "Alice,Bob,Carol" --duration 15

# Add notes during the meeting
meeting-notes add abc123 "Yesterday" "Completed user auth API"
meeting-notes add abc123 "Today" "Starting payment integration"
meeting-notes add abc123 "Blockers" "Need staging environment access"

# Capture action items and decisions
meeting-notes action abc123 "Set up staging access" --assignee "DevOps Team" --due "2026-02-10"
meeting-notes decision abc123 "Approved move to TypeScript for new features"

# Review and follow up
meeting-notes list
meeting-notes actions
meeting-notes search "payment"
```

## Features

### 📝 **Smart Templates**
Pre-configured sections for common meeting types:
- **1-on-1:** Previous actions, current projects, blockers, goals, feedback
- **Standup:** Yesterday, today, blockers, notes
- **Planning:** Objectives, requirements, timeline, resources, risks, decisions
- **Retrospective:** What went well, improvements, action items, experiments
- **General:** Agenda, discussion, decisions, action items, next steps

### 🎯 **Action Item Tracking**
- Assign ownership and due dates
- Track completion status
- View all open items across meetings
- Automatic timestamping in NST

### 📊 **Decision Documentation**
- Capture decisions with timestamps
- Search decision history across all meetings
- Perfect for architecture and product decisions

### 🔍 **Powerful Search**
- Search across all meeting content
- Filter by attendees, meeting type, or keywords
- Find past decisions and action items instantly

### 📅 **Meeting Management**
- NST timezone-aware timestamps
- Attendee tracking
- Duration recording
- Meeting type categorization
- Tag-based organization

## Installation

```bash
# Make globally available
sudo ln -sf /home/azureuser/clawd/tools/meeting-notes /usr/local/bin/mn

# Test installation
mn help
```

## Usage Patterns

### Daily Standup Workflow
```bash
# Create recurring standup
mn create "Daily Standup - Feb 8" --type standup --attendees "TeamLead,Dev1,Dev2,QA" --duration 15

# During meeting - rapid capture
mn add abc123 "Yesterday" "Fixed login bug, deployed hotfix"
mn add abc123 "Today" "Code review sprint tasks, start user dashboard"
mn add abc123 "Blockers" "Waiting for design assets"

# Capture actions
mn action abc123 "Follow up with design team" --assignee "TeamLead" --due "2026-02-09"
```

### 1-on-1 Meeting Workflow
```bash
# Weekly 1-on-1
mn create "1-on-1 with Sarah" --type 1-on-1 --attendees "Sarah Chen" --duration 30

# Structured conversation
mn add def456 "Previous Action Items" "Career development plan - in progress"
mn add def456 "Current Projects" "Leading mobile app redesign, 60% complete"
mn add def456 "Blockers" "Need Android developer for native features"
mn add def456 "Goals" "Complete mobile project by end of month"
mn add def456 "Feedback" "Great leadership on cross-team collaboration"

# Follow-up actions
mn action def456 "Schedule mobile dev interviews" --assignee "Sarah" --due "2026-02-15"
mn decision def456 "Approved Sarah for tech lead promotion track"
```

### Planning Session Workflow
```bash
# Sprint planning
mn create "Q1 Sprint Planning" --type planning --attendees "ProductLead,TechLead,Designer" --duration 120

# Capture planning details
mn add ghi789 "Objectives" "Complete user onboarding flow redesign"
mn add ghi789 "Requirements" "Mobile-first, accessibility compliant, A/B testable"
mn add ghi789 "Timeline" "2 week sprint, delivery by Feb 22"
mn add ghi789 "Resources" "2 frontend devs, 1 backend dev, UX designer"
mn add ghi789 "Risks" "New auth system integration complexity"

# Document decisions
mn decision ghi789 "Use React Native for mobile implementation"
mn decision ghi789 "Implement feature flags for gradual rollout"

# Set action items
mn action ghi789 "Create detailed user stories" --assignee "ProductLead" --due "2026-02-10"
mn action ghi789 "Design system component audit" --assignee "Designer" --due "2026-02-12"
```

## Power User Commands

### Meeting History & Analytics
```bash
# Recent meetings with filtering
mn list 20 --filter "1-on-1"
mn list 10 --filter "planning"

# Search across all meetings
mn search "authentication"
mn search "performance"
mn search "Sarah"

# Action item management
mn actions                          # All open action items
mn search "action:John"             # John's action items
mn search "due:2026-02"             # Items due in February
```

### Meeting Follow-up
```bash
# Show full meeting details
mn show abc123

# Export meeting notes (copy/paste ready)
mn show abc123 | pbcopy

# Find related meetings
mn search "mobile app"
mn list --filter "team standup"
```

## Data Storage

**Location:** `~/.meeting-notes/`
- `meetings.json` - All meeting data
- `templates.json` - Meeting templates (customizable)

**Format:** Human-readable JSON for easy backup/migration

## Integration Ideas

**Future enhancements:**
- Export action items to ClickUp: `mn export-actions --clickup`
- Calendar integration: `mn upcoming` (show today's meetings)
- Slack summaries: `mn slack-summary abc123`
- Meeting analytics: `mn stats` (patterns, frequency, action item completion)

## Perfect For

✅ **CTOs and Engineering Leaders** - Multiple team meetings daily  
✅ **Product Managers** - Decision tracking across product discussions  
✅ **Team Leads** - 1-on-1s with direct reports  
✅ **Project Managers** - Action item accountability  
✅ **Anyone with meeting overload** - Systematic organization without tool switching

## Why Terminal-Based?

- **Zero context switching** - stays in development environment
- **Faster than any web app** - 2-second note capture vs 30+ second browser workflow
- **Searchable history** - grep-like power across all meeting content
- **Scriptable** - integrate with other CLI tools and workflows
- **Always available** - works over SSH, in terminal multiplexers, anywhere

Transform meeting chaos into systematic knowledge capture that actually gets used.
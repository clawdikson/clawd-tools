# 📚 Reading Progress Tracker

**Transform reading from sporadic activity into a powerful daily habit.**

## Why This Tool Exists

Dikson is actively working to read more books and build consistent reading habits. He just finished "Atomic Habits" and is currently reading "Rich Dad Poor Dad" — but tracking progress manually is friction that kills momentum.

This tool eliminates that friction by making reading sessions visible, measurable, and rewarding.

## Perfect For

- **Habit builders** who want quantified reading progress
- **Busy professionals** who need efficient session tracking  
- **Learning-focused people** who value insights capture
- **1% better daily philosophy** — small consistent sessions compound

## Core Features

### 📖 Book Management
```bash
# Add books with optional page count
read add "Atomic Habits" "James Clear" 320
read add "Rich Dad Poor Dad" "Robert Kiyosaki" 336

# View your reading list with progress
read list
```

### ⏱️ Session Tracking
```bash
# Real-time session (start when you begin reading)
read start <book-id>
# ... read for 30 minutes ...
read end <session-id> --pages 15 --notes "Key insight about compound interest"

# Quick logging (for past sessions)
read quick <book-id> --pages 20 --duration 45 --notes "Chapter on assets vs liabilities"
```

### 📊 Progress Analytics
```bash
# Overall reading stats
read stats

# Specific book progress
read stats <book-id>
```

### 💡 Insight Capture
Every session can capture insights immediately while they're fresh in memory. These build into a searchable knowledge base over time.

## Example Workflow

### Initial Setup
```bash
# Add current books
read add "Rich Dad Poor Dad" "Robert Kiyosaki" 336
read add "The Lean Startup" "Eric Ries" 336

# See your library
read list
```

### Daily Reading Session
```bash
# Start session
read start abc123

# ... read for 25 minutes ...

# End with progress and insight
read end def456 --pages 12 --notes "Cash flow quadrant: E-S-B-I framework for understanding income sources"
```

### Quick Logging (Retroactive)
```bash
# Log yesterday's session you forgot to track
read quick abc123 --pages 18 --duration 35 --notes "Rich people buy assets, poor people buy liabilities"
```

### Review Progress
```bash
# Check overall stats
read stats

# Focus on specific book
read stats abc123
```

## Data Organization

All data stored in `/home/azureuser/clawd/tools/.reading-data/`:
- `books.json` - Library and progress
- `sessions.json` - Reading session history

**Timezone-aware:** All timestamps use NST (Dikson's timezone).

## Integration Ideas

### With Memory System
```bash
# Capture insights to daily memory
echo "$(date): Reading insight from Rich Dad Poor Dad: $(read stats abc123 | grep -A3 'Recent insights')" >> memory/$(date +%Y-%m-%d).md
```

### With Productivity System
- Use 25-minute reading sessions as Pomodoro blocks
- Track reading streaks alongside other habits
- Schedule reading sessions in calendar

### With ClickUp
- Create reading tasks in ClickUp with progress updates
- Use insights as input for strategic thinking tasks

## Success Metrics

The tool tracks what matters for habit formation:
- **Consistency:** Sessions per week/month
- **Volume:** Pages read over time  
- **Efficiency:** Pages per hour reading speed
- **Insight density:** Notes captured per session
- **Completion:** Books finished vs. started

## Why It Works

1. **Zero friction capture** - Start/stop takes 5 seconds
2. **Immediate feedback** - See progress instantly
3. **Insight preservation** - Capture learning while fresh
4. **Progress visibility** - Charts momentum over time
5. **Habit reinforcement** - Consistent tracking builds the routine

## Advanced Usage

### Batch Import Historical Data
```bash
# If you want to backfill data from other tracking systems
read quick book-id --pages X --duration Y --notes "insight"
```

### Weekly Review
```bash
# See weekly progress
read stats | grep "Total time"
read stats | grep "Recent sessions"
```

### Goal Setting
Use stats to set realistic targets:
- "Read 30 minutes daily" = ~210 minutes/week
- "Finish 1 book monthly" = Track pages/day needed
- "Capture 1 insight per session" = Review insights count

Perfect alignment with Dikson's growth mindset: **measure what matters, improve incrementally, build systems over goals.**
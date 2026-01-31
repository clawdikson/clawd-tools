# Quick Note (`qn`) - Instant Thought Capture

A lightning-fast CLI tool for capturing ideas, thoughts, and notes without breaking your flow. Perfect for busy CTOs who need to quickly log insights throughout the day.

## 🚀 Quick Start

```bash
# Capture a thought instantly
qn "Remember to update the API documentation"

# Add tags for better organization  
qn -t meeting,action "Follow up with team about deployment timeline"

# Search your notes
qn -s "deployment"

# See recent notes
qn -l

# Get statistics
qn --stats
```

## 📁 File Structure

Notes are organized in `/home/azureuser/clawd/memory/quick-notes/`:
- `YYYY-MM-DD.md` - Daily note files
- `all-notes.md` - Master searchable file (auto-generated)

## 🏷️ Features

### Context-Aware Capture
- **Auto-timestamps** with NST timezone
- **Auto-context detection** based on current directory:
  - `[WORK]` when in beena/monorepo directories
  - `[PERSONAL]` when in clawd directory
  - `[GENERAL]` for other locations

### Smart Organization
- **Daily files** keep notes organized by date
- **Master file** enables fast searching across all notes
- **Tags** for categorization (`-t tag1,tag2`)

### Quick Retrieval
- **Search** across all notes (`-s "keyword"`)
- **List recent** notes (`-l [count]`)
- **Stats** to track note-taking habits

## 📋 Usage Examples

### Basic Note Taking
```bash
qn "Need to refactor the authentication module"
qn "Great insight from the team meeting about user onboarding"
qn "Remember to check server logs for that API timeout issue"
```

### Tagged Notes
```bash
qn -t idea,product "What if we added voice commands to Beena?"
qn -t bug,urgent "Memory leak in the background sync process"
qn -t meeting,follow-up "Send technical spec to Ayush by Friday"
```

### Search & Review
```bash
qn -s "API"           # Find all notes about APIs
qn -s "meeting"       # Find meeting-related notes
qn -l 5              # Show last 5 notes
qn --stats           # See note-taking patterns
```

## 🎯 Why This Matters

### For Dikson's Workflow
- **Capture without context switching** - No need to open ClickUp or other apps
- **Timestamped record** of insights and decisions
- **Searchable knowledge base** that grows over time
- **Tags align with ClickUp** organization (can migrate important notes later)

### Productivity Benefits
- **Reduced mental load** - externalize thoughts instantly
- **Better meeting follow-up** - tag action items for easy retrieval
- **Decision tracking** - see thought evolution over time
- **Quick reference** during standups or planning

## 🔄 Integration Potential

The tool is designed to be standalone but extensible:

```bash
# Future: Auto-sync tagged notes to ClickUp
qn -t task "Review Q1 roadmap priorities" --sync-clickup

# Future: Integration with daily standup generator
standup-gen --include-quick-notes

# Current: Manual review and migration
qn -s "task" | grep -v "^$" > /tmp/action-items.md
```

## 📊 File Format

Each note entry follows this format:
```markdown
## 2026-01-30 15:45:32 NST #tag1 #tag2
[CONTEXT] Note content here

```

This makes notes:
- **Human readable** in any markdown editor
- **Easily parsed** by other tools
- **Searchable** with standard text tools
- **Portable** - just markdown files

## 🔧 Advanced Usage

### Bulk Operations
```bash
# Find all action items from last week
qn -s "action" | head -20

# Export notes with specific tag
grep -A1 "#meeting" ~/.clawd/memory/quick-notes/all-notes.md

# Count notes per day
ls ~/.clawd/memory/quick-notes/*.md | wc -l
```

### Custom Context
The tool detects context from your current directory. Work in your project directories to get automatic `[WORK]` tagging.

## 🎉 Perfect For

- **Capturing insights** during coding sessions
- **Meeting follow-ups** without leaving the terminal  
- **Building a searchable knowledge base** of decisions
- **Quick task capture** before formal ClickUp entry
- **Thought logging** during deep work blocks

---

**Installation**: Already installed as `qn` command system-wide.  
**Location**: `/home/azureuser/clawd/tools/quick-note`  
**Data**: `/home/azureuser/clawd/memory/quick-notes/`
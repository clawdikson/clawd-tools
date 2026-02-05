# Search Debugging Knowledge Base

Search the debugging knowledge base for relevant past fixes and solutions.

## Usage
`/search-debugging <query>`

## Examples
- `/search-debugging NPI matching issues`
- `/search-debugging 403 blocking healthsparq`
- `/search-debugging missing providers devoted health`
- `/search-debugging false drops carrier`

## Implementation

```python
import json
import os
from pathlib import Path

def search_debugging_kb(query):
    """Search the debugging knowledge base for relevant entries"""
    
    # Path to the knowledge base
    kb_path = Path("docs/debugging")
    index_path = kb_path / "index.json"
    
    if not index_path.exists():
        return "❌ Debugging knowledge base not found. Run sync first."
    
    # Load index
    with open(index_path) as f:
        index = json.load(f)
    
    query_lower = query.lower()
    matching_entries = []
    
    # Search logic
    for entry in index['entries']:
        score = 0
        reasons = []
        
        # Match in error type (high weight)
        if any(word in entry['error_type'].lower() for word in query_lower.split()):
            score += 10
            reasons.append("error type match")
        
        # Match in tags (medium weight)
        for tag in entry['tags']:
            if any(word in tag for word in query_lower.split()):
                score += 5
                reasons.append(f"tag: {tag}")
        
        # Match in organization (medium weight)
        if any(word in entry['organization'].lower() for word in query_lower.split()):
            score += 5
            reasons.append("organization match")
        
        # Match in site type (low weight)
        if any(word in entry['site_type'] for word in query_lower.split()):
            score += 2
            reasons.append("site type match")
        
        if score > 0:
            matching_entries.append((entry, score, reasons))
    
    # Sort by relevance score
    matching_entries.sort(key=lambda x: x[1], reverse=True)
    
    if not matching_entries:
        return f"🔍 No matches found for '{query}'\n\nTry searching for:\n- Error types: 'NPI', 'blocking', 'false drops'\n- Site types: 'healthsparq', 'carrier', 'sapphire'\n- Organizations: specific org names\n- Technologies: 'proxy', 'algolia', 'autoqa'"
    
    # Format results
    result = f"🎯 Found {len(matching_entries)} debugging solution(s) for '{query}':\n\n"
    
    # Show top 5 matches
    for entry, score, reasons in matching_entries[:5]:
        file_path = kb_path / entry['path']
        
        result += f"## {entry['error_type']} ({entry['date']})\n"
        result += f"**Site:** {entry['site_type']} → {entry['organization']}\n"
        result += f"**Match reasons:** {', '.join(reasons)}\n"
        result += f"**Tags:** {', '.join(entry['tags'])}\n\n"
        
        # Read the actual content for key details
        if file_path.exists():
            with open(file_path) as f:
                content = f.read()
                
            # Extract key sections
            sections = {}
            current_section = None
            current_content = []
            
            for line in content.split('\n'):
                if line.startswith('# ') and not line.startswith('---'):
                    if current_section:
                        sections[current_section] = '\n'.join(current_content).strip()
                    current_section = line.strip('# ').strip()
                    current_content = []
                elif current_section:
                    current_content.append(line)
            
            if current_section:
                sections[current_section] = '\n'.join(current_content).strip()
            
            # Show condensed fix
            if 'Fix' in sections:
                fix = sections['Fix'][:200] + "..." if len(sections['Fix']) > 200 else sections['Fix']
                result += f"**Fix:** {fix}\n"
            
            if 'Key Takeaway' in sections:
                result += f"**Key Takeaway:** {sections['Key Takeaway']}\n"
                
            result += f"📄 Full details: `{entry['path']}`\n\n"
        else:
            result += f"⚠️ File not found: {entry['path']}\n\n"
    
    # Show summary patterns if multiple matches
    if len(matching_entries) > 1:
        result += "## 🔄 Common Patterns\n"
        
        # Analyze tags across matches
        all_tags = []
        for entry, _, _ in matching_entries:
            all_tags.extend(entry['tags'])
        
        tag_counts = {}
        for tag in all_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        common_tags = [(tag, count) for tag, count in tag_counts.items() if count > 1]
        common_tags.sort(key=lambda x: x[1], reverse=True)
        
        if common_tags:
            result += "**Recurring issues:** " + ", ".join([f"{tag} ({count}x)" for tag, count in common_tags[:5]]) + "\n"
        
        # Date pattern
        dates = [entry['date'] for entry, _, _ in matching_entries]
        result += f"**Time range:** {min(dates)} to {max(dates)}\n"
    
    return result

# Execute the search
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(search_debugging_kb(query))
    else:
        print("Usage: python search-debugging.py <search query>")
```

## Command Execution

When invoked with `/search-debugging <query>`, this command will:

1. **Load the index** — Read `docs/debugging/index.json` for fast lookup
2. **Score matches** — Rank entries by relevance to the search query
3. **Extract key info** — Show condensed fixes and takeaways
4. **Identify patterns** — Highlight common tags and time ranges
5. **Provide file paths** — Direct links to full debugging entries

The search considers:
- **Error types** (highest weight) — Direct problem matches
- **Tags** (medium weight) — Topic and technique matches  
- **Organization** (medium weight) — Site-specific issues
- **Site type** (low weight) — Platform-level patterns

This command helps developers quickly find relevant solutions without manually browsing the entire knowledge base.
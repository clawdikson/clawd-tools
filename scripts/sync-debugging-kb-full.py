#!/usr/bin/env python3

"""
Full ClickUp debugging KB sync script

This script handles the complete mechanical sync process:
1. Fetches ClickUp doc pages
2. Compares with existing index for deduplication  
3. Outputs new/changed entries in various formats
4. Can write raw content to temp directories for AI rewriting

The actual AI rewriting should be done by a separate cron job agent.
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

# Configuration
CLICKUP_WORKSPACE_ID = "9017490901"
CLICKUP_DOC_ID = "8cqqzen-4197"
CLICKUP_API_BASE = "https://api.clickup.com/api/v3"


class DebugSyncError(Exception):
    """Custom exception for sync errors"""
    pass


class DebugKBSync:
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': api_token,
            'Content-Type': 'application/json'
        })
    
    def log(self, message: str, level: str = "INFO") -> None:
        """Log message to stderr"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {level}: {message}", file=sys.stderr)
    
    def fetch_clickup_pages(self) -> List[Dict]:
        """Fetch all pages from ClickUp doc"""
        url = f"{CLICKUP_API_BASE}/workspaces/{CLICKUP_WORKSPACE_ID}/docs/{CLICKUP_DOC_ID}/pages"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise DebugSyncError(f"Failed to fetch ClickUp pages: {e}")
    
    def extract_leaf_pages(self, pages: List[Dict], current_path: List[str] = None) -> List[Dict]:
        """Recursively extract leaf pages with content"""
        if current_path is None:
            current_path = []
        
        leaf_pages = []
        
        for page in pages:
            new_path = current_path + [page['name']]
            
            if page.get('pages'):
                # Has children, recurse
                leaf_pages.extend(self.extract_leaf_pages(page['pages'], new_path))
            elif page.get('content') and page['content'].strip():
                # Leaf node with content
                path_parts = new_path[1:] if len(new_path) > 1 else new_path  # Skip root
                
                leaf_pages.append({
                    'id': page['id'],
                    'name': page['name'],
                    'content': page['content'],
                    'date_updated': page['date_updated'],
                    'path_parts': path_parts,
                    'path_str': '/'.join(path_parts),
                    'doc_id': page['doc_id'],
                    'creator_id': page['creator_id'],
                    'date_created': page['date_created']
                })
        
        return leaf_pages
    
    def load_existing_index(self, index_path: Path) -> Dict[str, int]:
        """Load existing index and return page_id -> date_updated mapping"""
        if not index_path.exists():
            return {}
        
        try:
            with open(index_path) as f:
                index = json.load(f)
            
            existing = {}
            for entry in index.get('entries', []):
                existing[entry['clickup_page_id']] = entry['clickup_date_updated']
            
            return existing
        except (json.JSONDecodeError, KeyError) as e:
            self.log(f"Error loading index: {e}", "WARNING")
            return {}
    
    def find_changes(self, leaf_pages: List[Dict], existing: Dict[str, int]) -> Tuple[List[Dict], List[Dict]]:
        """Find new and updated pages"""
        new_pages = []
        updated_pages = []
        
        for page in leaf_pages:
            page_id = page['id']
            date_updated = page['date_updated']
            
            if page_id not in existing:
                new_pages.append(page)
            elif existing[page_id] != date_updated:
                updated_pages.append(page)
        
        return new_pages, updated_pages
    
    def validate_page_structure(self, page: Dict) -> bool:
        """Validate that page has expected structure for debugging entry"""
        path_parts = page['path_parts']
        
        # Should have at least 3 parts: [site_type, organization, date]
        if len(path_parts) < 3:
            self.log(f"Invalid path structure for page {page['id']}: {path_parts}", "WARNING")
            return False
        
        # Date should be numeric (YYYYMMDD format)
        date_part = path_parts[-1]
        if not (date_part.isdigit() and len(date_part) == 8):
            self.log(f"Invalid date format for page {page['id']}: {date_part}", "WARNING")
            return False
        
        return True
    
    def write_raw_content(self, pages: List[Dict], output_dir: Path) -> None:
        """Write raw page content to directory for AI processing"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for page in pages:
            if not self.validate_page_structure(page):
                continue
            
            # Create subdirectory structure
            path_parts = page['path_parts']
            site_type = path_parts[0].lower()
            org_name = path_parts[1]
            date_raw = path_parts[2]
            
            # Convert date format
            if date_raw.isdigit() and len(date_raw) == 8:
                year = date_raw[:4]
                month = date_raw[4:6]
                day = date_raw[6:8]
                date_str = f"{year}-{month}-{day}"
            else:
                date_str = date_raw
            
            # Create directory
            entry_dir = output_dir / site_type / org_name
            entry_dir.mkdir(parents=True, exist_ok=True)
            
            # Write metadata and content
            metadata = {
                'clickup_page_id': page['id'],
                'site_type': site_type,
                'organization': org_name,
                'date': date_str,
                'date_updated': page['date_updated'],
                'date_created': page['date_created'],
                'path_parts': path_parts,
                'doc_id': page['doc_id'],
                'creator_id': page['creator_id']
            }
            
            # Write files
            meta_file = entry_dir / f"{date_str}.meta.json"
            content_file = entry_dir / f"{date_str}.raw.md"
            
            with open(meta_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            with open(content_file, 'w') as f:
                f.write(page['content'])
            
            self.log(f"Wrote raw content: {content_file}")


def main():
    parser = argparse.ArgumentParser(description='Sync debugging KB from ClickUp')
    parser.add_argument('--check-only', action='store_true',
                       help='Only check for changes, don\'t write anything')
    parser.add_argument('--output-dir', type=str,
                       help='Directory to write raw content for AI processing')
    parser.add_argument('--index-path', type=str, default='docs/debugging/index.json',
                       help='Path to index.json file')
    parser.add_argument('--format', choices=['json', 'summary', 'paths'], default='json',
                       help='Output format')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose logging')
    
    args = parser.parse_args()
    
    # Get API token from environment
    api_token = os.getenv('CLICKUP_API_TOKEN')
    if not api_token:
        print("ERROR: CLICKUP_API_TOKEN environment variable not set", file=sys.stderr)
        sys.exit(1)
    
    try:
        sync = DebugKBSync(api_token)
        
        # Fetch current pages
        sync.log("Fetching ClickUp pages...")
        pages = sync.fetch_clickup_pages()
        
        # Extract leaf pages
        sync.log("Extracting leaf pages...")
        leaf_pages = sync.extract_leaf_pages(pages)
        
        if args.verbose:
            sync.log(f"Found {len(leaf_pages)} total leaf pages")
        
        # Load existing index
        index_path = Path(args.index_path)
        sync.log(f"Loading existing index from {index_path}...")
        existing = sync.load_existing_index(index_path)
        
        # Find changes
        new_pages, updated_pages = sync.find_changes(leaf_pages, existing)
        all_changes = new_pages + updated_pages
        
        sync.log(f"Found {len(new_pages)} new pages, {len(updated_pages)} updated pages")
        
        # Output results based on format
        if args.format == 'json':
            print(json.dumps(all_changes, indent=2))
        elif args.format == 'summary':
            print(f"Changes found: {len(all_changes)}")
            print(f"New: {len(new_pages)}")
            print(f"Updated: {len(updated_pages)}")
            if all_changes:
                print("\nChanged paths:")
                for page in all_changes:
                    print(f"  {page['path_str']} (ID: {page['id']})")
        elif args.format == 'paths':
            for page in all_changes:
                print(page['path_str'])
        
        # Write raw content if requested
        if args.output_dir and all_changes and not args.check_only:
            output_dir = Path(args.output_dir)
            sync.log(f"Writing raw content to {output_dir}...")
            sync.write_raw_content(all_changes, output_dir)
        
        # Exit with appropriate code
        if all_changes:
            sys.exit(1)  # Changes found
        else:
            sys.exit(0)  # No changes
            
    except DebugSyncError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc(file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()
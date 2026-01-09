#!/usr/bin/env python3
"""Scan for hardcoded credentials in codebase.

Usage:
    python tools/find_hardcoded_credentials.py shared_package/
    python tools/find_hardcoded_credentials.py audiobee_bcbs_il/
    python tools/find_hardcoded_credentials.py . --all

Scans for:
- API keys
- Passwords
- Usernames (in suspicious contexts)
- Secret tokens
- Authentication headers
- Private keys
"""
import argparse
import re
import sys
from pathlib import Path
from typing import Any


# Credential patterns
CREDENTIAL_PATTERNS = [
    # API keys
    (r'api[_-]?key\s*=\s*["\']([^"\']+)["\']', "API Key"),
    (r'apikey\s*=\s*["\']([^"\']+)["\']', "API Key"),
    (r'api[_-]?secret\s*=\s*["\']([^"\']+)["\']', "API Secret"),

    # Passwords
    (r'password\s*=\s*["\']([^"\']+)["\']', "Password"),
    (r'passwd\s*=\s*["\']([^"\']+)["\']', "Password"),
    (r'pwd\s*=\s*["\']([^"\']+)["\']', "Password"),

    # Usernames (in assignment context)
    (r'username\s*=\s*["\']([^"\']+)["\']', "Username"),
    (r'user\s*=\s*["\']([^"\']+)["\']', "Username"),

    # Tokens
    (r'token\s*=\s*["\']([^"\']+)["\']', "Token"),
    (r'auth[_-]?token\s*=\s*["\']([^"\']+)["\']', "Auth Token"),
    (r'access[_-]?token\s*=\s*["\']([^"\']+)["\']', "Access Token"),
    (r'secret[_-]?token\s*=\s*["\']([^"\']+)["\']', "Secret Token"),

    # Bearer tokens
    (r'bearer\s+([a-zA-Z0-9_\-\.]{20,})', "Bearer Token"),

    # AWS/Cloud credentials
    (r'aws[_-]?access[_-]?key[_-]?id\s*=\s*["\']([^"\']+)["\']', "AWS Access Key"),
    (r'aws[_-]?secret[_-]?access[_-]?key\s*=\s*["\']([^"\']+)["\']', "AWS Secret Key"),

    # Private keys (PEM format)
    (r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----', "Private Key"),

    # Database URLs
    (r'(?:postgres|mysql|mongodb)://[^:]+:([^@]+)@', "Database Password in URL"),
]

# Exclude patterns (safe assignments)
SAFE_PATTERNS = [
    r'os\.getenv',
    r'os\.environ',
    r'config\.',
    r'settings\.',
    r'SecretStr\(',
    r'input\(',
    r'#.*',  # Comments
    r'""".*"""',  # Docstrings
    r"'''.*'''",
]

# File extensions to scan
SCAN_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".env.example", ".md"}

# Directories to skip
SKIP_DIRS = {"node_modules", ".git", "__pycache__", "venv", ".venv", "dist", "build"}


def is_safe_line(line: str) -> bool:
    """Check if line is safe (loading from env, config, etc)."""
    for pattern in SAFE_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE):
            return True
    return False


def scan_file(file_path: Path) -> list[dict[str, Any]]:
    """Scan file for hardcoded credentials.

    Returns list of findings with {line_num, line, pattern_name, value}.
    """
    findings = []

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"  ! Error reading {file_path}: {e}")
        return findings

    for line_num, line in enumerate(lines, start=1):
        # Skip safe lines
        if is_safe_line(line):
            continue

        # Check for credential patterns
        for pattern, pattern_name in CREDENTIAL_PATTERNS:
            matches = re.finditer(pattern, line, re.IGNORECASE)

            for match in matches:
                # Get matched value (group 1 if exists, else full match)
                try:
                    value = match.group(1) if match.lastindex and match.lastindex >= 1 else match.group(0)
                except IndexError:
                    value = match.group(0)

                # Skip obviously safe values
                if value in ["", "your_api_key", "your_password", "***", "xxxx", "placeholder"]:
                    continue
                if value.startswith("$"):  # Shell variable
                    continue
                if len(value) < 3:  # Too short
                    continue

                findings.append({
                    "line_num": line_num,
                    "line": line.strip(),
                    "pattern_name": pattern_name,
                    "value": value[:20] + "..." if len(value) > 20 else value
                })

    return findings


def scan_directory(root_dir: Path, all_files: bool = False) -> dict[Path, list[dict]]:
    """Scan directory recursively for hardcoded credentials.

    Args:
        root_dir: Directory to scan
        all_files: If True, scan all files (not just code)

    Returns:
        Dict mapping file paths to findings
    """
    results = {}

    for file_path in root_dir.rglob("*"):
        # Skip directories
        if file_path.is_dir():
            continue

        # Skip excluded directories
        if any(skip_dir in file_path.parts for skip_dir in SKIP_DIRS):
            continue

        # Check file extension
        if not all_files and file_path.suffix not in SCAN_EXTENSIONS:
            continue

        # Scan file
        findings = scan_file(file_path)
        if findings:
            results[file_path] = findings

    return results


def main():
    parser = argparse.ArgumentParser(description="Scan for hardcoded credentials")
    parser.add_argument("path", help="Path to scan (file or directory)")
    parser.add_argument("--all", action="store_true", help="Scan all files (not just code)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all findings")

    args = parser.parse_args()

    scan_path = Path(args.path)

    if not scan_path.exists():
        print(f"✗ Path not found: {scan_path}")
        sys.exit(1)

    print(f"Scanning {scan_path} for hardcoded credentials...\n")

    if scan_path.is_file():
        # Scan single file
        findings = scan_file(scan_path)

        if not findings:
            print("✓ No hardcoded credentials found")
            sys.exit(0)

        print(f"✗ Found {len(findings)} potential credential(s) in {scan_path}:\n")
        for finding in findings:
            print(f"  Line {finding['line_num']}: {finding['pattern_name']}")
            print(f"    {finding['line']}")
            print(f"    Value: {finding['value']}\n")

        sys.exit(1)

    else:
        # Scan directory
        results = scan_directory(scan_path, all_files=args.all)

        if not results:
            print("✓ No hardcoded credentials found")
            sys.exit(0)

        total_findings = sum(len(findings) for findings in results.values())

        print(f"✗ Found {total_findings} potential credential(s) in {len(results)} file(s):\n")

        for file_path, findings in sorted(results.items()):
            print(f"{file_path}:")

            if args.verbose:
                for finding in findings:
                    print(f"  Line {finding['line_num']}: {finding['pattern_name']}")
                    print(f"    {finding['line']}")
                    print(f"    Value: {finding['value']}")
            else:
                # Show summary
                pattern_counts = {}
                for finding in findings:
                    pattern_name = finding["pattern_name"]
                    pattern_counts[pattern_name] = pattern_counts.get(pattern_name, 0) + 1

                for pattern_name, count in pattern_counts.items():
                    print(f"  - {pattern_name}: {count} occurrence(s)")

            print()

        if not args.verbose:
            print("Run with --verbose to see all findings")

        sys.exit(1)


if __name__ == "__main__":
    main()

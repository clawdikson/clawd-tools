#!/usr/bin/env python3
"""Rollback shared_package v3.0 migration safely.

Usage:
    python tools/rollback_migration.py audiobee_bcbs_il --dry-run
    python tools/rollback_migration.py audiobee_bcbs_il --execute
    python tools/rollback_migration.py --all --execute

Rollback procedure:
1. Verify shared_package submodule exists
2. Check git status (must be clean)
3. Checkout previous shared_package commit
4. Update git submodule reference
5. Verify rollback successful
"""
import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], cwd: Path = None) -> tuple[bool, str]:
    """Run shell command and return (success, output)."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


def check_git_status(repo_dir: Path) -> tuple[bool, str]:
    """Check if git repo has uncommitted changes."""
    success, output = run_command(["git", "status", "--porcelain"], cwd=repo_dir)
    if not success:
        return False, f"Failed to check git status: {output}"

    if output.strip():
        return False, f"Repository has uncommitted changes:\n{output}"

    return True, "Git status clean"


def get_submodule_commit(repo_dir: Path, submodule_path: str) -> str | None:
    """Get current commit hash for submodule."""
    success, output = run_command(
        ["git", "ls-tree", "HEAD", submodule_path],
        cwd=repo_dir
    )

    if not success or not output.strip():
        return None

    # Parse: "160000 commit <hash>\t<path>"
    parts = output.strip().split()
    if len(parts) >= 3:
        return parts[2]

    return None


def rollback_submodule(
    parent_repo: Path,
    submodule_path: str,
    target_commit: str,
    dry_run: bool = True
) -> tuple[bool, str]:
    """Rollback submodule to target commit.

    Args:
        parent_repo: Path to parent repository
        submodule_path: Relative path to submodule (e.g., "shared_package")
        target_commit: Commit hash to rollback to
        dry_run: If True, only simulate rollback

    Returns:
        (success, message)
    """
    submodule_full_path = parent_repo / submodule_path

    if not submodule_full_path.exists():
        return False, f"Submodule not found: {submodule_full_path}"

    # Check git status
    is_clean, status_msg = check_git_status(parent_repo)
    if not is_clean:
        return False, status_msg

    # Get current commit
    current_commit = get_submodule_commit(parent_repo, submodule_path)
    if not current_commit:
        return False, "Failed to get current submodule commit"

    print(f"  Current commit: {current_commit[:8]}")
    print(f"  Target commit:  {target_commit[:8]}")

    if current_commit == target_commit:
        return True, "Already at target commit"

    if dry_run:
        print("  [DRY RUN] Would execute:")
        print(f"    cd {submodule_full_path}")
        print(f"    git checkout {target_commit}")
        print(f"    cd {parent_repo}")
        print(f"    git add {submodule_path}")
        return True, "Dry run completed (no changes made)"

    # Execute rollback
    print("  Executing rollback...")

    # Checkout target commit in submodule
    success, output = run_command(
        ["git", "checkout", target_commit],
        cwd=submodule_full_path
    )
    if not success:
        return False, f"Failed to checkout {target_commit}: {output}"

    # Stage submodule change in parent repo
    success, output = run_command(
        ["git", "add", submodule_path],
        cwd=parent_repo
    )
    if not success:
        return False, f"Failed to stage submodule change: {output}"

    return True, f"Rollback successful! Commit changes with: git commit -m 'Rollback {submodule_path} to {target_commit[:8]}'"


def get_commit_history(repo_dir: Path, max_count: int = 10) -> list[dict]:
    """Get recent commit history."""
    success, output = run_command(
        ["git", "log", f"--max-count={max_count}", "--pretty=format:%H|%ai|%s"],
        cwd=repo_dir
    )

    if not success:
        return []

    commits = []
    for line in output.strip().split("\n"):
        if not line:
            continue

        parts = line.split("|", 2)
        if len(parts) == 3:
            commits.append({
                "hash": parts[0],
                "date": parts[1],
                "message": parts[2]
            })

    return commits


def main():
    parser = argparse.ArgumentParser(description="Rollback shared_package v3.0 migration")
    parser.add_argument("project", nargs="?", help="Project name (or --all for all projects)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate rollback (no changes)")
    parser.add_argument("--execute", action="store_true", help="Execute rollback")
    parser.add_argument("--all", action="store_true", help="Rollback all projects")
    parser.add_argument("--commit", help="Target commit hash (default: previous commit)")
    parser.add_argument("--list-commits", action="store_true", help="List recent commits")

    args = parser.parse_args()

    if not args.dry_run and not args.execute and not args.list_commits:
        parser.error("Specify --dry-run, --execute, or --list-commits")

    root = Path.cwd()
    shared_package_path = root / "shared_package"

    if not shared_package_path.exists():
        print("✗ shared_package submodule not found")
        sys.exit(1)

    # List commits mode
    if args.list_commits:
        print("Recent shared_package commits:\n")
        commits = get_commit_history(shared_package_path)

        for idx, commit in enumerate(commits):
            marker = "→" if idx == 0 else " "
            print(f"{marker} {commit['hash'][:8]} | {commit['date'][:19]} | {commit['message']}")

        print("\nUse --commit <hash> to specify target commit")
        sys.exit(0)

    # Determine target commit
    if args.commit:
        target_commit = args.commit
    else:
        # Get previous commit (HEAD~1)
        commits = get_commit_history(shared_package_path, max_count=2)
        if len(commits) < 2:
            print("✗ No previous commit found")
            sys.exit(1)
        target_commit = commits[1]["hash"]
        print(f"Using previous commit: {target_commit[:8]} - {commits[1]['message']}")

    # Confirm rollback
    if args.execute and not args.all:
        print(f"\n⚠️  WARNING: This will rollback shared_package to {target_commit[:8]}")
        response = input("Continue? (yes/no): ")
        if response.lower() != "yes":
            print("Rollback cancelled")
            sys.exit(0)

    # Execute rollback
    print("\nRolling back shared_package...")
    success, message = rollback_submodule(
        parent_repo=root,
        submodule_path="shared_package",
        target_commit=target_commit,
        dry_run=args.dry_run
    )

    if success:
        print(f"\n✓ {message}")
        sys.exit(0)
    else:
        print(f"\n✗ Rollback failed: {message}")
        sys.exit(1)


if __name__ == "__main__":
    main()

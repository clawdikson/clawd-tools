#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer>=0.9.0",
#     "rich>=13.0.0",
# ]
# ///
"""
HealthSparq Restructuring Executor

CLI tool for executing the HealthSparq singleton implementation plan
using Ralph Wiggum-style autonomous execution with progress tracking.

Usage:
    # Show current progress
    python tools/healthsparq_executor.py status

    # Execute all phases (continues from last incomplete)
    python tools/healthsparq_executor.py run

    # Execute specific phase
    python tools/healthsparq_executor.py run --phase 0

    # Generate prompt for a phase (for manual execution)
    python tools/healthsparq_executor.py prompt --phase 0

    # Reset progress
    python tools/healthsparq_executor.py reset

    # Verify phase completion
    python tools/healthsparq_executor.py verify --phase 0
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import typer
    from rich import print as rprint
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
except ImportError:
    print("Missing dependencies. Install with: pip install typer rich")
    sys.exit(1)

# Constants
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
PROGRESS_FILE = REPO_ROOT / "docs" / "restructuring" / "healthsparq" / "PROGRESS.json"
PLAN_FILE = REPO_ROOT / "docs" / "restructuring" / "healthsparq" / "HEALTHSPARQ_SINGLETON_PLAN.md"

app = typer.Typer(
    name="healthsparq-executor",
    help="Execute HealthSparq singleton restructuring plan with progress tracking",
    add_completion=False,
)
console = Console()


def load_progress() -> dict:
    """Load progress from JSON file."""
    if not PROGRESS_FILE.exists():
        console.print(f"[red]Progress file not found: {PROGRESS_FILE}[/red]")
        raise typer.Exit(1)
    return json.loads(PROGRESS_FILE.read_text())


def save_progress(progress: dict) -> None:
    """Save progress to JSON file with timestamp update."""
    progress["updated_at"] = datetime.now().isoformat()
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2))


def get_phase_status_emoji(status: str) -> str:
    """Get emoji for phase status."""
    return {
        "pending": "⏳",
        "in_progress": "🔄",
        "completed": "✅",
        "failed": "❌",
        "skipped": "⏭️",
    }.get(status, "❓")


def get_next_phase(progress: dict) -> Optional[str]:
    """Get the next phase that needs to be executed."""
    phase_order = ["0", "1", "2", "3", "4", "5", "6", "7", "8"]
    for phase_id in phase_order:
        if phase_id in progress["phases"]:
            phase = progress["phases"][phase_id]
            if phase["status"] in ["pending", "in_progress"]:
                return phase_id
    return None


def update_phase_status(
    progress: dict,
    phase_id: str,
    status: str,
    error: Optional[str] = None,
    increment_iteration: bool = False,
) -> None:
    """Update phase status with timestamp."""
    phase = progress["phases"][phase_id]
    phase["status"] = status

    if status == "in_progress" and phase["started_at"] is None:
        phase["started_at"] = datetime.now().isoformat()
    elif status in ["completed", "failed"]:
        phase["completed_at"] = datetime.now().isoformat()

    if error:
        phase["error"] = error

    if increment_iteration:
        phase["current_iteration"] += 1

    progress["current_phase"] = phase_id
    save_progress(progress)


def update_criterion_status(
    progress: dict, phase_id: str, criterion_index: int, passed: bool
) -> None:
    """Update a specific criterion's pass/fail status."""
    progress["phases"][phase_id]["success_criteria"][criterion_index]["passed"] = passed
    save_progress(progress)


def add_execution_log(progress: dict, message: str, level: str = "info") -> None:
    """Add entry to execution log."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "message": message,
    }
    progress["execution_log"].append(log_entry)
    # Keep only last 100 entries
    progress["execution_log"] = progress["execution_log"][-100:]
    save_progress(progress)


def run_verification_command(command: str, cwd: Path) -> tuple[bool, str]:
    """Run a verification command and return (success, output)."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        return result.returncode == 0, output.strip()
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def generate_phase_prompt(phase_id: str, progress: dict) -> str:
    """Generate a Ralph Wiggum style prompt for a phase."""
    phase = progress["phases"][phase_id]
    plan_content = PLAN_FILE.read_text()

    # Extract phase section from plan
    phase_section = f"## PHASE {phase_id}:"
    if phase_section not in plan_content:
        phase_section = f"## PHASE {phase_id} "

    # Build success criteria list
    criteria = "\n".join(
        f"  - {'[x]' if c['passed'] else '[ ]'} {c['criterion']}"
        for c in phase["success_criteria"]
    )

    # Build verification commands
    verifications = "\n".join(f"  {cmd}" for cmd in phase["verification_commands"])

    prompt = f"""Execute PHASE {phase_id} ({phase["name"]}) of the HealthSparq singleton implementation.

## Reference Document
Read the full plan at: docs/restructuring/healthsparq/HEALTHSPARQ_SINGLETON_PLAN.md

## Goal
{phase["name"]}

## Subagent
Use Task tool with subagent_type="{phase["subagent"]}"

## Success Criteria (check each when complete)
{criteria}

## Verification Commands (all must exit 0)
{verifications}

## Progress Tracking
After EACH significant step:
1. Update PROGRESS.json at docs/restructuring/healthsparq/PROGRESS.json
2. Mark criteria as passed when verified
3. Increment current_iteration after each attempt

## Iteration Limits
Max iterations: {phase["max_iterations"]}
Current iteration: {phase["current_iteration"]}

## Completion Signal
When ALL criteria pass, output: PHASE_{phase_id}_COMPLETE

## Instructions
1. Read HEALTHSPARQ_SINGLETON_PLAN.md for detailed task list
2. Execute tasks for Phase {phase_id}
3. After each task, update PROGRESS.json
4. Run verification commands to check success criteria
5. Update each criterion's "passed" field in PROGRESS.json when verified
6. When complete, update phase status to "completed"
"""
    return prompt


def generate_full_execution_prompt(progress: dict) -> str:
    """Generate prompt for full autonomous execution."""
    # Get pending phases
    phase_order = ["0", "1", "2", "3", "4", "5", "6", "7", "8"]
    pending = []
    for pid in phase_order:
        if pid in progress["phases"]:
            p = progress["phases"][pid]
            if p["status"] not in ["completed", "skipped"]:
                pending.append(f"  Phase {pid}: {p['name']} ({p['status']})")

    pending_list = "\n".join(pending) if pending else "  All phases complete!"

    prompt = f"""Execute the HealthSparq singleton implementation plan autonomously.

## Reference Document
docs/restructuring/healthsparq/HEALTHSPARQ_SINGLETON_PLAN.md

## Progress Tracking File
docs/restructuring/healthsparq/PROGRESS.json

## Pending Phases
{pending_list}

## Execution Pattern
For EACH phase:
1. Read PROGRESS.json to get current state
2. Generate subagent task using Task tool with specified subagent_type
3. Execute phase tasks
4. Update PROGRESS.json after each significant step:
   - Update current_iteration
   - Mark success_criteria as passed when verified
   - Update phase status (pending -> in_progress -> completed)
   - Add to execution_log
5. Run all verification commands
6. Only proceed to next phase when current is COMPLETE

## Critical: Progress Tracking
You MUST update PROGRESS.json:
- BEFORE starting a phase (status: "in_progress", started_at: timestamp)
- AFTER each criterion passes (success_criteria[n].passed: true)
- WHEN phase completes (status: "completed", completed_at: timestamp)

## Completion Signal
Output HEALTHSPARQ_COMPLETE when all phases are done.

## Error Handling
If a phase fails after max_iterations:
1. Set phase status to "failed"
2. Set phase error message
3. Add to execution_log
4. Report to user before continuing
"""
    return prompt


@app.command()
def status():
    """Show current progress status."""
    progress = load_progress()

    # Create status table
    table = Table(title="HealthSparq Restructuring Progress")
    table.add_column("Phase", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Status", justify="center")
    table.add_column("Subagent", style="dim")
    table.add_column("Progress", justify="right")
    table.add_column("Criteria", justify="center")

    phase_order = ["0", "1", "2", "3", "4", "5", "6", "7", "8"]
    for phase_id in phase_order:
        if phase_id not in progress["phases"]:
            continue

        phase = progress["phases"][phase_id]
        status_emoji = get_phase_status_emoji(phase["status"])
        passed_criteria = sum(1 for c in phase["success_criteria"] if c["passed"])
        total_criteria = len(phase["success_criteria"])

        table.add_row(
            phase_id,
            phase["name"],
            f"{status_emoji} {phase['status']}",
            phase["subagent"],
            f"{phase['current_iteration']}/{phase['max_iterations']}",
            f"{passed_criteria}/{total_criteria}",
        )

    console.print(table)

    # Show overall status
    current = progress.get("current_phase")
    if current:
        console.print(f"\n[bold]Current Phase:[/bold] {current}")

    # Show recent log entries
    if progress.get("execution_log"):
        console.print("\n[bold]Recent Activity:[/bold]")
        for entry in progress["execution_log"][-5:]:
            level_color = {"info": "blue", "error": "red", "warning": "yellow"}.get(
                entry["level"], "white"
            )
            console.print(
                f"  [{level_color}]{entry['timestamp'][:19]}[/{level_color}] {entry['message']}"
            )


@app.command()
def run(
    phase: Optional[int] = typer.Option(
        None, "--phase", "-p", help="Run specific phase (0-8)"
    ),
    all_phases: bool = typer.Option(
        False, "--all", "-a", help="Run all remaining phases"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be executed without running"
    ),
    plain: bool = typer.Option(
        False, "--plain", "-c", help="Output plain text prompt (easy to copy)"
    ),
):
    """Run restructuring phases."""
    progress = load_progress()

    if phase is not None:
        phase_id = str(phase)
        if phase_id not in progress["phases"]:
            console.print(f"[red]Invalid phase: {phase}[/red]")
            raise typer.Exit(1)

        prompt = generate_phase_prompt(phase_id, progress)

        if dry_run or plain:
            if plain:
                # Plain text output for easy copying
                print(prompt)
            else:
                console.print(Panel(prompt, title=f"Phase {phase_id} Prompt", expand=False))
            return

        # Generate and display the prompt
        update_phase_status(progress, phase_id, "in_progress")
        add_execution_log(progress, f"Started Phase {phase_id}: {progress['phases'][phase_id]['name']}")

        # Output plain prompt for easy copying
        console.print(f"\n[bold green]Phase {phase_id} Prompt[/bold green] (copy below):\n")
        console.print("-" * 60)
        print(prompt)
        console.print("-" * 60)
        console.print(f"\n[dim]Execute with: /ralph-loop \"<prompt>\" --max-iterations {progress['phases'][phase_id]['max_iterations']}[/dim]")

    elif all_phases:
        prompt = generate_full_execution_prompt(progress)

        if dry_run or plain:
            if plain:
                print(prompt)
            else:
                console.print(Panel(prompt, title="Full Execution Prompt", expand=False))
            return

        next_phase = get_next_phase(progress)
        if next_phase:
            update_phase_status(progress, next_phase, "in_progress")
        add_execution_log(progress, "Started full autonomous execution")
        progress["overall_status"] = "in_progress"
        save_progress(progress)

        # Output plain prompt for easy copying
        console.print(f"\n[bold green]Full Execution Prompt[/bold green] (copy below):\n")
        console.print("-" * 60)
        print(prompt)
        console.print("-" * 60)
        console.print(f"\n[dim]Execute with: /ralph-loop \"<prompt>\" --max-iterations 100[/dim]")

    else:
        # Run next pending phase
        next_phase = get_next_phase(progress)
        if next_phase is None:
            console.print("[green]All phases complete![/green]")
            return

        prompt = generate_phase_prompt(next_phase, progress)

        if dry_run or plain:
            if plain:
                print(prompt)
            else:
                console.print(Panel(prompt, title=f"Phase {next_phase} Prompt", expand=False))
            return

        update_phase_status(progress, next_phase, "in_progress")
        add_execution_log(
            progress,
            f"Started Phase {next_phase}: {progress['phases'][next_phase]['name']}",
        )

        # Output plain prompt for easy copying
        console.print(f"\n[bold green]Phase {next_phase} Prompt[/bold green] (copy below):\n")
        console.print("-" * 60)
        print(prompt)
        console.print("-" * 60)
        console.print(f"\n[dim]Execute with: /ralph-loop \"<prompt>\" --max-iterations {progress['phases'][next_phase]['max_iterations']}[/dim]")


@app.command()
def prompt(
    phase: int = typer.Option(..., "--phase", "-p", help="Phase number (0-8)"),
    plain: bool = typer.Option(
        True, "--plain/--rich", help="Output plain text (default) or rich format"
    ),
):
    """Generate Ralph Wiggum prompt for a phase."""
    progress = load_progress()
    phase_id = str(phase)

    if phase_id not in progress["phases"]:
        console.print(f"[red]Invalid phase: {phase}[/red]")
        raise typer.Exit(1)

    prompt_text = generate_phase_prompt(phase_id, progress)

    if plain:
        # Plain text output - easy to copy
        print(prompt_text)
    else:
        console.print(Panel(prompt_text, title=f"Phase {phase_id} Prompt", expand=False))


@app.command()
def verify(
    phase: int = typer.Option(..., "--phase", "-p", help="Phase number (0-8)"),
):
    """Verify a phase's completion by running verification commands."""
    progress = load_progress()
    phase_id = str(phase)

    if phase_id not in progress["phases"]:
        console.print(f"[red]Invalid phase: {phase}[/red]")
        raise typer.Exit(1)

    phase_data = progress["phases"][phase_id]
    console.print(f"\n[bold]Verifying Phase {phase_id}: {phase_data['name']}[/bold]\n")

    all_passed = True
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress_bar:
        for i, cmd in enumerate(phase_data["verification_commands"]):
            task = progress_bar.add_task(f"Running: {cmd[:50]}...", total=None)
            success, output = run_verification_command(cmd, REPO_ROOT)

            if success:
                console.print(f"  [green]✓[/green] {cmd}")
                # Update corresponding criterion if exists
                if i < len(phase_data["success_criteria"]):
                    update_criterion_status(progress, phase_id, i, True)
            else:
                console.print(f"  [red]✗[/red] {cmd}")
                if output:
                    console.print(f"    [dim]{output[:200]}[/dim]")
                all_passed = False
                if i < len(phase_data["success_criteria"]):
                    update_criterion_status(progress, phase_id, i, False)

            progress_bar.remove_task(task)

    # Update phase status based on verification
    if all_passed:
        update_phase_status(progress, phase_id, "completed")
        add_execution_log(progress, f"Phase {phase_id} verification PASSED")
        console.print(f"\n[green]Phase {phase_id} COMPLETE![/green]")
    else:
        add_execution_log(
            progress, f"Phase {phase_id} verification FAILED", level="warning"
        )
        console.print(f"\n[yellow]Phase {phase_id} verification failed[/yellow]")


@app.command()
def reset(
    phase: Optional[int] = typer.Option(None, "--phase", "-p", help="Reset specific phase"),
    all_phases: bool = typer.Option(False, "--all", "-a", help="Reset all phases"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Reset progress (specific phase or all)."""
    progress = load_progress()

    if all_phases:
        if not confirm:
            if not typer.confirm("Reset ALL phases? This cannot be undone."):
                raise typer.Abort()

        for phase_id in progress["phases"]:
            progress["phases"][phase_id]["status"] = "pending"
            progress["phases"][phase_id]["current_iteration"] = 0
            progress["phases"][phase_id]["started_at"] = None
            progress["phases"][phase_id]["completed_at"] = None
            progress["phases"][phase_id]["error"] = None
            for criterion in progress["phases"][phase_id]["success_criteria"]:
                criterion["passed"] = False

        progress["current_phase"] = None
        progress["overall_status"] = "pending"
        progress["execution_log"] = []
        save_progress(progress)
        add_execution_log(progress, "Reset all phases")
        console.print("[yellow]All phases reset[/yellow]")

    elif phase is not None:
        phase_id = str(phase)
        if phase_id not in progress["phases"]:
            console.print(f"[red]Invalid phase: {phase}[/red]")
            raise typer.Exit(1)

        if not confirm:
            if not typer.confirm(f"Reset phase {phase}?"):
                raise typer.Abort()

        progress["phases"][phase_id]["status"] = "pending"
        progress["phases"][phase_id]["current_iteration"] = 0
        progress["phases"][phase_id]["started_at"] = None
        progress["phases"][phase_id]["completed_at"] = None
        progress["phases"][phase_id]["error"] = None
        for criterion in progress["phases"][phase_id]["success_criteria"]:
            criterion["passed"] = False

        save_progress(progress)
        add_execution_log(progress, f"Reset phase {phase_id}")
        console.print(f"[yellow]Phase {phase} reset[/yellow]")

    else:
        console.print("[red]Specify --phase or --all[/red]")
        raise typer.Exit(1)


@app.command()
def log(
    count: int = typer.Option(20, "--count", "-n", help="Number of entries to show"),
):
    """Show execution log."""
    progress = load_progress()

    if not progress.get("execution_log"):
        console.print("[dim]No log entries[/dim]")
        return

    table = Table(title="Execution Log")
    table.add_column("Timestamp", style="dim")
    table.add_column("Level", justify="center")
    table.add_column("Message")

    for entry in progress["execution_log"][-count:]:
        level_color = {"info": "blue", "error": "red", "warning": "yellow"}.get(
            entry["level"], "white"
        )
        table.add_row(
            entry["timestamp"][:19],
            f"[{level_color}]{entry['level']}[/{level_color}]",
            entry["message"],
        )

    console.print(table)


@app.command()
def update_criterion(
    phase: int = typer.Option(..., "--phase", "-p", help="Phase number"),
    criterion: int = typer.Option(..., "--criterion", "-c", help="Criterion index (0-based)"),
    passed: bool = typer.Option(..., "--passed/--failed", help="Mark as passed or failed"),
):
    """Manually update a criterion's status."""
    progress = load_progress()
    phase_id = str(phase)

    if phase_id not in progress["phases"]:
        console.print(f"[red]Invalid phase: {phase}[/red]")
        raise typer.Exit(1)

    phase_data = progress["phases"][phase_id]
    if criterion >= len(phase_data["success_criteria"]):
        console.print(f"[red]Invalid criterion index: {criterion}[/red]")
        raise typer.Exit(1)

    update_criterion_status(progress, phase_id, criterion, passed)
    crit_text = phase_data["success_criteria"][criterion]["criterion"]
    status_text = "[green]PASSED[/green]" if passed else "[red]FAILED[/red]"
    console.print(f"Updated: {crit_text} → {status_text}")
    add_execution_log(
        progress,
        f"Manual update: Phase {phase_id} criterion {criterion} → {'passed' if passed else 'failed'}",
    )


@app.command()
def complete_phase(
    phase: int = typer.Option(..., "--phase", "-p", help="Phase number"),
):
    """Mark a phase as completed (after manual verification)."""
    progress = load_progress()
    phase_id = str(phase)

    if phase_id not in progress["phases"]:
        console.print(f"[red]Invalid phase: {phase}[/red]")
        raise typer.Exit(1)

    # Mark all criteria as passed
    for criterion in progress["phases"][phase_id]["success_criteria"]:
        criterion["passed"] = True

    update_phase_status(progress, phase_id, "completed")
    add_execution_log(progress, f"Manually completed Phase {phase_id}")
    console.print(f"[green]Phase {phase_id} marked as COMPLETE[/green]")


if __name__ == "__main__":
    app()

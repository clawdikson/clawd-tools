#!/usr/bin/env python
"""AI-powered documentation generation using Claude Code CLI.

Uses `claude -p` (print mode) to generate documentation from code structure.

Usage:
    # Generate docs for a package
    python scripts/generate_docs.py generate core/ --output docs/api/core.md

    # Generate project index
    python scripts/generate_docs.py index --output docs/PROJECTS.md

    # Generate config schema reference
    python scripts/generate_docs.py schema healthsparq --output docs/config/healthsparq.md

Requirements:
    Claude Code CLI must be installed and configured.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
import yaml
from loguru import logger

# Configure loguru for better output
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
    level="INFO",
)

app = typer.Typer(
    name="generate-docs",
    help="AI-powered documentation generation using Claude Code CLI.",
    no_args_is_help=True,
)

REPO_ROOT = Path(__file__).parent.parent


@dataclass
class ModuleInfo:
    """Information about a Python module."""

    path: Path
    name: str
    docstring: str | None = None
    classes: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)


@dataclass
class PackageStructure:
    """Structure information for a package."""

    name: str
    path: Path
    modules: list[ModuleInfo] = field(default_factory=list)
    subpackages: list[str] = field(default_factory=list)


def run_claude(prompt: str, max_turns: int = 1) -> str:
    """Run claude -p with the given prompt and return the output.

    Args:
        prompt: The prompt to send to Claude
        max_turns: Maximum turns (default 1 for simple generation)

    Returns:
        Claude's response text
    """
    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--max-turns", str(max_turns)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            typer.echo(f"Error from claude: {result.stderr}", err=True)
            raise typer.Exit(1)
        return result.stdout.strip()
    except FileNotFoundError:
        typer.echo("Error: 'claude' CLI not found. Install Claude Code first.", err=True)
        typer.echo("See: https://docs.anthropic.com/claude-code", err=True)
        raise typer.Exit(1)
    except subprocess.TimeoutExpired:
        typer.echo("Error: Claude request timed out after 120s", err=True)
        raise typer.Exit(1)


def extract_module_info(file_path: Path) -> ModuleInfo | None:
    """Extract information from a Python module."""
    try:
        content = file_path.read_text()
        tree = ast.parse(content)
    except (SyntaxError, UnicodeDecodeError):
        return None

    docstring = ast.get_docstring(tree)
    classes = []
    functions = []
    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_doc = ast.get_docstring(node)
            classes.append(f"{node.name}: {class_doc[:100] if class_doc else 'No docstring'}")
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if not node.name.startswith("_") or node.name == "__init__":
                func_doc = ast.get_docstring(node)
                functions.append(f"{node.name}: {func_doc[:100] if func_doc else 'No docstring'}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    return ModuleInfo(
        path=file_path,
        name=file_path.stem,
        docstring=docstring,
        classes=classes,
        functions=functions,
        imports=list(set(imports)),
    )


def analyze_package(package_path: Path) -> PackageStructure:
    """Analyze a Python package structure."""
    package_name = package_path.name
    modules = []
    subpackages = []

    for item in sorted(package_path.iterdir()):
        if item.is_file() and item.suffix == ".py" and not item.name.startswith("_"):
            info = extract_module_info(item)
            if info:
                modules.append(info)
        elif item.is_dir() and (item / "__init__.py").exists():
            subpackages.append(item.name)

    # Also check __init__.py
    init_file = package_path / "__init__.py"
    if init_file.exists():
        info = extract_module_info(init_file)
        if info:
            info.name = "__init__"
            modules.insert(0, info)

    return PackageStructure(
        name=package_name,
        path=package_path,
        modules=modules,
        subpackages=subpackages,
    )


def get_tldr_structure(path: Path) -> str | None:
    """Get code structure using tldr CLI if available."""
    try:
        result = subprocess.run(
            ["tldr", "structure", str(path), "--lang", "python"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


@app.command()
def generate(
    package_path: Annotated[Path, typer.Argument(help="Path to package directory")],
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output file path")] = None,
    include_private: Annotated[
        bool, typer.Option("--private", help="Include private members")
    ] = False,
) -> None:
    """Generate API documentation for a Python package.

    Uses Claude Code CLI to analyze code structure and generate comprehensive documentation.
    """
    if not package_path.exists():
        typer.echo(f"Error: Path not found: {package_path}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Analyzing package: {package_path}")

    # Get structure info
    structure = analyze_package(package_path)
    tldr_output = get_tldr_structure(package_path)

    # Build context
    context_parts = [
        f"Package: {structure.name}",
        f"Modules: {len(structure.modules)}",
        f"Subpackages: {', '.join(structure.subpackages) if structure.subpackages else 'None'}",
        "",
    ]

    for module in structure.modules:
        context_parts.append(f"## {module.name}")
        if module.docstring:
            context_parts.append(f"Docstring: {module.docstring[:500]}")
        if module.classes:
            context_parts.append(f"Classes: {', '.join(c.split(':')[0] for c in module.classes)}")
        if module.functions:
            context_parts.append(
                f"Functions: {', '.join(f.split(':')[0] for f in module.functions)}"
            )
        context_parts.append("")

    if tldr_output:
        context_parts.append("## Code Structure (from tldr)")
        context_parts.append(tldr_output[:3000])

    context = "\n".join(context_parts)

    prompt = f"""You are a technical documentation writer. Generate API documentation for the '{structure.name}' Python package in Markdown format.

Context:
{context}

Generate documentation that includes:
1. Overview section explaining the package purpose
2. Installation/import instructions
3. Module reference with classes and functions
4. Usage examples
5. Common patterns

Output ONLY the Markdown content, no explanations or preamble.
Reference docs/SCRAPER_DOCUMENTATION.md for examples of how to structure the documentation."""

    typer.echo("Generating documentation with Claude...")

    doc_content = run_claude(prompt)

    # Add header
    header = f"""---
generated: {datetime.now().isoformat()}
package: {structure.name}
---

"""
    final_content = header + doc_content

    # Output
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(final_content)
        typer.echo(f"✓ Documentation written to: {output}")
    else:
        typer.echo("\n" + "=" * 60)
        typer.echo(final_content)


@app.command()
def index(
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output file path")] = None,
) -> None:
    """Generate a project index with all audiobee_* projects.

    Creates a Markdown table with project information, last run dates, and status.
    """
    typer.echo("Scanning projects...")

    projects = []
    for d in sorted(REPO_ROOT.iterdir()):
        if d.is_dir() and d.name.startswith("audiobee_"):
            project_info = {
                "name": d.name,
                "platform": "unknown",
                "states": [],
                "last_run": None,
            }

            # Check config.yaml
            config_path = d / "config.yaml"
            if config_path.exists():
                try:
                    with open(config_path) as f:
                        config = yaml.safe_load(f)
                    if "site" in config:
                        project_info["platform"] = "healthsparq"
                    elif "api" in config:
                        project_info["platform"] = "sapphire"
                    if "coverage" in config:
                        project_info["states"] = config["coverage"].get("states", [])
                except Exception:
                    pass

            # Check for output directories (date-formatted)
            for item in d.iterdir():
                if item.is_dir() and item.name.isdigit() and len(item.name) == 8:
                    run_date = item.name
                    if project_info["last_run"] is None or run_date > project_info["last_run"]:
                        project_info["last_run"] = run_date

            projects.append(project_info)

    typer.echo(f"Found {len(projects)} projects")

    # Build context
    context = json.dumps(projects, indent=2)

    prompt = f"""You are a technical documentation writer. Generate a project index document in Markdown format.

Project data (JSON):
{context}

Generate an index that includes:
1. Summary statistics (total projects, by platform, by state)
2. Table of all projects with columns: Project, Platform, States, Last Run
3. Projects grouped by platform
4. Any projects that haven't been run recently (last_run > 30 days or null)

Output ONLY the Markdown content, no explanations or preamble."""

    typer.echo("Generating index with Claude...")

    doc_content = run_claude(prompt)

    header = f"""---
generated: {datetime.now().isoformat()}
total_projects: {len(projects)}
---

"""
    final_content = header + doc_content

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(final_content)
        typer.echo(f"✓ Index written to: {output}")
    else:
        typer.echo("\n" + "=" * 60)
        typer.echo(final_content)


@app.command()
def schema(
    platform: Annotated[str, typer.Argument(help="Platform: healthsparq or sapphire")],
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output file path")] = None,
) -> None:
    """Generate configuration schema reference for a platform.

    Extracts Pydantic model definitions and generates human-readable documentation.
    """
    if platform not in ["healthsparq", "sapphire"]:
        typer.echo("Error: Platform must be 'healthsparq' or 'sapphire'", err=True)
        raise typer.Exit(1)

    schema_path = REPO_ROOT / platform / "config" / "schema.py"
    if not schema_path.exists():
        typer.echo(f"Error: Schema file not found: {schema_path}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Analyzing schema: {schema_path}")

    # Read schema file
    schema_content = schema_path.read_text()

    # Also check for a sample config
    sample_config = ""
    configs_dir = REPO_ROOT / platform / "configs"
    if configs_dir.exists():
        for f in configs_dir.iterdir():
            if f.suffix == ".yaml" and not f.name.startswith("_"):
                sample_config = f.read_text()[:2000]
                break

    prompt = f"""You are a technical documentation writer. Generate a configuration schema reference for the {platform} platform in Markdown format.

Schema source ({platform}/config/schema.py):
```python
{schema_content[:8000]}
```

Sample config:
```yaml
{sample_config}
```

Generate documentation that includes:
1. Overview of configuration structure
2. Table of all configuration options with: Field name, Type, Required/Optional, Default value, Description
3. Validation rules and constraints
4. Complete example config.yaml
5. Common configuration patterns

Output ONLY the Markdown content, no explanations or preamble."""

    typer.echo("Generating schema docs with Claude...")

    doc_content = run_claude(prompt)

    header = f"""---
generated: {datetime.now().isoformat()}
platform: {platform}
---

"""
    final_content = header + doc_content

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(final_content)
        typer.echo(f"✓ Schema docs written to: {output}")
    else:
        typer.echo("\n" + "=" * 60)
        typer.echo(final_content)


@app.command("readme")
def generate_readme(
    project_path: Annotated[Path, typer.Argument(help="Path to project directory")],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output file (default: README.md in project)"),
    ] = None,
) -> None:
    """Generate or update a project README.md using AI.

    Analyzes the project structure and generates a comprehensive README.
    """
    if not project_path.exists():
        typer.echo(f"Error: Path not found: {project_path}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Analyzing project: {project_path}")

    # Gather project info
    project_info = {
        "name": project_path.name,
        "files": [],
        "config": None,
        "has_mapper": False,
        "has_tests": False,
    }

    for f in project_path.iterdir():
        if f.is_file():
            project_info["files"].append(f.name)
            if f.name == "config.yaml":
                try:
                    project_info["config"] = yaml.safe_load(f.read_text())
                except Exception:
                    pass
            elif f.name == "mapper.py":
                project_info["has_mapper"] = True

    if (project_path / "tests").exists():
        project_info["has_tests"] = True

    context = json.dumps(project_info, indent=2, default=str)

    prompt = f"""You are a technical documentation writer. Generate a README.md for this scraper project in Markdown format.

Project info (JSON):
{context}

Generate a README that includes:
1. Project title and brief description
2. Prerequisites (Python version, dependencies)
3. Setup instructions
4. Usage examples (CLI commands)
5. Configuration reference (key fields from config.yaml)
6. Custom mapper description (if has_mapper is true)
7. Output format description
8. Troubleshooting tips

Output ONLY the Markdown content, no explanations or preamble."""

    typer.echo("Generating README with Claude...")

    doc_content = run_claude(prompt)

    output_path = output or (project_path / "README.md")
    output_path.write_text(doc_content)
    typer.echo(f"✓ README written to: {output_path}")


@app.command("claude-md")
def generate_claude_md(
    project_path: Annotated[Path, typer.Argument(help="Path to project or package directory")],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output file (default: CLAUDE.md in project)"),
    ] = None,
) -> None:
    """Generate or update a CLAUDE.md file for Claude Code context.

    Creates a context file optimized for Claude Code to understand the project.
    """
    if not project_path.exists():
        typer.echo(f"Error: Path not found: {project_path}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Analyzing project: {project_path}")

    # Gather comprehensive project info
    structure = analyze_package(project_path) if (project_path / "__init__.py").exists() else None
    tldr_output = get_tldr_structure(project_path)

    # Check for config files
    config_content = ""
    for config_name in ["config.yaml", "pyproject.toml"]:
        config_path = project_path / config_name
        if config_path.exists():
            config_content += f"\n{config_name}:\n{config_path.read_text()[:1500]}\n"

    # Build context
    context_parts = [f"Project: {project_path.name}"]

    if structure:
        context_parts.append("Type: Python package")
        context_parts.append(f"Modules: {len(structure.modules)}")
        context_parts.append(f"Subpackages: {', '.join(structure.subpackages)}")
    else:
        context_parts.append("Type: Project directory")

    if tldr_output:
        context_parts.append(f"\nCode structure:\n{tldr_output[:2000]}")

    if config_content:
        context_parts.append(f"\nConfig files:{config_content}")

    context = "\n".join(context_parts)

    prompt = f"""You are creating a CLAUDE.md file - a context document for Claude Code (AI coding assistant).

Project info:
{context}

Generate a CLAUDE.md that includes:
1. Brief overview (what this project/package does)
2. Key commands (build, test, run)
3. Architecture overview (main components, data flow)
4. Important patterns and conventions used
5. Common tasks and how to do them

Format guidelines:
- Use clear headers and bullet points
- Include code examples for commands
- Keep it concise but complete
- Focus on what an AI assistant needs to know to help effectively

Output ONLY the Markdown content, no explanations or preamble."""

    typer.echo("Generating CLAUDE.md with Claude...")

    doc_content = run_claude(prompt)

    output_path = output or (project_path / "CLAUDE.md")
    output_path.write_text(doc_content)
    typer.echo(f"✓ CLAUDE.md written to: {output_path}")


# Thread-safe counter for progress tracking
_progress_lock = threading.Lock()
_progress = {"completed": 0, "failed": 0, "skipped": 0, "total": 0, "total_time": 0.0}


SCRAPER_DOC_PROMPT = """Analyze the scraper in {site_path} and create SCRAPER_DOCUMENTATION.md.

Read all Python files (*.py), config files (config.yaml, config.py), and data files.
Document the scraper following this exact structure:

## 1. Overview
Create a table with:
- Project Name
- States covered
- Lines of Business (LOB)
- Update Frequency
- Site Type (healthsparq, sapphire, carrier, etc.)

## 2. Pipeline Steps
Create an ASCII flowchart showing the script execution order:
- 0_*.py → 1_*.py → 2_*.py → etc.
- Or run.py → mapper.py for library-based scrapers
Show what each script does.

## 3. API Details
Document:
- Base URL
- Key endpoints
- Sample request/response (if visible in code)

## 4. Search Strategy
Explain how providers are discovered:
- ZIP codes, coordinates, radius
- Specialty iteration
- Pagination approach

## 5. Networks
Create a table of network codes and their descriptions (if found in config or code).

## 6. Mapping
Document:
- Input format (raw API response structure)
- Output format (Ideon schema fields)
- NPI merge/dedup logic

## 7. AutoQA (if applicable)
Document dropped NPI recovery workflow if the scraper has QA/recovery phases.

## 8. Directory Structure
Show the file tree of the project.

## 9. Configuration
Document config.py or config.yaml settings with descriptions.

## 10. Proxy Configuration
Document proxy setup if configured.

## 11. Running Instructions
How to run the scraper with example commands.

## 12. QA Functions
List QA utilities used (validation, comparison, sampling).

Write the documentation to {site_path}/SCRAPER_DOCUMENTATION.md"""


def generate_scraper_doc(
    site_name: str, repo_root: Path, max_retries: int = 2
) -> tuple[str, str, str, float]:
    """Generate documentation for a single scraper site.

    Args:
        site_name: Name of the audiobee_* directory
        repo_root: Path to the repository root
        max_retries: Number of retries on failure

    Returns:
        Tuple of (site_name, status, message, elapsed_seconds)
        status is one of: 'completed', 'skipped', 'failed'
    """
    start_time = time.time()
    site_path = repo_root / site_name
    doc_path = site_path / "SCRAPER_DOCUMENTATION.md"

    # Skip if documentation already exists
    if doc_path.exists():
        return (site_name, "skipped", "Documentation already exists", 0.0)

    # Skip if directory doesn't exist
    if not site_path.exists():
        return (site_name, "failed", "Directory not found", 0.0)

    # Count files in directory for context
    py_files = list(site_path.glob("*.py"))
    config_files = list(site_path.glob("config.*"))
    logger.info(f"🚀 STARTING {site_name} ({len(py_files)} .py files, {len(config_files)} config files)")

    prompt = SCRAPER_DOC_PROMPT.format(site_path=site_path)

    for attempt in range(max_retries + 1):
        attempt_start = time.time()
        if attempt > 0:
            logger.warning(f"🔄 RETRY {attempt}/{max_retries} for {site_name}")

        try:
            logger.debug(f"📝 Invoking Claude CLI for {site_name} (attempt {attempt + 1})")
            result = subprocess.run(
                ["claude", "-p", prompt, "--max-turns", "5"],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout per site
                cwd=str(repo_root),
            )
            attempt_elapsed = time.time() - attempt_start

            if result.returncode == 0:
                # Check if documentation was created
                if doc_path.exists():
                    doc_size = doc_path.stat().st_size
                    total_elapsed = time.time() - start_time
                    logger.success(
                        f"✅ COMPLETED {site_name} in {total_elapsed:.1f}s "
                        f"(doc size: {doc_size / 1024:.1f}KB)"
                    )
                    return (site_name, "completed", f"Generated ({doc_size / 1024:.1f}KB)", total_elapsed)
                else:
                    # Claude completed but didn't write the file
                    logger.error(f"❌ {site_name}: Claude finished but no file created")
                    if attempt < max_retries:
                        continue
                    return (site_name, "failed", "Claude completed but file not created", time.time() - start_time)
            else:
                error_msg = result.stderr[:200] if result.stderr else "Unknown error"
                logger.error(f"❌ {site_name}: Claude error after {attempt_elapsed:.1f}s - {error_msg}")
                if attempt < max_retries:
                    time.sleep(2)  # Brief pause before retry
                    continue
                return (site_name, "failed", f"Claude error: {error_msg}", time.time() - start_time)

        except subprocess.TimeoutExpired:
            logger.error(f"⏰ TIMEOUT {site_name} after 5 minutes (attempt {attempt + 1})")
            if attempt < max_retries:
                continue
            return (site_name, "failed", "Timeout after 5 minutes", time.time() - start_time)
        except FileNotFoundError:
            logger.critical(f"🚫 Claude CLI not found!")
            return (site_name, "failed", "Claude CLI not found", time.time() - start_time)
        except Exception as e:
            logger.error(f"💥 EXCEPTION {site_name}: {type(e).__name__}: {str(e)[:100]}")
            if attempt < max_retries:
                continue
            return (site_name, "failed", f"Exception: {str(e)[:200]}", time.time() - start_time)

    return (site_name, "failed", "Max retries exceeded", time.time() - start_time)


def update_progress(status: str, site_name: str, message: str, elapsed: float = 0.0) -> None:
    """Update and log progress in a thread-safe manner."""
    with _progress_lock:
        _progress[status] += 1
        _progress["total_time"] += elapsed
        completed = _progress["completed"]
        failed = _progress["failed"]
        skipped = _progress["skipped"]
        total = _progress["total"]
        processed = completed + failed + skipped

        # Calculate progress percentage
        pct = (processed / total * 100) if total > 0 else 0

        # Progress bar
        bar_width = 20
        filled = int(bar_width * processed / total) if total > 0 else 0
        bar = "█" * filled + "░" * (bar_width - filled)

        status_icon = {"completed": "✅", "failed": "❌", "skipped": "⏭️"}[status]
        elapsed_str = f" ({elapsed:.1f}s)" if elapsed > 0 else ""

        logger.info(
            f"[{bar}] {pct:5.1f}% ({processed}/{total}) | "
            f"{status_icon} {site_name}{elapsed_str}"
        )

        # Log running totals every 10 completions
        if processed % 10 == 0 and processed > 0:
            avg_time = _progress["total_time"] / completed if completed > 0 else 0
            logger.info(
                f"📊 Progress: {completed} completed, {failed} failed, {skipped} skipped | "
                f"Avg time: {avg_time:.1f}s/site"
            )


@app.command("scrapers")
def generate_all_scraper_docs(
    workers: Annotated[int, typer.Option("--workers", "-w", help="Number of parallel workers")] = 4,
    sites_file: Annotated[
        Path | None, typer.Option("--sites", "-s", help="Path to sites.txt file")
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show what would be done without executing")
    ] = False,
) -> None:
    """Generate SCRAPER_DOCUMENTATION.md for all audiobee_* sites in parallel.

    Uses Claude Code CLI to analyze each scraper and generate comprehensive documentation.
    Skips sites that already have SCRAPER_DOCUMENTATION.md.

    Example:
        python scripts/generate_docs.py scrapers --workers 4
        python scripts/generate_docs.py scrapers --dry-run
    """
    global _progress

    # Determine sites file path
    if sites_file is None:
        sites_file = REPO_ROOT / "scripts" / "sites.txt"

    if not sites_file.exists():
        typer.echo(f"Error: Sites file not found: {sites_file}", err=True)
        typer.echo(
            "Create it with: ls -d audiobee_*/ | sed 's/\\/$//' > scripts/sites.txt", err=True
        )
        raise typer.Exit(1)

    # Read sites from file
    sites = [line.strip() for line in sites_file.read_text().splitlines() if line.strip()]

    if not sites:
        typer.echo("Error: No sites found in sites.txt", err=True)
        raise typer.Exit(1)

    # Check which sites need documentation
    sites_to_process = []
    sites_to_skip = []

    for site in sites:
        doc_path = REPO_ROOT / site / "SCRAPER_DOCUMENTATION.md"
        if doc_path.exists():
            sites_to_skip.append(site)
        elif not (REPO_ROOT / site).exists():
            logger.warning(f"Directory not found: {site}")
        else:
            sites_to_process.append(site)

    typer.echo(f"\n{'=' * 60}")
    typer.echo("Scraper Documentation Generator")
    typer.echo(f"{'=' * 60}")
    typer.echo(f"Total sites: {len(sites)}")
    typer.echo(f"Already documented: {len(sites_to_skip)}")
    typer.echo(f"To process: {len(sites_to_process)}")
    typer.echo(f"Workers: {workers}")
    typer.echo(f"{'=' * 60}\n")

    if dry_run:
        typer.echo("DRY RUN - Sites that would be processed:")
        for site in sites_to_process:
            typer.echo(f"  - {site}")
        typer.echo("\nSites that would be skipped (already documented):")
        for site in sites_to_skip[:10]:
            typer.echo(f"  - {site}")
        if len(sites_to_skip) > 10:
            typer.echo(f"  ... and {len(sites_to_skip) - 10} more")
        return

    if not sites_to_process:
        typer.echo("All sites already have documentation. Nothing to do.")
        return

    # Reset progress
    _progress = {"completed": 0, "failed": 0, "skipped": 0, "total": len(sites_to_process), "total_time": 0.0}

    # Process sites in parallel
    results = {"completed": [], "failed": [], "skipped": []}

    overall_start = time.time()
    logger.info(f"🏁 Starting documentation generation for {len(sites_to_process)} sites with {workers} workers")
    logger.info(f"📋 Sites queue: {', '.join(sites_to_process[:5])}{'...' if len(sites_to_process) > 5 else ''}")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(generate_scraper_doc, site, REPO_ROOT): site
            for site in sites_to_process
        }
        logger.info(f"📤 Submitted {len(futures)} tasks to thread pool")

        for future in as_completed(futures):
            site_name, status, message, elapsed = future.result()
            results[status].append((site_name, message, elapsed))
            update_progress(status, site_name, message, elapsed)

    overall_elapsed = time.time() - overall_start

    # Summary
    typer.echo(f"\n{'=' * 60}")
    typer.echo("📊 SUMMARY")
    typer.echo(f"{'=' * 60}")
    typer.echo(f"✅ Completed: {len(results['completed'])}")
    typer.echo(f"❌ Failed: {len(results['failed'])}")
    typer.echo(f"⏭️  Skipped: {len(results['skipped'])}")
    typer.echo(f"⏱️  Total time: {overall_elapsed:.1f}s ({overall_elapsed / 60:.1f} minutes)")

    if results["completed"]:
        avg_time = sum(r[2] for r in results["completed"]) / len(results["completed"])
        typer.echo(f"📈 Average time per site: {avg_time:.1f}s")

    if results["failed"]:
        typer.echo(f"\n{'=' * 60}")
        typer.echo("❌ FAILED SITES:")
        typer.echo(f"{'=' * 60}")
        for site, message, elapsed in results["failed"]:
            typer.echo(f"  • {site}: {message}")

    if results["completed"]:
        typer.echo(f"\n{'=' * 60}")
        typer.echo("✅ COMPLETED SITES:")
        typer.echo(f"{'=' * 60}")
        for site, message, elapsed in sorted(results["completed"], key=lambda x: x[2], reverse=True)[:10]:
            typer.echo(f"  • {site}: {message}")
        if len(results["completed"]) > 10:
            typer.echo(f"  ... and {len(results['completed']) - 10} more")


if __name__ == "__main__":
    app()

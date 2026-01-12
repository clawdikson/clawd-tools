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
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
import yaml

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
    include_private: Annotated[bool, typer.Option("--private", help="Include private members")] = False,
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
            context_parts.append(f"Functions: {', '.join(f.split(':')[0] for f in module.functions)}")
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

Output ONLY the Markdown content, no explanations or preamble."""

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
        typer.echo(f"Error: Platform must be 'healthsparq' or 'sapphire'", err=True)
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
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output file (default: README.md in project)")] = None,
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
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output file (default: CLAUDE.md in project)")] = None,
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
        context_parts.append(f"Type: Python package")
        context_parts.append(f"Modules: {len(structure.modules)}")
        context_parts.append(f"Subpackages: {', '.join(structure.subpackages)}")
    else:
        context_parts.append(f"Type: Project directory")

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


if __name__ == "__main__":
    app()

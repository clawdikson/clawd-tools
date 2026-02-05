"""
Project configuration loader for upload_to_drive.

Supports:
- Audiobee projects: Load CURR_DATE from config.py
- HealthSparq projects: Load metadata from healthsparq/configs/{project}.yaml
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import NamedTuple

try:
    from core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class ProjectConfig(NamedTuple):
    """Project configuration for upload."""

    name: str
    project_type: str  # "audiobee" or "healthsparq"
    curr_date: str | None
    base_path: Path


def detect_project_type(project_name: str, base_dir: Path = Path(".")) -> str:
    """Detect whether project is Audiobee (config.py) or HealthSparq (YAML).

    Args:
        project_name: Project name (e.g., "audiobee_bcbs_il" or "christus_health_plan")
        base_dir: Base directory to search from

    Returns:
        "audiobee" or "healthsparq"

    Raises:
        FileNotFoundError: If project config not found
    """
    # Check for Audiobee config.py
    audiobee_config = base_dir / project_name / "config.py"
    if audiobee_config.exists():
        return "audiobee"

    # Check for HealthSparq YAML config
    healthsparq_config = base_dir / "healthsparq" / "configs" / f"{project_name}.yaml"
    if healthsparq_config.exists():
        return "healthsparq"

    raise FileNotFoundError(
        f"Project '{project_name}' not found. Checked:\n"
        f"  - {audiobee_config}\n"
        f"  - {healthsparq_config}\n"
        "Ensure project name is correct."
    )


def extract_curr_date_from_config_py(config_path: Path) -> str:
    """Extract CURR_DATE from config.py using AST parsing.

    Args:
        config_path: Path to config.py file

    Returns:
        CURR_DATE value as string (e.g., "20251110")

    Raises:
        ValueError: If CURR_DATE not found or has invalid format
    """
    with open(config_path) as f:
        source = f.read()

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        raise ValueError(f"Syntax error in {config_path}: {e}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "CURR_DATE":
                    if isinstance(node.value, ast.Constant):
                        value = str(node.value.value)
                        # Validate date format (YYYYMMDD)
                        if len(value) == 8 and value.isdigit():
                            return value
                        raise ValueError(
                            f"CURR_DATE '{value}' in {config_path} is not YYYYMMDD format"
                        )

    raise ValueError(f"CURR_DATE not found in {config_path}")


def load_project_config(
    project_name: str,
    date_override: str | None = None,
    base_dir: Path = Path("."),
) -> ProjectConfig:
    """Load project configuration for upload.

    Args:
        project_name: Project name
        date_override: Optional date to use instead of config value
        base_dir: Base directory

    Returns:
        ProjectConfig with name, type, date, and path

    Raises:
        FileNotFoundError: If project not found
        ValueError: If date invalid or required but missing
    """
    project_type = detect_project_type(project_name, base_dir)
    curr_date = date_override

    if project_type == "audiobee":
        base_path = base_dir / project_name
        if not curr_date:
            config_path = base_path / "config.py"
            curr_date = extract_curr_date_from_config_py(config_path)
            logger.info(f"Loaded CURR_DATE={curr_date} from {config_path}")

    elif project_type == "healthsparq":
        # HealthSparq projects: output goes to healthsparq/{project_slug}/{date}/
        # or project-specific directory if it exists
        project_dir = base_dir / project_name
        base_path = project_dir if project_dir.exists() else base_dir / "healthsparq" / project_name

        if not curr_date:
            # Try to find latest date directory
            possible_dates = []
            if base_path.exists():
                for subdir in base_path.iterdir():
                    if subdir.is_dir() and len(subdir.name) == 8 and subdir.name.isdigit():
                        possible_dates.append(subdir.name)

            if possible_dates:
                curr_date = sorted(possible_dates)[-1]  # Latest date
                logger.info(f"Auto-detected CURR_DATE={curr_date} from {base_path}")
            else:
                raise ValueError(
                    f"HealthSparq project '{project_name}' requires --date argument. "
                    f"No date directories found in {base_path}."
                )

    # Validate date format
    if curr_date and (len(curr_date) != 8 or not curr_date.isdigit()):
        raise ValueError(f"Date '{curr_date}' must be YYYYMMDD format (e.g., 20251227)")

    return ProjectConfig(
        name=project_name,
        project_type=project_type,
        curr_date=curr_date,
        base_path=base_path,
    )

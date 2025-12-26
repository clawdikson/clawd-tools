"""
HealthSparq Configuration Loader.

Loads and validates project configurations from YAML files.
"""

from pathlib import Path
from typing import Any, Optional

import yaml

from .schema import HealthSparqProjectConfig


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries.

    Values in override take precedence over values in base.
    Nested dictionaries are merged recursively.
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(
    project_slug: str, config_dir: Optional[Path] = None
) -> HealthSparqProjectConfig:
    """Load and validate project configuration.

    Args:
        project_slug: The project slug (e.g., 'christus_health_plan')
        config_dir: Optional path to config directory. Defaults to healthsparq/configs/

    Returns:
        HealthSparqProjectConfig: Validated project configuration

    Raises:
        FileNotFoundError: If project config file doesn't exist
        ValidationError: If configuration fails Pydantic validation
    """
    if config_dir is None:
        config_dir = Path(__file__).parent.parent / "configs"

    # Load base config
    base_path = config_dir / "_base.yaml"
    base_config: dict[str, Any] = {}
    if base_path.exists():
        with open(base_path, encoding="utf-8") as f:
            base_config = yaml.safe_load(f) or {}

    # Load project config
    project_path = config_dir / f"{project_slug}.yaml"
    if not project_path.exists():
        raise FileNotFoundError(f"Config not found: {project_path}")

    with open(project_path, encoding="utf-8") as f:
        project_config = yaml.safe_load(f)

    # Merge configs (project overrides base)
    merged = deep_merge(base_config, project_config)

    # Inherit site-level auth codes to plans if not specified
    site = merged.get("site", {})
    site_insurer = site.get("insurer_code")
    site_brand = site.get("brand_code")
    for plan in merged.get("plans", []):
        if plan.get("insurer_code") is None:
            plan["insurer_code"] = site_insurer
        if plan.get("brand_code") is None:
            plan["brand_code"] = site_brand

    # Validate with Pydantic
    return HealthSparqProjectConfig(**merged)


def list_projects(config_dir: Optional[Path] = None) -> list[str]:
    """List all available project slugs.

    Args:
        config_dir: Optional path to config directory. Defaults to healthsparq/configs/

    Returns:
        List of project slugs (config file names without .yaml extension)
    """
    if config_dir is None:
        config_dir = Path(__file__).parent.parent / "configs"

    return sorted(
        p.stem for p in config_dir.glob("*.yaml") if not p.name.startswith("_")
    )

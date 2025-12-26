"""
HealthSparq Configuration Module.

Contains configuration loading and schema validation:
- load_config: Load project configuration by name
- list_projects: List all available project slugs
- HealthSparqProjectConfig: Main Pydantic configuration schema
"""

from .loader import list_projects, load_config
from .schema import HealthSparqProjectConfig

__all__ = [
    "load_config",
    "list_projects",
    "HealthSparqProjectConfig",
]

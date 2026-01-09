"""Sapphire mapper registry and utilities."""

from typing import Callable, Dict

# MapperFunc type: takes raw dict, returns normalized dict
MapperFunc = Callable[[dict], dict]

# Registry of custom mappers by project slug
_MAPPER_REGISTRY: Dict[str, MapperFunc] = {}


def register_mapper(project_slug: str, mapper: MapperFunc) -> None:
    """Register a custom mapper for a project.

    Args:
        project_slug: Project identifier (e.g., "bcbs_mn")
        mapper: Mapper function to register
    """
    _MAPPER_REGISTRY[project_slug] = mapper


def get_mapper(project_slug: str) -> MapperFunc | None:
    """Get the registered mapper for a project.

    Args:
        project_slug: Project identifier

    Returns:
        Registered mapper or None if not found
    """
    return _MAPPER_REGISTRY.get(project_slug)


__all__ = ["MapperFunc", "register_mapper", "get_mapper"]

"""Dashboard services layer.

Provides business logic for:
- Project discovery and registry
- Validation of environment and security
- Cross-terminal state management
"""

from tools.dashboard.services.registry import Project, ProjectRegistry
from tools.dashboard.services.state import SharedState
from tools.dashboard.services.validator import SecurityIssue, ValidationResult, Validator

__all__ = [
    "Project",
    "ProjectRegistry",
    "SharedState",
    "SecurityIssue",
    "ValidationResult",
    "Validator",
]

"""Project registry service for discovering and managing scraper projects.

Scans the repository for audiobee_* directories and extracts metadata
about each project including platform type, last run date, and status.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Project:
    """Represents a scraper project.

    Attributes:
        name: Project directory name (e.g., audiobee_bcbs_il)
        path: Full path to project directory
        platform: Platform type (healthsparq, sapphire, standalone)
        last_run: Latest run date in YYYYMMDD format, or None if never run
        has_env: Whether project has a .env file
        status: Project health status (healthy, warning, error)
    """

    name: str
    path: Path
    platform: str
    last_run: str | None
    has_env: bool
    status: str


class ProjectRegistry:
    """Service for discovering and managing scraper projects.

    Scans for audiobee_* directories and extracts project metadata.
    Supports filtering by platform and caching for performance.

    Attributes:
        root_path: Root directory to scan for projects

    Example:
        >>> registry = ProjectRegistry(Path("/path/to/scraping"))
        >>> projects = registry.discover_projects()
        >>> healthsparq_projects = registry.get_projects_by_platform("healthsparq")
    """

    # Pattern to match YYYYMMDD directories
    DATE_PATTERN = re.compile(r"^\d{8}$")

    def __init__(self, root_path: Path | None = None):
        """Initialize the registry.

        Args:
            root_path: Root directory to scan. Defaults to current directory.
        """
        self.root_path = root_path or Path.cwd()
        self._projects: list[Project] | None = None

    def discover_projects(self) -> list[Project]:
        """Discover all audiobee_* projects in root directory.

        Returns:
            List of Project objects found in root_path
        """
        if self._projects is not None:
            return self._projects

        projects = []
        for item in self.root_path.iterdir():
            if not item.is_dir():
                continue
            if not item.name.startswith("audiobee_"):
                continue

            project = self._create_project(item)
            projects.append(project)

        self._projects = sorted(projects, key=lambda p: p.name)
        return self._projects

    def _create_project(self, project_path: Path) -> Project:
        """Create a Project object from a directory.

        Args:
            project_path: Path to project directory

        Returns:
            Project object with extracted metadata
        """
        platform = self._detect_platform(project_path)
        last_run = self._get_latest_run(project_path)
        has_env = self._has_env(project_path)
        status = self._determine_status(has_env, last_run, project_path)

        return Project(
            name=project_path.name,
            path=project_path,
            platform=platform,
            last_run=last_run,
            has_env=has_env,
            status=status,
        )

    # Cache for platform configs (class-level)
    _healthsparq_projects: set[str] | None = None
    _sapphire_projects: set[str] | None = None

    def _detect_platform(self, project_path: Path) -> str:
        """Detect platform type for a project.

        Detection order:
        1. Check for .healthsparq or .sapphire marker files
        2. Check SCRAPER_SITE_TYPE in .env file
        3. Check if project has config in healthsparq/configs/ or sapphire/configs/
        4. Default to standalone

        Args:
            project_path: Path to project directory

        Returns:
            Platform type string (healthsparq, sapphire, or standalone)
        """
        # Check for marker files
        if (project_path / ".healthsparq").exists():
            return "healthsparq"
        if (project_path / ".sapphire").exists():
            return "sapphire"

        # Check .env file for SCRAPER_SITE_TYPE
        env_file = project_path / ".env"
        if env_file.exists():
            try:
                content = env_file.read_text()
                for line in content.splitlines():
                    if line.startswith("SCRAPER_SITE_TYPE="):
                        site_type = line.split("=", 1)[1].strip().strip("'\"")
                        if site_type in ("healthsparq", "sapphire"):
                            return site_type
            except Exception:
                pass

        # Check for config files in platform libraries
        # Project name: audiobee_<config_name> -> config_name.yaml
        project_name = project_path.name
        if project_name.startswith("audiobee_"):
            config_name = project_name[9:]  # Remove "audiobee_" prefix

            # Load platform project sets if not cached
            if self._healthsparq_projects is None:
                self._load_platform_configs()

            if config_name in self._healthsparq_projects:
                return "healthsparq"
            if config_name in self._sapphire_projects:
                return "sapphire"

        return "standalone"

    def _load_platform_configs(self) -> None:
        """Load project names from platform config directories."""
        ProjectRegistry._healthsparq_projects = set()
        ProjectRegistry._sapphire_projects = set()

        # Load healthsparq configs
        hs_configs = self.root_path / "healthsparq" / "configs"
        if hs_configs.exists():
            for config_file in hs_configs.glob("*.yaml"):
                name = config_file.stem
                if not name.startswith("_"):  # Skip _base.yaml
                    ProjectRegistry._healthsparq_projects.add(name)

        # Load sapphire configs
        sp_configs = self.root_path / "sapphire" / "configs"
        if sp_configs.exists():
            for config_file in sp_configs.glob("*.yaml"):
                name = config_file.stem
                if not name.startswith("_"):
                    ProjectRegistry._sapphire_projects.add(name)

    def _get_latest_run(self, project_path: Path) -> str | None:
        """Find the latest run date directory.

        Looks for directories matching YYYYMMDD pattern and returns
        the most recent one.

        Args:
            project_path: Path to project directory

        Returns:
            Latest date string (YYYYMMDD) or None if no runs found
        """
        dates = []
        for item in project_path.iterdir():
            if item.is_dir() and self.DATE_PATTERN.match(item.name):
                dates.append(item.name)

        if not dates:
            return None

        return max(dates)

    def _has_env(self, project_path: Path) -> bool:
        """Check if project has a .env file.

        Args:
            project_path: Path to project directory

        Returns:
            True if .env file exists, False otherwise
        """
        return (project_path / ".env").exists()

    def _determine_status(
        self,
        has_env: bool,
        last_run: str | None,
        project_path: Path,
    ) -> str:
        """Determine project health status.

        Status rules:
        - healthy: Has .env and has been run
        - warning: Missing .env or never run
        - error: Has critical issues (not yet implemented)

        Args:
            has_env: Whether project has .env file
            last_run: Latest run date or None
            project_path: Path to project directory

        Returns:
            Status string (healthy, warning, or error)
        """
        if not has_env:
            return "warning"
        if last_run is None:
            return "warning"
        return "healthy"

    def get_projects_by_platform(self, platform: str) -> list[Project]:
        """Filter projects by platform type.

        Args:
            platform: Platform type (healthsparq, sapphire, standalone)

        Returns:
            List of projects matching the platform
        """
        projects = self.discover_projects()
        return [p for p in projects if p.platform == platform]

    def get_project_count(self) -> int:
        """Get total number of discovered projects.

        Returns:
            Number of projects
        """
        return len(self.discover_projects())

    def get_project_by_name(self, name: str) -> Project | None:
        """Find a project by name.

        Args:
            name: Project directory name

        Returns:
            Project object or None if not found
        """
        projects = self.discover_projects()
        for project in projects:
            if project.name == name:
                return project
        return None

    def refresh(self) -> None:
        """Clear cache and re-discover projects."""
        self._projects = None
        self.discover_projects()

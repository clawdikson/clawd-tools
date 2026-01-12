"""Tests for dashboard registry service - project discovery.

TDD tests written before implementation.
"""

import tempfile
from pathlib import Path

import pytest


class TestProject:
    """Tests for Project dataclass."""

    def test_project_has_required_fields(self):
        """Project should have name, path, platform, last_run, has_env, status."""
        from tools.dashboard.services.registry import Project

        project = Project(
            name="audiobee_test",
            path=Path("/tmp/test"),
            platform="healthsparq",
            last_run="20260110",
            has_env=True,
            status="healthy",
        )

        assert project.name == "audiobee_test"
        assert project.path == Path("/tmp/test")
        assert project.platform == "healthsparq"
        assert project.last_run == "20260110"
        assert project.has_env is True
        assert project.status == "healthy"

    def test_project_optional_last_run(self):
        """last_run should be optional (None for never run)."""
        from tools.dashboard.services.registry import Project

        project = Project(
            name="audiobee_new",
            path=Path("/tmp/test"),
            platform="standalone",
            last_run=None,
            has_env=False,
            status="warning",
        )

        assert project.last_run is None

    def test_project_status_values(self):
        """status should accept healthy, warning, error."""
        from tools.dashboard.services.registry import Project

        for status in ["healthy", "warning", "error"]:
            project = Project(
                name="test",
                path=Path("/tmp"),
                platform="standalone",
                last_run=None,
                has_env=False,
                status=status,
            )
            assert project.status == status


class TestProjectRegistry:
    """Tests for ProjectRegistry service."""

    def test_registry_init(self, tmp_path: Path):
        """Registry should initialize with a root path."""
        from tools.dashboard.services.registry import ProjectRegistry

        registry = ProjectRegistry(root_path=tmp_path)
        assert registry.root_path == tmp_path

    def test_discover_projects_empty_directory(self, tmp_path: Path):
        """Empty directory should return empty list."""
        from tools.dashboard.services.registry import ProjectRegistry

        registry = ProjectRegistry(root_path=tmp_path)
        projects = registry.discover_projects()

        assert projects == []

    def test_discover_projects_finds_audiobee_directories(self, tmp_path: Path):
        """Should find directories starting with audiobee_."""
        from tools.dashboard.services.registry import ProjectRegistry

        # Create audiobee_ directories
        (tmp_path / "audiobee_test1").mkdir()
        (tmp_path / "audiobee_test2").mkdir()
        (tmp_path / "not_a_project").mkdir()

        registry = ProjectRegistry(root_path=tmp_path)
        projects = registry.discover_projects()

        assert len(projects) == 2
        names = {p.name for p in projects}
        assert names == {"audiobee_test1", "audiobee_test2"}

    def test_detect_platform_healthsparq(self, tmp_path: Path):
        """Should detect healthsparq platform from config file."""
        from tools.dashboard.services.registry import ProjectRegistry

        project_dir = tmp_path / "audiobee_hsq"
        project_dir.mkdir()
        # HealthSparq projects have a config.yaml or use healthsparq.configs
        # We'll check for healthsparq-specific markers
        (project_dir / ".healthsparq").touch()  # Marker file

        registry = ProjectRegistry(root_path=tmp_path)
        platform = registry._detect_platform(project_dir)

        assert platform == "healthsparq"

    def test_detect_platform_sapphire(self, tmp_path: Path):
        """Should detect sapphire platform from config file."""
        from tools.dashboard.services.registry import ProjectRegistry

        project_dir = tmp_path / "audiobee_saph"
        project_dir.mkdir()
        (project_dir / ".sapphire").touch()  # Marker file

        registry = ProjectRegistry(root_path=tmp_path)
        platform = registry._detect_platform(project_dir)

        assert platform == "sapphire"

    def test_detect_platform_standalone(self, tmp_path: Path):
        """Should detect standalone platform when no markers present."""
        from tools.dashboard.services.registry import ProjectRegistry

        project_dir = tmp_path / "audiobee_custom"
        project_dir.mkdir()

        registry = ProjectRegistry(root_path=tmp_path)
        platform = registry._detect_platform(project_dir)

        assert platform == "standalone"

    def test_detect_platform_from_env_file(self, tmp_path: Path):
        """Should detect platform from SCRAPER_SITE_TYPE in .env file."""
        from tools.dashboard.services.registry import ProjectRegistry

        project_dir = tmp_path / "audiobee_env_test"
        project_dir.mkdir()
        env_file = project_dir / ".env"
        env_file.write_text("SCRAPER_SITE_TYPE=healthsparq\nOTHER_VAR=value")

        registry = ProjectRegistry(root_path=tmp_path)
        platform = registry._detect_platform(project_dir)

        assert platform == "healthsparq"

    def test_get_latest_run_date(self, tmp_path: Path):
        """Should find latest YYYYMMDD directory."""
        from tools.dashboard.services.registry import ProjectRegistry

        project_dir = tmp_path / "audiobee_dated"
        project_dir.mkdir()
        (project_dir / "20260108").mkdir()
        (project_dir / "20260110").mkdir()
        (project_dir / "20260105").mkdir()
        (project_dir / "not_a_date").mkdir()

        registry = ProjectRegistry(root_path=tmp_path)
        latest = registry._get_latest_run(project_dir)

        assert latest == "20260110"

    def test_get_latest_run_no_dates(self, tmp_path: Path):
        """Should return None when no date directories exist."""
        from tools.dashboard.services.registry import ProjectRegistry

        project_dir = tmp_path / "audiobee_no_dates"
        project_dir.mkdir()
        (project_dir / "config").mkdir()
        (project_dir / "src").mkdir()

        registry = ProjectRegistry(root_path=tmp_path)
        latest = registry._get_latest_run(project_dir)

        assert latest is None

    def test_check_env_file(self, tmp_path: Path):
        """Should detect presence of .env file."""
        from tools.dashboard.services.registry import ProjectRegistry

        project_with_env = tmp_path / "audiobee_with_env"
        project_with_env.mkdir()
        (project_with_env / ".env").touch()

        project_without_env = tmp_path / "audiobee_no_env"
        project_without_env.mkdir()

        registry = ProjectRegistry(root_path=tmp_path)

        assert registry._has_env(project_with_env) is True
        assert registry._has_env(project_without_env) is False

    def test_determine_status_healthy(self, tmp_path: Path):
        """Project with env and recent run should be healthy."""
        from tools.dashboard.services.registry import ProjectRegistry

        project_dir = tmp_path / "audiobee_healthy"
        project_dir.mkdir()
        (project_dir / ".env").touch()
        (project_dir / "20260110").mkdir()

        registry = ProjectRegistry(root_path=tmp_path)
        status = registry._determine_status(
            has_env=True,
            last_run="20260110",
            project_path=project_dir,
        )

        assert status == "healthy"

    def test_determine_status_warning_no_env(self, tmp_path: Path):
        """Project without env should be warning."""
        from tools.dashboard.services.registry import ProjectRegistry

        registry = ProjectRegistry(root_path=tmp_path)
        status = registry._determine_status(
            has_env=False,
            last_run="20260110",
            project_path=tmp_path,
        )

        assert status == "warning"

    def test_determine_status_warning_never_run(self, tmp_path: Path):
        """Project never run should be warning."""
        from tools.dashboard.services.registry import ProjectRegistry

        registry = ProjectRegistry(root_path=tmp_path)
        status = registry._determine_status(
            has_env=True,
            last_run=None,
            project_path=tmp_path,
        )

        assert status == "warning"

    def test_get_projects_by_platform(self, tmp_path: Path):
        """Should filter projects by platform."""
        from tools.dashboard.services.registry import ProjectRegistry

        # Create projects with different platforms
        hsq_dir = tmp_path / "audiobee_hsq"
        hsq_dir.mkdir()
        (hsq_dir / ".healthsparq").touch()

        saph_dir = tmp_path / "audiobee_saph"
        saph_dir.mkdir()
        (saph_dir / ".sapphire").touch()

        standalone_dir = tmp_path / "audiobee_custom"
        standalone_dir.mkdir()

        registry = ProjectRegistry(root_path=tmp_path)

        hsq_projects = registry.get_projects_by_platform("healthsparq")
        assert len(hsq_projects) == 1
        assert hsq_projects[0].name == "audiobee_hsq"

        saph_projects = registry.get_projects_by_platform("sapphire")
        assert len(saph_projects) == 1
        assert saph_projects[0].name == "audiobee_saph"

    def test_get_project_count(self, tmp_path: Path):
        """Should return count of projects."""
        from tools.dashboard.services.registry import ProjectRegistry

        (tmp_path / "audiobee_a").mkdir()
        (tmp_path / "audiobee_b").mkdir()
        (tmp_path / "audiobee_c").mkdir()

        registry = ProjectRegistry(root_path=tmp_path)

        assert registry.get_project_count() == 3

    def test_get_project_by_name(self, tmp_path: Path):
        """Should find project by name."""
        from tools.dashboard.services.registry import ProjectRegistry

        (tmp_path / "audiobee_target").mkdir()
        (tmp_path / "audiobee_other").mkdir()

        registry = ProjectRegistry(root_path=tmp_path)
        project = registry.get_project_by_name("audiobee_target")

        assert project is not None
        assert project.name == "audiobee_target"

    def test_get_project_by_name_not_found(self, tmp_path: Path):
        """Should return None for non-existent project."""
        from tools.dashboard.services.registry import ProjectRegistry

        (tmp_path / "audiobee_exists").mkdir()

        registry = ProjectRegistry(root_path=tmp_path)
        project = registry.get_project_by_name("audiobee_not_exists")

        assert project is None

    def test_refresh_clears_cache(self, tmp_path: Path):
        """refresh() should re-discover projects."""
        from tools.dashboard.services.registry import ProjectRegistry

        (tmp_path / "audiobee_first").mkdir()

        registry = ProjectRegistry(root_path=tmp_path)
        assert registry.get_project_count() == 1

        # Add new project
        (tmp_path / "audiobee_second").mkdir()

        # Before refresh, should still be 1
        assert registry.get_project_count() == 1

        # After refresh, should be 2
        registry.refresh()
        assert registry.get_project_count() == 2

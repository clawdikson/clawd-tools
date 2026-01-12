"""Tests for project registry service.

Tests the platform detection fixes:
1. Detection via marker files (.healthsparq, .sapphire)
2. Detection via .env SCRAPER_SITE_TYPE
3. Detection via config files in healthsparq/configs/ and sapphire/configs/
4. Fallback to standalone when no platform detected
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.dashboard.services.registry import Project, ProjectRegistry


class TestPlatformDetection:
    """Test platform detection logic."""

    def test_detect_platform_via_marker_file(self, mock_project_structure: Path):
        """Test that .healthsparq marker file is detected."""
        registry = ProjectRegistry(root_path=mock_project_structure)
        project = registry.get_project_by_name("audiobee_test_marker")

        assert project is not None
        assert project.platform == "healthsparq"

    def test_detect_platform_via_env_file(self, mock_project_structure: Path):
        """Test that SCRAPER_SITE_TYPE in .env is detected."""
        registry = ProjectRegistry(root_path=mock_project_structure)
        project = registry.get_project_by_name("audiobee_test_env")

        assert project is not None
        assert project.platform == "sapphire"

    def test_detect_platform_via_healthsparq_config(self, mock_project_structure: Path):
        """Test detection via healthsparq/configs/*.yaml files."""
        registry = ProjectRegistry(root_path=mock_project_structure)
        project = registry.get_project_by_name("audiobee_test_hs")

        assert project is not None
        assert project.platform == "healthsparq"

    def test_detect_platform_via_sapphire_config(self, mock_project_structure: Path):
        """Test detection via sapphire/configs/*.yaml files."""
        registry = ProjectRegistry(root_path=mock_project_structure)
        project = registry.get_project_by_name("audiobee_test_sp")

        assert project is not None
        assert project.platform == "sapphire"

    def test_detect_standalone_fallback(self, mock_project_structure: Path):
        """Test fallback to standalone when no platform detected."""
        registry = ProjectRegistry(root_path=mock_project_structure)
        project = registry.get_project_by_name("audiobee_test_standalone")

        assert project is not None
        assert project.platform == "standalone"

    def test_base_config_ignored(self, mock_project_structure: Path):
        """Test that _base.yaml config files are ignored."""
        registry = ProjectRegistry(root_path=mock_project_structure)

        # _base should not be detected as a project config
        # (it's used for shared config, not per-project)
        project = registry.get_project_by_name("audiobee__base")
        assert project is None


class TestProjectDiscovery:
    """Test project discovery functionality."""

    def test_discover_only_audiobee_dirs(self, mock_project_structure: Path):
        """Test that only audiobee_* directories are discovered."""
        # Create a non-audiobee directory
        (mock_project_structure / "other_project").mkdir()
        (mock_project_structure / "healthsparq" / "some_file.py").touch()

        registry = ProjectRegistry(root_path=mock_project_structure)
        projects = registry.discover_projects()

        # Should only find audiobee_* directories
        names = [p.name for p in projects]
        assert all(n.startswith("audiobee_") for n in names)
        assert "other_project" not in names
        assert "healthsparq" not in names

    def test_projects_sorted_by_name(self, mock_project_structure: Path):
        """Test that projects are returned sorted by name."""
        registry = ProjectRegistry(root_path=mock_project_structure)
        projects = registry.discover_projects()

        names = [p.name for p in projects]
        assert names == sorted(names)

    def test_discover_caches_results(self, mock_project_structure: Path):
        """Test that discover_projects caches results."""
        registry = ProjectRegistry(root_path=mock_project_structure)

        projects1 = registry.discover_projects()
        projects2 = registry.discover_projects()

        # Should be the same list object (cached)
        assert projects1 is projects2

    def test_refresh_clears_cache(self, mock_project_structure: Path):
        """Test that refresh clears the cache."""
        registry = ProjectRegistry(root_path=mock_project_structure)

        projects1 = registry.discover_projects()
        registry.refresh()
        projects2 = registry.discover_projects()

        # Should be different list objects after refresh
        assert projects1 is not projects2
        # But same content
        assert [p.name for p in projects1] == [p.name for p in projects2]


class TestProjectMetadata:
    """Test project metadata extraction."""

    def test_project_has_env(self, mock_project_structure: Path):
        """Test detection of .env file presence."""
        registry = ProjectRegistry(root_path=mock_project_structure)

        # Project with .env
        project_env = registry.get_project_by_name("audiobee_test_env")
        assert project_env is not None
        assert project_env.has_env is True

        # Project without .env
        project_no_env = registry.get_project_by_name("audiobee_test_standalone")
        assert project_no_env is not None
        assert project_no_env.has_env is False

    def test_latest_run_detection(self, mock_run_structure: Path):
        """Test detection of latest run date."""
        # Create the audiobee project as expected by registry
        registry = ProjectRegistry(root_path=mock_run_structure)
        project = registry.get_project_by_name("audiobee_test")

        assert project is not None
        # Should find 20260111 as latest (newer than 20260110)
        assert project.last_run == "20260111"

    def test_status_healthy_with_env_and_run(self, mock_run_structure: Path):
        """Test healthy status when project has .env and runs."""
        project_dir = mock_run_structure / "audiobee_test"
        (project_dir / ".env").write_text("SCRAPER_SITE_TYPE=standalone\n")

        registry = ProjectRegistry(root_path=mock_run_structure)
        project = registry.get_project_by_name("audiobee_test")

        assert project is not None
        assert project.status == "healthy"

    def test_status_warning_without_env(self, mock_run_structure: Path):
        """Test warning status when project lacks .env."""
        registry = ProjectRegistry(root_path=mock_run_structure)
        project = registry.get_project_by_name("audiobee_test")

        assert project is not None
        # No .env file, so warning status
        assert project.status == "warning"

    def test_status_warning_without_runs(self, mock_project_structure: Path):
        """Test warning status when project has no runs."""
        registry = ProjectRegistry(root_path=mock_project_structure)
        project = registry.get_project_by_name("audiobee_test_env")

        assert project is not None
        # Has .env but no runs, so warning status
        assert project.status == "warning"


class TestProjectFiltering:
    """Test project filtering methods."""

    def test_get_projects_by_platform(self, mock_project_structure: Path):
        """Test filtering projects by platform."""
        registry = ProjectRegistry(root_path=mock_project_structure)

        # Get healthsparq projects
        hs_projects = registry.get_projects_by_platform("healthsparq")
        assert len(hs_projects) == 2  # test_hs and test_marker

        # Get sapphire projects
        sp_projects = registry.get_projects_by_platform("sapphire")
        assert len(sp_projects) == 2  # test_sp and test_env

        # Get standalone projects
        standalone = registry.get_projects_by_platform("standalone")
        assert len(standalone) == 1  # test_standalone

    def test_get_project_count(self, mock_project_structure: Path):
        """Test project count."""
        registry = ProjectRegistry(root_path=mock_project_structure)
        assert registry.get_project_count() == 5

    def test_get_project_by_name_not_found(self, mock_project_structure: Path):
        """Test get_project_by_name returns None for unknown project."""
        registry = ProjectRegistry(root_path=mock_project_structure)
        project = registry.get_project_by_name("nonexistent_project")
        assert project is None

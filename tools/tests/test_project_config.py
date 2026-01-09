"""Unit tests for project_config module."""
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.project_config import (
    detect_project_type,
    extract_curr_date_from_config_py,
    load_project_config,
)


class TestDetectProjectType:
    """Tests for detect_project_type function."""

    def test_audiobee_project_with_config_py(self, tmp_path):
        """Should detect audiobee project when config.py exists."""
        project_dir = tmp_path / "audiobee_test"
        project_dir.mkdir()
        (project_dir / "config.py").write_text('CURR_DATE = "20251227"')

        result = detect_project_type("audiobee_test", tmp_path)
        assert result == "audiobee"

    def test_healthsparq_project_with_yaml(self, tmp_path):
        """Should detect healthsparq project when YAML config exists."""
        configs_dir = tmp_path / "healthsparq" / "configs"
        configs_dir.mkdir(parents=True)
        (configs_dir / "test_project.yaml").write_text("project:\n  name: Test")

        result = detect_project_type("test_project", tmp_path)
        assert result == "healthsparq"

    def test_nonexistent_project_raises_error(self, tmp_path):
        """Should raise FileNotFoundError for unknown project."""
        with pytest.raises(FileNotFoundError, match="not found"):
            detect_project_type("nonexistent", tmp_path)

    def test_audiobee_takes_precedence_over_healthsparq(self, tmp_path):
        """Should prefer audiobee config.py over healthsparq YAML if both exist."""
        # Create both config.py and YAML
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        (project_dir / "config.py").write_text('CURR_DATE = "20251227"')

        configs_dir = tmp_path / "healthsparq" / "configs"
        configs_dir.mkdir(parents=True)
        (configs_dir / "test_project.yaml").write_text("project:\n  name: Test")

        result = detect_project_type("test_project", tmp_path)
        assert result == "audiobee"


class TestExtractCurrDate:
    """Tests for extract_curr_date_from_config_py function."""

    def test_extracts_valid_date(self, tmp_path):
        """Should extract CURR_DATE from config.py."""
        config_file = tmp_path / "config.py"
        config_file.write_text('PREV_DATE = "20251010"\nCURR_DATE = "20251227"\n')

        result = extract_curr_date_from_config_py(config_file)
        assert result == "20251227"

    def test_extracts_date_with_other_assignments(self, tmp_path):
        """Should extract CURR_DATE even with other complex assignments."""
        config_file = tmp_path / "config.py"
        config_file.write_text('''
import os

PREV_DATE = "20251010"
CURR_DATE = "20251227"
MAX_WORKERS = 25

DIRS = {
    "raw": os.path.join(CURR_DATE, "raw"),
}
''')

        result = extract_curr_date_from_config_py(config_file)
        assert result == "20251227"

    def test_raises_on_missing_curr_date(self, tmp_path):
        """Should raise ValueError if CURR_DATE not found."""
        config_file = tmp_path / "config.py"
        config_file.write_text('PREV_DATE = "20251010"\n')

        with pytest.raises(ValueError, match="not found"):
            extract_curr_date_from_config_py(config_file)

    def test_raises_on_invalid_date_format(self, tmp_path):
        """Should raise ValueError for non-YYYYMMDD format."""
        config_file = tmp_path / "config.py"
        config_file.write_text('CURR_DATE = "2025-12-27"\n')

        with pytest.raises(ValueError, match="not YYYYMMDD"):
            extract_curr_date_from_config_py(config_file)

    def test_raises_on_syntax_error(self, tmp_path):
        """Should raise ValueError for malformed config.py."""
        config_file = tmp_path / "config.py"
        config_file.write_text('CURR_DATE = "20251227\n')  # Missing closing quote

        with pytest.raises(ValueError, match="Syntax error"):
            extract_curr_date_from_config_py(config_file)

    def test_raises_on_empty_date(self, tmp_path):
        """Should raise ValueError for empty date."""
        config_file = tmp_path / "config.py"
        config_file.write_text('CURR_DATE = ""\n')

        with pytest.raises(ValueError, match="not YYYYMMDD"):
            extract_curr_date_from_config_py(config_file)

    def test_raises_on_non_numeric_date(self, tmp_path):
        """Should raise ValueError for non-numeric date."""
        config_file = tmp_path / "config.py"
        config_file.write_text('CURR_DATE = "abcdefgh"\n')

        with pytest.raises(ValueError, match="not YYYYMMDD"):
            extract_curr_date_from_config_py(config_file)


class TestLoadProjectConfig:
    """Tests for load_project_config function."""

    def test_loads_audiobee_config(self, tmp_path):
        """Should load config from audiobee project."""
        project_dir = tmp_path / "audiobee_test"
        project_dir.mkdir()
        (project_dir / "config.py").write_text('CURR_DATE = "20251227"')

        config = load_project_config("audiobee_test", base_dir=tmp_path)

        assert config.name == "audiobee_test"
        assert config.project_type == "audiobee"
        assert config.curr_date == "20251227"
        assert config.base_path == project_dir

    def test_date_override_takes_precedence(self, tmp_path):
        """Should use date_override instead of config.py value."""
        project_dir = tmp_path / "audiobee_test"
        project_dir.mkdir()
        (project_dir / "config.py").write_text('CURR_DATE = "20251110"')

        config = load_project_config(
            "audiobee_test",
            date_override="20251227",
            base_dir=tmp_path,
        )

        assert config.curr_date == "20251227"

    def test_validates_date_format(self, tmp_path):
        """Should reject invalid date format."""
        project_dir = tmp_path / "audiobee_test"
        project_dir.mkdir()
        (project_dir / "config.py").write_text('CURR_DATE = "20251227"')

        with pytest.raises(ValueError, match="YYYYMMDD"):
            load_project_config(
                "audiobee_test",
                date_override="2025-12-27",  # Invalid format
                base_dir=tmp_path,
            )

    def test_healthsparq_auto_detects_date_directory(self, tmp_path):
        """Should auto-detect date from directory for HealthSparq projects."""
        # Create healthsparq YAML config
        configs_dir = tmp_path / "healthsparq" / "configs"
        configs_dir.mkdir(parents=True)
        (configs_dir / "test_project.yaml").write_text("project:\n  name: Test")

        # Create project directory with date folders
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        (project_dir / "20251110").mkdir()
        (project_dir / "20251227").mkdir()

        config = load_project_config("test_project", base_dir=tmp_path)

        assert config.name == "test_project"
        assert config.project_type == "healthsparq"
        assert config.curr_date == "20251227"  # Latest date

    def test_healthsparq_requires_date_when_no_directories(self, tmp_path):
        """Should require --date when no date directories exist for HealthSparq."""
        # Create healthsparq YAML config only (no project directory)
        configs_dir = tmp_path / "healthsparq" / "configs"
        configs_dir.mkdir(parents=True)
        (configs_dir / "test_project.yaml").write_text("project:\n  name: Test")

        with pytest.raises(ValueError, match="requires --date"):
            load_project_config("test_project", base_dir=tmp_path)

    def test_project_not_found(self, tmp_path):
        """Should raise error for nonexistent project."""
        with pytest.raises(FileNotFoundError, match="not found"):
            load_project_config("nonexistent", base_dir=tmp_path)

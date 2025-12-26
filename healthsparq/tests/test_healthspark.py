"""Tests for HealthSpark core module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from healthsparq.config import load_config
from healthsparq.core import (
    HealthSpark,
    HealthSparkConfig,
    HealthSparqSession,
    SessionConfig,
    create_session,
    FileWriteWorker,
)


class TestHealthSparkConfig:
    """Test HealthSparkConfig dataclass."""

    def test_config_creation(self):
        """HealthSparkConfig creates with required fields."""
        config = HealthSparkConfig(
            domain="test.healthsparq.com",
            insurer_code="TEST_I",
            brand_code="TEST",
            product_code="MA",
        )
        assert config.domain == "test.healthsparq.com"
        assert config.insurer_code == "TEST_I"
        assert config.brand_code == "TEST"
        assert config.product_code == "MA"
        assert config.api_version == "v4"

    def test_config_urls(self):
        """HealthSparkConfig generates correct URLs."""
        config = HealthSparkConfig(
            domain="test.healthsparq.com",
            insurer_code="TEST_I",
            brand_code="TEST",
            product_code="MA",
        )
        assert config.base_url == "https://test.healthsparq.com/healthsparq/public/service"
        assert "insurerCode=TEST_I" in config.auth_url
        assert "brandCode=TEST" in config.auth_url
        assert "/v4/search" in config.search_url
        assert "/profile" in config.profile_url

    def test_from_project_config(self):
        """HealthSparkConfig creates from project config."""
        project_config = load_config("christus_health_plan")
        config = HealthSparkConfig.from_project_config(
            project_config,
            product_code="MA",
        )
        assert config.domain == "christushealthplan.healthsparq.com"
        assert config.insurer_code == "CHRISTUS_I"
        assert config.brand_code == "CHRISTUS"
        assert config.product_code == "MA"

    def test_no_hardcoded_values(self):
        """Config has no hardcoded domains or plan codes."""
        config = HealthSparkConfig(
            domain="custom.healthsparq.com",
            insurer_code="CUSTOM_I",
            brand_code="CUSTOM",
            product_code="CUSTOM_PLAN",
        )
        assert "custom" in config.domain.lower()
        assert config.insurer_code == "CUSTOM_I"
        assert config.brand_code == "CUSTOM"
        assert config.product_code == "CUSTOM_PLAN"


class TestHealthSpark:
    """Test HealthSpark API wrapper."""

    def test_healthspark_instantiates(self):
        """HealthSpark instantiates with config."""
        config = HealthSparkConfig(
            domain="test.healthsparq.com",
            insurer_code="TEST_I",
            brand_code="TEST",
            product_code="MA",
        )
        spark = HealthSpark(config)
        assert spark.config == config
        assert spark._session is None
        assert not spark._initialized

    def test_search_request_base(self):
        """HealthSpark builds correct search request base."""
        config = HealthSparkConfig(
            domain="test.healthsparq.com",
            insurer_code="TEST_I",
            brand_code="TEST",
            product_code="MA",
        )
        spark = HealthSpark(config)
        assert spark._search_request_base["productCode"] == "MA"
        assert spark._search_request_base["clientCode"] == "TEST"
        assert spark._search_request_base["languageCode"] == "EN"

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """HealthSpark works as async context manager."""
        config = HealthSparkConfig(
            domain="test.healthsparq.com",
            insurer_code="TEST_I",
            brand_code="TEST",
            product_code="MA",
        )
        async with HealthSpark(config) as spark:
            assert spark._initialized
            assert spark._session is not None
        assert spark._session is None


class TestSessionModule:
    """Test session module."""

    def test_session_config_defaults(self):
        """SessionConfig has sensible defaults."""
        config = SessionConfig()
        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.backoff_factor == 2.0

    def test_create_session(self):
        """create_session returns HealthSparqSession."""
        session = create_session()
        assert isinstance(session, HealthSparqSession)

    def test_create_session_with_cookies(self):
        """create_session accepts cookies."""
        cookies = {"session": "abc123"}
        session = create_session(cookies=cookies)
        assert session.config.cookies == cookies


class TestFileWriteWorker:
    """Test FileWriteWorker."""

    def test_worker_instantiates(self):
        """FileWriteWorker instantiates with defaults."""
        worker = FileWriteWorker()
        assert worker._batch_size == 50
        assert worker._queue_size == 1000
        worker.stop()

    def test_worker_normalize_path(self):
        """FileWriteWorker normalizes paths correctly."""
        path = FileWriteWorker._normalize_path("/tmp/test/../file.json")
        assert "test" not in path
        assert path.endswith("file.json")

    def test_worker_context_manager(self):
        """FileWriteWorker works as context manager."""
        with FileWriteWorker() as worker:
            assert worker._running
        assert not worker._running


class TestImports:
    """Test all imports resolve correctly."""

    def test_core_imports(self):
        """All core module imports work."""
        from healthsparq.core import HealthSpark, HealthSparkConfig
        from healthsparq.core.session import create_session
        from healthsparq.core.file_writer import FileWriteWorker

        assert HealthSpark is not None
        assert HealthSparkConfig is not None
        assert create_session is not None
        assert FileWriteWorker is not None


class TestLOCCount:
    """Verify healthspark.py is under 600 lines."""

    def test_healthspark_under_600_loc(self):
        """healthspark.py is under 600 lines of code."""
        import os
        from pathlib import Path

        healthspark_path = (
            Path(__file__).parent.parent / "core" / "healthspark.py"
        )
        with open(healthspark_path) as f:
            line_count = sum(1 for _ in f)

        assert line_count < 600, f"healthspark.py has {line_count} lines (limit: 600)"

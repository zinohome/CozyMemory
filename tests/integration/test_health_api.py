"""健康检查 API 集成测试"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from cozymemory.app import create_app


@pytest.fixture
def client():
    """创建测试客户端"""
    app = create_app()
    return TestClient(app)


class TestHealthEndpoint:
    """健康检查端点测试"""

    def test_health_returns_200(self, client):
        """健康检查应返回 200"""
        with (
            patch("cozymemory.api.v1.health.get_mem0_client") as mock_mem0,
            patch("cozymemory.api.v1.health.get_memobase_client") as mock_memobase,
            patch("cozymemory.api.v1.health.get_cognee_client") as mock_cognee,
        ):
            mock_mem0.return_value.health_check = AsyncMock(return_value=True)
            mock_memobase.return_value.health_check = AsyncMock(return_value=True)
            mock_cognee.return_value.health_check = AsyncMock(return_value=True)
            response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "engines" in data

    def test_health_degraded_when_one_fails(self, client):
        """一个引擎不健康时状态应为 degraded"""
        with (
            patch("cozymemory.api.v1.health.get_mem0_client") as mock_mem0,
            patch("cozymemory.api.v1.health.get_memobase_client") as mock_memobase,
            patch("cozymemory.api.v1.health.get_cognee_client") as mock_cognee,
        ):
            mock_mem0.return_value.health_check = AsyncMock(return_value=True)
            mock_memobase.return_value.health_check = AsyncMock(return_value=False)
            mock_cognee.return_value.health_check = AsyncMock(return_value=True)
            response = client.get("/api/v1/health")
        data = response.json()
        assert data["status"] == "degraded"

    def test_health_unhealthy_when_all_fail(self, client):
        """所有引擎不健康时状态应为 unhealthy"""
        with (
            patch("cozymemory.api.v1.health.get_mem0_client") as mock_mem0,
            patch("cozymemory.api.v1.health.get_memobase_client") as mock_memobase,
            patch("cozymemory.api.v1.health.get_cognee_client") as mock_cognee,
        ):
            mock_mem0.return_value.health_check = AsyncMock(
                side_effect=Exception("connection refused")
            )
            mock_memobase.return_value.health_check = AsyncMock(
                side_effect=Exception("connection refused")
            )
            mock_cognee.return_value.health_check = AsyncMock(
                side_effect=Exception("connection refused")
            )
            response = client.get("/api/v1/health")
        data = response.json()
        assert data["status"] == "unhealthy"

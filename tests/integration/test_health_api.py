"""健康检查 API 集成测试

针对真实运行的 CozyMemory 服务执行。
服务地址由 COZY_TEST_URL 环境变量控制（默认 http://localhost:8000）。
若服务不可达，测试自动跳过。
"""

import pytest

from .conftest import requires_server


@requires_server
@pytest.mark.asyncio
async def test_health_returns_200(http):
    """GET /api/v1/health 返回 200"""
    response = await http.get("/api/v1/health")
    assert response.status_code == 200


@requires_server
@pytest.mark.asyncio
async def test_health_response_shape(http):
    """健康检查响应包含 status 和 engines 字段"""
    response = await http.get("/api/v1/health")
    body = response.json()
    assert "status" in body
    assert "engines" in body
    assert body["status"] in ("healthy", "degraded", "unhealthy")


@requires_server
@pytest.mark.asyncio
async def test_health_engines_have_required_keys(http):
    """engines 字典中每个条目包含必要字段"""
    response = await http.get("/api/v1/health")
    body = response.json()
    engines = body.get("engines", {})
    assert isinstance(engines, dict)
    for engine_info in engines.values():
        assert "name" in engine_info
        assert "status" in engine_info

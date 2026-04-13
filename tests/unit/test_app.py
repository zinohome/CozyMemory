"""app.py 补充测试 - 覆盖 CORS 中间件, lifespan, create_app"""

import pytest
from httpx import ASGITransport, AsyncClient

from cozymemory.app import create_app


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_cors_middleware(client):
    """CORS 中间件允许跨域请求"""
    response = await client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code in (200, 204)
    assert response.headers.get("access-control-allow-origin") in ("*", "http://example.com")


@pytest.mark.asyncio
async def test_create_app_returns_fastapi():
    """create_app 返回 FastAPI 实例"""
    app = create_app()
    assert app.title == "CozyMemory"
    assert app.version is not None


@pytest.mark.asyncio
async def test_health_endpoint_accessible(client):
    """健康检查端点可访问"""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200

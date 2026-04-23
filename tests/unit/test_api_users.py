"""/api/v1/operator/users-mapping 路由测试 — user_id ↔ UUID 映射管理。"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from cozymemory.api.deps import get_user_mapping_service
from cozymemory.app import create_app


@pytest.fixture
def mock_service():
    return MagicMock()


@pytest.fixture
async def client(mock_service, monkeypatch):
    monkeypatch.setenv("COZY_API_KEYS", "")
    from cozymemory.config import settings

    settings.COZY_API_KEYS = ""
    app = create_app()
    app.dependency_overrides[get_user_mapping_service] = lambda: mock_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ───────────────────────── list ─────────────────────────


@pytest.mark.asyncio
async def test_list_users(client, mock_service):
    mock_service.list_users = AsyncMock(return_value=["alice", "bob"])
    resp = await client.get("/api/v1/operator/users-mapping")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert body["data"] == ["alice", "bob"]


@pytest.mark.asyncio
async def test_list_users_empty(client, mock_service):
    mock_service.list_users = AsyncMock(return_value=[])
    resp = await client.get("/api/v1/operator/users-mapping")
    assert resp.json()["total"] == 0


# ───────────────────────── get uuid (create=false) ─────────────────────────


@pytest.mark.asyncio
async def test_get_uuid_found(client, mock_service):
    mock_service.get_uuid = AsyncMock(return_value="uuid-v4-here")
    resp = await client.get("/api/v1/operator/users-mapping/alice/uuid")
    assert resp.status_code == 200
    body = resp.json()
    assert body["uuid"] == "uuid-v4-here"
    assert body["user_id"] == "alice"
    assert body["created"] is False


@pytest.mark.asyncio
async def test_get_uuid_missing_returns_404(client, mock_service):
    mock_service.get_uuid = AsyncMock(return_value=None)
    resp = await client.get("/api/v1/operator/users-mapping/ghost/uuid")
    assert resp.status_code == 404
    assert resp.json()["error"] == "NotFoundError"


# ───────────────────────── get uuid (create=true) ─────────────────────────


@pytest.mark.asyncio
async def test_get_uuid_create_true_new_mapping(client, mock_service):
    mock_service.get_uuid = AsyncMock(return_value=None)  # 不存在
    mock_service.get_or_create_uuid = AsyncMock(return_value="new-uuid")
    resp = await client.get("/api/v1/operator/users-mapping/alice/uuid?create=true")
    assert resp.status_code == 200
    body = resp.json()
    assert body["uuid"] == "new-uuid"
    assert body["created"] is True  # 新建标记


@pytest.mark.asyncio
async def test_get_uuid_create_true_existing_mapping(client, mock_service):
    mock_service.get_uuid = AsyncMock(return_value="already-there")
    mock_service.get_or_create_uuid = AsyncMock(return_value="already-there")
    resp = await client.get("/api/v1/operator/users-mapping/alice/uuid?create=true")
    body = resp.json()
    assert body["uuid"] == "already-there"
    # 已存在时 created=False
    assert body["created"] is False


# ───────────────────────── delete mapping ─────────────────────────


@pytest.mark.asyncio
async def test_delete_mapping_existed(client, mock_service):
    mock_service.delete_mapping = AsyncMock(return_value=True)
    resp = await client.delete("/api/v1/operator/users-mapping/alice/uuid")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    # 存在过的映射删除返回警告
    assert "孤立" in body["warning"]


@pytest.mark.asyncio
async def test_delete_mapping_not_existed(client, mock_service):
    mock_service.delete_mapping = AsyncMock(return_value=False)
    resp = await client.delete("/api/v1/operator/users-mapping/ghost/uuid")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["warning"] == ""  # 不存在时不发警告

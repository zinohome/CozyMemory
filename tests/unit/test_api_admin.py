"""/api/v1/admin/api-keys 路由测试。"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from cozymemory.api.deps import get_api_key_store
from cozymemory.app import create_app
from cozymemory.models.admin import (
    ApiKeyCreateResponse,
    ApiKeyLogEntry,
    ApiKeyRecord,
)


@pytest.fixture
def mock_store():
    return MagicMock()


@pytest.fixture
async def client(mock_store, monkeypatch):
    # 关鉴权以绕过中间件（本测试只关注路由逻辑）
    monkeypatch.setenv("COZY_API_KEYS", "")
    from cozymemory.config import settings

    settings.COZY_API_KEYS = ""
    app = create_app()
    app.dependency_overrides[get_api_key_store] = lambda: mock_store
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


def _record(kid: str = "k1", name: str = "test") -> ApiKeyRecord:
    return ApiKeyRecord(
        id=kid,
        name=name,
        prefix="cozy_abc12345",
        created_at=datetime.now(timezone.utc),
        last_used_at=None,
        disabled=False,
    )


# ───────────────────────── list ─────────────────────────


@pytest.mark.asyncio
async def test_list_keys_returns_total(client, mock_store):
    mock_store.list_keys = AsyncMock(return_value=[_record("a"), _record("b")])
    resp = await client.get("/api/v1/admin/api-keys")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["data"]) == 2


@pytest.mark.asyncio
async def test_list_keys_empty(client, mock_store):
    mock_store.list_keys = AsyncMock(return_value=[])
    resp = await client.get("/api/v1/admin/api-keys")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# ───────────────────────── create ─────────────────────────


@pytest.mark.asyncio
async def test_create_key_returns_201_and_plaintext(client, mock_store):
    mock_store.create = AsyncMock(
        return_value=ApiKeyCreateResponse(
            record=_record("new-id", "prod"), key="cozy_plaintext_value"
        )
    )
    resp = await client.post(
        "/api/v1/admin/api-keys", json={"name": "prod"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["key"] == "cozy_plaintext_value"
    assert body["record"]["name"] == "prod"
    # service 收到的 name 已 strip
    mock_store.create.assert_awaited_once_with(name="prod")


@pytest.mark.asyncio
async def test_create_key_strips_whitespace(client, mock_store):
    mock_store.create = AsyncMock(
        return_value=ApiKeyCreateResponse(record=_record(), key="k")
    )
    await client.post("/api/v1/admin/api-keys", json={"name": "  spaced  "})
    mock_store.create.assert_awaited_once_with(name="spaced")


# ───────────────────────── update ─────────────────────────


@pytest.mark.asyncio
async def test_update_key_name_and_disabled(client, mock_store):
    updated = _record("k1", "renamed")
    updated.disabled = True
    mock_store.update = AsyncMock(return_value=updated)
    resp = await client.patch(
        "/api/v1/admin/api-keys/k1", json={"name": "renamed", "disabled": True}
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "renamed"
    assert resp.json()["disabled"] is True


@pytest.mark.asyncio
async def test_update_key_not_found_returns_404(client, mock_store):
    mock_store.update = AsyncMock(return_value=None)
    resp = await client.patch(
        "/api/v1/admin/api-keys/missing", json={"name": "x"}
    )
    assert resp.status_code == 404


# ───────────────────────── rotate ─────────────────────────


@pytest.mark.asyncio
async def test_rotate_key_success(client, mock_store):
    mock_store.rotate = AsyncMock(
        return_value=ApiKeyCreateResponse(record=_record(), key="cozy_new")
    )
    resp = await client.post("/api/v1/admin/api-keys/k1/rotate")
    assert resp.status_code == 200
    assert resp.json()["key"] == "cozy_new"


@pytest.mark.asyncio
async def test_rotate_key_not_found(client, mock_store):
    mock_store.rotate = AsyncMock(return_value=None)
    resp = await client.post("/api/v1/admin/api-keys/missing/rotate")
    assert resp.status_code == 404


# ───────────────────────── logs ─────────────────────────


@pytest.mark.asyncio
async def test_get_logs(client, mock_store):
    mock_store.get_logs = AsyncMock(
        return_value=[
            ApiKeyLogEntry(
                ts=datetime.now(timezone.utc),
                method="GET",
                path="/users",
                status=200,
            ),
        ]
    )
    resp = await client.get("/api/v1/admin/api-keys/k1/logs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["data"][0]["path"] == "/users"


@pytest.mark.asyncio
async def test_get_logs_respects_limit_param(client, mock_store):
    mock_store.get_logs = AsyncMock(return_value=[])
    await client.get("/api/v1/admin/api-keys/k1/logs?limit=5")
    mock_store.get_logs.assert_awaited_once_with("k1", limit=5)


# ───────────────────────── delete ─────────────────────────


@pytest.mark.asyncio
async def test_delete_key_success(client, mock_store):
    mock_store.delete = AsyncMock(return_value=True)
    resp = await client.delete("/api/v1/admin/api-keys/k1")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_delete_key_not_found(client, mock_store):
    mock_store.delete = AsyncMock(return_value=False)
    resp = await client.delete("/api/v1/admin/api-keys/missing")
    assert resp.status_code == 404

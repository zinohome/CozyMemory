"""Dashboard Users API — 列出 / 删除 App 下的 external user 映射。"""
import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

from cozymemory.api.deps import get_conversation_service
from cozymemory.app import create_app
from cozymemory.db.models import Base
from cozymemory.models.conversation import ConversationMemoryListResponse

DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://cozymemory_user:cozymemory_pass@localhost:5433/cozymemory",
)

pytestmark = pytest.mark.skipif(
    os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true",
    reason="requires local postgres + redis",
)


@pytest.fixture(autouse=True)
async def clean_db():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for t in reversed(Base.metadata.sorted_tables):
            await conn.execute(t.delete())
    await engine.dispose()
    yield


@pytest.fixture
async def client():
    from cozymemory.config import settings as _s
    _s.COZY_API_KEYS = "bootstrap-x"
    _s.DATABASE_URL = DATABASE_URL
    from cozymemory.db import engine as db_engine
    db_engine._engine = None
    db_engine._session_factory = None
    mock = MagicMock()
    mock.add = AsyncMock(
        return_value=ConversationMemoryListResponse(success=True, data=[], total=0)
    )
    app = create_app()
    app.dependency_overrides[get_conversation_service] = lambda: mock
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c, mock
    app.dependency_overrides.clear()


async def _bootstrap(c):
    r = await c.post("/api/v1/auth/register", json={
        "email": "d@c.com", "password": "Password1",
        "org_name": "O", "org_slug": "oo"})
    token = r.json()["access_token"]
    r2 = await c.post("/api/v1/dashboard/apps",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "A", "slug": "aa"})
    app_id = r2.json()["id"]
    r3 = await c.post(f"/api/v1/dashboard/apps/{app_id}/keys",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "k"})
    key = r3.json()["key"]
    for ext in ["alice", "bob", "carol"]:
        await c.post("/api/v1/conversations",
            headers={"X-Cozy-API-Key": key},
            json={"user_id": ext, "messages": [{"role": "user", "content": "hi"}]})
    return token, app_id


@pytest.mark.asyncio
async def test_list_users_paginated(client):
    c, _ = client
    token, app_id = await _bootstrap(c)
    r = await c.get(
        f"/api/v1/dashboard/apps/{app_id}/users?limit=2&offset=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3
    assert len(data["data"]) == 2


@pytest.mark.asyncio
async def test_users_not_visible_across_apps(client):
    c, _ = client
    token_a, _ = await _bootstrap(c)
    r = await c.post("/api/v1/dashboard/apps",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"name": "B", "slug": "bb"})
    app_b = r.json()["id"]
    r2 = await c.get(f"/api/v1/dashboard/apps/{app_b}/users",
        headers={"Authorization": f"Bearer {token_a}"})
    assert r2.json()["total"] == 0


@pytest.mark.asyncio
async def test_delete_user_then_404(client):
    c, _ = client
    token, app_id = await _bootstrap(c)
    r = await c.delete(
        f"/api/v1/dashboard/apps/{app_id}/users/alice",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    r2 = await c.delete(
        f"/api/v1/dashboard/apps/{app_id}/users/alice",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_users_count_matches(client):
    c, _ = client
    token, app_id = await _bootstrap(c)
    r = await c.get(f"/api/v1/dashboard/apps/{app_id}/users",
        headers={"Authorization": f"Bearer {token}"})
    assert r.json()["total"] == 3

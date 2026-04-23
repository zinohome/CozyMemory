"""Step 8 — operator / developer 角色鉴权边界。

- /api/v1/operator/* 只接 bootstrap key，拒 JWT
- 业务路由（/conversations 等）的 Bearer 分支必须带 X-Cozy-App-Id
"""
import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

from cozymemory.api.deps import get_conversation_service, get_user_mapping_service
from cozymemory.app import create_app
from cozymemory.db.models import Base
from cozymemory.models.conversation import ConversationMemoryListResponse

DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://cozymemory_user:cozymemory_pass@localhost:5433/cozymemory_test",
)
BOOTSTRAP_KEY = "bootstrap-role-test"

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
def mock_conv():
    svc = MagicMock()
    svc.add = AsyncMock(
        return_value=ConversationMemoryListResponse(success=True, data=[], total=0)
    )
    return svc


@pytest.fixture
def mock_user_mapping():
    svc = MagicMock()
    svc.list_users = AsyncMock(return_value=[])
    return svc


@pytest.fixture
async def client(mock_conv, mock_user_mapping):
    from cozymemory.config import settings as _s
    _s.COZY_API_KEYS = BOOTSTRAP_KEY
    _s.DATABASE_URL = DATABASE_URL
    from cozymemory.db import engine as db_engine
    db_engine._engine = None
    db_engine._session_factory = None
    app = create_app()
    app.dependency_overrides[get_conversation_service] = lambda: mock_conv
    app.dependency_overrides[get_user_mapping_service] = lambda: mock_user_mapping
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _register(client):
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "d@c.com", "password": "Password1",
              "org_name": "Org", "org_slug": "org"},
    )
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_bearer_without_appid_on_business_route_rejected(client):
    """Bearer 无 AppId 调 /conversations → 401（Step 7 之前 ok=True，这里收紧）"""
    token = await _register(client)
    r = await client.post(
        "/api/v1/conversations",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": "x", "messages": [{"role": "user", "content": "x"}]},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_bearer_without_appid_on_dashboard_allowed(client):
    """Bearer 无 AppId 调 /dashboard/apps（管理接口）→ 200（合理）"""
    token = await _register(client)
    r = await client.get(
        "/api/v1/dashboard/apps",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_jwt_cannot_access_operator_routes(client):
    """Developer JWT 调 /operator/* → 401（operator 只认 bootstrap）。"""
    token = await _register(client)
    r = await client.get(
        "/api/v1/operator/users-mapping",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_bootstrap_key_can_access_operator_routes(client):
    """bootstrap key 调 /operator/* → 放行（路由不存在会 404，但至少不是 401）"""
    r = await client.get(
        "/api/v1/operator/users-mapping",
        headers={"X-Cozy-API-Key": BOOTSTRAP_KEY},
    )
    assert r.status_code != 401

"""JWT + X-Cozy-App-Id 鉴权通路（方案 C）。

外部 App 走 X-Cozy-API-Key 的老路径不动；UI Dashboard 走 Bearer JWT +
X-Cozy-App-Id，中间件按 header 分流。本套测试覆盖 6 个关键场景。
"""

import os
import uuid
from datetime import UTC
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
BOOTSTRAP_KEY = "bootstrap-jwt-test"

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
    svc.add = AsyncMock(return_value=ConversationMemoryListResponse(success=True, data=[], total=0))
    return svc


@pytest.fixture
async def client(mock_conv):
    from cozymemory.config import settings as _s

    _s.COZY_API_KEYS = BOOTSTRAP_KEY
    _s.DATABASE_URL = DATABASE_URL
    from cozymemory.db import engine as db_engine

    db_engine._engine = None
    db_engine._session_factory = None
    app = create_app()
    app.dependency_overrides[get_conversation_service] = lambda: mock_conv
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _register_and_app(client):
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "d@c.com", "password": "Password1", "org_name": "Org", "org_slug": "org"},
    )
    token = r.json()["access_token"]
    r2 = await client.post(
        "/api/v1/dashboard/apps",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "A", "slug": "aa"},
    )
    return token, r2.json()["id"], uuid.UUID(r2.json()["namespace_id"])


@pytest.mark.asyncio
async def test_bearer_plus_app_id_passes_and_scopes(client, mock_conv):
    token, app_id, ns = await _register_and_app(client)
    ext = "ext_user_1"
    expected = uuid.uuid5(ns, ext)

    r = await client.post(
        "/api/v1/conversations",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Cozy-App-Id": app_id,
        },
        json={"user_id": ext, "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 200
    kwargs = mock_conv.add.await_args.kwargs
    assert kwargs["user_id"] == str(expected)


@pytest.mark.asyncio
async def test_bearer_plus_cross_org_app_id_rejected(client):
    """A developer 用 B org 的 app_id → 401"""
    token_a, _, _ = await _register_and_app(client)
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "b@c.com", "password": "Password1", "org_name": "B", "org_slug": "bb"},
    )
    tb = r.json()["access_token"]
    rb = await client.post(
        "/api/v1/dashboard/apps",
        headers={"Authorization": f"Bearer {tb}"},
        json={"name": "B", "slug": "bbapp"},
    )
    cross_app_id = rb.json()["id"]

    r3 = await client.post(
        "/api/v1/conversations",
        headers={
            "Authorization": f"Bearer {token_a}",
            "X-Cozy-App-Id": cross_app_id,
        },
        json={"user_id": "x", "messages": [{"role": "user", "content": "x"}]},
    )
    assert r3.status_code == 401


@pytest.mark.asyncio
async def test_bearer_without_app_id_on_business_route_now_rejected(client, mock_conv):
    """Step 8 收紧：Bearer 无 AppId 调业务路由现在是 401"""
    token, _, _ = await _register_and_app(client)
    r = await client.post(
        "/api/v1/conversations",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": "x", "messages": [{"role": "user", "content": "x"}]},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_expired_jwt_rejected(client):
    from datetime import datetime, timedelta

    import jwt as _jwt

    from cozymemory.config import settings

    token = _jwt.encode(
        {"sub": "00000000-0000-0000-0000-000000000000", "exp": datetime.now(UTC) - timedelta(seconds=1)},
        settings.JWT_SECRET,
        algorithm="HS256",
    )
    r = await client.post(
        "/api/v1/conversations",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": "x", "messages": [{"role": "user", "content": "x"}]},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_forged_jwt_rejected(client):
    r = await client.post(
        "/api/v1/conversations",
        headers={"Authorization": "Bearer not.a.valid.jwt"},
        json={"user_id": "x", "messages": [{"role": "user", "content": "x"}]},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_api_key_wins_over_bearer(client, mock_conv):
    r = await client.post(
        "/api/v1/conversations",
        headers={
            "X-Cozy-API-Key": BOOTSTRAP_KEY,
            "Authorization": "Bearer something.invalid.here",
        },
        json={"user_id": "raw", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 200
    kwargs = mock_conv.add.await_args.kwargs
    assert kwargs["user_id"] == "raw"

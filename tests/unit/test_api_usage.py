"""APIUsage middleware tap + dashboard endpoint (Step 8.16)."""
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
    "postgresql+asyncpg://cozymemory_user:cozymemory_pass@localhost:5433/cozymemory_test",
)
BOOTSTRAP_KEY = "bootstrap-usage-test"

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


async def _mk_app_and_key(c):
    r = await c.post("/api/v1/auth/register", json={
        "email": "u@c.com", "password": "Password1",
        "org_name": "U", "org_slug": "utest"})
    tok = r.json()["access_token"]
    r2 = await c.post("/api/v1/dashboard/apps",
        headers={"Authorization": f"Bearer {tok}"},
        json={"name": "U", "slug": "uapp"})
    app_id = r2.json()["id"]
    r3 = await c.post(f"/api/v1/dashboard/apps/{app_id}/keys",
        headers={"Authorization": f"Bearer {tok}"},
        json={"name": "k"})
    return tok, app_id, r3.json()["key"]


@pytest.mark.asyncio
async def test_business_route_call_records_usage(client):
    tok, app_id, key = await _mk_app_and_key(client)
    # 触发 3 次 business call
    for _ in range(3):
        await client.post("/api/v1/conversations",
            headers={"X-Cozy-API-Key": key},
            json={"user_id": "alice", "messages": [{"role": "user", "content": "hi"}]})
    r = await client.get(f"/api/v1/dashboard/apps/{app_id}/usage?days=7",
        headers={"Authorization": f"Bearer {tok}"})
    data = r.json()
    assert data["total"] == 3
    assert data["success"] == 3
    assert data["errors"] == 0
    assert data["avg_latency_ms"] > 0
    assert any(row["route"] == "conversations" for row in data["per_route"])


@pytest.mark.asyncio
async def test_bootstrap_calls_are_not_tracked(client):
    tok, app_id, _ = await _mk_app_and_key(client)
    # bootstrap 调业务 → passthrough，不应写 api_usage
    await client.post("/api/v1/conversations",
        headers={"X-Cozy-API-Key": BOOTSTRAP_KEY},
        json={"user_id": "alice", "messages": [{"role": "user", "content": "hi"}]})
    r = await client.get(f"/api/v1/dashboard/apps/{app_id}/usage",
        headers={"Authorization": f"Bearer {tok}"})
    assert r.json()["total"] == 0


@pytest.mark.asyncio
async def test_non_business_routes_skip_tracking(client):
    tok, app_id, key = await _mk_app_and_key(client)
    # /dashboard/apps (管理路由) 不算 usage
    await client.get("/api/v1/dashboard/apps",
        headers={"Authorization": f"Bearer {tok}"})
    r = await client.get(f"/api/v1/dashboard/apps/{app_id}/usage",
        headers={"Authorization": f"Bearer {tok}"})
    assert r.json()["total"] == 0


@pytest.mark.asyncio
async def test_cross_org_usage_returns_404(client):
    tok_a, _, _ = await _mk_app_and_key(client)
    # 另一个 org 拿到别家 app_id 查 usage → 404
    import uuid as _uuid
    fake_app = str(_uuid.uuid4())
    r = await client.get(f"/api/v1/dashboard/apps/{fake_app}/usage",
        headers={"Authorization": f"Bearer {tok_a}"})
    assert r.status_code == 404

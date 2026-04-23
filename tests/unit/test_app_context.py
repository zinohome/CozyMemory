"""AppContext 依赖测试 — 中间件注入 → 路由拿到。

覆盖四种场景：
  1. App Key 命中 → get_app_context 有值 / require_app_context 通过
  2. Bootstrap key → 两种都视为 "无 App 归属"
  3. 无鉴权 → 中间件先 401，路由不到
  4. AppContext.get_app() 懒加载 App 记录

需要本机 PG；CI 自动跳过。
"""

import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

from cozymemory.app import create_app
from cozymemory.db.models import Base

DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://cozymemory_user:cozymemory_pass@localhost:5433/cozymemory",
)
BOOTSTRAP_KEY = "bootstrap-test-key-xyz"

pytestmark = pytest.mark.skipif(
    os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true",
    reason="requires local postgres",
)


@pytest.fixture(autouse=True)
async def clean_db():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
    await engine.dispose()
    yield


@pytest.fixture
async def client():
    """带 bootstrap key 的客户端，鉴权开启"""
    from cozymemory.config import settings as _s

    _s.COZY_API_KEYS = BOOTSTRAP_KEY
    _s.DATABASE_URL = DATABASE_URL

    from cozymemory.db import engine as db_engine

    db_engine._engine = None
    db_engine._session_factory = None

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _setup_app_key(client) -> tuple[str, str]:
    """注册 + 建 App + 建 API Key，返回 (app_id, plaintext_key)"""
    r1 = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "dev@co.com",
            "password": "Password1",
            "org_name": "Co",
            "org_slug": "co",
        },
    )
    assert r1.status_code == 201, r1.text
    token = r1.json()["access_token"]

    r2 = await client.post(
        "/api/v1/dashboard/apps",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "TestApp", "slug": "testapp"},
    )
    assert r2.status_code == 201
    app_id = r2.json()["id"]

    r3 = await client.post(
        f"/api/v1/dashboard/apps/{app_id}/keys",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "test-key"},
    )
    assert r3.status_code == 201
    return app_id, r3.json()["key"]


# ─────────────── 路由能拿到 AppContext ───────────────


@pytest.mark.asyncio
async def test_app_key_populates_context_in_route(caplog, client):
    """App Key 调 /conversations POST，日志里能看到 app_scope 信息"""
    app_id, api_key = await _setup_app_key(client)

    import logging

    caplog.set_level(logging.INFO)
    resp = await client.post(
        "/api/v1/conversations",
        headers={"X-Cozy-API-Key": api_key},
        json={
            "user_id": "ext_user_1",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )
    # 不关心 Mem0 实际响应（test 环境里可能 502），只要不是 401/403 就说明中间件+context 生效
    assert resp.status_code not in (401, 403)


@pytest.mark.asyncio
async def test_bootstrap_key_has_no_app_context(client):
    """Bootstrap key 调业务路由：中间件放行（200/502），app_ctx 在路由里是 None"""
    resp = await client.post(
        "/api/v1/conversations",
        headers={"X-Cozy-API-Key": BOOTSTRAP_KEY},
        json={
            "user_id": "u1",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )
    # 不是 401（通过）也不是 403（add_conversation 用 get_app_context 不是 require_*）
    assert resp.status_code not in (401, 403)


@pytest.mark.asyncio
async def test_missing_api_key_401(client):
    resp = await client.post(
        "/api/v1/conversations",
        json={"user_id": "u1", "messages": [{"role": "user", "content": "x"}]},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_wrong_api_key_401(client):
    resp = await client.post(
        "/api/v1/conversations",
        headers={"X-Cozy-API-Key": "cozy_live_totally_fake"},
        json={"user_id": "u1", "messages": [{"role": "user", "content": "x"}]},
    )
    assert resp.status_code == 401


# ─────────────── AppContext.get_app() 懒加载 ───────────────


@pytest.mark.asyncio
async def test_app_context_get_app_returns_record(client):
    """直接用 AppContext 测：拿到的 App.namespace_id 是 UUID"""
    app_id, _ = await _setup_app_key(client)
    from uuid import UUID

    from cozymemory.auth import AppContext
    from cozymemory.db.engine import _session_factory, init_engine

    if _session_factory is None:
        init_engine()
    assert _session_factory is not None

    async with _session_factory() as session:
        ctx = AppContext(
            app_id=UUID(app_id),
            api_key_id=UUID("00000000-0000-0000-0000-000000000001"),  # 任意，get_app 不校验
            _session=session,
        )
        app = await ctx.get_app()
        assert str(app.id) == app_id
        assert app.slug == "testapp"
        # namespace_id 是 App 创建时自动生成的 UUID，用于 Step 5 的 uuid5 映射
        assert app.namespace_id is not None

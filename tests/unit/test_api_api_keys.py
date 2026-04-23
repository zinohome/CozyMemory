"""/api/v1/dashboard/apps/{app_id}/keys 端到端测试。

覆盖 CRUD + rotate、RBAC、跨组织 404、审计、鉴权通路（plaintext → PG 查回）。
需要本机 PG；CI 自动跳过。
"""

import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from cozymemory.app import create_app
from cozymemory.db.models import AuditLog, Base, Developer

DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://cozymemory_user:cozymemory_pass@localhost:5433/cozymemory_test",
)

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
async def client(monkeypatch):
    monkeypatch.setenv("COZY_API_KEYS", "")
    from cozymemory.config import settings as _s

    _s.COZY_API_KEYS = ""
    _s.DATABASE_URL = DATABASE_URL

    from cozymemory.db import engine as db_engine

    db_engine._engine = None
    db_engine._session_factory = None

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _register_and_app(client, email="a@x.com", org_slug="acme"):
    """注册 owner + 建一个 App，返回 (token, app_id)"""
    r1 = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password1",
            "org_name": "Org",
            "org_slug": org_slug,
        },
    )
    assert r1.status_code == 201, r1.text
    token = r1.json()["access_token"]

    r2 = await client.post(
        "/api/v1/dashboard/apps",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "App", "slug": "app-one"},
    )
    assert r2.status_code == 201, r2.text
    return token, r2.json()["id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ─────────────── list / create ───────────────


@pytest.mark.asyncio
async def test_list_keys_empty_initially(client):
    token, app_id = await _register_and_app(client)
    resp = await client.get(
        f"/api/v1/dashboard/apps/{app_id}/keys", headers=_auth(token)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["data"] == []


@pytest.mark.asyncio
async def test_create_key_returns_plaintext_once(client):
    token, app_id = await _register_and_app(client)
    resp = await client.post(
        f"/api/v1/dashboard/apps/{app_id}/keys",
        headers=_auth(token),
        json={"name": "prod", "environment": "live"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["key"].startswith("cozy_live_")
    assert body["record"]["prefix"] == body["key"][:18]
    assert body["record"]["environment"] == "live"
    assert body["record"]["disabled"] is False

    # list 显示有 1 个，但不含 plaintext
    resp_list = await client.get(
        f"/api/v1/dashboard/apps/{app_id}/keys", headers=_auth(token)
    )
    assert resp_list.json()["total"] == 1
    assert "key" not in resp_list.json()["data"][0]  # 没有明文字段


@pytest.mark.asyncio
async def test_create_test_environment_key(client):
    token, app_id = await _register_and_app(client)
    resp = await client.post(
        f"/api/v1/dashboard/apps/{app_id}/keys",
        headers=_auth(token),
        json={"name": "sandbox", "environment": "test"},
    )
    assert resp.status_code == 201
    assert resp.json()["key"].startswith("cozy_test_")


@pytest.mark.asyncio
async def test_cross_org_cannot_see_keys_404(client):
    """B org 的 dev 查 A 的 App key → 404"""
    t1, app1 = await _register_and_app(client, email="a@x.com", org_slug="org-a")
    t2, _ = await _register_and_app(client, email="b@x.com", org_slug="org-b")

    resp = await client.get(
        f"/api/v1/dashboard/apps/{app1}/keys", headers=_auth(t2)
    )
    assert resp.status_code == 404


# ─────────────── rotate ───────────────


@pytest.mark.asyncio
async def test_rotate_invalidates_old_plaintext(client):
    token, app_id = await _register_and_app(client)
    r_create = await client.post(
        f"/api/v1/dashboard/apps/{app_id}/keys",
        headers=_auth(token),
        json={"name": "k", "environment": "live"},
    )
    key_id = r_create.json()["record"]["id"]
    old_plain = r_create.json()["key"]

    r_rotate = await client.post(
        f"/api/v1/dashboard/apps/{app_id}/keys/{key_id}/rotate",
        headers=_auth(token),
    )
    assert r_rotate.status_code == 200
    new_plain = r_rotate.json()["key"]
    assert new_plain != old_plain


# ─────────────── update ───────────────


@pytest.mark.asyncio
async def test_update_disable_enables(client):
    token, app_id = await _register_and_app(client)
    r_create = await client.post(
        f"/api/v1/dashboard/apps/{app_id}/keys",
        headers=_auth(token),
        json={"name": "k"},
    )
    key_id = r_create.json()["record"]["id"]

    # 禁用
    r1 = await client.patch(
        f"/api/v1/dashboard/apps/{app_id}/keys/{key_id}",
        headers=_auth(token),
        json={"disabled": True},
    )
    assert r1.status_code == 200
    assert r1.json()["disabled"] is True

    # 启用 + 改名
    r2 = await client.patch(
        f"/api/v1/dashboard/apps/{app_id}/keys/{key_id}",
        headers=_auth(token),
        json={"disabled": False, "name": "renamed"},
    )
    assert r2.json()["disabled"] is False
    assert r2.json()["name"] == "renamed"


# ─────────────── delete ───────────────


@pytest.mark.asyncio
async def test_delete_key(client):
    token, app_id = await _register_and_app(client)
    r_create = await client.post(
        f"/api/v1/dashboard/apps/{app_id}/keys",
        headers=_auth(token),
        json={"name": "k"},
    )
    key_id = r_create.json()["record"]["id"]

    r_del = await client.delete(
        f"/api/v1/dashboard/apps/{app_id}/keys/{key_id}",
        headers=_auth(token),
    )
    assert r_del.status_code == 204

    # list 空
    assert (
        await client.get(
            f"/api/v1/dashboard/apps/{app_id}/keys", headers=_auth(token)
        )
    ).json()["total"] == 0


# ─────────────── RBAC ───────────────


@pytest.mark.asyncio
async def test_member_cannot_create_key(client):
    token, app_id = await _register_and_app(client)

    # 改 owner → member
    engine = create_async_engine(DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        dev = (await s.execute(select(Developer))).scalar_one()
        dev.role = "member"
        await s.commit()
    await engine.dispose()

    resp = await client.post(
        f"/api/v1/dashboard/apps/{app_id}/keys",
        headers=_auth(token),
        json={"name": "k"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_rotate_but_not_delete(client):
    token, app_id = await _register_and_app(client)
    r_create = await client.post(
        f"/api/v1/dashboard/apps/{app_id}/keys",
        headers=_auth(token),
        json={"name": "k"},
    )
    key_id = r_create.json()["record"]["id"]

    # 改 owner → admin
    engine = create_async_engine(DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        dev = (await s.execute(select(Developer))).scalar_one()
        dev.role = "admin"
        await s.commit()
    await engine.dispose()

    # rotate 可
    assert (
        await client.post(
            f"/api/v1/dashboard/apps/{app_id}/keys/{key_id}/rotate",
            headers=_auth(token),
        )
    ).status_code == 200

    # delete 不可
    assert (
        await client.delete(
            f"/api/v1/dashboard/apps/{app_id}/keys/{key_id}",
            headers=_auth(token),
        )
    ).status_code == 403


# ─────────────── 鉴权通路（plaintext → PG 查回） ───────────────


@pytest.mark.asyncio
async def test_plaintext_verifies_against_pg(monkeypatch, client):
    """创建的 key 用于业务端口鉴权：打开 auth_enabled + 带 X-Cozy-API-Key 应该命中"""
    token, app_id = await _register_and_app(client)
    r_create = await client.post(
        f"/api/v1/dashboard/apps/{app_id}/keys",
        headers=_auth(token),
        json={"name": "real"},
    )
    plaintext = r_create.json()["key"]

    # 打开 bootstrap 之外的鉴权 — 让中间件走 PG 路径
    from cozymemory.config import settings as _s

    _s.COZY_API_KEYS = "bootstrap-never-matches"

    # 带着明文 key 去访问受保护路由 /api/v1/operator/users-mapping
    resp_ok = await client.get(
        "/api/v1/operator/users-mapping", headers={"X-Cozy-API-Key": plaintext}
    )
    assert resp_ok.status_code != 401, resp_ok.text

    # 错误 key
    resp_bad = await client.get(
        "/api/v1/operator/users-mapping", headers={"X-Cozy-API-Key": "cozy_live_totally-wrong"}
    )
    assert resp_bad.status_code == 401


@pytest.mark.asyncio
async def test_disabled_key_rejected(monkeypatch, client):
    token, app_id = await _register_and_app(client)
    r_create = await client.post(
        f"/api/v1/dashboard/apps/{app_id}/keys",
        headers=_auth(token),
        json={"name": "k"},
    )
    key_id = r_create.json()["record"]["id"]
    plaintext = r_create.json()["key"]

    # 禁用
    await client.patch(
        f"/api/v1/dashboard/apps/{app_id}/keys/{key_id}",
        headers=_auth(token),
        json={"disabled": True},
    )

    from cozymemory.config import settings as _s

    _s.COZY_API_KEYS = "bootstrap-never-matches"

    # 禁用后不能通过
    resp = await client.get(
        "/api/v1/operator/users-mapping", headers={"X-Cozy-API-Key": plaintext}
    )
    assert resp.status_code == 401


# ─────────────── audit ───────────────


@pytest.mark.asyncio
async def test_audit_log_on_create_rotate_delete(client):
    token, app_id = await _register_and_app(client)
    r_create = await client.post(
        f"/api/v1/dashboard/apps/{app_id}/keys",
        headers=_auth(token),
        json={"name": "audit"},
    )
    key_id = r_create.json()["record"]["id"]

    await client.post(
        f"/api/v1/dashboard/apps/{app_id}/keys/{key_id}/rotate",
        headers=_auth(token),
    )
    await client.delete(
        f"/api/v1/dashboard/apps/{app_id}/keys/{key_id}",
        headers=_auth(token),
    )

    engine = create_async_engine(DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        logs = (
            await s.execute(
                select(AuditLog).where(AuditLog.target_type == "api_key").order_by(AuditLog.created_at)
            )
        ).scalars().all()
        actions = [log.action for log in logs]
        assert "api_key.created" in actions
        assert "api_key.rotated" in actions
        assert "api_key.deleted" in actions
    await engine.dispose()

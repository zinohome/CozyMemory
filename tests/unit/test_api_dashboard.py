"""/api/v1/dashboard/apps 端到端测试。

覆盖：CRUD 完整流程、slug 冲突、角色权限、跨组织隔离（404）、审计日志写入。
需要本机 PG；CI 自动跳过。
"""

import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from cozymemory.app import create_app
from cozymemory.db.models import AuditLog, Base

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


async def _register(client, email="a@x.com", slug="acme", role_check=None) -> str:
    """注册一个 owner，返回 access_token。"""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password1",
            "org_name": "Org",
            "org_slug": slug,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ───────────────────────── List / Create ─────────────────────────


@pytest.mark.asyncio
async def test_list_apps_empty_initially(client):
    token = await _register(client)
    resp = await client.get("/api/v1/dashboard/apps", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["data"] == []


@pytest.mark.asyncio
async def test_create_app_success(client):
    token = await _register(client)
    resp = await client.post(
        "/api/v1/dashboard/apps",
        headers=_auth(token),
        json={
            "name": "Douyin Memory",
            "slug": "douyin-memory",
            "description": "抖音记忆",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "Douyin Memory"
    assert body["slug"] == "douyin-memory"
    assert body["description"] == "抖音记忆"
    # namespace_id 自动生成，是 UUID
    uuid.UUID(body["namespace_id"])
    # created_at 非空
    assert body["created_at"]


@pytest.mark.asyncio
async def test_create_app_duplicate_slug_in_same_org_conflicts(client):
    token = await _register(client)
    r1 = await client.post(
        "/api/v1/dashboard/apps",
        headers=_auth(token),
        json={"name": "X", "slug": "samex"},
    )
    assert r1.status_code == 201

    r2 = await client.post(
        "/api/v1/dashboard/apps",
        headers=_auth(token),
        json={"name": "Y", "slug": "samex"},  # 冲突
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_same_slug_allowed_across_different_orgs(client):
    """不同 org 可以有相同 slug 的 App（唯一约束是 (org_id, slug)）"""
    t1 = await _register(client, email="a@x.com", slug="org-a")
    t2 = await _register(client, email="b@x.com", slug="org-b")

    r1 = await client.post(
        "/api/v1/dashboard/apps",
        headers=_auth(t1),
        json={"name": "Same", "slug": "myapp"},
    )
    r2 = await client.post(
        "/api/v1/dashboard/apps",
        headers=_auth(t2),
        json={"name": "Same", "slug": "myapp"},  # 另一个 org 里可以
    )
    assert r1.status_code == 201
    assert r2.status_code == 201


@pytest.mark.asyncio
async def test_create_app_invalid_slug_422(client):
    token = await _register(client)
    resp = await client.post(
        "/api/v1/dashboard/apps",
        headers=_auth(token),
        json={"name": "X", "slug": "Invalid Slug"},  # 空格 / 大写违反 pattern
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_apps_after_create_returns_correct_order(client):
    token = await _register(client)
    await client.post(
        "/api/v1/dashboard/apps",
        headers=_auth(token),
        json={"name": "First", "slug": "first"},
    )
    await client.post(
        "/api/v1/dashboard/apps",
        headers=_auth(token),
        json={"name": "Second", "slug": "second"},
    )
    resp = await client.get("/api/v1/dashboard/apps", headers=_auth(token))
    body = resp.json()
    assert body["total"] == 2
    # 倒序（最新在前）
    assert body["data"][0]["name"] == "Second"
    assert body["data"][1]["name"] == "First"


# ───────────────────────── Get by ID ─────────────────────────


@pytest.mark.asyncio
async def test_get_app_success(client):
    token = await _register(client)
    created = (
        await client.post(
            "/api/v1/dashboard/apps",
            headers=_auth(token),
            json={"name": "X", "slug": "xx"},
        )
    ).json()
    resp = await client.get(
        f"/api/v1/dashboard/apps/{created['id']}", headers=_auth(token)
    )
    assert resp.status_code == 200
    assert resp.json()["slug"] == "xx"


@pytest.mark.asyncio
async def test_get_app_other_org_returns_404(client):
    """跨组织隔离：A 的 app B 查不到（返 404 不是 403，防枚举）"""
    t1 = await _register(client, email="a@x.com", slug="org-a")
    t2 = await _register(client, email="b@x.com", slug="org-b")

    created = (
        await client.post(
            "/api/v1/dashboard/apps",
            headers=_auth(t1),
            json={"name": "Secret", "slug": "secret"},
        )
    ).json()

    # B 去看 A 的 app → 404
    resp = await client.get(
        f"/api/v1/dashboard/apps/{created['id']}", headers=_auth(t2)
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_unknown_app_404(client):
    token = await _register(client)
    fake = uuid.uuid4()
    resp = await client.get(f"/api/v1/dashboard/apps/{fake}", headers=_auth(token))
    assert resp.status_code == 404


# ───────────────────────── Update ─────────────────────────


@pytest.mark.asyncio
async def test_update_app_name(client):
    token = await _register(client)
    created = (
        await client.post(
            "/api/v1/dashboard/apps",
            headers=_auth(token),
            json={"name": "Old", "slug": "old"},
        )
    ).json()

    resp = await client.patch(
        f"/api/v1/dashboard/apps/{created['id']}",
        headers=_auth(token),
        json={"name": "New"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New"
    assert resp.json()["slug"] == "old"  # slug 不变


@pytest.mark.asyncio
async def test_update_app_other_org_404(client):
    t1 = await _register(client, email="a@x.com", slug="org-a")
    t2 = await _register(client, email="b@x.com", slug="org-b")

    created = (
        await client.post(
            "/api/v1/dashboard/apps",
            headers=_auth(t1),
            json={"name": "X", "slug": "xx"},
        )
    ).json()

    resp = await client.patch(
        f"/api/v1/dashboard/apps/{created['id']}",
        headers=_auth(t2),
        json={"name": "hacked"},
    )
    assert resp.status_code == 404


# ───────────────────────── Delete ─────────────────────────


@pytest.mark.asyncio
async def test_delete_app(client):
    token = await _register(client)
    created = (
        await client.post(
            "/api/v1/dashboard/apps",
            headers=_auth(token),
            json={"name": "Gone", "slug": "gone"},
        )
    ).json()

    resp = await client.delete(
        f"/api/v1/dashboard/apps/{created['id']}", headers=_auth(token)
    )
    assert resp.status_code == 204

    # 再查 404
    resp2 = await client.get(
        f"/api/v1/dashboard/apps/{created['id']}", headers=_auth(token)
    )
    assert resp2.status_code == 404


# ───────────────────────── 角色权限 ─────────────────────────


@pytest.mark.asyncio
async def test_member_cannot_create_app(client):
    """非 owner/admin 不能 create。通过直接改 DB role 模拟"""
    token = await _register(client)

    # 改 role = member
    engine = create_async_engine(DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        from cozymemory.db.models import Developer

        result = await s.execute(select(Developer))
        dev = result.scalar_one()
        dev.role = "member"
        await s.commit()
    await engine.dispose()

    resp = await client.post(
        "/api/v1/dashboard/apps",
        headers=_auth(token),
        json={"name": "X", "slug": "xx"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_create_but_not_delete(client):
    """admin 能 create，但不能 delete（owner 唯一）"""
    token = await _register(client)

    # 改 role = admin
    engine = create_async_engine(DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        from cozymemory.db.models import Developer

        result = await s.execute(select(Developer))
        dev = result.scalar_one()
        dev.role = "admin"
        await s.commit()
    await engine.dispose()

    # create 能
    r_create = await client.post(
        "/api/v1/dashboard/apps",
        headers=_auth(token),
        json={"name": "X", "slug": "xx"},
    )
    assert r_create.status_code == 201

    # delete 不能
    r_del = await client.delete(
        f"/api/v1/dashboard/apps/{r_create.json()['id']}",
        headers=_auth(token),
    )
    assert r_del.status_code == 403


# ───────────────────────── 审计日志 ─────────────────────────


@pytest.mark.asyncio
async def test_audit_log_written_on_create_and_delete(client):
    token = await _register(client)

    # create
    r_create = await client.post(
        "/api/v1/dashboard/apps",
        headers=_auth(token),
        json={"name": "Audit Test", "slug": "audit-test"},
    )
    app_id = r_create.json()["id"]

    # delete
    await client.delete(
        f"/api/v1/dashboard/apps/{app_id}", headers=_auth(token)
    )

    # 查审计日志
    engine = create_async_engine(DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        result = await s.execute(select(AuditLog).order_by(AuditLog.created_at))
        logs = list(result.scalars().all())
        actions = [log.action for log in logs]
        assert "app.created" in actions
        assert "app.deleted" in actions
    await engine.dispose()


# ───────────────────────── Auth 必需 ─────────────────────────


@pytest.mark.asyncio
async def test_list_apps_without_token_401(client):
    resp = await client.get("/api/v1/dashboard/apps")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_app_with_invalid_token_401(client):
    resp = await client.post(
        "/api/v1/dashboard/apps",
        headers={"Authorization": "Bearer garbage"},
        json={"name": "X", "slug": "xx"},
    )
    assert resp.status_code == 401

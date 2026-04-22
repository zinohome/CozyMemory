"""/api/v1/auth 端到端测试（注册 → 登录 → /me）

需要本机可达的 cozymemory PG；CI 自动跳过。
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

pytestmark = pytest.mark.skipif(
    os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true",
    reason="requires local postgres",
)


@pytest.fixture(autouse=True)
async def clean_db():
    """每个测试前清空表"""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
    await engine.dispose()
    yield


@pytest.fixture
async def client(monkeypatch):
    # 关掉外部 API Key 鉴权（中间件跳过 /auth 已配，但 /me 也要走 JWT，不受 X-Cozy-API-Key 影响）
    monkeypatch.setenv("COZY_API_KEYS", "")
    from cozymemory.config import settings as _s

    _s.COZY_API_KEYS = ""
    # 让 DB engine 用 test URL
    monkeypatch.setenv("DATABASE_URL", DATABASE_URL)
    _s.DATABASE_URL = DATABASE_URL

    # 强制重置 engine（之前可能已经用别的 URL 初始化过）
    from cozymemory.db import engine as db_engine

    db_engine._engine = None
    db_engine._session_factory = None

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ───────────────────────── Register ─────────────────────────


@pytest.mark.asyncio
async def test_register_creates_org_and_dev_returns_token(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice@acme.com",
            "password": "SuperSecret123",
            "org_name": "Acme Inc",
            "org_slug": "acme",
            "name": "Alice",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 30
    assert body["expires_in"] > 0
    dev = body["developer"]
    assert dev["email"] == "alice@acme.com"
    assert dev["name"] == "Alice"
    assert dev["role"] == "owner"
    assert dev["org_name"] == "Acme Inc"
    assert dev["org_slug"] == "acme"
    assert dev["is_active"] is True


@pytest.mark.asyncio
async def test_register_duplicate_email_conflict(client):
    payload = {
        "email": "same@x.com",
        "password": "Password1",
        "org_name": "First",
        "org_slug": "first",
    }
    r1 = await client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201

    payload2 = {**payload, "org_name": "Second", "org_slug": "second"}
    r2 = await client.post("/api/v1/auth/register", json=payload2)
    assert r2.status_code == 409
    assert "email" in r2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_duplicate_org_slug_conflict(client):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "a@x.com",
            "password": "Password1",
            "org_name": "Org",
            "org_slug": "sameslug",
        },
    )
    r2 = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "b@x.com",
            "password": "Password1",
            "org_name": "OrgTwo",
            "org_slug": "sameslug",  # 冲突
        },
    )
    assert r2.status_code == 409
    assert "slug" in r2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_password_too_short(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "a@x.com",
            "password": "short",  # < 8
            "org_name": "O",
            "org_slug": "org",
        },
    )
    assert resp.status_code == 422  # pydantic validation


@pytest.mark.asyncio
async def test_register_invalid_org_slug(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "a@x.com",
            "password": "Password1",
            "org_name": "O",
            "org_slug": "Invalid Slug",  # 不符合 pattern
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "Password1",
            "org_name": "O",
            "org_slug": "org",
        },
    )
    assert resp.status_code == 422


# ───────────────────────── Login ─────────────────────────


@pytest.mark.asyncio
async def test_login_success_returns_token(client):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "bob@x.com",
            "password": "Password1",
            "org_name": "O",
            "org_slug": "org",
        },
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "bob@x.com", "password": "Password1"},
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


@pytest.mark.asyncio
async def test_login_wrong_password_401(client):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "c@x.com",
            "password": "CorrectPass1",
            "org_name": "O",
            "org_slug": "org",
        },
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "c@x.com", "password": "WrongPass"},
    )
    assert resp.status_code == 401
    assert "invalid credentials" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_login_unknown_email_401_same_message(client):
    """防用户枚举：不存在的 email 和密码错同一个错误消息"""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@x.com", "password": "whatever"},
    )
    assert resp.status_code == 401
    assert "invalid credentials" in resp.json()["detail"]


# ───────────────────────── /me ─────────────────────────


@pytest.mark.asyncio
async def test_me_returns_current_developer(client):
    r_register = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "dan@x.com",
            "password": "Password1",
            "org_name": "Danny Co",
            "org_slug": "danny",
        },
    )
    token = r_register.json()["access_token"]

    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "dan@x.com"
    assert body["role"] == "owner"


@pytest.mark.asyncio
async def test_me_without_token_401(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_with_invalid_token_401(client):
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-real-jwt"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_with_non_bearer_scheme_401(client):
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Basic somebase64"},
    )
    assert resp.status_code == 401

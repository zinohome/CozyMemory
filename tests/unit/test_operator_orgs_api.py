"""Operator orgs 路由 —— 列所有 Organization + 对应 dev/app 数。"""
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
BOOTSTRAP_KEY = "boot-orgs-test"

pytestmark = pytest.mark.skipif(
    os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true",
    reason="requires local postgres",
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
    _s.COZY_API_KEYS = BOOTSTRAP_KEY
    _s.DATABASE_URL = DATABASE_URL
    from cozymemory.db import engine as db_engine
    db_engine._engine = None
    db_engine._session_factory = None
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _seed(c):
    # 建两个 org。OrgA 有 1 dev + 1 app；OrgB 有 1 dev + 0 app。
    r = await c.post("/api/v1/auth/register", json={
        "email": "a@c.com", "password": "Password1",
        "org_name": "OrgA", "org_slug": "orga"})
    tok_a = r.json()["access_token"]
    await c.post(
        "/api/v1/dashboard/apps",
        headers={"Authorization": f"Bearer {tok_a}"},
        json={"name": "A1", "slug": "a1"},
    )
    await c.post("/api/v1/auth/register", json={
        "email": "b@c.com", "password": "Password1",
        "org_name": "OrgB", "org_slug": "orgb"})


@pytest.mark.asyncio
async def test_orgs_list_requires_bootstrap_key(client):
    await _seed(client)
    r = await client.get("/api/v1/operator/orgs")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_orgs_list_returns_all_orgs_with_counts(client):
    await _seed(client)
    r = await client.get(
        "/api/v1/operator/orgs",
        headers={"X-Cozy-API-Key": BOOTSTRAP_KEY},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    slugs = {row["slug"] for row in data["data"]}
    assert slugs == {"orga", "orgb"}
    orga = next(r for r in data["data"] if r["slug"] == "orga")
    assert orga["dev_count"] == 1
    assert orga["app_count"] == 1
    orgb = next(r for r in data["data"] if r["slug"] == "orgb")
    assert orgb["dev_count"] == 1
    assert orgb["app_count"] == 0

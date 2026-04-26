"""Knowledge 路由 per-App 归属隔离 (Step 8.15)."""
import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

from cozymemory.api.deps import get_knowledge_service
from cozymemory.app import create_app
from cozymemory.db.models import Base
from cozymemory.models.knowledge import (
    KnowledgeAddResponse,
    KnowledgeDataset,
    KnowledgeDatasetListResponse,
    KnowledgeDeleteResponse,
)

DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://cozymemory_user:cozymemory_pass@localhost:5433/cozymemory_test",
)
BOOTSTRAP_KEY = "bootstrap-kb-test"

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


DS_A_ID = "11111111-1111-4111-8111-111111111111"
DS_B_ID = "22222222-2222-4222-8222-222222222222"


@pytest.fixture
def mock_knowledge():
    svc = MagicMock()
    # create_dataset 返回刚创建的 ds；list 返回所有已知（app-隔离前）
    svc.create_dataset = AsyncMock(side_effect=lambda name: KnowledgeDatasetListResponse(
        success=True,
        data=[KnowledgeDataset(id=DS_A_ID if name == "dsA" else DS_B_ID, name=name)],
        message="created",
    ))
    svc.list_datasets = AsyncMock(return_value=KnowledgeDatasetListResponse(
        success=True,
        data=[
            KnowledgeDataset(id=DS_A_ID, name="dsA"),
            KnowledgeDataset(id=DS_B_ID, name="dsB"),
        ],
    ))
    svc.list_dataset_data = AsyncMock(return_value=MagicMock())
    svc.delete_dataset = AsyncMock(return_value=KnowledgeDeleteResponse(success=True, message=""))
    svc.get_dataset_graph = AsyncMock(return_value=MagicMock())
    svc.add = AsyncMock(return_value=KnowledgeAddResponse(
        success=True, data_id="data-1", dataset="dsNew", message=""
    ))
    return svc


@pytest.fixture
async def client(mock_knowledge):
    from cozymemory.config import settings as _s
    _s.COZY_API_KEYS = BOOTSTRAP_KEY
    _s.DATABASE_URL = DATABASE_URL
    from cozymemory.db import engine as db_engine
    db_engine._engine = None
    db_engine._session_factory = None
    app = create_app()
    app.dependency_overrides[get_knowledge_service] = lambda: mock_knowledge
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _make_app_key(c):
    r = await c.post("/api/v1/auth/register", json={
        "email": "dev@co.com", "password": "Password1",
        "org_name": "Co", "org_slug": "cokb"})
    token = r.json()["access_token"]
    r2 = await c.post("/api/v1/dashboard/apps",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "A", "slug": "aa"})
    app_id = r2.json()["id"]
    r3 = await c.post(f"/api/v1/dashboard/apps/{app_id}/keys",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "k"})
    return r3.json()["key"], app_id


async def _make_second_app(c):
    r = await c.post("/api/v1/auth/register", json={
        "email": "b@co.com", "password": "Password1",
        "org_name": "B", "org_slug": "bbkb"})
    token = r.json()["access_token"]
    r2 = await c.post("/api/v1/dashboard/apps",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "B", "slug": "bapp"})
    r3 = await c.post(f"/api/v1/dashboard/apps/{r2.json()['id']}/keys",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "k"})
    return r3.json()["key"]


@pytest.mark.asyncio
async def test_create_dataset_auto_registers_for_app(client):
    key, _ = await _make_app_key(client)
    r = await client.post(
        "/api/v1/knowledge/datasets?name=dsA",
        headers={"X-Cozy-API-Key": key},
    )
    assert r.status_code == 200
    # list via same key → sees dsA
    r2 = await client.get("/api/v1/knowledge/datasets", headers={"X-Cozy-API-Key": key})
    names = [d["name"] for d in r2.json()["data"]]
    assert "dsA" in names


@pytest.mark.asyncio
async def test_list_filters_to_owned_only(client):
    key_a, _ = await _make_app_key(client)
    await client.post("/api/v1/knowledge/datasets?name=dsA", headers={"X-Cozy-API-Key": key_a})
    key_b = await _make_second_app(client)
    r = await client.get("/api/v1/knowledge/datasets", headers={"X-Cozy-API-Key": key_b})
    names = [d["name"] for d in r.json()["data"]]
    assert "dsA" not in names


@pytest.mark.asyncio
async def test_bootstrap_sees_all(client):
    key_a, _ = await _make_app_key(client)
    await client.post("/api/v1/knowledge/datasets?name=dsA", headers={"X-Cozy-API-Key": key_a})
    # bootstrap 看全局
    r = await client.get("/api/v1/knowledge/datasets", headers={"X-Cozy-API-Key": BOOTSTRAP_KEY})
    names = [d["name"] for d in r.json()["data"]]
    # mock 的 list_datasets 会返 dsA 和 dsB（bootstrap 不过滤）
    assert "dsA" in names and "dsB" in names


@pytest.mark.asyncio
async def test_cross_app_dataset_get_returns_404(client):
    key_a, _ = await _make_app_key(client)
    await client.post("/api/v1/knowledge/datasets?name=dsA", headers={"X-Cozy-API-Key": key_a})
    key_b = await _make_second_app(client)
    # App B 尝试访问 App A 的 dsA
    r = await client.get(
        f"/api/v1/knowledge/datasets/{DS_A_ID}/data",
        headers={"X-Cozy-API-Key": key_b},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_cross_app_dataset_delete_returns_404(client):
    key_a, _ = await _make_app_key(client)
    await client.post("/api/v1/knowledge/datasets?name=dsA", headers={"X-Cozy-API-Key": key_a})
    key_b = await _make_second_app(client)
    r = await client.delete(
        f"/api/v1/knowledge/datasets/{DS_A_ID}",
        headers={"X-Cozy-API-Key": key_b},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_bootstrap_can_delete_any_dataset(client):
    key_a, _ = await _make_app_key(client)
    await client.post("/api/v1/knowledge/datasets?name=dsA", headers={"X-Cozy-API-Key": key_a})
    r = await client.delete(
        f"/api/v1/knowledge/datasets/{DS_A_ID}",
        headers={"X-Cozy-API-Key": BOOTSTRAP_KEY},
    )
    assert r.status_code == 200  # 经过 service.delete_dataset

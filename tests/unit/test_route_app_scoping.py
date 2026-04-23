"""业务路由 App 范围化端到端验证（Step 6）。

思路：打 App Key 和 bootstrap key 两次同样的请求，验证
    App Key → service 收到的 user_id 是 uuid5(namespace, ext_id)
    bootstrap → service 收到的 user_id 原样

不依赖真实 Mem0/Memobase；用 dependency_overrides 替换 service 层，
断言它拿到的 user_id 是期望值。

需要本机 PG + Redis；CI 自动跳过。
"""

import os
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

from cozymemory.api.deps import (
    get_context_service,
    get_conversation_service,
    get_profile_service,
)
from cozymemory.app import create_app
from cozymemory.db.models import Base
from cozymemory.models.context import ContextResponse
from cozymemory.models.conversation import ConversationMemoryListResponse
from cozymemory.models.profile import (
    ProfileAddItemResponse,
    ProfileGetResponse,
)

DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://cozymemory_user:cozymemory_pass@localhost:5433/cozymemory",
)
BOOTSTRAP_KEY = "bootstrap-scope-test"

pytestmark = pytest.mark.skipif(
    os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true",
    reason="requires local postgres + redis",
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
def mock_conv_service():
    svc = MagicMock()
    svc.add = AsyncMock(
        return_value=ConversationMemoryListResponse(success=True, data=[], total=0)
    )
    svc.get_all = AsyncMock(
        return_value=ConversationMemoryListResponse(success=True, data=[], total=0)
    )
    return svc


@pytest.fixture
def mock_profile_service():
    svc = MagicMock()
    svc.get_profile = AsyncMock(
        return_value=ProfileGetResponse(success=True, data=None)
    )
    svc.add_profile_item = AsyncMock(
        return_value=ProfileAddItemResponse(success=True, data=None)
    )
    return svc


@pytest.fixture
def mock_context_service():
    svc = MagicMock()
    svc.get_context = AsyncMock(
        return_value=ContextResponse(
            success=True,
            user_id="will-be-overwritten",
            conversations=[],
            profile_context=None,
            knowledge=[],
            errors={},
            latency_ms=1.0,
        )
    )
    return svc


@pytest.fixture
async def client(mock_conv_service, mock_profile_service, mock_context_service):
    from cozymemory.config import settings as _s

    _s.COZY_API_KEYS = BOOTSTRAP_KEY
    _s.DATABASE_URL = DATABASE_URL

    from cozymemory.db import engine as db_engine

    db_engine._engine = None
    db_engine._session_factory = None

    app = create_app()
    app.dependency_overrides[get_conversation_service] = lambda: mock_conv_service
    app.dependency_overrides[get_profile_service] = lambda: mock_profile_service
    app.dependency_overrides[get_context_service] = lambda: mock_context_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _create_app_and_key(client):
    """注册 + 建 App + 建 API Key。返回 (namespace_id, api_key)"""
    r1 = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "dev@co.com",
            "password": "Password1",
            "org_name": "Co",
            "org_slug": "co",
        },
    )
    assert r1.status_code == 201
    token = r1.json()["access_token"]

    r2 = await client.post(
        "/api/v1/dashboard/apps",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "App", "slug": "app"},
    )
    assert r2.status_code == 201
    namespace_id = uuid.UUID(r2.json()["namespace_id"])
    app_id = r2.json()["id"]

    r3 = await client.post(
        f"/api/v1/dashboard/apps/{app_id}/keys",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "k"},
    )
    assert r3.status_code == 201
    return namespace_id, r3.json()["key"]


# ─────────────── conversation.add ───────────────


@pytest.mark.asyncio
async def test_add_conversation_app_key_uses_uuid5(client, mock_conv_service):
    ns, api_key = await _create_app_and_key(client)
    ext_id = "ext_user_42"
    expected_uuid = uuid.uuid5(ns, ext_id)

    await client.post(
        "/api/v1/conversations",
        headers={"X-Cozy-API-Key": api_key},
        json={
            "user_id": ext_id,
            "messages": [{"role": "user", "content": "hi"}],
        },
    )

    mock_conv_service.add.assert_awaited_once()
    kwargs = mock_conv_service.add.await_args.kwargs
    assert kwargs["user_id"] == str(expected_uuid), (
        f"service 收到 {kwargs['user_id']}，期望 {expected_uuid}"
    )


@pytest.mark.asyncio
async def test_add_conversation_bootstrap_key_passes_through(client, mock_conv_service):
    """bootstrap key 行为不变：user_id 原样透传"""
    await client.post(
        "/api/v1/conversations",
        headers={"X-Cozy-API-Key": BOOTSTRAP_KEY},
        json={
            "user_id": "raw-user-id",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )
    mock_conv_service.add.assert_awaited_once()
    kwargs = mock_conv_service.add.await_args.kwargs
    assert kwargs["user_id"] == "raw-user-id"


# ─────────────── conversation.get_all ───────────────


@pytest.mark.asyncio
async def test_list_conversations_app_key_uses_uuid5(client, mock_conv_service):
    ns, api_key = await _create_app_and_key(client)
    ext_id = "list_user"
    expected = uuid.uuid5(ns, ext_id)

    await client.get(
        f"/api/v1/conversations?user_id={ext_id}",
        headers={"X-Cozy-API-Key": api_key},
    )
    kwargs = mock_conv_service.get_all.await_args.kwargs
    assert kwargs["user_id"] == str(expected)


# ─────────────── profile.get ───────────────


@pytest.mark.asyncio
async def test_get_profile_app_key_uses_uuid5(client, mock_profile_service):
    ns, api_key = await _create_app_and_key(client)
    ext_id = "profile_user"
    expected = uuid.uuid5(ns, ext_id)

    await client.get(
        f"/api/v1/profiles/{ext_id}",
        headers={"X-Cozy-API-Key": api_key},
    )
    # get_profile 是 positional arg
    args = mock_profile_service.get_profile.await_args.args
    assert args[0] == str(expected)


@pytest.mark.asyncio
async def test_get_profile_bootstrap_passes_through(client, mock_profile_service):
    await client.get(
        "/api/v1/profiles/raw-user",
        headers={"X-Cozy-API-Key": BOOTSTRAP_KEY},
    )
    args = mock_profile_service.get_profile.await_args.args
    assert args[0] == "raw-user"


# ─────────────── profile.add_item ───────────────


@pytest.mark.asyncio
async def test_add_profile_item_app_key_uses_uuid5(client, mock_profile_service):
    ns, api_key = await _create_app_and_key(client)
    ext_id = "p_item_user"
    expected = uuid.uuid5(ns, ext_id)

    await client.post(
        f"/api/v1/profiles/{ext_id}/items",
        headers={"X-Cozy-API-Key": api_key},
        json={"topic": "hobby", "sub_topic": "sport", "content": "basketball"},
    )
    kwargs = mock_profile_service.add_profile_item.await_args.kwargs
    assert kwargs["user_id"] == str(expected)


# ─────────────── context ───────────────


@pytest.mark.asyncio
async def test_context_app_key_uses_uuid5(client, mock_context_service):
    ns, api_key = await _create_app_and_key(client)
    ext_id = "ctx_user"
    expected = uuid.uuid5(ns, ext_id)

    await client.post(
        "/api/v1/context",
        headers={"X-Cozy-API-Key": api_key},
        json={"user_id": ext_id, "query": "hello"},
    )
    # ContextService.get_context(req) 拿 req.user_id
    call = mock_context_service.get_context.await_args
    req = call.args[0]
    assert req.user_id == str(expected)


@pytest.mark.asyncio
async def test_context_bootstrap_passes_through(client, mock_context_service):
    await client.post(
        "/api/v1/context",
        headers={"X-Cozy-API-Key": BOOTSTRAP_KEY},
        json={"user_id": "raw-ctx", "query": "hello"},
    )
    req = mock_context_service.get_context.await_args.args[0]
    assert req.user_id == "raw-ctx"


# ─────────────── 跨 App 隔离（真场景）───────────────


@pytest.mark.asyncio
async def test_two_apps_same_ext_id_get_different_uuid(client, mock_conv_service):
    """模拟两个 App 用同样的 external user_id 调 POST /conversations，
    service 看到的内部 UUID 必须不同 → 证明数据隔离有效。"""
    ns_a, key_a = await _create_app_and_key(client)
    # 注册第二个 org + app
    r = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "b@co.com",
            "password": "Password1",
            "org_name": "B",
            "org_slug": "bb",
        },
    )
    token_b = r.json()["access_token"]
    app_b = (
        await client.post(
            "/api/v1/dashboard/apps",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"name": "B App", "slug": "b-app"},
        )
    ).json()
    ns_b = uuid.UUID(app_b["namespace_id"])
    key_b = (
        await client.post(
            f"/api/v1/dashboard/apps/{app_b['id']}/keys",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"name": "k"},
        )
    ).json()["key"]

    same_ext = "shared_user"
    await client.post(
        "/api/v1/conversations",
        headers={"X-Cozy-API-Key": key_a},
        json={"user_id": same_ext, "messages": [{"role": "user", "content": "x"}]},
    )
    await client.post(
        "/api/v1/conversations",
        headers={"X-Cozy-API-Key": key_b},
        json={"user_id": same_ext, "messages": [{"role": "user", "content": "y"}]},
    )

    calls = mock_conv_service.add.await_args_list
    uid_a = calls[0].kwargs["user_id"]
    uid_b = calls[1].kwargs["user_id"]
    assert uid_a == str(uuid.uuid5(ns_a, same_ext))
    assert uid_b == str(uuid.uuid5(ns_b, same_ext))
    assert uid_a != uid_b  # 核心断言：数据物理上隔离

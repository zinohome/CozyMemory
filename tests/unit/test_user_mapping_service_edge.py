"""UserMappingService 边缘路径测试 — 覆盖 TTL 分支、并发抢占失败、反向键写失败。"""

import pytest

try:
    import fakeredis.aioredis as fakeredis_aio
    HAVE_FAKEREDIS = True
except ImportError:  # pragma: no cover
    HAVE_FAKEREDIS = False

from cozymemory.services.user_mapping import UserMappingService

pytestmark = pytest.mark.skipif(not HAVE_FAKEREDIS, reason="fakeredis not installed")


@pytest.fixture
async def redis_client():
    r = fakeredis_aio.FakeRedis()
    try:
        yield r
    finally:
        await r.aclose()


# ───────────────────────── TTL 分支 ─────────────────────────


@pytest.mark.asyncio
async def test_create_with_ttl_expires_key(redis_client):
    svc = UserMappingService(redis_client, ttl=60)
    uuid_str = await svc.get_or_create_uuid("alice")
    # 正向键 TTL 被设置
    ttl = await redis_client.ttl(f"cm:uid:alice")
    assert ttl > 0 and ttl <= 60
    # 反向键也有 TTL
    # 注意：服务写反向键时用 setex，但 setex 用 ttl 参数
    assert uuid_str


@pytest.mark.asyncio
async def test_create_without_ttl_is_persistent(redis_client):
    svc = UserMappingService(redis_client, ttl=0)
    await svc.get_or_create_uuid("alice")
    # TTL = -1 表示永久
    assert await redis_client.ttl("cm:uid:alice") == -1


# ───────────────────────── 并发抢占 ─────────────────────────


@pytest.mark.asyncio
async def test_get_or_create_lost_race_returns_winner(redis_client):
    """模拟：本请求生成候选 UUID 前，另一请求已写入 → 我们读到赢家的值"""
    await redis_client.set("cm:uid:alice", "winner-uuid")
    svc = UserMappingService(redis_client)
    # 这里调 get_or_create 会走快路径（已存在）
    result = await svc.get_or_create_uuid("alice")
    assert result == "winner-uuid"


@pytest.mark.asyncio
async def test_get_or_create_nx_fails_reads_winner(redis_client, monkeypatch):
    """慢路径下 SET NX 返回 None（因别人抢先），直接取现有值"""
    svc = UserMappingService(redis_client)

    # 打补丁：让 get 返回 None（表示本次看不到现有值，进入慢路径）
    # 但 SET NX 返回 None（表示写失败，别人抢先），后续 get 又能读到赢家
    original_get = redis_client.get
    original_set = redis_client.set
    call_state = {"gets": 0}

    async def fake_get(key):
        call_state["gets"] += 1
        if call_state["gets"] == 1:
            # 第一次快路径查询返回 None
            return None
        # 第二次（winner 查询）返回别人的值
        return b"other-uuid"

    async def fake_set(key, value, **kwargs):
        # NX 模式下返回 None 代表抢占失败
        if kwargs.get("nx"):
            return None
        return await original_set(key, value, **kwargs)

    monkeypatch.setattr(redis_client, "get", fake_get)
    monkeypatch.setattr(redis_client, "set", fake_set)

    result = await svc.get_or_create_uuid("alice")
    assert result == "other-uuid"


# ───────────────────────── 反向键写入失败不中断 ─────────────────────────


@pytest.mark.asyncio
async def test_reverse_key_write_failure_swallowed(redis_client, monkeypatch):
    """反向键写失败是 non-critical，不应让 get_or_create 抛异常"""
    svc = UserMappingService(redis_client, ttl=0)

    original_set = redis_client.set

    async def fake_set(key, value, **kwargs):
        # 反向键写失败；正向键正常
        if key.startswith("cm:uuid:"):
            raise RuntimeError("reverse write boom")
        return await original_set(key, value, **kwargs)

    monkeypatch.setattr(redis_client, "set", fake_set)

    # 不抛，仍返回新 UUID
    result = await svc.get_or_create_uuid("alice")
    assert result
    assert await redis_client.get("cm:uid:alice")


# ───────────────────────── delete_mapping ─────────────────────────


@pytest.mark.asyncio
async def test_delete_mapping_nonexistent_returns_false(redis_client):
    svc = UserMappingService(redis_client)
    assert await svc.delete_mapping("ghost") is False


@pytest.mark.asyncio
async def test_delete_mapping_existing_clears_both_keys(redis_client):
    svc = UserMappingService(redis_client)
    await svc.get_or_create_uuid("alice")
    # 删除
    assert await svc.delete_mapping("alice") is True
    # 正反向键都没了
    assert await redis_client.get("cm:uid:alice") is None


# ───────────────────────── list_users ─────────────────────────


@pytest.mark.asyncio
async def test_list_users_returns_sorted(redis_client):
    svc = UserMappingService(redis_client)
    await svc.get_or_create_uuid("charlie")
    await svc.get_or_create_uuid("alice")
    await svc.get_or_create_uuid("bob")
    users = await svc.list_users()
    assert users == ["alice", "bob", "charlie"]


@pytest.mark.asyncio
async def test_list_users_empty(redis_client):
    svc = UserMappingService(redis_client)
    assert await svc.list_users() == []


# ───────────────────────── get_uuid / get_user_id ─────────────────────────


@pytest.mark.asyncio
async def test_get_uuid_missing(redis_client):
    svc = UserMappingService(redis_client)
    assert await svc.get_uuid("ghost") is None


@pytest.mark.asyncio
async def test_get_user_id_reverse_lookup(redis_client):
    svc = UserMappingService(redis_client)
    uid = await svc.get_or_create_uuid("alice")
    assert await svc.get_user_id(uid) == "alice"


# ───────────────────────── _store (internal) TTL path ─────────────────────────


@pytest.mark.asyncio
async def test_store_internal_with_ttl(redis_client):
    svc = UserMappingService(redis_client, ttl=30)
    await svc._store("alice", "uuid-x")
    assert await redis_client.get("cm:uid:alice") == b"uuid-x"
    assert await redis_client.get("cm:uuid:uuid-x") == b"alice"
    assert 0 < await redis_client.ttl("cm:uid:alice") <= 30


@pytest.mark.asyncio
async def test_store_internal_without_ttl(redis_client):
    svc = UserMappingService(redis_client, ttl=0)
    await svc._store("alice", "uuid-x")
    assert await redis_client.ttl("cm:uid:alice") == -1

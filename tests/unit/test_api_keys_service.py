"""ApiKeyStore 测试 — 用 fakeredis 做 Redis 后端，验证完整 CRUD 流程。

覆盖：
  - create / list / rotate / update / delete 的幂等性和返回值
  - verify_and_touch 命中/未命中/disabled 三种路径
  - 轮换后旧明文失效、新明文有效
  - 禁用 key 无法通过鉴权但 list 仍显示
  - 审计日志 LPUSH + LTRIM 保留最近 N 条
"""

import pytest
import redis.asyncio as aioredis

try:
    import fakeredis.aioredis as fakeredis_aio
    HAVE_FAKEREDIS = True
except ImportError:  # pragma: no cover
    HAVE_FAKEREDIS = False

from cozymemory.services.api_keys import (
    _LOG_MAX_ENTRIES,
    ApiKeyStore,
    _generate_key,
    _hash_key,
)

pytestmark = pytest.mark.skipif(
    not HAVE_FAKEREDIS, reason="fakeredis not installed"
)


@pytest.fixture
async def redis_client() -> aioredis.Redis:
    r = fakeredis_aio.FakeRedis()
    try:
        yield r
    finally:
        await r.aclose()


@pytest.fixture
async def store(redis_client):
    return ApiKeyStore(redis_client)


# ───────────────────────── 内部辅助函数 ─────────────────────────


def test_hash_key_deterministic():
    assert _hash_key("abc") == _hash_key("abc")
    assert _hash_key("a") != _hash_key("b")
    # sha256 输出 64 字符 hex
    assert len(_hash_key("x")) == 64


def test_generate_key_shape():
    plaintext, prefix = _generate_key()
    # cozy_<32 hex>_<48 hex>
    assert plaintext.startswith("cozy_")
    assert len(plaintext) == len("cozy_") + 32 + 1 + 48
    assert prefix == plaintext[:14]
    # 每次都不同
    p2, _ = _generate_key()
    assert plaintext != p2


# ───────────────────────── create / list ─────────────────────────


@pytest.mark.asyncio
async def test_create_returns_plaintext_and_record(store):
    resp = await store.create(name="prod-backend")
    assert resp.key.startswith("cozy_")
    assert resp.record.name == "prod-backend"
    assert resp.record.prefix == resp.key[:14]
    assert resp.record.disabled is False
    assert resp.record.last_used_at is None


@pytest.mark.asyncio
async def test_create_multiple_and_list(store):
    a = await store.create(name="a")
    b = await store.create(name="b")
    records = await store.list_keys()
    assert len(records) == 2
    ids = {r.id for r in records}
    assert a.record.id in ids and b.record.id in ids
    # 按 created_at 倒序
    assert records[0].created_at >= records[1].created_at


@pytest.mark.asyncio
async def test_list_empty_initially(store):
    assert await store.list_keys() == []


# ───────────────────────── verify_and_touch ─────────────────────────


@pytest.mark.asyncio
async def test_verify_success_returns_id(store):
    resp = await store.create(name="x")
    kid = await store.verify_and_touch(resp.key)
    assert kid == resp.record.id


@pytest.mark.asyncio
async def test_verify_updates_last_used_at(store):
    resp = await store.create(name="x")
    assert resp.record.last_used_at is None
    await store.verify_and_touch(resp.key)
    records = await store.list_keys()
    rec = next(r for r in records if r.id == resp.record.id)
    assert rec.last_used_at is not None


@pytest.mark.asyncio
async def test_verify_empty_plaintext_is_none(store):
    assert await store.verify_and_touch("") is None


@pytest.mark.asyncio
async def test_verify_unknown_key_is_none(store):
    assert await store.verify_and_touch("cozy_not_real") is None


@pytest.mark.asyncio
async def test_verify_disabled_key_rejected(store):
    resp = await store.create(name="x")
    await store.update(resp.record.id, disabled=True)
    assert await store.verify_and_touch(resp.key) is None


# ───────────────────────── rotate ─────────────────────────


@pytest.mark.asyncio
async def test_rotate_invalidates_old_key(store):
    resp = await store.create(name="x")
    old_plain = resp.key
    rotated = await store.rotate(resp.record.id)
    assert rotated is not None
    assert rotated.key != old_plain
    # 旧 key 不再通过
    assert await store.verify_and_touch(old_plain) is None
    # 新 key 通过
    assert await store.verify_and_touch(rotated.key) == resp.record.id


@pytest.mark.asyncio
async def test_rotate_unknown_id_returns_none(store):
    assert await store.rotate("not-a-real-id") is None


@pytest.mark.asyncio
async def test_rotate_preserves_name_and_id(store):
    resp = await store.create(name="preserve-me")
    rotated = await store.rotate(resp.record.id)
    assert rotated.record.id == resp.record.id
    assert rotated.record.name == "preserve-me"


# ───────────────────────── update ─────────────────────────


@pytest.mark.asyncio
async def test_update_name_only(store):
    resp = await store.create(name="old")
    updated = await store.update(resp.record.id, name="new")
    assert updated.name == "new"
    assert updated.disabled is False


@pytest.mark.asyncio
async def test_update_disabled_only(store):
    resp = await store.create(name="x")
    updated = await store.update(resp.record.id, disabled=True)
    assert updated.disabled is True
    assert updated.name == "x"


@pytest.mark.asyncio
async def test_update_unknown_id_is_none(store):
    assert await store.update("not-real", name="x") is None


# ───────────────────────── delete ─────────────────────────


@pytest.mark.asyncio
async def test_delete_removes_and_invalidates(store):
    resp = await store.create(name="x")
    assert await store.delete(resp.record.id) is True
    # 列表里没了
    assert await store.list_keys() == []
    # 明文也认证不过了
    assert await store.verify_and_touch(resp.key) is None


@pytest.mark.asyncio
async def test_delete_unknown_id_returns_false(store):
    assert await store.delete("not-real") is False


# ───────────────────────── 审计日志 ─────────────────────────


@pytest.mark.asyncio
async def test_record_and_get_logs(store):
    resp = await store.create(name="x")
    await store.record_usage(resp.record.id, "GET", "/users", 200)
    await store.record_usage(resp.record.id, "POST", "/conversations", 201)
    logs = await store.get_logs(resp.record.id, limit=10)
    # LPUSH 所以最新的在前
    assert len(logs) == 2
    assert logs[0].path == "/conversations"
    assert logs[0].status == 201
    assert logs[1].path == "/users"


@pytest.mark.asyncio
async def test_get_logs_empty(store):
    resp = await store.create(name="x")
    assert await store.get_logs(resp.record.id) == []


@pytest.mark.asyncio
async def test_record_usage_ltrim_enforces_max(store, redis_client):
    resp = await store.create(name="x")
    # 写 _LOG_MAX_ENTRIES + 5 条，验证只保留前 _LOG_MAX_ENTRIES 条
    for i in range(_LOG_MAX_ENTRIES + 5):
        await store.record_usage(resp.record.id, "GET", f"/p{i}", 200)
    # 直接读 Redis 长度验证
    log_key = f"cozy:apikey:log:{resp.record.id}"
    length = await redis_client.llen(log_key)
    assert length == _LOG_MAX_ENTRIES


@pytest.mark.asyncio
async def test_record_usage_swallows_exceptions(monkeypatch, store):
    """record_usage 的失败必须不抛，不能影响主请求"""

    async def boom(*_a, **_kw):
        raise RuntimeError("redis dead")

    # 把 pipeline 打坏
    monkeypatch.setattr(
        store._r, "pipeline", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("x"))
    )
    # 应该静默不抛
    await store.record_usage("any-id", "GET", "/x", 200)


@pytest.mark.asyncio
async def test_get_logs_skips_malformed_entries(store, redis_client):
    resp = await store.create(name="x")
    log_key = f"cozy:apikey:log:{resp.record.id}"
    await redis_client.lpush(log_key, "not-json")
    await redis_client.lpush(log_key, '{"missing": "fields"}')
    # 合法一条
    await store.record_usage(resp.record.id, "GET", "/ok", 200)
    logs = await store.get_logs(resp.record.id)
    # 只有合法那条进结果
    assert len(logs) == 1
    assert logs[0].path == "/ok"

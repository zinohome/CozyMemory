"""UserResolver 测试 — uuid5 映射 + PG upsert 幂等 + Redis 缓存。

需要本机 PG + Redis；CI 自动跳过。
"""

import os
import uuid

import pytest
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from cozymemory.db.models import App, Base, Organization
from cozymemory.services.user_resolver import (
    UserResolver,
    compute_internal_uuid,
)

DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://cozymemory_user:cozymemory_pass@localhost:5433/cozymemory",
)
REDIS_URL = os.getenv("TEST_REDIS_URL", "redis://localhost:6379/14")

pytestmark = pytest.mark.skipif(
    os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true",
    reason="requires local postgres + redis",
)


@pytest.fixture
async def redis_client():
    """独立测试用 Redis DB（db=14），每个测试前后清空。"""
    try:
        client = aioredis.from_url(REDIS_URL, decode_responses=False)
        await client.flushdb()
        yield client
        await client.flushdb()
        await client.aclose()
    except Exception:
        pytest.skip("Redis unreachable")


@pytest.fixture
async def session():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest.fixture
async def app(session):
    """建一个 Org + App，返回 App 记录。"""
    org = Organization(name="TestOrg", slug="testorg")
    session.add(org)
    await session.flush()
    a = App(org_id=org.id, name="App", slug="app")
    session.add(a)
    await session.commit()
    await session.refresh(a)
    return a


@pytest.fixture
async def resolver(session, redis_client):
    return UserResolver(session, redis_client)


# ───────────────────────── uuid5 确定性 ─────────────────────────


def test_compute_internal_uuid_is_deterministic():
    ns = uuid.UUID("12345678-1234-5678-1234-567812345678")
    u1 = compute_internal_uuid(ns, "ext_user_1")
    u2 = compute_internal_uuid(ns, "ext_user_1")
    assert u1 == u2


def test_compute_internal_uuid_different_namespace_different_uuid():
    ns1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
    ns2 = uuid.UUID("22222222-2222-2222-2222-222222222222")
    u1 = compute_internal_uuid(ns1, "same_ext_id")
    u2 = compute_internal_uuid(ns2, "same_ext_id")
    assert u1 != u2


def test_compute_internal_uuid_different_ext_id_different_uuid():
    ns = uuid.UUID("11111111-1111-1111-1111-111111111111")
    u1 = compute_internal_uuid(ns, "a")
    u2 = compute_internal_uuid(ns, "b")
    assert u1 != u2


# ───────────────────────── resolve (整合 PG + Redis) ─────────────────────────


@pytest.mark.asyncio
async def test_resolve_first_call_creates_pg_record(resolver, session, app):
    uid = await resolver.resolve(app, "alice")
    await session.commit()

    # 验证 uuid 确实是 uuid5
    assert uid == uuid.uuid5(app.namespace_id, "alice")
    # 验证 PG 里有了记录
    record = await resolver.get(app.id, "alice")
    assert record is not None
    assert record.internal_uuid == uid


@pytest.mark.asyncio
async def test_resolve_same_args_returns_same_uuid(resolver, session, app):
    u1 = await resolver.resolve(app, "bob")
    await session.commit()
    u2 = await resolver.resolve(app, "bob")
    await session.commit()
    assert u1 == u2


@pytest.mark.asyncio
async def test_resolve_cross_app_same_ext_id_different_uuid(
    resolver, session, app
):
    """同一 org 下 app A 和 app B，同个 ext_id → 不同 UUID"""
    org = (await session.execute(__import__("sqlalchemy").select(Organization))).scalar_one()
    app_b = App(org_id=org.id, name="AppB", slug="app-b")
    session.add(app_b)
    await session.commit()
    await session.refresh(app_b)

    u_a = await resolver.resolve(app, "shared_ext_id")
    u_b = await resolver.resolve(app_b, "shared_ext_id")
    await session.commit()
    assert u_a != u_b


@pytest.mark.asyncio
async def test_resolve_sets_redis_cache(resolver, redis_client, session, app):
    await resolver.resolve(app, "cached_user")
    await session.commit()
    cache_key = f"cm:app:{app.id}:uid:cached_user"
    assert await redis_client.exists(cache_key) == 1


@pytest.mark.asyncio
async def test_resolve_empty_external_id_raises(resolver, app):
    with pytest.raises(ValueError):
        await resolver.resolve(app, "")


@pytest.mark.asyncio
async def test_resolve_redis_down_still_works(session, app, monkeypatch):
    """Redis 挂了不应阻塞：走 PG upsert + 跳过缓存写"""

    class BrokenRedis:
        async def exists(self, *args, **kwargs):
            raise RuntimeError("redis boom")

        async def setex(self, *args, **kwargs):
            raise RuntimeError("redis boom")

        async def delete(self, *args, **kwargs):
            raise RuntimeError("redis boom")

    r = UserResolver(session, BrokenRedis())
    uid = await r.resolve(app, "user_x")
    await session.commit()
    # 仍能解出 UUID，PG 仍有记录
    assert uid == uuid.uuid5(app.namespace_id, "user_x")
    rec = await r.get(app.id, "user_x")
    assert rec is not None


# ───────────────────────── list / count / delete ─────────────────────────


@pytest.mark.asyncio
async def test_list_for_app(resolver, session, app):
    for name in ["alice", "bob", "charlie"]:
        await resolver.resolve(app, name)
    await session.commit()

    rows = await resolver.list_for_app(app.id)
    assert len(rows) == 3
    assert {r.external_user_id for r in rows} == {"alice", "bob", "charlie"}


@pytest.mark.asyncio
async def test_list_for_app_pagination(resolver, session, app):
    for i in range(5):
        await resolver.resolve(app, f"user_{i}")
    await session.commit()
    page1 = await resolver.list_for_app(app.id, limit=2, offset=0)
    page2 = await resolver.list_for_app(app.id, limit=2, offset=2)
    assert len(page1) == 2
    assert len(page2) == 2
    # 无重叠
    ids1 = {r.external_user_id for r in page1}
    ids2 = {r.external_user_id for r in page2}
    assert ids1 & ids2 == set()


@pytest.mark.asyncio
async def test_count_for_app(resolver, session, app):
    assert await resolver.count_for_app(app.id) == 0
    await resolver.resolve(app, "u1")
    await resolver.resolve(app, "u2")
    await session.commit()
    assert await resolver.count_for_app(app.id) == 2


@pytest.mark.asyncio
async def test_get_missing_returns_none(resolver, app):
    assert await resolver.get(app.id, "nonexistent") is None


@pytest.mark.asyncio
async def test_delete_existing(resolver, session, app, redis_client):
    await resolver.resolve(app, "to_delete")
    await session.commit()
    cache_key = f"cm:app:{app.id}:uid:to_delete"
    assert await redis_client.exists(cache_key) == 1

    assert await resolver.delete(app.id, "to_delete") is True
    await session.commit()

    # PG 没了
    assert await resolver.get(app.id, "to_delete") is None
    # Redis 缓存也清了
    assert await redis_client.exists(cache_key) == 0


@pytest.mark.asyncio
async def test_delete_missing_returns_false(resolver, app):
    assert await resolver.delete(app.id, "ghost") is False


# ───────────────────────── 幂等性（并发模拟） ─────────────────────────


@pytest.mark.asyncio
async def test_resolve_concurrent_same_user_only_one_row(resolver, session, app):
    """两次 resolve 同 user，PG 里只有一条记录（ON CONFLICT DO NOTHING）"""
    # 第一次：新建记录 + 写 Redis 缓存
    u1 = await resolver.resolve(app, "race_user")
    await session.commit()
    # 手动删 Redis 缓存，模拟缓存过期 / 第二次请求的 resolver 实例
    await resolver.redis.delete(f"cm:app:{app.id}:uid:race_user")
    # 第二次：PG 里已有，upsert ON CONFLICT DO NOTHING
    u2 = await resolver.resolve(app, "race_user")
    await session.commit()
    assert u1 == u2
    assert await resolver.count_for_app(app.id) == 1

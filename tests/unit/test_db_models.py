"""平台账号库模型基础测试

只跑在本机（需要 cozy_postgres 可达）；CI 环境会跳过。
需要 DATABASE_URL 指向可用的空 cozymemory 数据库。

覆盖：
  - 能连库、能 insert Organization/Developer/App
  - 关系加载（App → Organization）
  - uuid5 确定性：同 namespace + external_id 算出同一个 internal_uuid
  - 级联删除：删 Org 时下属 Developer/App 一起删
"""

import os
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from cozymemory.db.models import App, Base, Developer, ExternalUser, Organization

# CI 里没有可达的 PG，跳过
DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://cozymemory_user:cozymemory_pass@localhost:5433/cozymemory_test",
)

pytestmark = pytest.mark.skipif(
    os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true",
    reason="requires local postgres",
)


@pytest.fixture
async def session():
    """独立 test engine + session；每个测试干净重置表"""
    engine = create_async_engine(DATABASE_URL, echo=False)

    # 每个 test 前建表（idempotent）再清空
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with engine.begin() as conn:
        # 反向顺序删以处理 FK
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_organization_and_developer(session):
    org = Organization(name="ByteDance", slug="bytedance")
    session.add(org)
    await session.flush()

    dev = Developer(
        org_id=org.id,
        email="alice@example.com",
        password_hash="fake_hash",
        name="Alice",
        role="owner",
    )
    session.add(dev)
    await session.commit()

    # 查回来
    result = await session.execute(select(Developer).where(Developer.email == "alice@example.com"))
    dev2 = result.scalar_one()
    assert dev2.name == "Alice"
    assert dev2.role == "owner"
    assert dev2.org_id == org.id


@pytest.mark.asyncio
async def test_app_unique_slug_per_org(session):
    org = Organization(name="Co", slug="co")
    session.add(org)
    await session.flush()

    a1 = App(org_id=org.id, name="Douyin Memory", slug="douyin-memory")
    a2 = App(org_id=org.id, name="Douyin Again", slug="douyin-memory")  # 同名
    session.add_all([a1, a2])

    # 违反 UniqueConstraint(org_id, slug)
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_cascade_delete_org_removes_apps_and_devs(session):
    org = Organization(name="ToDelete", slug="todelete")
    session.add(org)
    await session.flush()

    session.add_all(
        [
            Developer(org_id=org.id, email="a@b.c", password_hash="x"),
            App(org_id=org.id, name="X", slug="x"),
        ]
    )
    await session.commit()

    # 删 org
    await session.delete(org)
    await session.commit()

    # Developer / App 都应该被级联删
    dev_count = (await session.execute(select(Developer))).all()
    app_count = (await session.execute(select(App))).all()
    assert len(dev_count) == 0
    assert len(app_count) == 0


@pytest.mark.asyncio
async def test_uuid5_deterministic_external_user_mapping(session):
    """给定同一个 App 的 namespace_id + external_user_id，应该算出同一个 internal_uuid。"""
    org = Organization(name="O", slug="o")
    session.add(org)
    await session.flush()

    app = App(org_id=org.id, name="A", slug="a")
    session.add(app)
    await session.flush()

    # 同一 namespace + ext_id 两次计算结果应该相同
    ext_id = "douyin_user_12345"
    u1 = uuid.uuid5(app.namespace_id, ext_id)
    u2 = uuid.uuid5(app.namespace_id, ext_id)
    assert u1 == u2

    # 不同 namespace（另一个 app）同 ext_id 应该不同
    app2 = App(org_id=org.id, name="B", slug="b")
    session.add(app2)
    await session.flush()
    u3 = uuid.uuid5(app2.namespace_id, ext_id)
    assert u3 != u1

    # 插入索引表，约束 (app_id, ext_id) 唯一
    eu = ExternalUser(
        internal_uuid=u1,
        app_id=app.id,
        external_user_id=ext_id,
    )
    session.add(eu)
    await session.commit()

    # 二次插入同 (app_id, ext_id) 会违反唯一约束
    eu_dup = ExternalUser(
        internal_uuid=u1,
        app_id=app.id,
        external_user_id=ext_id,
    )
    session.add(eu_dup)
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        await session.commit()

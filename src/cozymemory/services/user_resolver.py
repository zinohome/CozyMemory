"""External user_id → internal UUID 映射服务。

这是多租户数据隔离的核心：
  internal_uuid = uuid5(app.namespace_id, external_user_id)
  三引擎（Mem0/Memobase/Cognee）都用同一个 internal_uuid 作 user_id。

为什么用 uuid5 而不是随机 uuid4：
  - 确定性：给定同 (app_ns, ext_id) 永远算出同 UUID
  - Redis 丢数据不影响底层引擎数据归属（可重算）
  - Memobase 兼容（UUID 格式符合）

PG external_users 表的作用：
  - 列出 App 下所有 user（dashboard 用）
  - GDPR 级联删除时枚举 external_user_id
  - 审计：创建时间

Redis 的作用：
  - cm:app:{app_id}:uid:{ext_id} → "1"（TTL 7d）
    仅作为"已 upsert PG"的标记，命中即可跳过 upsert 减少写负载
  - UUID 本身不走缓存（确定性，每次都能重算）
"""

from __future__ import annotations

import uuid
from uuid import UUID

import redis.asyncio as aioredis
import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import App, ExternalUser

logger = structlog.get_logger()

_CACHE_PREFIX = "cm:app:"
_CACHE_TTL = 7 * 86400  # 7 天


def _cache_key(app_id: UUID, external_user_id: str) -> str:
    return f"{_CACHE_PREFIX}{app_id}:uid:{external_user_id}"


def compute_internal_uuid(app_namespace_id: UUID, external_user_id: str) -> UUID:
    """无副作用 — 算 uuid5。可在路由 / 测试 / 迁移脚本里独立使用。"""
    return uuid.uuid5(app_namespace_id, external_user_id)


class UserResolver:
    """把外部 app 传进来的 user_id 字符串解析成内部稳定 UUID。"""

    def __init__(self, session: AsyncSession, redis: aioredis.Redis) -> None:
        self.session = session
        self.redis = redis

    async def resolve(self, app: App, external_user_id: str) -> UUID:
        """拿到（可能首次创建）内部 UUID。线程/协程安全：PG 幂等 upsert。

        调用方在路由里拿到此 UUID 后，传给 Mem0/Memobase/Cognee 作 user_id。
        事务由 caller（FastAPI Depends(get_session)）统一管理。
        """
        if not external_user_id:
            raise ValueError("external_user_id 不能为空")

        internal_uuid = compute_internal_uuid(app.namespace_id, external_user_id)

        cache_key = _cache_key(app.id, external_user_id)
        try:
            hit = await self.redis.exists(cache_key)
        except Exception:
            hit = 0  # Redis 挂了不阻塞主流程，走 PG upsert 路径

        if not hit:
            # 幂等 upsert：unique (app_id, external_user_id)
            # ON CONFLICT DO NOTHING，避免并发两个请求同 ext_id 造成重复
            stmt = (
                pg_insert(ExternalUser)
                .values(
                    internal_uuid=internal_uuid,
                    app_id=app.id,
                    external_user_id=external_user_id,
                )
                .on_conflict_do_nothing(index_elements=["app_id", "external_user_id"])
            )
            await self.session.execute(stmt)
            # 缓存 TTL，下次请求同 user 跳过 upsert
            try:
                await self.redis.setex(cache_key, _CACHE_TTL, "1")
            except Exception:
                pass
            logger.info(
                "user_resolver.resolve.upserted",
                app_id=str(app.id),
                external_user_id=external_user_id,
                internal_uuid=str(internal_uuid),
            )

        return internal_uuid

    async def list_for_app(
        self, app_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[ExternalUser]:
        """分页列出 App 下的 external users。给 dashboard 用。"""
        result = await self.session.execute(
            select(ExternalUser)
            .where(ExternalUser.app_id == app_id)
            .order_by(ExternalUser.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_for_app(self, app_id: UUID) -> int:
        """App 下 user 总数。"""
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count())
            .select_from(ExternalUser)
            .where(ExternalUser.app_id == app_id)
        )
        return int(result.scalar() or 0)

    async def get(self, app_id: UUID, external_user_id: str) -> ExternalUser | None:
        """查单个 mapping。不存在返 None（不创建）。"""
        result = await self.session.execute(
            select(ExternalUser).where(
                ExternalUser.app_id == app_id,
                ExternalUser.external_user_id == external_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def delete(self, app_id: UUID, external_user_id: str) -> bool:
        """从索引删除一个 mapping（GDPR 级联删除的第一步）。

        返回 True 表示删除了一条；False 表示原本就不存在。
        注意：不会级联到 Mem0/Memobase/Cognee 的数据 — 那是上层服务的责任。
        """
        record = await self.get(app_id, external_user_id)
        if record is None:
            return False
        await self.session.delete(record)
        try:
            await self.redis.delete(_cache_key(app_id, external_user_id))
        except Exception:
            pass
        logger.info(
            "user_resolver.deleted",
            app_id=str(app_id),
            external_user_id=external_user_id,
        )
        return True

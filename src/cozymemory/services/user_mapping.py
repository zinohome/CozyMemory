"""用户 ID 映射服务

Memobase 要求 user_id 必须是 UUID v4。
本服务使用 Redis 在任意字符串 user_id 和 UUID v4 之间建立双向映射，
使调用方可以使用自己的 ID 格式而不必关心底层引擎的约束。

Redis 键设计：
  cm:uid:{user_id}  →  uuid_str   （正向：任意 ID → UUID）
  cm:uuid:{uuid}    →  user_id    （反向：UUID → 任意 ID，供排查）
"""

from __future__ import annotations

import uuid

import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger()

_UID_PREFIX = "cm:uid:"
_UUID_PREFIX = "cm:uuid:"


class UserMappingService:
    """在 Redis 中维护 user_id ↔ UUID v4 双向映射"""

    def __init__(self, redis: aioredis.Redis, ttl: int = 0) -> None:
        """
        Args:
            redis: 已连接的异步 Redis 客户端。
            ttl:   键的存活时间（秒）。0 = 永不过期。
        """
        self._redis = redis
        self._ttl = ttl

    # ── 公开 API ──────────────────────────────────────────────────────────

    async def get_or_create_uuid(self, user_id: str) -> str:
        """返回 user_id 对应的 UUID，不存在则自动创建并持久化。"""
        existing = await self._redis.get(_UID_PREFIX + user_id)
        if existing:
            return existing.decode() if isinstance(existing, bytes) else existing

        new_uuid = str(uuid.uuid4())
        await self._store(user_id, new_uuid)
        logger.info("user_mapping.created", user_id=user_id, uuid=new_uuid)
        return new_uuid

    async def get_uuid(self, user_id: str) -> str | None:
        """查询 user_id 对应的 UUID，不存在返回 None（不自动创建）。"""
        val = await self._redis.get(_UID_PREFIX + user_id)
        if val is None:
            return None
        return val.decode() if isinstance(val, bytes) else val

    async def get_user_id(self, uuid_str: str) -> str | None:
        """根据 UUID 反查原始 user_id，不存在返回 None。"""
        val = await self._redis.get(_UUID_PREFIX + uuid_str)
        if val is None:
            return None
        return val.decode() if isinstance(val, bytes) else val

    async def delete_mapping(self, user_id: str) -> bool:
        """删除 user_id 的全部映射记录，返回是否存在过该映射。"""
        uuid_str = await self.get_uuid(user_id)
        if uuid_str is None:
            return False
        pipe = self._redis.pipeline()
        pipe.delete(_UID_PREFIX + user_id)
        pipe.delete(_UUID_PREFIX + uuid_str)
        await pipe.execute()
        logger.info("user_mapping.deleted", user_id=user_id, uuid=uuid_str)
        return True

    # ── 内部方法 ──────────────────────────────────────────────────────────

    async def _store(self, user_id: str, uuid_str: str) -> None:
        """原子写入正向 + 反向键。"""
        pipe = self._redis.pipeline()
        if self._ttl > 0:
            pipe.setex(_UID_PREFIX + user_id, self._ttl, uuid_str)
            pipe.setex(_UUID_PREFIX + uuid_str, self._ttl, user_id)
        else:
            pipe.set(_UID_PREFIX + user_id, uuid_str)
            pipe.set(_UUID_PREFIX + uuid_str, user_id)
        await pipe.execute()

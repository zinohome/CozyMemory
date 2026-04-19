"""用户 ID 映射服务

Memobase 要求 user_id 必须是 UUID v4。
本服务使用 Redis 在任意字符串 user_id 和 UUID v4 之间建立双向映射，
使调用方可以使用自己的 ID 格式而不必关心底层引擎的约束。

Redis 键设计：
  cm:uid:{user_id}  →  uuid_str   （正向：任意 ID → UUID）
  cm:uuid:{uuid}    →  user_id    （反向：UUID → 任意 ID，供排查）

并发安全：
  get_or_create_uuid 使用 generate-then-SET-NX 模式：
  先生成候选 UUID，再原子写入正向键（SET NX）。
  若 NX 失败表示另一请求已抢先完成，直接返回赢家写入的值。
  反向键在正向键写入成功后追加写入（非原子，可容忍：反向键仅供调试查询）。
"""

from __future__ import annotations

import uuid

import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger()

_UID_PREFIX = "cm:uid:"
_UUID_PREFIX = "cm:uuid:"


def _decode(val: bytes | str | None) -> str | None:
    if val is None:
        return None
    return val.decode() if isinstance(val, bytes) else val


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
        """返回 user_id 对应的 UUID，不存在则原子创建并持久化。

        并发安全：使用 generate-then-SET-NX 模式，避免竞态条件下
        同一 user_id 被分配不同 UUID 导致 Memobase 数据孤立。
        """
        fwd_key = _UID_PREFIX + user_id

        # 快路径：已存在
        existing = _decode(await self._redis.get(fwd_key))
        if existing:
            return existing

        # 慢路径：原子抢占写入
        candidate = str(uuid.uuid4())
        rev_key = _UUID_PREFIX + candidate

        if self._ttl > 0:
            wrote = await self._redis.set(fwd_key, candidate, ex=self._ttl, nx=True)
        else:
            wrote = await self._redis.set(fwd_key, candidate, nx=True)

        if wrote:
            # 本请求赢得竞争，追加写入反向键（供调试；非关键路径）
            try:
                if self._ttl > 0:
                    await self._redis.setex(rev_key, self._ttl, user_id)
                else:
                    await self._redis.set(rev_key, user_id)
            except Exception:
                logger.warning("user_mapping.reverse_key_failed", user_id=user_id, uuid=candidate)
            logger.info("user_mapping.created", user_id=user_id, uuid=candidate)
            return candidate

        # 另一请求抢先完成，读取赢家写入的值
        winner = _decode(await self._redis.get(fwd_key))
        if winner:
            return winner
        # 极端情况：赢家写入后立即被删除（TTL 极短），重试一次
        return await self.get_or_create_uuid(user_id)

    async def get_uuid(self, user_id: str) -> str | None:
        """查询 user_id 对应的 UUID，不存在返回 None（不自动创建）。"""
        return _decode(await self._redis.get(_UID_PREFIX + user_id))

    async def get_user_id(self, uuid_str: str) -> str | None:
        """根据 UUID 反查原始 user_id，不存在返回 None。"""
        return _decode(await self._redis.get(_UUID_PREFIX + uuid_str))

    async def delete_mapping(self, user_id: str) -> bool:
        """删除 user_id 的全部映射记录，返回是否存在过该映射。

        注意：仅删除 Redis 映射，Memobase 中对应的用户数据不受影响，
        但删除后该用户数据将无法通过 CozyMemory 画像接口访问（孤立）。
        """
        uuid_str = await self.get_uuid(user_id)
        if uuid_str is None:
            return False
        pipe = self._redis.pipeline(transaction=True)
        pipe.delete(_UID_PREFIX + user_id)
        pipe.delete(_UUID_PREFIX + uuid_str)
        await pipe.execute()
        logger.info("user_mapping.deleted", user_id=user_id, uuid=uuid_str)
        return True

    # ── 内部方法 ──────────────────────────────────────────────────────────

    async def _store(self, user_id: str, uuid_str: str) -> None:
        """原子写入正向 + 反向键（MULTI/EXEC 事务）。

        内部使用，仅在单元测试中直接调用。
        正常写入路径请使用 get_or_create_uuid（SET NX 模式）。
        """
        pipe = self._redis.pipeline(transaction=True)
        if self._ttl > 0:
            pipe.setex(_UID_PREFIX + user_id, self._ttl, uuid_str)
            pipe.setex(_UUID_PREFIX + uuid_str, self._ttl, user_id)
        else:
            pipe.set(_UID_PREFIX + user_id, uuid_str)
            pipe.set(_UUID_PREFIX + uuid_str, user_id)
        await pipe.execute()

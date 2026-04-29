"""会话记忆服务

薄层封装 Mem0 客户端，负责请求转发和错误转换。
搜索结果带 TTL 缓存（60 秒），减少重复 embedding API 调用。
"""

import time
from typing import Any

import structlog

from ..clients.mem0 import Mem0Client
from ..models.conversation import ConversationMemory, ConversationMemoryListResponse, MemoryScope

logger = structlog.get_logger()

# 搜索结果缓存：key=(user_id, query, limit) → (timestamp, result)
_search_cache: dict[tuple, tuple[float, list[ConversationMemory]]] = {}
_CACHE_TTL = 60  # 秒
_CACHE_MAX_SIZE = 200


def _cache_get(key: tuple) -> list[ConversationMemory] | None:
    entry = _search_cache.get(key)
    if entry and (time.monotonic() - entry[0]) < _CACHE_TTL:
        return entry[1]
    if entry:
        _search_cache.pop(key, None)
    return None


def _cache_set(key: tuple, value: list[ConversationMemory]):
    if len(_search_cache) >= _CACHE_MAX_SIZE:
        # 清理过期条目
        now = time.monotonic()
        expired = [k for k, (t, _) in _search_cache.items() if now - t >= _CACHE_TTL]
        for k in expired:
            _search_cache.pop(k, None)
        # 仍然太多就清一半
        if len(_search_cache) >= _CACHE_MAX_SIZE:
            keys = list(_search_cache.keys())
            for k in keys[: len(keys) // 2]:
                _search_cache.pop(k, None)
    _search_cache[key] = (time.monotonic(), value)


class ConversationService:
    """会话记忆服务"""

    def __init__(self, client: Mem0Client):
        self.client = client

    async def add(
        self,
        user_id: str,
        messages: list[dict[str, str]],
        metadata: dict[str, Any] | None = None,
        infer: bool = True,
        agent_id: str | None = None,
        session_id: str | None = None,
    ) -> ConversationMemoryListResponse:
        """添加对话，Mem0 自动提取事实"""
        memories = await self.client.add(
            user_id=user_id,
            messages=messages,
            metadata=metadata,
            infer=infer,
            agent_id=agent_id,
            session_id=session_id,
        )
        logger.info(
            "conversation.add",
            user_id=user_id,
            agent_id=agent_id,
            session_id=session_id,
            extracted=len(memories),
            infer=infer,
        )
        return ConversationMemoryListResponse(
            success=True,
            data=memories,
            total=len(memories),
            message=f"对话已添加，提取出 {len(memories)} 条记忆",
        )

    async def search(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        threshold: float | None = None,
        agent_id: str | None = None,
        session_id: str | None = None,
        memory_scope: MemoryScope = "long",
    ) -> ConversationMemoryListResponse:
        """搜索会话记忆（带 60 秒 TTL 缓存）。

        memory_scope:
          long  — 不带 session 过滤，返回全量历史记忆（默认）
          short — 带 session 过滤，仅返回本 session 记忆
          both  — 短期（带 session）和长期（不带 session）各搜一次，合并去重后返回
        """
        # 缓存检查（仅缓存 long scope 的搜索，short 和 both 不缓存）
        cache_key = (user_id, query, limit, agent_id, memory_scope) if memory_scope == "long" else None
        if cache_key:
            cached = _cache_get(cache_key)
            if cached is not None:
                logger.debug("conversation.search.cache_hit", user_id=user_id, query=query[:30])
                return ConversationMemoryListResponse(
                    success=True, data=cached, total=len(cached))

        if memory_scope == "short":
            memories = await self.client.search(
                user_id=user_id, query=query, limit=limit, threshold=threshold,
                agent_id=agent_id, session_id=session_id,
            )
        elif memory_scope == "long":
            memories = await self.client.search(
                user_id=user_id, query=query, limit=limit, threshold=threshold,
                agent_id=agent_id, session_id=None,
            )
        else:  # both — 两次并发查询
            import asyncio
            short_task = self.client.search(
                user_id=user_id, query=query, limit=limit, threshold=threshold,
                agent_id=agent_id, session_id=session_id,
            )
            long_task = self.client.search(
                user_id=user_id, query=query, limit=limit, threshold=threshold,
                agent_id=agent_id, session_id=None,
            )
            short_mems, long_mems = await asyncio.gather(short_task, long_task)
            logger.debug(
                "conversation.search.both",
                user_id=user_id, short=len(short_mems), long=len(long_mems),
            )
            return ConversationMemoryListResponse(
                success=True,
                data=long_mems,           # 向后兼容：主列表 = 长期记忆
                total=len(long_mems),
                short_term_memories=short_mems,
                long_term_memories=long_mems,
            )

        logger.debug(
            "conversation.search",
            user_id=user_id, agent_id=agent_id, session_id=session_id,
            scope=memory_scope, results=len(memories),
        )
        # 缓存搜索结果
        if cache_key:
            _cache_set(cache_key, memories)
        return ConversationMemoryListResponse(success=True, data=memories, total=len(memories))

    async def search_short(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        threshold: float | None = None,
        agent_id: str | None = None,
        session_id: str | None = None,
    ) -> list[ConversationMemory]:
        """仅返回短期记忆列表（内部辅助方法，供 ContextService memory_scope=both 使用）"""
        return await self.client.search(
            user_id=user_id, query=query, limit=limit, threshold=threshold,
            agent_id=agent_id, session_id=session_id,
        )

    async def get(self, memory_id: str) -> ConversationMemory | None:
        """获取单条记忆"""
        return await self.client.get(memory_id)

    async def get_all(
        self,
        user_id: str,
        limit: int = 100,
        agent_id: str | None = None,
        session_id: str | None = None,
        memory_scope: MemoryScope = "long",
    ) -> ConversationMemoryListResponse:
        """获取用户记忆列表。

        memory_scope:
          long  — 全量历史（默认）
          short — 仅本 session
          both  — 两者（short_term_memories + long_term_memories 分别填充）
        """
        if memory_scope == "short":
            memories = await self.client.get_all(
                user_id=user_id, limit=limit, agent_id=agent_id, session_id=session_id,
            )
            return ConversationMemoryListResponse(success=True, data=memories, total=len(memories))
        elif memory_scope == "long":
            memories = await self.client.get_all(
                user_id=user_id, limit=limit, agent_id=agent_id, session_id=None,
            )
            return ConversationMemoryListResponse(success=True, data=memories, total=len(memories))
        else:  # both
            import asyncio
            short_task = self.client.get_all(
                user_id=user_id, limit=limit, agent_id=agent_id, session_id=session_id,
            )
            long_task = self.client.get_all(
                user_id=user_id, limit=limit, agent_id=agent_id, session_id=None,
            )
            short_mems, long_mems = await asyncio.gather(short_task, long_task)
            return ConversationMemoryListResponse(
                success=True,
                data=long_mems,           # 向后兼容：主列表 = 长期记忆
                total=len(long_mems),
                short_term_memories=short_mems,
                long_term_memories=long_mems,
            )

    async def get_all_short(
        self,
        user_id: str,
        limit: int = 100,
        agent_id: str | None = None,
        session_id: str | None = None,
    ) -> list[ConversationMemory]:
        """仅返回短期记忆列表（内部辅助方法，供 ContextService memory_scope=both 使用）"""
        return await self.client.get_all(
            user_id=user_id, limit=limit, agent_id=agent_id, session_id=session_id,
        )

    async def delete(self, memory_id: str) -> ConversationMemoryListResponse:
        """删除单条记忆"""
        success = await self.client.delete(memory_id)
        return ConversationMemoryListResponse(
            success=success, message="记忆已删除" if success else "删除失败"
        )

    async def delete_all(self, user_id: str) -> ConversationMemoryListResponse:
        """删除用户所有记忆"""
        success = await self.client.delete_all(user_id)
        return ConversationMemoryListResponse(
            success=success, message="用户所有记忆已删除" if success else "删除失败"
        )

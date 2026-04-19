"""会话记忆服务

薄层封装 Mem0 客户端，负责请求转发和错误转换。
"""

from typing import Any

import structlog

from ..clients.mem0 import Mem0Client
from ..models.conversation import ConversationMemory, ConversationMemoryListResponse, MemoryScope

logger = structlog.get_logger()


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
        """搜索会话记忆。

        memory_scope:
          long  — 不带 session 过滤，返回全量历史记忆（默认）
          short — 带 session 过滤，仅返回本 session 记忆
          both  — 短期（带 session）和长期（不带 session）各搜一次，合并去重后返回
                  （调用方通过 ContextResponse.short_term_memories/long_term_memories 区分）
        """
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
            # 返回长期记忆作为主列表（向后兼容），短期/长期分别通过 extra 字段标记
            for m in short_mems:
                m.metadata = {**(m.metadata or {}), "_scope": "short"}
            for m in long_mems:
                m.metadata = {**(m.metadata or {}), "_scope": "long"}
            memories = long_mems  # 主列表用长期
            # 将两组记忆均返回，service 层携带 short 组供 ContextService 解析
            logger.debug(
                "conversation.search.both",
                user_id=user_id, short=len(short_mems), long=len(long_mems),
            )
            return ConversationMemoryListResponse(
                success=True,
                data=long_mems,
                total=len(long_mems),
                _short_term=short_mems,  # type: ignore[call-arg]
            )

        logger.debug(
            "conversation.search",
            user_id=user_id, agent_id=agent_id, session_id=session_id,
            scope=memory_scope, results=len(memories),
        )
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
          both  — 两者（返回长期，短期存于 _short_term）
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
                data=long_mems,
                total=len(long_mems),
                _short_term=short_mems,  # type: ignore[call-arg]
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

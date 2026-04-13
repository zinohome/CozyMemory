"""会话记忆服务

薄层封装 Mem0 客户端，负责请求转发和错误转换。
"""

import logging
from typing import Any

from ..clients.mem0 import Mem0Client
from ..models.conversation import ConversationMemory, ConversationMemoryListResponse

logger = logging.getLogger(__name__)


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
    ) -> ConversationMemoryListResponse:
        """添加对话，Mem0 自动提取事实"""
        memories = await self.client.add(
            user_id=user_id, messages=messages, metadata=metadata, infer=infer
        )
        return ConversationMemoryListResponse(
            success=True,
            data=memories,
            total=len(memories),
            message=f"对话已添加，提取出 {len(memories)} 条记忆",
        )

    async def search(
        self, user_id: str, query: str, limit: int = 10, threshold: float | None = None
    ) -> ConversationMemoryListResponse:
        """搜索会话记忆"""
        memories = await self.client.search(
            user_id=user_id, query=query, limit=limit, threshold=threshold
        )
        return ConversationMemoryListResponse(success=True, data=memories, total=len(memories))

    async def get(self, memory_id: str) -> ConversationMemory | None:
        """获取单条记忆"""
        return await self.client.get(memory_id)

    async def get_all(self, user_id: str, limit: int = 100) -> ConversationMemoryListResponse:
        """获取用户所有记忆"""
        memories = await self.client.get_all(user_id=user_id, limit=limit)
        return ConversationMemoryListResponse(success=True, data=memories, total=len(memories))

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

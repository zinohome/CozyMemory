"""用户画像服务

薄层封装 Memobase 客户端，负责请求转发和错误转换。
"""

import logging
from typing import Any

from ..clients.memobase import MemobaseClient
from ..clients.base import EngineError
from ..models.profile import ProfileInsertResponse, ProfileTopic, ProfileContext
from ..models.common import Message

logger = logging.getLogger(__name__)


class ProfileService:
    """用户画像服务"""

    def __init__(self, client: MemobaseClient):
        self.client = client

    async def insert(self, user_id: str, messages: list[dict[str, str] | Message], sync: bool = False) -> ProfileInsertResponse:
        """插入对话到 Memobase 缓冲区"""
        msg_dicts = [{"role": m.role, "content": m.content} if isinstance(m, Message) else m for m in messages]
        blob_id = await self.client.insert(user_id=user_id, messages=msg_dicts, sync=sync)
        return ProfileInsertResponse(success=True, user_id=user_id, blob_id=blob_id, message="对话已插入缓冲区")

    async def flush(self, user_id: str, sync: bool = False) -> dict:
        """触发缓冲区处理"""
        await self.client.flush(user_id=user_id, sync=sync)
        return {"success": True, "message": "处理完成"}

    async def get_profile(self, user_id: str) -> dict:
        """获取用户结构化画像"""
        profile = await self.client.profile(user_id=user_id)
        return {"success": True, "data": profile, "message": ""}

    async def get_context(self, user_id: str, max_token_size: int = 500, chats: list[dict[str, str]] | None = None) -> dict:
        """获取上下文提示词"""
        ctx = await self.client.context(user_id=user_id, max_token_size=max_token_size, chats=chats)
        return {"success": True, "data": ctx, "message": ""}

    async def add_profile_item(self, user_id: str, topic: str, sub_topic: str, content: str) -> dict:
        """手动添加画像条目"""
        result = await self.client.add_profile(user_id=user_id, topic=topic, sub_topic=sub_topic, content=content)
        return {"success": True, "data": result, "message": ""}

    async def delete_profile_item(self, user_id: str, profile_id: str) -> dict:
        """删除画像条目"""
        success = await self.client.delete_profile(user_id=user_id, profile_id=profile_id)
        return {"success": success, "message": "已删除" if success else "删除失败"}
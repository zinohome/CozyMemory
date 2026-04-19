"""用户画像服务

薄层封装 Memobase 客户端，负责请求转发和错误转换。
通过 UserMappingService 自动将任意 user_id 转换为 Memobase 所需的 UUID v4。
"""

import structlog

from ..clients.memobase import MemobaseClient
from ..models.profile import (
    ProfileAddItemResponse,
    ProfileContextResponse,
    ProfileDeleteItemResponse,
    ProfileFlushResponse,
    ProfileGetResponse,
    ProfileInsertResponse,
)
from .user_mapping import UserMappingService

logger = structlog.get_logger()


class ProfileService:
    """用户画像服务（含透明 user_id → UUID v4 转换）"""

    def __init__(self, client: MemobaseClient, user_mapping: UserMappingService) -> None:
        self.client = client
        self._mapping = user_mapping

    async def _resolve_uuid(self, user_id: str) -> str:
        """将任意 user_id 解析为 Memobase 兼容的 UUID v4。"""
        return await self._mapping.get_or_create_uuid(user_id)

    async def insert(
        self, user_id: str, messages: list[dict[str, str]], sync: bool = False
    ) -> ProfileInsertResponse:
        """插入对话到 Memobase 缓冲区"""
        uuid_id = await self._resolve_uuid(user_id)
        blob_id = await self.client.insert(user_id=uuid_id, messages=messages, sync=sync)
        logger.info(
            "profile.insert", user_id=user_id, uuid=uuid_id, messages=len(messages), sync=sync
        )
        return ProfileInsertResponse(
            success=True, user_id=user_id, blob_id=blob_id, message="对话已插入缓冲区"
        )

    async def flush(self, user_id: str, sync: bool = False) -> ProfileFlushResponse:
        """触发缓冲区处理"""
        uuid_id = await self._resolve_uuid(user_id)
        await self.client.flush(user_id=uuid_id, sync=sync)
        return ProfileFlushResponse(success=True, message="处理完成")

    async def get_profile(self, user_id: str) -> ProfileGetResponse:
        """获取用户结构化画像"""
        uuid_id = await self._resolve_uuid(user_id)
        profile = await self.client.profile(user_id=uuid_id)
        return ProfileGetResponse(success=True, data=profile, message="")

    async def get_context(
        self, user_id: str, max_token_size: int = 500, chats: list[dict[str, str]] | None = None
    ) -> ProfileContextResponse:
        """获取上下文提示词"""
        uuid_id = await self._resolve_uuid(user_id)
        ctx = await self.client.context(user_id=uuid_id, max_token_size=max_token_size, chats=chats)
        return ProfileContextResponse(success=True, data=ctx, message="")

    async def add_profile_item(
        self, user_id: str, topic: str, sub_topic: str, content: str
    ) -> ProfileAddItemResponse:
        """手动添加画像条目"""
        uuid_id = await self._resolve_uuid(user_id)
        result = await self.client.add_profile(
            user_id=uuid_id, topic=topic, sub_topic=sub_topic, content=content
        )
        return ProfileAddItemResponse(success=True, data=result, message="")

    async def delete_profile_item(self, user_id: str, profile_id: str) -> ProfileDeleteItemResponse:
        """删除画像条目"""
        uuid_id = await self._resolve_uuid(user_id)
        success = await self.client.delete_profile(user_id=uuid_id, profile_id=profile_id)
        msg = "已删除" if success else "删除失败"
        return ProfileDeleteItemResponse(success=success, message=msg)

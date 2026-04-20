"""记忆备份/恢复服务

组合 ConversationService + ProfileService 读出用户的记忆 + 画像打包为
MemoryBundle；导入时反向分发写回。

注意：
  - Mem0 的 conversation 原文未保留（只存 LLM 提取后的事实），导入时以
    fake user message 重放，让 Mem0 重新提取，可能与原记忆不完全一致。
    适合人眼备份 / 跨实例迁移，不适合精确恢复。
  - Memobase profile topic 精确恢复（add_profile 支持 id 无关，属性保真）。
"""

from datetime import datetime, timezone

import structlog

from ..clients.base import EngineError
from ..models.backup import BackupImportResponse, MemoryBundle
from .conversation import ConversationService
from .profile import ProfileService

logger = structlog.get_logger()


class BackupService:
    def __init__(
        self, conv_service: ConversationService, profile_service: ProfileService
    ) -> None:
        self.conv = conv_service
        self.profile = profile_service

    async def export_user(self, user_id: str) -> MemoryBundle:
        """拉该用户全部 Mem0 记忆 + Memobase topics，打成 bundle"""
        conv_resp = await self.conv.get_all(user_id=user_id, limit=1000)
        profile_resp = await self.profile.get_profile(user_id=user_id)

        topics = profile_resp.data.topics if profile_resp.data else []

        bundle = MemoryBundle(
            exported_at=datetime.now(timezone.utc),
            user_id=user_id,
            conversations=conv_resp.data or [],
            profile_topics=topics,
        )
        logger.info(
            "backup.export",
            user_id=user_id,
            conversations=len(bundle.conversations),
            profile_topics=len(bundle.profile_topics),
        )
        return bundle

    async def import_bundle(
        self, bundle: MemoryBundle, target_user_id: str | None = None
    ) -> BackupImportResponse:
        """把 bundle 写回目标用户。失败单条记录不中断整体"""
        uid = target_user_id or bundle.user_id
        resp = BackupImportResponse(user_id=uid)

        # 对话：每条 content 作为 user 发言重放，Mem0 重新提取
        for mem in bundle.conversations:
            text = mem.content.strip()
            if not text:
                resp.conversations_skipped += 1
                continue
            try:
                await self.conv.add(
                    user_id=uid,
                    messages=[{"role": "user", "content": text}],
                    infer=True,
                )
                resp.conversations_imported += 1
            except EngineError as e:
                resp.conversations_skipped += 1
                resp.errors.append(
                    {"kind": "conversation", "id": mem.id, "reason": str(e)}
                )

        # 画像主题：精确恢复
        for topic in bundle.profile_topics:
            try:
                await self.profile.add_profile_item(
                    user_id=uid,
                    topic=topic.topic,
                    sub_topic=topic.sub_topic,
                    content=topic.content,
                )
                resp.profiles_imported += 1
            except EngineError as e:
                resp.profiles_skipped += 1
                resp.errors.append(
                    {"kind": "profile", "id": topic.id, "reason": str(e)}
                )

        logger.info(
            "backup.import",
            user_id=uid,
            conversations_imported=resp.conversations_imported,
            profiles_imported=resp.profiles_imported,
            errors=len(resp.errors),
        )
        return resp

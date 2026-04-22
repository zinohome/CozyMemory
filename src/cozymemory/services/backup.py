"""记忆备份/恢复服务

组合 ConversationService + ProfileService 读出用户的记忆 + 画像打包为
MemoryBundle；导入时反向分发写回。

注意：
  - Mem0 的 conversation 原文未保留（只存 LLM 提取后的事实），导入时以
    fake user message 重放，让 Mem0 重新提取，可能与原记忆不完全一致。
    适合人眼备份 / 跨实例迁移，不适合精确恢复。
  - Memobase profile topic 精确恢复（add_profile 支持 id 无关，属性保真）。
"""

from datetime import UTC, datetime

import structlog

from ..clients.base import EngineError
from ..models.backup import BackupImportResponse, DatasetDump, MemoryBundle
from .conversation import ConversationService
from .knowledge import KnowledgeService
from .profile import ProfileService

logger = structlog.get_logger()


class BackupService:
    def __init__(
        self,
        conv_service: ConversationService,
        profile_service: ProfileService,
        knowledge_service: KnowledgeService,
    ) -> None:
        self.conv = conv_service
        self.profile = profile_service
        self.knowledge = knowledge_service

    async def _dump_dataset(self, dataset_id: str) -> DatasetDump | None:
        """从 dataset graph 提取 DocumentChunk 的 text 字段作为原文备份"""
        try:
            resp = await self.knowledge.get_dataset_graph(dataset_id)
        except EngineError:
            return None
        raw = resp.data if hasattr(resp, "data") else None
        if not isinstance(raw, dict):
            return None
        nodes = raw.get("nodes") or []
        documents: list[str] = []
        for n in nodes:
            if not isinstance(n, dict):
                continue
            if n.get("type") != "DocumentChunk":
                continue
            props = n.get("properties") or {}
            text = props.get("text")
            if isinstance(text, str) and text.strip():
                documents.append(text)
        # dataset 名字从 listing 查（graph 没带名字）
        name = await self._dataset_name(dataset_id)
        if not name:
            return None
        return DatasetDump(name=name, documents=documents)

    async def _dataset_name(self, dataset_id: str) -> str | None:
        resp = await self.knowledge.list_datasets()
        for ds in resp.data or []:
            if ds.id == dataset_id:
                return ds.name
        return None

    async def export_user(
        self, user_id: str, dataset_ids: list[str] | None = None
    ) -> MemoryBundle:
        """拉该用户全部 Mem0 记忆 + Memobase topics；可选附带若干 Cognee 数据集"""
        conv_resp = await self.conv.get_all(user_id=user_id, limit=1000)
        profile_resp = await self.profile.get_profile(user_id=user_id)

        topics = profile_resp.data.topics if profile_resp.data else []

        datasets: list[DatasetDump] = []
        if dataset_ids:
            for did in dataset_ids:
                dump = await self._dump_dataset(did)
                if dump:
                    datasets.append(dump)

        bundle = MemoryBundle(
            exported_at=datetime.now(UTC),
            user_id=user_id,
            conversations=conv_resp.data or [],
            profile_topics=topics,
            datasets=datasets,
        )
        logger.info(
            "backup.export",
            user_id=user_id,
            conversations=len(bundle.conversations),
            profile_topics=len(bundle.profile_topics),
            datasets=len(bundle.datasets),
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

        # Cognee 数据集：创建 + 逐条 add + cognify 触发（后台）
        datasets_to_build: list[str] = []
        for ds in bundle.datasets:
            try:
                await self.knowledge.create_dataset(name=ds.name)
            except EngineError as e:
                # 已存在时 Cognee 返回错误，忽略继续 add（知识库按名累加）
                logger.info("backup.import.create_dataset_skipped", name=ds.name, reason=str(e))
            added = 0
            for doc in ds.documents:
                if not doc.strip():
                    continue
                try:
                    await self.knowledge.add(data=doc, dataset=ds.name)
                    added += 1
                except EngineError as e:
                    resp.errors.append(
                        {"kind": "dataset_doc", "id": ds.name, "reason": str(e)}
                    )
            if added > 0:
                resp.datasets_imported += 1
                resp.documents_imported += added
                datasets_to_build.append(ds.name)
            else:
                resp.datasets_skipped += 1

        if datasets_to_build:
            try:
                await self.knowledge.cognify(
                    datasets=datasets_to_build, run_in_background=True
                )
            except EngineError as e:
                resp.errors.append(
                    {"kind": "cognify", "id": ",".join(datasets_to_build), "reason": str(e)}
                )

        logger.info(
            "backup.import",
            user_id=uid,
            conversations_imported=resp.conversations_imported,
            profiles_imported=resp.profiles_imported,
            datasets_imported=resp.datasets_imported,
            documents_imported=resp.documents_imported,
            errors=len(resp.errors),
        )
        return resp

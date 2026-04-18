"""统一上下文服务

并发调用三大引擎，将结果合并为单一响应。
部分引擎失败时仍返回其他引擎的结果，错误记录在 errors 字段。
"""

import asyncio
import time

import structlog

from ..clients.base import EngineError
from ..models.context import ContextRequest, ContextResponse
from .conversation import ConversationService
from .knowledge import KnowledgeService
from .profile import ProfileService

logger = structlog.get_logger()


class ContextService:
    """统一上下文服务：并发编排三大引擎"""

    def __init__(
        self,
        conv_service: ConversationService,
        profile_service: ProfileService,
        knowledge_service: KnowledgeService,
    ):
        self._conv = conv_service
        self._profile = profile_service
        self._knowledge = knowledge_service

    async def get_context(self, request: ContextRequest) -> ContextResponse:
        """并发获取三类记忆，返回统一上下文。

        执行策略：
        - asyncio.gather(..., return_exceptions=True) 保证单引擎失败不影响其他引擎
        - query 有值 → Mem0 语义搜索 + Cognee 图谱搜索
        - query 为 None → Mem0 get_all，Cognee 跳过（搜索需要 query）
        - Memobase get_context 始终执行（不依赖 query）
        """
        start = time.monotonic()

        # ── 构建并发任务列表 ──────────────────────────────────────────────
        task_keys: list[str] = []
        coros = []

        if request.include_conversations:
            task_keys.append("conversations")
            if request.query:
                coros.append(
                    self._conv.search(
                        user_id=request.user_id,
                        query=request.query,
                        limit=request.conversation_limit,
                    )
                )
            else:
                coros.append(
                    self._conv.get_all(
                        user_id=request.user_id,
                        limit=request.conversation_limit,
                    )
                )

        if request.include_profile:
            task_keys.append("profile")
            coros.append(
                self._profile.get_context(
                    user_id=request.user_id,
                    max_token_size=request.max_token_size,
                )
            )

        if request.include_knowledge and request.query:
            task_keys.append("knowledge")
            coros.append(
                self._knowledge.search(
                    query=request.query,
                    search_type=request.knowledge_search_type,
                    top_k=request.knowledge_top_k,
                )
            )

        # ── 并发执行 ─────────────────────────────────────────────────────
        raw_results = await asyncio.gather(*coros, return_exceptions=True)

        # ── 结果归并 ─────────────────────────────────────────────────────
        conversations = []
        profile_context = None
        knowledge = []
        errors: dict[str, str] = {}

        for key, result in zip(task_keys, raw_results):
            if isinstance(result, (EngineError, Exception)):
                errors[key] = str(result)
                logger.warning("context.engine_error", engine=key, error=str(result))
            elif key == "conversations":
                conversations = result.data
            elif key == "profile":
                profile_context = result.data.context if result.data else None
            elif key == "knowledge":
                knowledge = result.data

        latency_ms = round((time.monotonic() - start) * 1000, 1)
        logger.info(
            "context.get",
            user_id=request.user_id,
            engines=task_keys,
            errors=list(errors.keys()),
            latency_ms=latency_ms,
        )

        return ContextResponse(
            user_id=request.user_id,
            conversations=conversations,
            profile_context=profile_context,
            knowledge=knowledge,
            errors=errors,
            latency_ms=latency_ms,
        )

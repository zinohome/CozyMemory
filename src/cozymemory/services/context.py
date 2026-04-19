"""统一上下文服务

并发调用三大引擎，将结果合并为单一响应。
部分引擎失败时仍返回其他引擎的结果，错误记录在 errors 字段。
"""

import asyncio
import time

import structlog

from ..clients.base import EngineError
from ..models.context import ContextRequest, ContextResponse
from ..models.conversation import ConversationMemory, ConversationMemoryListResponse
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
        - memory_scope=both 时对 Mem0 发起两次并发查询（短期 + 长期）
        - knowledge_datasets 有值时对每个 dataset 并发搜索后合并结果
        """
        start = time.monotonic()

        chats = (
            [{"role": m.role, "content": m.content} for m in request.chats]
            if request.chats
            else None
        )
        need_both = request.memory_scope == "both"

        # ── 构建并发任务列表 ──────────────────────────────────────────────
        task_keys: list[str] = []
        coros = []

        if request.include_conversations:
            if need_both:
                # 两次并发：短期（带 session）+ 长期（不带 session）
                task_keys.append("conversations_short")
                task_keys.append("conversations_long")
                if request.query:
                    coros.append(self._conv.search_short(
                        user_id=request.user_id, query=request.query,
                        limit=request.conversation_limit,
                        agent_id=request.agent_id, session_id=request.session_id,
                    ))
                    coros.append(self._conv.search(
                        user_id=request.user_id, query=request.query,
                        limit=request.conversation_limit,
                        agent_id=request.agent_id, session_id=None,
                        memory_scope="long",
                    ))
                else:
                    coros.append(self._conv.get_all_short(
                        user_id=request.user_id, limit=request.conversation_limit,
                        agent_id=request.agent_id, session_id=request.session_id,
                    ))
                    coros.append(self._conv.get_all(
                        user_id=request.user_id, limit=request.conversation_limit,
                        agent_id=request.agent_id, session_id=None,
                        memory_scope="long",
                    ))
            else:
                task_keys.append("conversations")
                session_id = request.session_id if request.memory_scope == "short" else None
                if request.query:
                    coros.append(self._conv.search(
                        user_id=request.user_id, query=request.query,
                        limit=request.conversation_limit,
                        agent_id=request.agent_id, session_id=session_id,
                        memory_scope=request.memory_scope,
                    ))
                else:
                    coros.append(self._conv.get_all(
                        user_id=request.user_id, limit=request.conversation_limit,
                        agent_id=request.agent_id, session_id=session_id,
                        memory_scope=request.memory_scope,
                    ))

        if request.include_profile:
            task_keys.append("profile")
            coros.append(
                self._profile.get_context(
                    user_id=request.user_id,
                    max_token_size=request.max_token_size,
                    chats=chats,
                )
            )

        if request.include_knowledge and request.query:
            datasets = request.knowledge_datasets or [None]  # None = 搜索全部
            for ds in datasets:
                key = f"knowledge:{ds}" if ds else "knowledge"
                task_keys.append(key)
                coros.append(
                    self._knowledge.search(
                        query=request.query,
                        dataset=ds,
                        search_type=request.knowledge_search_type,
                        top_k=request.knowledge_top_k,
                    )
                )

        # ── 并发执行（可选每引擎超时）────────────────────────────────────
        timeout = request.engine_timeout
        if timeout is not None:
            wrapped = [asyncio.wait_for(c, timeout=timeout) for c in coros]
        else:
            wrapped = coros  # type: ignore[assignment]
        raw_results = await asyncio.gather(*wrapped, return_exceptions=True)

        # ── 结果归并 ─────────────────────────────────────────────────────
        conversations: list[ConversationMemory] = []
        short_term_memories: list[ConversationMemory] = []
        long_term_memories: list[ConversationMemory] = []
        profile_context = None
        knowledge = []
        errors: dict[str, str] = {}

        for key, result in zip(task_keys, raw_results):
            if isinstance(result, asyncio.TimeoutError):
                # 超时：提取引擎域名作为 error key
                domain = key.split(":")[0] if ":" in key else key
                if "conversations" in domain:
                    domain = "conversations"
                msg = f"engine timeout after {timeout}s"
                errors[domain] = msg
                logger.warning("context.engine_timeout", engine=key, timeout=timeout)
                continue
            if isinstance(result, (EngineError, Exception)):
                domain = key.split(":")[0] if ":" in key else key
                if "conversations" in domain:
                    domain = "conversations"
                errors[domain] = str(result)
                logger.warning("context.engine_error", engine=key, error=str(result))
                continue

            if key == "conversations_short":
                # search_short / get_all_short 直接返回 list[ConversationMemory]
                short_term_memories = result if isinstance(result, list) else result.data
            elif key == "conversations_long":
                # search / get_all 返回 ConversationMemoryListResponse
                long_term_memories = (
                    result.data if isinstance(result, ConversationMemoryListResponse) else result
                )
                conversations = long_term_memories  # 向后兼容
            elif key == "conversations":
                # memory_scope != both：单次调用，返回 ConversationMemoryListResponse
                data: list[ConversationMemory] = (
                    result if isinstance(result, list) else result.data
                )
                conversations = data
                if request.memory_scope == "short":
                    short_term_memories = data
                else:
                    long_term_memories = data
            elif key == "profile":
                profile_context = result.data.context if result.data else None
            elif key.startswith("knowledge"):
                items = result if isinstance(result, list) else result.data
                knowledge.extend(items)

        latency_ms = round((time.monotonic() - start) * 1000, 1)
        logger.info(
            "context.get",
            user_id=request.user_id,
            agent_id=request.agent_id,
            session_id=request.session_id,
            memory_scope=request.memory_scope,
            engines=task_keys,
            errors=list(errors.keys()),
            latency_ms=latency_ms,
        )

        return ContextResponse(
            user_id=request.user_id,
            conversations=conversations,
            short_term_memories=short_term_memories,
            long_term_memories=long_term_memories,
            profile_context=profile_context,
            knowledge=knowledge,
            errors=errors,
            latency_ms=latency_ms,
        )

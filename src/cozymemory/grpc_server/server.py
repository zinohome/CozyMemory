"""gRPC 服务器

启动 gRPC 服务，复用 Service 层逻辑。
"""

from typing import Any

import grpc
import structlog

from ..api.deps import (
    get_context_service,
    get_conversation_service,
    get_knowledge_service,
    get_profile_service,
)
from ..clients.base import EngineError
from ..config import settings
from . import (  # noqa: F401
    context_pb2,
    context_pb2_grpc,
    conversation_pb2,
    conversation_pb2_grpc,
    knowledge_pb2,
    knowledge_pb2_grpc,
    profile_pb2,
    profile_pb2_grpc,
)

logger = structlog.get_logger()


def _handle_engine_error(exc: EngineError, context: grpc.aio.ServicerContext) -> None:
    """将 EngineError 映射为 gRPC 状态码并设置到 context。

    映射规则：
    - 5xx → UNAVAILABLE（后端服务不可用）
    - 404 → NOT_FOUND
    - 其他 4xx → FAILED_PRECONDITION
    - 无状态码 → INTERNAL
    """
    if exc.status_code is None:
        context.set_code(grpc.StatusCode.INTERNAL)
    elif exc.status_code >= 500:
        context.set_code(grpc.StatusCode.UNAVAILABLE)
    elif exc.status_code == 404:
        context.set_code(grpc.StatusCode.NOT_FOUND)
    else:
        context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
    context.set_details(f"[{exc.engine}] {exc.message}")


class ConversationGrpcServicer(conversation_pb2_grpc.ConversationServiceServicer):
    """会话记忆 gRPC 服务实现"""

    def __init__(self) -> None:
        self._svc = get_conversation_service()

    async def AddConversation(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
        try:
            svc = self._svc
            messages = [{"role": m.role, "content": m.content} for m in request.messages]
            metadata = dict(request.metadata) if request.metadata else None
            result = await svc.add(
                user_id=request.user_id,
                messages=messages,
                metadata=metadata,
                infer=request.infer,
                agent_id=request.agent_id or None,
                session_id=request.session_id or None,
            )
            memories = [
                conversation_pb2.ConversationMemory(id=m.id, user_id=m.user_id, content=m.content)
                for m in result.data
            ]
            return conversation_pb2.AddConversationResponse(
                success=result.success,
                data=memories,
                message=result.message,
            )
        except EngineError as exc:
            _handle_engine_error(exc, context)
            return conversation_pb2.AddConversationResponse()

    async def SearchConversations(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
        try:
            svc = self._svc
            result = await svc.search(
                user_id=request.user_id,
                query=request.query,
                limit=request.limit,
                threshold=request.threshold if request.HasField("threshold") else None,
                agent_id=request.agent_id or None,
                session_id=request.session_id or None,
                memory_scope=request.memory_scope or "long",
            )
            memories = []
            for m in result.data:
                memories.append(
                    conversation_pb2.ConversationMemory(
                        id=m.id,
                        user_id=m.user_id,
                        content=m.content,
                        score=m.score or 0.0,
                    )
                )
            return conversation_pb2.SearchConversationsResponse(
                success=result.success,
                data=memories,
                total=result.total,
                message=result.message,
            )
        except EngineError as exc:
            _handle_engine_error(exc, context)
            return conversation_pb2.SearchConversationsResponse()

    async def GetConversation(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
        try:
            svc = self._svc
            result = await svc.get(request.memory_id)
            if result is None:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("记忆不存在")
                return conversation_pb2.ConversationMemory()
            return conversation_pb2.ConversationMemory(
                id=result.id,
                user_id=result.user_id,
                content=result.content,
            )
        except EngineError as exc:
            _handle_engine_error(exc, context)
            return conversation_pb2.ConversationMemory()

    async def DeleteConversation(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
        try:
            svc = self._svc
            result = await svc.delete(request.memory_id)
            return conversation_pb2.DeleteResponse(success=result.success, message=result.message)
        except EngineError as exc:
            _handle_engine_error(exc, context)
            return conversation_pb2.DeleteResponse()

    async def DeleteAllConversations(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
        try:
            svc = self._svc
            result = await svc.delete_all(request.user_id)
            return conversation_pb2.DeleteResponse(success=result.success, message=result.message)
        except EngineError as exc:
            _handle_engine_error(exc, context)
            return conversation_pb2.DeleteResponse()

    async def ListConversations(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
        try:
            svc = self._svc
            result = await svc.get_all(
                user_id=request.user_id,
                limit=request.limit or 100,
                agent_id=request.agent_id or None,
                session_id=request.session_id or None,
                memory_scope=request.memory_scope or "long",
            )
            memories = [
                conversation_pb2.ConversationMemory(id=m.id, user_id=m.user_id, content=m.content)
                for m in result.data
            ]
            return conversation_pb2.SearchConversationsResponse(
                success=result.success,
                data=memories,
                total=result.total,
                message=result.message,
            )
        except EngineError as exc:
            _handle_engine_error(exc, context)
            return conversation_pb2.SearchConversationsResponse()


class ProfileGrpcServicer(profile_pb2_grpc.ProfileServiceServicer):
    """用户画像 gRPC 服务实现"""

    def __init__(self) -> None:
        self._svc = get_profile_service()

    async def InsertProfile(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
        try:
            svc = self._svc
            messages = [{"role": m.role, "content": m.content} for m in request.messages]
            result = await svc.insert(user_id=request.user_id, messages=messages, sync=request.sync)
            return profile_pb2.InsertProfileResponse(
                success=result.success,
                user_id=result.user_id,
                blob_id=result.blob_id or "",
                message=result.message,
            )
        except EngineError as exc:
            _handle_engine_error(exc, context)
            return profile_pb2.InsertProfileResponse()

    async def FlushProfile(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
        try:
            svc = self._svc
            result = await svc.flush(user_id=request.user_id, sync=request.sync)
            return profile_pb2.FlushProfileResponse(
                success=result.success,
                message=result.message,
            )
        except EngineError as exc:
            _handle_engine_error(exc, context)
            return profile_pb2.FlushProfileResponse()

    async def GetProfile(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
        try:
            svc = self._svc
            result = await svc.get_profile(request.user_id)
            topics = []
            if result.data and hasattr(result.data, "topics"):
                for t in result.data.topics:
                    topics.append(
                        profile_pb2.ProfileTopic(
                            id=t.id,
                            topic=t.topic,
                            sub_topic=t.sub_topic,
                            content=t.content,
                        )
                    )
            return profile_pb2.UserProfile(
                user_id=request.user_id,
                topics=topics,
            )
        except EngineError as exc:
            _handle_engine_error(exc, context)
            return profile_pb2.UserProfile()

    async def GetContext(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
        try:
            svc = self._svc
            chats = (
                [{"role": m.role, "content": m.content} for m in request.chats]
                if request.chats
                else None
            )
            result = await svc.get_context(
                user_id=request.user_id,
                max_token_size=request.max_token_size,
                chats=chats,
            )
            context_text = result.data.context if result.data else ""
            return profile_pb2.GetContextResponse(
                success=result.success,
                user_id=request.user_id,
                context=context_text,
            )
        except EngineError as exc:
            _handle_engine_error(exc, context)
            return profile_pb2.GetContextResponse()

    async def AddProfileItem(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
        try:
            svc = self._svc
            result = await svc.add_profile_item(
                user_id=request.user_id,
                topic=request.topic,
                sub_topic=request.sub_topic,
                content=request.content,
            )
            topic_proto = None
            if result.data:
                topic_proto = profile_pb2.ProfileTopic(
                    id=result.data.id,
                    topic=result.data.topic,
                    sub_topic=result.data.sub_topic,
                    content=result.data.content,
                )
            return profile_pb2.AddProfileItemResponse(
                success=result.success,
                data=topic_proto,
                message=result.message,
            )
        except EngineError as exc:
            _handle_engine_error(exc, context)
            return profile_pb2.AddProfileItemResponse()

    async def DeleteProfileItem(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
        try:
            svc = self._svc
            result = await svc.delete_profile_item(
                user_id=request.user_id,
                profile_id=request.profile_id,
            )
            return conversation_pb2.DeleteResponse(success=result.success, message=result.message)
        except EngineError as exc:
            _handle_engine_error(exc, context)
            return conversation_pb2.DeleteResponse()


class KnowledgeGrpcServicer(knowledge_pb2_grpc.KnowledgeServiceServicer):
    """知识库 gRPC 服务实现"""

    def __init__(self) -> None:
        self._svc = get_knowledge_service()

    async def CreateDataset(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
        try:
            svc = self._svc
            result = await svc.create_dataset(name=request.name)
            ds = result.data[0] if result.data else None
            return knowledge_pb2.DatasetInfo(
                id=ds.id if ds else "",
                name=ds.name if ds else request.name,
            )
        except EngineError as exc:
            _handle_engine_error(exc, context)
            return knowledge_pb2.DatasetInfo()

    async def ListDatasets(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
        try:
            svc = self._svc
            result = await svc.list_datasets()
            datasets = [knowledge_pb2.DatasetInfo(id=ds.id, name=ds.name) for ds in result.data]
            return knowledge_pb2.ListDatasetsResponse(
                success=result.success,
                data=datasets,
                message=result.message,
            )
        except EngineError as exc:
            _handle_engine_error(exc, context)
            return knowledge_pb2.ListDatasetsResponse()

    async def AddKnowledge(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
        try:
            svc = self._svc
            result = await svc.add(data=request.data, dataset=request.dataset)
            return knowledge_pb2.AddKnowledgeResponse(
                success=result.success,
                data_id=result.data_id or "",
                dataset_name=result.dataset_name,
                message=result.message,
            )
        except EngineError as exc:
            _handle_engine_error(exc, context)
            return knowledge_pb2.AddKnowledgeResponse()

    async def Cognify(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
        try:
            svc = self._svc
            datasets = list(request.datasets) if request.datasets else None
            result = await svc.cognify(
                datasets=datasets, run_in_background=request.run_in_background
            )
            return knowledge_pb2.CognifyResponse(
                success=result.success,
                pipeline_run_id=result.pipeline_run_id or "",
                status=result.status,
                message=result.message,
            )
        except EngineError as exc:
            _handle_engine_error(exc, context)
            return knowledge_pb2.CognifyResponse()

    async def SearchKnowledge(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
        try:
            svc = self._svc
            result = await svc.search(
                query=request.query,
                dataset=request.dataset or None,
                search_type=request.search_type,
                top_k=request.top_k,
            )
            results = [
                knowledge_pb2.KnowledgeSearchResult(
                    id=r.id or "",
                    text=getattr(r, "content", None) or r.text or "",
                    score=r.score or 0.0,
                )
                for r in result.data
            ]
            return knowledge_pb2.SearchKnowledgeResponse(
                success=result.success,
                data=results,
                total=result.total,
                message=result.message,
            )
        except EngineError as exc:
            _handle_engine_error(exc, context)
            return knowledge_pb2.SearchKnowledgeResponse()

    async def DeleteKnowledge(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
        try:
            svc = self._svc
            result = await svc.delete(data_id=request.data_id, dataset_id=request.dataset_id)
            return conversation_pb2.DeleteResponse(success=result.success, message=result.message)
        except EngineError as exc:
            _handle_engine_error(exc, context)
            return conversation_pb2.DeleteResponse()


class ContextGrpcServicer(context_pb2_grpc.ContextServiceServicer):
    """统一上下文 gRPC 服务实现"""

    def __init__(self) -> None:
        self._svc = get_context_service()

    async def GetUnifiedContext(self, request: Any, context: grpc.aio.ServicerContext) -> Any:
        from ..models.common import Message
        from ..models.context import ContextRequest

        try:
            chats = (
                [Message(role=m.role, content=m.content) for m in request.chats]
                if request.chats
                else None
            )
            ctx_request = ContextRequest(
                user_id=request.user_id,
                query=request.query or None,
                agent_id=request.agent_id or None,
                session_id=request.session_id or None,
                memory_scope=request.memory_scope or "long",
                include_conversations=request.include_conversations,
                include_profile=request.include_profile,
                include_knowledge=request.include_knowledge,
                conversation_limit=request.conversation_limit or 5,
                max_token_size=request.max_token_size or 500,
                knowledge_top_k=request.knowledge_top_k or 3,
                knowledge_search_type=request.knowledge_search_type or "GRAPH_COMPLETION",
                knowledge_datasets=list(request.knowledge_datasets) or None,
                engine_timeout=request.engine_timeout or None,
                chats=chats,
            )
            result = await self._svc.get_context(ctx_request)

            def _to_conv_proto(mems):
                return [
                    conversation_pb2.ConversationMemory(
                        id=m.id, user_id=m.user_id, content=m.content
                    )
                    for m in mems
                ]

            knowledge = [
                knowledge_pb2.KnowledgeSearchResult(
                    id=r.id or "",
                    text=r.text or "",
                    score=r.score or 0.0,
                )
                for r in result.knowledge
            ]
            return context_pb2.GetUnifiedContextResponse(
                success=result.success,
                user_id=result.user_id,
                conversations=_to_conv_proto(result.conversations),
                short_term_memories=_to_conv_proto(result.short_term_memories),
                long_term_memories=_to_conv_proto(result.long_term_memories),
                profile_context=result.profile_context or "",
                knowledge=knowledge,
                errors=result.errors,
                latency_ms=result.latency_ms,
            )
        except EngineError as exc:
            _handle_engine_error(exc, context)
            return context_pb2.GetUnifiedContextResponse()


async def serve_grpc() -> None:
    """启动 gRPC 服务器"""
    server = grpc.aio.server()

    # 注册服务
    conversation_pb2_grpc.add_ConversationServiceServicer_to_server(
        ConversationGrpcServicer(), server
    )
    profile_pb2_grpc.add_ProfileServiceServicer_to_server(ProfileGrpcServicer(), server)
    knowledge_pb2_grpc.add_KnowledgeServiceServicer_to_server(KnowledgeGrpcServicer(), server)
    context_pb2_grpc.add_ContextServiceServicer_to_server(ContextGrpcServicer(), server)

    server.add_insecure_port(f"[::]:{settings.GRPC_PORT}")
    await server.start()
    logger.info(f"gRPC server started on port {settings.GRPC_PORT}")
    await server.wait_for_termination()

"""gRPC 服务器

启动 gRPC 服务，复用 Service 层逻辑。
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import grpc

from ..api.deps import (
    get_conversation_service,
    get_knowledge_service,
    get_profile_service,
)
from ..config import settings
from . import (  # noqa: F401
    conversation_pb2,
    conversation_pb2_grpc,
    knowledge_pb2,
    knowledge_pb2_grpc,
    profile_pb2,
    profile_pb2_grpc,
)

logger = logging.getLogger(__name__)


class ConversationGrpcServicer(conversation_pb2_grpc.ConversationServiceServicer):
    """会话记忆 gRPC 服务实现"""

    async def AddConversation(
        self, request: Any, context: grpc.aio.ServicerContext
    ) -> Any:
        svc = get_conversation_service()
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        metadata = dict(request.metadata) if request.metadata else None
        result = await svc.add(
            user_id=request.user_id,
            messages=messages,
            metadata=metadata,
            infer=request.infer,
        )
        memories = [
            conversation_pb2.ConversationMemory(
                id=m.id, user_id=m.user_id, content=m.content
            )
            for m in result.data
        ]
        return conversation_pb2.AddConversationResponse(
            success=result.success,
            data=memories,
            message=result.message,
        )

    async def SearchConversations(
        self, request: Any, context: grpc.aio.ServicerContext
    ) -> Any:
        svc = get_conversation_service()
        result = await svc.search(
            user_id=request.user_id,
            query=request.query,
            limit=request.limit,
            threshold=request.threshold if request.HasField("threshold") else None,
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

    async def GetConversation(
        self, request: Any, context: grpc.aio.ServicerContext
    ) -> Any:
        svc = get_conversation_service()
        result = await svc.get(request.memory_id)
        if result is None:
            await context.set_code(grpc.StatusCode.NOT_FOUND)
            await context.set_details("记忆不存在")
            return conversation_pb2.ConversationMemory()
        return conversation_pb2.ConversationMemory(
            id=result.id,
            user_id=result.user_id,
            content=result.content,
        )

    async def DeleteConversation(
        self, request: Any, context: grpc.aio.ServicerContext
    ) -> Any:
        svc = get_conversation_service()
        result = await svc.delete(request.memory_id)
        return conversation_pb2.DeleteResponse(success=result.success, message=result.message)

    async def DeleteAllConversations(
        self, request: Any, context: grpc.aio.ServicerContext
    ) -> Any:
        svc = get_conversation_service()
        result = await svc.delete_all(request.user_id)
        return conversation_pb2.DeleteResponse(success=result.success, message=result.message)


class ProfileGrpcServicer(profile_pb2_grpc.ProfileServiceServicer):
    """用户画像 gRPC 服务实现"""

    async def InsertProfile(
        self, request: Any, context: grpc.aio.ServicerContext
    ) -> Any:
        svc = get_profile_service()
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        result = await svc.insert(
            user_id=request.user_id, messages=messages, sync=request.sync
        )
        return profile_pb2.InsertProfileResponse(
            success=result.success,
            user_id=result.user_id,
            blob_id=result.blob_id or "",
            message=result.message,
        )

    async def FlushProfile(
        self, request: Any, context: grpc.aio.ServicerContext
    ) -> Any:
        svc = get_profile_service()
        result = await svc.flush(user_id=request.user_id, sync=request.sync)
        return profile_pb2.FlushProfileResponse(
            success=result.get("success", True),
            message=result.get("message", ""),
        )

    async def GetProfile(
        self, request: Any, context: grpc.aio.ServicerContext
    ) -> Any:
        svc = get_profile_service()
        result = await svc.get_profile(request.user_id)
        profile_data = result.get("data")
        topics = []
        if profile_data and hasattr(profile_data, "topics"):
            for t in profile_data.topics:
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

    async def GetContext(
        self, request: Any, context: grpc.aio.ServicerContext
    ) -> Any:
        svc = get_profile_service()
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
        ctx_data = result.get("data")
        context_text = ctx_data.context if ctx_data and hasattr(ctx_data, "context") else ""
        return profile_pb2.GetContextResponse(
            success=result.get("success", True),
            user_id=request.user_id,
            context=context_text,
        )


class KnowledgeGrpcServicer(knowledge_pb2_grpc.KnowledgeServiceServicer):
    """知识库 gRPC 服务实现"""

    async def CreateDataset(
        self, request: Any, context: grpc.aio.ServicerContext
    ) -> Any:
        svc = get_knowledge_service()
        result = await svc.create_dataset(name=request.name)
        ds = result.data[0] if result.data else None
        return knowledge_pb2.DatasetInfo(
            id=ds.id if ds else "",
            name=ds.name if ds else request.name,
        )

    async def ListDatasets(
        self, request: Any, context: grpc.aio.ServicerContext
    ) -> Any:
        svc = get_knowledge_service()
        result = await svc.list_datasets()
        datasets = [
            knowledge_pb2.DatasetInfo(id=ds.id, name=ds.name) for ds in result.data
        ]
        return knowledge_pb2.ListDatasetsResponse(
            success=result.success,
            data=datasets,
            message=result.message,
        )

    async def AddKnowledge(
        self, request: Any, context: grpc.aio.ServicerContext
    ) -> Any:
        svc = get_knowledge_service()
        result = await svc.add(data=request.data, dataset=request.dataset)
        return knowledge_pb2.AddKnowledgeResponse(
            success=result.success,
            data_id=result.data_id or "",
            dataset_name=result.dataset_name,
            message=result.message,
        )

    async def Cognify(
        self, request: Any, context: grpc.aio.ServicerContext
    ) -> Any:
        svc = get_knowledge_service()
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

    async def SearchKnowledge(
        self, request: Any, context: grpc.aio.ServicerContext
    ) -> Any:
        svc = get_knowledge_service()
        result = await svc.search(
            query=request.query,
            dataset=request.dataset or None,
            search_type=request.search_type,
            top_k=request.top_k,
        )
        results = [
            knowledge_pb2.KnowledgeSearchResult(
                id=r.id,
                text=r.text if hasattr(r, "text") else r.content if hasattr(r, "content") else "",
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


async def serve_grpc() -> None:
    """启动 gRPC 服务器"""
    server = grpc.aio.server(ThreadPoolExecutor(max_workers=10))

    # 注册服务
    conversation_pb2_grpc.add_ConversationServiceServicer_to_server(
        ConversationGrpcServicer(), server
    )
    profile_pb2_grpc.add_ProfileServiceServicer_to_server(
        ProfileGrpcServicer(), server
    )
    knowledge_pb2_grpc.add_KnowledgeServiceServicer_to_server(
        KnowledgeGrpcServicer(), server
    )

    server.add_insecure_port(f"[::]:{settings.GRPC_PORT}")
    await server.start()
    logger.info(f"gRPC server started on port {settings.GRPC_PORT}")
    await server.wait_for_termination()

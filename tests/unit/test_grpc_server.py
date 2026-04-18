"""gRPC 服务实现单元测试

测试三个 gRPC Servicer 类的业务逻辑：
- 正确委托到 Service 层
- 正确将 Service 响应转为 proto 消息
- EngineError → 正确的 gRPC 状态码和错误详情
- _handle_engine_error 状态码映射
"""

from unittest.mock import AsyncMock, MagicMock, patch

import grpc
import pytest

from cozymemory.clients.base import EngineError
from cozymemory.grpc_server import (
    conversation_pb2,
    knowledge_pb2,
    profile_pb2,
)
from cozymemory.grpc_server.server import (
    ConversationGrpcServicer,
    KnowledgeGrpcServicer,
    ProfileGrpcServicer,
    _handle_engine_error,
)
from cozymemory.models.conversation import ConversationMemory, ConversationMemoryListResponse
from cozymemory.models.knowledge import (
    KnowledgeAddResponse,
    KnowledgeCognifyResponse,
    KnowledgeDataset,
    KnowledgeDatasetListResponse,
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
)
from cozymemory.models.profile import (
    ProfileContext,
    ProfileContextResponse,
    ProfileFlushResponse,
    ProfileGetResponse,
    ProfileInsertResponse,
    ProfileTopic,
    UserProfile,
)


def _ctx() -> MagicMock:
    """创建 mock gRPC context。
    set_code / set_details 用 AsyncMock，兼容两种调用方式：
    - _handle_engine_error 里不加 await（同步调用）
    - GetConversation 里用 await（异步调用）
    """
    ctx = MagicMock()
    ctx.set_code = AsyncMock()
    ctx.set_details = AsyncMock()
    return ctx


# ══════════════════════════════════════════════════════════════════════════════
# _handle_engine_error 状态码映射
# ══════════════════════════════════════════════════════════════════════════════


class TestHandleEngineError:
    """_handle_engine_error 将 EngineError 映射为正确的 gRPC 状态码"""

    def test_5xx_maps_to_unavailable(self):
        ctx = MagicMock()
        _handle_engine_error(EngineError("Mem0", "Service unavailable", 503), ctx)
        ctx.set_code.assert_called_once_with(grpc.StatusCode.UNAVAILABLE)

    def test_500_maps_to_unavailable(self):
        ctx = MagicMock()
        _handle_engine_error(EngineError("Mem0", "Internal error", 500), ctx)
        ctx.set_code.assert_called_once_with(grpc.StatusCode.UNAVAILABLE)

    def test_404_maps_to_not_found(self):
        ctx = MagicMock()
        _handle_engine_error(EngineError("Mem0", "Not found", 404), ctx)
        ctx.set_code.assert_called_once_with(grpc.StatusCode.NOT_FOUND)

    def test_4xx_maps_to_failed_precondition(self):
        ctx = MagicMock()
        _handle_engine_error(EngineError("Mem0", "Bad request", 400), ctx)
        ctx.set_code.assert_called_once_with(grpc.StatusCode.FAILED_PRECONDITION)

    def test_none_status_maps_to_internal(self):
        ctx = MagicMock()
        _handle_engine_error(EngineError("Mem0", "Unknown", None), ctx)
        ctx.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)

    def test_set_details_includes_engine_and_message(self):
        ctx = MagicMock()
        _handle_engine_error(EngineError("Cognee", "graph error", 500), ctx)
        ctx.set_details.assert_called_once_with("[Cognee] graph error")


# ══════════════════════════════════════════════════════════════════════════════
# ConversationGrpcServicer
# ══════════════════════════════════════════════════════════════════════════════


class TestConversationGrpcServicer:

    # ── AddConversation ──────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_add_conversation_success(self):
        mock_svc = MagicMock()
        mock_svc.add = AsyncMock(
            return_value=ConversationMemoryListResponse(
                success=True,
                data=[ConversationMemory(id="m1", user_id="u1", content="喜欢咖啡")],
                total=1,
                message="提取 1 条记忆",
            )
        )
        req = conversation_pb2.AddConversationRequest(
            user_id="u1",
            messages=[conversation_pb2.Message(role="user", content="我喜欢咖啡")],
            infer=True,
        )
        with patch("cozymemory.grpc_server.server.get_conversation_service", return_value=mock_svc):
            resp = await ConversationGrpcServicer().AddConversation(req, _ctx())
        assert resp.success is True
        assert len(resp.data) == 1
        assert resp.data[0].id == "m1"
        assert resp.data[0].content == "喜欢咖啡"

    @pytest.mark.asyncio
    async def test_add_conversation_engine_error_sets_grpc_status(self):
        mock_svc = MagicMock()
        mock_svc.add = AsyncMock(side_effect=EngineError("Mem0", "upstream down", 503))
        req = conversation_pb2.AddConversationRequest(
            user_id="u1",
            messages=[conversation_pb2.Message(role="user", content="hi")],
        )
        ctx = _ctx()
        with patch("cozymemory.grpc_server.server.get_conversation_service", return_value=mock_svc):
            resp = await ConversationGrpcServicer().AddConversation(req, ctx)
        ctx.set_code.assert_called_once_with(grpc.StatusCode.UNAVAILABLE)
        ctx.set_details.assert_called_once()
        assert resp.success is False  # default proto bool value

    # ── SearchConversations ──────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_search_conversations_returns_results(self):
        mock_svc = MagicMock()
        mock_svc.search = AsyncMock(
            return_value=ConversationMemoryListResponse(
                success=True,
                data=[ConversationMemory(id="m2", user_id="u1", content="咖啡", score=0.9)],
                total=1,
            )
        )
        req = conversation_pb2.SearchConversationsRequest(
            user_id="u1", query="咖啡", limit=10
        )
        with patch("cozymemory.grpc_server.server.get_conversation_service", return_value=mock_svc):
            resp = await ConversationGrpcServicer().SearchConversations(req, _ctx())
        assert resp.success is True
        assert resp.total == 1
        assert resp.data[0].score == pytest.approx(0.9)

    @pytest.mark.asyncio
    async def test_search_conversations_engine_error(self):
        mock_svc = MagicMock()
        mock_svc.search = AsyncMock(side_effect=EngineError("Mem0", "timeout", 504))
        req = conversation_pb2.SearchConversationsRequest(user_id="u1", query="test")
        ctx = _ctx()
        with patch("cozymemory.grpc_server.server.get_conversation_service", return_value=mock_svc):
            await ConversationGrpcServicer().SearchConversations(req, ctx)
        ctx.set_code.assert_called_once_with(grpc.StatusCode.UNAVAILABLE)

    # ── GetConversation ──────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_conversation_found(self):
        mock_svc = MagicMock()
        mock_svc.get = AsyncMock(
            return_value=ConversationMemory(id="m1", user_id="u1", content="咖啡")
        )
        req = conversation_pb2.GetConversationRequest(memory_id="m1")
        with patch("cozymemory.grpc_server.server.get_conversation_service", return_value=mock_svc):
            resp = await ConversationGrpcServicer().GetConversation(req, _ctx())
        assert resp.id == "m1"
        assert resp.content == "咖啡"

    @pytest.mark.asyncio
    async def test_get_conversation_not_found_sets_not_found_code(self):
        mock_svc = MagicMock()
        mock_svc.get = AsyncMock(return_value=None)
        req = conversation_pb2.GetConversationRequest(memory_id="nonexistent")
        ctx = _ctx()
        with patch("cozymemory.grpc_server.server.get_conversation_service", return_value=mock_svc):
            await ConversationGrpcServicer().GetConversation(req, ctx)
        ctx.set_code.assert_called_once_with(grpc.StatusCode.NOT_FOUND)

    @pytest.mark.asyncio
    async def test_get_conversation_engine_error(self):
        mock_svc = MagicMock()
        mock_svc.get = AsyncMock(side_effect=EngineError("Mem0", "error", 500))
        req = conversation_pb2.GetConversationRequest(memory_id="m1")
        ctx = _ctx()
        with patch("cozymemory.grpc_server.server.get_conversation_service", return_value=mock_svc):
            await ConversationGrpcServicer().GetConversation(req, ctx)
        ctx.set_code.assert_called_once_with(grpc.StatusCode.UNAVAILABLE)

    # ── DeleteConversation ───────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_delete_conversation_success(self):
        mock_svc = MagicMock()
        mock_svc.delete = AsyncMock(
            return_value=ConversationMemoryListResponse(success=True, message="已删除")
        )
        req = conversation_pb2.DeleteConversationRequest(memory_id="m1")
        with patch("cozymemory.grpc_server.server.get_conversation_service", return_value=mock_svc):
            resp = await ConversationGrpcServicer().DeleteConversation(req, _ctx())
        assert resp.success is True
        assert resp.message == "已删除"

    @pytest.mark.asyncio
    async def test_delete_all_conversations_success(self):
        mock_svc = MagicMock()
        mock_svc.delete_all = AsyncMock(
            return_value=ConversationMemoryListResponse(success=True, message="全部删除")
        )
        req = conversation_pb2.DeleteAllConversationsRequest(user_id="u1")
        with patch("cozymemory.grpc_server.server.get_conversation_service", return_value=mock_svc):
            resp = await ConversationGrpcServicer().DeleteAllConversations(req, _ctx())
        assert resp.success is True


# ══════════════════════════════════════════════════════════════════════════════
# ProfileGrpcServicer
# ══════════════════════════════════════════════════════════════════════════════


class TestProfileGrpcServicer:

    # ── InsertProfile ────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_insert_profile_success(self):
        mock_svc = MagicMock()
        mock_svc.insert = AsyncMock(
            return_value=ProfileInsertResponse(
                success=True, user_id="uid-1", blob_id="blob_x", message="已插入"
            )
        )
        req = profile_pb2.InsertProfileRequest(
            user_id="uid-1",
            messages=[conversation_pb2.Message(role="user", content="我叫小明")],
            sync=True,
        )
        with patch("cozymemory.grpc_server.server.get_profile_service", return_value=mock_svc):
            resp = await ProfileGrpcServicer().InsertProfile(req, _ctx())
        assert resp.success is True
        assert resp.user_id == "uid-1"
        assert resp.blob_id == "blob_x"

    @pytest.mark.asyncio
    async def test_insert_profile_engine_error(self):
        mock_svc = MagicMock()
        mock_svc.insert = AsyncMock(side_effect=EngineError("Memobase", "FK error", 500))
        req = profile_pb2.InsertProfileRequest(
            user_id="uid-1",
            messages=[conversation_pb2.Message(role="user", content="test")],
        )
        ctx = _ctx()
        with patch("cozymemory.grpc_server.server.get_profile_service", return_value=mock_svc):
            await ProfileGrpcServicer().InsertProfile(req, ctx)
        ctx.set_code.assert_called_once_with(grpc.StatusCode.UNAVAILABLE)
        ctx.set_details.assert_called_once_with("[Memobase] FK error")

    # ── FlushProfile ─────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_flush_profile_success(self):
        mock_svc = MagicMock()
        mock_svc.flush = AsyncMock(
            return_value=ProfileFlushResponse(success=True, message="处理完成")
        )
        req = profile_pb2.FlushProfileRequest(user_id="uid-1", sync=True)
        with patch("cozymemory.grpc_server.server.get_profile_service", return_value=mock_svc):
            resp = await ProfileGrpcServicer().FlushProfile(req, _ctx())
        assert resp.success is True

    @pytest.mark.asyncio
    async def test_flush_profile_engine_error(self):
        mock_svc = MagicMock()
        mock_svc.flush = AsyncMock(side_effect=EngineError("Memobase", "flush failed", 500))
        req = profile_pb2.FlushProfileRequest(user_id="uid-1")
        ctx = _ctx()
        with patch("cozymemory.grpc_server.server.get_profile_service", return_value=mock_svc):
            await ProfileGrpcServicer().FlushProfile(req, ctx)
        ctx.set_code.assert_called_once_with(grpc.StatusCode.UNAVAILABLE)

    # ── GetProfile ───────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_profile_with_topics(self):
        mock_svc = MagicMock()
        mock_svc.get_profile = AsyncMock(
            return_value=ProfileGetResponse(
                success=True,
                data=UserProfile(
                    user_id="uid-1",
                    topics=[
                        ProfileTopic(
                            id="p1", topic="basic_info", sub_topic="name", content="小明"
                        ),
                        ProfileTopic(
                            id="p2", topic="interest", sub_topic="hobby", content="游泳"
                        ),
                    ],
                ),
            )
        )
        req = profile_pb2.GetProfileRequest(user_id="uid-1")
        with patch("cozymemory.grpc_server.server.get_profile_service", return_value=mock_svc):
            resp = await ProfileGrpcServicer().GetProfile(req, _ctx())
        assert resp.user_id == "uid-1"
        assert len(resp.topics) == 2
        assert resp.topics[0].topic == "basic_info"
        assert resp.topics[1].content == "游泳"

    @pytest.mark.asyncio
    async def test_get_profile_engine_error(self):
        mock_svc = MagicMock()
        mock_svc.get_profile = AsyncMock(side_effect=EngineError("Memobase", "error", 500))
        req = profile_pb2.GetProfileRequest(user_id="uid-1")
        ctx = _ctx()
        with patch("cozymemory.grpc_server.server.get_profile_service", return_value=mock_svc):
            await ProfileGrpcServicer().GetProfile(req, ctx)
        ctx.set_code.assert_called_once_with(grpc.StatusCode.UNAVAILABLE)

    # ── GetContext ───────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_context_success(self):
        mock_svc = MagicMock()
        mock_svc.get_context = AsyncMock(
            return_value=ProfileContextResponse(
                success=True,
                data=ProfileContext(user_id="uid-1", context="# 用户背景\n- 姓名: 小明"),
            )
        )
        req = profile_pb2.GetContextRequest(user_id="uid-1", max_token_size=500)
        with patch("cozymemory.grpc_server.server.get_profile_service", return_value=mock_svc):
            resp = await ProfileGrpcServicer().GetContext(req, _ctx())
        assert resp.success is True
        assert "小明" in resp.context

    @pytest.mark.asyncio
    async def test_get_context_engine_error(self):
        mock_svc = MagicMock()
        mock_svc.get_context = AsyncMock(side_effect=EngineError("Memobase", "error", 400))
        req = profile_pb2.GetContextRequest(user_id="uid-1", max_token_size=300)
        ctx = _ctx()
        with patch("cozymemory.grpc_server.server.get_profile_service", return_value=mock_svc):
            await ProfileGrpcServicer().GetContext(req, ctx)
        ctx.set_code.assert_called_once_with(grpc.StatusCode.FAILED_PRECONDITION)


# ══════════════════════════════════════════════════════════════════════════════
# KnowledgeGrpcServicer
# ══════════════════════════════════════════════════════════════════════════════


class TestKnowledgeGrpcServicer:

    # ── ListDatasets ─────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_list_datasets_success(self):
        mock_svc = MagicMock()
        mock_svc.list_datasets = AsyncMock(
            return_value=KnowledgeDatasetListResponse(
                success=True,
                data=[
                    KnowledgeDataset(id="ds-1", name="default"),
                    KnowledgeDataset(id="ds-2", name="docs"),
                ],
            )
        )
        req = knowledge_pb2.ListDatasetsRequest()
        with patch("cozymemory.grpc_server.server.get_knowledge_service", return_value=mock_svc):
            resp = await KnowledgeGrpcServicer().ListDatasets(req, _ctx())
        assert resp.success is True
        assert len(resp.data) == 2
        assert resp.data[0].name == "default"

    @pytest.mark.asyncio
    async def test_list_datasets_engine_error(self):
        mock_svc = MagicMock()
        mock_svc.list_datasets = AsyncMock(
            side_effect=EngineError("Cognee", "graph unavailable", 503)
        )
        ctx = _ctx()
        with patch("cozymemory.grpc_server.server.get_knowledge_service", return_value=mock_svc):
            await KnowledgeGrpcServicer().ListDatasets(knowledge_pb2.ListDatasetsRequest(), ctx)
        ctx.set_code.assert_called_once_with(grpc.StatusCode.UNAVAILABLE)

    # ── AddKnowledge ─────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_add_knowledge_success(self):
        mock_svc = MagicMock()
        mock_svc.add = AsyncMock(
            return_value=KnowledgeAddResponse(
                success=True, data_id="doc-1", dataset_name="default", message="已添加"
            )
        )
        req = knowledge_pb2.AddKnowledgeRequest(data="CozyMemory 介绍", dataset="default")
        with patch("cozymemory.grpc_server.server.get_knowledge_service", return_value=mock_svc):
            resp = await KnowledgeGrpcServicer().AddKnowledge(req, _ctx())
        assert resp.success is True
        assert resp.data_id == "doc-1"
        assert resp.dataset_name == "default"

    @pytest.mark.asyncio
    async def test_add_knowledge_engine_error(self):
        mock_svc = MagicMock()
        mock_svc.add = AsyncMock(side_effect=EngineError("Cognee", "add failed", 500))
        req = knowledge_pb2.AddKnowledgeRequest(data="test", dataset="ds")
        ctx = _ctx()
        with patch("cozymemory.grpc_server.server.get_knowledge_service", return_value=mock_svc):
            await KnowledgeGrpcServicer().AddKnowledge(req, ctx)
        ctx.set_code.assert_called_once_with(grpc.StatusCode.UNAVAILABLE)
        ctx.set_details.assert_called_once_with("[Cognee] add failed")

    # ── Cognify ──────────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_cognify_success(self):
        mock_svc = MagicMock()
        mock_svc.cognify = AsyncMock(
            return_value=KnowledgeCognifyResponse(
                success=True, pipeline_run_id="run-42", status="pending", message="已启动"
            )
        )
        req = knowledge_pb2.CognifyRequest(datasets=["default"], run_in_background=True)
        with patch("cozymemory.grpc_server.server.get_knowledge_service", return_value=mock_svc):
            resp = await KnowledgeGrpcServicer().Cognify(req, _ctx())
        assert resp.success is True
        assert resp.pipeline_run_id == "run-42"
        assert resp.status == "pending"

    @pytest.mark.asyncio
    async def test_cognify_engine_error(self):
        mock_svc = MagicMock()
        mock_svc.cognify = AsyncMock(side_effect=EngineError("Cognee", "cognify error", 500))
        ctx = _ctx()
        with patch("cozymemory.grpc_server.server.get_knowledge_service", return_value=mock_svc):
            await KnowledgeGrpcServicer().Cognify(knowledge_pb2.CognifyRequest(), ctx)
        ctx.set_code.assert_called_once_with(grpc.StatusCode.UNAVAILABLE)

    # ── SearchKnowledge ──────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_search_knowledge_returns_results(self):
        mock_svc = MagicMock()
        mock_svc.search = AsyncMock(
            return_value=KnowledgeSearchResponse(
                success=True,
                data=[KnowledgeSearchResult(id="r1", text="CozyMemory 介绍", score=0.95)],
                total=1,
            )
        )
        req = knowledge_pb2.SearchKnowledgeRequest(
            query="CozyMemory 是什么", search_type="CHUNKS", top_k=5
        )
        with patch("cozymemory.grpc_server.server.get_knowledge_service", return_value=mock_svc):
            resp = await KnowledgeGrpcServicer().SearchKnowledge(req, _ctx())
        assert resp.success is True
        assert resp.total == 1
        assert resp.data[0].score == pytest.approx(0.95)

    @pytest.mark.asyncio
    async def test_search_knowledge_engine_error(self):
        mock_svc = MagicMock()
        mock_svc.search = AsyncMock(side_effect=EngineError("Cognee", "search error", 500))
        req = knowledge_pb2.SearchKnowledgeRequest(query="test")
        ctx = _ctx()
        with patch("cozymemory.grpc_server.server.get_knowledge_service", return_value=mock_svc):
            await KnowledgeGrpcServicer().SearchKnowledge(req, ctx)
        ctx.set_code.assert_called_once_with(grpc.StatusCode.UNAVAILABLE)

    # ── CreateDataset ─────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_create_dataset_success(self):
        mock_svc = MagicMock()
        mock_svc.create_dataset = AsyncMock(
            return_value=KnowledgeDatasetListResponse(
                success=True,
                data=[KnowledgeDataset(id="ds-new", name="my-ds")],
            )
        )
        req = knowledge_pb2.CreateDatasetRequest(name="my-ds")
        with patch("cozymemory.grpc_server.server.get_knowledge_service", return_value=mock_svc):
            resp = await KnowledgeGrpcServicer().CreateDataset(req, _ctx())
        assert resp.name == "my-ds"
        assert resp.id == "ds-new"

    @pytest.mark.asyncio
    async def test_create_dataset_engine_error(self):
        mock_svc = MagicMock()
        mock_svc.create_dataset = AsyncMock(
            side_effect=EngineError("Cognee", "create failed", 500)
        )
        ctx = _ctx()
        with patch("cozymemory.grpc_server.server.get_knowledge_service", return_value=mock_svc):
            await KnowledgeGrpcServicer().CreateDataset(
                knowledge_pb2.CreateDatasetRequest(name="ds"), ctx
            )
        ctx.set_code.assert_called_once_with(grpc.StatusCode.UNAVAILABLE)


# ══════════════════════════════════════════════════════════════════════════════
# 烟雾测试：类结构与 proto 模块可导入性（保留原有检查）
# ══════════════════════════════════════════════════════════════════════════════


class TestServicerStructure:

    def test_conversation_servicer_has_all_methods(self):
        s = ConversationGrpcServicer()
        for method in ("AddConversation", "SearchConversations", "GetConversation",
                       "DeleteConversation", "DeleteAllConversations"):
            assert hasattr(s, method)

    def test_profile_servicer_has_all_methods(self):
        s = ProfileGrpcServicer()
        for method in ("InsertProfile", "FlushProfile", "GetProfile", "GetContext"):
            assert hasattr(s, method)

    def test_knowledge_servicer_has_all_methods(self):
        s = KnowledgeGrpcServicer()
        for method in ("CreateDataset", "ListDatasets", "AddKnowledge",
                       "Cognify", "SearchKnowledge"):
            assert hasattr(s, method)

    def test_serve_grpc_is_coroutine(self):
        import asyncio

        from cozymemory.grpc_server.server import serve_grpc
        assert asyncio.iscoroutinefunction(serve_grpc)

    def test_proto_modules_importable(self):
        from cozymemory.grpc_server import (
            common_pb2,
            conversation_pb2,
            knowledge_pb2,
            profile_pb2,
        )
        assert hasattr(conversation_pb2, "AddConversationRequest")
        assert hasattr(profile_pb2, "InsertProfileRequest")
        assert hasattr(knowledge_pb2, "AddKnowledgeRequest")
        assert hasattr(common_pb2, "HealthRequest")

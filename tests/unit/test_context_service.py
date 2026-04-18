"""ContextService 单元测试

验证并发编排逻辑、部分失败容错、query 路由、include 开关。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from cozymemory.clients.base import EngineError
from cozymemory.models.context import ContextRequest
from cozymemory.models.conversation import ConversationMemory, ConversationMemoryListResponse
from cozymemory.models.knowledge import KnowledgeSearchResponse, KnowledgeSearchResult
from cozymemory.models.profile import ProfileContext, ProfileContextResponse
from cozymemory.services.context import ContextService


def _make_service(
    conv_result=None,
    profile_result=None,
    knowledge_result=None,
    conv_error=None,
    profile_error=None,
    knowledge_error=None,
):
    """构造 ContextService，注入 mock 子服务"""
    conv = MagicMock()
    profile = MagicMock()
    knowledge = MagicMock()

    conv.search = AsyncMock(
        return_value=conv_result or ConversationMemoryListResponse(success=True, data=[], total=0),
        side_effect=conv_error,
    )
    conv.get_all = AsyncMock(
        return_value=conv_result or ConversationMemoryListResponse(success=True, data=[], total=0),
        side_effect=conv_error,
    )
    profile.get_context = AsyncMock(
        return_value=profile_result
        or ProfileContextResponse(
            success=True, data=ProfileContext(user_id="u1", context="用户叫小明")
        ),
        side_effect=profile_error,
    )
    knowledge.search = AsyncMock(
        return_value=knowledge_result
        or KnowledgeSearchResponse(success=True, data=[], total=0),
        side_effect=knowledge_error,
    )
    return ContextService(conv_service=conv, profile_service=profile, knowledge_service=knowledge)


# ===== 正常路径 =====


@pytest.mark.asyncio
async def test_all_engines_succeed_with_query():
    """有 query 时三个引擎全部成功"""
    memory = ConversationMemory(id="m1", user_id="u1", content="喜欢篮球")
    knowledge_item = KnowledgeSearchResult(id="k1", text="篮球知识")
    svc = _make_service(
        conv_result=ConversationMemoryListResponse(success=True, data=[memory], total=1),
        profile_result=ProfileContextResponse(
            success=True, data=ProfileContext(user_id="u1", context="用户叫小明，喜欢运动")
        ),
        knowledge_result=KnowledgeSearchResponse(success=True, data=[knowledge_item], total=1),
    )

    req = ContextRequest(user_id="u1", query="用户喜欢什么运动")
    resp = await svc.get_context(req)

    assert resp.success is True
    assert len(resp.conversations) == 1
    assert resp.conversations[0].content == "喜欢篮球"
    assert resp.profile_context == "用户叫小明，喜欢运动"
    assert len(resp.knowledge) == 1
    assert resp.errors == {}
    assert resp.latency_ms >= 0


@pytest.mark.asyncio
async def test_no_query_uses_get_all_and_skips_knowledge():
    """无 query 时使用 get_all，Cognee 不执行"""
    svc = _make_service()
    req = ContextRequest(user_id="u1", query=None, include_knowledge=True)
    resp = await svc.get_context(req)

    svc._conv.get_all.assert_called_once()
    svc._conv.search.assert_not_called()
    svc._knowledge.search.assert_not_called()
    assert resp.knowledge == []
    assert "knowledge" not in resp.errors


@pytest.mark.asyncio
async def test_include_flags_disable_engines():
    """include_conversations=False 时 Mem0 不执行"""
    svc = _make_service()
    req = ContextRequest(
        user_id="u1",
        query="test",
        include_conversations=False,
        include_profile=True,
        include_knowledge=False,
    )
    resp = await svc.get_context(req)

    svc._conv.search.assert_not_called()
    svc._conv.get_all.assert_not_called()
    svc._knowledge.search.assert_not_called()
    svc._profile.get_context.assert_called_once()
    assert resp.conversations == []


# ===== 部分失败 =====


@pytest.mark.asyncio
async def test_one_engine_fails_others_still_return():
    """单个引擎 EngineError 时，其余引擎结果正常返回"""
    svc = _make_service(
        profile_error=EngineError("Memobase", "timeout", 504),
    )
    req = ContextRequest(user_id="u1", query="test")
    resp = await svc.get_context(req)

    assert resp.success is True
    assert "profile" in resp.errors
    assert "timeout" in resp.errors["profile"]
    assert resp.profile_context is None
    # conversations and knowledge should still be populated (empty lists from mock defaults)
    assert isinstance(resp.conversations, list)


@pytest.mark.asyncio
async def test_all_engines_fail_errors_populated():
    """三个引擎全部失败时 errors 包含全部键，数据字段为空"""
    svc = _make_service(
        conv_error=EngineError("Mem0", "down", 503),
        profile_error=EngineError("Memobase", "down", 503),
        knowledge_error=EngineError("Cognee", "down", 503),
    )
    req = ContextRequest(user_id="u1", query="test")
    resp = await svc.get_context(req)

    assert resp.success is True  # 仍返回 200，调用方通过 errors 判断
    assert set(resp.errors.keys()) == {"conversations", "profile", "knowledge"}
    assert resp.conversations == []
    assert resp.profile_context is None
    assert resp.knowledge == []


@pytest.mark.asyncio
async def test_generic_exception_also_captured():
    """非 EngineError 的普通异常也被捕获到 errors"""
    svc = _make_service(conv_error=RuntimeError("unexpected"))
    req = ContextRequest(user_id="u1", query="test")
    resp = await svc.get_context(req)

    assert "conversations" in resp.errors
    assert "unexpected" in resp.errors["conversations"]


# ===== 参数透传 =====


@pytest.mark.asyncio
async def test_conversation_limit_forwarded():
    """conversation_limit 参数正确传递给子服务"""
    svc = _make_service()
    req = ContextRequest(user_id="u1", query="test", conversation_limit=3)
    await svc.get_context(req)

    call_kwargs = svc._conv.search.call_args.kwargs
    assert call_kwargs["limit"] == 3


@pytest.mark.asyncio
async def test_knowledge_search_type_forwarded():
    """knowledge_search_type 正确传递给 KnowledgeService"""
    svc = _make_service()
    req = ContextRequest(user_id="u1", query="test", knowledge_search_type="CHUNKS")
    await svc.get_context(req)

    call_kwargs = svc._knowledge.search.call_args.kwargs
    assert call_kwargs["search_type"] == "CHUNKS"


@pytest.mark.asyncio
async def test_profile_context_none_when_data_missing():
    """Memobase 返回 data=None 时 profile_context 为 None"""
    svc = _make_service(
        profile_result=ProfileContextResponse(success=True, data=None),
    )
    req = ContextRequest(user_id="u1", include_knowledge=False)
    resp = await svc.get_context(req)

    assert resp.profile_context is None


# ===== engine_timeout =====


@pytest.mark.asyncio
async def test_engine_timeout_captures_error():
    """engine_timeout 触发时，超时引擎记录专用错误消息，其他引擎结果正常返回"""
    import asyncio

    async def slow_profile(*args, **kwargs):
        await asyncio.sleep(10)  # 故意超时

    svc = _make_service()
    svc._profile.get_context = slow_profile  # type: ignore[method-assign]

    req = ContextRequest(user_id="u1", query="test", engine_timeout=0.05)
    resp = await svc.get_context(req)

    assert "profile" in resp.errors
    assert "timeout" in resp.errors["profile"]
    assert resp.profile_context is None
    # 其他引擎不受影响
    assert isinstance(resp.conversations, list)


@pytest.mark.asyncio
async def test_engine_timeout_none_no_wrapping():
    """engine_timeout=None 时不包装协程，所有引擎正常执行"""
    svc = _make_service()
    req = ContextRequest(user_id="u1", query="test", engine_timeout=None)
    resp = await svc.get_context(req)

    assert resp.errors == {}
    assert resp.profile_context is not None


# ===== chats 参数透传 =====


@pytest.mark.asyncio
async def test_chats_forwarded_to_profile_service():
    """chats 参数正确转换并传递给 ProfileService.get_context"""
    from cozymemory.models.common import Message

    svc = _make_service()
    req = ContextRequest(
        user_id="u1",
        include_knowledge=False,
        chats=[Message(role="user", content="你好")],
    )
    await svc.get_context(req)

    call_kwargs = svc._profile.get_context.call_args.kwargs
    assert call_kwargs["chats"] == [{"role": "user", "content": "你好"}]


@pytest.mark.asyncio
async def test_chats_none_passes_none_to_profile_service():
    """chats=None 时传给 ProfileService 的 chats 也是 None"""
    svc = _make_service()
    req = ContextRequest(user_id="u1", include_knowledge=False, chats=None)
    await svc.get_context(req)

    call_kwargs = svc._profile.get_context.call_args.kwargs
    assert call_kwargs["chats"] is None

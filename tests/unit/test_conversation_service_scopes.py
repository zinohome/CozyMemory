"""ConversationService 补测 — memory_scope 三档 + search_short 辅助方法。"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from cozymemory.models.conversation import ConversationMemory
from cozymemory.services.conversation import ConversationService


def _mem(mid: str, content: str) -> ConversationMemory:
    return ConversationMemory(id=mid, user_id="u1", content=content)


@pytest.fixture
def mock_client():
    c = MagicMock()
    c.search = AsyncMock(return_value=[])
    c.get_all = AsyncMock(return_value=[])
    return c


@pytest.fixture
def service(mock_client):
    return ConversationService(mock_client)


# ───────────────────────── search: long / short / both ─────────────────────────


@pytest.mark.asyncio
async def test_search_short_scope_passes_session_id(service, mock_client):
    mock_client.search.return_value = [_mem("m1", "short-only")]
    resp = await service.search(
        user_id="u1", query="q", session_id="s1", memory_scope="short"
    )
    assert len(resp.data) == 1
    call = mock_client.search.await_args
    assert call.kwargs["session_id"] == "s1"


@pytest.mark.asyncio
async def test_search_long_scope_drops_session_id(service, mock_client):
    mock_client.search.return_value = [_mem("m1", "long")]
    await service.search(
        user_id="u1", query="q", session_id="s1", memory_scope="long"
    )
    call = mock_client.search.await_args
    # long scope 应该 session_id=None 而不是用户传的
    assert call.kwargs["session_id"] is None


@pytest.mark.asyncio
async def test_search_both_scope_returns_short_and_long_separately(
    service, mock_client
):
    # 两次并发调用 client.search 会拿到不同结果
    mock_client.search.side_effect = [
        [_mem("s1", "short-1")],  # 第一次 = short
        [_mem("l1", "long-1"), _mem("l2", "long-2")],  # 第二次 = long
    ]
    resp = await service.search(
        user_id="u1", query="q", session_id="sess", memory_scope="both"
    )
    # data 默认映射到长期记忆（向后兼容）
    assert resp.total == 2
    assert len(resp.long_term_memories) == 2
    assert len(resp.short_term_memories) == 1
    assert mock_client.search.await_count == 2


# ───────────────────────── get_all: long / short / both ─────────────────────────


@pytest.mark.asyncio
async def test_get_all_short_scope(service, mock_client):
    mock_client.get_all.return_value = [_mem("m1", "x")]
    resp = await service.get_all(
        user_id="u1", session_id="s", memory_scope="short"
    )
    assert resp.total == 1
    call = mock_client.get_all.await_args
    assert call.kwargs["session_id"] == "s"


@pytest.mark.asyncio
async def test_get_all_long_scope_nulls_session(service, mock_client):
    await service.get_all(
        user_id="u1", session_id="s", memory_scope="long"
    )
    call = mock_client.get_all.await_args
    assert call.kwargs["session_id"] is None


@pytest.mark.asyncio
async def test_get_all_both_scope(service, mock_client):
    mock_client.get_all.side_effect = [
        [_mem("s1", "short")],
        [_mem("l1", "long-a"), _mem("l2", "long-b")],
    ]
    resp = await service.get_all(
        user_id="u1", session_id="sess", memory_scope="both"
    )
    # 主列表 = 长期
    assert resp.total == 2
    assert len(resp.short_term_memories) == 1
    assert len(resp.long_term_memories) == 2


# ───────────────────────── search_short 辅助 ─────────────────────────


@pytest.mark.asyncio
async def test_search_short_helper_returns_raw_list(service, mock_client):
    mock_client.search.return_value = [_mem("a", "x"), _mem("b", "y")]
    result = await service.search_short(
        user_id="u1", query="q", session_id="sess"
    )
    # 返回 list[ConversationMemory] 而不是包装后的 Response
    assert isinstance(result, list)
    assert len(result) == 2
    call = mock_client.search.await_args
    assert call.kwargs["session_id"] == "sess"

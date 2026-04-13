"""会话记忆模型测试"""

import pytest

from cozymemory.models.common import Message
from cozymemory.models.conversation import (
    ConversationMemory,
    ConversationMemoryCreate,
    ConversationMemoryListResponse,
    ConversationMemorySearch,
)


def test_conversation_memory_create():
    req = ConversationMemoryCreate(
        user_id="user_123",
        messages=[Message(role="user", content="我喜欢咖啡")],
    )
    assert req.user_id == "user_123"
    assert len(req.messages) == 1
    assert req.infer is True
    assert req.metadata is None


def test_conversation_memory_create_with_metadata():
    req = ConversationMemoryCreate(
        user_id="user_123",
        messages=[Message(role="user", content="我喜欢咖啡")],
        metadata={"source": "chat", "session_id": "sess_001"},
        infer=False,
    )
    assert req.metadata["source"] == "chat"
    assert req.infer is False


def test_conversation_memory_create_validation():
    with pytest.raises(Exception):
        ConversationMemoryCreate(user_id="user_123", messages=[])


def test_conversation_memory_search():
    req = ConversationMemorySearch(user_id="user_123", query="咖啡")
    assert req.limit == 10
    assert req.threshold is None


def test_conversation_memory_search_limit_range():
    with pytest.raises(Exception):
        ConversationMemorySearch(user_id="user_123", query="咖啡", limit=0)
    with pytest.raises(Exception):
        ConversationMemorySearch(user_id="user_123", query="咖啡", limit=101)


def test_conversation_memory_response():
    mem = ConversationMemory(
        id="mem_123", user_id="user_123", content="用户喜欢喝拿铁咖啡", score=0.92
    )
    assert mem.id == "mem_123"
    assert mem.score == 0.92


def test_conversation_memory_list_response():
    resp = ConversationMemoryListResponse(
        data=[
            ConversationMemory(id="mem_1", user_id="u1", content="事实1"),
            ConversationMemory(id="mem_2", user_id="u1", content="事实2"),
        ],
        total=2,
    )
    assert resp.success is True
    assert resp.total == 2

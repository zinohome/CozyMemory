"""会话记忆服务测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from cozymemory.services.conversation import ConversationService
from cozymemory.models.conversation import ConversationMemory, ConversationMemoryListResponse
from cozymemory.clients.base import EngineError


@pytest.fixture
def mock_mem0_client():
    client = MagicMock()
    client.add = AsyncMock(return_value=[
        ConversationMemory(id="mem_1", user_id="u1", content="事实1"),
    ])
    client.search = AsyncMock(return_value=[
        ConversationMemory(id="mem_1", user_id="u1", content="事实1", score=0.9),
    ])
    client.get = AsyncMock(return_value=ConversationMemory(id="mem_1", user_id="u1", content="事实1"))
    client.get_all = AsyncMock(return_value=[
        ConversationMemory(id="mem_1", user_id="u1", content="事实1"),
    ])
    client.delete = AsyncMock(return_value=True)
    client.delete_all = AsyncMock(return_value=True)
    return client


@pytest.mark.asyncio
async def test_conversation_service_add(mock_mem0_client):
    service = ConversationService(client=mock_mem0_client)
    result = await service.add(user_id="u1", messages=[{"role": "user", "content": "你好"}])
    assert result.success is True
    assert len(result.data) == 1
    mock_mem0_client.add.assert_called_once()


@pytest.mark.asyncio
async def test_conversation_service_search(mock_mem0_client):
    service = ConversationService(client=mock_mem0_client)
    result = await service.search(user_id="u1", query="你好")
    assert result.success is True
    assert result.total == 1
    mock_mem0_client.search.assert_called_once()


@pytest.mark.asyncio
async def test_conversation_service_get(mock_mem0_client):
    service = ConversationService(client=mock_mem0_client)
    result = await service.get("mem_1")
    assert result is not None
    assert result.id == "mem_1"


@pytest.mark.asyncio
async def test_conversation_service_delete(mock_mem0_client):
    service = ConversationService(client=mock_mem0_client)
    result = await service.delete("mem_1")
    assert result.success is True
    mock_mem0_client.delete.assert_called_once_with("mem_1")


@pytest.mark.asyncio
async def test_conversation_service_delete_all(mock_mem0_client):
    service = ConversationService(client=mock_mem0_client)
    result = await service.delete_all("u1")
    assert result.success is True
    mock_mem0_client.delete_all.assert_called_once_with("u1")


@pytest.mark.asyncio
async def test_conversation_service_add_engine_error(mock_mem0_client):
    mock_mem0_client.add = AsyncMock(side_effect=EngineError("Mem0", "不可用", 503))
    service = ConversationService(client=mock_mem0_client)
    with pytest.raises(EngineError):
        await service.add(user_id="u1", messages=[{"role": "user", "content": "你好"}])
"""服务层补充测试 - 覆盖错误路径"""

from unittest.mock import AsyncMock

import pytest

from cozymemory.clients.base import EngineError
from cozymemory.services.conversation import ConversationService
from cozymemory.services.knowledge import KnowledgeService
from cozymemory.services.profile import ProfileService


@pytest.fixture
def mock_mem0_client():
    return AsyncMock()


@pytest.fixture
def mock_memobase_client():
    return AsyncMock()


@pytest.fixture
def mock_cognee_client():
    return AsyncMock()


# --- ConversationService ---


@pytest.mark.asyncio
async def test_conversation_service_add_failure_raises(mock_mem0_client):
    """ConversationService.add 失败时抛出 EngineError"""
    mock_mem0_client.add = AsyncMock(side_effect=EngineError("Mem0", "timeout", 504))
    svc = ConversationService(mock_mem0_client)
    with pytest.raises(EngineError):
        await svc.add("user_1", [{"role": "user", "content": "hello"}], metadata={})


@pytest.mark.asyncio
async def test_conversation_service_search_failure_raises(mock_mem0_client):
    """ConversationService.search 失败时抛出 EngineError"""
    mock_mem0_client.search = AsyncMock(side_effect=EngineError("Mem0", "timeout", 504))
    svc = ConversationService(mock_mem0_client)
    with pytest.raises(EngineError):
        await svc.search("user_1", "hello")


@pytest.mark.asyncio
async def test_conversation_service_get_all_failure_raises(mock_mem0_client):
    """ConversationService.get_all 失败时抛出 EngineError"""
    mock_mem0_client.get_all = AsyncMock(side_effect=EngineError("Mem0", "timeout", 504))
    svc = ConversationService(mock_mem0_client)
    with pytest.raises(EngineError):
        await svc.get_all("user_1")


@pytest.mark.asyncio
async def test_conversation_service_delete_failure_raises(mock_mem0_client):
    """ConversationService.delete 失败时抛出 EngineError"""
    mock_mem0_client.delete = AsyncMock(side_effect=EngineError("Mem0", "timeout", 504))
    svc = ConversationService(mock_mem0_client)
    with pytest.raises(EngineError):
        await svc.delete("msg_1")


@pytest.mark.asyncio
async def test_conversation_service_delete_all_failure_raises(mock_mem0_client):
    """ConversationService.delete_all 失败时抛出 EngineError"""
    mock_mem0_client.delete_all = AsyncMock(side_effect=EngineError("Mem0", "timeout", 504))
    svc = ConversationService(mock_mem0_client)
    with pytest.raises(EngineError):
        await svc.delete_all("user_1")


# --- ProfileService ---


@pytest.mark.asyncio
async def test_profile_service_insert_failure_raises(mock_memobase_client):
    """ProfileService.insert 失败时抛出 EngineError"""
    mock_memobase_client.insert = AsyncMock(side_effect=EngineError("Memobase", "error", 500))
    svc = ProfileService(mock_memobase_client)
    with pytest.raises(EngineError):
        await svc.insert("user_1", [{"role": "user", "content": "hello"}])


@pytest.mark.asyncio
async def test_profile_service_flush_failure_raises(mock_memobase_client):
    """ProfileService.flush 失败时抛出 EngineError"""
    mock_memobase_client.flush = AsyncMock(side_effect=EngineError("Memobase", "error", 500))
    svc = ProfileService(mock_memobase_client)
    with pytest.raises(EngineError):
        await svc.flush("user_1")


@pytest.mark.asyncio
async def test_profile_service_get_profile_failure_raises(mock_memobase_client):
    """ProfileService.get_profile 失败时抛出 EngineError"""
    mock_memobase_client.profile = AsyncMock(side_effect=EngineError("Memobase", "error", 500))
    svc = ProfileService(mock_memobase_client)
    with pytest.raises(EngineError):
        await svc.get_profile("user_1")


@pytest.mark.asyncio
async def test_profile_service_get_context_failure_raises(mock_memobase_client):
    """ProfileService.get_context 失败时抛出 EngineError"""
    mock_memobase_client.context = AsyncMock(side_effect=EngineError("Memobase", "error", 500))
    svc = ProfileService(mock_memobase_client)
    with pytest.raises(EngineError):
        await svc.get_context("user_1", max_token_size=300)


@pytest.mark.asyncio
async def test_profile_service_add_profile_item_failure_raises(mock_memobase_client):
    """ProfileService.add_profile_item 失败时抛出 EngineError"""
    mock_memobase_client.add_profile = AsyncMock(side_effect=EngineError("Memobase", "error", 500))
    svc = ProfileService(mock_memobase_client)
    with pytest.raises(EngineError):
        await svc.add_profile_item("user_1", "interest", "hobby", "游泳")


@pytest.mark.asyncio
async def test_profile_service_delete_profile_item_failure_raises(mock_memobase_client):
    """ProfileService.delete_profile_item 失败时抛出 EngineError"""
    mock_memobase_client.delete_profile = AsyncMock(
        side_effect=EngineError("Memobase", "error", 500)
    )
    svc = ProfileService(mock_memobase_client)
    with pytest.raises(EngineError):
        await svc.delete_profile_item("user_1", "prof_1")


# --- KnowledgeService ---


@pytest.mark.asyncio
async def test_knowledge_service_add_failure_raises(mock_cognee_client):
    """KnowledgeService.add 失败时抛出 EngineError"""
    mock_cognee_client.add = AsyncMock(side_effect=EngineError("Cognee", "error", 500))
    svc = KnowledgeService(mock_cognee_client)
    with pytest.raises(EngineError):
        await svc.add("content", dataset="test")


@pytest.mark.asyncio
async def test_knowledge_service_search_failure_raises(mock_cognee_client):
    """KnowledgeService.search 失败时抛出 EngineError"""
    mock_cognee_client.search = AsyncMock(side_effect=EngineError("Cognee", "error", 500))
    svc = KnowledgeService(mock_cognee_client)
    with pytest.raises(EngineError):
        await svc.search("test query")


@pytest.mark.asyncio
async def test_knowledge_service_cognify_failure_raises(mock_cognee_client):
    """KnowledgeService.cognify 失败时抛出 EngineError"""
    mock_cognee_client.cognify = AsyncMock(side_effect=EngineError("Cognee", "error", 500))
    svc = KnowledgeService(mock_cognee_client)
    with pytest.raises(EngineError):
        await svc.cognify()


@pytest.mark.asyncio
async def test_knowledge_service_create_dataset_failure_raises(mock_cognee_client):
    """KnowledgeService.create_dataset 失败时抛出 EngineError"""
    mock_cognee_client.create_dataset = AsyncMock(side_effect=EngineError("Cognee", "error", 500))
    svc = KnowledgeService(mock_cognee_client)
    with pytest.raises(EngineError):
        await svc.create_dataset("test_dataset")


@pytest.mark.asyncio
async def test_knowledge_service_list_datasets_failure_raises(mock_cognee_client):
    """KnowledgeService.list_datasets 失败时抛出 EngineError"""
    mock_cognee_client.list_datasets = AsyncMock(side_effect=EngineError("Cognee", "error", 500))
    svc = KnowledgeService(mock_cognee_client)
    with pytest.raises(EngineError):
        await svc.list_datasets()

"""知识库服务测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from cozymemory.services.knowledge import KnowledgeService
from cozymemory.models.knowledge import (
    KnowledgeDataset, KnowledgeAddResponse, KnowledgeCognifyResponse,
    KnowledgeSearchResponse, KnowledgeSearchResult, KnowledgeDatasetListResponse,
)
from cozymemory.clients.base import EngineError


@pytest.fixture
def mock_cognee_client():
    client = MagicMock()
    client.add = AsyncMock(return_value={"id": "data_123"})
    client.cognify = AsyncMock(return_value={"run_id": "pipe_123", "status": "pending"})
    client.search = AsyncMock(return_value=[
        KnowledgeSearchResult(id="n1", text="结果1", score=0.9),
    ])
    client.create_dataset = AsyncMock(return_value=KnowledgeDataset(id="uuid-1", name="my-ds"))
    client.list_datasets = AsyncMock(return_value=[
        KnowledgeDataset(id="uuid-1", name="ds1"),
    ])
    return client


@pytest.mark.asyncio
async def test_knowledge_service_add(mock_cognee_client):
    service = KnowledgeService(client=mock_cognee_client)
    result = await service.add(data="文本", dataset="my-ds")
    assert result.success is True
    mock_cognee_client.add.assert_called_once_with(data="文本", dataset="my-ds")


@pytest.mark.asyncio
async def test_knowledge_service_cognify(mock_cognee_client):
    service = KnowledgeService(client=mock_cognee_client)
    result = await service.cognify(datasets=["my-ds"])
    assert result.success is True
    mock_cognee_client.cognify.assert_called_once()


@pytest.mark.asyncio
async def test_knowledge_service_search(mock_cognee_client):
    service = KnowledgeService(client=mock_cognee_client)
    result = await service.search(query="Cognee 是什么？")
    assert result.success is True
    assert result.total == 1


@pytest.mark.asyncio
async def test_knowledge_service_create_dataset(mock_cognee_client):
    service = KnowledgeService(client=mock_cognee_client)
    result = await service.create_dataset(name="my-ds")
    assert result.success is True
    assert result.data[0].name == "my-ds"


@pytest.mark.asyncio
async def test_knowledge_service_list_datasets(mock_cognee_client):
    service = KnowledgeService(client=mock_cognee_client)
    result = await service.list_datasets()
    assert result.success is True
    assert len(result.data) == 1
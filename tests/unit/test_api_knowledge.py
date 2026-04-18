"""知识库 API 端点测试

测试 /api/v1/knowledge/* 的请求路由、响应格式和错误处理。
使用 dependency_overrides 注入 mock 服务。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from cozymemory.api.deps import get_knowledge_service
from cozymemory.app import create_app
from cozymemory.clients.base import EngineError
from cozymemory.models.knowledge import (
    KnowledgeAddResponse,
    KnowledgeCognifyResponse,
    KnowledgeDataset,
    KnowledgeDatasetListResponse,
    KnowledgeDeleteResponse,
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
)


@pytest.fixture
def mock_service():
    return MagicMock()


@pytest.fixture
async def client(mock_service):
    app = create_app()
    app.dependency_overrides[get_knowledge_service] = lambda: mock_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ===== GET /knowledge/datasets =====


@pytest.mark.asyncio
async def test_list_datasets_success(client, mock_service):
    """GET /knowledge/datasets 列出数据集"""
    mock_service.list_datasets = AsyncMock(
        return_value=KnowledgeDatasetListResponse(
            success=True,
            data=[
                KnowledgeDataset(id="ds-1", name="default"),
                KnowledgeDataset(id="ds-2", name="docs"),
            ],
        )
    )
    response = await client.get("/api/v1/knowledge/datasets")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) == 2
    assert body["data"][0]["name"] == "default"


@pytest.mark.asyncio
async def test_list_datasets_engine_error(client, mock_service):
    """GET /knowledge/datasets 引擎错误 → 502"""
    mock_service.list_datasets = AsyncMock(
        side_effect=EngineError("Cognee", "graph unavailable", 503)
    )
    response = await client.get("/api/v1/knowledge/datasets")
    assert response.status_code == 502
    assert response.json()["engine"] == "Cognee"


# ===== POST /knowledge/datasets =====


@pytest.mark.asyncio
async def test_create_dataset_success(client, mock_service):
    """POST /knowledge/datasets?name=test 创建数据集"""
    mock_service.create_dataset = AsyncMock(
        return_value=KnowledgeDatasetListResponse(
            success=True,
            data=[KnowledgeDataset(id="ds-new", name="test")],
            message="数据集已创建",
        )
    )
    response = await client.post("/api/v1/knowledge/datasets", params={"name": "test"})
    assert response.status_code == 200
    assert response.json()["data"][0]["name"] == "test"


# ===== POST /knowledge/add =====


@pytest.mark.asyncio
async def test_add_knowledge_success(client, mock_service):
    """POST /knowledge/add 添加文档"""
    mock_service.add = AsyncMock(
        return_value=KnowledgeAddResponse(
            success=True, data_id="doc-1", dataset_name="default", message="数据已添加"
        )
    )
    response = await client.post(
        "/api/v1/knowledge/add",
        json={"data": "CozyMemory 是一个统一记忆服务", "dataset": "default"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data_id"] == "doc-1"


@pytest.mark.asyncio
async def test_add_knowledge_missing_fields(client, mock_service):
    """POST /knowledge/add 缺少必填字段 → 422"""
    response = await client.post(
        "/api/v1/knowledge/add",
        json={"data": "内容"},  # 缺少 dataset
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_knowledge_engine_error(client, mock_service):
    """POST /knowledge/add 引擎错误 → 502"""
    mock_service.add = AsyncMock(
        side_effect=EngineError("Cognee", "add failed", 500)
    )
    response = await client.post(
        "/api/v1/knowledge/add",
        json={"data": "内容", "dataset": "default"},
    )
    assert response.status_code == 502


# ===== POST /knowledge/cognify =====


@pytest.mark.asyncio
async def test_cognify_success(client, mock_service):
    """POST /knowledge/cognify 触发知识图谱构建"""
    mock_service.cognify = AsyncMock(
        return_value=KnowledgeCognifyResponse(
            success=True, pipeline_run_id="run-1", status="pending", message="知识图谱构建已启动"
        )
    )
    response = await client.post(
        "/api/v1/knowledge/cognify",
        json={"run_in_background": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["pipeline_run_id"] == "run-1"


@pytest.mark.asyncio
async def test_cognify_with_datasets(client, mock_service):
    """POST /knowledge/cognify 指定数据集"""
    mock_service.cognify = AsyncMock(
        return_value=KnowledgeCognifyResponse(success=True, status="pending")
    )
    response = await client.post(
        "/api/v1/knowledge/cognify",
        json={"datasets": ["default", "docs"], "run_in_background": False},
    )
    assert response.status_code == 200
    _, kwargs = mock_service.cognify.call_args
    assert kwargs["datasets"] == ["default", "docs"]


# ===== POST /knowledge/search =====


@pytest.mark.asyncio
async def test_search_knowledge_success(client, mock_service):
    """POST /knowledge/search 成功搜索"""
    mock_service.search = AsyncMock(
        return_value=KnowledgeSearchResponse(
            success=True,
            data=[
                KnowledgeSearchResult(id="r1", text="CozyMemory 统一记忆服务", score=0.95)
            ],
            total=1,
        )
    )
    response = await client.post(
        "/api/v1/knowledge/search",
        json={"query": "什么是 CozyMemory"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["data"][0]["score"] == 0.95


@pytest.mark.asyncio
async def test_search_knowledge_with_search_type(client, mock_service):
    """POST /knowledge/search 使用指定 search_type"""
    mock_service.search = AsyncMock(
        return_value=KnowledgeSearchResponse(success=True, data=[], total=0)
    )
    response = await client.post(
        "/api/v1/knowledge/search",
        json={"query": "测试", "search_type": "CHUNKS", "top_k": 5},
    )
    assert response.status_code == 200
    _, kwargs = mock_service.search.call_args
    assert kwargs["search_type"] == "CHUNKS"
    assert kwargs["top_k"] == 5


@pytest.mark.asyncio
async def test_search_knowledge_engine_error(client, mock_service):
    """POST /knowledge/search 引擎错误 → 502"""
    mock_service.search = AsyncMock(
        side_effect=EngineError("Cognee", "search error", 500)
    )
    response = await client.post(
        "/api/v1/knowledge/search",
        json={"query": "test"},
    )
    assert response.status_code == 502


@pytest.mark.asyncio
async def test_search_knowledge_empty_query(client, mock_service):
    """POST /knowledge/search 空 query → 422"""
    response = await client.post(
        "/api/v1/knowledge/search",
        json={"query": ""},
    )
    assert response.status_code == 422


# ===== DELETE /knowledge =====


@pytest.mark.asyncio
async def test_delete_knowledge_success(client, mock_service):
    """DELETE /knowledge 成功删除知识数据"""
    mock_service.delete = AsyncMock(
        return_value=KnowledgeDeleteResponse(success=True, message="已删除")
    )
    response = await client.request(
        "DELETE",
        "/api/v1/knowledge",
        json={"data_id": "doc-1", "dataset_id": "ds-abc"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "已删除"


@pytest.mark.asyncio
async def test_delete_knowledge_forwards_ids(client, mock_service):
    """DELETE /knowledge 正确传递 data_id 和 dataset_id 给服务层"""
    mock_service.delete = AsyncMock(
        return_value=KnowledgeDeleteResponse(success=True, message="已删除")
    )
    await client.request(
        "DELETE",
        "/api/v1/knowledge",
        json={"data_id": "doc-42", "dataset_id": "ds-xyz"},
    )
    _, kwargs = mock_service.delete.call_args
    assert kwargs["data_id"] == "doc-42"
    assert kwargs["dataset_id"] == "ds-xyz"


@pytest.mark.asyncio
async def test_delete_knowledge_missing_fields(client, mock_service):
    """DELETE /knowledge 缺少必填字段 → 422"""
    response = await client.request(
        "DELETE",
        "/api/v1/knowledge",
        json={"data_id": "doc-1"},  # 缺少 dataset_id
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_knowledge_engine_error(client, mock_service):
    """DELETE /knowledge 引擎错误 → 502"""
    mock_service.delete = AsyncMock(
        side_effect=EngineError("Cognee", "delete failed", 500)
    )
    response = await client.request(
        "DELETE",
        "/api/v1/knowledge",
        json={"data_id": "doc-1", "dataset_id": "ds-abc"},
    )
    assert response.status_code == 502
    assert response.json()["error"] == "CogneeError"

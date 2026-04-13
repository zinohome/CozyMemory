"""知识库 API 集成测试"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from cozymemory.api.deps import get_knowledge_service
from cozymemory.app import create_app
from cozymemory.models.knowledge import (
    KnowledgeAddResponse,
    KnowledgeCognifyResponse,
    KnowledgeDatasetListResponse,
    KnowledgeSearchResponse,
)


@pytest.fixture
def mock_knowledge_service():
    """创建 mock 的 KnowledgeService"""
    service = MagicMock()
    service.create_dataset = AsyncMock(
        return_value=KnowledgeDatasetListResponse(success=True, data=[], message="ok")
    )
    service.list_datasets = AsyncMock(
        return_value=KnowledgeDatasetListResponse(success=True, data=[], message="ok")
    )
    service.add = AsyncMock(
        return_value=KnowledgeAddResponse(
            success=True, data_id="d1", dataset_name="test", message="ok"
        )
    )
    service.cognify = AsyncMock(
        return_value=KnowledgeCognifyResponse(
            success=True, pipeline_run_id="run1", status="running", message="ok"
        )
    )
    service.search = AsyncMock(
        return_value=KnowledgeSearchResponse(success=True, data=[], total=0, message="ok")
    )
    return service


@pytest.fixture
def client(mock_knowledge_service):
    app = create_app()
    app.dependency_overrides[get_knowledge_service] = lambda: mock_knowledge_service
    return TestClient(app)


class TestKnowledgeAPI:
    """知识库 API 测试"""

    def test_create_dataset(self, client, mock_knowledge_service):
        """创建数据集应返回 200"""
        response = client.post("/api/v1/knowledge/datasets?name=test_ds")
        assert response.status_code == 200

    def test_list_datasets(self, client, mock_knowledge_service):
        """列出数据集应返回 200"""
        response = client.get("/api/v1/knowledge/datasets")
        assert response.status_code == 200

    def test_add_knowledge(self, client, mock_knowledge_service):
        """添加知识应返回 200"""
        response = client.post(
            "/api/v1/knowledge/add",
            json={
                "data": "some text",
                "dataset": "test",
            },
        )
        assert response.status_code == 200

    def test_cognify(self, client, mock_knowledge_service):
        """触发知识图谱构建应返回 200"""
        response = client.post(
            "/api/v1/knowledge/cognify",
            json={
                "datasets": ["test"],
                "run_in_background": True,
            },
        )
        assert response.status_code == 200

    def test_search_knowledge(self, client, mock_knowledge_service):
        """搜索知识应返回 200"""
        response = client.post(
            "/api/v1/knowledge/search",
            json={
                "query": "test query",
                "dataset": "test",
            },
        )
        assert response.status_code == 200

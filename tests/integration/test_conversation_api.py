"""会话记忆 API 集成测试"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from cozymemory.api.deps import get_conversation_service
from cozymemory.app import create_app
from cozymemory.models.conversation import ConversationMemoryListResponse


@pytest.fixture
def mock_conversation_service():
    """创建 mock 的 ConversationService"""
    service = MagicMock()
    service.add = AsyncMock(
        return_value=ConversationMemoryListResponse(success=True, data=[], message="ok")
    )
    service.search = AsyncMock(
        return_value=ConversationMemoryListResponse(success=True, data=[], total=0, message="ok")
    )
    service.get = AsyncMock(return_value=None)
    service.delete = AsyncMock(
        return_value=ConversationMemoryListResponse(success=True, message="ok")
    )
    service.delete_all = AsyncMock(
        return_value=ConversationMemoryListResponse(success=True, message="ok")
    )
    return service


@pytest.fixture
def client(mock_conversation_service):
    app = create_app()
    app.dependency_overrides[get_conversation_service] = lambda: mock_conversation_service
    return TestClient(app)


class TestConversationAPI:
    """会话记忆 API 测试"""

    def test_add_conversation(self, client, mock_conversation_service):
        """添加对话应返回 200"""
        response = client.post(
            "/api/v1/conversations",
            json={
                "user_id": "user1",
                "messages": [{"role": "user", "content": "hello"}],
                "infer": True,
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_search_conversations(self, client, mock_conversation_service):
        """搜索会话记忆应返回 200"""
        response = client.post(
            "/api/v1/conversations/search",
            json={
                "user_id": "user1",
                "query": "test",
            },
        )
        assert response.status_code == 200

    def test_get_conversation_not_found(self, client, mock_conversation_service):
        """获取不存在的记忆应返回 404"""
        response = client.get("/api/v1/conversations/nonexistent")
        assert response.status_code == 404

    def test_delete_conversation(self, client, mock_conversation_service):
        """删除记忆应返回 200"""
        response = client.delete("/api/v1/conversations/mem123")
        assert response.status_code == 200

    def test_delete_all_conversations(self, client, mock_conversation_service):
        """删除所有记忆应返回 200"""
        response = client.delete("/api/v1/conversations?user_id=user1")
        assert response.status_code == 200

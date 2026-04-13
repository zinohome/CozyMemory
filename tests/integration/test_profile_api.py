"""用户画像 API 集成测试"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from cozymemory.api.deps import get_profile_service
from cozymemory.app import create_app
from cozymemory.models.profile import ProfileInsertResponse


@pytest.fixture
def mock_profile_service():
    """创建 mock 的 ProfileService"""
    service = MagicMock()
    service.insert = AsyncMock(
        return_value=ProfileInsertResponse(
            success=True, user_id="user1", blob_id="blob1", message="ok"
        )
    )
    service.flush = AsyncMock(return_value={"success": True, "message": "ok"})
    service.get_profile = AsyncMock(return_value={"user_id": "user1", "topics": []})
    service.get_context = AsyncMock(
        return_value={"success": True, "user_id": "user1", "context": "prompt"}
    )
    return service


@pytest.fixture
def client(mock_profile_service):
    app = create_app()
    app.dependency_overrides[get_profile_service] = lambda: mock_profile_service
    return TestClient(app)


class TestProfileAPI:
    """用户画像 API 测试"""

    def test_insert_profile(self, client, mock_profile_service):
        """插入画像应返回 200"""
        response = client.post(
            "/api/v1/profiles/insert",
            json={
                "user_id": "user1",
                "messages": [{"role": "user", "content": "I like cats"}],
                "sync": False,
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_flush_profile(self, client, mock_profile_service):
        """刷新画像应返回 200"""
        response = client.post(
            "/api/v1/profiles/flush",
            json={
                "user_id": "user1",
                "sync": False,
            },
        )
        assert response.status_code == 200

    def test_get_profile(self, client, mock_profile_service):
        """获取画像应返回 200"""
        response = client.get("/api/v1/profiles/user1")
        assert response.status_code == 200

    def test_get_context(self, client, mock_profile_service):
        """获取上下文应返回 200"""
        response = client.post(
            "/api/v1/profiles/user1/context",
            json={
                "max_token_size": 500,
            },
        )
        assert response.status_code == 200

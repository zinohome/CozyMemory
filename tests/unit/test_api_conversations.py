"""会话记忆 API 端点测试

测试 POST/GET/DELETE /api/v1/conversations 的请求路由、响应格式和错误处理。
使用 dependency_overrides 注入 mock 服务，不依赖真实引擎后端。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from cozymemory.api.deps import get_conversation_service
from cozymemory.app import create_app
from cozymemory.clients.base import EngineError
from cozymemory.models.conversation import ConversationMemory, ConversationMemoryListResponse


@pytest.fixture
def mock_service():
    return MagicMock()


@pytest.fixture
async def client(mock_service):
    app = create_app()
    app.dependency_overrides[get_conversation_service] = lambda: mock_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ===== POST /conversations =====


@pytest.mark.asyncio
async def test_add_conversation_success(client, mock_service):
    """POST /conversations 成功添加，返回记忆列表"""
    mock_service.add = AsyncMock(
        return_value=ConversationMemoryListResponse(
            success=True,
            data=[
                ConversationMemory(id="m1", user_id="u1", content="用户喜欢咖啡")
            ],
            total=1,
            message="对话已添加，提取出 1 条记忆",
        )
    )
    response = await client.post(
        "/api/v1/conversations",
        json={
            "user_id": "u1",
            "messages": [{"role": "user", "content": "我喜欢咖啡"}],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["total"] == 1
    assert body["data"][0]["content"] == "用户喜欢咖啡"


@pytest.mark.asyncio
async def test_add_conversation_engine_error_returns_502(client, mock_service):
    """POST /conversations 引擎 500 错误 → 返回 502"""
    mock_service.add = AsyncMock(
        side_effect=EngineError("Mem0", "upstream unavailable", 503)
    )
    response = await client.post(
        "/api/v1/conversations",
        json={
            "user_id": "u1",
            "messages": [{"role": "user", "content": "测试"}],
        },
    )
    assert response.status_code == 502
    body = response.json()
    assert body["success"] is False
    assert body["error"] == "Mem0Error"
    assert body["engine"] == "Mem0"


@pytest.mark.asyncio
async def test_add_conversation_engine_error_400(client, mock_service):
    """POST /conversations 引擎 400 错误 → 返回 400"""
    mock_service.add = AsyncMock(
        side_effect=EngineError("Mem0", "bad request", 400)
    )
    response = await client.post(
        "/api/v1/conversations",
        json={
            "user_id": "u1",
            "messages": [{"role": "user", "content": "测试"}],
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_add_conversation_missing_user_id_returns_422(client, mock_service):
    """POST /conversations 缺少 user_id → 422 校验错误"""
    response = await client.post(
        "/api/v1/conversations",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_conversation_empty_messages_returns_422(client, mock_service):
    """POST /conversations 空消息列表 → 422 校验错误"""
    response = await client.post(
        "/api/v1/conversations",
        json={"user_id": "u1", "messages": []},
    )
    assert response.status_code == 422


# ===== POST /conversations/search =====


@pytest.mark.asyncio
async def test_search_conversation_success(client, mock_service):
    """POST /conversations/search 成功搜索"""
    mock_service.search = AsyncMock(
        return_value=ConversationMemoryListResponse(
            success=True,
            data=[ConversationMemory(id="m1", user_id="u1", content="咖啡", score=0.9)],
            total=1,
        )
    )
    response = await client.post(
        "/api/v1/conversations/search",
        json={"user_id": "u1", "query": "咖啡"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"][0]["score"] == 0.9


@pytest.mark.asyncio
async def test_search_conversation_engine_error(client, mock_service):
    """POST /conversations/search 引擎错误 → 502"""
    mock_service.search = AsyncMock(
        side_effect=EngineError("Mem0", "search failed", 500)
    )
    response = await client.post(
        "/api/v1/conversations/search",
        json={"user_id": "u1", "query": "test"},
    )
    assert response.status_code == 502


# ===== GET /conversations/{memory_id} =====


@pytest.mark.asyncio
async def test_get_conversation_found(client, mock_service):
    """GET /conversations/{id} 记忆存在 → 返回记忆"""
    mock_service.get = AsyncMock(
        return_value=ConversationMemory(id="m1", user_id="u1", content="咖啡")
    )
    response = await client.get("/api/v1/conversations/m1")
    assert response.status_code == 200
    assert response.json()["id"] == "m1"


@pytest.mark.asyncio
async def test_get_conversation_not_found(client, mock_service):
    """GET /conversations/{id} 记忆不存在 → 404"""
    mock_service.get = AsyncMock(return_value=None)
    response = await client.get("/api/v1/conversations/nonexistent")
    assert response.status_code == 404
    assert response.json()["error"] == "NotFoundError"


# ===== DELETE /conversations/{memory_id} =====


@pytest.mark.asyncio
async def test_delete_conversation_success(client, mock_service):
    """DELETE /conversations/{id} 成功删除"""
    mock_service.delete = AsyncMock(
        return_value=ConversationMemoryListResponse(success=True, message="记忆已删除")
    )
    response = await client.delete("/api/v1/conversations/m1")
    assert response.status_code == 200
    assert response.json()["success"] is True


# ===== DELETE /conversations (delete all) =====


@pytest.mark.asyncio
async def test_delete_all_conversations_success(client, mock_service):
    """DELETE /conversations?user_id=u1 删除所有记忆"""
    mock_service.delete_all = AsyncMock(
        return_value=ConversationMemoryListResponse(success=True, message="用户所有记忆已删除")
    )
    response = await client.delete("/api/v1/conversations", params={"user_id": "u1"})
    assert response.status_code == 200
    assert response.json()["success"] is True


# ===== GET /conversations (list all) =====


@pytest.mark.asyncio
async def test_list_conversations_success(client, mock_service):
    """GET /conversations?user_id=u1 返回用户所有记忆"""
    mock_service.get_all = AsyncMock(
        return_value=ConversationMemoryListResponse(
            success=True,
            data=[
                ConversationMemory(id="m1", user_id="u1", content="用户喜欢咖啡"),
                ConversationMemory(id="m2", user_id="u1", content="用户住在上海"),
            ],
            total=2,
        )
    )
    response = await client.get("/api/v1/conversations", params={"user_id": "u1"})
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["total"] == 2
    assert len(body["data"]) == 2


@pytest.mark.asyncio
async def test_list_conversations_with_limit(client, mock_service):
    """GET /conversations?user_id=u1&limit=5 传递 limit 给服务层"""
    mock_service.get_all = AsyncMock(
        return_value=ConversationMemoryListResponse(success=True, data=[], total=0)
    )
    response = await client.get(
        "/api/v1/conversations", params={"user_id": "u1", "limit": 5}
    )
    assert response.status_code == 200
    _, kwargs = mock_service.get_all.call_args
    assert kwargs["limit"] == 5


@pytest.mark.asyncio
async def test_list_conversations_engine_error(client, mock_service):
    """GET /conversations 引擎错误 → 502"""
    mock_service.get_all = AsyncMock(
        side_effect=EngineError("Mem0", "list failed", 500)
    )
    response = await client.get("/api/v1/conversations", params={"user_id": "u1"})
    assert response.status_code == 502
    assert response.json()["error"] == "Mem0Error"


@pytest.mark.asyncio
async def test_list_conversations_missing_user_id(client, mock_service):
    """GET /conversations 缺少 user_id → 422"""
    response = await client.get("/api/v1/conversations")
    assert response.status_code == 422

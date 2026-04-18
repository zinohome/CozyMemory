"""统一上下文 API 端点测试

测试 POST /api/v1/context 的路由、响应格式、部分失败格式。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from cozymemory.api.deps import get_context_service
from cozymemory.app import create_app
from cozymemory.models.context import ContextResponse
from cozymemory.models.conversation import ConversationMemory


@pytest.fixture
def mock_service():
    return MagicMock()


@pytest.fixture
async def client(mock_service):
    app = create_app()
    app.dependency_overrides[get_context_service] = lambda: mock_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_context_success(client, mock_service):
    """POST /context 返回合并后的三类记忆"""
    mock_service.get_context = AsyncMock(
        return_value=ContextResponse(
            user_id="u1",
            conversations=[ConversationMemory(id="m1", user_id="u1", content="喜欢篮球")],
            profile_context="用户叫小明",
            knowledge=[],
            errors={},
            latency_ms=42.0,
        )
    )

    response = await client.post(
        "/api/v1/context",
        json={"user_id": "u1", "query": "用户喜欢什么"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["user_id"] == "u1"
    assert len(body["conversations"]) == 1
    assert body["profile_context"] == "用户叫小明"
    assert body["errors"] == {}
    assert body["latency_ms"] == 42.0


@pytest.mark.asyncio
async def test_context_partial_failure_in_response(client, mock_service):
    """引擎部分失败时 errors 字段有值，HTTP 状态码仍为 200"""
    mock_service.get_context = AsyncMock(
        return_value=ContextResponse(
            user_id="u1",
            conversations=[],
            profile_context=None,
            knowledge=[],
            errors={"profile": "[Memobase] timeout"},
            latency_ms=3200.0,
        )
    )

    response = await client.post("/api/v1/context", json={"user_id": "u1"})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "profile" in body["errors"]


@pytest.mark.asyncio
async def test_context_request_validation_empty_user_id(client, mock_service):
    """user_id 为空字符串时返回 422"""
    response = await client.post("/api/v1/context", json={"user_id": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_context_request_validation_empty_query(client, mock_service):
    """query 为空字符串时返回 422（min_length=1）"""
    response = await client.post("/api/v1/context", json={"user_id": "u1", "query": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_context_service_called_with_correct_params(client, mock_service):
    """服务层收到正确的请求参数"""
    mock_service.get_context = AsyncMock(
        return_value=ContextResponse(user_id="u1", errors={}, latency_ms=1.0)
    )

    await client.post(
        "/api/v1/context",
        json={
            "user_id": "u1",
            "query": "运动",
            "include_knowledge": False,
            "conversation_limit": 10,
        },
    )

    call_arg = mock_service.get_context.call_args[0][0]
    assert call_arg.user_id == "u1"
    assert call_arg.query == "运动"
    assert call_arg.include_knowledge is False
    assert call_arg.conversation_limit == 10

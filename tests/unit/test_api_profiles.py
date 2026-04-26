"""用户画像 API 端点测试

测试 /api/v1/profiles/* 的请求路由、响应格式和错误处理。
使用 dependency_overrides 注入 mock 服务。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from cozymemory.api.deps import get_profile_service
from cozymemory.app import create_app
from cozymemory.clients.base import EngineError
from cozymemory.models.profile import (
    ProfileAddItemResponse,
    ProfileContext,
    ProfileContextResponse,
    ProfileDeleteItemResponse,
    ProfileFlushResponse,
    ProfileGetResponse,
    ProfileInsertResponse,
    ProfileTopic,
    UserProfile,
)


@pytest.fixture
def mock_service():
    return MagicMock()


@pytest.fixture
async def client(mock_service):
    app = create_app()
    app.dependency_overrides[get_profile_service] = lambda: mock_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ===== POST /profiles/insert =====


@pytest.mark.asyncio
async def test_insert_profile_success(client, mock_service):
    """POST /profiles/insert 成功插入"""
    mock_service.insert = AsyncMock(
        return_value=ProfileInsertResponse(
            success=True, user_id="uid-abc", blob_id="blob_1", message="对话已插入缓冲区"
        )
    )
    response = await client.post(
        "/api/v1/profiles/insert",
        json={
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "messages": [{"role": "user", "content": "我叫小明"}],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["blob_id"] == "blob_1"
    assert body["user_id"] == "550e8400-e29b-41d4-a716-446655440000"


@pytest.mark.asyncio
async def test_insert_profile_engine_error_returns_502(client, mock_service):
    """POST /profiles/insert 引擎错误 → 502"""
    mock_service.insert = AsyncMock(
        side_effect=EngineError("Memobase", "service unavailable", 503)
    )
    response = await client.post(
        "/api/v1/profiles/insert",
        json={
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "messages": [{"role": "user", "content": "测试"}],
        },
    )
    assert response.status_code == 502
    body = response.json()
    assert body["error"] == "MemobaseError"


@pytest.mark.asyncio
async def test_insert_profile_missing_user_id(client, mock_service):
    """POST /profiles/insert 缺少 user_id → 422"""
    response = await client.post(
        "/api/v1/profiles/insert",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert response.status_code == 422


# ===== POST /profiles/flush =====


@pytest.mark.asyncio
async def test_flush_profile_success(client, mock_service):
    """POST /profiles/flush 成功触发处理"""
    mock_service.flush = AsyncMock(
        return_value=ProfileFlushResponse(success=True, message="处理完成")
    )
    response = await client.post(
        "/api/v1/profiles/flush",
        json={"user_id": "uid-abc"},
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_flush_profile_engine_error(client, mock_service):
    """POST /profiles/flush 引擎错误 → 502"""
    mock_service.flush = AsyncMock(
        side_effect=EngineError("Memobase", "flush failed", 500)
    )
    response = await client.post(
        "/api/v1/profiles/flush",
        json={"user_id": "uid-abc"},
    )
    assert response.status_code == 502


# ===== GET /profiles/{user_id} =====


@pytest.mark.asyncio
async def test_get_profile_success(client, mock_service):
    """GET /profiles/{user_id} 返回用户画像"""
    mock_service.get_profile = AsyncMock(
        return_value=ProfileGetResponse(
            success=True,
            data=UserProfile(
                user_id="uid-abc",
                topics=[
                    ProfileTopic(
                        id="p1", topic="basic_info", sub_topic="name", content="小明"
                    )
                ],
            ),
        )
    )
    response = await client.get("/api/v1/profiles/uid-abc")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["user_id"] == "uid-abc"
    assert body["data"]["topics"][0]["content"] == "小明"


@pytest.mark.asyncio
async def test_get_profile_engine_error(client, mock_service):
    """GET /profiles/{user_id} 引擎错误 → 502"""
    mock_service.get_profile = AsyncMock(
        side_effect=EngineError("Memobase", "not found", 500)
    )
    response = await client.get("/api/v1/profiles/uid-abc")
    assert response.status_code == 502


# ===== POST /profiles/{user_id}/context =====


@pytest.mark.asyncio
async def test_get_context_success(client, mock_service):
    """POST /profiles/{user_id}/context 返回上下文提示词"""
    mock_service.get_context = AsyncMock(
        return_value=ProfileContextResponse(
            success=True,
            data=ProfileContext(user_id="uid-abc", context="# 用户背景\n- 姓名: 小明"),
        )
    )
    response = await client.post(
        "/api/v1/profiles/uid-abc/context",
        json={"max_token_size": 500},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "小明" in body["data"]["context"]


@pytest.mark.asyncio
async def test_get_context_with_chats(client, mock_service):
    """POST /profiles/{user_id}/context 带 chats 参数"""
    mock_service.get_context = AsyncMock(
        return_value=ProfileContextResponse(
            success=True,
            data=ProfileContext(user_id="uid-abc", context="上下文内容"),
        )
    )
    response = await client.post(
        "/api/v1/profiles/uid-abc/context",
        json={
            "max_token_size": 300,
            "chats": [{"role": "user", "content": "你好"}],
        },
    )
    assert response.status_code == 200
    # 验证 chats 参数被传递给服务层
    _, kwargs = mock_service.get_context.call_args
    assert kwargs.get("chats") is not None


@pytest.mark.asyncio
async def test_get_context_engine_error(client, mock_service):
    """POST /profiles/{user_id}/context 引擎错误 → 502"""
    mock_service.get_context = AsyncMock(
        side_effect=EngineError("Memobase", "context error", 500)
    )
    response = await client.post(
        "/api/v1/profiles/uid-abc/context",
        json={},
    )
    assert response.status_code == 502


# ===== POST /profiles/{user_id}/items =====


@pytest.mark.asyncio
async def test_add_profile_item_success(client, mock_service):
    """POST /profiles/{user_id}/items 手动添加画像条目"""
    mock_service.add_profile_item = AsyncMock(
        return_value=ProfileAddItemResponse(
            success=True,
            data=ProfileTopic(id="p99", topic="interest", sub_topic="sport", content="游泳"),
            message="",
        )
    )
    response = await client.post(
        "/api/v1/profiles/uid-abc/items",
        json={"topic": "interest", "sub_topic": "sport", "content": "游泳"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["topic"] == "interest"
    assert body["data"]["content"] == "游泳"


@pytest.mark.asyncio
async def test_add_profile_item_missing_fields(client, mock_service):
    """POST /profiles/{user_id}/items 缺少必填字段 → 422"""
    response = await client.post(
        "/api/v1/profiles/uid-abc/items",
        json={"topic": "interest"},  # 缺少 sub_topic 和 content
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_profile_item_engine_error(client, mock_service):
    """POST /profiles/{user_id}/items 引擎错误 → 502"""
    mock_service.add_profile_item = AsyncMock(
        side_effect=EngineError("Memobase", "add profile failed", 500)
    )
    response = await client.post(
        "/api/v1/profiles/uid-abc/items",
        json={"topic": "interest", "sub_topic": "sport", "content": "游泳"},
    )
    assert response.status_code == 502
    assert response.json()["error"] == "MemobaseError"


# ===== DELETE /profiles/{user_id}/items/{profile_id} =====


@pytest.mark.asyncio
async def test_delete_profile_item_success(client, mock_service):
    """DELETE /profiles/{user_id}/items/{profile_id} 成功删除"""
    mock_service.delete_profile_item = AsyncMock(
        return_value=ProfileDeleteItemResponse(success=True, message="已删除")
    )
    response = await client.delete("/api/v1/profiles/uid-abc/items/p99")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "已删除"


@pytest.mark.asyncio
async def test_delete_profile_item_engine_error(client, mock_service):
    """DELETE /profiles/{user_id}/items/{profile_id} 引擎错误 → 502"""
    mock_service.delete_profile_item = AsyncMock(
        side_effect=EngineError("Memobase", "delete failed", 500)
    )
    response = await client.delete("/api/v1/profiles/uid-abc/items/p99")
    assert response.status_code == 502

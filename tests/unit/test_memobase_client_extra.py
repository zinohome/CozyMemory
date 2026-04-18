"""Memobase 客户端补充测试 - 覆盖用户管理、profile 操作、事件"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from cozymemory.clients.base import EngineError
from cozymemory.clients.memobase import MemobaseClient


@pytest.fixture
def memobase_client():
    return MemobaseClient(api_url="http://localhost:8019")


@pytest.mark.asyncio
async def test_memobase_add_user_with_data(memobase_client):
    """MemobaseClient.add_user 带 user_id 和 data"""
    mock_response = httpx.Response(200, json={"id": "user_123"})
    with patch.object(
        memobase_client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        user_id = await memobase_client.add_user(user_id="user_123", data={"name": "小明"})
        assert user_id == "user_123"


@pytest.mark.asyncio
async def test_memobase_add_user_no_id(memobase_client):
    """MemobaseClient.add_user 不带 user_id"""
    mock_response = httpx.Response(200, json={"data": {"id": "generated_id"}, "errno": 0})
    with patch.object(
        memobase_client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        user_id = await memobase_client.add_user()
        assert user_id == "generated_id"


@pytest.mark.asyncio
async def test_memobase_get_user(memobase_client):
    """MemobaseClient.get_user 获取用户信息"""
    mock_response = httpx.Response(200, json={"id": "user_123", "status": "active"})
    with patch.object(
        memobase_client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        user = await memobase_client.get_user("user_123")
        assert user["id"] == "user_123"


@pytest.mark.asyncio
async def test_memobase_delete_user_success(memobase_client):
    """MemobaseClient.delete_user 成功"""
    mock_response = httpx.Response(200, json={})
    with patch.object(
        memobase_client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        result = await memobase_client.delete_user("user_123")
        assert result is True


@pytest.mark.asyncio
async def test_memobase_delete_user_failure(memobase_client):
    """MemobaseClient.delete_user 5xx 引擎错误向上抛出"""
    with patch.object(
        memobase_client._client,
        "request",
        new_callable=AsyncMock,
        side_effect=EngineError("Memobase", "error", 500),
    ):
        with pytest.raises(EngineError):
            await memobase_client.delete_user("user_123")


@pytest.mark.asyncio
async def test_memobase_delete_user_404_idempotent(memobase_client):
    """MemobaseClient.delete_user 404 返回 True（幂等）"""
    with patch.object(
        memobase_client._client,
        "request",
        new_callable=AsyncMock,
        side_effect=EngineError("Memobase", "not found", 404),
    ):
        result = await memobase_client.delete_user("user_123")
        assert result is True


@pytest.mark.asyncio
async def test_memobase_insert_with_sync(memobase_client):
    """MemobaseClient.insert 同步模式"""
    mock_response = httpx.Response(200, json={"data": {"id": "blob_1"}, "errno": 0})
    with patch.object(
        memobase_client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        blob_id = await memobase_client.insert(
            "user_123", [{"role": "user", "content": "你好"}], sync=True
        )
        assert blob_id == "blob_1"


@pytest.mark.asyncio
async def test_memobase_flush_with_sync(memobase_client):
    """MemobaseClient.flush 同步模式"""
    mock_response = httpx.Response(200, json={})
    with patch.object(
        memobase_client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        await memobase_client.flush("user_123", sync=True)


@pytest.mark.asyncio
async def test_memobase_add_profile(memobase_client):
    """MemobaseClient.add_profile 手动添加画像 — 使用 Memobase 真实响应格式"""
    mock_response = httpx.Response(200, json={"data": {"id": "prof_1"}, "errno": 0})
    with patch.object(
        memobase_client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        result = await memobase_client.add_profile("user_123", "interest", "hobby", "游泳")
        assert result.id == "prof_1"
        assert result.topic == "interest"
        assert result.sub_topic == "hobby"
        assert result.content == "游泳"


@pytest.mark.asyncio
async def test_memobase_add_profile_errno_raises(memobase_client):
    """MemobaseClient.add_profile errno != 0 应抛出 EngineError"""
    mock_response = httpx.Response(200, json={"errno": 1, "errmsg": "duplicate profile"})
    with patch.object(
        memobase_client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        with pytest.raises(EngineError, match="duplicate profile"):
            await memobase_client.add_profile("user_123", "interest", "hobby", "游泳")


@pytest.mark.asyncio
async def test_memobase_delete_profile_success(memobase_client):
    """MemobaseClient.delete_profile 成功"""
    mock_response = httpx.Response(200, json={})
    with patch.object(
        memobase_client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        result = await memobase_client.delete_profile("user_123", "prof_1")
        assert result is True


@pytest.mark.asyncio
async def test_memobase_delete_profile_failure(memobase_client):
    """MemobaseClient.delete_profile 5xx 引擎错误向上抛出"""
    with patch.object(
        memobase_client._client,
        "request",
        new_callable=AsyncMock,
        side_effect=EngineError("Memobase", "error", 500),
    ):
        with pytest.raises(EngineError):
            await memobase_client.delete_profile("user_123", "prof_1")


@pytest.mark.asyncio
async def test_memobase_delete_profile_404_idempotent(memobase_client):
    """MemobaseClient.delete_profile 404 返回 True（幂等）"""
    with patch.object(
        memobase_client._client,
        "request",
        new_callable=AsyncMock,
        side_effect=EngineError("Memobase", "not found", 404),
    ):
        result = await memobase_client.delete_profile("user_123", "prof_1")
        assert result is True


@pytest.mark.asyncio
async def test_memobase_context_no_json_body_on_get(memobase_client):
    """MemobaseClient.context 使用 GET 请求，不发送 JSON body（GET body 会被服务器忽略）"""
    mock_response = httpx.Response(
        200,
        json={"data": {"context": "# Memory\n用户喜欢游泳"}, "errno": 0},
        headers={"content-type": "application/json"},
    )
    mock_req = AsyncMock(return_value=mock_response)
    with patch.object(memobase_client._client, "request", mock_req):
        ctx = await memobase_client.context(
            "user_123", max_token_size=300, chats=[{"role": "user", "content": "你好"}]
        )
        assert ctx.user_id == "user_123"
        assert "游泳" in ctx.context
    # chats 参数当前在 GET 请求中未传递
    call_kwargs = mock_req.call_args[1]
    assert call_kwargs.get("json") is None


@pytest.mark.asyncio
async def test_memobase_events(memobase_client):
    """MemobaseClient.events 获取事件"""
    mock_response = httpx.Response(
        200,
        json=[{"id": "evt_1", "content": "事件1"}, {"id": "evt_2", "content": "事件2"}],
    )
    with patch.object(
        memobase_client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        events = await memobase_client.events("user_123", topk=5)
        assert len(events) == 2


@pytest.mark.asyncio
async def test_memobase_events_dict_response(memobase_client):
    """MemobaseClient.events 返回字典格式"""
    mock_response = httpx.Response(
        200,
        json={"events": [{"id": "evt_1", "content": "事件1"}]},
    )
    with patch.object(
        memobase_client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        events = await memobase_client.events("user_123")
        assert len(events) == 1

"""Memobase 客户端测试"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from cozymemory.clients.memobase import MemobaseClient


def test_memobase_client_init():
    """MemobaseClient 正确初始化"""
    client = MemobaseClient(api_url="http://localhost:8019")
    assert client.engine_name == "Memobase"
    assert client.api_url == "http://localhost:8019"


def test_memobase_client_headers():
    """MemobaseClient 使用 Bearer Token 认证"""
    client = MemobaseClient(api_url="http://localhost:8019", api_key="my-token")
    headers = client._get_headers()
    assert headers["Authorization"] == "Bearer my-token"


@pytest.mark.asyncio
async def test_memobase_health_check():
    """MemobaseClient 健康检查"""
    client = MemobaseClient(api_url="http://localhost:8019")
    mock_response = httpx.Response(200, json={"status": "ok"})
    with patch.object(
        client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        result = await client.health_check()
        assert result is True


@pytest.mark.asyncio
async def test_memobase_add_user():
    """MemobaseClient.add_user 创建用户"""
    client = MemobaseClient(api_url="http://localhost:8019")
    mock_response = httpx.Response(200, json={"id": "user_123"})
    with patch.object(
        client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        user_id = await client.add_user("user_123")
        assert user_id == "user_123"


@pytest.mark.asyncio
async def test_memobase_insert():
    """MemobaseClient.insert 插入对话"""
    client = MemobaseClient(api_url="http://localhost:8019")
    mock_response = httpx.Response(200, json={"data": {"id": "blob_123"}, "errno": 0})
    with patch.object(
        client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        blob_id = await client.insert(
            user_id="user_123", messages=[{"role": "user", "content": "你好"}]
        )
        assert blob_id == "blob_123"


@pytest.mark.asyncio
async def test_memobase_flush():
    """MemobaseClient.flush 触发处理"""
    client = MemobaseClient(api_url="http://localhost:8019")
    mock_response = httpx.Response(200, json={})
    with patch.object(
        client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        await client.flush("user_123", sync=True)


@pytest.mark.asyncio
async def test_memobase_profile():
    """MemobaseClient.profile 获取画像"""
    client = MemobaseClient(api_url="http://localhost:8019")
    mock_response = httpx.Response(
        200,
        json={
            "basic_info": {
                "name": {"id": "p1", "content": "小明", "created_at": None, "updated_at": None}
            }
        },
    )
    with patch.object(
        client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        profile = await client.profile("user_123")
        assert profile.user_id == "user_123"
        assert len(profile.topics) == 1
        assert profile.topics[0].topic == "basic_info"
        assert profile.topics[0].sub_topic == "name"
        assert profile.topics[0].content == "小明"


@pytest.mark.asyncio
async def test_memobase_context():
    """MemobaseClient.context 获取上下文"""
    client = MemobaseClient(api_url="http://localhost:8019")
    mock_response = httpx.Response(
        200, json={"data": {"context": "# Memory\n用户背景..."}, "errno": 0}
    )
    with patch.object(
        client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        ctx = await client.context("user_123")
        assert ctx.user_id == "user_123"
        assert "用户背景" in ctx.context

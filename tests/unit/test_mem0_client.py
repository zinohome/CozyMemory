"""Mem0 客户端测试"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from cozymemory.clients.mem0 import Mem0Client


def test_mem0_client_init():
    """Mem0Client 正确初始化"""
    client = Mem0Client(api_url="http://localhost:8888")
    assert client.engine_name == "Mem0"
    assert client.api_url == "http://localhost:8888"


def test_mem0_client_headers():
    """Mem0Client 使用 X-API-Key 认证"""
    client = Mem0Client(api_url="http://localhost:8888", api_key="test-key")
    headers = client._get_headers()
    assert headers.get("X-API-Key") == "test-key"
    assert "Authorization" not in headers


def test_mem0_client_headers_no_key():
    """Mem0Client 无 API Key"""
    client = Mem0Client(api_url="http://localhost:8888")
    headers = client._get_headers()
    assert "X-API-Key" not in headers


@pytest.mark.asyncio
async def test_mem0_health_check_healthy():
    """Mem0Client 健康检查 - 正常"""
    client = Mem0Client(api_url="http://localhost:8888")
    mock_response = httpx.Response(200, json={"status": "ok"})
    with patch.object(
        client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        result = await client.health_check()
        assert result is True


@pytest.mark.asyncio
async def test_mem0_health_check_unhealthy():
    """Mem0Client 健康检查 - 异常"""
    client = Mem0Client(api_url="http://localhost:8888")
    with patch.object(
        client._client, "request", new_callable=AsyncMock, side_effect=httpx.ConnectError("refused")
    ):
        result = await client.health_check()
        assert result is False


@pytest.mark.asyncio
async def test_mem0_add():
    """Mem0Client.add 添加对话"""
    client = Mem0Client(api_url="http://localhost:8888")
    mock_response = httpx.Response(
        200,
        json=[{"id": "mem_1", "event": "ADD", "data": {"memory": "用户喜欢咖啡"}}],
    )
    with patch.object(
        client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        results = await client.add(
            user_id="user_123", messages=[{"role": "user", "content": "我喜欢咖啡"}]
        )
        assert len(results) == 1
        assert results[0].content == "用户喜欢咖啡"
        assert results[0].user_id == "user_123"


@pytest.mark.asyncio
async def test_mem0_search():
    """Mem0Client.search 语义搜索"""
    client = Mem0Client(api_url="http://localhost:8888")
    mock_response = httpx.Response(
        200,
        json={"results": [{"id": "mem_1", "user_id": "user_123", "memory": "咖啡", "score": 0.92}]},
    )
    with patch.object(
        client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        results = await client.search(user_id="user_123", query="咖啡")
        assert len(results) == 1
        assert results[0].score == 0.92


@pytest.mark.asyncio
async def test_mem0_get():
    """Mem0Client.get 获取单条记忆"""
    client = Mem0Client(api_url="http://localhost:8888")
    mock_response = httpx.Response(
        200, json={"id": "mem_1", "user_id": "user_123", "memory": "用户喜欢咖啡"}
    )
    with patch.object(
        client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        result = await client.get("mem_1")
        assert result is not None
        assert result.id == "mem_1"


@pytest.mark.asyncio
async def test_mem0_get_not_found():
    """Mem0Client.get 404 返回 None"""
    client = Mem0Client(api_url="http://localhost:8888")
    mock_response = httpx.Response(404, text="Not Found")
    with patch.object(
        client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        result = await client.get("nonexistent")
        assert result is None


@pytest.mark.asyncio
async def test_mem0_delete():
    """Mem0Client.delete 删除记忆"""
    client = Mem0Client(api_url="http://localhost:8888")
    mock_response = httpx.Response(200, json={})
    with patch.object(
        client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        result = await client.delete("mem_1")
        assert result is True


@pytest.mark.asyncio
async def test_mem0_delete_all():
    """Mem0Client.delete_all 删除所有记忆"""
    client = Mem0Client(api_url="http://localhost:8888")
    mock_response = httpx.Response(200, json={})
    with patch.object(
        client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        result = await client.delete_all("user_123")
        assert result is True

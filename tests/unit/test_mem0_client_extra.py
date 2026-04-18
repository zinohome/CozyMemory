"""Mem0 客户端补充测试 - 覆盖 get, get_all, update, delete 方法"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from cozymemory.clients.base import EngineError
from cozymemory.clients.mem0 import Mem0Client


@pytest.fixture
def mem0_client():
    return Mem0Client(api_url="http://localhost:8888")


@pytest.mark.asyncio
async def test_mem0_get_all(mem0_client):
    """Mem0Client.get_all 获取所有记忆"""
    mock_response = httpx.Response(
        200,
        json={
            "results": [
                {"id": "mem_1", "user_id": "u1", "memory": "事实1"},
                {"id": "mem_2", "user_id": "u1", "memory": "事实2"},
            ]
        },
    )
    with patch.object(
        mem0_client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        results = await mem0_client.get_all("u1", limit=50)
        assert len(results) == 2
        assert results[0].id == "mem_1"
        assert results[1].content == "事实2"


@pytest.mark.asyncio
async def test_mem0_get_all_empty_list(mem0_client):
    """Mem0Client.get_all 返回空列表"""
    mock_response = httpx.Response(200, json=[])
    with patch.object(
        mem0_client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        results = await mem0_client.get_all("u1")
        assert len(results) == 0


@pytest.mark.asyncio
async def test_mem0_update(mem0_client):
    """Mem0Client.update 更新记忆"""
    mock_response = httpx.Response(
        200,
        json={"id": "mem_1", "user_id": "u1", "memory": "更新后内容"},
    )
    with patch.object(
        mem0_client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        result = await mem0_client.update("mem_1", "更新后内容")
        assert result is not None
        assert result.content == "更新后内容"


@pytest.mark.asyncio
async def test_mem0_delete_failure(mem0_client):
    """Mem0Client.delete 5xx 引擎错误向上抛出"""
    with patch.object(
        mem0_client._client,
        "request",
        new_callable=AsyncMock,
        side_effect=EngineError("Mem0", "error", 500),
    ):
        with pytest.raises(EngineError):
            await mem0_client.delete("mem_1")


@pytest.mark.asyncio
async def test_mem0_delete_404_idempotent(mem0_client):
    """Mem0Client.delete 404 返回 True（幂等）"""
    with patch.object(
        mem0_client._client,
        "request",
        new_callable=AsyncMock,
        side_effect=EngineError("Mem0", "not found", 404),
    ):
        result = await mem0_client.delete("mem_1")
        assert result is True


@pytest.mark.asyncio
async def test_mem0_delete_all_failure(mem0_client):
    """Mem0Client.delete_all 5xx 引擎错误向上抛出"""
    with patch.object(
        mem0_client._client,
        "request",
        new_callable=AsyncMock,
        side_effect=EngineError("Mem0", "error", 500),
    ):
        with pytest.raises(EngineError):
            await mem0_client.delete_all("u1")


@pytest.mark.asyncio
async def test_mem0_delete_all_404_idempotent(mem0_client):
    """Mem0Client.delete_all 404 返回 True（幂等）"""
    with patch.object(
        mem0_client._client,
        "request",
        new_callable=AsyncMock,
        side_effect=EngineError("Mem0", "not found", 404),
    ):
        result = await mem0_client.delete_all("u1")
        assert result is True


@pytest.mark.asyncio
async def test_mem0_add_with_metadata(mem0_client):
    """Mem0Client.add 带元数据"""
    mock_response = httpx.Response(
        200,
        json=[
            {
                "id": "mem_1",
                "event": "ADD",
                "data": {"memory": "事实"},
                "metadata": {"source": "chat"},
            }
        ],
    )
    with patch.object(
        mem0_client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        results = await mem0_client.add(
            user_id="u1",
            messages=[{"role": "user", "content": "你好"}],
            metadata={"source": "chat"},
            infer=True,
        )
        assert len(results) == 1
        assert results[0].metadata == {"source": "chat"}


@pytest.mark.asyncio
async def test_mem0_add_dict_response(mem0_client):
    """Mem0Client.add 返回 results 包装格式"""
    mock_response = httpx.Response(
        200,
        json={"results": [{"id": "mem_1", "memory": "单条记忆"}]},
    )
    with patch.object(
        mem0_client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        results = await mem0_client.add(
            user_id="u1", messages=[{"role": "user", "content": "你好"}]
        )
        assert len(results) == 1
        assert results[0].content == "单条记忆"


@pytest.mark.asyncio
async def test_mem0_search_empty_results(mem0_client):
    """Mem0Client.search 返回空结果"""
    mock_response = httpx.Response(200, json={"results": []})
    with patch.object(
        mem0_client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        results = await mem0_client.search(user_id="u1", query="test")
        assert len(results) == 0


@pytest.mark.asyncio
async def test_mem0_search_dict_response(mem0_client):
    """Mem0Client.search 返回字典列表而非嵌套 results"""
    mock_response = httpx.Response(
        200,
        json=[{"id": "mem_1", "user_id": "u1", "memory": "事实", "score": 0.8}],
    )
    with patch.object(
        mem0_client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        results = await mem0_client.search(user_id="u1", query="test")
        assert len(results) == 1
        assert results[0].score == 0.8


@pytest.mark.asyncio
async def test_mem0_get_engine_error_500(mem0_client):
    """Mem0Client.get 500 错误时抛出异常"""
    with patch.object(
        mem0_client._client,
        "request",
        new_callable=AsyncMock,
        side_effect=EngineError("Mem0", "Server error", 500),
    ):
        with pytest.raises(EngineError):
            await mem0_client.get("mem_1")

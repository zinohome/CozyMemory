"""Cognee 客户端测试"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from cozymemory.clients.cognee import CogneeClient


def test_cognee_client_init():
    """CogneeClient 正确初始化"""
    client = CogneeClient(api_url="http://localhost:8000")
    assert client.engine_name == "Cognee"
    assert client.api_url == "http://localhost:8000"


def test_cognee_client_default_timeout():
    """CogneeClient 默认超时为 300s"""
    client = CogneeClient(api_url="http://localhost:8000")
    assert client.timeout == 300.0


@pytest.mark.asyncio
async def test_cognee_health_check():
    """CogneeClient 健康检查"""
    client = CogneeClient(api_url="http://localhost:8000")
    mock_response = httpx.Response(200, json={"status": "ok"})
    with patch.object(
        client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        result = await client.health_check()
        assert result is True


@pytest.mark.asyncio
async def test_cognee_add():
    """CogneeClient.add 添加数据"""
    client = CogneeClient(api_url="http://localhost:8000")
    mock_response = httpx.Response(200, json={"id": "data_123"})
    with patch.object(
        client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        result = await client.add(data="文本内容", dataset="my-dataset")
        assert "id" in result


@pytest.mark.asyncio
async def test_cognee_cognify():
    """CogneeClient.cognify 构建知识图谱"""
    client = CogneeClient(api_url="http://localhost:8000")
    mock_response = httpx.Response(200, json={"run_id": "pipe_123", "status": "pending"})
    with patch.object(
        client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        result = await client.cognify(datasets=["my-dataset"])
        assert result["status"] == "pending"


@pytest.mark.asyncio
async def test_cognee_search():
    """CogneeClient.search 搜索知识库"""
    client = CogneeClient(api_url="http://localhost:8000")
    mock_response = httpx.Response(
        200, json=[{"id": "node_1", "text": "Cognee 是知识图谱引擎", "score": 0.95}]
    )
    with patch.object(
        client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        results = await client.search(query="Cognee 是什么？")
        assert len(results) == 1
        assert results[0].score == 0.95


@pytest.mark.asyncio
async def test_cognee_create_dataset():
    """CogneeClient.create_dataset 创建数据集"""
    client = CogneeClient(api_url="http://localhost:8000")
    mock_response = httpx.Response(
        200, json={"id": "550e8400-e29b-41d4-a716-446655440000", "name": "my-dataset"}
    )
    with patch.object(
        client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        ds = await client.create_dataset("my-dataset")
        assert ds.name == "my-dataset"


@pytest.mark.asyncio
async def test_cognee_list_datasets():
    """CogneeClient.list_datasets 列出数据集"""
    client = CogneeClient(api_url="http://localhost:8000")
    mock_response = httpx.Response(
        200, json=[{"id": "uuid-1", "name": "ds1"}, {"id": "uuid-2", "name": "ds2"}]
    )
    with patch.object(
        client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        datasets = await client.list_datasets()
        assert len(datasets) == 2

"""Cognee 客户端补充测试 - 覆盖 add, delete, search dict response, health_check failure"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from cozymemory.clients.base import EngineError
from cozymemory.clients.cognee import CogneeClient


@pytest.fixture
def cognee_client():
    return CogneeClient(api_url="http://localhost:8018")


@pytest.mark.asyncio
async def test_cognee_add_with_data(cognee_client):
    """CogneeClient.add 成功"""
    mock_response = httpx.Response(200, json={"id": "data_1"})
    with patch.object(
        cognee_client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        result = await cognee_client.add("content text", dataset="test_ds")
        assert result["id"] == "data_1"


@pytest.mark.asyncio
async def test_cognee_add_failure(cognee_client):
    """CogneeClient.add 失败抛出异常"""
    with patch.object(
        cognee_client._client,
        "request",
        new_callable=AsyncMock,
        side_effect=EngineError("Cognee", "error", 500),
    ):
        with pytest.raises(EngineError):
            await cognee_client.add("content text", dataset="test_ds")


@pytest.mark.asyncio
async def test_cognee_delete_success(cognee_client):
    """CogneeClient.delete 成功"""
    mock_response = httpx.Response(200, json={})
    with patch.object(
        cognee_client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        result = await cognee_client.delete(data_id="data_1", dataset_id="ds_1")
        assert result is True


@pytest.mark.asyncio
async def test_cognee_delete_failure(cognee_client):
    """CogneeClient.delete 5xx 引擎错误向上抛出"""
    with patch.object(
        cognee_client._client,
        "request",
        new_callable=AsyncMock,
        side_effect=EngineError("Cognee", "error", 500),
    ):
        with pytest.raises(EngineError):
            await cognee_client.delete(data_id="data_1", dataset_id="ds_1")


@pytest.mark.asyncio
async def test_cognee_delete_404_idempotent(cognee_client):
    """CogneeClient.delete 404 返回 True（幂等）"""
    with patch.object(
        cognee_client._client,
        "request",
        new_callable=AsyncMock,
        side_effect=EngineError("Cognee", "not found", 404),
    ):
        result = await cognee_client.delete(data_id="data_1", dataset_id="ds_1")
        assert result is True


@pytest.mark.asyncio
async def test_cognee_search_dict_response(cognee_client):
    """CogneeClient.search 返回字典格式响应"""
    mock_response = httpx.Response(
        200,
        json={"id": "n1", "content": "result1"},
    )
    with patch.object(
        cognee_client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        results = await cognee_client.search("test query")
        assert len(results) == 1


@pytest.mark.asyncio
async def test_cognee_search_list_response(cognee_client):
    """CogneeClient.search 返回列表格式响应"""
    mock_response = httpx.Response(
        200,
        json=[{"id": "n1", "content": "r1"}, {"id": "n2", "content": "r2"}],
    )
    with patch.object(
        cognee_client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        results = await cognee_client.search("test query")
        assert len(results) == 2


@pytest.mark.asyncio
async def test_cognee_search_failure(cognee_client):
    """CogneeClient.search 失败抛出异常"""
    with patch.object(
        cognee_client._client,
        "request",
        new_callable=AsyncMock,
        side_effect=EngineError("Cognee", "error", 500),
    ):
        with pytest.raises(EngineError):
            await cognee_client.search("test query")


@pytest.mark.asyncio
async def test_cognee_list_datasets(cognee_client):
    """CogneeClient.list_datasets 列出数据集"""
    mock_response = httpx.Response(
        200,
        json=[
            {"id": 1, "name": "ds1", "createdAt": "2024-01-01"},
            {"id": 2, "name": "ds2", "created_at": "2024-02-01"},
        ],
    )
    with patch.object(
        cognee_client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        datasets = await cognee_client.list_datasets()
        assert len(datasets) == 2
        assert datasets[0].name == "ds1"


@pytest.mark.asyncio
async def test_cognee_create_dataset(cognee_client):
    """CogneeClient.create_dataset 创建数据集"""
    mock_response = httpx.Response(200, json={"id": "3", "name": "new_ds"})
    with patch.object(
        cognee_client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        ds = await cognee_client.create_dataset("new_ds")
        assert ds.name == "new_ds"


@pytest.mark.asyncio
async def test_cognee_cognify(cognee_client):
    """CogneeClient.cognify 成功"""
    mock_response = httpx.Response(200, json={"run_id": "run_1", "status": "pending"})
    with patch.object(
        cognee_client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        result = await cognee_client.cognify(datasets=["ds1"], run_in_background=True)
        assert result["run_id"] == "run_1"


@pytest.mark.asyncio
async def test_cognee_health_check_failure(cognee_client):
    """CogneeClient.health_check 失败"""
    with patch.object(
        cognee_client._client,
        "request",
        new_callable=AsyncMock,
        side_effect=EngineError("Cognee", "error", 500),
    ):
        result = await cognee_client.health_check()
        assert result is False

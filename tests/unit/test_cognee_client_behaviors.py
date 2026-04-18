"""Cognee 客户端行为测试

覆盖 Cognee 特有的、非显而易见的行为：
- add() 使用 multipart/form-data（非 JSON），字段名为 datasetName
- search() 将 dataset 参数包装为 datasets 列表
- search() search_type / top_k 正确透传
- search() KnowledgeSearchResult extra="allow" 保留未知字段
- cognify() datasets 参数有无时的 payload 差异
- list_datasets() 兼容 camelCase createdAt 和 snake_case created_at
- health_check() 使用 /health 路径
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from cozymemory.clients.cognee import CogneeClient


@pytest.fixture
def client():
    return CogneeClient(api_url="http://localhost:8000")


def _mock(response: httpx.Response) -> AsyncMock:
    """快捷构造 AsyncMock，避免 patch.object 行过长"""
    return AsyncMock(return_value=response)


# ===== add() 请求格式 =====


@pytest.mark.asyncio
async def test_add_uses_multipart_not_json(client):
    """add() 必须用 multipart/form-data，而非 JSON body"""
    mock_req = _mock(httpx.Response(200, json={"id": "data_1"}))
    with patch.object(client._client, "request", mock_req):
        await client.add(data="CozyMemory 是统一记忆服务", dataset="docs")

    _, kwargs = mock_req.call_args
    assert kwargs.get("files") is not None, "add() 必须使用 multipart files= 参数"
    assert kwargs.get("json") is None, "add() 不能使用 json= 参数"


@pytest.mark.asyncio
async def test_add_field_name_is_dataset_name(client):
    """add() form data 字段名必须是 datasetName（非 dataset）"""
    mock_req = _mock(httpx.Response(200, json={"id": "data_1"}))
    with patch.object(client._client, "request", mock_req):
        await client.add(data="内容", dataset="my-dataset")

    _, kwargs = mock_req.call_args
    form_data = kwargs.get("data", {})
    assert "datasetName" in form_data, "Cognee API 字段名是 datasetName，不是 dataset"
    assert form_data["datasetName"] == "my-dataset"


@pytest.mark.asyncio
async def test_add_encodes_data_as_bytes(client):
    """add() 将文本编码为 UTF-8 bytes 放入 files"""
    mock_req = _mock(httpx.Response(200, json={"id": "data_1"}))
    with patch.object(client._client, "request", mock_req):
        await client.add(data="中文内容", dataset="ds")

    _, kwargs = mock_req.call_args
    files = kwargs.get("files")
    # files = [("data", ("data.txt", b"...", "text/plain"))]
    assert files is not None
    field_name, (filename, content, mime_type) = files[0]
    assert field_name == "data"
    assert filename == "data.txt"
    assert content == "中文内容".encode()
    assert mime_type == "text/plain"


@pytest.mark.asyncio
async def test_add_removes_content_type_header_for_multipart(client):
    """add() 发送 multipart 时不应设置 Content-Type（让 httpx 自动加 boundary）"""
    mock_req = _mock(httpx.Response(200, json={"id": "data_1"}))
    with patch.object(client._client, "request", mock_req):
        await client.add(data="内容", dataset="ds")

    _, kwargs = mock_req.call_args
    headers = kwargs.get("headers", {})
    # BaseClient._request 在有 files 时会 pop Content-Type
    assert "Content-Type" not in headers


# ===== search() 参数包装 =====


@pytest.mark.asyncio
async def test_search_wraps_dataset_into_datasets_list(client):
    """search(dataset='ds') 应在 payload 中生成 datasets=['ds'] 列表"""
    mock_req = _mock(httpx.Response(200, json=[]))
    with patch.object(client._client, "request", mock_req):
        await client.search(query="测试", dataset="my-dataset")

    _, kwargs = mock_req.call_args
    payload = kwargs.get("json", {})
    assert "datasets" in payload, "提供 dataset 时 payload 必须包含 datasets 键"
    assert payload["datasets"] == ["my-dataset"]


@pytest.mark.asyncio
async def test_search_without_dataset_omits_datasets_key(client):
    """search() 不提供 dataset 时，payload 中不应有 datasets 键"""
    mock_req = _mock(httpx.Response(200, json=[]))
    with patch.object(client._client, "request", mock_req):
        await client.search(query="测试")

    _, kwargs = mock_req.call_args
    payload = kwargs.get("json", {})
    assert "datasets" not in payload, "不提供 dataset 时 payload 不应包含 datasets 键"


@pytest.mark.asyncio
async def test_search_passes_search_type(client):
    """search() 将 search_type 原样传入 payload"""
    mock_req = _mock(httpx.Response(200, json=[]))
    with patch.object(client._client, "request", mock_req):
        await client.search(query="测试", search_type="CHUNKS")

    assert mock_req.call_args[1]["json"]["search_type"] == "CHUNKS"


@pytest.mark.asyncio
async def test_search_passes_top_k(client):
    """search() 将 top_k 传入 payload"""
    mock_req = _mock(httpx.Response(200, json=[]))
    with patch.object(client._client, "request", mock_req):
        await client.search(query="测试", top_k=5)

    assert mock_req.call_args[1]["json"]["top_k"] == 5


@pytest.mark.asyncio
async def test_search_default_search_type_is_graph_completion(client):
    """search() 默认 search_type 为 GRAPH_COMPLETION"""
    mock_req = _mock(httpx.Response(200, json=[]))
    with patch.object(client._client, "request", mock_req):
        await client.search(query="测试")

    assert mock_req.call_args[1]["json"]["search_type"] == "GRAPH_COMPLETION"


# ===== search() 响应解析 =====


@pytest.mark.asyncio
async def test_search_empty_list_returns_empty(client):
    """search() 返回空列表时正常处理"""
    with patch.object(client._client, "request", _mock(httpx.Response(200, json=[]))):
        results = await client.search(query="测试")
    assert results == []


@pytest.mark.asyncio
async def test_search_preserves_extra_fields(client):
    """search() 结果中的未知字段应被保留（KnowledgeSearchResult extra='allow'）"""
    resp = httpx.Response(
        200,
        json=[
            {
                "id": "n1",
                "text": "Cognee 是知识图谱引擎",
                "score": 0.9,
                "node_type": "entity",
                "layer": "summarization",
            }
        ],
    )
    with patch.object(client._client, "request", _mock(resp)):
        results = await client.search(query="测试")

    assert len(results) == 1
    r = results[0]
    assert r.text == "Cognee 是知识图谱引擎"
    # extra="allow" 保证未知字段可通过属性访问
    assert r.node_type == "entity"
    assert r.layer == "summarization"


@pytest.mark.asyncio
async def test_search_with_all_search_types(client):
    """search() 支持所有合法的 Cognee search_type 枚举值"""
    valid_types = ["CHUNKS", "SUMMARIES", "RAG_COMPLETION", "GRAPH_COMPLETION"]
    for search_type in valid_types:
        mock_req = _mock(httpx.Response(200, json=[]))
        with patch.object(client._client, "request", mock_req):
            await client.search(query="测试", search_type=search_type)
        assert mock_req.call_args[1]["json"]["search_type"] == search_type


# ===== cognify() payload 构造 =====


@pytest.mark.asyncio
async def test_cognify_without_datasets_omits_key(client):
    """cognify() 不提供 datasets 时 payload 中不应有 datasets 键"""
    mock_req = _mock(httpx.Response(200, json={"run_id": "r1", "status": "pending"}))
    with patch.object(client._client, "request", mock_req):
        await client.cognify()

    assert "datasets" not in mock_req.call_args[1]["json"]


@pytest.mark.asyncio
async def test_cognify_with_datasets_includes_key(client):
    """cognify(datasets=[...]) 应在 payload 中包含 datasets 键"""
    mock_req = _mock(httpx.Response(200, json={"run_id": "r1", "status": "pending"}))
    with patch.object(client._client, "request", mock_req):
        await client.cognify(datasets=["ds1", "ds2"])

    assert mock_req.call_args[1]["json"]["datasets"] == ["ds1", "ds2"]


@pytest.mark.asyncio
async def test_cognify_run_in_background_false(client):
    """cognify(run_in_background=False) 同步模式正确传递"""
    mock_req = _mock(httpx.Response(200, json={"run_id": "r1", "status": "completed"}))
    with patch.object(client._client, "request", mock_req):
        result = await client.cognify(run_in_background=False)

    assert mock_req.call_args[1]["json"]["run_in_background"] is False
    assert result["status"] == "completed"


# ===== list_datasets() =====


@pytest.mark.asyncio
async def test_list_datasets_empty(client):
    """list_datasets() 空列表正常返回"""
    with patch.object(client._client, "request", _mock(httpx.Response(200, json=[]))):
        datasets = await client.list_datasets()
    assert datasets == []


@pytest.mark.asyncio
async def test_list_datasets_prefers_camel_case_created_at(client):
    """list_datasets() 优先使用 createdAt（camelCase），再降级到 created_at"""
    resp = httpx.Response(
        200,
        json=[
            {"id": "1", "name": "ds1", "createdAt": "2024-01-01T00:00:00"},
            {"id": "2", "name": "ds2", "created_at": "2024-02-01T00:00:00"},
            {"id": "3", "name": "ds3"},
        ],
    )
    with patch.object(client._client, "request", _mock(resp)):
        datasets = await client.list_datasets()

    assert len(datasets) == 3
    assert datasets[0].created_at is not None  # createdAt
    assert datasets[1].created_at is not None  # created_at fallback
    assert datasets[2].created_at is None  # 无时间戳


# ===== health_check() 路径 =====


@pytest.mark.asyncio
async def test_health_check_uses_health_path(client):
    """/health 路径（不带 /api/v1 前缀）"""
    mock_req = _mock(httpx.Response(200, json={"status": "ok"}))
    with patch.object(client._client, "request", mock_req):
        result = await client.health_check()

    assert result is True
    assert mock_req.call_args[1]["url"].endswith("/health")
    assert "/api/v1" not in mock_req.call_args[1]["url"]

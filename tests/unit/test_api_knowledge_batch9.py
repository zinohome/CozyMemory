"""/api/v1/knowledge/add-files、datasets/{id}/data[/{data_id}[/raw]] 测试。

验证 batch 9 新增 4 个 endpoint 的路由、响应格式、错误处理、multipart 解析。
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from cozymemory.api.deps import get_knowledge_service
from cozymemory.app import create_app
from cozymemory.clients.base import EngineError
from cozymemory.models.knowledge import (
    DatasetDataItem,
    DatasetDataListResponse,
    KnowledgeAddResponse,
    KnowledgeDeleteResponse,
)


@pytest.fixture
def mock_service():
    return MagicMock()


@pytest.fixture
async def client(mock_service):
    app = create_app()
    app.dependency_overrides[get_knowledge_service] = lambda: mock_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ───────────────────────── POST /knowledge/add-files ─────────────────────────


@pytest.mark.asyncio
async def test_add_files_single_file(client, mock_service):
    mock_service.add_files = AsyncMock(
        return_value=KnowledgeAddResponse(
            success=True, dataset="ds", message="已上传 1 个文件"
        )
    )
    response = await client.post(
        "/api/v1/knowledge/add-files",
        data={"dataset": "ds"},
        files={"files": ("hello.txt", b"hi there", "text/plain")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["dataset"] == "ds"
    # service 收到的 payload 形状正确
    mock_service.add_files.assert_awaited_once()
    kwargs = mock_service.add_files.await_args.kwargs
    files = kwargs["files"]
    assert kwargs["dataset"] == "ds"
    assert len(files) == 1
    name, content, ct = files[0]
    assert name == "hello.txt"
    assert content == b"hi there"
    assert ct == "text/plain"


@pytest.mark.asyncio
async def test_add_files_multiple_files(client, mock_service):
    mock_service.add_files = AsyncMock(
        return_value=KnowledgeAddResponse(success=True, dataset="ds")
    )
    response = await client.post(
        "/api/v1/knowledge/add-files",
        data={"dataset": "ds"},
        files=[
            ("files", ("a.txt", b"A", "text/plain")),
            ("files", ("b.md", b"B", "text/markdown")),
        ],
    )
    assert response.status_code == 200
    files = mock_service.add_files.await_args.kwargs["files"]
    assert len(files) == 2


@pytest.mark.asyncio
async def test_add_files_empty_file_skipped(client, mock_service):
    """所有文件为空时返回 400"""
    mock_service.add_files = AsyncMock()
    response = await client.post(
        "/api/v1/knowledge/add-files",
        data={"dataset": "ds"},
        files={"files": ("empty.txt", b"", "text/plain")},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert "ValidationError" in body["error"]
    mock_service.add_files.assert_not_called()


@pytest.mark.asyncio
async def test_add_files_mixed_empty_and_real(client, mock_service):
    """部分为空部分有内容：空的被过滤，有内容的继续"""
    mock_service.add_files = AsyncMock(
        return_value=KnowledgeAddResponse(success=True, dataset="ds")
    )
    response = await client.post(
        "/api/v1/knowledge/add-files",
        data={"dataset": "ds"},
        files=[
            ("files", ("empty.txt", b"", "text/plain")),
            ("files", ("real.txt", b"hello", "text/plain")),
        ],
    )
    assert response.status_code == 200
    files = mock_service.add_files.await_args.kwargs["files"]
    assert len(files) == 1
    assert files[0][0] == "real.txt"


@pytest.mark.asyncio
async def test_add_files_engine_error_502(client, mock_service):
    mock_service.add_files = AsyncMock(
        side_effect=EngineError("Cognee", "upstream down", 503)
    )
    response = await client.post(
        "/api/v1/knowledge/add-files",
        data={"dataset": "ds"},
        files={"files": ("a.txt", b"x", "text/plain")},
    )
    assert response.status_code == 502
    assert response.json()["success"] is False


# ───────────── GET /knowledge/datasets/{id}/data ─────────────


@pytest.mark.asyncio
async def test_list_dataset_data_success(client, mock_service):
    mock_service.list_dataset_data = AsyncMock(
        return_value=DatasetDataListResponse(
            success=True,
            dataset_id="ds-1",
            data=[
                DatasetDataItem(
                    id="d1",
                    name="doc1",
                    mime_type="text/plain",
                    extension="txt",
                    created_at=datetime(2026, 4, 22, tzinfo=UTC),
                ),
                DatasetDataItem(id="d2", name="doc2"),
            ],
            total=2,
        )
    )
    response = await client.get("/api/v1/knowledge/datasets/ds-1/data")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["dataset_id"] == "ds-1"
    assert body["total"] == 2
    assert body["data"][0]["name"] == "doc1"


@pytest.mark.asyncio
async def test_list_dataset_data_empty(client, mock_service):
    mock_service.list_dataset_data = AsyncMock(
        return_value=DatasetDataListResponse(
            success=True, dataset_id="ds-empty", data=[], total=0
        )
    )
    response = await client.get("/api/v1/knowledge/datasets/ds-empty/data")
    assert response.status_code == 200
    assert response.json()["total"] == 0


@pytest.mark.asyncio
async def test_list_dataset_data_engine_error(client, mock_service):
    mock_service.list_dataset_data = AsyncMock(
        side_effect=EngineError("Cognee", "boom", 502)
    )
    response = await client.get("/api/v1/knowledge/datasets/ds-1/data")
    assert response.status_code == 502


# ───── GET /knowledge/datasets/{id}/data/{data_id}/raw ─────


@pytest.mark.asyncio
async def test_get_raw_data_text(client, mock_service):
    mock_service.get_raw_data = AsyncMock(
        return_value=(b"hello content", "text/plain", "doc.txt")
    )
    response = await client.get("/api/v1/knowledge/datasets/ds-1/data/d1/raw")
    assert response.status_code == 200
    assert response.content == b"hello content"
    assert response.headers["content-type"].startswith("text/plain")
    # inline filename 头让浏览器尝试嵌入显示
    assert "doc.txt" in response.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_get_raw_data_without_filename(client, mock_service):
    """service 返回空 filename 时不应该设置 content-disposition"""
    mock_service.get_raw_data = AsyncMock(
        return_value=(b"xx", "application/octet-stream", "")
    )
    response = await client.get("/api/v1/knowledge/datasets/ds-1/data/d1/raw")
    assert response.status_code == 200
    assert response.content == b"xx"
    # 没有 filename 时不带 content-disposition
    assert "content-disposition" not in response.headers


@pytest.mark.asyncio
async def test_get_raw_data_404(client, mock_service):
    mock_service.get_raw_data = AsyncMock(
        side_effect=EngineError("Cognee", "not found", 404)
    )
    response = await client.get("/api/v1/knowledge/datasets/ds-1/data/missing/raw")
    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "NotFoundError"


@pytest.mark.asyncio
async def test_get_raw_data_5xx(client, mock_service):
    mock_service.get_raw_data = AsyncMock(
        side_effect=EngineError("Cognee", "upstream", 502)
    )
    response = await client.get("/api/v1/knowledge/datasets/ds-1/data/d1/raw")
    assert response.status_code == 502


# ───── DELETE /knowledge/datasets/{id}/data/{data_id} ─────


@pytest.mark.asyncio
async def test_delete_dataset_data_success(client, mock_service):
    mock_service.delete_dataset_data = AsyncMock(
        return_value=KnowledgeDeleteResponse(success=True, message="已删除")
    )
    response = await client.delete("/api/v1/knowledge/datasets/ds-1/data/d1")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    mock_service.delete_dataset_data.assert_awaited_once_with(
        dataset_id="ds-1", data_id="d1"
    )


@pytest.mark.asyncio
async def test_delete_dataset_data_engine_error(client, mock_service):
    mock_service.delete_dataset_data = AsyncMock(
        side_effect=EngineError("Cognee", "boom", 502)
    )
    response = await client.delete("/api/v1/knowledge/datasets/ds-1/data/d1")
    assert response.status_code == 502

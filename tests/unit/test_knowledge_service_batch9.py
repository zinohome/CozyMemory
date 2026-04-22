"""KnowledgeService batch 9 薄包装测试 — add_files / list_dataset_data /
get_raw_data / delete_dataset_data。"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from cozymemory.clients.base import EngineError
from cozymemory.services.knowledge import KnowledgeService


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def service(mock_client):
    return KnowledgeService(mock_client)


@pytest.mark.asyncio
async def test_add_files_forwards_to_client(service, mock_client):
    mock_client.add_files = AsyncMock(return_value={"id": "up-1"})
    resp = await service.add_files(
        files=[("a.txt", b"A", "text/plain")], dataset="ds"
    )
    assert resp.success is True
    assert resp.dataset_name == "ds"
    assert "1 个文件" in resp.message
    mock_client.add_files.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_dataset_data_maps_fields(service, mock_client):
    mock_client.list_dataset_data = AsyncMock(
        return_value=[
            {
                "id": "d1",
                "name": "doc",
                "mime_type": "text/plain",
                "extension": "txt",
                "raw_data_location": "file:///tmp/x",
                "createdAt": "2026-04-22T00:00:00Z",
                "updatedAt": "2026-04-22T01:00:00Z",
            },
            # Cognee 原始字段有时用 camelCase；服务层应兼容
            {
                "id": "d2",
                "name": "doc2",
                "mimeType": "application/pdf",
                "fileExtension": "pdf",
                "rawDataLocation": "file:///tmp/y",
            },
        ]
    )
    resp = await service.list_dataset_data(dataset_id="ds-1")
    assert resp.success is True
    assert resp.dataset_id == "ds-1"
    assert resp.total == 2
    # snake_case 直接映射
    assert resp.data[0].mime_type == "text/plain"
    assert resp.data[0].extension == "txt"
    # camelCase 也能映射
    assert resp.data[1].mime_type == "application/pdf"
    assert resp.data[1].extension == "pdf"
    assert resp.data[1].raw_data_location == "file:///tmp/y"


@pytest.mark.asyncio
async def test_get_raw_data_forwards(service, mock_client):
    mock_client.get_raw_data = AsyncMock(
        return_value=(b"bytes", "text/plain", "x.txt")
    )
    result = await service.get_raw_data(dataset_id="ds", data_id="d1")
    assert result == (b"bytes", "text/plain", "x.txt")
    mock_client.get_raw_data.assert_awaited_once_with(
        dataset_id="ds", data_id="d1"
    )


@pytest.mark.asyncio
async def test_delete_dataset_data_success(service, mock_client):
    mock_client.delete_dataset_data = AsyncMock(return_value=True)
    resp = await service.delete_dataset_data(dataset_id="ds", data_id="d1")
    assert resp.success is True
    assert "已删除" in resp.message


@pytest.mark.asyncio
async def test_delete_dataset_data_engine_error_propagates(
    service, mock_client
):
    mock_client.delete_dataset_data = AsyncMock(
        side_effect=EngineError("Cognee", "boom", 502)
    )
    with pytest.raises(EngineError):
        await service.delete_dataset_data(dataset_id="ds", data_id="d1")

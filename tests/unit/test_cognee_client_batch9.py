"""Cognee 客户端 batch 9 新方法测试 — 文件上传、列文档、读原文、删文档。"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from cozymemory.clients.base import EngineError
from cozymemory.clients.cognee import CogneeClient


@pytest.fixture
def cognee():
    return CogneeClient(api_url="http://localhost:8018")


# ───────────────────────── add_files ─────────────────────────


@pytest.mark.asyncio
async def test_add_files_single(cognee):
    mock_response = httpx.Response(200, json={"id": "up_1"})
    with patch.object(
        cognee._client, "request", new_callable=AsyncMock, return_value=mock_response
    ) as m:
        result = await cognee.add_files(
            files=[("hello.txt", b"hi", "text/plain")], dataset="ds"
        )
        assert result["id"] == "up_1"
        # 验证 multipart 负载
        kwargs = m.call_args.kwargs
        files = kwargs["files"]
        assert len(files) == 1
        assert files[0][0] == "data"
        assert files[0][1][0] == "hello.txt"
        assert files[0][1][1] == b"hi"
        assert files[0][1][2] == "text/plain"
        assert kwargs["data"] == {"datasetName": "ds"}


@pytest.mark.asyncio
async def test_add_files_multiple(cognee):
    mock_response = httpx.Response(200, json={"id": "up_many"})
    with patch.object(
        cognee._client, "request", new_callable=AsyncMock, return_value=mock_response
    ) as m:
        await cognee.add_files(
            files=[
                ("a.txt", b"A", "text/plain"),
                ("b.pdf", b"%PDF", "application/pdf"),
            ],
            dataset="ds",
        )
        files = m.call_args.kwargs["files"]
        assert len(files) == 2
        assert [f[1][0] for f in files] == ["a.txt", "b.pdf"]


@pytest.mark.asyncio
async def test_add_files_engine_error(cognee):
    with patch.object(
        cognee._client,
        "request",
        new_callable=AsyncMock,
        side_effect=EngineError("Cognee", "boom", 502),
    ):
        with pytest.raises(EngineError):
            await cognee.add_files(
                files=[("x.txt", b"x", "text/plain")], dataset="ds"
            )


# ───────────────────────── list_dataset_data ─────────────────────────


@pytest.mark.asyncio
async def test_list_dataset_data_returns_list(cognee):
    mock_response = httpx.Response(
        200,
        json=[
            {"id": "d1", "name": "doc1"},
            {"id": "d2", "name": "doc2"},
        ],
    )
    with patch.object(
        cognee._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        items = await cognee.list_dataset_data("ds-1")
        assert len(items) == 2
        assert items[0]["name"] == "doc1"


@pytest.mark.asyncio
async def test_list_dataset_data_non_list_returns_empty(cognee):
    """Cognee 偶发返回非 list（错误响应等）时应该优雅返回空列表"""
    mock_response = httpx.Response(200, json={"not": "a list"})
    with patch.object(
        cognee._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        assert await cognee.list_dataset_data("ds-1") == []


# ───────────────────────── get_raw_data ─────────────────────────


@pytest.mark.asyncio
async def test_get_raw_data_parses_filename_from_header(cognee):
    resp = httpx.Response(
        200,
        content=b"hello world",
        headers={
            "content-type": "text/plain; charset=utf-8",
            "content-disposition": 'attachment; filename="doc.txt"',
        },
    )
    with patch.object(
        cognee._client, "request", new_callable=AsyncMock, return_value=resp
    ):
        content, ct, name = await cognee.get_raw_data("ds", "d1")
        assert content == b"hello world"
        assert ct.startswith("text/plain")
        assert name == "doc.txt"


@pytest.mark.asyncio
async def test_get_raw_data_missing_headers_defaults(cognee):
    """没有 content-type / content-disposition 时使用默认值"""
    resp = httpx.Response(200, content=b"raw-bytes")
    with patch.object(
        cognee._client, "request", new_callable=AsyncMock, return_value=resp
    ):
        content, ct, name = await cognee.get_raw_data("ds", "d1")
        assert content == b"raw-bytes"
        # httpx 默认的 content-type 可能为空或 application/octet-stream
        assert name == ""


@pytest.mark.asyncio
async def test_get_raw_data_filename_without_quotes(cognee):
    """某些服务返回不带引号的 filename"""
    resp = httpx.Response(
        200,
        content=b"x",
        headers={"content-disposition": "inline; filename=no-quotes.md"},
    )
    with patch.object(
        cognee._client, "request", new_callable=AsyncMock, return_value=resp
    ):
        _, _, name = await cognee.get_raw_data("ds", "d1")
        assert name == "no-quotes.md"


# ───────────────────────── delete_dataset_data ─────────────────────────


@pytest.mark.asyncio
async def test_delete_dataset_data_success(cognee):
    resp = httpx.Response(200, json={"ok": True})
    with patch.object(
        cognee._client, "request", new_callable=AsyncMock, return_value=resp
    ):
        assert await cognee.delete_dataset_data("ds", "d1") is True


@pytest.mark.asyncio
async def test_delete_dataset_data_404_is_idempotent(cognee):
    """Cognee 返回 404 代表已经不存在，视为删除成功"""
    with patch.object(
        cognee._client,
        "request",
        new_callable=AsyncMock,
        side_effect=EngineError("Cognee", "not found", 404),
    ):
        assert await cognee.delete_dataset_data("ds", "missing") is True


@pytest.mark.asyncio
async def test_delete_dataset_data_5xx_raises(cognee):
    with patch.object(
        cognee._client,
        "request",
        new_callable=AsyncMock,
        side_effect=EngineError("Cognee", "boom", 502),
    ):
        with pytest.raises(EngineError):
            await cognee.delete_dataset_data("ds", "d1")

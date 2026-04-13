"""API 路由 EngineError 错误处理测试"""

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from cozymemory.api.deps import (
    get_conversation_service,
    get_knowledge_service,
    get_profile_service,
)
from cozymemory.app import create_app
from cozymemory.clients.base import EngineError
from cozymemory.services.conversation import ConversationService
from cozymemory.services.knowledge import KnowledgeService
from cozymemory.services.profile import ProfileService


def _make_app_with_override(dep, mock_service):
    """创建带依赖覆盖的测试 app"""
    app = create_app()
    app.dependency_overrides[dep] = lambda: mock_service
    return app


# ===== Conversation EngineError =====


@pytest.mark.asyncio
async def test_conversation_add_502():
    """POST /conversations - EngineError 500+ 返回 502"""
    mock_svc = AsyncMock(spec=ConversationService)
    mock_svc.add = AsyncMock(side_effect=EngineError("Mem0", "Server error", 500))
    app = _make_app_with_override(get_conversation_service, mock_svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/conversations",
            json={"user_id": "u1", "messages": [{"role": "user", "content": "hi"}]},
        )
        assert resp.status_code == 502
        assert "Mem0" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_conversation_add_400():
    """POST /conversations - EngineError 4xx 返回 400"""
    mock_svc = AsyncMock(spec=ConversationService)
    mock_svc.add = AsyncMock(side_effect=EngineError("Mem0", "Bad request", 400))
    app = _make_app_with_override(get_conversation_service, mock_svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/conversations",
            json={"user_id": "u1", "messages": [{"role": "user", "content": "hi"}]},
        )
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_conversation_search_502():
    """POST /conversations/search - EngineError 500+ 返回 502"""
    mock_svc = AsyncMock(spec=ConversationService)
    mock_svc.search = AsyncMock(side_effect=EngineError("Mem0", "Timeout", 504))
    app = _make_app_with_override(get_conversation_service, mock_svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/conversations/search",
            json={"user_id": "u1", "query": "test"},
        )
        assert resp.status_code == 502


@pytest.mark.asyncio
async def test_conversation_get_502():
    """GET /conversations/{id} - EngineError 500+ 返回 502"""
    mock_svc = AsyncMock(spec=ConversationService)
    mock_svc.get = AsyncMock(side_effect=EngineError("Mem0", "Error", 500))
    app = _make_app_with_override(get_conversation_service, mock_svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/conversations/mem_1")
        assert resp.status_code == 502


@pytest.mark.asyncio
async def test_conversation_delete_502():
    """DELETE /conversations/{id} - EngineError 500+ 返回 502"""
    mock_svc = AsyncMock(spec=ConversationService)
    mock_svc.delete = AsyncMock(side_effect=EngineError("Mem0", "Error", 500))
    app = _make_app_with_override(get_conversation_service, mock_svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete("/api/v1/conversations/mem_1")
        assert resp.status_code == 502


@pytest.mark.asyncio
async def test_conversation_delete_all_502():
    """DELETE /conversations?user_id=u1 - EngineError 500+ 返回 502"""
    mock_svc = AsyncMock(spec=ConversationService)
    mock_svc.delete_all = AsyncMock(side_effect=EngineError("Mem0", "Error", 500))
    app = _make_app_with_override(get_conversation_service, mock_svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete("/api/v1/conversations?user_id=u1")
        assert resp.status_code == 502


# ===== Profile EngineError =====


@pytest.mark.asyncio
async def test_profile_insert_502():
    """POST /profiles/insert - EngineError 500+ 返回 502"""
    mock_svc = AsyncMock(spec=ProfileService)
    mock_svc.insert = AsyncMock(side_effect=EngineError("Memobase", "Error", 500))
    app = _make_app_with_override(get_profile_service, mock_svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/profiles/insert",
            json={"user_id": "u1", "messages": [{"role": "user", "content": "hi"}]},
        )
        assert resp.status_code == 502
        assert "Memobase" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_profile_flush_502():
    """POST /profiles/flush - EngineError 500+ 返回 502"""
    mock_svc = AsyncMock(spec=ProfileService)
    mock_svc.flush = AsyncMock(side_effect=EngineError("Memobase", "Error", 500))
    app = _make_app_with_override(get_profile_service, mock_svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/profiles/flush",
            json={"user_id": "u1"},
        )
        assert resp.status_code == 502


@pytest.mark.asyncio
async def test_profile_get_502():
    """GET /profiles/{user_id} - EngineError 500+ 返回 502"""
    mock_svc = AsyncMock(spec=ProfileService)
    mock_svc.get_profile = AsyncMock(side_effect=EngineError("Memobase", "Error", 500))
    app = _make_app_with_override(get_profile_service, mock_svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/profiles/u1")
        assert resp.status_code == 502


@pytest.mark.asyncio
async def test_profile_context_502():
    """POST /profiles/{user_id}/context - EngineError 500+ 返回 502"""
    mock_svc = AsyncMock(spec=ProfileService)
    mock_svc.get_context = AsyncMock(side_effect=EngineError("Memobase", "Error", 500))
    app = _make_app_with_override(get_profile_service, mock_svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/profiles/u1/context",
            json={"max_token_size": 300},
        )
        assert resp.status_code == 502


@pytest.mark.asyncio
async def test_profile_insert_400():
    """POST /profiles/insert - EngineError 4xx 返回 400"""
    mock_svc = AsyncMock(spec=ProfileService)
    mock_svc.insert = AsyncMock(side_effect=EngineError("Memobase", "Bad request", 400))
    app = _make_app_with_override(get_profile_service, mock_svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/profiles/insert",
            json={"user_id": "u1", "messages": [{"role": "user", "content": "hi"}]},
        )
        assert resp.status_code == 400


# ===== Knowledge EngineError =====


@pytest.mark.asyncio
async def test_knowledge_add_502():
    """POST /knowledge/add - EngineError 500+ 返回 502"""
    mock_svc = AsyncMock(spec=KnowledgeService)
    mock_svc.add = AsyncMock(side_effect=EngineError("Cognee", "Error", 500))
    app = _make_app_with_override(get_knowledge_service, mock_svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/knowledge/add",
            json={"data": "test content", "dataset": "test_ds"},
        )
        assert resp.status_code == 502
        assert "Cognee" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_knowledge_cognify_502():
    """POST /knowledge/cognify - EngineError 500+ 返回 502"""
    mock_svc = AsyncMock(spec=KnowledgeService)
    mock_svc.cognify = AsyncMock(side_effect=EngineError("Cognee", "Error", 500))
    app = _make_app_with_override(get_knowledge_service, mock_svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/knowledge/cognify",
            json={"datasets": ["ds1"]},
        )
        assert resp.status_code == 502


@pytest.mark.asyncio
async def test_knowledge_search_502():
    """POST /knowledge/search - EngineError 500+ 返回 502"""
    mock_svc = AsyncMock(spec=KnowledgeService)
    mock_svc.search = AsyncMock(side_effect=EngineError("Cognee", "Error", 500))
    app = _make_app_with_override(get_knowledge_service, mock_svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/knowledge/search",
            json={"query": "test query"},
        )
        assert resp.status_code == 502


@pytest.mark.asyncio
async def test_knowledge_create_dataset_502():
    """POST /knowledge/datasets?name=ds1 - EngineError 500+ 返回 502"""
    mock_svc = AsyncMock(spec=KnowledgeService)
    mock_svc.create_dataset = AsyncMock(side_effect=EngineError("Cognee", "Error", 500))
    app = _make_app_with_override(get_knowledge_service, mock_svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/knowledge/datasets?name=ds1")
        assert resp.status_code == 502


@pytest.mark.asyncio
async def test_knowledge_list_datasets_502():
    """GET /knowledge/datasets - EngineError 500+ 返回 502"""
    mock_svc = AsyncMock(spec=KnowledgeService)
    mock_svc.list_datasets = AsyncMock(side_effect=EngineError("Cognee", "Error", 500))
    app = _make_app_with_override(get_knowledge_service, mock_svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/knowledge/datasets")
        assert resp.status_code == 502


@pytest.mark.asyncio
async def test_knowledge_add_400():
    """POST /knowledge/add - EngineError 4xx 返回 400"""
    mock_svc = AsyncMock(spec=KnowledgeService)
    mock_svc.add = AsyncMock(side_effect=EngineError("Cognee", "Bad request", 400))
    app = _make_app_with_override(get_knowledge_service, mock_svc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/knowledge/add",
            json={"data": "test content", "dataset": "test_ds"},
        )
        assert resp.status_code == 400

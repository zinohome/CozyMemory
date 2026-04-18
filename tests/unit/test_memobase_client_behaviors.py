"""Memobase 客户端新行为测试

覆盖客户端重写后新增的核心行为：
- insert() 的 FK 自动重试逻辑
- add_user() 的 UniqueViolation 静默忽略
- profile() 新响应格式解析
- context() 新响应格式解析
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from cozymemory.clients.base import EngineError
from cozymemory.clients.memobase import MemobaseClient


@pytest.fixture
def client():
    return MemobaseClient(api_url="http://localhost:8019", api_key="secret")


# ===== insert() FK 自动重试 =====


@pytest.mark.asyncio
async def test_insert_auto_creates_user_on_fk_violation(client):
    """insert() 检测到 ForeignKeyViolation 时自动调用 add_user() 并重试"""
    fk_response = httpx.Response(
        200, json={"errno": 500, "errmsg": "ForeignKeyViolation: user not found"}
    )
    ok_response = httpx.Response(200, json={"data": {"id": "blob_1"}, "errno": 0})
    add_user_response = httpx.Response(200, json={"data": {"id": "uid-123"}, "errno": 0})

    request_mock = AsyncMock(side_effect=[fk_response, add_user_response, ok_response])
    with patch.object(client._client, "request", request_mock):
        blob_id = await client.insert(
            user_id="uid-123", messages=[{"role": "user", "content": "你好"}]
        )
        assert blob_id == "blob_1"
        # 第1次: insert 请求, 第2次: add_user 请求, 第3次: insert 重试
        assert request_mock.call_count == 3


@pytest.mark.asyncio
async def test_insert_no_retry_on_success(client):
    """insert() 首次成功时不触发重试"""
    ok_response = httpx.Response(200, json={"data": {"id": "blob_ok"}, "errno": 0})
    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=ok_response):
        blob_id = await client.insert("uid-abc", [{"role": "user", "content": "hi"}])
        assert blob_id == "blob_ok"


@pytest.mark.asyncio
async def test_insert_raises_on_other_errno(client):
    """insert() 非 FK 错误时抛出 EngineError"""
    error_response = httpx.Response(
        200, json={"errno": 500, "errmsg": "SomeOtherDatabaseError occurred"}
    )
    mock = AsyncMock(return_value=error_response)
    with patch.object(client._client, "request", mock):
        with pytest.raises(EngineError):
            await client.insert("uid-abc", [{"role": "user", "content": "hi"}])


# ===== add_user() UniqueViolation 静默 =====


@pytest.mark.asyncio
async def test_add_user_ignores_unique_violation(client):
    """add_user() 收到 UniqueViolation 时静默返回，而不是抛出异常"""
    response = httpx.Response(
        200, json={"errno": 500, "errmsg": "UniqueViolation: user already exists", "data": None}
    )
    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=response):
        uid = await client.add_user(user_id="existing-user")
        assert uid == "existing-user"


@pytest.mark.asyncio
async def test_add_user_raises_on_real_error(client):
    """add_user() 非 UniqueViolation 的 errno 应该抛出 EngineError"""
    response = httpx.Response(
        200, json={"errno": 500, "errmsg": "ConnectionError: database unavailable"}
    )
    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=response):
        with pytest.raises(EngineError):
            await client.add_user(user_id="new-user")


# ===== profile() 新格式解析 =====


@pytest.mark.asyncio
async def test_profile_new_format(client):
    """profile() 正确解析新格式 {"data": {"profiles": [...]}, "errno": 0}"""
    response = httpx.Response(
        200,
        json={
            "data": {
                "profiles": [
                    {
                        "id": "p1",
                        "content": "小明",
                        "attributes": {"topic": "basic_info", "sub_topic": "name"},
                        "created_at": "2024-01-01",
                        "updated_at": "2024-01-02",
                    },
                    {
                        "id": "p2",
                        "content": "游泳",
                        "attributes": {"topic": "interest", "sub_topic": "hobby"},
                        "created_at": None,
                        "updated_at": None,
                    },
                ]
            },
            "errno": 0,
        },
    )
    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=response):
        profile = await client.profile("uid-abc")
        assert profile.user_id == "uid-abc"
        assert len(profile.topics) == 2
        assert profile.topics[0].id == "p1"
        assert profile.topics[0].topic == "basic_info"
        assert profile.topics[0].sub_topic == "name"
        assert profile.topics[0].content == "小明"
        assert profile.topics[1].topic == "interest"


@pytest.mark.asyncio
async def test_profile_old_format_fallback(client):
    """profile() 兼容旧格式 {topic: {sub_topic: {id, content}}}"""
    response = httpx.Response(
        200,
        json={
            "basic_info": {
                "name": {"id": "p1", "content": "小红", "created_at": None, "updated_at": None}
            }
        },
    )
    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=response):
        profile = await client.profile("uid-xyz")
        assert len(profile.topics) == 1
        assert profile.topics[0].topic == "basic_info"
        assert profile.topics[0].sub_topic == "name"
        assert profile.topics[0].content == "小红"


@pytest.mark.asyncio
async def test_profile_empty(client):
    """profile() 空画像返回空列表"""
    response = httpx.Response(200, json={"data": {"profiles": []}, "errno": 0})
    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=response):
        profile = await client.profile("uid-empty")
        assert len(profile.topics) == 0


# ===== context() 新格式解析 =====


@pytest.mark.asyncio
async def test_context_new_format(client):
    """context() 正确解析 {"data": {"context": "..."}, "errno": 0}"""
    response = httpx.Response(
        200, json={"data": {"context": "# 用户背景\n- 喜欢游泳"}, "errno": 0}
    )
    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=response):
        ctx = await client.context("uid-abc", max_token_size=500)
        assert ctx.user_id == "uid-abc"
        assert "游泳" in ctx.context


@pytest.mark.asyncio
async def test_context_fallback_format(client):
    """context() 兼容旧格式 {"context": "..."}（无 data 包装）"""
    response = httpx.Response(200, json={"context": "旧格式上下文"})
    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=response):
        ctx = await client.context("uid-abc")
        assert "旧格式上下文" in ctx.context

"""用户画像 API 集成测试

针对真实运行的 CozyMemory + Memobase 后端执行完整流程。
服务地址由 COZY_TEST_URL 环境变量控制（默认 http://localhost:8000）。
若服务不可达，测试自动跳过。

注意：Memobase 要求 user_id 必须为 UUID v4 格式。
"""

import pytest

from .conftest import requires_server


@requires_server
@pytest.mark.asyncio
async def test_insert_profile(http, unique_user_id):
    """POST /profiles/insert 成功插入对话"""
    response = await http.post(
        "/api/v1/profiles/insert",
        json={
            "user_id": unique_user_id,
            "messages": [{"role": "user", "content": "我叫小明，今年 25 岁，喜欢游泳"}],
            "sync": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["user_id"] == unique_user_id


@requires_server
@pytest.mark.asyncio
async def test_insert_requires_uuid_user_id(http):
    """POST /profiles/insert user_id 非 UUID v4 → 400/422"""
    response = await http.post(
        "/api/v1/profiles/insert",
        json={
            "user_id": "not-a-uuid",
            "messages": [{"role": "user", "content": "测试"}],
        },
    )
    # Memobase 在路径层拒绝非 UUID，CozyMemory 转发 → 400 或 502
    assert response.status_code in (400, 422, 502)


@requires_server
@pytest.mark.asyncio
async def test_flush_profile(http, unique_user_id):
    """POST /profiles/flush 触发缓冲区处理"""
    # 先插入数据
    await http.post(
        "/api/v1/profiles/insert",
        json={
            "user_id": unique_user_id,
            "messages": [{"role": "user", "content": "我喜欢编程"}],
            "sync": False,
        },
    )

    response = await http.post(
        "/api/v1/profiles/flush",
        json={"user_id": unique_user_id, "sync": True},
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


@requires_server
@pytest.mark.asyncio
async def test_get_profile(http, unique_user_id):
    """GET /profiles/{user_id} 返回用户画像结构"""
    # 先插入并 flush
    await http.post(
        "/api/v1/profiles/insert",
        json={
            "user_id": unique_user_id,
            "messages": [{"role": "user", "content": "我是程序员，居住在上海"}],
            "sync": True,
        },
    )

    response = await http.get(f"/api/v1/profiles/{unique_user_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "data" in body


@requires_server
@pytest.mark.asyncio
async def test_get_context(http, unique_user_id):
    """POST /profiles/{user_id}/context 返回可插入 prompt 的上下文"""
    # 先插入数据
    await http.post(
        "/api/v1/profiles/insert",
        json={
            "user_id": unique_user_id,
            "messages": [{"role": "user", "content": "我叫李雷，喜欢打篮球"}],
            "sync": True,
        },
    )

    response = await http.post(
        f"/api/v1/profiles/{unique_user_id}/context",
        json={"max_token_size": 500},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "data" in body


@requires_server
@pytest.mark.asyncio
async def test_insert_missing_user_id_422(http):
    """POST /profiles/insert 缺少 user_id → 422"""
    response = await http.post(
        "/api/v1/profiles/insert",
        json={"messages": [{"role": "user", "content": "hello"}]},
    )
    assert response.status_code == 422

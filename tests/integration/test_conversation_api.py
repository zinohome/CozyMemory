"""会话记忆 API 集成测试

针对真实运行的 CozyMemory + Mem0 后端执行完整 CRUD 流程。
服务地址由 COZY_TEST_URL 环境变量控制（默认 http://localhost:8000）。
若服务不可达，测试自动跳过。
"""

import pytest

from .conftest import requires_server

USER_ID = "integration-test-user"


@requires_server
@pytest.mark.asyncio
async def test_add_conversation(http):
    """POST /conversations 成功添加对话，返回 success=True"""
    response = await http.post(
        "/api/v1/conversations",
        json={
            "user_id": USER_ID,
            "messages": [{"role": "user", "content": "我叫测试用户，喜欢喝绿茶"}],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True


@requires_server
@pytest.mark.asyncio
async def test_list_conversations(http):
    """GET /conversations?user_id= 返回用户记忆列表"""
    # 先确保有记忆
    await http.post(
        "/api/v1/conversations",
        json={
            "user_id": USER_ID,
            "messages": [{"role": "user", "content": "我住在北京"}],
        },
    )

    response = await http.get("/api/v1/conversations", params={"user_id": USER_ID})
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    assert body["total"] >= 0


@requires_server
@pytest.mark.asyncio
async def test_search_conversations(http):
    """POST /conversations/search 返回搜索结果"""
    response = await http.post(
        "/api/v1/conversations/search",
        json={"user_id": USER_ID, "query": "用户喜好"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)


@requires_server
@pytest.mark.asyncio
async def test_add_and_get_conversation(http):
    """POST /conversations → GET /conversations/{id} 完整读写流程"""
    add_resp = await http.post(
        "/api/v1/conversations",
        json={
            "user_id": USER_ID,
            "messages": [{"role": "user", "content": "我的爱好是阅读"}],
        },
    )
    assert add_resp.status_code == 200
    data = add_resp.json().get("data", [])

    if not data:
        pytest.skip("Mem0 没有提取到记忆，跳过 get 验证")

    memory_id = data[0]["id"]
    get_resp = await http.get(f"/api/v1/conversations/{memory_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == memory_id


@requires_server
@pytest.mark.asyncio
async def test_get_nonexistent_conversation_404(http):
    """GET /conversations/{id} 不存在的 UUID 记忆 → 404"""
    import uuid
    fake_id = str(uuid.uuid4())
    response = await http.get(f"/api/v1/conversations/{fake_id}")
    # Mem0 对不存在的 UUID 返回 404，客户端转为 None，API 返回 404
    assert response.status_code == 404


@requires_server
@pytest.mark.asyncio
async def test_delete_all_conversations(http):
    """DELETE /conversations?user_id= 删除用户所有记忆"""
    response = await http.delete("/api/v1/conversations", params={"user_id": USER_ID})
    assert response.status_code == 200
    assert response.json()["success"] is True


@requires_server
@pytest.mark.asyncio
async def test_invalid_request_returns_422(http):
    """POST /conversations 缺少必填字段 → 422"""
    response = await http.post(
        "/api/v1/conversations",
        json={"messages": [{"role": "user", "content": "hello"}]},
    )
    assert response.status_code == 422

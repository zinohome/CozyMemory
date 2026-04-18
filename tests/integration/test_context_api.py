"""统一上下文 API 集成测试

POST /api/v1/context 端到端验证：
  - 三引擎并发调用，latency_ms 字段存在
  - include_* 开关生效
  - engine_timeout 触发时 errors 字段有内容
  - query 为空时 Cognee 跳过
  - 参数校验 422

服务地址由 COZY_TEST_URL 环境变量控制（默认 http://localhost:8000）。
"""

import pytest

from .conftest import requires_server


@requires_server
@pytest.mark.asyncio
async def test_context_all_engines(http, unique_user_id):
    """三引擎全开：success=True，latency_ms 存在，结构完整"""
    # 先写入一条 Mem0 记忆作为背景数据
    await http.post(
        "/api/v1/conversations",
        json={
            "user_id": unique_user_id,
            "messages": [{"role": "user", "content": "我喜欢打篮球"}],
        },
    )

    response = await http.post(
        "/api/v1/context",
        json={
            "user_id": unique_user_id,
            "query": "用户喜欢什么运动",
            "include_conversations": True,
            "include_profile": True,
            "include_knowledge": True,
            "conversation_limit": 5,
            "max_token_size": 300,
            "knowledge_top_k": 3,
            "knowledge_search_type": "CHUNKS",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["user_id"] == unique_user_id
    assert isinstance(body["conversations"], list)
    assert isinstance(body["knowledge"], list)
    assert isinstance(body["errors"], dict)
    assert body["latency_ms"] >= 0


@requires_server
@pytest.mark.asyncio
async def test_context_conversations_only(http, unique_user_id):
    """只开 Mem0，profile/knowledge 跳过"""
    response = await http.post(
        "/api/v1/context",
        json={
            "user_id": unique_user_id,
            "query": "test",
            "include_conversations": True,
            "include_profile": False,
            "include_knowledge": False,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["profile_context"] is None
    assert body["knowledge"] == []


@requires_server
@pytest.mark.asyncio
async def test_context_profile_only(http, unique_user_id):
    """只开 Memobase"""
    response = await http.post(
        "/api/v1/context",
        json={
            "user_id": unique_user_id,
            "include_conversations": False,
            "include_profile": True,
            "include_knowledge": False,
            "max_token_size": 200,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["conversations"] == []
    assert body["knowledge"] == []
    # profile_context 可以是 None（新用户无画像）或字符串
    assert body["profile_context"] is None or isinstance(body["profile_context"], str)


@requires_server
@pytest.mark.asyncio
async def test_context_no_query_skips_knowledge(http, unique_user_id):
    """query=None 时 Cognee 自动跳过，knowledge 为空列表"""
    response = await http.post(
        "/api/v1/context",
        json={
            "user_id": unique_user_id,
            "query": None,
            "include_conversations": True,
            "include_profile": False,
            "include_knowledge": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["knowledge"] == []
    assert "knowledge" not in body["errors"]


@requires_server
@pytest.mark.asyncio
async def test_context_engine_timeout_records_error(http, unique_user_id):
    """engine_timeout=0.001 极短超时：至少有一个引擎超时，errors 非空"""
    response = await http.post(
        "/api/v1/context",
        json={
            "user_id": unique_user_id,
            "query": "test",
            "include_conversations": True,
            "include_profile": True,
            "include_knowledge": True,
            "engine_timeout": 0.001,   # 1ms，必然超时
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True  # 整体不失败
    assert len(body["errors"]) > 0   # 至少有一个引擎超时
    for v in body["errors"].values():
        assert "timeout" in v.lower()


@requires_server
@pytest.mark.asyncio
async def test_context_missing_user_id_422(http):
    """缺少 user_id → 422"""
    response = await http.post(
        "/api/v1/context",
        json={"query": "test"},
    )
    assert response.status_code == 422


@requires_server
@pytest.mark.asyncio
async def test_context_with_chats(http, unique_user_id):
    """chats 参数透传不报错，接口正常返回"""
    response = await http.post(
        "/api/v1/context",
        json={
            "user_id": unique_user_id,
            "include_conversations": False,
            "include_profile": True,
            "include_knowledge": False,
            "chats": [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "你好！有什么需要帮助的？"},
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


@requires_server
@pytest.mark.asyncio
async def test_context_latency_ms_reflects_real_time(http, unique_user_id):
    """latency_ms 是真实耗时，应大于 0"""
    response = await http.post(
        "/api/v1/context",
        json={
            "user_id": unique_user_id,
            "include_conversations": True,
            "include_profile": True,
            "include_knowledge": False,
        },
    )
    assert response.status_code == 200
    assert response.json()["latency_ms"] > 0

"""
真实适配器测试

测试 MemobaseAdapter 的 HTTP 请求逻辑
使用 pytest-httpx 模拟 HTTP 响应
"""

import pytest
import httpx
from datetime import datetime

from src.models.memory import (
    MemoryCreate,
    MemoryQuery,
    MemoryUpdate,
    MemoryType,
)
from src.adapters.memobase_adapter import MemobaseAdapter


@pytest.fixture
def adapter():
    """创建真实适配器"""
    return MemobaseAdapter(
        api_url="http://localhost:8001",
        api_key="test_key",
        timeout=5.0,
    )


@pytest.mark.asyncio
async def test_health_check_success(adapter, httpx_mock):
    """测试健康检查成功"""
    httpx_mock.add_response(
        url="http://localhost:8001/health",
        json={"status": "healthy"},
        status_code=200
    )
    
    result = await adapter.health_check()
    
    assert result is True
    assert adapter._healthy is True


@pytest.mark.asyncio
async def test_health_check_failure(adapter, httpx_mock):
    """测试健康检查失败"""
    httpx_mock.add_response(
        url="http://localhost:8001/health",
        json={"status": "unhealthy"},
        status_code=200
    )
    
    result = await adapter.health_check()
    
    assert result is False
    assert adapter._healthy is False


@pytest.mark.asyncio
async def test_health_check_timeout(adapter, httpx_mock):
    """测试健康检查超时"""
    httpx_mock.add_exception(
        url="http://localhost:8001/health",
        exception=httpx.TimeoutException("Timeout")
    )
    
    result = await adapter.health_check()
    
    assert result is False
    assert adapter._healthy is False


@pytest.mark.asyncio
async def test_health_check_connection_error(adapter, httpx_mock):
    """测试健康检查连接错误"""
    httpx_mock.add_exception(
        url="http://localhost:8001/health",
        exception=httpx.ConnectError("Connection refused")
    )
    
    result = await adapter.health_check()
    
    assert result is False
    assert adapter._healthy is False


@pytest.mark.asyncio
async def test_create_memory(adapter, httpx_mock):
    """测试创建记忆"""
    memory = MemoryCreate(
        user_id="user_123",
        content="测试内容",
        memory_type=MemoryType.FACT,
        metadata={"source": "test"}
    )
    
    httpx_mock.add_response(
        url="http://localhost:8001/api/v1/memories",
        method="POST",
        json={
            "id": "mem_123",
            "user_id": "user_123",
            "content": "测试内容",
            "memory_type": "fact",
            "metadata": {"source": "test"},
            "created_at": "2026-04-06T10:00:00Z"
        },
        status_code=200
    )
    
    created = await adapter.create_memory(memory)
    
    assert created.id == "mem_123"
    assert created.user_id == "user_123"
    assert created.content == "测试内容"


@pytest.mark.asyncio
async def test_get_memory(adapter, httpx_mock):
    """测试获取记忆"""
    httpx_mock.add_response(
        url="http://localhost:8001/api/v1/memories/mem_123",
        method="GET",
        json={
            "id": "mem_123",
            "user_id": "user_123",
            "content": "测试内容",
            "memory_type": "fact",
            "created_at": "2026-04-06T10:00:00Z"
        },
        status_code=200
    )
    
    result = await adapter.get_memory("mem_123")
    
    assert result is not None
    assert result.id == "mem_123"


@pytest.mark.asyncio
async def test_get_memory_not_found(adapter, httpx_mock):
    """测试获取不存在的记忆"""
    httpx_mock.add_response(
        url="http://localhost:8001/api/v1/memories/mem_123",
        method="GET",
        status_code=404
    )
    
    result = await adapter.get_memory("mem_123")
    
    assert result is None


@pytest.mark.asyncio
async def test_query_memories(adapter, httpx_mock):
    """测试查询记忆"""
    query = MemoryQuery(
        user_id="user_123",
        query="测试",
        memory_type=MemoryType.FACT,
        limit=10
    )
    
    # 使用 params 匹配
    httpx_mock.add_response(
        url="http://localhost:8001/api/v1/memories/search",
        method="GET",
        match_params={
            "user_id": "user_123",
            "limit": "10",
            "q": "测试",
            "type": "fact"
        },
        json={
            "memories": [
                {
                    "id": "mem_123",
                    "user_id": "user_123",
                    "content": "测试内容",
                    "memory_type": "fact",
                    "created_at": "2026-04-06T10:00:00Z"
                }
            ]
        },
        status_code=200
    )
    
    results = await adapter.query_memories(query)
    
    assert len(results) == 1
    assert results[0].id == "mem_123"


@pytest.mark.asyncio
async def test_update_memory(adapter, httpx_mock):
    """测试更新记忆"""
    # 先 mock get
    httpx_mock.add_response(
        url="http://localhost:8001/api/v1/memories/mem_123",
        method="GET",
        json={
            "id": "mem_123",
            "user_id": "user_123",
            "content": "原始内容",
            "memory_type": "fact",
            "created_at": "2026-04-06T10:00:00Z"
        },
        status_code=200
    )
    
    # 再 mock update
    httpx_mock.add_response(
        url="http://localhost:8001/api/v1/memories/mem_123",
        method="PUT",
        json={
            "id": "mem_123",
            "user_id": "user_123",
            "content": "新内容",
            "memory_type": "fact",
            "created_at": "2026-04-06T10:00:00Z",
            "updated_at": "2026-04-06T11:00:00Z"
        },
        status_code=200
    )
    
    update = MemoryUpdate(content="新内容")
    result = await adapter.update_memory("mem_123", update)
    
    assert result is not None
    assert result.content == "新内容"


@pytest.mark.asyncio
async def test_delete_memory(adapter, httpx_mock):
    """测试删除记忆"""
    httpx_mock.add_response(
        url="http://localhost:8001/api/v1/memories/mem_123",
        method="DELETE",
        status_code=200,
        json={"success": True}
    )
    
    result = await adapter.delete_memory("mem_123")
    
    assert result is True


@pytest.mark.asyncio
async def test_delete_memory_not_found(adapter, httpx_mock):
    """测试删除不存在的记忆"""
    httpx_mock.add_response(
        url="http://localhost:8001/api/v1/memories/mem_123",
        method="DELETE",
        status_code=404
    )
    
    result = await adapter.delete_memory("mem_123")
    
    assert result is False


@pytest.mark.asyncio
async def test_batch_create(adapter, httpx_mock):
    """测试批量创建"""
    memories = [
        MemoryCreate(
            user_id="user_123",
            content=f"内容 {i}",
            memory_type=MemoryType.FACT,
        )
        for i in range(3)
    ]
    
    # Mock 3 次创建响应
    for i in range(3):
        httpx_mock.add_response(
            url="http://localhost:8001/api/v1/memories",
            method="POST",
            json={
                "id": f"mem_{i}",
                "user_id": "user_123",
                "content": f"内容 {i}",
                "memory_type": "fact",
                "created_at": "2026-04-06T10:00:00Z"
            },
            status_code=200
        )
    
    results = await adapter.batch_create(memories)
    
    assert len(results) == 3
    assert all(r.id.startswith("mem_") for r in results)


@pytest.mark.asyncio
async def test_request_with_api_key(adapter, httpx_mock):
    """测试带 API Key 的请求"""
    httpx_mock.add_response(
        url="http://localhost:8001/health",
        json={"status": "healthy"},
        status_code=200
    )
    
    await adapter.health_check()
    
    # 验证请求头包含 API Key
    request = httpx_mock.get_request()
    assert request.headers["Authorization"] == "Bearer test_key"


@pytest.mark.asyncio
async def test_request_timeout(adapter, httpx_mock):
    """测试请求超时处理"""
    httpx_mock.add_exception(
        url="http://localhost:8001/health",
        exception=httpx.TimeoutException("Timeout")
    )
    
    with pytest.raises(httpx.TimeoutException):
        await adapter._request("GET", "/health")
    
    # 验证健康状态变为 False
    assert adapter._healthy is False


@pytest.mark.asyncio
async def test_request_http_error(adapter, httpx_mock):
    """测试 HTTP 错误处理"""
    httpx_mock.add_response(
        url="http://localhost:8001/health",
        status_code=500
    )
    
    with pytest.raises(httpx.HTTPStatusError):
        await adapter._request("GET", "/health")
    
    # 验证健康状态变为 False
    assert adapter._healthy is False


@pytest.mark.asyncio
async def test_create_memory_object(adapter):
    """测试创建 Memory 对象辅助方法"""
    data = {
        "id": "mem_123",
        "content": "测试内容",
        "memory_type": "fact",
        "metadata": {"key": "value"},
        "created_at": "2026-04-06T10:00:00Z",
        "updated_at": "2026-04-06T11:00:00Z",
        "confidence": 0.95
    }
    
    memory = adapter._create_memory_object(data, "user_123")
    
    assert memory.id == "mem_123"
    assert memory.user_id == "user_123"
    assert memory.content == "测试内容"
    assert memory.memory_type == "fact"
    assert memory.metadata == {"key": "value"}
    assert memory.confidence == 0.95
    # 时区处理
    assert memory.created_at.replace(tzinfo=None) == datetime(2026, 4, 6, 10, 0, 0)
    assert memory.updated_at.replace(tzinfo=None) == datetime(2026, 4, 6, 11, 0, 0)


@pytest.mark.asyncio
async def test_create_memory_object_minimal(adapter):
    """测试创建最小化 Memory 对象"""
    data = {
        "content": "测试内容"
    }
    
    memory = adapter._create_memory_object(data, "user_123")
    
    assert memory.id.startswith("memobase_")
    assert memory.user_id == "user_123"
    assert memory.content == "测试内容"
    assert memory.memory_type == "fact"  # 默认值
    assert memory.metadata is None
    assert memory.confidence is None

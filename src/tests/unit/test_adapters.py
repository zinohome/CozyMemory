"""
适配器测试

测试 Memobase Mock 适配器的功能。
"""

import pytest
import asyncio
from datetime import datetime

from src.models.memory import (
    MemoryCreate,
    MemoryQuery,
    MemoryUpdate,
    MemoryType,
    MemorySource,
)
from src.adapters.memobase_mock_adapter import MemobaseMockAdapter


@pytest.fixture
def adapter():
    """创建 Mock 适配器"""
    return MemobaseMockAdapter(
        api_url="http://localhost:8001",
        api_key="test_key",
        timeout=5.0,
    )


@pytest.fixture(autouse=True)
def clear_mock_data():
    """每个测试前清空 Mock 数据"""
    MemobaseMockAdapter.clear_all()
    yield


@pytest.mark.asyncio
async def test_health_check(adapter):
    """测试健康检查"""
    result = await adapter.health_check()
    
    assert result is True
    assert adapter._healthy is True
    assert adapter._last_check is not None
    assert adapter._latency_ms == 10.0


@pytest.mark.asyncio
async def test_create_memory(adapter):
    """测试创建记忆"""
    memory = MemoryCreate(
        user_id="user_123",
        content="用户喜欢喝拿铁咖啡",
        memory_type=MemoryType.PREFERENCE,
        metadata={"source": "chat", "confidence": 0.95}
    )
    
    created = await adapter.create_memory(memory)
    
    assert created.id.startswith("mem_")
    assert created.user_id == "user_123"
    assert created.content == "用户喜欢喝拿铁咖啡"
    assert created.memory_type == MemoryType.PREFERENCE
    assert created.source == MemorySource.MEMOBASE
    assert created.confidence == 0.95


@pytest.mark.asyncio
async def test_get_memory(adapter):
    """测试获取记忆"""
    # 先创建
    memory = MemoryCreate(
        user_id="user_123",
        content="测试内容",
        memory_type=MemoryType.FACT,
    )
    created = await adapter.create_memory(memory)
    
    # 再获取
    retrieved = await adapter.get_memory(created.id)
    
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.content == "测试内容"


@pytest.mark.asyncio
async def test_get_memory_not_found(adapter):
    """测试获取不存在的记忆"""
    result = await adapter.get_memory("non_existent_id")
    assert result is None


@pytest.mark.asyncio
async def test_query_memories(adapter):
    """测试查询记忆"""
    # 创建多条记忆
    for i in range(5):
        await adapter.create_memory(
            MemoryCreate(
                user_id="user_123",
                content=f"测试内容 {i}",
                memory_type=MemoryType.FACT,
            )
        )
    
    # 查询
    query = MemoryQuery(
        user_id="user_123",
        limit=10
    )
    results = await adapter.query_memories(query)
    
    assert len(results) == 5


@pytest.mark.asyncio
async def test_query_memories_with_filter(adapter):
    """测试带过滤的查询"""
    # 创建不同类型记忆
    await adapter.create_memory(
        MemoryCreate(
            user_id="user_123",
            content="咖啡偏好",
            memory_type=MemoryType.PREFERENCE,
        )
    )
    await adapter.create_memory(
        MemoryCreate(
            user_id="user_123",
            content="事实信息",
            memory_type=MemoryType.FACT,
        )
    )
    
    # 按类型过滤
    query = MemoryQuery(
        user_id="user_123",
        memory_type=MemoryType.PREFERENCE,
        limit=10
    )
    results = await adapter.query_memories(query)
    
    assert len(results) == 1
    assert results[0].memory_type == MemoryType.PREFERENCE


@pytest.mark.asyncio
async def test_update_memory(adapter):
    """测试更新记忆"""
    # 创建
    memory = MemoryCreate(
        user_id="user_123",
        content="原始内容",
        memory_type=MemoryType.FACT,
    )
    created = await adapter.create_memory(memory)
    
    # 更新
    update = MemoryUpdate(
        content="更新后的内容",
        metadata={"updated": True}
    )
    updated = await adapter.update_memory(created.id, update)
    
    assert updated is not None
    assert updated.content == "更新后的内容"
    assert updated.metadata == {"updated": True}
    assert updated.updated_at is not None


@pytest.mark.asyncio
async def test_delete_memory(adapter):
    """测试删除记忆"""
    # 创建
    memory = MemoryCreate(
        user_id="user_123",
        content="待删除",
        memory_type=MemoryType.FACT,
    )
    created = await adapter.create_memory(memory)
    
    # 删除
    success = await adapter.delete_memory(created.id)
    assert success is True
    
    # 验证已删除
    retrieved = await adapter.get_memory(created.id)
    assert retrieved is None


@pytest.mark.asyncio
async def test_delete_non_existent_memory(adapter):
    """测试删除不存在的记忆"""
    result = await adapter.delete_memory("non_existent")
    assert result is False


@pytest.mark.asyncio
async def test_batch_create(adapter):
    """测试批量创建"""
    memories = [
        MemoryCreate(
            user_id="user_123",
            content=f"批量内容 {i}",
            memory_type=MemoryType.FACT,
        )
        for i in range(10)
    ]
    
    results = await adapter.batch_create(memories)
    
    assert len(results) == 10
    assert all(r.id.startswith("mem_") for r in results)


@pytest.mark.asyncio
async def test_query_with_text_search(adapter):
    """测试文本搜索"""
    # 创建包含关键词的记忆
    await adapter.create_memory(
        MemoryCreate(
            user_id="user_123",
            content="用户喜欢咖啡",
            memory_type=MemoryType.PREFERENCE,
        )
    )
    await adapter.create_memory(
        MemoryCreate(
            user_id="user_123",
            content="用户喜欢茶",
            memory_type=MemoryType.PREFERENCE,
        )
    )
    
    # 搜索"咖啡"
    query = MemoryQuery(
        user_id="user_123",
        query="咖啡",
        limit=10
    )
    results = await adapter.query_memories(query)
    
    assert len(results) == 1
    assert "咖啡" in results[0].content

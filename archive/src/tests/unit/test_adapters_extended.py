"""
适配器补充测试

提高适配器测试覆盖率至 85%+
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
from src.adapters.base import BaseAdapter


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
async def test_adapter_properties(adapter):
    """测试适配器属性"""
    assert adapter.engine_name == "Memobase (Mock)"
    assert adapter.source == MemorySource.MEMOBASE
    assert adapter.api_url == "http://localhost:8001"
    assert adapter.api_key == "test_key"
    assert adapter.timeout == 5.0


@pytest.mark.asyncio
async def test_adapter_status(adapter):
    """测试适配器状态"""
    status = adapter.get_status()
    
    assert status["name"] == "Memobase (Mock)"
    assert status["enabled"] is True
    assert "status" in status
    assert "latency_ms" in status


@pytest.mark.asyncio
async def test_health_check_multiple_times(adapter):
    """测试多次健康检查"""
    # 第一次检查
    result1 = await adapter.health_check()
    assert result1 is True
    assert adapter._healthy is True
    
    # 第二次检查
    result2 = await adapter.health_check()
    assert result2 is True
    assert adapter._healthy is True
    
    # 检查时间更新
    assert adapter._last_check is not None


@pytest.mark.asyncio
async def test_create_memory_with_all_types(adapter):
    """测试创建所有类型的记忆"""
    types = [
        MemoryType.FACT,
        MemoryType.EVENT,
        MemoryType.PREFERENCE,
        MemoryType.SKILL,
        MemoryType.CONVERSATION,
    ]
    
    for mem_type in types:
        memory = MemoryCreate(
            user_id="user_123",
            content=f"{mem_type.value} 类型记忆",
            memory_type=mem_type,
            metadata={"type": mem_type.value}
        )
        
        created = await adapter.create_memory(memory)
        
        assert created.id.startswith("mem_")
        assert created.memory_type == mem_type
        assert created.source == MemorySource.MEMOBASE


@pytest.mark.asyncio
async def test_create_memory_with_metadata(adapter):
    """测试创建带元数据的记忆"""
    memory = MemoryCreate(
        user_id="user_123",
        content="带元数据的记忆",
        memory_type=MemoryType.FACT,
        metadata={
            "source": "chat",
            "confidence": 0.95,
            "tags": ["important", "verified"],
            "nested": {"key": "value"}
        }
    )
    
    created = await adapter.create_memory(memory)
    
    assert created.metadata is not None
    assert created.metadata["source"] == "chat"
    assert created.metadata["confidence"] == 0.95
    assert created.metadata["tags"] == ["important", "verified"]


@pytest.mark.asyncio
async def test_query_memories_pagination(adapter):
    """测试查询分页"""
    # 创建 25 条记忆
    for i in range(25):
        await adapter.create_memory(
            MemoryCreate(
                user_id="user_123",
                content=f"内容 {i}",
                memory_type=MemoryType.FACT,
            )
        )
    
    # 查询前 10 条
    query = MemoryQuery(user_id="user_123", limit=10)
    results = await adapter.query_memories(query)
    assert len(results) == 10
    
    # 查询前 5 条
    query = MemoryQuery(user_id="user_123", limit=5)
    results = await adapter.query_memories(query)
    assert len(results) == 5


@pytest.mark.asyncio
async def test_query_memories_multiple_users(adapter):
    """测试多用户查询隔离"""
    # 用户 A 的记忆
    for i in range(5):
        await adapter.create_memory(
            MemoryCreate(
                user_id="user_a",
                content=f"用户 A 内容 {i}",
                memory_type=MemoryType.FACT,
            )
        )
    
    # 用户 B 的记忆
    for i in range(3):
        await adapter.create_memory(
            MemoryCreate(
                user_id="user_b",
                content=f"用户 B 内容 {i}",
                memory_type=MemoryType.FACT,
            )
        )
    
    # 查询用户 A
    query_a = MemoryQuery(user_id="user_a", limit=10)
    results_a = await adapter.query_memories(query_a)
    assert len(results_a) == 5
    assert all(m.user_id == "user_a" for m in results_a)
    
    # 查询用户 B
    query_b = MemoryQuery(user_id="user_b", limit=10)
    results_b = await adapter.query_memories(query_b)
    assert len(results_b) == 3
    assert all(m.user_id == "user_b" for m in results_b)


@pytest.mark.asyncio
async def test_update_memory_content_only(adapter):
    """测试只更新内容"""
    memory = MemoryCreate(
        user_id="user_123",
        content="原始内容",
        memory_type=MemoryType.FACT,
        metadata={"key": "value"}
    )
    created = await adapter.create_memory(memory)
    
    update = MemoryUpdate(content="新内容")
    updated = await adapter.update_memory(created.id, update)
    
    assert updated is not None
    assert updated.content == "新内容"
    assert updated.metadata == {"key": "value"}  # 元数据保留


@pytest.mark.asyncio
async def test_update_memory_metadata_only(adapter):
    """测试只更新元数据"""
    memory = MemoryCreate(
        user_id="user_123",
        content="原始内容",
        memory_type=MemoryType.FACT,
        metadata={"key": "value"}
    )
    created = await adapter.create_memory(memory)
    
    update = MemoryUpdate(metadata={"updated": True, "new_key": "new_value"})
    updated = await adapter.update_memory(created.id, update)
    
    assert updated is not None
    assert updated.content == "原始内容"  # 内容保留
    assert updated.metadata == {"updated": True, "new_key": "new_value"}


@pytest.mark.asyncio
async def test_update_memory_empty_update(adapter):
    """测试空更新"""
    memory = MemoryCreate(
        user_id="user_123",
        content="原始内容",
        memory_type=MemoryType.FACT,
    )
    created = await adapter.create_memory(memory)
    
    update = MemoryUpdate()  # 空更新
    updated = await adapter.update_memory(created.id, update)
    
    assert updated is not None
    assert updated.content == "原始内容"


@pytest.mark.asyncio
async def test_batch_create_large(adapter):
    """测试大批量创建"""
    memories = [
        MemoryCreate(
            user_id="user_123",
            content=f"批量内容 {i}",
            memory_type=MemoryType.FACT,
        )
        for i in range(50)
    ]
    
    results = await adapter.batch_create(memories)
    
    assert len(results) == 50
    assert all(r.id.startswith("mem_") for r in results)
    assert all(r.user_id == "user_123" for r in results)


@pytest.mark.asyncio
async def test_batch_create_mixed_types(adapter):
    """测试批量创建混合类型"""
    memories = [
        MemoryCreate(
            user_id="user_123",
            content=f"{t.value} 类型",
            memory_type=t,
        )
        for t in [
            MemoryType.FACT,
            MemoryType.EVENT,
            MemoryType.PREFERENCE,
            MemoryType.SKILL,
            MemoryType.CONVERSATION,
        ]
    ]
    
    results = await adapter.batch_create(memories)
    
    assert len(results) == 5
    types = [r.memory_type for r in results]
    assert MemoryType.FACT in types
    assert MemoryType.EVENT in types
    assert MemoryType.PREFERENCE in types
    assert MemoryType.SKILL in types
    assert MemoryType.CONVERSATION in types


@pytest.mark.asyncio
async def test_query_after_delete(adapter):
    """测试删除后查询"""
    # 创建记忆
    memory = MemoryCreate(
        user_id="user_123",
        content="待删除",
        memory_type=MemoryType.FACT,
    )
    created = await adapter.create_memory(memory)
    
    # 删除
    success = await adapter.delete_memory(created.id)
    assert success is True
    
    # 查询不应包含已删除
    query = MemoryQuery(user_id="user_123", limit=10)
    results = await adapter.query_memories(query)
    assert not any(m.id == created.id for m in results)


@pytest.mark.asyncio
async def test_memory_timestamps(adapter):
    """测试记忆时间戳"""
    memory = MemoryCreate(
        user_id="user_123",
        content="时间戳测试",
        memory_type=MemoryType.FACT,
    )
    created = await adapter.create_memory(memory)
    
    assert created.created_at is not None
    assert created.updated_at is None  # 创建时未更新
    
    # 更新后
    update = MemoryUpdate(content="新内容")
    updated = await adapter.update_memory(created.id, update)
    
    assert updated.updated_at is not None
    assert updated.updated_at > updated.created_at


@pytest.mark.asyncio
async def test_memory_confidence(adapter):
    """测试记忆置信度"""
    memory = MemoryCreate(
        user_id="user_123",
        content="置信度测试",
        memory_type=MemoryType.FACT,
        metadata={"confidence": 0.95}
    )
    created = await adapter.create_memory(memory)
    
    # Mock 适配器默认置信度 0.95
    assert created.confidence == 0.95


@pytest.mark.asyncio
async def test_clear_all(adapter):
    """测试清空所有数据"""
    # 创建多条记忆
    for i in range(10):
        await adapter.create_memory(
            MemoryCreate(
                user_id="user_123",
                content=f"内容 {i}",
                memory_type=MemoryType.FACT,
            )
        )
    
    # 验证创建
    query = MemoryQuery(user_id="user_123", limit=100)
    results = await adapter.query_memories(query)
    assert len(results) == 10
    
    # 清空
    MemobaseMockAdapter.clear_all()
    
    # 验证清空
    results = await adapter.query_memories(query)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_concurrent_create(adapter):
    """测试并发创建"""
    async def create_memory(i):
        return await adapter.create_memory(
            MemoryCreate(
                user_id="user_123",
                content=f"并发内容 {i}",
                memory_type=MemoryType.FACT,
            )
        )
    
    # 并发创建 10 条
    tasks = [create_memory(i) for i in range(10)]
    results = await asyncio.gather(*tasks)
    
    assert len(results) == 10
    assert all(r.id.startswith("mem_") for r in results)
    
    # 验证所有记忆都存在
    query = MemoryQuery(user_id="user_123", limit=100)
    all_memories = await adapter.query_memories(query)
    assert len(all_memories) == 10

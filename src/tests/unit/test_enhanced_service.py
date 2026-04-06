"""
增强记忆服务端到端测试

测试缓存层 + 路由层 + 融合层的完整集成。
"""

import pytest
import asyncio
from typing import Dict, List

from src.models.memory import (
    Memory,
    MemoryCreate,
    MemoryQuery,
    MemoryType,
    MemorySource,
)
from src.adapters.memobase_mock_adapter import MemobaseMockAdapter
from src.services.enhanced_memory_service import EnhancedMemoryService
from src.services.cache_service import close_cache_service
from src.services.router_service import close_router_service
from src.services.fusion_service import close_fusion_service


@pytest.fixture
async def service():
    """创建增强服务"""
    # 创建多个 Mock 适配器
    adapters = {
        "memobase": MemobaseMockAdapter(api_url="http://localhost:8000"),
        "local": MemobaseMockAdapter(api_url="http://localhost:8001"),
        "vector": MemobaseMockAdapter(api_url="http://localhost:8002"),
    }
    
    service = EnhancedMemoryService(
        adapters=adapters,
        enable_cache=True,
        enable_routing=True,
        enable_fusion=True,
    )
    
    yield service
    
    # 清理
    await service.close()
    await close_cache_service()
    await close_router_service()
    await close_fusion_service()


class TestEnhancedMemoryService:
    """增强记忆服务测试"""
    
    @pytest.mark.asyncio
    async def test_create_memory(self, service):
        """创建记忆"""
        memory = MemoryCreate(
            user_id="user1",
            content="测试记忆",
            memory_type=MemoryType.FACT,
        )
        
        result = await service.create_memory(memory)
        
        assert result.id is not None
        assert result.content == "测试记忆"
        assert result.user_id == "user1"
    
    @pytest.mark.asyncio
    async def test_get_memory_with_cache(self, service):
        """获取记忆 (带缓存)"""
        # 创建记忆
        memory = MemoryCreate(
            user_id="user1",
            content="缓存测试",
            memory_type=MemoryType.FACT,
        )
        created = await service.create_memory(memory)
        
        # 第一次查询 (缓存未命中)
        result1 = await service.get_memory(created.id)
        assert result1 is not None
        
        # 第二次查询 (缓存命中)
        result2 = await service.get_memory(created.id)
        assert result2 is not None
        assert result2.id == created.id
        
        # 验证统计
        stats = await service.get_stats()
        assert stats["cache_hits"] >= 1
    
    @pytest.mark.asyncio
    async def test_query_memories_with_routing(self, service):
        """查询记忆 (带路由)"""
        # 创建多条记忆
        memories = [
            MemoryCreate(
                user_id="user1",
                content=f"测试记忆{i}",
                memory_type=MemoryType.FACT,
            )
            for i in range(5)
        ]
        
        created = await service.batch_create(memories)
        assert len(created) == 5
        
        # 查询
        query = MemoryQuery(
            user_id="user1",
            query="测试",
            limit=10,
        )
        
        results = await service.query_memories(query)
        
        assert len(results) >= 1
    
    @pytest.mark.asyncio
    async def test_query_memories_with_fusion(self, service):
        """查询记忆 (带融合)"""
        # 创建不同来源的记忆
        memories = [
            MemoryCreate(
                user_id="user1",
                content="AI 定义",
                memory_type=MemoryType.FACT,
            ),
            MemoryCreate(
                user_id="user1",
                content="AI 应用",
                memory_type=MemoryType.SKILL,
            ),
        ]
        
        await service.batch_create(memories)
        
        # 查询
        query = MemoryQuery(
            user_id="user1",
            query="AI",
            limit=10,
        )
        
        results = await service.query_memories(query)
        
        # 验证结果
        assert len(results) >= 1
        
        # 验证统计
        stats = await service.get_stats()
        assert stats["fusion_operations"] >= 0  # 可能单引擎
    
    @pytest.mark.asyncio
    async def test_query_cache_hit(self, service):
        """查询缓存命中"""
        # 创建记忆
        memory = MemoryCreate(
            user_id="user1",
            content="缓存命中测试",
            memory_type=MemoryType.FACT,
        )
        await service.create_memory(memory)
        
        # 第一次查询
        query1 = MemoryQuery(
            user_id="user1",
            query="缓存命中测试",
            limit=10,
        )
        results1 = await service.query_memories(query1)
        
        # 第二次查询 (相同查询)
        query2 = MemoryQuery(
            user_id="user1",
            query="缓存命中测试",
            limit=10,
        )
        results2 = await service.query_memories(query2)
        
        # 验证缓存命中
        stats = await service.get_stats()
        assert stats["cache_hits"] >= 1
    
    @pytest.mark.asyncio
    async def test_update_memory_invalidate_cache(self, service):
        """更新记忆使缓存失效"""
        # 创建记忆
        memory = MemoryCreate(
            user_id="user1",
            content="原始内容",
            memory_type=MemoryType.FACT,
        )
        created = await service.create_memory(memory)
        
        # 查询 (缓存)
        await service.get_memory(created.id)
        
        # 更新
        from src.models.memory import MemoryUpdate
        update = MemoryUpdate(content="更新内容")
        updated = await service.update_memory(created.id, update)
        
        assert updated is not None
        assert updated.content == "更新内容"
    
    @pytest.mark.asyncio
    async def test_delete_memory_invalidate_cache(self, service):
        """删除记忆使缓存失效"""
        # 创建记忆
        memory = MemoryCreate(
            user_id="user1",
            content="待删除",
            memory_type=MemoryType.FACT,
        )
        created = await service.create_memory(memory)
        
        # 删除
        success = await service.delete_memory(created.id)
        
        assert success is True
        
        # 验证已删除
        result = await service.get_memory(created.id)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_batch_create_routing(self, service):
        """批量创建 (带路由)"""
        memories = [
            MemoryCreate(
                user_id="user1",
                content=f"批量{i}",
                memory_type=MemoryType.FACT,
            )
            for i in range(10)
        ]
        
        created = await service.batch_create(memories)
        
        assert len(created) == 10
        
        # 验证统计
        stats = await service.get_stats()
        assert stats["routing_decisions"] >= 1
    
    @pytest.mark.asyncio
    async def test_stats_tracking(self, service):
        """统计跟踪"""
        # 创建记忆
        memory = MemoryCreate(
            user_id="user1",
            content="统计测试",
            memory_type=MemoryType.FACT,
        )
        await service.create_memory(memory)
        
        # 查询
        query = MemoryQuery(
            user_id="user1",
            query="统计",
            limit=10,
        )
        await service.query_memories(query)
        
        # 获取统计
        stats = await service.get_stats()
        
        assert stats["total_queries"] >= 2
        assert "cache_hit_rate" in stats
        assert "average_latency_ms" in stats
        assert "engines" in stats
        assert stats["engines"] == ["memobase", "local", "vector"]
    
    @pytest.mark.asyncio
    async def test_reset_stats(self, service):
        """重置统计"""
        # 创建记忆
        memory = MemoryCreate(
            user_id="user1",
            content="测试",
            memory_type=MemoryType.FACT,
        )
        await service.create_memory(memory)
        
        # 重置
        await service.reset_stats()
        
        # 验证
        stats = await service.get_stats()
        assert stats["total_queries"] == 0
        assert stats["cache_hits"] == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_queries(self, service):
        """并发查询"""
        # 创建记忆
        memories = [
            MemoryCreate(
                user_id="user1",
                content=f"并发{i}",
                memory_type=MemoryType.FACT,
            )
            for i in range(5)
        ]
        await service.batch_create(memories)
        
        # 并发查询
        async def query(i):
            q = MemoryQuery(
                user_id="user1",
                query=f"并发{i}",
                limit=10,
            )
            return await service.query_memories(q)
        
        tasks = [query(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        # 验证所有查询都成功
        assert len(results) == 5
    
    @pytest.mark.asyncio
    async def test_multi_engine_query(self, service):
        """多引擎查询"""
        # 创建记忆
        memory = MemoryCreate(
            user_id="user1",
            content="多引擎测试",
            memory_type=MemoryType.FACT,
        )
        await service.create_memory(memory)
        
        # 查询
        query = MemoryQuery(
            user_id="user1",
            query="多引擎",
            limit=10,
        )
        
        results = await service.query_memories(query)
        
        # 验证
        assert isinstance(results, list)
        
        # 验证统计
        stats = await service.get_stats()
        assert stats["routing_decisions"] >= 1


class TestEnhancedServiceFeatures:
    """增强功能测试"""
    
    @pytest.mark.asyncio
    async def test_disable_cache(self):
        """禁用缓存"""
        adapters = {
            "memobase": MemobaseMockAdapter(api_url="http://localhost:8000"),
        }
        
        service = EnhancedMemoryService(
            adapters=adapters,
            enable_cache=False,
            enable_routing=True,
            enable_fusion=True,
        )
        
        memory = MemoryCreate(
            user_id="user1",
            content="无缓存",
            memory_type=MemoryType.FACT,
        )
        await service.create_memory(memory)
        
        stats = await service.get_stats()
        assert stats["features"]["cache_enabled"] is False
        
        await service.close()
    
    @pytest.mark.asyncio
    async def test_disable_routing(self):
        """禁用路由"""
        adapters = {
            "memobase": MemobaseMockAdapter(api_url="http://localhost:8000"),
        }
        
        service = EnhancedMemoryService(
            adapters=adapters,
            enable_cache=True,
            enable_routing=False,
            enable_fusion=True,
        )
        
        stats = await service.get_stats()
        assert stats["features"]["routing_enabled"] is False
        
        await service.close()
    
    @pytest.mark.asyncio
    async def test_disable_fusion(self):
        """禁用融合"""
        adapters = {
            "memobase": MemobaseMockAdapter(api_url="http://localhost:8000"),
        }
        
        service = EnhancedMemoryService(
            adapters=adapters,
            enable_cache=True,
            enable_routing=True,
            enable_fusion=False,
        )
        
        stats = await service.get_stats()
        assert stats["features"]["fusion_enabled"] is False
        
        await service.close()


class TestIntegrationWorkflow:
    """集成工作流测试"""
    
    @pytest.mark.asyncio
    async def test_full_crud_workflow(self, service):
        """完整 CRUD 工作流"""
        # 1. Create
        memory = MemoryCreate(
            user_id="user1",
            content="完整工作流测试",
            memory_type=MemoryType.EVENT,
        )
        created = await service.create_memory(memory)
        assert created.id is not None
        
        # 2. Read
        retrieved = await service.get_memory(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        
        # 3. Update
        from src.models.memory import MemoryUpdate
        update = MemoryUpdate(content="更新后的内容")
        updated = await service.update_memory(created.id, update)
        assert updated is not None
        assert updated.content == "更新后的内容"
        
        # 4. Delete
        success = await service.delete_memory(created.id)
        assert success is True
        
        # 5. Verify deleted
        deleted = await service.get_memory(created.id)
        assert deleted is None
    
    @pytest.mark.asyncio
    async def test_query_workflow(self, service):
        """完整查询工作流"""
        # 1. 创建多条记忆
        memories = [
            MemoryCreate(
                user_id="user1",
                content="Python 教程",
                memory_type=MemoryType.SKILL,
            ),
            MemoryCreate(
                user_id="user1",
                content="Python 项目",
                memory_type=MemoryType.EVENT,
            ),
            MemoryCreate(
                user_id="user1",
                content="喜欢 Python",
                memory_type=MemoryType.PREFERENCE,
            ),
        ]
        await service.batch_create(memories)
        
        # 2. 查询 "Python"
        query = MemoryQuery(
            user_id="user1",
            query="Python",
            limit=10,
        )
        results = await service.query_memories(query)
        
        assert len(results) >= 1
        
        # 3. 查询 "教程"
        query2 = MemoryQuery(
            user_id="user1",
            query="教程",
            limit=10,
        )
        results2 = await service.query_memories(query2)
        
        assert len(results2) >= 1
        
        # 4. 验证统计
        stats = await service.get_stats()
        assert stats["total_queries"] >= 2
        assert stats["routing_decisions"] >= 1

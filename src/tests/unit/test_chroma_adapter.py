"""
ChromaDB 适配器单元测试

测试覆盖:
- CRUD 操作
- 语义搜索
- 批量操作
- 相似度计算
- 性能测试

注意：需要安装 chromadb 和 sentence-transformers
     如果未安装，测试将自动跳过
"""

import pytest
import tempfile
from pathlib import Path
from typing import List

# 检查依赖
chromadb_installed = False
try:
    import chromadb
    chromadb_installed = True
except ImportError:
    pass

pytestmark = pytest.mark.skipif(
    not chromadb_installed,
    reason="chromadb not installed",
)

from src.adapters.chroma_adapter import ChromaAdapter
from src.models.memory import MemoryCreate, MemoryQuery, MemoryType, MemorySource


@pytest.fixture
def chroma_adapter():
    """创建 ChromaDB 适配器 (使用临时目录)"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        adapter = ChromaAdapter(
            persist_dir=tmp_dir,
            collection_name="test_memories",
            similarity_threshold=0.3,  # 降低阈值便于测试
        )
        
        yield adapter
        
        # 清理
        adapter._client = None


class TestChromaAdapter:
    """ChromaDB 适配器测试"""
    
    @pytest.mark.asyncio
    async def test_create_memory(self, chroma_adapter):
        """创建记忆"""
        memory = MemoryCreate(
            user_id="user1",
            content="测试记忆",
            memory_type=MemoryType.FACT,
        )
        
        created = await chroma_adapter.create_memory(memory)
        
        assert created.id.startswith("mem_")
        assert created.user_id == "user1"
        assert created.content == "测试记忆"
        assert created.memory_type == MemoryType.FACT
        assert created.source == MemorySource.LOCAL
    
    @pytest.mark.asyncio
    async def test_get_memory(self, chroma_adapter):
        """获取记忆"""
        # 创建
        memory = MemoryCreate(
            user_id="user1",
            content="获取测试",
            memory_type=MemoryType.EVENT,
        )
        created = await chroma_adapter.create_memory(memory)
        
        # 获取
        retrieved = await chroma_adapter.get_memory(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.content == "获取测试"
    
    @pytest.mark.asyncio
    async def test_get_memory_not_found(self, chroma_adapter):
        """获取不存在的记忆"""
        result = await chroma_adapter.get_memory("nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_memory(self, chroma_adapter):
        """更新记忆"""
        # 创建
        memory = MemoryCreate(
            user_id="user1",
            content="原始内容",
            memory_type=MemoryType.FACT,
        )
        created = await chroma_adapter.create_memory(memory)
        
        # 更新
        updated = await chroma_adapter.update_memory(
            created.id,
            {"content": "更新后的内容"},
        )
        
        assert updated is not None
        assert updated.content == "更新后的内容"
        assert updated.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_delete_memory(self, chroma_adapter):
        """删除记忆"""
        # 创建
        memory = MemoryCreate(
            user_id="user1",
            content="删除测试",
            memory_type=MemoryType.FACT,
        )
        created = await chroma_adapter.create_memory(memory)
        
        # 删除
        deleted = await chroma_adapter.delete_memory(created.id)
        assert deleted is True
        
        # 验证已删除
        retrieved = await chroma_adapter.get_memory(created.id)
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, chroma_adapter):
        """删除不存在的记忆"""
        result = await chroma_adapter.delete_memory("nonexistent")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_query_memories_basic(self, chroma_adapter):
        """基本查询"""
        # 创建多条记忆
        memories = [
            MemoryCreate(user_id="user1", content=f"记忆{i}", memory_type=MemoryType.FACT)
            for i in range(5)
        ]
        for m in memories:
            await chroma_adapter.create_memory(m)
        
        # 查询
        query = MemoryQuery(user_id="user1", limit=10)
        results = await chroma_adapter.query_memories(query)
        
        assert len(results) == 5
        assert all(r.user_id == "user1" for r in results)
    
    @pytest.mark.asyncio
    async def test_query_with_type_filter(self, chroma_adapter):
        """按类型过滤查询"""
        # 创建不同类型记忆
        await chroma_adapter.create_memory(
            MemoryCreate(user_id="user1", content="事实 1", memory_type=MemoryType.FACT)
        )
        await chroma_adapter.create_memory(
            MemoryCreate(user_id="user1", content="事件 1", memory_type=MemoryType.EVENT)
        )
        await chroma_adapter.create_memory(
            MemoryCreate(user_id="user1", content="事实 2", memory_type=MemoryType.FACT)
        )
        
        # 按类型查询
        query = MemoryQuery(user_id="user1", memory_type=MemoryType.FACT, limit=10)
        results = await chroma_adapter.query_memories(query)
        
        assert len(results) == 2
        assert all(r.memory_type == MemoryType.FACT for r in results)
    
    @pytest.mark.asyncio
    async def test_semantic_search(self, chroma_adapter):
        """语义搜索"""
        # 创建相关记忆
        await chroma_adapter.create_memory(
            MemoryCreate(user_id="user1", content="Python 编程语言很流行", memory_type=MemoryType.SKILL)
        )
        await chroma_adapter.create_memory(
            MemoryCreate(user_id="user1", content="Java 用于企业开发", memory_type=MemoryType.SKILL)
        )
        await chroma_adapter.create_memory(
            MemoryCreate(user_id="user1", content="JavaScript 用于网页开发", memory_type=MemoryType.SKILL)
        )
        
        # 语义搜索：编程相关
        query = MemoryQuery(user_id="user1", query="编程语言", limit=10)
        results = await chroma_adapter.query_memories(query)
        
        # 应该找到相关记忆
        assert len(results) >= 1
        # Python 记忆应该排第一 (最相关)
        assert "Python" in results[0].content or "编程" in results[0].content
    
    @pytest.mark.asyncio
    async def test_batch_create(self, chroma_adapter):
        """批量创建"""
        memories = [
            MemoryCreate(user_id="user1", content=f"批量{i}", memory_type=MemoryType.FACT)
            for i in range(10)
        ]
        
        created = await chroma_adapter.batch_create(memories)
        
        assert len(created) == 10
        assert all(c.id.startswith("mem_") for c in created)
        assert all(c.user_id == "user1" for c in created)
        
        # 验证都已存入
        query = MemoryQuery(user_id="user1", limit=20)
        results = await chroma_adapter.query_memories(query)
        assert len(results) == 10
    
    @pytest.mark.asyncio
    async def test_get_stats(self, chroma_adapter):
        """获取统计信息"""
        # 创建测试数据
        for i in range(5):
            await chroma_adapter.create_memory(
                MemoryCreate(user_id="user1", content=f"事实{i}", memory_type=MemoryType.FACT)
            )
        
        # 获取统计
        stats = await chroma_adapter.get_stats()
        
        assert stats["total_memories"] == 5
        assert stats["collection_name"] == "test_memories"
        assert "persist_dir" in stats
        assert "embedding_model" in stats
    
    @pytest.mark.asyncio
    async def test_health_check(self, chroma_adapter):
        """健康检查"""
        healthy = await chroma_adapter.health_check()
        assert healthy is True
    
    @pytest.mark.asyncio
    async def test_metadata_storage(self, chroma_adapter):
        """元数据存储"""
        memory = MemoryCreate(
            user_id="user1",
            content="带元数据的记忆",
            memory_type=MemoryType.FACT,
            metadata={"key": "value", "number": 42},
        )
        
        created = await chroma_adapter.create_memory(memory)
        retrieved = await chroma_adapter.get_memory(created.id)
        
        assert retrieved is not None
        assert retrieved.metadata is not None


class TestChromaAdapterSemantic:
    """语义搜索测试"""
    
    @pytest.mark.asyncio
    async def test_similarity_ranking(self, chroma_adapter):
        """相似度排序"""
        # 创建不同相关度的记忆
        await chroma_adapter.create_memory(
            MemoryCreate(user_id="user1", content="机器学习是人工智能的子集", memory_type=MemoryType.SKILL)
        )
        await chroma_adapter.create_memory(
            MemoryCreate(user_id="user1", content="深度学习需要大量数据", memory_type=MemoryType.SKILL)
        )
        await chroma_adapter.create_memory(
            MemoryCreate(user_id="user1", content="今天天气不错", memory_type=MemoryType.EVENT)
        )
        
        # 搜索 AI 相关
        query = MemoryQuery(user_id="user1", query="人工智能和机器学习", limit=10)
        results = await chroma_adapter.query_memories(query)
        
        # AI/ML 相关的应该排前面
        assert len(results) >= 2
        # 第一个应该是 ML 或 AI 相关
        first_content = results[0].content.lower()
        assert any(kw in first_content for kw in ["机器", "人工", "智能", "学习"])
    
    @pytest.mark.asyncio
    async def test_cross_user_isolation(self, chroma_adapter):
        """跨用户隔离"""
        # 用户 1 的记忆
        await chroma_adapter.create_memory(
            MemoryCreate(user_id="user1", content="用户 1 的秘密", memory_type=MemoryType.FACT)
        )
        
        # 用户 2 的记忆
        await chroma_adapter.create_memory(
            MemoryCreate(user_id="user2", content="用户 2 的秘密", memory_type=MemoryType.FACT)
        )
        
        # 用户 1 查询
        query1 = MemoryQuery(user_id="user1", query="秘密", limit=10)
        results1 = await chroma_adapter.query_memories(query1)
        
        # 用户 2 查询
        query2 = MemoryQuery(user_id="user2", query="秘密", limit=10)
        results2 = await chroma_adapter.query_memories(query2)
        
        # 应该只能看到自己的
        assert len(results1) == 1
        assert len(results2) == 1
        assert "用户 1" in results1[0].content
        assert "用户 2" in results2[0].content


class TestChromaAdapterPerformance:
    """性能测试"""
    
    @pytest.mark.asyncio
    async def test_insert_performance(self, chroma_adapter):
        """插入性能测试"""
        import time
        
        # 插入 20 条记录 (减少数量避免测试过慢)
        start = time.perf_counter()
        for i in range(20):
            await chroma_adapter.create_memory(
                MemoryCreate(user_id="user1", content=f"性能测试{i}", memory_type=MemoryType.FACT)
            )
        elapsed = time.perf_counter() - start
        
        # 20 条插入应在 10 秒内完成 (考虑嵌入生成)
        assert elapsed < 10.0
        print(f"\n插入 20 条记录耗时：{elapsed:.2f}秒 ({20/elapsed:.1f} 条/秒)")
    
    @pytest.mark.asyncio
    async def test_semantic_search_performance(self, chroma_adapter):
        """语义搜索性能测试"""
        import time
        
        # 准备数据
        for i in range(50):
            await chroma_adapter.create_memory(
                MemoryCreate(user_id="user1", content=f"搜索测试{i} 相关内容", memory_type=MemoryType.FACT)
            )
        
        # 语义搜索
        start = time.perf_counter()
        query = MemoryQuery(user_id="user1", query="相关内容", limit=10)
        results = await chroma_adapter.query_memories(query)
        elapsed = time.perf_counter() - start
        
        # 搜索应在 2 秒内完成 (考虑嵌入生成)
        assert elapsed < 2.0
        assert len(results) == 10
        print(f"\n语义搜索耗时：{elapsed*1000:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_batch_insert_performance(self, chroma_adapter):
        """批量插入性能测试"""
        import time
        
        # 批量插入 50 条
        memories = [
            MemoryCreate(user_id="user1", content=f"批量{i}", memory_type=MemoryType.FACT)
            for i in range(50)
        ]
        
        start = time.perf_counter()
        created = await chroma_adapter.batch_create(memories)
        elapsed = time.perf_counter() - start
        
        assert len(created) == 50
        # 50 条批量插入应在 10 秒内完成
        assert elapsed < 10.0
        print(f"\n批量插入 50 条记录耗时：{elapsed:.2f}秒 ({50/elapsed:.1f} 条/秒)")

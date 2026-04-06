"""
缓存层单元测试

测试覆盖：
- BaseCache 抽象基类
- MemoryCache (LRU)
- RedisCache (Mock)
- 缓存保护机制
- 缓存服务
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

from src.cache.base import BaseCache
from src.cache.memory_cache import MemoryCache
from src.cache.protection import (
    CacheWithProtection,
    AntiAvalancheCache,
    CacheChain,
)
from src.services.cache_service import CacheService


# ==================== BaseCache 测试 ====================

class MockCache(BaseCache):
    """用于测试的 Mock 缓存"""
    
    def __init__(self):
        self._data = {}
    
    async def get(self, key: str):
        return self._data.get(key)
    
    async def set(self, key: str, value, ttl=None):
        self._data[key] = value
        return True
    
    async def delete(self, key: str):
        if key in self._data:
            del self._data[key]
            return True
        return False
    
    async def exists(self, key: str):
        return key in self._data
    
    async def clear(self, pattern="*"):
        count = len(self._data)
        self._data.clear()
        return count
    
    async def get_stats(self):
        return {"size": len(self._data)}


class TestBaseCache:
    """BaseCache 抽象基类测试"""
    
    def test_base_cache_is_abstract(self):
        """BaseCache 是抽象类，不能直接实例化"""
        with pytest.raises(TypeError):
            BaseCache()
    
    def test_mock_cache_implementation(self):
        """Mock 缓存实现可以正常工作"""
        cache = MockCache()
        assert isinstance(cache, BaseCache)
    
    @pytest.mark.asyncio
    async def test_mock_cache_crud(self):
        """Mock 缓存 CRUD 操作"""
        cache = MockCache()
        
        # Set
        assert await cache.set("key1", "value1")
        
        # Get
        assert await cache.get("key1") == "value1"
        
        # Exists
        assert await cache.exists("key1")
        assert not await cache.exists("key2")
        
        # Delete
        assert await cache.delete("key1")
        assert not await cache.exists("key1")
        
        # Clear
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        count = await cache.clear()
        assert count == 2
        assert await cache.get_stats() == {"size": 0}


# ==================== MemoryCache 测试 ====================

class TestMemoryCache:
    """MemoryCache (LRU) 测试"""
    
    @pytest.fixture
    def cache(self):
        """创建测试缓存"""
        return MemoryCache(max_size=5, default_ttl=60)
    
    @pytest.mark.asyncio
    async def test_set_and_get(self, cache):
        """基本设置和获取"""
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent(self, cache):
        """获取不存在的键"""
        result = await cache.get("nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        """TTL 过期测试"""
        cache = MemoryCache(max_size=5, default_ttl=1)
        
        await cache.set("key1", "value1", ttl=1)
        assert await cache.get("key1") == "value1"
        
        # 等待过期
        await asyncio.sleep(1.1)
        
        assert await cache.get("key1") is None
    
    @pytest.mark.asyncio
    async def test_lru_eviction(self, cache):
        """LRU 驱逐测试"""
        # 填满缓存
        for i in range(5):
            await cache.set(f"key{i}", f"value{i}")
        
        # 添加新条目，应该驱逐最旧的
        await cache.set("key5", "value5")
        
        # key0 应该被驱逐
        assert await cache.get("key0") is None
        assert await cache.get("key5") == "value5"
    
    @pytest.mark.asyncio
    async def test_lru_update_access_order(self, cache):
        """LRU 更新访问顺序"""
        # 添加
        for i in range(5):
            await cache.set(f"key{i}", f"value{i}")
        
        # 访问 key0，移到末尾
        await cache.get("key0")
        
        # 添加新条目，应该驱逐 key1 (现在最旧)
        await cache.set("key5", "value5")
        
        assert await cache.get("key0") == "value0"  # 还在
        assert await cache.get("key1") is None  # 被驱逐
    
    @pytest.mark.asyncio
    async def test_delete(self, cache):
        """删除测试"""
        await cache.set("key1", "value1")
        assert await cache.delete("key1")
        assert await cache.get("key1") is None
        assert not await cache.delete("key1")  # 再次删除返回 False
    
    @pytest.mark.asyncio
    async def test_clear_all(self, cache):
        """清除所有"""
        for i in range(3):
            await cache.set(f"key{i}", f"value{i}")
        
        count = await cache.clear()
        assert count == 3
        assert len(cache) == 0
    
    @pytest.mark.asyncio
    async def test_clear_pattern(self, cache):
        """按模式清除"""
        await cache.set("user:1:name", "Alice")
        await cache.set("user:1:age", "25")
        await cache.set("user:2:name", "Bob")
        await cache.set("query:123", "result")
        
        # 清除所有 user:1:*
        count = await cache.clear("user:1:*")
        assert count == 2
        
        # 检查
        assert await cache.get("user:1:name") is None
        assert await cache.get("user:2:name") == "Bob"
    
    @pytest.mark.asyncio
    async def test_exists(self, cache):
        """存在性检查"""
        await cache.set("key1", "value1")
        assert await cache.exists("key1")
        assert not await cache.exists("key2")
    
    @pytest.mark.asyncio
    async def test_stats(self, cache):
        """统计信息"""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.get("key1")  # hit
        await cache.get("key3")  # miss
        
        stats = await cache.get_stats()
        
        assert stats["type"] == "memory"
        assert stats["max_size"] == 5
        assert stats["current_size"] == 2
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["sets"] == 2
        assert "hit_rate" in stats
    
    @pytest.mark.asyncio
    async def test_never_expire(self, cache):
        """永不过期 (ttl=0)"""
        await cache.set("key1", "value1", ttl=0)
        
        # 等待一段时间
        await asyncio.sleep(0.1)
        
        assert await cache.get("key1") == "value1"
    
    @pytest.mark.asyncio
    async def test_concurrent_access(self, cache):
        """并发访问测试"""
        async def worker(i):
            await cache.set(f"key{i}", f"value{i}")
            return await cache.get(f"key{i}")
        
        tasks = [worker(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        assert all(r == f"value{i}" for i, r in enumerate(results))
    
    @pytest.mark.asyncio
    async def test_repr(self, cache):
        """字符串表示"""
        await cache.set("key1", "value1")
        repr_str = repr(cache)
        assert "MemoryCache" in repr_str
        assert "max_size=5" in repr_str


# ==================== CacheWithProtection 测试 ====================

class TestCacheWithProtection:
    """CacheWithProtection 测试"""
    
    @pytest.fixture
    def mock_cache(self):
        """创建 Mock 缓存"""
        return MockCache()
    
    @pytest.fixture
    def protected_cache(self, mock_cache):
        """创建带保护的缓存"""
        return CacheWithProtection(mock_cache, null_cache_ttl=60)
    
    @pytest.mark.asyncio
    async def test_bloom_filter_prevents_miss(self, protected_cache):
        """布隆过滤器阻止未命中的查询"""
        # 未添加到布隆过滤器的键，直接返回 None
        result = await protected_cache.get("nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_set_adds_to_bloom_filter(self, protected_cache):
        """设置自动添加到布隆过滤器"""
        await protected_cache.set("key1", "value1")
        
        # 现在可以获取到
        result = await protected_cache.get("key1")
        assert result == "value1"
    
    @pytest.mark.asyncio
    async def test_null_value_caching(self, protected_cache):
        """空值缓存"""
        # 设置 None 值
        await protected_cache.set("key1", None)
        
        # 获取应该返回 None，但不是因为未命中
        result = await protected_cache.get("key1")
        assert result is None
        
        # 检查底层缓存是否有空值标记
        raw_value = await protected_cache.cache.get("key1")
        assert raw_value == "__NULL__"
    
    @pytest.mark.asyncio
    async def test_stats_include_protection(self, protected_cache):
        """统计信息包含保护机制"""
        await protected_cache.set("key1", "value1")
        await protected_cache.get("key1")  # hit
        await protected_cache.get("nonexistent")  # bloom miss
        
        stats = await protected_cache.get_stats()
        
        assert "protection" in stats
        assert "bloom_filter_hits" in stats["protection"]
        assert "bloom_filter_misses" in stats["protection"]


# ==================== AntiAvalancheCache 测试 ====================

class TestAntiAvalancheCache:
    """AntiAvalancheCache 测试"""
    
    @pytest.fixture
    def mock_cache(self):
        """创建 Mock 缓存"""
        return MockCache()
    
    @pytest.fixture
    def anti_avalanche_cache(self, mock_cache):
        """创建防雪崩缓存"""
        return AntiAvalancheCache(
            mock_cache,
            hot_threshold=5,  # 降低阈值便于测试
            hot_ttl_multiplier=2.0,
        )
    
    @pytest.mark.asyncio
    async def test_hot_key_detection(self, anti_avalanche_cache):
        """热点数据检测"""
        # 访问多次
        for _ in range(5):
            await anti_avalanche_cache.get("hot_key")
        
        # 检查统计
        stats = await anti_avalanche_cache.get_stats()
        assert stats["anti_avalanche"]["hot_keys_count"] >= 1
    
    @pytest.mark.asyncio
    async def test_hot_key_extended_ttl(self, anti_avalanche_cache):
        """热点数据延长 TTL"""
        # 先访问多次使其成为热点
        for _ in range(5):
            await anti_avalanche_cache.get("hot_key")
        
        # 设置 TTL
        with patch.object(anti_avalanche_cache.cache, 'set') as mock_set:
            mock_set.return_value = True
            await anti_avalanche_cache.set("hot_key", "value", ttl=100)
            
            # 验证 TTL 被延长
            mock_set.assert_called_once()
            call_args = mock_set.call_args
            assert call_args[0][2] == 200  # 100 * 2.0


# ==================== CacheChain 测试 ====================

class TestCacheChain:
    """CacheChain (多级缓存) 测试"""
    
    @pytest.fixture
    def l1_cache(self):
        return MemoryCache(max_size=10)
    
    @pytest.fixture
    def l2_cache(self):
        return MemoryCache(max_size=100)
    
    @pytest.fixture
    def cache_chain(self, l1_cache, l2_cache):
        return CacheChain([l1_cache, l2_cache])
    
    @pytest.mark.asyncio
    async def test_chain_get_from_l1(self, cache_chain, l1_cache, l2_cache):
        """从 L1 获取"""
        # 同时在 L1 和 L2 设置
        await l1_cache.set("key1", "value1")
        await l2_cache.set("key1", "value1")
        
        result = await cache_chain.get("key1")
        assert result == "value1"
    
    @pytest.mark.asyncio
    async def test_chain_get_from_l2_and_write_through(self, cache_chain, l1_cache, l2_cache):
        """从 L2 获取并写回 L1"""
        # 只在 L2 设置
        await l2_cache.set("key2", "value2")
        
        # 从链获取
        result = await cache_chain.get("key2")
        assert result == "value2"
        
        # 验证 L1 现在也有了 (write-through)
        assert await l1_cache.get("key2") == "value2"
    
    @pytest.mark.asyncio
    async def test_chain_miss(self, cache_chain):
        """缓存未命中"""
        result = await cache_chain.get("nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_chain_set_all_levels(self, cache_chain, l1_cache, l2_cache):
        """设置到所有层级"""
        await cache_chain.set("key1", "value1")
        
        assert await l1_cache.get("key1") == "value1"
        assert await l2_cache.get("key1") == "value1"
    
    @pytest.mark.asyncio
    async def test_chain_stats(self, cache_chain, l1_cache, l2_cache):
        """链统计信息"""
        await l1_cache.set("key1", "value1")
        await l2_cache.set("key2", "value2")
        
        await cache_chain.get("key1")  # L1 hit
        await cache_chain.get("key2")  # L2 hit
        await cache_chain.get("key3")  # miss
        
        stats = await cache_chain.get_stats()
        
        assert stats["type"] == "cache_chain"
        assert stats["levels"] == 2
        assert stats["l1_hits"] == 1
        assert stats["l2_hits"] == 1
        assert stats["misses"] == 1


# ==================== CacheService 测试 ====================

class TestCacheService:
    """CacheService 测试"""
    
    @pytest.fixture
    def cache_service(self):
        """创建缓存服务 (不使用 Redis)"""
        return CacheService(
            use_redis=False,
            enable_protection=True,
            enable_anti_avalanche=True,
        )
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, cache_service):
        """服务初始化"""
        await cache_service.initialize()
        assert cache_service._initialized
    
    @pytest.mark.asyncio
    async def test_service_crud(self, cache_service):
        """服务 CRUD 操作"""
        await cache_service.initialize()
        
        # Set
        await cache_service.set("key1", "value1")
        
        # Get
        result = await cache_service.get("key1")
        assert result == "value1"
        
        # Delete
        await cache_service.delete("key1")
        assert await cache_service.get("key1") is None
    
    @pytest.mark.asyncio
    async def test_query_key_generation(self, cache_service):
        """查询键生成"""
        await cache_service.initialize()
        
        key = cache_service._make_query_key(
            user_id="user123",
            query="test",
            memory_type="preference",
            source="memobase",
            limit=10,
        )
        
        assert key.startswith("query:")
        assert "user123" in key
        assert "preference" in key
    
    @pytest.mark.asyncio
    async def test_memory_key_generation(self, cache_service):
        """记忆键生成"""
        await cache_service.initialize()
        
        key = cache_service._make_memory_key("mem_123")
        assert key == "memory:mem_123"
    
    @pytest.mark.asyncio
    async def test_invalidate_user_cache(self, cache_service):
        """失效用户缓存"""
        await cache_service.initialize()
        
        # 设置一些查询缓存
        await cache_service.set_query("query:user123:abc", "result1")
        await cache_service.set_query("query:user123:def", "result2")
        await cache_service.set_query("query:user456:abc", "result3")
        
        # 失效 user123 的缓存
        count = await cache_service.invalidate_user_cache("user123")
        assert count == 2
        
        # user456 的不受影响
        assert await cache_service.get_query("query:user456:abc") == "result3"
    
    @pytest.mark.asyncio
    async def test_invalidate_memory_cache(self, cache_service):
        """失效记忆缓存"""
        await cache_service.initialize()
        
        await cache_service.set_memory("mem_123", {"content": "test"})
        result = await cache_service.invalidate_memory_cache("mem_123")
        assert result
        assert await cache_service.get_memory("mem_123") is None
    
    @pytest.mark.asyncio
    async def test_warmup_query(self, cache_service):
        """预热查询缓存"""
        await cache_service.initialize()
        
        result = await cache_service.warmup_query(
            user_id="user123",
            query="test",
            memory_type="preference",
            source="memobase",
            limit=10,
            value=["result1", "result2"],
        )
        
        assert result
        
        # 验证可以获取
        key = cache_service._make_query_key(
            "user123", "test", "preference", "memobase", 10
        )
        assert await cache_service.get_query(key) == ["result1", "result2"]
    
    @pytest.mark.asyncio
    async def test_service_stats(self, cache_service):
        """服务统计"""
        await cache_service.initialize()
        
        await cache_service.set("key1", "value1")
        await cache_service.get("key1")
        
        stats = await cache_service.get_stats()
        assert stats is not None
    
    @pytest.mark.asyncio
    async def test_service_close(self, cache_service):
        """服务关闭"""
        await cache_service.initialize()
        await cache_service.close()
        assert not cache_service._initialized


# ==================== 集成测试 ====================

class TestCacheIntegration:
    """缓存集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """完整工作流测试"""
        # 创建缓存服务
        service = CacheService(use_redis=False)
        await service.initialize()
        
        # 1. 设置记忆缓存
        memory_id = "mem_test_123"
        memory_data = {
            "id": memory_id,
            "content": "Test memory",
            "type": "fact",
        }
        await service.set_memory(memory_id, memory_data)
        
        # 2. 获取记忆缓存
        result = await service.get_memory(memory_id)
        assert result == memory_data
        
        # 3. 设置查询缓存
        query_key = service._make_query_key(
            user_id="user123",
            query="test",
            memory_type="fact",
            source="local",
            limit=10,
        )
        query_result = [memory_data]
        await service.set_query(query_key, query_result)
        
        # 4. 获取查询缓存
        result = await service.get_query(query_key)
        assert result == query_result
        
        # 5. 更新记忆，失效用户缓存
        await service.invalidate_user_cache("user123")
        assert await service.get_query(query_key) is None
        
        # 6. 删除记忆
        await service.invalidate_memory_cache(memory_id)
        assert await service.get_memory(memory_id) is None
        
        # 7. 关闭服务
        await service.close()

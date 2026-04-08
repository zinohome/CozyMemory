"""
CozyMemory 核心测试
"""

import pytest
from cozy_memory.models import MemoryCreate, MemoryQuery, MemoryType, Config, EngineConfig
from cozy_memory.adapters.memobase import MemobaseAdapter
from cozy_memory.adapters.mem0 import Mem0Adapter
from cozy_memory.router import Router
from cozy_memory.cache import Cache


class TestModels:
    """模型测试"""
    
    def test_memory_create(self):
        """创建记忆模型"""
        memory = MemoryCreate(
            user_id="user1",
            content="测试内容",
            memory_type=MemoryType.FACT,
        )
        
        assert memory.user_id == "user1"
        assert memory.content == "测试内容"
        assert memory.memory_type == MemoryType.FACT
    
    def test_memory_query(self):
        """查询模型"""
        query = MemoryQuery(
            user_id="user1",
            query="测试查询",
            limit=20,
        )
        
        assert query.user_id == "user1"
        assert query.query == "测试查询"
        assert query.limit == 20
    
    def test_config_from_dict(self):
        """配置创建"""
        config = Config(
            engines={
                "memobase": EngineConfig(enabled=True, api_url="http://localhost:8000"),
                "mem0": EngineConfig(enabled=True, api_key="test-key"),
            },
            router={"default_engine": "memobase"},
        )
        
        assert config.engines["memobase"].enabled is True
        assert config.engines["mem0"].api_key == "test-key"
        assert config.router.default_engine == "memobase"


class TestRouter:
    """路由测试"""
    
    @pytest.fixture
    def router(self):
        """创建路由器"""
        # Mock 适配器
        class MockAdapter:
            def __init__(self, name):
                self.name = name
        
        adapters = {
            "memobase": MockAdapter("memobase"),
            "mem0": MockAdapter("mem0"),
        }
        
        return Router(adapters, default_engine="memobase")
    
    def test_detect_intent_preference(self, router):
        """检测偏好意图"""
        intent, confidence = router.detect_intent("我喜欢 Python 编程")
        assert intent == "preference"
    
    def test_detect_intent_fact(self, router):
        """检测事实意图"""
        intent, confidence = router.detect_intent("我知道地球是圆的")
        assert intent == "fact"
    
    def test_select_engine_default(self, router):
        """默认引擎选择"""
        query = MemoryQuery(user_id="user1")
        engine = router.select_engine(query)
        assert engine == "memobase"
    
    def test_select_engine_by_intent(self, router):
        """按意图选择引擎"""
        query = MemoryQuery(user_id="user1", query="我喜欢什么")
        engine = router.select_engine(query)
        assert engine in ["mem0", "memobase"]
    
    def test_select_engine_specified(self, router):
        """用户指定引擎"""
        query = MemoryQuery(user_id="user1", engine="mem0")
        engine = router.select_engine(query)
        assert engine == "mem0"


class TestCache:
    """缓存测试"""
    
    @pytest.mark.asyncio
    async def test_cache_set_get(self):
        """缓存设置和获取"""
        cache = Cache(ttl=60)
        
        query = MemoryQuery(user_id="user1", query="测试")
        memories = []  # Mock 数据
        
        # 设置缓存
        await cache.set(query, memories)
        
        # 获取缓存
        result = await cache.get(query)
        assert result == memories
    
    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """缓存未命中"""
        cache = Cache(ttl=60)
        
        query = MemoryQuery(user_id="user1", query="不存在的查询")
        result = await cache.get(query)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_stats(self):
        """缓存统计"""
        cache = Cache(ttl=60, max_size=100)
        
        stats = await cache.get_stats()
        
        assert stats["ttl"] == 60
        assert stats["max_size"] == 100
        assert "size" in stats
    
    @pytest.mark.asyncio
    async def test_cache_clear(self):
        """清空缓存"""
        cache = Cache(ttl=60)
        
        # 添加数据
        query = MemoryQuery(user_id="user1", query="测试")
        await cache.set(query, [])
        
        # 清空
        await cache.clear()
        
        stats = await cache.get_stats()
        assert stats["size"] == 0


class TestIntegration:
    """集成测试"""
    
    def test_import_main_class(self):
        """导入主类"""
        from cozy_memory import CozyMemory
        
        assert CozyMemory is not None
    
    def test_create_instance(self):
        """创建实例"""
        from cozy_memory import CozyMemory
        
        cm = CozyMemory()
        assert cm is not None
        assert len(cm.adapters) == 0
    
    def test_add_adapter(self):
        """添加适配器"""
        from cozy_memory import CozyMemory, MemobaseAdapter
        
        cm = CozyMemory()
        
        # 添加 Mock 适配器
        class MockAdapter:
            pass
        
        cm.add_adapter("mock", MockAdapter())
        assert "mock" in cm.adapters

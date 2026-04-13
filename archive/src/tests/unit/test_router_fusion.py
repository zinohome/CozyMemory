"""
路由层和融合层单元测试

测试覆盖:
- 路由层 (Intent, RoundRobin, Weighted)
- 融合层 (RRF, Weighted)
- 服务层 (RouterService, FusionService)
"""

import pytest
from typing import Dict, List, Any

from src.routers.base import BaseRouter, RouterStrategy
from src.routers.intent_router import IntentRouter
from src.routers.round_robin_router import RoundRobinRouter
from src.routers.weighted_router import WeightedRouter
from src.services.router_service import RouterService

from src.fusion.base import BaseFusion
from src.fusion.rrf_fusion import RRFFusion
from src.fusion.weighted_fusion import WeightedFusion
from src.services.fusion_service import FusionService


# ==================== 路由层测试 ====================

class TestIntentRouter:
    """意图识别路由测试"""
    
    @pytest.fixture
    def router(self):
        return IntentRouter()
    
    @pytest.mark.asyncio
    async def test_route_by_memory_type(self, router):
        """通过记忆类型路由"""
        engines = ["memobase", "local", "vector"]
        
        result = await router.route(
            user_id="user1",
            query="test",
            memory_type="preference",
            source=None,
            available_engines=engines,
        )
        
        # preference 应该优先 local
        assert result[0] == "local"
    
    @pytest.mark.asyncio
    async def test_route_by_query_keywords(self, router):
        """通过查询关键词路由"""
        engines = ["memobase", "local", "vector"]
        
        # "喜欢" 关键词 → preference
        result = await router.route(
            user_id="user1",
            query="我喜欢什么",
            memory_type=None,
            source=None,
            available_engines=engines,
        )
        
        assert result[0] == "local"
    
    @pytest.mark.asyncio
    async def test_route_default_to_fact(self, router):
        """默认路由到 fact"""
        engines = ["memobase", "local", "vector"]
        
        result = await router.route(
            user_id="user1",
            query="随机查询",
            memory_type=None,
            source=None,
            available_engines=engines,
        )
        
        # fact 优先 memobase
        assert result[0] == "memobase"
    
    @pytest.mark.asyncio
    async def test_route_filter_unavailable_engines(self, router):
        """过滤不可用引擎"""
        engines = ["local"]  # 只有 local
        
        result = await router.route(
            user_id="user1",
            query="test",
            memory_type="fact",
            source=None,
            available_engines=engines,
        )
        
        assert result == ["local"]
    
    @pytest.mark.asyncio
    async def test_route_empty_engines(self, router):
        """空引擎列表"""
        result = await router.route(
            user_id="user1",
            query="test",
            memory_type=None,
            source=None,
            available_engines=[],
        )
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_stats(self, router):
        """统计信息"""
        engines = ["memobase", "local"]
        
        await router.route("user1", "什么是 AI", None, None, engines)
        await router.route("user1", "我喜欢什么", None, None, engines)
        
        stats = await router.get_stats()
        
        assert stats["type"] == "intent"
        assert stats["total_requests"] == 2
        assert "fact" in stats["intent_distribution"]
        assert "preference" in stats["intent_distribution"]


class TestRoundRobinRouter:
    """轮询路由测试"""
    
    @pytest.fixture
    def router(self):
        return RoundRobinRouter()
    
    @pytest.mark.asyncio
    async def test_round_robin_distribution(self, router):
        """轮询分布测试"""
        engines = ["engine1", "engine2", "engine3"]
        
        # 多次路由
        results = []
        for _ in range(6):
            result = await router.route(
                user_id="user1",
                query="test",
                memory_type=None,
                source=None,
                available_engines=engines,
            )
            results.append(result[0])
        
        # 每个引擎应该被选择 2 次
        assert results.count("engine1") == 2
        assert results.count("engine2") == 2
        assert results.count("engine3") == 2
    
    @pytest.mark.asyncio
    async def test_round_robin_empty_engines(self, router):
        """空引擎列表"""
        result = await router.route(
            user_id="user1",
            query="test",
            memory_type=None,
            source=None,
            available_engines=[],
        )
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_round_robin_stats(self, router):
        """统计信息"""
        engines = ["engine1", "engine2"]
        
        for _ in range(4):
            await router.route("user1", "test", None, None, engines)
        
        stats = await router.get_stats()
        
        assert stats["type"] == "round_robin"
        assert stats["total_requests"] == 4
        assert stats["balance_score"] == 100.0  # 完全均衡
    
    @pytest.mark.asyncio
    async def test_round_robin_reset(self, router):
        """重置计数器"""
        engines = ["engine1", "engine2"]
        
        await router.route("user1", "test", None, None, engines)
        await router.reset()
        
        stats = await router.get_stats()
        assert stats["current_counter"] == 0


class TestWeightedRouter:
    """权重路由测试"""
    
    @pytest.fixture
    def router(self):
        return WeightedRouter(
            default_weights={"memobase": 1.0, "local": 0.5, "vector": 0.3},
        )
    
    @pytest.mark.asyncio
    async def test_weighted_primary_selection(self, router):
        """权重选择主引擎"""
        engines = ["memobase", "local", "vector"]
        
        # 多次路由，memobase 应该被选中最多次
        results = []
        for _ in range(100):
            result = await router.route(
                user_id="user1",
                query="test",
                memory_type=None,
                source=None,
                available_engines=engines,
            )
            results.append(result[0])
        
        # memobase 权重最高，应该被选中最多
        assert results.count("memobase") > results.count("local")
        assert results.count("memobase") > results.count("vector")
    
    @pytest.mark.asyncio
    async def test_weighted_set_weight(self, router):
        """手动设置权重"""
        await router.set_weight("local", 2.0)
        
        stats = await router.get_stats()
        assert stats["current_weights"]["local"] == 2.0
    
    @pytest.mark.asyncio
    async def test_weighted_reset_weights(self, router):
        """重置权重"""
        await router.set_weight("local", 2.0)
        await router.reset_weights()
        
        stats = await router.get_stats()
        assert stats["current_weights"]["local"] == 0.5
    
    @pytest.mark.asyncio
    async def test_weighted_record_performance(self, router):
        """记录性能"""
        await router.record_performance("memobase", latency=0.05, success=True)
        await router.record_performance("memobase", latency=0.1, success=True)
        
        stats = await router.get_stats()
        perf = stats["performance_stats"]["memobase"]
        
        assert perf["total_requests"] == 2
        assert perf["success_count"] == 2
    
    @pytest.mark.asyncio
    async def test_weighted_empty_engines(self, router):
        """空引擎列表"""
        result = await router.route(
            user_id="user1",
            query="test",
            memory_type=None,
            source=None,
            available_engines=[],
        )
        
        assert result == []


class TestRouterService:
    """路由服务测试"""
    
    @pytest.fixture
    def service(self):
        return RouterService()
    
    @pytest.mark.asyncio
    async def test_service_route(self, service):
        """服务路由"""
        engines = ["memobase", "local", "vector"]
        
        result = await service.route(
            user_id="user1",
            query="test",
            memory_type=None,
            source=None,
            available_engines=engines,
        )
        
        assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_service_switch_strategy(self, service):
        """切换策略"""
        await service.switch_strategy(RouterStrategy.ROUND_ROBIN)
        
        stats = await service.get_stats()
        assert stats["current_strategy"] == "round_robin"
    
    @pytest.mark.asyncio
    async def test_service_get_all_stats(self, service):
        """获取所有统计"""
        all_stats = await service.get_all_stats()
        
        assert "intent" in all_stats
        assert "round_robin" in all_stats
        assert "weighted" in all_stats
    
    @pytest.mark.asyncio
    async def test_service_invalid_strategy(self, service):
        """无效策略"""
        with pytest.raises(ValueError):
            await service.switch_strategy(RouterStrategy("invalid"))


# ==================== 融合层测试 ====================

class TestRRFFusion:
    """RRF 融合测试"""
    
    @pytest.fixture
    def fusion(self):
        return RRFFusion(k=60)
    
    @pytest.mark.asyncio
    async def test_rrf_fuse_basic(self, fusion):
        """基本融合"""
        results = {
            "engine1": [
                {"id": "1", "content": "A"},
                {"id": "2", "content": "B"},
            ],
            "engine2": [
                {"id": "2", "content": "B"},
                {"id": "3", "content": "C"},
            ],
        }
        
        fused = await fusion.fuse(results, limit=3)
        
        # 应该返回 3 个结果
        assert len(fused) == 3
        
        # id=2 在两个引擎都出现，应该排名更高
        assert fused[0]["id"] == "2"
    
    @pytest.mark.asyncio
    async def test_rrf_fuse_empty_results(self, fusion):
        """空结果"""
        fused = await fusion.fuse({}, limit=10)
        assert fused == []
    
    @pytest.mark.asyncio
    async def test_rrf_fuse_deduplication(self, fusion):
        """去重"""
        results = {
            "engine1": [
                {"id": "1", "content": "A"},
                {"id": "1", "content": "A"},  # 重复
            ],
        }
        
        fused = await fusion.fuse(results, limit=10)
        
        # 应该去重
        assert len(fused) == 1
        assert fused[0]["id"] == "1"
    
    @pytest.mark.asyncio
    async def test_rrf_fuse_limit(self, fusion):
        """限制数量"""
        results = {
            "engine1": [{"id": str(i)} for i in range(20)],
            "engine2": [{"id": str(i)} for i in range(10, 30)],
        }
        
        fused = await fusion.fuse(results, limit=5)
        
        assert len(fused) == 5
    
    @pytest.mark.asyncio
    async def test_rrf_stats(self, fusion):
        """统计信息"""
        results = {
            "engine1": [{"id": "1"}, {"id": "2"}],
            "engine2": [{"id": "2"}, {"id": "3"}],
        }
        
        await fusion.fuse(results)
        await fusion.fuse(results)
        
        stats = await fusion.get_stats()
        
        assert stats["type"] == "rrf"
        assert stats["total_fusions"] == 2
        assert stats["k"] == 60


class TestWeightedFusion:
    """权重融合测试"""
    
    @pytest.fixture
    def fusion(self):
        return WeightedFusion(
            engine_weights={"memobase": 1.0, "local": 0.5, "vector": 0.3},
        )
    
    @pytest.mark.asyncio
    async def test_weighted_fuse_basic(self, fusion):
        """基本融合"""
        results = {
            "memobase": [
                {"id": "1", "score": 0.9},
                {"id": "2", "score": 0.7},
            ],
            "local": [
                {"id": "2", "score": 0.8},
                {"id": "3", "score": 0.6},
            ],
        }
        
        fused = await fusion.fuse(results, limit=3)
        
        assert len(fused) == 3
        
        # memobase 权重高，id=1 应该排第一
        assert fused[0]["id"] == "1"
    
    @pytest.mark.asyncio
    async def test_weighted_fuse_without_scores(self, fusion):
        """无分数结果"""
        fusion_no_score = WeightedFusion(use_result_score=False)
        
        results = {
            "engine1": [{"id": "1"}, {"id": "2"}],
            "engine2": [{"id": "2"}, {"id": "3"}],
        }
        
        fused = await fusion_no_score.fuse(results, limit=3)
        
        assert len(fused) == 3
    
    @pytest.mark.asyncio
    async def test_weighted_set_engine_weight(self, fusion):
        """设置引擎权重"""
        await fusion.set_engine_weight("local", 2.0)
        
        stats = await fusion.get_stats()
        assert stats["engine_weights"]["local"] == 2.0
    
    @pytest.mark.asyncio
    async def test_weighted_stats(self, fusion):
        """统计信息"""
        results = {
            "memobase": [{"id": "1", "score": 0.9}],
            "local": [{"id": "2", "score": 0.8}],
        }
        
        await fusion.fuse(results)
        
        stats = await fusion.get_stats()
        
        assert stats["type"] == "weighted"
        assert stats["engine_weights"]["memobase"] == 1.0


class TestFusionService:
    """融合服务测试"""
    
    @pytest.fixture
    def service(self):
        return FusionService()
    
    @pytest.mark.asyncio
    async def test_service_fuse(self, service):
        """服务融合"""
        results = {
            "engine1": [{"id": "1", "content": "A"}],
            "engine2": [{"id": "2", "content": "B"}],
        }
        
        fused = await service.fuse(results, limit=10)
        
        assert len(fused) == 2
    
    @pytest.mark.asyncio
    async def test_service_switch_strategy(self, service):
        """切换策略"""
        await service.switch_strategy("weighted")
        
        stats = await service.get_stats()
        assert stats["current_strategy"] == "weighted"
    
    @pytest.mark.asyncio
    async def test_service_deduplicate(self, service):
        """去重"""
        results = [
            {"id": "1", "content": "A"},
            {"id": "1", "content": "A"},
            {"id": "2", "content": "B"},
        ]
        
        deduped = service.deduplicate(results)
        
        assert len(deduped) == 2
    
    @pytest.mark.asyncio
    async def test_service_invalid_strategy(self, service):
        """无效策略"""
        with pytest.raises(ValueError):
            await service.switch_strategy("invalid")


# ==================== 集成测试 ====================

class TestRouterFusionIntegration:
    """路由 + 融合集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """完整工作流"""
        # 初始化服务
        router_service = RouterService()
        fusion_service = FusionService()
        
        # 1. 路由
        engines = ["memobase", "local", "vector"]
        routed = await router_service.route(
            user_id="user1",
            query="什么是 AI",
            memory_type=None,
            source=None,
            available_engines=engines,
        )
        
        assert len(routed) > 0
        
        # 2. 模拟引擎查询结果
        engine_results = {
            "memobase": [
                {"id": "mem_1", "content": "AI 定义", "score": 0.9},
                {"id": "mem_2", "content": "AI 历史", "score": 0.7},
            ],
            "local": [
                {"id": "loc_1", "content": "AI 应用", "score": 0.8},
            ],
            "vector": [
                {"id": "vec_1", "content": "AI 技术", "score": 0.6},
            ],
        }
        
        # 3. 融合
        fused = await fusion_service.fuse(engine_results, limit=5)
        
        assert len(fused) <= 5
        
        # 4. 验证去重
        ids = [r["id"] for r in fused]
        assert len(ids) == len(set(ids))
        
        # 5. 关闭服务
        await router_service.close()
        await fusion_service.close()

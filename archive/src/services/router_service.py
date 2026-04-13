"""
CozyMemory 路由服务

提供统一的路由管理服务，支持：
- 多路由策略
- 路由统计
- 动态切换
"""

from typing import Any, Dict, List, Optional
from structlog import get_logger

from ..routers.base import BaseRouter, RouterStrategy
from ..routers.intent_router import IntentRouter
from ..routers.round_robin_router import RoundRobinRouter
from ..routers.weighted_router import WeightedRouter
from ..utils.config import settings

logger = get_logger(__name__)


class RouterService:
    """
    路由服务
    
    提供统一的路由管理接口，支持多种路由策略。
    
    架构:
        RouterService
        ├── IntentRouter (意图识别)
        ├── RoundRobinRouter (轮询)
        └── WeightedRouter (权重)
    
    特性:
    - 策略动态切换
    - 统计监控
    - 自动降级
    """
    
    def __init__(self):
        self._routers: Dict[RouterStrategy, BaseRouter] = {
            RouterStrategy.INTENT: IntentRouter(),
            RouterStrategy.ROUND_ROBIN: RoundRobinRouter(),
            RouterStrategy.WEIGHTED: WeightedRouter(),
        }
        
        # 当前策略
        self._current_strategy = self._parse_strategy(settings.ROUTER_STRATEGY)
        
        self._stats = {
            "total_requests": 0,
            "strategy_switches": 0,
        }
        
        logger.info(
            "router_service_initialized",
            current_strategy=self._current_strategy.value,
        )
    
    def _parse_strategy(self, strategy_str: str) -> RouterStrategy:
        """解析路由策略"""
        try:
            return RouterStrategy(strategy_str)
        except ValueError:
            logger.warning("invalid_strategy", strategy=strategy_str, fallback="intent")
            return RouterStrategy.INTENT
    
    async def route(
        self,
        user_id: str,
        query: Optional[str],
        memory_type: Optional[str],
        source: Optional[str],
        available_engines: List[str],
    ) -> List[str]:
        """
        路由决策
        
        使用当前策略进行路由
        """
        self._stats["total_requests"] += 1
        
        router = self._routers[self._current_strategy]
        
        result = await router.route(
            user_id=user_id,
            query=query,
            memory_type=memory_type,
            source=source,
            available_engines=available_engines,
        )
        
        logger.debug(
            "routing_completed",
            strategy=self._current_strategy.value,
            result=result,
        )
        
        return result
    
    async def switch_strategy(self, strategy: RouterStrategy) -> None:
        """切换路由策略"""
        if strategy not in self._routers:
            logger.error("invalid_strategy", strategy=strategy.value)
            raise ValueError(f"Invalid strategy: {strategy.value}")
        
        old_strategy = self._current_strategy
        self._current_strategy = strategy
        self._stats["strategy_switches"] += 1
        
        logger.info(
            "strategy_switched",
            old_strategy=old_strategy.value,
            new_strategy=strategy.value,
        )
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        current_router = self._routers[self._current_strategy]
        router_stats = await current_router.get_stats()
        
        return {
            "current_strategy": self._current_strategy.value,
            "total_requests": self._stats["total_requests"],
            "strategy_switches": self._stats["strategy_switches"],
            "available_strategies": list(self._routers.keys()),
            "current_router_stats": router_stats,
        }
    
    async def get_all_stats(self) -> Dict[str, Any]:
        """获取所有路由器的统计"""
        all_stats = {}
        for strategy, router in self._routers.items():
            all_stats[strategy.value] = await router.get_stats()
        
        return all_stats
    
    async def close(self) -> None:
        """关闭所有路由"""
        for router in self._routers.values():
            await router.close()
        
        logger.info("router_service_closed")


# 全局路由服务实例
_router_service: Optional[RouterService] = None


async def get_router_service() -> RouterService:
    """获取路由服务单例"""
    global _router_service
    if _router_service is None:
        _router_service = RouterService()
    return _router_service


async def close_router_service() -> None:
    """关闭路由服务"""
    global _router_service
    if _router_service:
        await _router_service.close()
        _router_service = None

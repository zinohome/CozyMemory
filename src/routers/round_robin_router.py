"""
轮询路由模块

简单的负载均衡策略，均匀分配请求到所有引擎。
"""

import asyncio
from typing import Any, Dict, List, Optional
from structlog import get_logger

from .base import BaseRouter

logger = get_logger(__name__)


class RoundRobinRouter(BaseRouter):
    """
    轮询路由
    
    策略:
    - 按顺序循环选择引擎
    - 均匀分配负载
    - 支持并发安全
    
    适用场景:
    - 所有引擎性能相近
    - 需要简单负载均衡
    - 无特殊路由需求
    """
    
    def __init__(self):
        self._counter = 0
        self._lock = asyncio.Lock()
        self._stats = {
            "total_requests": 0,
            "engine_distribution": {},
        }
        
        logger.info("round_robin_router_initialized")
    
    async def route(
        self,
        user_id: str,
        query: Optional[str],
        memory_type: Optional[str],
        source: Optional[str],
        available_engines: List[str],
    ) -> List[str]:
        """
        轮询路由
        
        流程:
        1. 获取当前索引
        2. 选择起始引擎
        3. 返回循环排序的引擎列表
        """
        async with self._lock:
            self._stats["total_requests"] += 1
            
            if not available_engines:
                logger.warning("no_available_engines")
                return []
            
            # 计算起始索引
            index = self._counter % len(available_engines)
            self._counter += 1
            
            # 轮询排序
            routed_engines = (
                available_engines[index:] + available_engines[:index]
            )
            
            # 更新统计
            first_engine = routed_engines[0] if routed_engines else "none"
            self._stats["engine_distribution"][first_engine] = (
                self._stats["engine_distribution"].get(first_engine, 0) + 1
            )
            
            logger.debug(
                "round_robin_routing",
                index=index,
                counter=self._counter,
                routed_engines=routed_engines,
            )
            
            return routed_engines
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = self._stats["total_requests"]
        
        # 计算均衡度
        distribution = self._stats["engine_distribution"]
        if distribution:
            values = list(distribution.values())
            max_count = max(values)
            min_count = min(values)
            balance_score = (
                (1 - (max_count - min_count) / max_count) * 100
                if max_count > 0 else 100
            )
        else:
            balance_score = 100.0
        
        return {
            "type": "round_robin",
            "total_requests": total,
            "engine_distribution": distribution,
            "current_counter": self._counter,
            "balance_score": round(balance_score, 2),
        }
    
    async def reset(self) -> None:
        """重置计数器"""
        async with self._lock:
            self._counter = 0
            self._stats["engine_distribution"] = {}
            logger.info("round_robin_router_reset")
    
    async def close(self) -> None:
        """关闭路由"""
        logger.info("round_robin_router_closed")

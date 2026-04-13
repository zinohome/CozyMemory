"""
权重路由模块

基于引擎权重和性能指标进行路由。
"""

import asyncio
from typing import Any, Dict, List, Optional
from structlog import get_logger

from .base import BaseRouter

logger = get_logger(__name__)


class WeightedRouter(BaseRouter):
    """
    权重路由
    
    策略:
    - 基于配置的静态权重
    - 支持动态权重调整 (基于性能)
    - 加权随机选择
    
    适用场景:
    - 引擎性能差异明显
    - 需要优先级控制
    - 支持 A/B 测试
    """
    
    def __init__(
        self,
        default_weights: Optional[Dict[str, float]] = None,
        enable_dynamic: bool = False,
    ):
        """
        参数:
            default_weights: 默认权重配置
            enable_dynamic: 是否启用动态权重
        """
        self.default_weights = default_weights or {
            "memobase": 1.0,
            "local": 0.8,
            "vector": 0.6,
        }
        
        self.enable_dynamic = enable_dynamic
        self._current_weights = self.default_weights.copy()
        self._lock = asyncio.Lock()
        
        # 性能统计 (用于动态权重)
        self._performance_stats = {
            engine: {
                "total_requests": 0,
                "total_latency": 0.0,
                "success_count": 0,
                "error_count": 0,
            }
            for engine in self.default_weights.keys()
        }
        
        self._stats = {
            "total_requests": 0,
            "weight_adjustments": 0,
        }
        
        logger.info(
            "weighted_router_initialized",
            default_weights=self.default_weights,
            enable_dynamic=enable_dynamic,
        )
    
    def _calculate_weighted_random(
        self,
        available_engines: List[str],
    ) -> str:
        """
        加权随机选择
        
        使用简单的轮盘赌算法
        """
        import random
        
        if not available_engines:
            return ""
        
        # 获取权重
        weights = [
            self._current_weights.get(engine, 0.5)
            for engine in available_engines
        ]
        
        # 归一化
        total_weight = sum(weights)
        if total_weight == 0:
            return available_engines[0]
        
        # 轮盘赌
        rand = random.uniform(0, total_weight)
        cumulative = 0.0
        
        for engine, weight in zip(available_engines, weights):
            cumulative += weight
            if rand <= cumulative:
                return engine
        
        return available_engines[-1]
    
    async def _update_dynamic_weights(self) -> None:
        """
        动态更新权重
        
        基于:
        - 成功率
        - 平均延迟
        """
        if not self.enable_dynamic:
            return
        
        for engine, stats in self._performance_stats.items():
            if stats["total_requests"] == 0:
                continue
            
            # 计算成功率
            success_rate = (
                stats["success_count"] / stats["total_requests"]
            )
            
            # 计算平均延迟
            avg_latency = (
                stats["total_latency"] / stats["total_requests"]
                if stats["total_requests"] > 0 else 0
            )
            
            # 动态调整权重
            base_weight = self.default_weights.get(engine, 0.5)
            
            # 成功率影响 (±20%)
            success_factor = 1.0 + (success_rate - 0.8) * 0.5
            
            # 延迟影响 (±10%)
            latency_factor = 1.0
            if avg_latency > 0:
                # 假设目标延迟 < 100ms
                latency_factor = max(0.9, min(1.1, 1.0 - (avg_latency - 0.1) * 0.2))
            
            # 新权重
            new_weight = base_weight * success_factor * latency_factor
            new_weight = max(0.1, min(2.0, new_weight))  # 限制范围
            
            self._current_weights[engine] = new_weight
        
        self._stats["weight_adjustments"] += 1
    
    async def route(
        self,
        user_id: str,
        query: Optional[str],
        memory_type: Optional[str],
        source: Optional[str],
        available_engines: List[str],
    ) -> List[str]:
        """
        权重路由
        
        流程:
        1. 选择主引擎 (加权随机)
        2. 按权重排序其他引擎
        3. 返回排序后的列表
        """
        async with self._lock:
            self._stats["total_requests"] += 1
            
            if not available_engines:
                logger.warning("no_available_engines")
                return []
            
            # 动态权重更新
            if self.enable_dynamic:
                await self._update_dynamic_weights()
            
            # 选择主引擎
            primary = self._calculate_weighted_random(available_engines)
            
            # 排序其他引擎
            other_engines = [e for e in available_engines if e != primary]
            other_engines.sort(
                key=lambda e: self._current_weights.get(e, 0.5),
                reverse=True,
            )
            
            # 构建结果
            routed_engines = [primary] + other_engines
            
            # 更新性能统计
            if primary in self._performance_stats:
                self._performance_stats[primary]["total_requests"] += 1
            
            logger.debug(
                "weighted_routing",
                primary=primary,
                weights=self._current_weights,
            )
            
            return routed_engines
    
    async def record_performance(
        self,
        engine: str,
        latency: float,
        success: bool,
    ) -> None:
        """
        记录引擎性能
        
        用于动态权重调整
        """
        async with self._lock:
            if engine not in self._performance_stats:
                self._performance_stats[engine] = {
                    "total_requests": 0,
                    "total_latency": 0.0,
                    "success_count": 0,
                    "error_count": 0,
                }
            
            stats = self._performance_stats[engine]
            stats["total_requests"] += 1
            stats["total_latency"] += latency
            
            if success:
                stats["success_count"] += 1
            else:
                stats["error_count"] += 1
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "type": "weighted",
            "total_requests": self._stats["total_requests"],
            "weight_adjustments": self._stats["weight_adjustments"],
            "current_weights": self._current_weights,
            "default_weights": self.default_weights,
            "enable_dynamic": self.enable_dynamic,
            "performance_stats": self._performance_stats,
        }
    
    async def set_weight(self, engine: str, weight: float) -> None:
        """手动设置引擎权重"""
        async with self._lock:
            self._current_weights[engine] = weight
            logger.info("weight_updated", engine=engine, weight=weight)
    
    async def reset_weights(self) -> None:
        """重置为默认权重"""
        async with self._lock:
            self._current_weights = self.default_weights.copy()
            self._stats["weight_adjustments"] = 0
            logger.info("weights_reset")
    
    async def close(self) -> None:
        """关闭路由"""
        logger.info("weighted_router_closed")

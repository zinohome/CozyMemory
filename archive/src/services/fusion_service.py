"""
CozyMemory 融合服务

提供统一的结果融合管理服务。
"""

from typing import Any, Dict, List, Optional
from structlog import get_logger

from ..fusion.base import BaseFusion
from ..fusion.rrf_fusion import RRFFusion
from ..fusion.weighted_fusion import WeightedFusion
from ..utils.config import settings

logger = get_logger(__name__)


class FusionService:
    """
    融合服务
    
    提供统一的结果融合接口，支持多种融合策略。
    
    架构:
        FusionService
        ├── RRFFusion (RRF 算法)
        └── WeightedFusion (权重融合)
    
    特性:
    - 策略动态切换
    - 结果去重
    - 统计监控
    """
    
    def __init__(self):
        self._fusions: Dict[str, BaseFusion] = {
            "rrf": RRFFusion(k=60),
            "weighted": WeightedFusion(),
        }
        
        # 当前策略
        self._current_strategy = settings.FUSION_STRATEGY
        
        self._stats = {
            "total_fusions": 0,
        }
        
        logger.info(
            "fusion_service_initialized",
            current_strategy=self._current_strategy,
        )
    
    async def fuse(
        self,
        results: Dict[str, List[Any]],
        limit: int = 10,
    ) -> List[Any]:
        """
        融合结果
        
        使用当前策略进行融合
        """
        self._stats["total_fusions"] += 1
        
        if self._current_strategy not in self._fusions:
            logger.warning(
                "invalid_fusion_strategy",
                strategy=self._current_strategy,
                fallback="rrf",
            )
            self._current_strategy = "rrf"
        
        fusion = self._fusions[self._current_strategy]
        result = await fusion.fuse(results, limit)
        
        logger.debug(
            "fusion_completed",
            strategy=self._current_strategy,
            input_engines=len(results),
            output_results=len(result),
        )
        
        return result
    
    async def switch_strategy(self, strategy: str) -> None:
        """切换融合策略"""
        if strategy not in self._fusions:
            logger.error("invalid_strategy", strategy=strategy)
            raise ValueError(f"Invalid fusion strategy: {strategy}")
        
        old_strategy = self._current_strategy
        self._current_strategy = strategy
        
        logger.info(
            "fusion_strategy_switched",
            old_strategy=old_strategy,
            new_strategy=strategy,
        )
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        current_fusion = self._fusions[self._current_strategy]
        fusion_stats = await current_fusion.get_stats()
        
        return {
            "current_strategy": self._current_strategy,
            "total_fusions": self._stats["total_fusions"],
            "available_strategies": list(self._fusions.keys()),
            "current_fusion_stats": fusion_stats,
        }
    
    async def get_all_stats(self) -> Dict[str, Any]:
        """获取所有融合器的统计"""
        all_stats = {}
        for strategy, fusion in self._fusions.items():
            all_stats[strategy] = await fusion.get_stats()
        
        return all_stats
    
    @staticmethod
    def deduplicate(results: List[Any], key: str = "id") -> List[Any]:
        """静态去重方法"""
        return BaseFusion.deduplicate(results, key)
    
    async def close(self) -> None:
        """关闭融合服务"""
        logger.info("fusion_service_closed")


# 全局融合服务实例
_fusion_service: Optional[FusionService] = None


async def get_fusion_service() -> FusionService:
    """获取融合服务单例"""
    global _fusion_service
    if _fusion_service is None:
        _fusion_service = FusionService()
    return _fusion_service


async def close_fusion_service() -> None:
    """关闭融合服务"""
    global _fusion_service
    if _fusion_service:
        await _fusion_service.close()
        _fusion_service = None

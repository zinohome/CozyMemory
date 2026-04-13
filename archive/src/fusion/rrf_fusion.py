"""
RRF (Reciprocal Rank Fusion) 融合模块

经典的搜索结果融合算法。
"""

from typing import Any, Dict, List
from structlog import get_logger

from .base import BaseFusion

logger = get_logger(__name__)


class RRFFusion(BaseFusion):
    """
    RRF (Reciprocal Rank Fusion) 融合
    
    算法:
    score = Σ 1 / (k + rank_i)
    
    其中:
    - rank_i: 结果在引擎 i 中的排名
    - k: 平滑常数 (默认 60)
    
    特性:
    - 无需归一化
    - 对排名敏感
    - 广泛使用
    
    参数:
        k: 平滑常数，控制排名影响
    """
    
    def __init__(self, k: int = 60):
        self.k = k
        self._stats = {
            "total_fusions": 0,
            "total_results_processed": 0,
            "average_input_engines": 0.0,
            "average_output_results": 0.0,
        }
        
        logger.info("rrf_fusion_initialized", k=k)
    
    async def fuse(
        self,
        results: Dict[str, List[Any]],
        limit: int = 10,
    ) -> List[Any]:
        """
        RRF 融合
        
        流程:
        1. 计算每个结果的 RRF 分数
        2. 按分数排序
        3. 去重
        4. 返回前 limit 个
        
        Args:
            results: {engine_name: [results]}
            limit: 返回数量
        """
        self._stats["total_fusions"] += 1
        
        if not results:
            return []
        
        # 统计输入
        total_input = sum(len(r) for r in results.values())
        self._stats["total_results_processed"] += total_input
        self._stats["average_input_engines"] = (
            (self._stats["average_input_engines"] * (self._stats["total_fusions"] - 1)
             + len(results)) / self._stats["total_fusions"]
        )
        
        # 计算 RRF 分数
        scores: Dict[Any, float] = {}
        
        for engine_name, engine_results in results.items():
            for rank, result in enumerate(engine_results):
                # 获取结果 ID (用于合并相同结果)
                if isinstance(result, dict):
                    result_id = result.get("id", str(result))
                elif hasattr(result, "id"):
                    result_id = result.id
                else:
                    result_id = str(result)
                
                # RRF 分数
                score = 1.0 / (self.k + rank)
                
                if result_id not in scores:
                    scores[result_id] = 0.0
                
                scores[result_id] += score
        
        # 按分数排序
        sorted_results = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        
        # 构建结果 ID 到原始结果的映射
        result_map: Dict[Any, Any] = {}
        for engine_results in results.values():
            for result in engine_results:
                if isinstance(result, dict):
                    result_id = result.get("id", str(result))
                elif hasattr(result, "id"):
                    result_id = result.id
                else:
                    result_id = str(result)
                
                if result_id not in result_map:
                    result_map[result_id] = result
        
        # 获取前 limit 个
        fused = []
        for result_id, _ in sorted_results[:limit]:
            if result_id in result_map:
                fused.append(result_map[result_id])
        
        # 去重 (额外保护)
        fused = self.deduplicate(fused)
        
        # 更新统计
        self._stats["average_output_results"] = (
            (self._stats["average_output_results"] * (self._stats["total_fusions"] - 1)
             + len(fused)) / self._stats["total_fusions"]
        )
        
        logger.debug(
            "rrf_fusion_completed",
            input_engines=len(results),
            input_results=total_input,
            output_results=len(fused),
            limit=limit,
        )
        
        return fused
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "type": "rrf",
            "k": self.k,
            "total_fusions": self._stats["total_fusions"],
            "total_results_processed": self._stats["total_results_processed"],
            "average_input_engines": round(self._stats["average_input_engines"], 2),
            "average_output_results": round(self._stats["average_output_results"], 2),
        }

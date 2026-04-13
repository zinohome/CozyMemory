"""
权重融合模块

基于引擎权重的结果融合。
"""

from typing import Any, Dict, List, Optional
from structlog import get_logger

from .base import BaseFusion

logger = get_logger(__name__)


class WeightedFusion(BaseFusion):
    """
    权重融合
    
    算法:
    score = Σ (weight_i * normalized_score_i)
    
    特性:
    - 支持引擎权重
    - 支持结果分数
    - 可配置归一化
    
    参数:
        engine_weights: 引擎权重配置
        use_result_score: 是否使用结果自带分数
    """
    
    def __init__(
        self,
        engine_weights: Optional[Dict[str, float]] = None,
        use_result_score: bool = True,
    ):
        self.engine_weights = engine_weights or {
            "memobase": 1.0,
            "local": 0.8,
            "vector": 0.6,
        }
        
        self.use_result_score = use_result_score
        self._stats = {
            "total_fusions": 0,
            "total_results_processed": 0,
            "weighted_results": 0,
        }
        
        logger.info(
            "weighted_fusion_initialized",
            engine_weights=self.engine_weights,
            use_result_score=use_result_score,
        )
    
    def _normalize_score(
        self,
        score: float,
        min_score: float,
        max_score: float,
    ) -> float:
        """
        Min-Max 归一化
        
        将分数归一化到 [0, 1] 范围
        """
        if max_score == min_score:
            return 0.5
        
        normalized = (score - min_score) / (max_score - min_score)
        return max(0.0, min(1.0, normalized))
    
    async def fuse(
        self,
        results: Dict[str, List[Any]],
        limit: int = 10,
    ) -> List[Any]:
        """
        权重融合
        
        流程:
        1. 收集所有分数
        2. 归一化分数
        3. 加权求和
        4. 排序
        5. 去重
        6. 返回前 limit 个
        """
        self._stats["total_fusions"] += 1
        
        if not results:
            return []
        
        # 统计输入
        total_input = sum(len(r) for r in results.values())
        self._stats["total_results_processed"] += total_input
        
        # 收集所有分数 (用于归一化)
        all_scores = []
        
        for engine_name, engine_results in results.items():
            for result in engine_results:
                if self.use_result_score:
                    # 使用结果自带分数
                    if isinstance(result, dict):
                        score = result.get("score", 0.0)
                    elif hasattr(result, "score"):
                        score = getattr(result, "score", 0.0)
                    else:
                        score = 0.0
                else:
                    # 使用排名分数
                    score = 1.0 / (1 + engine_results.index(result))
                
                all_scores.append(score)
        
        # 计算归一化参数
        min_score = min(all_scores) if all_scores else 0.0
        max_score = max(all_scores) if all_scores else 1.0
        
        # 计算加权分数
        weighted_scores: Dict[Any, float] = {}
        
        for engine_name, engine_results in results.items():
            engine_weight = self.engine_weights.get(engine_name, 0.5)
            
            for rank, result in enumerate(engine_results):
                # 获取结果 ID
                if isinstance(result, dict):
                    result_id = result.get("id", str(result))
                    base_score = result.get("score", 0.0)
                elif hasattr(result, "id"):
                    result_id = result.id
                    base_score = getattr(result, "score", 0.0)
                else:
                    result_id = str(result)
                    base_score = 0.0
                
                # 归一化
                normalized = self._normalize_score(
                    base_score, min_score, max_score
                )
                
                # 加权
                weighted_score = engine_weight * normalized
                
                if result_id not in weighted_scores:
                    weighted_scores[result_id] = 0.0
                
                weighted_scores[result_id] += weighted_score
                
                if self.use_result_score:
                    self._stats["weighted_results"] += 1
        
        # 按加权分数排序
        sorted_results = sorted(
            weighted_scores.items(),
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
        
        # 去重
        fused = self.deduplicate(fused)
        
        logger.debug(
            "weighted_fusion_completed",
            input_engines=len(results),
            input_results=total_input,
            output_results=len(fused),
            limit=limit,
        )
        
        return fused
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "type": "weighted",
            "engine_weights": self.engine_weights,
            "use_result_score": self.use_result_score,
            "total_fusions": self._stats["total_fusions"],
            "total_results_processed": self._stats["total_results_processed"],
            "weighted_results": self._stats["weighted_results"],
        }
    
    async def set_engine_weight(self, engine: str, weight: float) -> None:
        """设置引擎权重"""
        self.engine_weights[engine] = weight
        logger.info("engine_weight_updated", engine=engine, weight=weight)

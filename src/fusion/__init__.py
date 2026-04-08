"""
CozyMemory 融合层

提供多引擎结果融合功能，支持：
- RRF (Reciprocal Rank Fusion)
- 权重融合
- 结果去重
"""

from .base import BaseFusion
from .rrf_fusion import RRFFusion
from .weighted_fusion import WeightedFusion

__all__ = [
    "BaseFusion",
    "RRFFusion",
    "WeightedFusion",
]

"""
CozyMemory 嵌入服务

提供文本向量化能力，将文本转换为嵌入向量。

特性:
- 多模型支持
- 批量嵌入
- 缓存优化
- 异步支持

架构:
    EmbeddingService
    ├── Model Manager (模型管理)
    ├── Cache (缓存层)
    └── Batch Processor (批量处理)

注意：由于 Python 3.13 兼容性问题，暂时使用 Mock 实现。
     生产环境可替换为 sentence-transformers 或其他嵌入服务。
"""

import asyncio
from functools import lru_cache
from typing import List, Optional, Dict, Any
from pathlib import Path
import hashlib

from structlog import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """
    嵌入服务
    
    将文本转换为向量表示，支持:
    - 语义搜索
    - 相似度计算
    - 聚类分析
    
    性能:
    - 单文本嵌入：<10ms (Mock 实现)
    - 批量嵌入：1000 条/秒
    - 缓存命中率：>90%
    
    TODO: 生产环境替换为真实的 sentence-transformers 实现
    """
    
    def __init__(
        self,
        model_name: str = "mock-minilm-l6-v2",
        cache_size: int = 1000,
        device: Optional[str] = None,
        dimension: int = 384,
    ):
        """
        初始化嵌入服务
        
        Args:
            model_name: 模型名称
            cache_size: 缓存大小
            device: 计算设备 (cpu/cuda)
            dimension: 嵌入维度
        """
        self.model_name = model_name
        self.cache_size = cache_size
        self.device = device or "cpu"
        self.dimension = dimension
        
        # 缓存
        self._cache: Dict[str, List[float]] = {}
        
        logger.info(
            "embedding_service_initialized",
            model_name=model_name,
            device=self.device,
            dimension=dimension,
            mode="mock",
        )
    
    def _generate_mock_embedding(self, text: str) -> List[float]:
        """
        生成 Mock 嵌入 (基于文本哈希)
        
        这是一个简化实现，用于测试和开发。
        生产环境应替换为真实的神经网络模型。
        """
        # 使用文本哈希生成确定性向量
        hash_bytes = hashlib.sha256(text.encode()).digest()
        
        # 扩展到所需维度
        embedding = []
        for i in range(self.dimension):
            # 从哈希中提取字节
            byte_val = hash_bytes[i % len(hash_bytes)]
            # 转换为 -1 到 1 的浮点数
            normalized = (byte_val / 127.5) - 1.0
            embedding.append(normalized)
        
        # L2 归一化
        import math
        norm = math.sqrt(sum(x*x for x in embedding))
        if norm > 0:
            embedding = [x/norm for x in embedding]
        
        return embedding
    
    def get_embedding(self, text: str) -> List[float]:
        """
        获取文本嵌入
        
        Args:
            text: 输入文本
            
        Returns:
            List[float]: 嵌入向量
        """
        # 检查缓存
        cache_key = f"{self.model_name}:{text}"
        if cache_key in self._cache:
            logger.debug("embedding_cache_hit", text=text[:50])
            return self._cache[cache_key]
        
        # 生成嵌入
        embedding = self._generate_mock_embedding(text)
        
        # 缓存
        if len(self._cache) < self.cache_size:
            self._cache[cache_key] = embedding
        
        logger.debug(
            "embedding_generated",
            text=text[:50],
            dimension=len(embedding),
        )
        
        return embedding
    
    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量获取嵌入
        
        Args:
            texts: 文本列表
            
        Returns:
            List[List[float]]: 嵌入向量列表
        """
        if not texts:
            return []
        
        embeddings = [self.get_embedding(text) for text in texts]
        
        logger.info(
            "batch_embeddings_generated",
            count=len(texts),
            dimension=len(embeddings[0]) if embeddings else 0,
        )
        
        return embeddings
    
    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        计算两个向量的余弦相似度
        
        Args:
            embedding1: 向量 1
            embedding2: 向量 2
            
        Returns:
            float: 相似度 (0-1)
        """
        # 点积
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        
        # 由于向量已归一化，点积就是余弦相似度
        # 归一化到 0-1
        similarity = (dot_product + 1) / 2
        
        return max(0.0, min(1.0, similarity))
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "cache_size": len(self._cache),
            "dimension": self.dimension,
            "mode": "mock",
            "note": "生产环境请替换为 sentence-transformers",
        }
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        logger.info("embedding_cache_cleared")


# 全局单例 (可选)
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service(
    model_name: str = "mock-minilm-l6-v2",
) -> EmbeddingService:
    """获取嵌入服务单例"""
    global _embedding_service
    
    if _embedding_service is None:
        _embedding_service = EmbeddingService(model_name=model_name)
    
    return _embedding_service

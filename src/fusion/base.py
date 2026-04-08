"""
融合基类模块

定义融合系统的抽象接口。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseFusion(ABC):
    """
    融合抽象基类
    
    定义融合系统的基本接口，支持：
    - 多结果融合
    - 结果去重
    - 排序优化
    """
    
    @abstractmethod
    async def fuse(
        self,
        results: Dict[str, List[Any]],
        limit: int = 10,
    ) -> List[Any]:
        """
        融合多个引擎的结果
        
        Args:
            results: 引擎结果字典 {engine_name: [results]}
            limit: 返回结果数量限制
            
        Returns:
            融合后的结果列表
        """
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """
        获取融合统计信息
        
        Returns:
            统计信息字典
        """
        pass
    
    @staticmethod
    def deduplicate(results: List[Any], key: str = "id") -> List[Any]:
        """
        结果去重
        
        Args:
            results: 结果列表
            key: 去重键名
            
        Returns:
            去重后的结果列表
        """
        seen = set()
        deduped = []
        
        for item in results:
            # 获取键值
            if isinstance(item, dict):
                key_value = item.get(key)
            elif hasattr(item, key):
                key_value = getattr(item, key)
            else:
                key_value = str(item)
            
            # 去重
            if key_value not in seen:
                seen.add(key_value)
                deduped.append(item)
        
        return deduped

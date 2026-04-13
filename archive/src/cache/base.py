"""
缓存基类模块

定义缓存系统的抽象接口，所有缓存实现必须继承此类。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseCache(ABC):
    """
    缓存抽象基类
    
    定义缓存系统的基本接口，支持：
    - 获取/设置/删除缓存
    - 检查缓存是否存在
    - 批量清除缓存
    - 获取缓存统计信息
    """
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果不存在则返回 None
        """
        pass
    
    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间 (秒)，None 表示使用默认 TTL，0 表示永不过期
            
        Returns:
            是否设置成功
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
            
        Returns:
            是否删除成功
        """
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        检查缓存是否存在
        
        Args:
            key: 缓存键
            
        Returns:
            是否存在
        """
        pass
    
    @abstractmethod
    async def clear(self, pattern: str = "*") -> int:
        """
        批量清除缓存
        
        Args:
            pattern: 键匹配模式，支持通配符 *
            
        Returns:
            清除的缓存数量
        """
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            统计信息字典，包含 hits, misses, hit_rate 等
        """
        pass
    
    async def close(self) -> None:
        """
        关闭缓存连接
        
        默认实现为空，子类可根据需要实现资源清理
        """
        pass

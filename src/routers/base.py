"""
路由基类模块

定义路由系统的抽象接口，所有路由实现必须继承此类。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum


class RouterStrategy(str, Enum):
    """路由策略枚举"""
    INTENT = "intent"
    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"


class BaseRouter(ABC):
    """
    路由抽象基类
    
    定义路由系统的基本接口，支持：
    - 路由决策
    - 引擎选择
    - 负载均衡
    """
    
    @abstractmethod
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
        
        Args:
            user_id: 用户 ID
            query: 查询内容
            memory_type: 记忆类型
            source: 来源
            available_engines: 可用引擎列表
            
        Returns:
            路由后的引擎列表 (按优先级排序)
        """
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """
        获取路由统计信息
        
        Returns:
            统计信息字典
        """
        pass
    
    async def close(self) -> None:
        """
        关闭路由
        
        默认实现为空，子类可根据需要实现资源清理
        """
        pass

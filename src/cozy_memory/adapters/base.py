"""
CozyMemory 适配器基类

所有记忆引擎适配器的统一接口。
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from structlog import get_logger

from ..models import Memory, MemoryCreate, MemoryQuery, MemorySource

logger = get_logger(__name__)


class BaseAdapter(ABC):
    """
    记忆适配器基类
    
    所有引擎适配器必须实现此接口。
    
    核心方法:
    - create_memory: 创建记忆
    - query_memories: 查询记忆
    - update_memory: 更新记忆
    - delete_memory: 删除记忆
    """
    
    def __init__(self, name: str):
        self.name = name
        self._healthy = False
        self._last_check: Optional[datetime] = None
    
    @property
    @abstractmethod
    def source(self) -> MemorySource:
        """记忆来源标识"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        pass
    
    @abstractmethod
    async def create_memory(self, memory: MemoryCreate) -> Memory:
        """创建记忆"""
        pass
    
    @abstractmethod
    async def query_memories(self, query: MemoryQuery) -> List[Memory]:
        """查询记忆"""
        pass
    
    @abstractmethod
    async def update_memory(self, memory_id: str, updates: Dict[str, Any]) -> Optional[Memory]:
        """更新记忆"""
        pass
    
    @abstractmethod
    async def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        pass
    
    async def batch_create(self, memories: List[MemoryCreate]) -> List[Memory]:
        """批量创建 (默认实现)"""
        results = []
        for memory in memories:
            try:
                result = await self.create_memory(memory)
                results.append(result)
            except Exception as e:
                logger.error("batch_create_failed", memory=memory, error=str(e))
        return results
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息 (可选实现)"""
        return {"adapter": self.name, "healthy": self._healthy}
    
    async def close(self):
        """关闭连接 (可选实现)"""
        pass

"""
适配器基类

定义记忆引擎适配器的统一接口，所有引擎适配器必须实现此接口。
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import asyncio
from datetime import datetime

from ..models.memory import (
    Memory,
    MemoryCreate,
    MemoryQuery,
    MemoryUpdate,
    MemorySource,
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


class BaseAdapter(ABC):
    """记忆引擎适配器基类"""
    
    def __init__(
        self,
        api_url: str,
        api_key: Optional[str] = None,
        timeout: float = 5.0,
    ):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._healthy = True
        self._last_check: Optional[datetime] = None
        self._latency_ms: Optional[float] = None
    
    @property
    @abstractmethod
    def engine_name(self) -> str:
        """引擎名称"""
        pass
    
    @property
    @abstractmethod
    def source(self) -> MemorySource:
        """记忆来源标识"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            bool: 引擎是否健康
        """
        pass
    
    @abstractmethod
    async def create_memory(self, memory: MemoryCreate) -> Memory:
        """
        创建记忆
        
        Args:
            memory: 记忆创建请求
            
        Returns:
            Memory: 创建的记忆对象
        """
        pass
    
    @abstractmethod
    async def get_memory(self, memory_id: str) -> Optional[Memory]:
        """
        获取单个记忆
        
        Args:
            memory_id: 记忆 ID
            
        Returns:
            Optional[Memory]: 记忆对象，不存在返回 None
        """
        pass
    
    @abstractmethod
    async def query_memories(self, query: MemoryQuery) -> List[Memory]:
        """
        查询记忆
        
        Args:
            query: 查询请求
            
        Returns:
            List[Memory]: 记忆列表
        """
        pass
    
    @abstractmethod
    async def update_memory(
        self,
        memory_id: str,
        update: MemoryUpdate
    ) -> Optional[Memory]:
        """
        更新记忆
        
        Args:
            memory_id: 记忆 ID
            update: 更新内容
            
        Returns:
            Optional[Memory]: 更新后的记忆对象
        """
        pass
    
    @abstractmethod
    async def delete_memory(self, memory_id: str) -> bool:
        """
        删除记忆
        
        Args:
            memory_id: 记忆 ID
            
        Returns:
            bool: 是否删除成功
        """
        pass
    
    @abstractmethod
    async def batch_create(
        self,
        memories: List[MemoryCreate]
    ) -> List[Memory]:
        """
        批量创建记忆
        
        Args:
            memories: 记忆创建请求列表
            
        Returns:
            List[Memory]: 创建的记忆列表
        """
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """获取引擎状态"""
        return {
            "name": self.engine_name,
            "enabled": True,
            "status": "healthy" if self._healthy else "down",
            "latency_ms": self._latency_ms,
            "last_check": self._last_check.isoformat() if self._last_check else None,
        }
    
    async def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """
        发送 HTTP 请求 (基类实现，子类可重写)
        
        Args:
            method: HTTP 方法
            path: API 路径
            **kwargs: 请求参数
            
        Returns:
            Dict[str, Any]: 响应数据
        """
        import httpx
        
        url = f"{self.api_url}{path}"
        headers = {}
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(method, url, headers=headers, **kwargs)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as e:
            logger.warning(
                f"{self.engine_name} 请求超时",
                path=path,
                timeout=self.timeout,
                error=str(e)
            )
            self._healthy = False
            raise
        except httpx.HTTPError as e:
            logger.error(
                f"{self.engine_name} 请求失败",
                path=path,
                error=str(e)
            )
            self._healthy = False
            raise
    
    def _create_memory_object(
        self,
        data: Dict[str, Any],
        user_id: str
    ) -> Memory:
        """
        创建 Memory 对象 (辅助方法)
        
        Args:
            data: 原始数据
            user_id: 用户 ID
            
        Returns:
            Memory: 记忆对象
        """
        return Memory(
            id=data.get("id", f"{self.source.value}_{datetime.now().timestamp()}"),
            user_id=user_id,
            content=data.get("content", ""),
            memory_type=data.get("memory_type", "fact"),
            source=self.source,
            metadata=data.get("metadata"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
            confidence=data.get("confidence"),
        )

"""
记忆服务层

封装记忆引擎操作，提供统一的业务逻辑接口。
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from ..models.memory import (
    Memory,
    MemoryCreate,
    MemoryQuery,
    MemoryUpdate,
)
from ..adapters.base import BaseAdapter
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MemoryService:
    """记忆服务"""
    
    def __init__(self, adapter: BaseAdapter):
        self.adapter = adapter
        logger.info(
            "记忆服务初始化",
            engine=adapter.engine_name
        )
    
    async def create_memory(self, memory: MemoryCreate) -> Memory:
        """
        创建记忆
        
        Args:
            memory: 记忆创建请求
            
        Returns:
            Memory: 创建的记忆对象
        """
        logger.info(
            "创建记忆",
            user_id=memory.user_id,
            engine=self.adapter.engine_name
        )
        
        created = await self.adapter.create_memory(memory)
        
        logger.info(
            "记忆创建成功",
            memory_id=created.id,
            user_id=created.user_id
        )
        
        return created
    
    async def get_memory(self, memory_id: str) -> Optional[Memory]:
        """
        获取记忆
        
        Args:
            memory_id: 记忆 ID
            
        Returns:
            Optional[Memory]: 记忆对象
        """
        logger.info("获取记忆", memory_id=memory_id)
        return await self.adapter.get_memory(memory_id)
    
    async def query_memories(self, query: MemoryQuery) -> List[Memory]:
        """
        查询记忆
        
        Args:
            query: 查询请求
            
        Returns:
            List[Memory]: 记忆列表
        """
        logger.info(
            "查询记忆",
            user_id=query.user_id,
            query_text=query.query,
            engine=self.adapter.engine_name
        )
        
        memories = await self.adapter.query_memories(query)
        
        logger.info(
            "查询完成",
            count=len(memories),
            user_id=query.user_id
        )
        
        return memories
    
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
            Optional[Memory]: 更新后的记忆
        """
        logger.info("更新记忆", memory_id=memory_id)
        return await self.adapter.update_memory(memory_id, update)
    
    async def delete_memory(self, memory_id: str) -> bool:
        """
        删除记忆
        
        Args:
            memory_id: 记忆 ID
            
        Returns:
            bool: 是否删除成功
        """
        logger.info("删除记忆", memory_id=memory_id)
        return await self.adapter.delete_memory(memory_id)
    
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
        logger.info(
            "批量创建记忆",
            count=len(memories),
            engine=self.adapter.engine_name
        )
        
        created = await self.adapter.batch_create(memories)
        
        logger.info(
            "批量创建完成",
            success_count=len(created),
            total_count=len(memories)
        )
        
        return created
    
    async def get_engine_status(self) -> Dict[str, Any]:
        """
        获取引擎状态
        
        Returns:
            Dict[str, Any]: 引擎状态信息
        """
        healthy = await self.adapter.health_check()
        status = self.adapter.get_status()
        status["healthy"] = healthy
        return status

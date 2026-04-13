"""
Memobase 适配器

实现 Memobase 记忆引擎的适配器。
文档：https://github.com/memobase/memobase
"""

from typing import List, Optional, Dict, Any
import asyncio
from datetime import datetime

from .base import BaseAdapter
from ..models.memory import (
    Memory,
    MemoryCreate,
    MemoryQuery,
    MemoryUpdate,
    MemorySource,
    MemoryType,
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MemobaseAdapter(BaseAdapter):
    """Memobase 记忆引擎适配器"""
    
    @property
    def engine_name(self) -> str:
        return "Memobase"
    
    @property
    def source(self) -> MemorySource:
        return MemorySource.MEMOBASE
    
    async def health_check(self) -> bool:
        """检查 Memobase 服务是否可用"""
        try:
            response = await self._request("GET", "/health")
            self._healthy = response.get("status") == "healthy"
            self._last_check = datetime.now()
            return self._healthy
        except Exception as e:
            logger.warning(f"Memobase 健康检查失败：{e}")
            self._healthy = False
            self._last_check = datetime.now()
            return False
    
    async def create_memory(self, memory: MemoryCreate) -> Memory:
        """创建记忆"""
        logger.info(
            "创建 Memobase 记忆",
            user_id=memory.user_id,
            memory_type=memory.memory_type.value
        )
        
        # Memobase API 调用
        payload = {
            "user_id": memory.user_id,
            "content": memory.content,
            "type": memory.memory_type.value,
            "metadata": memory.metadata or {},
        }
        
        response = await self._request("POST", "/api/v1/memories", json=payload)
        
        return self._create_memory_object(response, memory.user_id)
    
    async def get_memory(self, memory_id: str) -> Optional[Memory]:
        """获取单个记忆"""
        try:
            response = await self._request("GET", f"/api/v1/memories/{memory_id}")
            return self._create_memory_object(response, response["user_id"])
        except Exception as e:
            logger.warning(f"获取记忆失败：{memory_id}, error={e}")
            return None
    
    async def query_memories(self, query: MemoryQuery) -> List[Memory]:
        """查询记忆"""
        logger.info(
            "查询 Memobase 记忆",
            user_id=query.user_id,
            query_text=query.query,
            memory_type=query.memory_type.value if query.memory_type else None
        )
        
        params = {
            "user_id": query.user_id,
            "limit": query.limit,
        }
        
        if query.query:
            params["q"] = query.query
        
        if query.memory_type:
            params["type"] = query.memory_type.value
        
        response = await self._request("GET", "/api/v1/memories/search", params=params)
        
        memories = []
        for item in response.get("memories", []):
            memories.append(self._create_memory_object(item, query.user_id))
        
        return memories
    
    async def update_memory(
        self,
        memory_id: str,
        update: MemoryUpdate
    ) -> Optional[Memory]:
        """更新记忆"""
        try:
            # 先获取原记忆
            memory = await self.get_memory(memory_id)
            if not memory:
                return None
            
            # 构建更新 payload
            payload = {}
            if update.content:
                payload["content"] = update.content
            if update.metadata:
                payload["metadata"] = update.metadata
            
            response = await self._request(
                "PUT",
                f"/api/v1/memories/{memory_id}",
                json=payload
            )
            
            return self._create_memory_object(response, memory.user_id)
        except Exception as e:
            logger.error(f"更新记忆失败：{memory_id}, error={e}")
            return None
    
    async def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        try:
            await self._request("DELETE", f"/api/v1/memories/{memory_id}")
            logger.info(f"删除 Memobase 记忆：{memory_id}")
            return True
        except Exception as e:
            logger.error(f"删除记忆失败：{memory_id}, error={e}")
            return False
    
    async def batch_create(
        self,
        memories: List[MemoryCreate]
    ) -> List[Memory]:
        """批量创建记忆"""
        logger.info(f"批量创建 Memobase 记忆：{len(memories)} 条")
        
        # 并发创建
        tasks = [self.create_memory(memory) for memory in memories]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        created = []
        for i, result in enumerate(results):
            if isinstance(result, Memory):
                created.append(result)
            else:
                logger.error(
                    f"批量创建失败：索引 {i}",
                    error=str(result) if isinstance(result, Exception) else result
                )
        
        return created

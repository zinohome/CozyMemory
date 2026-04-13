"""
Memobase Mock 适配器

用于本地开发和测试，模拟 Memobase API 行为。
"""

from typing import List, Optional, Dict, Any
import asyncio
from datetime import datetime
import uuid

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


# 内存存储 (用于 Mock)
_mock_memories: Dict[str, Memory] = {}


class MemobaseMockAdapter(BaseAdapter):
    """Memobase Mock 适配器"""
    
    @property
    def engine_name(self) -> str:
        return "Memobase (Mock)"
    
    @property
    def source(self) -> MemorySource:
        return MemorySource.MEMOBASE
    
    async def health_check(self) -> bool:
        """Mock 服务始终健康"""
        self._healthy = True
        self._last_check = datetime.now()
        self._latency_ms = 10.0  # Mock 延迟 10ms
        return True
    
    async def create_memory(self, memory: MemoryCreate) -> Memory:
        """创建记忆 (Mock)"""
        logger.info(
            "[Mock] 创建 Memobase 记忆",
            user_id=memory.user_id,
            memory_type=memory.memory_type.value
        )
        
        # 模拟网络延迟
        await asyncio.sleep(0.05)
        
        memory_id = f"mem_{uuid.uuid4().hex[:8]}"
        now = datetime.now()
        
        memory_obj = Memory(
            id=memory_id,
            user_id=memory.user_id,
            content=memory.content,
            memory_type=memory.memory_type,
            source=self.source,
            metadata=memory.metadata,
            created_at=now,
            updated_at=None,
            confidence=0.95,
        )
        
        _mock_memories[memory_id] = memory_obj
        
        logger.info(f"[Mock] 记忆创建成功：{memory_id}")
        return memory_obj
    
    async def get_memory(self, memory_id: str) -> Optional[Memory]:
        """获取记忆 (Mock)"""
        await asyncio.sleep(0.02)
        return _mock_memories.get(memory_id)
    
    async def query_memories(self, query: MemoryQuery) -> List[Memory]:
        """查询记忆 (Mock)"""
        logger.info(
            "[Mock] 查询 Memobase 记忆",
            user_id=query.user_id,
            query_text=query.query
        )
        
        # 模拟网络延迟
        await asyncio.sleep(0.05)
        
        results = []
        for memory in _mock_memories.values():
            # 过滤用户 ID
            if memory.user_id != query.user_id:
                continue
            
            # 过滤记忆类型
            if query.memory_type and memory.memory_type != query.memory_type:
                continue
            
            # 简单文本搜索
            if query.query and query.query.lower() not in memory.content.lower():
                continue
            
            results.append(memory)
        
        # 限制数量
        results = results[:query.limit]
        
        logger.info(f"[Mock] 查询结果：{len(results)} 条")
        return results
    
    async def update_memory(
        self,
        memory_id: str,
        update: MemoryUpdate
    ) -> Optional[Memory]:
        """更新记忆 (Mock)"""
        await asyncio.sleep(0.03)
        
        memory = _mock_memories.get(memory_id)
        if not memory:
            return None
        
        if update.content:
            memory.content = update.content
        if update.metadata:
            memory.metadata = update.metadata
        
        memory.updated_at = datetime.now()
        _mock_memories[memory_id] = memory
        
        return memory
    
    async def delete_memory(self, memory_id: str) -> bool:
        """删除记忆 (Mock)"""
        await asyncio.sleep(0.02)
        
        if memory_id in _mock_memories:
            del _mock_memories[memory_id]
            logger.info(f"[Mock] 删除记忆：{memory_id}")
            return True
        
        return False
    
    async def batch_create(
        self,
        memories: List[MemoryCreate]
    ) -> List[Memory]:
        """批量创建记忆 (Mock)"""
        logger.info(f"[Mock] 批量创建记忆：{len(memories)} 条")
        
        # 模拟批量处理延迟
        await asyncio.sleep(0.1)
        
        results = []
        for memory in memories:
            created = await self.create_memory(memory)
            results.append(created)
        
        return results
    
    @classmethod
    def clear_all(cls):
        """清空所有 Mock 数据 (用于测试)"""
        _mock_memories.clear()
        logger.info("[Mock] 清空所有数据")

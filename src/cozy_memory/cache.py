"""
CozyMemory 缓存层

简单的内存缓存，支持 TTL。
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from structlog import get_logger

from .models import Memory, MemoryQuery

logger = get_logger(__name__)


class CacheEntry:
    """缓存条目"""
    
    def __init__(self, data: Any, ttl: int):
        self.data = data
        self.expires_at = datetime.now() + timedelta(seconds=ttl)
    
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at


class Cache:
    """
    内存缓存
    
    特性:
    - TTL 过期
    - 自动清理
    - 线程安全
    """
    
    def __init__(self, ttl: int = 3600, max_size: int = 1000):
        self.ttl = ttl
        self.max_size = max_size
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()
        
        logger.info("cache_initialized", ttl=ttl, max_size=max_size)
    
    def _make_key(self, query: MemoryQuery) -> str:
        """生成缓存键"""
        return f"query:{query.user_id}:{query.query or ''}:{query.memory_type or ''}:{query.limit}"
    
    async def get(self, query: MemoryQuery) -> Optional[List[Memory]]:
        """获取缓存"""
        key = self._make_key(query)
        
        async with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                return None
            
            if entry.is_expired():
                del self._cache[key]
                logger.debug("cache_expired", key=key)
                return None
            
            logger.debug("cache_hit", key=key)
            return entry.data
    
    async def set(self, query: MemoryQuery, memories: List[Memory]):
        """设置缓存"""
        key = self._make_key(query)
        
        async with self._lock:
            # 清理过期条目
            await self._cleanup()
            
            # 如果满了，删除最旧的
            if len(self._cache) >= self.max_size:
                oldest_key = min(self._cache.keys())
                del self._cache[oldest_key]
            
            # 添加新条目
            self._cache[key] = CacheEntry(memories, self.ttl)
            logger.debug("cache_set", key=key, count=len(memories))
    
    async def _cleanup(self):
        """清理过期条目"""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.debug("cache_cleaned", count=len(expired_keys))
    
    async def clear(self):
        """清空缓存"""
        async with self._lock:
            self._cache.clear()
            logger.info("cache_cleared")
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        async with self._lock:
            await self._cleanup()
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl": self.ttl,
            }

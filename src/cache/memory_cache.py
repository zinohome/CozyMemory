"""
内存缓存模块

基于 LRU (Least Recently Used) 策略的内存缓存实现。
适合用作 L1 缓存，提供亚毫秒级访问速度。
"""

import time
import asyncio
from collections import OrderedDict
from typing import Any, Dict, Optional
from structlog import get_logger

from .base import BaseCache

logger = get_logger(__name__)


class MemoryCache(BaseCache):
    """
    内存缓存 (LRU) 实现
    
    特性:
    - LRU 驱逐策略
    - 支持 TTL
    - 线程安全 (asyncio lock)
    - 统计信息
    
    参数:
        max_size: 最大缓存条目数 (默认 1000)
        default_ttl: 默认过期时间 (秒)，None 表示永不过期 (默认 300)
    
    示例:
        >>> cache = MemoryCache(max_size=100, default_ttl=60)
        >>> await cache.set("key", "value")
        >>> value = await cache.get("key")
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: int = 300,
    ):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._lock = asyncio.Lock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "evictions": 0,
        }
        
        logger.info(
            "memory_cache_initialized",
            max_size=max_size,
            default_ttl=default_ttl,
        )
    
    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存
        
        如果缓存存在且未过期，返回缓存值并移到末尾 (LRU)。
        如果缓存过期，删除并返回 None。
        """
        async with self._lock:
            if key not in self.cache:
                self._stats["misses"] += 1
                return None
            
            entry = self.cache[key]
            
            # 检查 TTL
            if entry["expires_at"] is not None and time.time() > entry["expires_at"]:
                del self.cache[key]
                self._stats["misses"] += 1
                logger.debug("cache_expired", key=key)
                return None
            
            # LRU: 移到末尾
            self.cache.move_to_end(key)
            self._stats["hits"] += 1
            logger.debug("cache_hit", key=key)
            return entry["value"]
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        设置缓存
        
        如果缓存已满，驱逐最久未使用的条目。
        """
        async with self._lock:
            # 如果已存在，移到末尾
            if key in self.cache:
                self.cache.move_to_end(key)
            
            # 计算过期时间
            if ttl == 0:
                expires_at = None  # 永不过期
            else:
                ttl = ttl if ttl is not None else self.default_ttl
                expires_at = time.time() + ttl
            
            # 设置缓存
            self.cache[key] = {
                "value": value,
                "expires_at": expires_at,
            }
            
            self._stats["sets"] += 1
            
            # LRU 驱逐
            if len(self.cache) > self.max_size:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                self._stats["evictions"] += 1
                logger.debug("cache_evicted", key=oldest_key)
            
            logger.debug("cache_set", key=key, ttl=ttl)
            return True
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        async with self._lock:
            if key in self.cache:
                del self.cache[key]
                self._stats["deletes"] += 1
                logger.debug("cache_delete", key=key)
                return True
            return False
    
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在 (不检查过期)"""
        async with self._lock:
            if key not in self.cache:
                return False
            
            # 检查是否过期
            entry = self.cache[key]
            if entry["expires_at"] is not None and time.time() > entry["expires_at"]:
                return False
            
            return True
    
    async def clear(self, pattern: str = "*") -> int:
        """
        批量清除缓存
        
        支持通配符 * 匹配：
        - "*" - 清除所有
        - "user:*" - 清除所有 user: 开头的键
        - "*:query:*" - 清除包含 :query: 的键
        """
        async with self._lock:
            if pattern == "*":
                count = len(self.cache)
                self.cache.clear()
                logger.info("cache_cleared_all", count=count)
                return count
            
            # 转换为正则表达式模式
            import fnmatch
            keys_to_delete = [
                key for key in self.cache.keys()
                if fnmatch.fnmatch(key, pattern)
            ]
            
            for key in keys_to_delete:
                del self.cache[key]
                self._stats["deletes"] += 1
            
            logger.info("cache_cleared_pattern", pattern=pattern, count=len(keys_to_delete))
            return len(keys_to_delete)
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        async with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0.0
            
            return {
                "type": "memory",
                "max_size": self.max_size,
                "current_size": len(self.cache),
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "sets": self._stats["sets"],
                "deletes": self._stats["deletes"],
                "evictions": self._stats["evictions"],
                "hit_rate": round(hit_rate, 2),
                "default_ttl": self.default_ttl,
            }
    
    async def close(self) -> None:
        """关闭缓存，清理资源"""
        async with self._lock:
            self.cache.clear()
            logger.info("memory_cache_closed")
    
    def __len__(self) -> int:
        """返回当前缓存条目数"""
        return len(self.cache)
    
    def __repr__(self) -> str:
        return f"MemoryCache(max_size={self.max_size}, current_size={len(self)})"

"""
CozyMemory 缓存层

提供多级缓存支持：
- L1: 内存缓存 (LRU)
- L2: Redis 缓存
- L3: 记忆引擎
"""

from .base import BaseCache
from .memory_cache import MemoryCache
from .redis_cache import RedisCache

__all__ = [
    "BaseCache",
    "MemoryCache",
    "RedisCache",
]

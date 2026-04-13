"""
Redis 缓存模块

基于 Redis 的分布式缓存实现。
适合用作 L2 缓存，支持持久化和多实例共享。
"""

import pickle
import asyncio
from typing import Any, Dict, Optional
from structlog import get_logger

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from .base import BaseCache

logger = get_logger(__name__)


class RedisCache(BaseCache):
    """
    Redis 缓存实现
    
    特性:
    - 支持 Redis 连接池
    - 支持 TTL
    - 支持键前缀
    - 统计信息
    - 自动重连
    
    参数:
        redis_url: Redis 连接 URL (默认: redis://localhost:6379/0)
        prefix: 键前缀 (默认: "cozymemory:")
        default_ttl: 默认过期时间 (秒)，None 表示永不过期 (默认 300)
        max_connections: 最大连接数 (默认: 10)
    
    示例:
        >>> cache = RedisCache(redis_url="redis://localhost:6379/0")
        >>> await cache.set("key", "value", ttl=60)
        >>> value = await cache.get("key")
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        prefix: str = "cozymemory:",
        default_ttl: int = 300,
        max_connections: int = 10,
    ):
        if not REDIS_AVAILABLE:
            raise ImportError(
                "redis package is required. Install with: pip install redis>=5.0.0"
            )
        
        self.redis_url = redis_url
        self.prefix = prefix
        self.default_ttl = default_ttl
        self.max_connections = max_connections
        self._redis: Optional[redis.Redis] = None
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0,
        }
        self._lock = asyncio.Lock()
        
        logger.info(
            "redis_cache_initialized",
            redis_url=redis_url,
            prefix=prefix,
            default_ttl=default_ttl,
        )
    
    async def _get_redis(self) -> redis.Redis:
        """获取 Redis 连接 (懒加载)"""
        if self._redis is None:
            async with self._lock:
                if self._redis is None:
                    self._redis = redis.from_url(
                        self.redis_url,
                        max_connections=self.max_connections,
                        decode_responses=False,  # 使用 pickle 序列化
                    )
                    logger.info("redis_connection_established")
        return self._redis
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        try:
            r = await self._get_redis()
            full_key = f"{self.prefix}{key}"
            data = await r.get(full_key)
            
            if data:
                self._stats["hits"] += 1
                logger.debug("redis_cache_hit", key=key)
                return pickle.loads(data)
            else:
                self._stats["misses"] += 1
                logger.debug("redis_cache_miss", key=key)
                return None
                
        except Exception as e:
            self._stats["errors"] += 1
            logger.error("redis_get_error", key=key, error=str(e))
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """设置缓存"""
        try:
            r = await self._get_redis()
            full_key = f"{self.prefix}{key}"
            
            # 计算 TTL
            if ttl == 0:
                # 永不过期
                await r.set(full_key, pickle.dumps(value))
            else:
                ttl = ttl if ttl is not None else self.default_ttl
                await r.setex(full_key, ttl, pickle.dumps(value))
            
            self._stats["sets"] += 1
            logger.debug("redis_cache_set", key=key, ttl=ttl)
            return True
            
        except Exception as e:
            self._stats["errors"] += 1
            logger.error("redis_set_error", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            r = await self._get_redis()
            full_key = f"{self.prefix}{key}"
            result = await r.delete(full_key)
            
            if result:
                self._stats["deletes"] += 1
                logger.debug("redis_cache_delete", key=key)
                return True
            return False
            
        except Exception as e:
            self._stats["errors"] += 1
            logger.error("redis_delete_error", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        try:
            r = await self._get_redis()
            full_key = f"{self.prefix}{key}"
            result = await r.exists(full_key)
            return bool(result)
        except Exception as e:
            self._stats["errors"] += 1
            logger.error("redis_exists_error", key=key, error=str(e))
            return False
    
    async def clear(self, pattern: str = "*") -> int:
        """
        批量清除缓存
        
        支持通配符 * 匹配
        """
        try:
            r = await self._get_redis()
            full_pattern = f"{self.prefix}{pattern}"
            
            # 查找匹配的键
            keys = await r.keys(full_pattern)
            
            if keys:
                count = await r.delete(*keys)
                self._stats["deletes"] += count
                logger.info("redis_cache_cleared", pattern=pattern, count=count)
                return count
            
            return 0
            
        except Exception as e:
            self._stats["errors"] += 1
            logger.error("redis_clear_error", pattern=pattern, error=str(e))
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            r = await self._get_redis()
            info = await r.info("memory")
            
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0.0
            
            # 获取键数量
            keys_count = await r.dbsize()
            
            return {
                "type": "redis",
                "redis_url": self.redis_url,
                "prefix": self.prefix,
                "current_size": keys_count,
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "sets": self._stats["sets"],
                "deletes": self._stats["deletes"],
                "errors": self._stats["errors"],
                "hit_rate": round(hit_rate, 2),
                "default_ttl": self.default_ttl,
                "memory_used": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", "N/A"),
            }
            
        except Exception as e:
            logger.error("redis_get_stats_error", error=str(e))
            return {
                "type": "redis",
                "error": str(e),
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "errors": self._stats["errors"],
            }
    
    async def close(self) -> None:
        """关闭 Redis 连接"""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("redis_cache_closed")
    
    async def ping(self) -> bool:
        """测试 Redis 连接"""
        try:
            r = await self._get_redis()
            result = await r.ping()
            return bool(result)
        except Exception as e:
            logger.error("redis_ping_error", error=str(e))
            return False
    
    def __repr__(self) -> str:
        return f"RedisCache(prefix={self.prefix}, url={self.redis_url})"


class RedisCacheFactory:
    """
    Redis 缓存工厂
    
    提供单例模式创建 Redis 缓存实例
    """
    
    _instances: Dict[str, RedisCache] = {}
    _lock = asyncio.Lock()
    
    @classmethod
    async def get_instance(
        cls,
        redis_url: str = "redis://localhost:6379/0",
        prefix: str = "cozymemory:",
        default_ttl: int = 300,
    ) -> RedisCache:
        """获取或创建 Redis 缓存单例"""
        key = f"{redis_url}:{prefix}"
        
        if key not in cls._instances:
            async with cls._lock:
                if key not in cls._instances:
                    cls._instances[key] = RedisCache(
                        redis_url=redis_url,
                        prefix=prefix,
                        default_ttl=default_ttl,
                    )
        
        return cls._instances[key]
    
    @classmethod
    async def close_all(cls) -> None:
        """关闭所有 Redis 连接"""
        async with cls._lock:
            for cache in cls._instances.values():
                await cache.close()
            cls._instances.clear()

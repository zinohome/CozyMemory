"""
CozyMemory 缓存服务

提供统一的缓存管理服务，支持：
- 多级缓存链
- 缓存保护机制
- 缓存失效策略
- 缓存统计监控
"""

import asyncio
from typing import Any, Dict, List, Optional
from structlog import get_logger

from ..cache.base import BaseCache
from ..cache.memory_cache import MemoryCache
from ..cache.redis_cache import RedisCache
from ..cache.protection import (
    CacheWithProtection,
    AntiAvalancheCache,
    CacheChain,
)
from ..utils.config import settings

logger = get_logger(__name__)


class CacheService:
    """
    缓存服务
    
    提供统一的缓存管理接口，支持多级缓存和保護機制。
    
    架构:
        L1: MemoryCache (LRU, 1000 条)
        ↓
        L2: RedisCache (可选)
        ↓
        L3: 记忆引擎
    
    特性:
    - 缓存穿透保护 (布隆过滤器)
    - 缓存雪崩保护 (随机 TTL)
    - 热点数据保护
    - 自动失效
    """
    
    def __init__(
        self,
        use_redis: bool = True,
        enable_protection: bool = True,
        enable_anti_avalanche: bool = True,
    ):
        self.use_redis = use_redis
        self.enable_protection = enable_protection
        self.enable_anti_avalanche = enable_anti_avalanche
        
        self._cache: Optional[BaseCache] = None
        self._initialized = False
        self._lock = asyncio.Lock()
        
        logger.info(
            "cache_service_initialized",
            use_redis=use_redis,
            enable_protection=enable_protection,
            enable_anti_avalanche=enable_anti_avalanche,
        )
    
    async def initialize(self) -> None:
        """初始化缓存服务"""
        async with self._lock:
            if self._initialized:
                return
            
            caches = []
            
            # L1: 内存缓存 (必选)
            l1_cache = MemoryCache(
                max_size=settings.CACHE_MEMORY_MAX_SIZE,
                default_ttl=settings.CACHE_TTL,
            )
            caches.append(l1_cache)
            logger.info("cache_service_l1_initialized", type="memory")
            
            # L2: Redis 缓存 (可选)
            if self.use_redis:
                try:
                    l2_cache = RedisCache(
                        redis_url=settings.REDIS_URL,
                        prefix=settings.REDIS_PREFIX,
                        default_ttl=settings.CACHE_TTL,
                    )
                    # 测试连接
                    if await l2_cache.ping():
                        caches.append(l2_cache)
                        logger.info("cache_service_l2_initialized", type="redis")
                    else:
                        logger.warning("redis_ping_failed，fallback to memory cache")
                except Exception as e:
                    logger.warning("redis_init_failed", error=str(e))
            
            # 创建缓存链
            if len(caches) == 1:
                self._cache = caches[0]
            else:
                self._cache = CacheChain(caches)
            
            # 添加保护机制
            if self.enable_protection:
                self._cache = CacheWithProtection(
                    self._cache,
                    null_cache_ttl=settings.CACHE_NULL_TTL,
                    jitter_ratio=settings.CACHE_TTL_JITTER,
                )
                logger.info("cache_protection_enabled")
            
            # 添加防雪崩机制
            if self.enable_anti_avalanche:
                self._cache = AntiAvalancheCache(
                    self._cache,
                    hot_threshold=settings.CACHE_HOT_THRESHOLD,
                    hot_ttl_multiplier=settings.CACHE_HOT_TTL_MULTIPLIER,
                )
                logger.info("cache_anti_avalanche_enabled")
            
            self._initialized = True
            logger.info("cache_service_fully_initialized")
    
    async def _ensure_initialized(self) -> None:
        """确保已初始化"""
        if not self._initialized:
            await self.initialize()
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        await self._ensure_initialized()
        return await self._cache.get(key)
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """设置缓存"""
        await self._ensure_initialized()
        return await self._cache.set(key, value, ttl)
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        await self._ensure_initialized()
        return await self._cache.delete(key)
    
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        await self._ensure_initialized()
        return await self._cache.exists(key)
    
    async def clear(self, pattern: str = "*") -> int:
        """清除缓存"""
        await self._ensure_initialized()
        return await self._cache.clear(pattern)
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        await self._ensure_initialized()
        return await self._cache.get_stats()
    
    # ========== 业务方法 ==========
    
    def _make_query_key(
        self,
        user_id: str,
        query: Optional[str],
        memory_type: Optional[str],
        source: Optional[str],
        limit: int,
    ) -> str:
        """
        生成查询缓存键
        
        格式：cozymemory:query:{user_id}:{query_hash}:{type}:{source}:{limit}
        """
        import hashlib
        
        # 生成查询哈希
        query_str = f"{query or ''}:{memory_type or ''}:{source or ''}"
        query_hash = hashlib.md5(query_str.encode()).hexdigest()[:8]
        
        parts = [
            "query",
            user_id,
            query_hash,
            memory_type or "all",
            source or "all",
            str(limit),
        ]
        
        return ":".join(parts)
    
    def _make_memory_key(self, memory_id: str) -> str:
        """
        生成记忆缓存键
        
        格式：cozymemory:memory:{memory_id}
        """
        return f"memory:{memory_id}"
    
    def _make_user_memories_key(
        self,
        user_id: str,
        memory_type: Optional[str],
        page: int,
    ) -> str:
        """
        生成用户记忆列表缓存键
        
        格式：cozymemory:user:{user_id}:memories:{type}:{page}
        """
        return f"user:{user_id}:memories:{memory_type or 'all'}:{page}"
    
    async def get_query(self, cache_key: str) -> Optional[Any]:
        """获取查询缓存"""
        return await self.get(cache_key)
    
    async def set_query(
        self,
        cache_key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """设置查询缓存"""
        return await self.set(cache_key, value, ttl)
    
    async def get_memory(self, memory_id: str) -> Optional[Any]:
        """获取记忆缓存"""
        cache_key = self._make_memory_key(memory_id)
        return await self.get(cache_key)
    
    async def set_memory(
        self,
        memory_id: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """设置记忆缓存"""
        cache_key = self._make_memory_key(memory_id)
        return await self.set(cache_key, value, ttl)
    
    async def invalidate_user_cache(self, user_id: str) -> int:
        """
        失效用户的所有查询缓存
        
        在创建/更新/删除记忆时调用
        """
        pattern = f"query:{user_id}:*"
        count = await self.clear(pattern)
        logger.info("user_cache_invalidated", user_id=user_id, count=count)
        return count
    
    async def invalidate_memory_cache(self, memory_id: str) -> bool:
        """
        失效单条记忆缓存
        
        在更新/删除记忆时调用
        """
        cache_key = self._make_memory_key(memory_id)
        result = await self.delete(cache_key)
        logger.debug("memory_cache_invalidated", memory_id=memory_id)
        return result
    
    async def warmup_query(
        self,
        user_id: str,
        query: Optional[str],
        memory_type: Optional[str],
        source: Optional[str],
        limit: int,
        value: Any,
    ) -> bool:
        """
        预热查询缓存
        
        用于主动缓存常用查询
        """
        cache_key = self._make_query_key(user_id, query, memory_type, source, limit)
        return await self.set_query(cache_key, value)
    
    # ========== 别名方法 (为了 EnhancedMemoryService 兼容) ==========
    
    async def get_by_key(self, key: str) -> Optional[Any]:
        """获取缓存 (别名)"""
        return await self.get(key)
    
    async def set_by_key(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """设置缓存 (别名)"""
        return await self.set(key, value, ttl)
    
    async def invalidate_memory(self, memory_id: str) -> bool:
        """失效记忆缓存 (别名)"""
        return await self.invalidate_memory_cache(memory_id)
    
    async def close(self) -> None:
        """关闭缓存服务"""
        if self._cache:
            await self._cache.close()
            self._initialized = False
            logger.info("cache_service_closed")


# 全局缓存服务实例
_cache_service: Optional[CacheService] = None


async def get_cache_service() -> CacheService:
    """获取缓存服务单例"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService(
            use_redis=settings.REDIS_ENABLED,
            enable_protection=True,
            enable_anti_avalanche=True,
        )
        await _cache_service.initialize()
    return _cache_service


async def close_cache_service() -> None:
    """关闭缓存服务"""
    global _cache_service
    if _cache_service:
        await _cache_service.close()
        _cache_service = None

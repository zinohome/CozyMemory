"""
缓存保护模块

提供缓存穿透和雪崩的保护机制：
- 布隆过滤器 (防穿透)
- 空值缓存 (防穿透)
- 随机 TTL (防雪崩)
- 热点数据保护
"""

import time
import random
import asyncio
import hashlib
from typing import Any, Dict, Optional, Set
from structlog import get_logger

from .base import BaseCache

logger = get_logger(__name__)


class CacheWithProtection(BaseCache):
    """
    带保护机制的缓存装饰器
    
    提供：
    - 缓存穿透保护 (布隆过滤器 + 空值缓存)
    - 缓存雪崩保护 (随机 TTL)
    
    参数:
        cache: 底层缓存实现
        null_cache_ttl: 空值缓存 TTL (秒)，默认 60
        jitter_ratio: TTL 抖动比例 (0.0-1.0)，默认 0.2 (±20%)
        bloom_filter_size: 布隆过滤器大小 (位)，默认 10000
    """
    
    def __init__(
        self,
        cache: BaseCache,
        null_cache_ttl: int = 60,
        jitter_ratio: float = 0.2,
        bloom_filter_size: int = 10000,
    ):
        self.cache = cache
        self.null_cache_ttl = null_cache_ttl
        self.jitter_ratio = jitter_ratio
        self.bloom_filter: Set[str] = set()
        self.bloom_filter_size = bloom_filter_size
        self._stats = {
            "bloom_filter_hits": 0,
            "bloom_filter_misses": 0,
            "null_cache_hits": 0,
        }
        
        logger.info(
            "cache_protection_initialized",
            null_cache_ttl=null_cache_ttl,
            jitter_ratio=jitter_ratio,
            bloom_filter_size=bloom_filter_size,
        )
    
    def _hash_key(self, key: str) -> int:
        """简单的哈希函数 (生产环境建议使用 pybloom)"""
        return int(hashlib.md5(key.encode()).hexdigest(), 16) % self.bloom_filter_size
    
    def _add_to_bloom_filter(self, key: str) -> None:
        """添加到布隆过滤器"""
        hash_value = self._hash_key(key)
        self.bloom_filter.add(hash_value)
    
    def _in_bloom_filter(self, key: str) -> bool:
        """检查是否在布隆过滤器中"""
        hash_value = self._hash_key(key)
        return hash_value in self.bloom_filter
    
    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存 (带保护)
        
        流程:
        1. 检查布隆过滤器 - 如果不存在，直接返回 None
        2. 从缓存获取
        3. 如果是空值标记，返回 None
        """
        # 检查布隆过滤器
        if not self._in_bloom_filter(key):
            self._stats["bloom_filter_misses"] += 1
            logger.debug("bloom_filter_miss", key=key)
            return None
        
        self._stats["bloom_filter_hits"] += 1
        
        # 从缓存获取
        value = await self.cache.get(key)
        
        # 检查空值标记
        if value == "__NULL__":
            self._stats["null_cache_hits"] += 1
            logger.debug("null_cache_hit", key=key)
            return None
        
        return value
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        设置缓存 (带保护)
        
        特性:
        - 添加到布隆过滤器
        - 空值使用特殊标记
        - 应用 TTL 抖动
        """
        # 添加到布隆过滤器
        self._add_to_bloom_filter(key)
        
        # 处理空值
        if value is None:
            logger.debug("cache_set_null", key=key)
            return await self.cache.set(key, "__NULL__", self.null_cache_ttl)
        
        # 应用 TTL 抖动 (防雪崩)
        if ttl is not None and ttl > 0 and self.jitter_ratio > 0:
            jitter = random.uniform(-self.jitter_ratio, self.jitter_ratio)
            ttl = int(ttl * (1 + jitter))
            logger.debug("cache_set_with_jitter", key=key, original_ttl=ttl, jitter=jitter)
        
        return await self.cache.set(key, value, ttl)
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        return await self.cache.delete(key)
    
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        return await self.cache.exists(key)
    
    async def clear(self, pattern: str = "*") -> int:
        """清除缓存"""
        return await self.cache.clear(pattern)
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        cache_stats = await self.cache.get_stats()
        
        total_bloom = self._stats["bloom_filter_hits"] + self._stats["bloom_filter_misses"]
        bloom_filter_rate = (
            self._stats["bloom_filter_hits"] / total_bloom * 100
        ) if total_bloom > 0 else 0.0
        
        return {
            **cache_stats,
            "protection": {
                "bloom_filter_size": len(self.bloom_filter),
                "bloom_filter_hits": self._stats["bloom_filter_hits"],
                "bloom_filter_misses": self._stats["bloom_filter_misses"],
                "bloom_filter_rate": round(bloom_filter_rate, 2),
                "null_cache_hits": self._stats["null_cache_hits"],
            },
        }
    
    async def close(self) -> None:
        """关闭缓存"""
        await self.cache.close()
        self.bloom_filter.clear()


class AntiAvalancheCache(BaseCache):
    """
    防雪崩缓存装饰器
    
    提供：
    - 热点数据识别
    - 热点数据延长 TTL
    - 访问频率统计
    
    参数:
        cache: 底层缓存实现
        hot_threshold: 热点阈值 (访问次数)，默认 100
        hot_ttl_multiplier: 热点 TTL 倍数，默认 2.0
        access_window: 访问统计窗口 (秒)，默认 300
    """
    
    def __init__(
        self,
        cache: BaseCache,
        hot_threshold: int = 100,
        hot_ttl_multiplier: float = 2.0,
        access_window: int = 300,
    ):
        self.cache = cache
        self.hot_threshold = hot_threshold
        self.hot_ttl_multiplier = hot_ttl_multiplier
        self.access_window = access_window
        
        # 访问统计: {key: [timestamp1, timestamp2, ...]}
        self._access_times: Dict[str, list] = {}
        self._hot_keys: Set[str] = set()
        self._lock = asyncio.Lock()
        
        logger.info(
            "anti_avalanche_cache_initialized",
            hot_threshold=hot_threshold,
            hot_ttl_multiplier=hot_ttl_multiplier,
            access_window=access_window,
        )
    
    async def _update_access_stats(self, key: str) -> bool:
        """
        更新访问统计
        
        Returns:
            是否为热点数据
        """
        async with self._lock:
            now = time.time()
            
            # 初始化
            if key not in self._access_times:
                self._access_times[key] = []
            
            # 添加访问时间
            self._access_times[key].append(now)
            
            # 清理过期记录
            cutoff = now - self.access_window
            self._access_times[key] = [
                t for t in self._access_times[key] if t > cutoff
            ]
            
            # 检查是否为热点
            access_count = len(self._access_times[key])
            is_hot = access_count >= self.hot_threshold
            
            if is_hot and key not in self._hot_keys:
                self._hot_keys.add(key)
                logger.info("hot_key_detected", key=key, access_count=access_count)
            
            return is_hot
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存并更新访问统计"""
        # 更新访问统计
        is_hot = await self._update_access_stats(key)
        
        value = await self.cache.get(key)
        
        if is_hot:
            logger.debug("hot_key_accessed", key=key)
        
        return value
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """设置缓存，热点数据使用延长 TTL"""
        # 检查是否为热点数据
        is_hot = key in self._hot_keys
        
        if is_hot and ttl is not None and ttl > 0:
            # 热点数据延长 TTL
            extended_ttl = int(ttl * self.hot_ttl_multiplier)
            logger.debug(
                "hot_key_extended_ttl",
                key=key,
                original_ttl=ttl,
                extended_ttl=extended_ttl,
            )
            return await self.cache.set(key, value, extended_ttl)
        
        return await self.cache.set(key, value, ttl)
    
    async def delete(self, key: str) -> bool:
        """删除缓存并清理统计"""
        async with self._lock:
            if key in self._access_times:
                del self._access_times[key]
            if key in self._hot_keys:
                self._hot_keys.remove(key)
        
        return await self.cache.delete(key)
    
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        return await self.cache.exists(key)
    
    async def clear(self, pattern: str = "*") -> int:
        """清除缓存"""
        async with self._lock:
            self._access_times.clear()
            self._hot_keys.clear()
        
        return await self.cache.clear(pattern)
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        cache_stats = await self.cache.get_stats()
        
        return {
            **cache_stats,
            "anti_avalanche": {
                "hot_keys_count": len(self._hot_keys),
                "hot_keys": list(self._hot_keys)[:10],  # 只显示前 10 个
                "hot_threshold": self.hot_threshold,
                "hot_ttl_multiplier": self.hot_ttl_multiplier,
            },
        }
    
    async def close(self) -> None:
        """关闭缓存"""
        await self.cache.close()
        async with self._lock:
            self._access_times.clear()
            self._hot_keys.clear()


class CacheChain(BaseCache):
    """
    缓存链 (多级缓存)
    
    实现 L1 -> L2 -> L3 的多级缓存策略
    
    参数:
        caches: 缓存列表，按优先级排序 (L1, L2, L3...)
    
    示例:
        >>> l1 = MemoryCache(max_size=1000)
        >>> l2 = RedisCache()
        >>> chain = CacheChain([l1, l2])
        >>> await chain.set("key", "value")
        >>> value = await chain.get("key")  # 从 L1 获取
    """
    
    def __init__(self, caches: list):
        self.caches = caches
        self._stats = {
            "l1_hits": 0,
            "l2_hits": 0,
            "l3_hits": 0,
            "misses": 0,
        }
        
        logger.info(
            "cache_chain_initialized",
            levels=len(caches),
        )
    
    async def get(self, key: str) -> Optional[Any]:
        """
        从多级缓存获取
        
        策略:
        1. 从 L1 开始逐级查找
        2. 找到后回填到上层缓存
        3. 都没找到返回 None
        """
        for i, cache in enumerate(self.caches):
            value = await cache.get(key)
            
            if value is not None:
                # 记录命中
                if i == 0:
                    self._stats["l1_hits"] += 1
                elif i == 1:
                    self._stats["l2_hits"] += 1
                else:
                    self._stats["l3_hits"] += 1
                
                # 回填到上层缓存 (write-through)
                if i > 0:
                    for upper_cache in self.caches[:i]:
                        await upper_cache.set(key, value)
                
                logger.debug("cache_chain_hit", level=i, key=key)
                return value
        
        # 未命中
        self._stats["misses"] += 1
        logger.debug("cache_chain_miss", key=key)
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """设置到所有缓存层级"""
        results = []
        for cache in self.caches:
            result = await cache.set(key, value, ttl)
            results.append(result)
        
        success = all(results)
        logger.debug("cache_chain_set", key=key, success=success)
        return success
    
    async def delete(self, key: str) -> bool:
        """从所有缓存层级删除"""
        results = []
        for cache in self.caches:
            result = await cache.delete(key)
            results.append(result)
        
        return any(results)
    
    async def exists(self, key: str) -> bool:
        """检查是否存在 (检查 L1)"""
        return await self.caches[0].exists(key) if self.caches else False
    
    async def clear(self, pattern: str = "*") -> int:
        """清除所有缓存层级"""
        total = 0
        for cache in self.caches:
            count = await cache.clear(pattern)
            total += count
        return total
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = sum([
            self._stats["l1_hits"],
            self._stats["l2_hits"],
            self._stats["l3_hits"],
            self._stats["misses"],
        ])
        
        hit_rate = (
            (self._stats["l1_hits"] + self._stats["l2_hits"] + self._stats["l3_hits"])
            / total * 100
        ) if total > 0 else 0.0
        
        return {
            "type": "cache_chain",
            "levels": len(self.caches),
            "l1_hits": self._stats["l1_hits"],
            "l2_hits": self._stats["l2_hits"],
            "l3_hits": self._stats["l3_hits"],
            "misses": self._stats["misses"],
            "hit_rate": round(hit_rate, 2),
            "level_stats": [
                await cache.get_stats() for cache in self.caches
            ],
        }
    
    async def close(self) -> None:
        """关闭所有缓存"""
        for cache in self.caches:
            await cache.close()

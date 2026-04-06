"""
CozyMemory 增强记忆服务

集成缓存层、路由层、融合层，提供智能记忆管理。

架构:
    MemoryService
    ├── CacheService (缓存层)
    ├── RouterService (路由层)
    ├── FusionService (融合层)
    └── Multi-Engine Adapters (多引擎)

工作流:
    1. 查询请求 → 检查缓存
    2. 缓存未命中 → 路由到引擎
    3. 多引擎查询 → 结果融合
    4. 缓存结果 → 返回用户
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from structlog import get_logger

from ..models.memory import (
    Memory,
    MemoryCreate,
    MemoryQuery,
    MemoryUpdate,
)
from ..adapters.base import BaseAdapter
from ..services.cache_service import get_cache_service
from ..services.router_service import get_router_service
from ..services.fusion_service import get_fusion_service
from ..utils.config import settings

logger = get_logger(__name__)


class EnhancedMemoryService:
    """
    增强记忆服务
    
    特性:
    - 多级缓存加速
    - 智能路由分发
    - 多引擎结果融合
    - 性能监控
    """
    
    def __init__(
        self,
        adapters: Dict[str, BaseAdapter],
        enable_cache: bool = True,
        enable_routing: bool = True,
        enable_fusion: bool = True,
    ):
        """
        参数:
            adapters: 引擎适配器字典 {engine_name: adapter}
            enable_cache: 启用缓存
            enable_routing: 启用智能路由
            enable_fusion: 启用结果融合
        """
        self.adapters = adapters
        self.enable_cache = enable_cache
        self.enable_routing = enable_routing
        self.enable_fusion = enable_fusion
        
        # 服务实例 (延迟初始化)
        self._cache_service = None
        self._router_service = None
        self._fusion_service = None
        
        # 性能统计
        self._stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "routing_decisions": 0,
            "fusion_operations": 0,
            "total_latency": 0.0,
        }
        
        # 初始化锁
        self._init_lock = asyncio.Lock()
        
        logger.info(
            "enhanced_memory_service_initialized",
            engines=list(adapters.keys()),
            enable_cache=enable_cache,
            enable_routing=enable_routing,
            enable_fusion=enable_fusion,
        )
    
    async def _ensure_services(self):
        """确保服务已初始化"""
        async with self._init_lock:
            if self._cache_service is None and self.enable_cache:
                try:
                    self._cache_service = await get_cache_service()
                except Exception as e:
                    logger.warning("cache_service_init_failed", error=str(e))
                    self.enable_cache = False
            
            if self._router_service is None and self.enable_routing:
                try:
                    self._router_service = await get_router_service()
                except Exception as e:
                    logger.warning("router_service_init_failed", error=str(e))
                    self.enable_routing = False
            
            if self._fusion_service is None and self.enable_fusion:
                try:
                    self._fusion_service = await get_fusion_service()
                except Exception as e:
                    logger.warning("fusion_service_init_failed", error=str(e))
                    self.enable_fusion = False
    
    async def create_memory(self, memory: MemoryCreate) -> Memory:
        """
        创建记忆
        
        流程:
        1. 选择主引擎 (默认 memobase)
        2. 创建记忆
        3. 使缓存失效
        """
        start_time = datetime.now()
        
        # 确保服务已初始化
        await self._ensure_services()
        
        logger.info(
            "create_memory",
            user_id=memory.user_id,
            memory_type=memory.memory_type,
        )
        
        # 选择引擎
        if self.enable_routing and self._router_service:
            engines = await self._router_service.route(
                user_id=memory.user_id,
                query=memory.content,
                memory_type=memory.memory_type,
                source=None,
                available_engines=list(self.adapters.keys()),
            )
            target_engine = engines[0] if engines else "memobase"
        else:
            target_engine = "memobase"
        
        # 创建记忆
        adapter = self.adapters.get(target_engine)
        if not adapter:
            logger.error("engine_not_found", engine=target_engine)
            raise ValueError(f"Engine {target_engine} not found")
        
        created = await adapter.create_memory(memory)
        
        # 使缓存失效
        if self.enable_cache and self._cache_service:
            await self._cache_service.invalidate_user_cache(memory.user_id)
        
        # 更新统计
        latency = (datetime.now() - start_time).total_seconds()
        self._stats["total_queries"] += 1
        self._stats["total_latency"] += latency
        
        logger.info(
            "memory_created",
            memory_id=created.id,
            engine=target_engine,
            latency_ms=latency * 1000,
        )
        
        return created
    
    async def get_memory(self, memory_id: str) -> Optional[Memory]:
        """
        获取记忆
        
        流程:
        1. 检查缓存
        2. 缓存命中 → 返回
        3. 缓存未命中 → 查询引擎
        4. 缓存结果
        """
        start_time = datetime.now()
        
        # 确保服务已初始化
        await self._ensure_services()
        
        logger.info("get_memory", memory_id=memory_id)
        
        # 检查缓存
        if self.enable_cache and self._cache_service:
            cached = await self._cache_service.get_memory(memory_id)
            if cached:
                self._stats["cache_hits"] += 1
                logger.debug("cache_hit", memory_id=memory_id)
                return cached
            
            self._stats["cache_misses"] += 1
        
        # 查询所有引擎
        for engine_name, adapter in self.adapters.items():
            try:
                memory = await adapter.get_memory(memory_id)
                if memory:
                    # 缓存结果
                    if self.enable_cache and self._cache_service:
                        await self._cache_service.set_memory(memory.id, memory)
                    
                    # 更新统计
                    latency = (datetime.now() - start_time).total_seconds()
                    self._stats["total_queries"] += 1
                    self._stats["total_latency"] += latency
                    
                    logger.info(
                        "memory_found",
                        memory_id=memory_id,
                        engine=engine_name,
                        latency_ms=latency * 1000,
                    )
                    
                    return memory
            except Exception as e:
                logger.warning(
                    "engine_query_failed",
                    engine=engine_name,
                    error=str(e),
                )
        
        logger.warning("memory_not_found", memory_id=memory_id)
        return None
    
    async def query_memories(self, query: MemoryQuery) -> List[Memory]:
        """
        查询记忆 (核心智能查询)
        
        流程:
        1. 检查查询缓存
        2. 缓存命中 → 返回
        3. 缓存未命中 → 智能路由
        4. 多引擎并行查询
        5. 结果融合
        6. 缓存结果
        7. 返回
        """
        start_time = datetime.now()
        self._stats["total_queries"] += 1
        
        # 确保服务已初始化
        await self._ensure_services()
        
        logger.info(
            "query_memories",
            user_id=query.user_id,
            query_text=query.query[:50] if query.query else None,
            memory_type=query.memory_type,
        )
        
        # 1. 检查查询缓存
        if self.enable_cache and self._cache_service:
            cache_key = f"query:{query.user_id}:{hash(query.model_dump_json())}"
            cached = await self._cache_service.get_by_key(cache_key)
            if cached:
                self._stats["cache_hits"] += 1
                logger.debug("query_cache_hit", cache_key=cache_key)
                return [Memory(**m) for m in cached]
            
            self._stats["cache_misses"] += 1
        
        # 2. 智能路由
        if self.enable_routing and self._router_service:
            routed_engines = await self._router_service.route(
                user_id=query.user_id,
                query=query.query,
                memory_type=query.memory_type.value if query.memory_type else None,
                source=None,  # MemoryQuery 没有 source 属性
                available_engines=list(self.adapters.keys()),
            )
            self._stats["routing_decisions"] += 1
        else:
            routed_engines = list(self.adapters.keys())
        
        logger.debug(
            "routing_completed",
            routed_engines=routed_engines,
        )
        
        # 3. 多引擎并行查询
        async def query_engine(engine_name: str):
            adapter = self.adapters.get(engine_name)
            if not adapter:
                return []
            
            try:
                results = await adapter.query_memories(query)
                logger.debug(
                    "engine_query_success",
                    engine=engine_name,
                    count=len(results),
                )
                return results
            except Exception as e:
                logger.warning(
                    "engine_query_failed",
                    engine=engine_name,
                    error=str(e),
                )
                return []
        
        # 并行查询
        tasks = [query_engine(engine) for engine in routed_engines]
        engine_results = await asyncio.gather(*tasks)
        
        # 构建结果字典
        results_dict = {
            engine: results
            for engine, results in zip(routed_engines, engine_results)
        }
        
        # 4. 结果融合
        if self.enable_fusion and self._fusion_service and len(results_dict) > 1:
            # 转换为字典格式供融合器使用
            fusion_input = {
                engine: [m.model_dump() for m in results]
                for engine, results in results_dict.items()
            }
            
            fused = await self._fusion_service.fuse(
                fusion_input,
                limit=query.limit,
            )
            self._stats["fusion_operations"] += 1
            
            memories = [Memory(**m) for m in fused]
            logger.info(
                "fusion_completed",
                input_engines=len(results_dict),
                output_count=len(memories),
            )
        else:
            # 单引擎结果或融合禁用
            memories = []
            for results in results_dict.values():
                memories.extend(results)
            
            # 去重
            seen_ids = set()
            unique_memories = []
            for m in memories:
                if m.id not in seen_ids:
                    seen_ids.add(m.id)
                    unique_memories.append(m)
            
            memories = unique_memories[:query.limit]
        
        # 5. 缓存结果
        if self.enable_cache and self._cache_service and memories:
            await self._cache_service.set_by_key(
                cache_key,
                [m.model_dump() for m in memories],
                ttl=300,  # 5 分钟
            )
        
        # 6. 更新统计
        latency = (datetime.now() - start_time).total_seconds()
        self._stats["total_latency"] += latency
        
        logger.info(
            "query_completed",
            count=len(memories),
            latency_ms=latency * 1000,
            cache_hit=False,
        )
        
        return memories
    
    async def update_memory(
        self,
        memory_id: str,
        update: MemoryUpdate
    ) -> Optional[Memory]:
        """
        更新记忆
        
        流程:
        1. 查找记忆所在引擎
        2. 更新
        3. 使缓存失效
        """
        logger.info("update_memory", memory_id=memory_id)
        
        # 查找记忆
        memory = await self.get_memory(memory_id)
        if not memory:
            logger.warning("memory_not_found_for_update", memory_id=memory_id)
            return None
        
        # 更新
        adapter = self.adapters.get(memory.source)
        if not adapter:
            adapter = list(self.adapters.values())[0]
        
        updated = await adapter.update_memory(memory_id, update)
        
        # 使缓存失效
        if self.enable_cache and self._cache_service:
            await self._cache_service.invalidate_memory(memory_id)
            await self._cache_service.invalidate_user_cache(memory.user_id)
        
        logger.info("memory_updated", memory_id=memory_id)
        return updated
    
    async def delete_memory(self, memory_id: str) -> bool:
        """
        删除记忆
        
        流程:
        1. 查找记忆
        2. 删除
        3. 使缓存失效
        """
        logger.info("delete_memory", memory_id=memory_id)
        
        # 查找记忆
        memory = await self.get_memory(memory_id)
        if not memory:
            logger.warning("memory_not_found_for_delete", memory_id=memory_id)
            return False
        
        # 删除
        adapter = self.adapters.get(memory.source)
        if not adapter:
            adapter = list(self.adapters.values())[0]
        
        success = await adapter.delete_memory(memory_id)
        
        # 使缓存失效
        if self.enable_cache and self._cache_service and success:
            await self._cache_service.invalidate_memory(memory_id)
            await self._cache_service.invalidate_user_cache(memory.user_id)
        
        logger.info("memory_deleted", memory_id=memory_id, success=success)
        return success
    
    async def batch_create(
        self,
        memories: List[MemoryCreate]
    ) -> List[Memory]:
        """
        批量创建记忆
        
        流程:
        1. 按引擎分组
        2. 并行创建
        3. 使缓存失效
        """
        logger.info("batch_create", count=len(memories))
        
        # 确保服务已初始化
        await self._ensure_services()
        
        # 按引擎分组
        by_engine: Dict[str, List[MemoryCreate]] = {}
        for memory in memories:
            if self.enable_routing and self._router_service:
                engines = await self._router_service.route(
                    user_id=memory.user_id,
                    query=memory.content,
                    memory_type=memory.memory_type.value if memory.memory_type else None,
                    source=None,
                    available_engines=list(self.adapters.keys()),
                )
                self._stats["routing_decisions"] += 1
                target = engines[0] if engines else "memobase"
            else:
                target = "memobase"
            
            if target not in by_engine:
                by_engine[target] = []
            by_engine[target].append(memory)
        
        # 并行创建
        async def create_batch(engine: str, batch: List[MemoryCreate]):
            adapter = self.adapters.get(engine)
            if not adapter:
                return []
            return await adapter.batch_create(batch)
        
        tasks = [
            create_batch(engine, batch)
            for engine, batch in by_engine.items()
        ]
        results = await asyncio.gather(*tasks)
        
        # 合并结果
        created = []
        for batch_results in results:
            created.extend(batch_results)
        
        # 使缓存失效
        if self.enable_cache and self._cache_service:
            user_ids = {m.user_id for m in memories}
            for user_id in user_ids:
                await self._cache_service.invalidate_user_cache(user_id)
        
        logger.info("batch_create_completed", success_count=len(created))
        return created
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取服务统计"""
        # 计算缓存命中率
        total_cache_ops = self._stats["cache_hits"] + self._stats["cache_misses"]
        cache_hit_rate = (
            self._stats["cache_hits"] / total_cache_ops * 100
            if total_cache_ops > 0 else 0.0
        )
        
        # 计算平均延迟
        avg_latency = (
            self._stats["total_latency"] / self._stats["total_queries"] * 1000
            if self._stats["total_queries"] > 0 else 0.0
        )
        
        stats = {
            "total_queries": self._stats["total_queries"],
            "cache_hits": self._stats["cache_hits"],
            "cache_misses": self._stats["cache_misses"],
            "cache_hit_rate": round(cache_hit_rate, 2),
            "routing_decisions": self._stats["routing_decisions"],
            "fusion_operations": self._stats["fusion_operations"],
            "average_latency_ms": round(avg_latency, 2),
            "engines": list(self.adapters.keys()),
            "features": {
                "cache_enabled": self.enable_cache,
                "routing_enabled": self.enable_routing,
                "fusion_enabled": self.enable_fusion,
            },
        }
        
        # 添加服务统计
        if self._cache_service:
            stats["cache_service"] = await self._cache_service.get_stats()
        
        if self._router_service:
            stats["router_service"] = await self._router_service.get_stats()
        
        if self._fusion_service:
            stats["fusion_service"] = await self._fusion_service.get_stats()
        
        return stats
    
    async def reset_stats(self) -> None:
        """重置统计"""
        self._stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "routing_decisions": 0,
            "fusion_operations": 0,
            "total_latency": 0.0,
        }
        logger.info("stats_reset")
    
    async def close(self) -> None:
        """关闭服务"""
        if self._cache_service:
            await self._cache_service.close()
        if self._router_service:
            await self._router_service.close()
        if self._fusion_service:
            await self._fusion_service.close()
        
        logger.info("enhanced_memory_service_closed")


# 全局服务实例
_enhanced_service: Optional[EnhancedMemoryService] = None


async def get_enhanced_memory_service(
    adapters: Optional[Dict[str, BaseAdapter]] = None,
) -> EnhancedMemoryService:
    """获取增强记忆服务单例"""
    global _enhanced_service
    if _enhanced_service is None:
        if adapters is None:
            # 默认使用 Mock 适配器
            from ..adapters.memobase_mock_adapter import MemobaseMockAdapter
            adapters = {
                "memobase": MemobaseMockAdapter(),
                "local": MemobaseMockAdapter(),
            }
        _enhanced_service = EnhancedMemoryService(adapters)
    return _enhanced_service


async def close_enhanced_memory_service() -> None:
    """关闭增强记忆服务"""
    global _enhanced_service
    if _enhanced_service:
        await _enhanced_service.close()
        _enhanced_service = None

"""
CozyMemory 核心类

统一记忆管理系统的入口。
"""

from typing import Any, Dict, List, Optional

import structlog
from structlog import get_logger

from .models import Config, Memory, MemoryCreate, MemoryQuery, EngineConfig
from .adapters.base import BaseAdapter
from .adapters import get_adapter, ADAPTERS
from .router import Router
from .cache import Cache

logger = get_logger(__name__)


class CozyMemory:
    """
    CozyMemory - 统一记忆管理系统
    
    整合多个记忆引擎，提供统一 API 和智能路由。
    
    使用示例:
    ```python
    from cozy_memory import CozyMemory
    
    # 从配置创建
    cm = CozyMemory.from_config("config.yaml")
    
    # 或者手动创建
    cm = CozyMemory()
    cm.add_adapter("memobase", MemobaseAdapter(api_url="http://localhost:8000"))
    cm.add_adapter("mem0", Mem0Adapter(api_key="your-key"))
    
    # 创建记忆
    memory = await cm.create_memory(
        user_id="user1",
        content="我喜欢 Python",
        memory_type="preference",
    )
    
    # 查询记忆 (自动路由)
    memories = await cm.query("我的编程偏好")
    ```
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        初始化 CozyMemory
        
        Args:
            config: 配置对象，为空则使用默认配置
        """
        self.config = config or Config()
        self.adapters: Dict[str, BaseAdapter] = {}
        self.router: Optional[Router] = None
        self.cache: Optional[Cache] = None
        
        logger.info("cozy_memory_initialized")
    
    @classmethod
    def from_config(cls, path: str) -> "CozyMemory":
        """从 YAML 配置文件创建"""
        config = Config.from_yaml(path)
        instance = cls(config)
        
        # 初始化启用的引擎
        for name, engine_config in config.engines.items():
            if not engine_config.enabled:
                continue
            
            try:
                adapter = instance._create_adapter(name, engine_config)
                instance.add_adapter(name, adapter)
            except Exception as e:
                logger.error("adapter_init_failed", name=name, error=str(e))
        
        # 初始化路由和缓存
        if instance.adapters:
            instance.router = Router(
                instance.adapters,
                default_engine=config.router.default_engine,
            )
        
        if config.router.cache_enabled:
            instance.cache = Cache(ttl=config.router.cache_ttl)
        
        return instance
    
    def _create_adapter(self, name: str, config: EngineConfig) -> BaseAdapter:
        """创建适配器实例"""
        if name == "memobase":
            return get_adapter(
                "memobase",
                api_url=config.api_url or "http://localhost:8000",
                timeout=config.timeout,
            )
        elif name == "mem0":
            if not config.api_key:
                raise ValueError("Mem0 requires api_key")
            return get_adapter(
                "mem0",
                api_key=config.api_key,
                timeout=config.timeout,
            )
        else:
            raise ValueError(f"Unknown engine: {name}")
    
    def add_adapter(self, name: str, adapter: BaseAdapter):
        """添加适配器"""
        self.adapters[name] = adapter
        logger.info("adapter_added", name=name)
        
        # 重新初始化路由
        if self.adapters:
            self.router = Router(
                self.adapters,
                default_engine=self.config.router.default_engine,
            )
    
    def remove_adapter(self, name: str):
        """移除适配器"""
        if name in self.adapters:
            del self.adapters[name]
            logger.info("adapter_removed", name=name)
    
    async def create_memory(self, memory: MemoryCreate) -> Memory:
        """创建记忆"""
        logger.info("create_memory", user_id=memory.user_id)
        
        if not self.router:
            raise RuntimeError("No adapters configured")
        
        # 创建记忆
        created = await self.router.create_memory(memory)
        
        # 清除缓存
        if self.cache:
            await self.cache.clear()
        
        return created
    
    async def query(self, query_text: str, user_id: str, **kwargs) -> List[Memory]:
        """
        查询记忆 (智能路由)
        
        Args:
            query_text: 查询文本
            user_id: 用户 ID
            **kwargs: 其他查询参数
        
        Returns:
            List[Memory]: 记忆列表
        """
        query = MemoryQuery(user_id=user_id, query=query_text, **kwargs)
        
        logger.info("query", user_id=user_id, query=query_text)
        
        # 检查缓存
        if self.cache:
            cached = await self.cache.get(query)
            if cached:
                logger.info("cache_hit")
                return cached
        
        # 路由查询
        if not self.router:
            raise RuntimeError("No adapters configured")
        
        memories = await self.router.query_memories(query)
        
        # 写入缓存
        if self.cache and memories:
            await self.cache.set(query, memories)
        
        return memories
    
    async def get_memory(self, memory_id: str, source: str) -> Optional[Memory]:
        """获取特定记忆"""
        if source not in self.adapters:
            logger.error("unknown_source", source=source)
            return None
        
        adapter = self.adapters[source]
        return await adapter.get_memory(memory_id)
    
    async def update_memory(self, memory_id: str, updates: Dict[str, Any], source: str) -> Optional[Memory]:
        """更新记忆"""
        if source not in self.adapters:
            logger.error("unknown_source", source=source)
            return None
        
        adapter = self.adapters[source]
        updated = await adapter.update_memory(memory_id, updates)
        
        # 清除缓存
        if self.cache:
            await self.cache.clear()
        
        return updated
    
    async def delete_memory(self, memory_id: str, source: str) -> bool:
        """删除记忆"""
        if source not in self.adapters:
            logger.error("unknown_source", source=source)
            return False
        
        adapter = self.adapters[source]
        deleted = await adapter.delete_memory(memory_id)
        
        # 清除缓存
        if self.cache:
            await self.cache.clear()
        
        return deleted
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        results = {}
        
        for name, adapter in self.adapters.items():
            healthy = await adapter.health_check()
            results[name] = {
                "healthy": healthy,
                "source": adapter.source.value,
            }
        
        cache_stats = None
        if self.cache:
            cache_stats = await self.cache.get_stats()
        
        return {
            "adapters": results,
            "cache": cache_stats,
            "router": "ready" if self.router else "not_ready",
        }
    
    async def close(self):
        """关闭所有连接"""
        logger.info("closing_cozy_memory")
        
        for name, adapter in self.adapters.items():
            try:
                await adapter.close()
            except Exception as e:
                logger.error("adapter_close_failed", name=name, error=str(e))
        
        if self.cache:
            await self.cache.clear()
        
        logger.info("cozy_memory_closed")

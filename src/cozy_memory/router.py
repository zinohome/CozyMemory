"""
CozyMemory 智能路由

根据查询意图自动选择最佳记忆引擎。
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from structlog import get_logger

from .models import Memory, MemoryCreate, MemoryQuery, MemorySource
from .adapters.base import BaseAdapter

logger = get_logger(__name__)


class Router:
    """
    智能路由器
    
    根据查询意图选择最佳引擎。
    
    路由策略:
    1. 规则路由 - 基于关键词匹配
    2. 优先级路由 - 基于引擎优先级
    3. 轮询路由 - 负载均衡
    4. LLM 路由 - 基于意图识别 (TODO)
    """
    
    # 意图关键词映射
    INTENT_KEYWORDS = {
        "preference": ["喜欢", "偏好", "习惯", "爱好", "prefer", "like"],
        "config": ["配置", "设置", "选项", "config", "setting"],
        "fact": ["事实", "知识", "知道", "fact", "know"],
        "event": ["事件", "发生", "经历", "event", "happen"],
        "skill": ["技能", "能力", "会", "skill", "can"],
    }
    
    # 引擎优先级 (针对不同类型)
    ENGINE_PRIORITY = {
        "preference": ["mem0", "memobase"],
        "config": ["mem0", "memobase"],
        "fact": ["memobase", "mem0"],
        "event": ["memobase"],
        "skill": ["memobase", "mem0"],
    }
    
    def __init__(self, adapters: Dict[str, BaseAdapter], default_engine: str = "memobase"):
        self.adapters = adapters
        self.default_engine = default_engine
        logger.info("router_initialized", adapters=list(adapters.keys()))
    
    def detect_intent(self, query: str) -> Tuple[str, str]:
        """
        检测查询意图
        
        Returns:
            (intent_type, confidence)
        """
        query_lower = query.lower()
        
        scores = {}
        for intent, keywords in self.INTENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            scores[intent] = score
        
        if not scores or max(scores.values()) == 0:
            return ("fact", 0.5)  # 默认
        
        best_intent = max(scores, key=scores.get)
        confidence = scores[best_intent] / len(self.INTENT_KEYWORDS[best_intent])
        
        return (best_intent, min(confidence * 2, 1.0))
    
    def select_engine(self, query: MemoryQuery) -> str:
        """选择引擎"""
        # 用户指定引擎
        if query.engine:
            if query.engine in self.adapters:
                logger.info("engine_specified_by_user", engine=query.engine)
                return query.engine
            else:
                logger.warning("unknown_engine", engine=query.engine)
        
        # 检测意图
        if query.query:
            intent, confidence = self.detect_intent(query.query)
            logger.info("intent_detected", intent=intent, confidence=confidence)
            
            # 根据意图选择引擎
            priority_list = self.ENGINE_PRIORITY.get(intent, [self.default_engine])
            
            for engine in priority_list:
                if engine in self.adapters:
                    logger.info("engine_selected", engine=engine, intent=intent)
                    return engine
        
        # 默认引擎
        logger.info("using_default_engine", engine=self.default_engine)
        return self.default_engine
    
    async def query_memories(self, query: MemoryQuery) -> List[Memory]:
        """路由查询"""
        engine_name = self.select_engine(query)
        adapter = self.adapters.get(engine_name)
        
        if not adapter:
            logger.error("adapter_not_found", engine=engine_name)
            return []
        
        try:
            memories = await adapter.query_memories(query)
            logger.info("query_completed", engine=engine_name, count=len(memories))
            return memories
        except Exception as e:
            logger.error("query_failed", engine=engine_name, error=str(e))
            return []
    
    async def create_memory(self, memory: MemoryCreate) -> Memory:
        """创建记忆 (路由到默认引擎)"""
        adapter = self.adapters.get(self.default_engine)
        
        if not adapter:
            raise RuntimeError(f"Default adapter not found: {self.default_engine}")
        
        return await adapter.create_memory(memory)
    
    async def update_memory(self, memory_id: str, updates: Dict[str, Any], source: MemorySource) -> Optional[Memory]:
        """更新记忆 (根据来源路由)"""
        engine_name = source.value if isinstance(source, MemorySource) else source
        
        adapter = self.adapters.get(engine_name)
        if not adapter:
            logger.error("adapter_not_found_for_update", engine=engine_name)
            return None
        
        return await adapter.update_memory(memory_id, updates)
    
    async def delete_memory(self, memory_id: str, source: MemorySource) -> bool:
        """删除记忆 (根据来源路由)"""
        engine_name = source.value if isinstance(source, MemorySource) else source
        
        adapter = self.adapters.get(engine_name)
        if not adapter:
            logger.error("adapter_not_found_for_delete", engine=engine_name)
            return False
        
        return await adapter.delete_memory(memory_id)

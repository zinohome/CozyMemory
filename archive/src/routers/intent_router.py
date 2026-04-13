"""
意图识别路由模块

基于查询内容和记忆类型，智能选择最合适的记忆引擎。
"""

import re
from typing import Any, Dict, List, Optional
from structlog import get_logger

from .base import BaseRouter

logger = get_logger(__name__)


class IntentRouter(BaseRouter):
    """
    意图识别路由
    
    根据查询特征自动选择最优引擎：
    - 事实类查询 → Memobase
    - 事件类查询 → Memobase
    - 偏好类查询 → Local
    - 技能类查询 → Vector
    - 对话类查询 → Memobase
    
    特性:
    - 关键词匹配
    - 正则表达式
    - 记忆类型优先
    - 回退机制
    """
    
    def __init__(self):
        # 意图模式定义
        self.intent_patterns = {
            "fact": [
                r"什么是",
                r"为什么",
                r"怎么",
                r"如何",
                r"who is",
                r"what is",
                r"how to",
                r"定义",
                r"概念",
            ],
            "event": [
                r"什么时候",
                r"何时",
                r"where",
                r"when",
                r"发生",
                r"经历",
                r"会议",
                r"约会",
            ],
            "preference": [
                r"喜欢",
                r"偏好",
                r"习惯",
                r"爱好",
                r"like",
                r"prefer",
                r"hobby",
            ],
            "skill": [
                r"技能",
                r"能力",
                r"会什么",
                r"能做什么",
                r"skill",
                r"ability",
            ],
            "conversation": [
                r"聊天",
                r"对话",
                r"谈谈",
                r"聊聊",
                r"chat",
                r"talk",
            ],
        }
        
        # 编译正则
        self.compiled_patterns = {
            intent: [re.compile(p, re.IGNORECASE) for p in patterns]
            for intent, patterns in self.intent_patterns.items()
        }
        
        # 引擎偏好配置
        self.engine_preferences = {
            "fact": ["memobase", "vector", "local"],
            "event": ["memobase", "local"],
            "preference": ["local", "memobase"],
            "skill": ["vector", "memobase"],
            "conversation": ["memobase", "local"],
        }
        
        self._stats = {
            "total_requests": 0,
            "intent_hits": {},
            "fallback_count": 0,
        }
        
        logger.info("intent_router_initialized")
    
    def _detect_intent(
        self,
        query: Optional[str],
        memory_type: Optional[str],
    ) -> str:
        """
        检测查询意图
        
        优先级:
        1. memory_type 直接指定
        2. 查询关键词匹配
        3. 默认返回 "fact"
        """
        # 1. memory_type 优先
        if memory_type:
            logger.debug("intent_from_memory_type", type=memory_type)
            return memory_type
        
        # 2. 查询匹配
        if query:
            query_lower = query.lower()
            for intent, patterns in self.compiled_patterns.items():
                for pattern in patterns:
                    if pattern.search(query_lower):
                        logger.debug("intent_detected", intent=intent, query=query[:50])
                        return intent
        
        # 3. 默认
        logger.debug("intent_default", default="fact")
        return "fact"
    
    async def route(
        self,
        user_id: str,
        query: Optional[str],
        memory_type: Optional[str],
        source: Optional[str],
        available_engines: List[str],
    ) -> List[str]:
        """
        基于意图的路由
        
        流程:
        1. 检测意图
        2. 获取引擎偏好
        3. 过滤可用引擎
        4. 返回排序后的引擎列表
        """
        self._stats["total_requests"] += 1
        
        # 检测意图
        intent = self._detect_intent(query, memory_type)
        
        # 更新统计
        self._stats["intent_hits"][intent] = self._stats["intent_hits"].get(intent, 0) + 1
        
        # 获取偏好引擎
        preferred_engines = self.engine_preferences.get(intent, ["memobase", "local"])
        
        # 过滤可用引擎
        routed_engines = []
        for engine in preferred_engines:
            if engine in available_engines:
                routed_engines.append(engine)
        
        # 添加剩余引擎
        for engine in available_engines:
            if engine not in routed_engines:
                routed_engines.append(engine)
        
        # 如果没有任何匹配，使用第一个可用引擎
        if not routed_engines and available_engines:
            self._stats["fallback_count"] += 1
            routed_engines = [available_engines[0]]
        
        logger.info(
            "intent_routing_completed",
            intent=intent,
            routed_engines=routed_engines,
            available_count=len(available_engines),
        )
        
        return routed_engines
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = self._stats["total_requests"]
        
        return {
            "type": "intent",
            "total_requests": total,
            "intent_distribution": self._stats["intent_hits"],
            "fallback_count": self._stats["fallback_count"],
            "intent_patterns_count": len(self.intent_patterns),
        }
    
    async def close(self) -> None:
        """关闭路由"""
        logger.info("intent_router_closed")

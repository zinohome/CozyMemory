# ADR-004: 路由策略设计

**状态**: 已决定  
**日期**: 2026-04-05  
**决策者**: 张老师  
**记录者**: AI 架构师

---

## 背景

统一 API 层需要智能路由用户请求到合适的记忆引擎（Cognee/Mem0/Memobase）。需要支持：
1. **规则路由**: 基于关键词/模式的快速路由
2. **LLM 意图识别**: 基于语义的智能路由
3. **降级机制**: 无 LLM 资源时可用

## 需求分析

| 需求 ID | 描述 | 优先级 |
|--------|------|--------|
| FR-01 | 支持基于规则的路由 | P0 |
| FR-02 | 支持基于 LLM 的意图识别路由 | P1 |
| FR-03 | 支持规则+LLM 混合模式 | P0 |
| FR-04 | LLM 不可用时自动降级到规则 | P0 |
| FR-05 | 路由延迟可控（规则<10ms, LLM<200ms） | P0 |
| FR-06 | 支持路由结果缓存 | P1 |

## 架构设计

### 混合路由架构

```
┌─────────────────────────────────────────────────────────┐
│                  User Request                            │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Router Configuration                        │
│  ┌───────────────────────────────────────────────────┐  │
│  │  routing_mode: "hybrid" | "rules_only" | "llm_only" │  │
│  │  llm_fallback_enabled: true                        │  │
│  │  cache_enabled: true                               │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Request Preprocessing                       │
│  ┌─────────────────┐  ┌─────────────────┐              │
│  │  Cache Lookup   │→ │ Cache Hit?      │──Yes──→ Return│
│  └─────────────────┘  └─────────────────┘              │
│                          │ No                           │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Routing Mode Decision                       │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │  if routing_mode == "rules_only":               │    │
│  │      → RuleRouter.classify()                    │    │
│  │  elif routing_mode == "llm_only":               │    │
│  │      → LLMRouter.classify()                     │    │
│  │  else:  # hybrid                                │    │
│  │      if llm_available and confidence_threshold: │    │
│  │          → LLMRouter.classify()                 │    │
│  │      else:                                      │    │
│  │          → RuleRouter.classify()                │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Routing Result                              │
│  {                                                       │
│    "engines": ["mem0", "cognee"],                       │
│    "confidence": 0.92,                                   │
│    "source": "llm" | "rules",                           │
│    "cache_hit": false                                    │
│  }                                                       │
└─────────────────────────────────────────────────────────┘
```

## 详细设计

### 1. 规则路由引擎

```python
# routers/rule_router.py
from typing import List, Callable
from pydantic import BaseModel

class RoutingRule(BaseModel):
    name: str
    condition: Callable[[str], bool]  # 条件函数
    engines: List[str]
    priority: int  # 优先级，数字越小优先级越高

class RuleRouter:
    def __init__(self):
        self.rules = self._load_rules()
    
    def _load_rules(self) -> List[RoutingRule]:
        return [
            # 用户偏好相关 → mem0
            RoutingRule(
                name="user_preference_store",
                condition=lambda q: any(kw in q.lower() for kw in 
                    ["喜欢", "偏好", "习惯", "记住我", "我喜欢", "我爱"]),
                engines=["mem0"],
                priority=10
            ),
            RoutingRule(
                name="user_preference_recall",
                condition=lambda q: any(kw in q.lower() for kw in 
                    ["我的偏好", "我喜欢什么", "我记得", "我的习惯"]),
                engines=["mem0"],
                priority=10
            ),
            
            # 知识/文档相关 → cognee
            RoutingRule(
                name="knowledge_search",
                condition=lambda q: any(kw in q.lower() for kw in 
                    ["文档", "文章", "知识", "资料", "教程", "指南", "代码"]),
                engines=["cognee"],
                priority=20
            ),
            
            # 长期记忆/跨会话 → memobase
            RoutingRule(
                name="long_term_recall",
                condition=lambda q: any(kw in q.lower() for kw in 
                    ["之前", "以前", "上次", "曾经", "过往", "历史", "还记得"]),
                engines=["memobase"],
                priority=30
            ),
            
            # 默认规则 → 全部引擎
            RoutingRule(
                name="default",
                condition=lambda q: True,
                engines=["mem0", "cognee", "memobase"],
                priority=999
            ),
        ]
    
    def classify(self, query: str) -> RoutingResult:
        # 按优先级排序
        sorted_rules = sorted(self.rules, key=lambda r: r.priority)
        
        for rule in sorted_rules:
            if rule.condition(query):
                return RoutingResult(
                    engines=rule.engines,
                    confidence=0.8,  # 规则路由固定置信度
                    source="rules",
                    rule_name=rule.name
                )
        
        # 不应该到这里，因为有默认规则
        return RoutingResult(
            engines=["mem0", "cognee", "memobase"],
            confidence=0.5,
            source="rules",
            rule_name="fallback"
        )
```

### 2. LLM 意图识别路由引擎

```python
# routers/llm_router.py
import httpx
from pydantic import BaseModel
from typing import Optional

class LLMRoutingResult(BaseModel):
    engines: List[str]
    confidence: float
    intent: str
    reasoning: str
    query_rewrite: Optional[str] = None

class LLMRouter:
    def __init__(self, llm_url: str, model: str, timeout: float = 5.0):
        self.llm_url = llm_url
        self.model = model
        self.timeout = timeout
        self.system_prompt = self._load_system_prompt()
    
    def _load_system_prompt(self) -> str:
        return """你是一个 AI 记忆系统的路由意图识别专家。
分析用户请求，选择最合适的记忆引擎。

## 引擎说明
- mem0: 用户偏好、习惯、短期记忆
- cognee: 知识、文档、复杂推理
- memobase: 长期记忆、跨会话回忆

## 输出格式 (JSON)
{
    "intent": "意图名称",
    "engines": ["选中的引擎"],
    "confidence": 0.0-1.0,
    "reasoning": "选择理由",
    "query_rewrite": "优化后的查询 (可选)"
}
"""
    
    async def classify(self, query: str, context: Optional[dict] = None) -> LLMRoutingResult:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.llm_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": f"用户请求：{query}",
                        "system": self.system_prompt,
                        "stream": False,
                        "format": "json"
                    },
                    timeout=self.timeout
                )
                response.raise_for_status()
                result = response.json()
                
            return LLMRoutingResult(**json.loads(result["response"]))
            
        except Exception as e:
            # LLM 调用失败，抛出异常由上层处理降级
            raise LLMRouterError(f"LLM 意图识别失败：{e}")
```

### 3. 混合路由引擎（Facade）

```python
# routers/hybrid_router.py
from typing import Optional
from functools import lru_cache

class HybridRouter:
    def __init__(
        self,
        rule_router: RuleRouter,
        llm_router: Optional[LLMRouter] = None,
        mode: str = "hybrid",
        cache_ttl: int = 3600
    ):
        self.rule_router = rule_router
        self.llm_router = llm_router
        self.mode = mode  # "hybrid" | "rules_only" | "llm_only"
        self.cache_ttl = cache_ttl
    
    @lru_cache(maxsize=1000)
    def _cache_get(self, cache_key: str) -> Optional[RoutingResult]:
        # 实际实现可以用 Redis
        pass
    
    def _cache_set(self, cache_key: str, result: RoutingResult):
        pass
    
    async def route(self, query: str, context: Optional[dict] = None) -> RoutingResult:
        # 1. 检查缓存
        cache_key = f"{query}:{hash(str(context))}"
        cached = self._cache_get(cache_key)
        if cached:
            cached.cache_hit = True
            return cached
        
        # 2. 根据模式选择路由策略
        if self.mode == "rules_only":
            result = self.rule_router.classify(query)
        
        elif self.mode == "llm_only":
            if not self.llm_router:
                raise ConfigurationError("LLM router not configured")
            result = await self.llm_router.classify(query, context)
        
        else:  # hybrid
            # 优先尝试 LLM
            if self.llm_router:
                try:
                    llm_result = await self.llm_router.classify(query, context)
                    
                    # 置信度足够，使用 LLM 结果
                    if llm_result.confidence >= 0.6:
                        result = llm_result
                    else:
                        # 置信度低，降级到规则
                        result = self.rule_router.classify(query)
                        result.llm_fallback = True
                        
                except LLMRouterError:
                    # LLM 不可用，降级到规则
                    result = self.rule_router.classify(query)
                    result.llm_fallback = True
            else:
                # 没有配置 LLM，使用规则
                result = self.rule_router.classify(query)
        
        # 3. 缓存结果
        self._cache_set(cache_key, result)
        
        return result
```

## 配置示例

```yaml
# config.yaml
routing:
  mode: "hybrid"  # hybrid | rules_only | llm_only
  
  llm:
    enabled: true
    url: "http://intent-llm:11434"
    model: "qwen2.5:1.5b"
    timeout: 5.0  # 超时时间 (秒)
    confidence_threshold: 0.6  # 置信度阈值
    
  cache:
    enabled: true
    ttl: 3600  # 1 小时
    max_size: 1000
    
  fallback:
    enabled: true  # LLM 失败时降级到规则
    log_fallbacks: true  # 记录降级事件
```

## 性能指标

| 路由模式 | P50 延迟 | P95 延迟 | P99 延迟 |
|---------|---------|---------|---------|
| Rules Only | <5ms | <10ms | <20ms |
| LLM Only | 80ms | 150ms | 200ms |
| Hybrid (Cache Hit) | <5ms | <10ms | <20ms |
| Hybrid (Cache Miss, LLM) | 90ms | 160ms | 220ms |
| Hybrid (Cache Miss, Fallback) | <10ms | <20ms | <30ms |

## 影响

- ✅ 无 LLM 时系统仍可工作（规则路由）
- ✅ LLM 故障时自动降级（高可用）
- ✅ 缓存提高高频查询性能
- ✅ 可配置模式便于调试和灰度

## 合规性

本决策符合架构原则：
- AP-02 (故障隔离): LLM 故障不影响整体
- AP-03 (渐进式复杂): 可从 rules_only 开始
- AP-04 (可观测性): 记录降级事件便于监控

---

**END OF ADR**

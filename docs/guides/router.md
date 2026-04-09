# 路由配置指南

**版本**: v0.2  
**日期**: 2026-04-09  
**状态**: 计划中 (v0.3)

---

## 🎯 路由概览

路由功能允许根据查询内容自动选择合适的适配器。

```
用户查询
    │
    ▼
┌─────────────────┐
│   Router        │  ← 智能路由
└────────┬────────┘
         │
    ┌────┴────┬──────────┬────────┐
    ▼         ▼          ▼        ▼
┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐
│Adapter│ │Adapter│ │Adapter│ │Adapter│
│ A     │ │ B     │ │ C     │ │ D     │
└───────┘ └───────┘ └───────┘ └───────┘
```

**路由策略**:
1. 关键词路由 (v0.3 - 计划中)
2. LLM 意图识别 (v0.4 - 计划中)
3. 混合路由 (v0.5 - 计划中)

---

## 🔑 关键词路由 (计划中)

### 基本使用

```python
from cozy_memory import (
    MemoryService,
    RouterAdapter,
    MemobaseAdapter,
    SQLiteAdapter
)

# 定义路由规则
rules = {
    "pricing": ["价格", "费用", "成本", "报价", "付费"],
    "technical": ["技术", "代码", "架构", "API", "开发"],
    "general": ["*"]  # 默认路由
}

# 创建适配器映射
adapters = {
    "pricing": MemobaseAdapter(api_key="xxx", project_id="yyy"),
    "technical": SQLiteAdapter(db_path="./tech.db"),
    "general": MemobaseAdapter(api_key="xxx", project_id="yyy"),
}

# 创建路由器
router = RouterAdapter(rules=rules, adapters=adapters)

# 使用路由器
service = MemoryService(adapter=router)

# 自动路由
await service.add("这个功能多少钱？")  # → pricing adapter
await service.add("API 怎么调用？")     # → technical adapter
await service.add("你好")              # → general adapter
```

---

### 路由规则语法

#### 简单关键词

```python
rules = {
    "pricing": ["价格", "费用"],  # 包含任一关键词
    "technical": ["技术", "代码"],
}
```

#### 正则表达式

```python
import re

rules = {
    "pricing": [re.compile(r"\d+元"), re.compile(r"\$[\d.]+")],
    "date": [re.compile(r"\d{4}-\d{2}-\d{2}")],
}
```

#### 组合规则

```python
rules = {
    "vip_pricing": [
        {"all": ["VIP", "价格"]},  # 同时包含
        {"any": ["会员费", "订阅费"]},  # 包含任一
    ],
    "general": ["*"],
}
```

#### 优先级

```python
rules = {
    "high_priority": {
        "keywords": ["紧急", "重要"],
        "priority": 10  # 高优先级
    },
    "normal": {
        "keywords": ["一般", "普通"],
        "priority": 1  # 正常优先级
    },
    "default": {
        "keywords": ["*"],
        "priority": 0  # 最低优先级
    },
}
```

---

### 自定义路由函数

```python
from cozy_memory import RouterAdapter, BaseAdapter

def custom_router(query: str, adapters: dict) -> BaseAdapter:
    """自定义路由逻辑"""
    
    # 示例：根据查询长度路由
    if len(query) < 10:
        return adapters["short"]
    elif len(query) < 100:
        return adapters["medium"]
    else:
        return adapters["long"]

# 使用自定义路由
router = RouterAdapter(
    adapters={
        "short": MemobaseAdapter(...),
        "medium": SQLiteAdapter(...),
        "long": MemobaseAdapter(...),
    },
    router_func=custom_router
)

service = MemoryService(adapter=router)
```

---

## 🧠 LLM 意图识别 (计划中)

### 基本使用

```python
from cozy_memory import LLMRouterAdapter, MemobaseAdapter

# 创建 LLM 路由器
router = LLMRouterAdapter(
    model="gpt-3.5-turbo",  # 或本地模型
    api_key="your-openai-key",
    adapters={
        "pricing": MemobaseAdapter(...),
        "technical": MemobaseAdapter(...),
        "general": MemobaseAdapter(...),
    }
)

service = MemoryService(adapter=router)

# 自动意图识别
await service.add("这个多少钱？")  # → 识别为 pricing
```

---

### 自定义意图定义

```python
from cozy_memory import LLMRouterAdapter

# 定义意图
intents = {
    "pricing": {
        "description": "询问价格、费用、成本相关问题",
        "examples": [
            "这个功能多少钱？",
            "收费标准是什么？",
            "有优惠吗？",
        ]
    },
    "technical": {
        "description": "技术咨询、API 使用、代码问题",
        "examples": [
            "API 怎么调用？",
            "有代码示例吗？",
            "支持哪些语言？",
        ]
    },
    "general": {
        "description": "其他一般性问题",
        "examples": [
            "你好",
            "谢谢",
            "再见",
        ]
    },
}

router = LLMRouterAdapter(
    model="gpt-3.5-turbo",
    intents=intents,
    adapters={...}
)
```

---

### 使用本地模型

```python
from cozy_memory import LLMRouterAdapter

# 使用本地 Ollama 模型
router = LLMRouterAdapter(
    model="ollama/llama2",
    api_base="http://localhost:11434",
    adapters={...}
)

# 或使用其他兼容 OpenAI API 的模型
router = LLMRouterAdapter(
    model="local-model",
    api_base="http://localhost:8000/v1",
    api_key="not-needed",
    adapters={...}
)
```

---

## 🔄 混合路由 (计划中)

### 关键词 + LLM

```python
from cozy_memory import HybridRouterAdapter

# 第一层：关键词路由 (快速)
# 第二层：LLM 路由 (准确)
router = HybridRouterAdapter(
    keyword_router=RouterAdapter(rules=rules, adapters=adapters),
    llm_router=LLMRouterAdapter(model="gpt-3.5-turbo", adapters=adapters),
    strategy="fallback"  # 关键词失败时用 LLM
)

service = MemoryService(adapter=router)
```

---

### 路由策略

#### 1. Fallback 策略

```python
router = HybridRouterAdapter(
    primary=keyword_router,
    fallback=llm_router,
    strategy="fallback"
)
```

#### 2. Voting 策略

```python
router = HybridRouterAdapter(
    routers=[keyword_router, llm_router, embedding_router],
    strategy="voting"  # 多数投票
)
```

#### 3. Confidence 策略

```python
router = HybridRouterAdapter(
    routers=[
        (keyword_router, 0.3),  # 权重 30%
        (llm_router, 0.5),      # 权重 50%
        (embedding_router, 0.2) # 权重 20%
    ],
    strategy="weighted"
)
```

---

## 📊 路由监控

### 路由日志

```python
from cozy_memory import RouterAdapter, LoggingMiddleware

router = RouterAdapter(
    rules=rules,
    adapters=adapters,
    middleware=[LoggingMiddleware()]
)
```

### 路由统计

```python
from cozy_memory import RouterAdapter, MetricsMiddleware

router = RouterAdapter(
    rules=rules,
    adapters=adapters,
    middleware=[MetricsMiddleware()]
)

# 获取统计
stats = router.get_stats()
print(stats)
# {
#     "pricing": {"count": 100, "avg_time_ms": 5},
#     "technical": {"count": 200, "avg_time_ms": 10},
#     "general": {"count": 500, "avg_time_ms": 3},
# }
```

---

## 🎯 最佳实践

### 1. 从简单开始

```python
# 先使用关键词路由
rules = {
    "pricing": ["价格", "费用"],
    "general": ["*"],
}

# 需要时再升级到 LLM 路由
```

### 2. 测试路由规则

```python
def test_routing():
    test_cases = [
        ("这个多少钱？", "pricing"),
        ("API 怎么用？", "technical"),
        ("你好", "general"),
    ]
    
    for query, expected in test_cases:
        adapter = router.route(query)
        assert adapter.name == expected
```

### 3. 监控路由准确率

```python
# 记录路由决策
router.log_decision(
    query="查询内容",
    selected_adapter="pricing",
    confidence=0.9
)

# 定期分析准确率
accuracy = router.calculate_accuracy()
```

### 4. 优化路由性能

```python
# 缓存路由结果
router = RouterAdapter(
    rules=rules,
    adapters=adapters,
    cache_ttl=3600  # 缓存 1 小时
)

# 预编译正则
rules = {
    "pricing": [re.compile(r"价格|费用")],  # 预编译
}
```

---

## 🦀 维护者注释

**路由设计原则**:

1. **渐进式**: 从关键词到 LLM，逐步升级
2. **可配置**: 规则可灵活配置
3. **可监控**: 记录路由决策和准确率
4. **可测试**: 易于测试路由逻辑

**性能考虑**:

- 关键词路由: <1ms
- LLM 路由: ~100-500ms
- 混合路由: 取决于策略

**准确率优化**:

1. 收集真实查询数据
2. 分析路由错误案例
3. 调整关键词规则
4. 优化 LLM prompt
5. 定期重新训练

---

## 📚 相关文档

- [快速开始](./getting-started.md)
- [配置指南](./configuration.md)
- [适配器指南](./adapters.md)

---

**最后更新**: 2026-04-09  
**维护者**: 蟹小五 🦀

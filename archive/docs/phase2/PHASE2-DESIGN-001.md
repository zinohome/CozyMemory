# Phase 2 详细设计文档

**文档编号**: PHASE2-DESIGN-001  
**版本**: 1.0  
**日期**: 2026-04-06  
**阶段**: Phase 2 (缓存层 + 智能路由)  
**作者**: AI 架构师  
**审批**: 张老师  

---

## 📋 文档控制

| 版本 | 日期 | 作者 | 变更说明 | 审批 |
|------|------|------|----------|------|
| 1.0 | 2026-04-06 | AI 架构师 | 初稿 | 张老师 |

---

## 📊 目录

1. [概述](#1-概述)
2. [架构设计](#2-架构设计)
3. [缓存层设计](#3-缓存层设计)
4. [智能路由设计](#4-智能路由设计)
5. [结果融合设计](#5-结果融合设计)
6. [API 设计](#6-api-设计)
7. [数据模型](#7-数据模型)
8. [测试计划](#8-测试计划)
9. [实施计划](#9-实施计划)
10. [风险评估](#10-风险评估)
11. [维护者注释](#11-维护者注释)

---

## 1. 概述

### 1.1 目标

Phase 2 的目标是为 CozyMemory 添加**缓存层**和**智能路由**功能，提升系统性能和可扩展性。

### 1.2 范围

**包括**:
- ✅ Redis 缓存适配器
- ✅ 内存缓存 (LRU) 实现
- ✅ 缓存穿透/雪崩处理
- ✅ 意图识别路由
- ✅ 轮询路由
- ✅ 权重路由
- ✅ RRF (Reciprocal Rank Fusion) 结果融合
- ✅ 单元测试 (目标覆盖率 90%+)

**不包括**:
- ❌ 多引擎支持 (Phase 3)
- ❌ 生产部署 (Phase 4)
- ❌ 向量数据库集成 (Phase 3)

### 1.3 性能目标

| 指标 | Phase 1 基准 | Phase 2 目标 | 提升 |
|------|-------------|-------------|------|
| 查询延迟 (P50) | ~50ms (Mock) | <20ms (缓存命中) | 60%↓ |
| 查询延迟 (P95) | ~100ms | <50ms | 50%↓ |
| 吞吐量 | 100 req/s | 500 req/s | 5x |
| 缓存命中率 | N/A | >80% | - |

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                      FastAPI API Layer                   │
│                    (src/api/v1/routes.py)                │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                    MemoryService                         │
│                  (src/services/)                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │              RouterService (新增)                  │  │
│  │  - 意图识别路由                                    │  │
│  │  - 轮询路由                                        │  │
│  │  - 权重路由                                        │  │
│  └───────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────┐  │
│  │              CacheService (新增)                   │  │
│  │  - Redis 缓存                                      │  │
│  │  - 内存缓存 (LRU)                                  │  │
│  │  - 缓存策略                                        │  │
│  └───────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│  Cache Layer    │     │  Adapter Layer  │
│  (新增)         │     │  (Phase 1)      │
│  - RedisCache   │     │  - BaseAdapter  │
│  - MemoryCache  │     │  - Memobase...  │
└─────────────────┘     └─────────────────┘
```

### 2.2 模块依赖

```
src/
├── cache/              # 新增：缓存层
│   ├── __init__.py
│   ├── base.py         # 缓存基类
│   ├── redis_cache.py  # Redis 缓存实现
│   └── memory_cache.py # 内存缓存 (LRU)
├── routers/            # 新增：路由层
│   ├── __init__.py
│   ├── base.py         # 路由基类
│   ├── intent_router.py # 意图识别路由
│   ├── round_robin_router.py # 轮询路由
│   └── weighted_router.py # 权重路由
├── fusion/             # 新增：结果融合
│   ├── __init__.py
│   ├── rrf.py          # RRF 算法
│   └── weighted.py     # 权重融合
├── services/           # 扩展：服务层
│   ├── memory_service.py (Phase 1)
│   ├── router_service.py (新增)
│   └── cache_service.py (新增)
├── adapters/           # Phase 1 (保持不变)
├── models/             # 扩展：新增缓存和路由模型
└── utils/              # 扩展：新增工具函数
```

---

## 3. 缓存层设计

### 3.1 缓存策略

#### 3.1.1 缓存层级

```
L1: 内存缓存 (LRU) - 10ms, 1000 条记录
     ↓ (未命中)
L2: Redis 缓存 - 20ms, 10 万条记录
     ↓ (未命中)
L3: 记忆引擎 - 50-200ms
```

#### 3.1.2 缓存键设计

```python
# 查询缓存键
"cozymemory:query:{user_id}:{query_hash}:{memory_type}:{limit}"

# 单条记忆缓存键
"cozymemory:memory:{memory_id}"

# 用户记忆列表缓存键
"cozymemory:user:{user_id}:memories:{memory_type}:{page}"

# 示例
"cozymemory:query:user_123:a1b2c3d4:preference:10"
"cozymemory:memory:mem_5678"
```

#### 3.1.3 缓存失效策略

| 事件 | 失效范围 | 说明 |
|------|---------|------|
| 创建记忆 | 用户查询缓存 | 失效该用户的所有查询缓存 |
| 更新记忆 | 单条 + 用户查询 | 失效该记忆和该用户查询缓存 |
| 删除记忆 | 单条 + 用户查询 | 失效该记忆和该用户查询缓存 |
| 定时清理 | 过期缓存 | TTL 自动过期 |

### 3.2 缓存基类设计

```python
# src/cache/base.py
class BaseCache(ABC):
    """缓存基类"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        pass
    
    @abstractmethod
    async def clear(self, pattern: str) -> int:
        """批量清除缓存"""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        pass
```

### 3.3 Redis 缓存实现

```python
# src/cache/redis_cache.py
class RedisCache(BaseCache):
    """Redis 缓存实现"""
    
    def __init__(
        self,
        redis_url: str,
        prefix: str = "cozymemory:",
        default_ttl: int = 300,
    ):
        self.redis = redis.asyncio.from_url(redis_url)
        self.prefix = prefix
        self.default_ttl = default_ttl
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
        }
    
    async def get(self, key: str) -> Optional[Any]:
        full_key = f"{self.prefix}{key}"
        data = await self.redis.get(full_key)
        if data:
            self._stats["hits"] += 1
            return pickle.loads(data)
        self._stats["misses"] += 1
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        full_key = f"{self.prefix}{key}"
        ttl = ttl or self.default_ttl
        await self.redis.setex(full_key, ttl, pickle.dumps(value))
        self._stats["sets"] += 1
        return True
    
    # ... 其他方法实现
```

### 3.4 内存缓存实现 (LRU)

```python
# src/cache/memory_cache.py
from collections import OrderedDict

class MemoryCache(BaseCache):
    """内存缓存 (LRU) 实现"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
        }
    
    async def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            entry = self.cache[key]
            # 检查 TTL
            if entry["expires_at"] and time.time() > entry["expires_at"]:
                del self.cache[key]
                self._stats["misses"] += 1
                return None
            # LRU: 移到末尾
            self.cache.move_to_end(key)
            self._stats["hits"] += 1
            return entry["value"]
        self._stats["misses"] += 1
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = {
            "value": value,
            "expires_at": time.time() + (ttl or self.default_ttl) if ttl != 0 else None,
        }
        # LRU 驱逐
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)
            self._stats["evictions"] += 1
        return True
    
    # ... 其他方法实现
```

### 3.5 缓存穿透/雪崩处理

#### 3.5.1 缓存穿透 (查询不存在的数据)

**解决方案**: 布隆过滤器 + 空值缓存

```python
class CacheWithProtection(BaseCache):
    """带保护的缓存"""
    
    def __init__(self, cache: BaseCache):
        self.cache = cache
        self.bloom_filter = set()  # 简化版，生产用 pybloom
        self.null_cache_ttl = 60  # 空值缓存 1 分钟
    
    async def get_with_protection(self, key: str) -> Optional[Any]:
        # 检查布隆过滤器
        if key not in self.bloom_filter:
            # 数据肯定不存在，返回 None
            return None
        
        # 正常缓存查询
        data = await self.cache.get(key)
        
        # 如果是空值标记，返回 None
        if data == "__NULL__":
            return None
        
        return data
    
    async def set_with_protection(
        self,
        key: str,
        value: Optional[Any],
        ttl: Optional[int] = None
    ) -> bool:
        # 添加到布隆过滤器
        self.bloom_filter.add(key)
        
        # 如果值为 None，存储空值标记
        if value is None:
            return await self.cache.set(key, "__NULL__", self.null_cache_ttl)
        
        return await self.cache.set(key, value, ttl)
```

#### 3.5.2 缓存雪崩 (大量缓存同时过期)

**解决方案**: 随机 TTL + 热点数据永不过期

```python
class CacheWithAntiAvalanche(BaseCache):
    """防雪崩缓存"""
    
    def __init__(self, cache: BaseCache):
        self.cache = cache
        self.hot_keys = set()  # 热点数据键
    
    async def set_with_jitter(
        self,
        key: str,
        value: Any,
        base_ttl: int,
        jitter_ratio: float = 0.2
    ) -> bool:
        # 添加随机抖动 (±20%)
        jitter = random.uniform(-jitter_ratio, jitter_ratio)
        ttl = int(base_ttl * (1 + jitter))
        
        # 热点数据延长 TTL
        if key in self.hot_keys:
            ttl *= 2
        
        return await self.cache.set(key, value, ttl)
    
    def mark_as_hot(self, key: str):
        """标记为热点数据"""
        self.hot_keys.add(key)
```

---

## 4. 智能路由设计

### 4.1 路由策略

#### 4.1.1 意图识别路由

根据查询内容自动选择最佳引擎：

```python
# src/routers/intent_router.py
class IntentRouter(BaseRouter):
    """意图识别路由"""
    
    # 意图关键词映射
    INTENT_KEYWORDS = {
        "memobase": ["偏好", "profile", "preference", "习惯", "喜欢"],
        "mem0": ["对话", "chat", "conversation", "上下文", "历史"],
        "cognee": ["知识", "knowledge", "文档", "document", "图谱"],
    }
    
    async def route(self, query: MemoryQuery) -> List[str]:
        """根据意图返回引擎列表"""
        query_text = (query.query or "").lower()
        
        # 计算每个引擎的得分
        scores = {}
        for engine, keywords in self.INTENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in query_text)
            scores[engine] = score
        
        # 返回得分最高的引擎
        if max(scores.values()) == 0:
            return self.enabled_engines  # 无明确意图，返回所有
        
        sorted_engines = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [engine for engine, score in sorted_engines if score > 0]
```

#### 4.1.2 轮询路由

均匀分配请求到各引擎：

```python
# src/routers/round_robin_router.py
class RoundRobinRouter(BaseRouter):
    """轮询路由"""
    
    def __init__(self, enabled_engines: List[str]):
        self.enabled_engines = enabled_engines
        self._counter = 0
        self._lock = asyncio.Lock()
    
    async def route(self, query: MemoryQuery) -> List[str]:
        async with self._lock:
            # 简单轮询：每次返回一个引擎
            engine = self.enabled_engines[self._counter % len(self.enabled_engines)]
            self._counter += 1
            return [engine]
```

#### 4.1.3 权重路由

根据配置的权重分配：

```python
# src/routers/weighted_router.py
class WeightedRouter(BaseRouter):
    """权重路由"""
    
    def __init__(
        self,
        engine_weights: Dict[str, float],
    ):
        self.engine_weights = engine_weights
        self.enabled_engines = list(engine_weights.keys())
    
    async def route(self, query: MemoryQuery) -> List[str]:
        # 根据权重随机选择
        engines = random.choices(
            self.enabled_engines,
            weights=[self.engine_weights[e] for e in self.enabled_engines],
            k=len(self.enabled_engines)
        )
        return engines
```

### 4.2 路由配置

```yaml
# 配置示例 (通过 settings 加载)
ROUTER_STRATEGY: intent  # intent, round_robin, weighted

# 意图路由配置
INTENT_ROUTER:
  enabled_engines:
    - memobase
    - mem0
    - cognee
  default_engine: memobase

# 权重路由配置
WEIGHTED_ROUTER:
  memobase: 0.6
  mem0: 0.3
  cognee: 0.1
```

---

## 5. 结果融合设计

### 5.1 RRF (Reciprocal Rank Fusion)

```python
# src/fusion/rrf.py
class RRFFusion:
    """RRF 结果融合"""
    
    def __init__(self, k: int = 60):
        self.k = k  # RRF 常数
    
    def fuse(
        self,
        result_lists: List[List[Memory]],
        engine_names: List[str]
    ) -> List[Memory]:
        """
        融合多个引擎的结果
        
        Args:
            result_lists: 每个引擎的结果列表 [[mem1, mem2], [mem3, mem4], ...]
            engine_names: 引擎名称列表
        
        Returns:
            融合后的排序结果
        """
        # 计算每个记忆的 RRF 得分
        scores = defaultdict(float)
        memory_map = {}
        
        for result_list in result_lists:
            for rank, memory in enumerate(result_list, start=1):
                memory_id = memory.id
                score = 1.0 / (self.k + rank)
                scores[memory_id] += score
                
                if memory_id not in memory_map:
                    memory_map[memory_id] = memory
        
        # 按得分排序
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        
        return [memory_map[mid] for mid in sorted_ids]
```

### 5.2 权重融合

```python
# src/fusion/weighted.py
class WeightedFusion:
    """权重融合"""
    
    def __init__(self, engine_weights: Dict[str, float]):
        self.engine_weights = engine_weights
    
    def fuse(
        self,
        result_lists: List[List[Memory]],
        engine_names: List[str]
    ) -> List[Memory]:
        """
        根据引擎权重融合结果
        
        Args:
            result_lists: 每个引擎的结果列表
            engine_names: 引擎名称列表
        
        Returns:
            融合后的排序结果
        """
        scores = defaultdict(float)
        memory_map = {}
        
        for result_list, engine_name in zip(result_lists, engine_names):
            weight = self.engine_weights.get(engine_name, 1.0)
            
            for rank, memory in enumerate(result_list, start=1):
                memory_id = memory.id
                # 权重 * 倒数排名
                score = weight * (1.0 / rank)
                scores[memory_id] += score
                
                if memory_id not in memory_map:
                    memory_map[memory_id] = memory
        
        # 按得分排序
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        
        return [memory_map[mid] for mid in sorted_ids]
```

### 5.3 去重处理

```python
def deduplicate_memories(memories: List[Memory]) -> List[Memory]:
    """
    去重记忆列表
    
    策略:
    1. 按 memory_id 去重
    2. 保留置信度最高的
    """
    memory_dict = {}
    
    for memory in memories:
        if memory.id not in memory_dict:
            memory_dict[memory.id] = memory
        else:
            # 保留置信度更高的
            existing = memory_dict[memory.id]
            if memory.confidence and (not existing.confidence or memory.confidence > existing.confidence):
                memory_dict[memory.id] = memory
    
    return list(memory_dict.values())
```

---

## 6. API 设计

### 6.1 新增 API 端点

```python
# 缓存管理 API (仅管理员)
POST   /api/v1/cache/clear          # 清除缓存
GET    /api/v1/cache/stats          # 缓存统计
POST   /api/v1/cache/warmup         # 预热缓存

# 路由配置 API (仅管理员)
GET    /api/v1/router/config        # 获取路由配置
PUT    /api/v1/router/config        # 更新路由配置
GET    /api/v1/router/stats         # 路由统计

# 健康检查增强
GET    /api/v1/health/detailed      # 详细健康检查 (包含缓存和路由)
```

### 6.2 请求/响应模型

```python
# src/models/cache.py
class CacheStats(BaseModel):
    """缓存统计"""
    hits: int
    misses: int
    hit_rate: float
    total_keys: int
    memory_usage_mb: float
    uptime_seconds: int

class CacheClearRequest(BaseModel):
    """清除缓存请求"""
    pattern: str = "*"  # 支持通配符
    confirm: bool = False  # 确认标志

class RouterStats(BaseModel):
    """路由统计"""
    total_requests: int
    engine_distribution: Dict[str, int]
    avg_latency_ms: float
    strategy: str
```

---

## 7. 数据模型

### 7.1 新增模型

```python
# src/models/cache.py
class CacheEntry(BaseModel):
    """缓存条目"""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime]
    hit_count: int = 0

# src/models/router.py
class RouterConfig(BaseModel):
    """路由配置"""
    strategy: str  # intent, round_robin, weighted
    enabled_engines: List[str]
    weights: Optional[Dict[str, float]] = None
    intent_keywords: Optional[Dict[str, List[str]]] = None
```

---

## 8. 测试计划

### 8.1 单元测试

#### 缓存层测试 (目标：90%+ 覆盖率)

| 测试文件 | 测试数 | 说明 |
|---------|--------|------|
| test_cache_base.py | 8 | 缓存基类测试 |
| test_redis_cache.py | 15 | Redis 缓存测试 (Mock) |
| test_memory_cache.py | 15 | 内存缓存测试 |
| test_cache_protection.py | 10 | 缓存穿透/雪崩测试 |
| test_cache_service.py | 12 | 缓存服务测试 |

#### 路由层测试 (目标：90%+ 覆盖率)

| 测试文件 | 测试数 | 说明 |
|---------|--------|------|
| test_router_base.py | 6 | 路由基类测试 |
| test_intent_router.py | 12 | 意图识别路由测试 |
| test_round_robin_router.py | 8 | 轮询路由测试 |
| test_weighted_router.py | 10 | 权重路由测试 |
| test_router_service.py | 10 | 路由服务测试 |

#### 融合层测试 (目标：90%+ 覆盖率)

| 测试文件 | 测试数 | 说明 |
|---------|--------|------|
| test_rrf_fusion.py | 10 | RRF 算法测试 |
| test_weighted_fusion.py | 8 | 权重融合测试 |
| test_deduplication.py | 6 | 去重测试 |

### 8.2 集成测试

| 测试文件 | 测试数 | 说明 |
|---------|--------|------|
| test_cache_integration.py | 8 | 缓存集成测试 |
| test_router_integration.py | 8 | 路由集成测试 |
| test_fusion_integration.py | 6 | 融合集成测试 |

### 8.3 性能测试

| 测试文件 | 测试数 | 说明 |
|---------|--------|------|
| test_cache_benchmark.py | 5 | 缓存性能基准 |
| test_router_benchmark.py | 5 | 路由性能基准 |

**总测试数**: ~154 个  
**目标覆盖率**: 90%+

---

## 9. 实施计划

### 9.1 时间安排

| 任务 | 预计时间 | 优先级 |
|------|---------|--------|
| Day 1 上午 | 缓存层实现 | P0 |
| Day 1 下午 | 缓存层测试 | P0 |
| Day 2 上午 | 路由层实现 | P0 |
| Day 2 下午 | 融合层实现 + 测试 | P0 |
| Day 3 上午 | 集成测试 + 性能测试 | P1 |
| Day 3 下午 | 文档 + 代码审查 | P1 |

### 9.2 实施步骤

#### Step 1: 缓存层实现

1. 创建 `src/cache/` 目录结构
2. 实现 `BaseCache` 抽象基类
3. 实现 `RedisCache` (使用 Mock 测试)
4. 实现 `MemoryCache` (LRU)
5. 实现缓存保护机制 (穿透/雪崩)
6. 编写单元测试

#### Step 2: 路由层实现

1. 创建 `src/routers/` 目录结构
2. 实现 `BaseRouter` 抽象基类
3. 实现 `IntentRouter`
4. 实现 `RoundRobinRouter`
5. 实现 `WeightedRouter`
6. 编写单元测试

#### Step 3: 融合层实现

1. 创建 `src/fusion/` 目录结构
2. 实现 `RRFFusion`
3. 实现 `WeightedFusion`
4. 实现去重函数
5. 编写单元测试

#### Step 4: 服务层集成

1. 创建 `RouterService`
2. 创建 `CacheService`
3. 修改 `MemoryService` 使用缓存和路由
4. 更新 API 路由
5. 编写集成测试

#### Step 5: 测试与优化

1. 运行所有测试
2. 检查覆盖率
3. 性能基准测试
4. 代码优化
5. 文档更新

---

## 10. 风险评估

### 10.1 技术风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| Redis 连接不稳定 | 高 | 低 | 降级到内存缓存、重试机制 |
| 缓存一致性问题 | 中 | 中 | 失效策略、版本号 |
| 路由策略效果不佳 | 中 | 中 | A/B 测试、可配置切换 |
| RRF 参数调优困难 | 低 | 中 | 默认值 + 可配置 |

### 10.2 进度风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 测试覆盖率不达标 | 中 | 低 | 提前编写测试、TDD |
| 性能优化耗时 | 中 | 中 | 设定明确目标、及时止损 |
| 集成问题 | 高 | 低 | 持续集成、早集成早发现问题 |

---

## 11. 维护者注释

### 11.1 为什么选择 LRU 作为内存缓存策略？

**原因**:
1. **简单高效**: LRU 实现简单，O(1) 时间复杂度
2. **适合场景**: 记忆查询符合"最近使用"模式
3. **内存可控**: 固定大小限制，避免内存泄漏

**替代方案**:
- LFU (Least Frequently Used): 适合热点数据明显的场景
- ARC (Adaptive Replacement Cache): 更智能，但实现复杂

**决策**: Phase 2 使用 LRU，Phase 3 可根据实际数据评估是否升级。

---

### 11.2 为什么 RRF 的 k 值设为 60？

**原因**:
1. **经验值**: 信息检索领域的经验值
2. **平衡性**: k 太小偏向高排名，k 太大趋向平均
3. **可调性**: 通过配置可调整

**调优建议**:
```python
# 根据实际效果调整
if 查询类型 == "精确查询":
    k = 30  # 更看重排名
elif 查询类型 == "模糊查询":
    k = 90  # 更平均
```

---

### 11.3 缓存 TTL 如何设置？

**推荐配置**:
```python
# 开发环境
CACHE_TTL = 60  # 1 分钟，快速验证

# 生产环境
CACHE_TTL = 300  # 5 分钟 (默认)
HOT_CACHE_TTL = 600  # 10 分钟 (热点数据)
NULL_CACHE_TTL = 60  # 1 分钟 (空值缓存)
```

**调优策略**:
1. 监控缓存命中率
2. 如果命中率 < 50%，增加 TTL
3. 如果数据更新频繁，减少 TTL
4. 使用动态 TTL (根据访问频率)

---

### 11.4 路由策略如何选择？

**推荐**:
```python
# 单引擎：不需要路由
ROUTER_STRATEGY = "none"

# 2-3 个引擎：意图识别
ROUTER_STRATEGY = "intent"

# 多引擎负载均衡：轮询
ROUTER_STRATEGY = "round_robin"

# 引擎性能差异大：权重
ROUTER_STRATEGY = "weighted"
```

---

### 11.5 性能优化建议

1. **缓存层**:
   - 使用连接池 (Redis)
   - 批量操作 (pipeline)
   - 压缩大对象 (gzip)

2. **路由层**:
   - 缓存路由决策
   - 异步并发查询
   - 超时控制

3. **融合层**:
   - 流式处理 (边查询边融合)
   - 提前终止 (达到数量即停止)

---

## 📚 参考文档

- [Redis 官方文档](https://redis.io/docs/)
- [RRF 论文](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [缓存设计模式](https://aws.amazon.com/caching/)
- [CozyMemory Phase 1 文档](../phase1/)

---

**文档生成时间**: 2026-04-06 12:30  
**作者**: AI 架构师  
**审批**: 张老师  
**状态**: ✅ 已批准，可开始实施

🦀 **Design Excellence Achieved!** 🎉

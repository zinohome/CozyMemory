# CozyMemory 架构设计

**版本**: v0.2  
**日期**: 2026-04-09  
**状态**: 已实现

---

## 🏗️ 架构概览

### 两层架构

```
┌─────────────────────────────────────┐
│         Application Layer           │
│      (你的 Python 项目)              │
└──────────────┬──────────────────────┘
               │
               │ 直接导入
               ▼
┌─────────────────────────────────────┐
│         CozyMemory Library          │
│  ┌─────────────────────────────┐    │
│  │   Public API (Service)      │    │
│  │   - MemoryService           │    │
│  │   - MemoryManager           │    │
│  └──────────────┬──────────────┘    │
│                 │                    │
│  ┌──────────────▼──────────────┐    │
│  │   Adapter Layer             │    │
│  │   - BaseAdapter             │    │
│  │   - MemobaseAdapter         │    │
│  │   - MemobaseMockAdapter     │    │
│  │   - SQLiteAdapter (TODO)    │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

**关键变化**:
- ❌ 移除 API Gateway 层
- ❌ 移除路由层
- ❌ 移除缓存层
- ✅ 简化为 2 层：Service + Adapter

---

## 📦 核心组件

### 1. MemoryService (服务层)

**职责**: 提供统一的记忆管理 API

```python
class MemoryService:
    def __init__(self, adapter: BaseAdapter):
        self.adapter = adapter
    
    async def add(self, content: str, **kwargs) -> Memory:
        """添加记忆"""
    
    async def get(self, memory_id: str) -> Memory:
        """获取记忆"""
    
    async def search(self, query: str, **filters) -> List[Memory]:
        """搜索记忆"""
    
    async def update(self, memory_id: str, **updates) -> Memory:
        """更新记忆"""
    
    async def delete(self, memory_id: str) -> bool:
        """删除记忆"""
```

**设计原则**:
- 无状态 (Stateless)
- 线程安全 (Thread-safe)
- 异步优先 (Async-first)
- 类型完整 (Fully-typed)

---

### 2. Adapter Layer (适配器层)

**职责**: 抽象记忆存储引擎

```python
class BaseAdapter(ABC):
    """适配器基类"""
    
    @abstractmethod
    async def add(self, memory: Memory) -> Memory:
        pass
    
    @abstractmethod
    async def get(self, memory_id: str) -> Memory:
        pass
    
    @abstractmethod
    async def search(self, query: str, **filters) -> List[Memory]:
        pass
    
    @abstractmethod
    async def update(self, memory_id: str, updates: dict) -> Memory:
        pass
    
    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        pass
```

**已实现适配器**:

| 适配器 | 状态 | 用途 |
|--------|------|------|
| `MemobaseMockAdapter` | ✅ 已完成 | 本地开发/测试 |
| `MemobaseAdapter` | ✅ 已完成 | 生产环境 (Memobase) |
| `SQLiteAdapter` | 🔄 计划中 | 本地持久化 |
| `RedisAdapter` | 🔄 计划中 | 缓存层 |

---

## 📊 数据模型

### 核心模型

```python
class Memory(BaseModel):
    """记忆模型"""
    id: str
    content: str
    memory_type: MemoryType  # fact, event, preference, skill, conversation
    source: MemorySource     # memobase, local, manual
    metadata: dict
    created_at: datetime
    updated_at: datetime


class MemoryType(str, Enum):
    FACT = "fact"
    EVENT = "event"
    PREFERENCE = "preference"
    SKILL = "skill"
    CONVERSATION = "conversation"


class MemorySource(str, Enum):
    MEMOBASE = "memobase"
    LOCAL = "local"
    MANUAL = "manual"
```

**设计考虑**:
- **简洁**: 只保留必要字段
- **可扩展**: metadata 支持任意扩展
- **类型安全**: Pydantic 验证
- **向后兼容**: 字段可选，有默认值

---

## 🔄 数据流

### 添加记忆流程

```
用户代码
    │
    │ memory_service.add("用户喜欢咖啡")
    ▼
MemoryService
    │
    │ 1. 验证数据
    │ 2. 创建 Memory 对象
    │ 3. 调用适配器
    ▼
MemobaseAdapter
    │
    │ 1. 转换为 Memobase 格式
    │ 2. 调用 Memobase API
    │ 3. 解析响应
    ▼
Memobase API
    │
    │ 存储记忆
    ▼
返回 Memory 对象
```

### 搜索记忆流程

```
用户代码
    │
    │ memory_service.search("咖啡")
    ▼
MemoryService
    │
    │ 1. 验证查询
    │ 2. 调用适配器
    ▼
MemobaseAdapter
    │
    │ 1. 转换为 Memobase 查询
    │ 2. 调用 Memobase API
    │ 3. 解析响应
    ▼
Memobase API
    │
    │ 搜索记忆
    ▼
返回 List[Memory]
```

---

## 🔧 配置管理

### 简化配置

```python
# v0.1 (过度设计)
config = Config(
    api_gateway="http://localhost:8000",
    database=DatabaseConfig(
        type="postgresql",
        host="localhost",
        port=5432,
        ...
    ),
    cache=CacheConfig(
        type="redis",
        host="localhost",
        port=6379,
        ...
    ),
    router=RouterConfig(
        type="llm",
        model="gpt-4",
        ...
    )
)

# v0.2 (简化)
config = Config(
    memobase_api_key="your-key",  # 可选
    memobase_project_id="your-project",  # 可选
)

# 甚至更简单 (使用 Mock)
service = MemoryService()  # 无需配置！
```

---

## 📈 扩展性设计

### 添加新适配器

```python
class SQLiteAdapter(BaseAdapter):
    """SQLite 本地存储适配器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    async def add(self, memory: Memory) -> Memory:
        # 实现 SQLite 插入逻辑
        pass
    
    # 实现其他方法...
```

**步骤**:
1. 继承 `BaseAdapter`
2. 实现 5 个抽象方法
3. 在 `MemoryService` 中使用

### 添加新功能

```python
# 在 MemoryService 中添加
async def batch_add(self, memories: List[Memory]) -> List[Memory]:
    """批量添加"""
    return await asyncio.gather(
        *[self.add(m) for m in memories]
    )
```

**原则**:
- 不破坏现有 API
- 保持向后兼容
- 添加单元测试

---

## 🦀 维护者注释

**为什么是两层架构？**

1. **简单**: 开发者容易理解
2. **直接**: 没有中间层损耗
3. **灵活**: 适配器可插拔
4. **可测试**: 每层独立测试

**为什么移除路由层？**

- **过早优化**: 99% 的场景不需要智能路由
- **增加复杂度**: LLM 路由增加延迟和成本
- **可后续添加**: 需要时作为可选层

**为什么移除缓存层？**

- **库的定位**: 缓存应由调用方管理
- **场景有限**: 记忆读取频率不高
- **可选实现**: 需要时用 RedisAdapter

**架构演进原则**:

> "先证明需要，再添加功能。而不是先添加功能，再证明需要。"

---

## 📚 相关文档

- [架构愿景](./00-vision.md)
- [架构决策](../decisions/)
- [适配器指南](../guides/adapters.md)

---

**最后更新**: 2026-04-09  
**维护者**: 蟹小五 🦀

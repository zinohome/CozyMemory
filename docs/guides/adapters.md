# 适配器使用指南

**版本**: v0.2  
**日期**: 2026-04-09  
**状态**: 已实现

---

## 🎯 适配器概览

适配器是 CozyMemory 的核心组件，负责抽象不同的记忆存储引擎。

```
┌─────────────────────────────────────┐
│         MemoryService               │
│         (统一 API)                  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│         Adapter Layer               │
│  ┌─────────────────────────────┐    │
│  │ BaseAdapter (抽象基类)      │    │
│  └─────────────────────────────┘    │
│  ┌─────────────────────────────┐    │
│  │ MemobaseMockAdapter         │    │ ← 默认
│  │ MemobaseAdapter             │    │
│  │ SQLiteAdapter (TODO)        │    │
│  │ RedisAdapter (TODO)         │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

---

## 📦 内置适配器

### 1. MemobaseMockAdapter (默认)

**用途**: 本地开发、测试、演示

**特点**:
- ✅ 零配置
- ✅ 内存存储
- ✅ 快速 (<1ms)
- ❌ 重启后数据丢失
- ❌ 单进程使用

**使用方式**:

```python
from cozy_memory import MemoryService

# 默认使用 Mock
service = MemoryService()

# 或显式指定
from cozy_memory import MemobaseMockAdapter
service = MemoryService(adapter=MemobaseMockAdapter())
```

**适用场景**:
- 本地开发
- 单元测试
- 快速原型
- 演示 Demo

---

### 2. MemobaseAdapter

**用途**: 生产环境，使用真实 Memobase 服务

**特点**:
- ✅ 持久化存储
- ✅ 多进程安全
- ✅ 支持搜索
- ❌ 需要 API Key
- ❌ 网络延迟 (~100ms)

**使用方式**:

```python
from cozy_memory import MemoryService, MemobaseAdapter

# 方式 1: 显式配置
service = MemoryService(
    adapter=MemobaseAdapter(
        api_key="your-api-key",
        project_id="your-project-id",
        api_base="https://api.memobase.io"  # 可选
    )
)

# 方式 2: 从环境变量读取
# export COZY_MEMOBASE_API_KEY=xxx
# export COZY_MEMOBASE_PROJECT_ID=yyy
service = MemoryService(adapter=MemobaseAdapter.from_env())

# 方式 3: 混合配置
service = MemoryService(
    adapter=MemobaseAdapter(
        api_key="explicit-key",  # 优先使用
        # project_id 从环境变量读取
    )
)
```

**配置项**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `api_key` | str | 无 | Memobase API Key |
| `project_id` | str | 无 | Memobase 项目 ID |
| `api_base` | str | `https://api.memobase.io` | API 端点 |
| `timeout` | float | 30.0 | 请求超时 (秒) |
| `max_retries` | int | 3 | 最大重试次数 |

**适用场景**:
- 生产环境
- 需要持久化
- 多进程/多实例
- 真实用户数据

---

### 3. SQLiteAdapter (计划中)

**用途**: 本地持久化存储

**特点**:
- ✅ 本地文件存储
- ✅ 无需外部服务
- ✅ 持久化
- ❌ 单进程
- ❌ 无网络同步

**使用方式** (计划中):

```python
from cozy_memory import MemoryService, SQLiteAdapter

service = MemoryService(
    adapter=SQLiteAdapter(
        db_path="./cozy_memory.db",
        pool_size=1,
        timeout=30
    )
)
```

**适用场景**:
- 本地应用
- 离线使用
- 个人项目

---

### 4. RedisAdapter (计划中)

**用途**: 缓存层，加速读取

**特点**:
- ✅ 高速缓存
- ✅ 支持 TTL
- ✅ 多进程安全
- ❌ 需要 Redis 服务
- ❌ 数据可能过期

**使用方式** (计划中):

```python
from cozy_memory import MemoryService, RedisAdapter

service = MemoryService(
    adapter=RedisAdapter(
        host="localhost",
        port=6379,
        db=0,
        password=None,
        ttl=3600  # 1 小时过期
    )
)
```

**适用场景**:
- 高频读取
- 缓存热点数据
- 配合其他适配器使用

---

## 🔧 自定义适配器

### 实现步骤

**Step 1: 继承 BaseAdapter**

```python
from cozy_memory import BaseAdapter, Memory
from typing import List, Optional

class MyCustomAdapter(BaseAdapter):
    """自定义适配器"""
    
    def __init__(self, config: dict):
        self.config = config
        self._init_storage()
    
    def _init_storage(self):
        """初始化存储"""
        # 例如：连接数据库、初始化文件等
        pass
```

**Step 2: 实现 5 个抽象方法**

```python
    async def add(self, memory: Memory) -> Memory:
        """添加记忆"""
        # 实现存储逻辑
        # 生成 ID
        # 保存到存储
        return memory
    
    async def get(self, memory_id: str) -> Optional[Memory]:
        """获取记忆"""
        # 根据 ID 查询
        # 返回 Memory 对象或 None
        pass
    
    async def search(self, query: str, **filters) -> List[Memory]:
        """搜索记忆"""
        # 实现搜索逻辑
        # 支持 filters: memory_type, source, limit, offset
        # 返回 Memory 列表
        pass
    
    async def update(self, memory_id: str, updates: dict) -> Optional[Memory]:
        """更新记忆"""
        # 根据 ID 更新
        # 返回更新后的 Memory 或 None
        pass
    
    async def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        # 根据 ID 删除
        # 返回是否成功
        pass
```

**Step 3: 使用自定义适配器**

```python
from cozy_memory import MemoryService

adapter = MyCustomAdapter(config={"db_path": "./my.db"})
service = MemoryService(adapter=adapter)

# 正常使用
await service.add("测试记忆")
results = await service.search("测试")
```

---

## 📝 适配器对比

| 适配器 | 配置 | 持久化 | 速度 | 多进程 | 适用场景 |
|--------|------|--------|------|--------|---------|
| **MemobaseMock** | 无需 | ❌ | ⚡⚡⚡ | ❌ | 开发/测试 |
| **Memobase** | API Key | ✅ | ⚡⚡ | ✅ | 生产环境 |
| **SQLite** (TODO) | 文件路径 | ✅ | ⚡⚡⚡ | ❌ | 本地应用 |
| **Redis** (TODO) | Redis 配置 | ⚠️ 临时 | ⚡⚡⚡⚡ | ✅ | 缓存层 |
| **自定义** | 自定 | 自定 | 自定 | 自定 | 特殊需求 |

---

## 🔄 适配器切换

### 开发环境 → 生产环境

```python
# config.py
import os
from cozy_memory import MemoryService, MemobaseMockAdapter, MemobaseAdapter

def create_service(environment="development"):
    if environment == "production":
        adapter = MemobaseAdapter.from_env()
    else:
        adapter = MemobaseMockAdapter()
    
    return MemoryService(adapter=adapter)

# 使用
service = create_service(os.getenv("ENV", "development"))
```

### 运行时切换

```python
from cozy_memory import MemoryService, MemobaseMockAdapter, MemobaseAdapter

# 初始使用 Mock
service = MemoryService()

# 切换到真实环境
service.adapter = MemobaseAdapter(api_key="xxx", project_id="yyy")

# 或创建新服务
service = MemoryService(adapter=MemobaseAdapter.from_env())
```

---

## 🎯 适配器选择建议

### 场景 1: 本地开发

```python
# 推荐：MemobaseMockAdapter
service = MemoryService()  # 默认就是 Mock
```

**理由**: 零配置，快速测试

---

### 场景 2: 单元测试

```python
import pytest
from cozy_memory import MemoryService, MemobaseMockAdapter

@pytest.fixture
def service():
    return MemoryService(adapter=MemobaseMockAdapter())

async def test_add_memory(service):
    memory = await service.add("测试")
    assert memory.content == "测试"
```

**理由**: 隔离外部依赖，测试快速

---

### 场景 3: 生产环境

```python
from cozy_memory import MemoryService, MemobaseAdapter

service = MemoryService(
    adapter=MemobaseAdapter(
        api_key=os.getenv("MEMOBASE_API_KEY"),
        project_id=os.getenv("MEMOBASE_PROJECT_ID"),
        max_retries=3,
        timeout=30
    )
)
```

**理由**: 持久化，多进程安全

---

### 场景 4: 混合使用 (缓存 + 持久化)

```python
# 计划中功能
from cozy_memory import MemoryService, CacheAdapter, MemobaseAdapter

# 缓存层 + 持久化层
cache = RedisAdapter(ttl=3600)
backend = MemobaseAdapter.from_env()

# 组合使用
adapter = CacheAdapter(backend=backend, cache=cache)
service = MemoryService(adapter=adapter)
```

**理由**: 加速读取，保持持久化

---

## 🦀 维护者注释

**适配器设计原则**:

1. **接口统一**: 所有适配器实现相同的 5 个方法
2. **可插拔**: 可以无缝切换适配器
3. **依赖倒置**: Service 依赖抽象 Adapter，不依赖具体实现
4. **单一职责**: 每个适配器只负责一种存储引擎

**适配器测试**:

```python
# 所有适配器应该通过相同的测试套件
class AdapterTestSuite:
    async def test_add(self, adapter):
        memory = await adapter.add(Memory(content="测试"))
        assert memory.id is not None
    
    async def test_get(self, adapter):
        # ...
    
    async def test_search(self, adapter):
        # ...
    
    async def test_update(self, adapter):
        # ...
    
    async def test_delete(self, adapter):
        # ...

# 对每个适配器运行测试
async def test_memobase_mock():
    adapter = MemobaseMockAdapter()
    suite = AdapterTestSuite()
    await suite.test_add(adapter)
    # ...
```

**性能考虑**:

- Mock: <1ms (内存)
- SQLite: ~5ms (本地文件)
- Redis: ~2ms (本地) / ~10ms (远程)
- Memobase: ~50-200ms (网络)

---

## 📚 相关文档

- [快速开始](./getting-started.md)
- [配置指南](./configuration.md)
- [API 参考](../api/reference.md)

---

**最后更新**: 2026-04-09  
**维护者**: 蟹小五 🦀

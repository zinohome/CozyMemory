# API 参考文档

**版本**: v0.2  
**日期**: 2026-04-09  
**状态**: 已实现

---

## 📦 包结构

```
cozy_memory/
├── __init__.py          # 包入口
├── service.py           # MemoryService
├── adapters/            # 适配器
│   ├── __init__.py
│   ├── base.py          # BaseAdapter
│   ├── mock.py          # MemobaseMockAdapter
│   └── memobase.py      # MemobaseAdapter
├── models/              # 数据模型
│   ├── __init__.py
│   └── memory.py        # Memory, MemoryType, MemorySource
├── config.py            # Config
└── utils/               # 工具函数
    ├── __init__.py
    ├── logger.py        # 日志
    └── helpers.py       # 辅助函数
```

---

## 🚀 快速导入

```python
# 推荐导入方式
from cozy_memory import MemoryService

# 完整导入
from cozy_memory import (
    MemoryService,
    Memory,
    MemoryType,
    MemorySource,
    Config,
    BaseAdapter,
    MemobaseMockAdapter,
    MemobaseAdapter,
)
```

---

## 📋 核心 API

### MemoryService

**主服务类，提供记忆管理功能**

#### 构造函数

```python
def __init__(
    self,
    adapter: Optional[BaseAdapter] = None,
    config: Optional[Config] = None
)
```

**参数**:
- `adapter`: 适配器实例，默认使用 `MemobaseMockAdapter()`
- `config`: 配置对象，可选

**示例**:

```python
# 使用默认 Mock 适配器
service = MemoryService()

# 使用指定适配器
service = MemoryService(adapter=MemobaseAdapter.from_env())

# 使用配置对象
config = Config(log_level="DEBUG")
service = MemoryService.from_config(config)
```

---

#### add() - 添加记忆

```python
async def add(
    self,
    content: str,
    memory_type: str = "fact",
    source: Optional[str] = None,
    metadata: Optional[dict] = None
) -> Memory
```

**参数**:
- `content`: 记忆内容 (必需)
- `memory_type`: 记忆类型，可选 `"fact"`, `"event"`, `"preference"`, `"skill"`, `"conversation"` (默认: `"fact"`)
- `source`: 记忆来源，默认自动检测
- `metadata`: 元数据字典，可选

**返回**: `Memory` 对象

**异常**:
- `ValueError`: 参数无效
- `MemoryError`: 存储失败

**示例**:

```python
# 简单添加
memory = await service.add("用户喜欢咖啡")

# 指定类型
memory = await service.add(
    "2026-04-09 会议",
    memory_type="event"
)

# 带元数据
memory = await service.add(
    "用户偏好 FastAPI",
    memory_type="preference",
    metadata={
        "category": "technology",
        "confidence": 0.9
    }
)

# 使用返回的 Memory 对象
print(f"ID: {memory.id}")
print(f"内容：{memory.content}")
print(f"类型：{memory.memory_type}")
print(f"创建时间：{memory.created_at}")
```

---

#### get() - 获取记忆

```python
async def get(self, memory_id: str) -> Optional[Memory]
```

**参数**:
- `memory_id`: 记忆 ID

**返回**: `Memory` 对象或 `None` (如果不存在)

**示例**:

```python
# 获取记忆
memory = await service.get("mem_123")

if memory:
    print(f"内容：{memory.content}")
else:
    print("记忆不存在")
```

---

#### search() - 搜索记忆

```python
async def search(
    self,
    query: str = "",
    memory_type: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 10,
    offset: int = 0
) -> List[Memory]
```

**参数**:
- `query`: 搜索关键词，空字符串表示获取全部
- `memory_type`: 按类型过滤，可选
- `source`: 按来源过滤，可选
- `limit`: 返回数量限制 (默认: 10)
- `offset`: 偏移量 (默认: 0)

**返回**: `List[Memory]` 记忆列表

**示例**:

```python
# 搜索关键词
results = await service.search("咖啡")

# 按类型过滤
facts = await service.search("", memory_type="fact")

# 分页
page1 = await service.search("", limit=10, offset=0)
page2 = await service.search("", limit=10, offset=10)

# 组合使用
results = await service.search(
    "技术",
    memory_type="preference",
    limit=5
)

# 遍历结果
for memory in results:
    print(f"- {memory.content}")
```

---

#### update() - 更新记忆

```python
async def update(
    self,
    memory_id: str,
    content: Optional[str] = None,
    memory_type: Optional[str] = None,
    metadata: Optional[dict] = None
) -> Optional[Memory]
```

**参数**:
- `memory_id`: 记忆 ID (必需)
- `content`: 新内容，可选
- `memory_type`: 新类型，可选
- `metadata`: 新元数据，可选 (会合并到现有元数据)

**返回**: 更新后的 `Memory` 对象或 `None`

**异常**:
- `ValueError`: 记忆不存在
- `ValueError`: 参数无效

**示例**:

```python
# 更新内容
updated = await service.update(
    "mem_123",
    content="更新后的内容"
)

# 更新类型
updated = await service.update(
    "mem_123",
    memory_type="event"
)

# 更新元数据 (合并)
updated = await service.update(
    "mem_123",
    metadata={"verified": True}
)

# 同时更新多个字段
updated = await service.update(
    "mem_123",
    content="完全更新",
    memory_type="fact",
    metadata={"version": 2}
)
```

---

#### delete() - 删除记忆

```python
async def delete(self, memory_id: str) -> bool
```

**参数**:
- `memory_id`: 记忆 ID

**返回**: `bool` 是否删除成功

**示例**:

```python
# 删除记忆
success = await service.delete("mem_123")

if success:
    print("删除成功")
else:
    print("删除失败 (可能不存在)")

# 批量删除
memory_ids = ["mem_1", "mem_2", "mem_3"]
results = await asyncio.gather(*[
    service.delete(mid) for mid in memory_ids
])
print(f"删除成功：{sum(results)}/{len(memory_ids)}")
```

---

#### batch_add() - 批量添加

```python
async def batch_add(
    self,
    memories: List[dict]
) -> List[Memory]
```

**参数**:
- `memories`: 记忆字典列表，每个字典包含 `content`, `memory_type`, `metadata`

**返回**: `List[Memory]` 添加成功的记忆列表

**示例**:

```python
# 批量添加
memories = [
    {"content": "记忆 1", "memory_type": "fact"},
    {"content": "记忆 2", "memory_type": "event"},
    {"content": "记忆 3", "memory_type": "preference", "metadata": {"priority": "high"}},
]

results = await service.batch_add(memories)
print(f"成功添加 {len(results)} 条记忆")
```

---

## 📊 数据模型

### Memory

**记忆数据模型**

```python
class Memory(BaseModel):
    id: str                    # 唯一标识符
    content: str               # 记忆内容
    memory_type: MemoryType    # 记忆类型
    source: MemorySource       # 记忆来源
    metadata: dict             # 元数据
    created_at: datetime       # 创建时间
    updated_at: datetime       # 更新时间
```

**属性说明**:

| 属性 | 类型 | 说明 |
|------|------|------|
| `id` | str | 唯一标识符，格式：`mem_xxx` |
| `content` | str | 记忆内容 |
| `memory_type` | MemoryType | 记忆类型枚举 |
| `source` | MemorySource | 记忆来源枚举 |
| `metadata` | dict | 元数据字典 |
| `created_at` | datetime | 创建时间 (UTC) |
| `updated_at` | datetime | 最后更新时间 (UTC) |

**示例**:

```python
from cozy_memory import Memory

memory = Memory(
    id="mem_123",
    content="用户喜欢咖啡",
    memory_type=MemoryType.PREFERENCE,
    source=MemorySource.MANUAL,
    metadata={"category": "food"},
    created_at=datetime.now(),
    updated_at=datetime.now()
)

# 访问属性
print(memory.content)
print(memory.memory_type.value)
```

---

### MemoryType

**记忆类型枚举**

```python
class MemoryType(str, Enum):
    FACT = "fact"              # 事实信息
    EVENT = "event"            # 事件记录
    PREFERENCE = "preference"  # 用户偏好
    SKILL = "skill"            # 技能知识
    CONVERSATION = "conversation"  # 对话历史
```

**使用示例**:

```python
from cozy_memory import MemoryType

# 使用枚举
memory_type = MemoryType.FACT

# 转换为字符串
type_str = memory_type.value  # "fact"

# 从字符串创建
memory_type = MemoryType("fact")

# 在 API 中使用
await service.add("内容", memory_type=MemoryType.PREFERENCE)
# 或
await service.add("内容", memory_type="preference")
```

---

### MemorySource

**记忆来源枚举**

```python
class MemorySource(str, Enum):
    MEMOBASE = "memobase"      # Memobase 引擎
    LOCAL = "local"            # 本地存储
    MANUAL = "manual"          # 手动输入
    VECTOR = "vector"          # 向量数据库 (计划中)
```

---

### Config

**配置类**

```python
class Config(BaseModel):
    memobase_api_key: Optional[str] = None
    memobase_project_id: Optional[str] = None
    memobase_api_base: str = "https://api.memobase.io"
    log_level: str = "INFO"
    log_format: str = "json"  # "json" or "text"
```

**使用示例**:

```python
from cozy_memory import Config, MemoryService

# 创建配置
config = Config(
    memobase_api_key="your-key",
    memobase_project_id="your-project",
    log_level="DEBUG"
)

# 从配置创建服务
service = MemoryService.from_config(config)

# 从环境变量加载
config = Config.from_env()
```

---

## 🔧 适配器 API

### BaseAdapter

**适配器抽象基类**

```python
class BaseAdapter(ABC):
    @abstractmethod
    async def add(self, memory: Memory) -> Memory:
        pass
    
    @abstractmethod
    async def get(self, memory_id: str) -> Optional[Memory]:
        pass
    
    @abstractmethod
    async def search(self, query: str, **filters) -> List[Memory]:
        pass
    
    @abstractmethod
    async def update(self, memory_id: str, updates: dict) -> Optional[Memory]:
        pass
    
    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        pass
```

---

### MemobaseMockAdapter

**Mock 适配器 (默认)**

```python
class MemobaseMockAdapter(BaseAdapter):
    def __init__(self):
        pass
    
    @classmethod
    def clear_all(cls):
        """清空所有 Mock 数据"""
        pass
```

**使用示例**:

```python
from cozy_memory import MemobaseMockAdapter

adapter = MemobaseMockAdapter()
service = MemoryService(adapter=adapter)

# 清空数据
MemobaseMockAdapter.clear_all()
```

---

### MemobaseAdapter

**Memobase 适配器**

```python
class MemobaseAdapter(BaseAdapter):
    def __init__(
        self,
        api_key: str,
        project_id: str,
        api_base: str = "https://api.memobase.io",
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        pass
    
    @classmethod
    def from_env(cls) -> "MemobaseAdapter":
        """从环境变量创建"""
        pass
```

**使用示例**:

```python
from cozy_memory import MemobaseAdapter

# 显式配置
adapter = MemobaseAdapter(
    api_key="your-key",
    project_id="your-project"
)

# 从环境变量
adapter = MemobaseAdapter.from_env()
```

---

## 🛠️ 工具函数

### 日志配置

```python
from cozy_memory.utils import setup_logger

# 设置日志
setup_logger(level="DEBUG", format="text")
```

### 内容脱敏

```python
from cozy_memory.utils import sanitize_content

# 脱敏
safe_content = sanitize_content(
    "用户电话：123-4567-8901",
    patterns=["phone", "email"]
)
```

---

## 🦀 维护者注释

**API 设计原则**:

1. **简单**: 常用功能简单易用
2. **一致**: 命名和行为规范统一
3. **类型安全**: 完整类型注解
4. **文档完整**: 每个函数都有 docstring
5. **向后兼容**: 避免破坏性变更

**版本管理**:

- 主版本：破坏性变更
- 次版本：新功能，向后兼容
- 修订版：Bug 修复

**废弃策略**:

```python
import warnings

def old_method():
    warnings.warn(
        "old_method is deprecated, use new_method instead",
        DeprecationWarning,
        stacklevel=2
    )
    return new_method()
```

---

## 📚 相关文档

- [快速开始](../guides/getting-started.md)
- [配置指南](../guides/configuration.md)
- [适配器指南](../guides/adapters.md)

---

**最后更新**: 2026-04-09  
**维护者**: 蟹小五 🦀

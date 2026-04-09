# 快速开始

**版本**: v0.2  
**时间**: 5 分钟

---

## 📦 安装

### 方式 1: 从 PyPI 安装 (推荐)

```bash
pip install cozy-memory
```

### 方式 2: 从源码安装

```bash
git clone https://github.com/zinohome/CozyMemory.git
cd CozyMemory
pip install -e .
```

### 方式 3: 开发模式

```bash
git clone https://github.com/zinohome/CozyMemory.git
cd CozyMemory
pip install -e ".[dev]"
```

---

## 🚀 5 分钟上手

### Step 1: 导入库

```python
from cozy_memory import MemoryService
```

### Step 2: 创建服务

```python
# 使用 Mock 适配器 (无需配置)
service = MemoryService()

# 或使用 Memobase 适配器
# service = MemoryService(
#     adapter=MemobaseAdapter(
#         api_key="your-api-key",
#         project_id="your-project-id"
#     )
# )
```

### Step 3: 添加记忆

```python
# 添加事实
memory = await service.add(
    "用户喜欢咖啡，不喜欢茶",
    memory_type="fact"
)
print(f"添加成功：{memory.id}")

# 添加事件
await service.add(
    "2026-04-09 与张老师讨论架构",
    memory_type="event",
    metadata={"date": "2026-04-09", "participants": ["张老师", "蟹小五"]}
)

# 添加偏好
await service.add(
    "偏好使用 FastAPI 而非 Flask",
    memory_type="preference"
)
```

### Step 4: 查询记忆

```python
# 获取单个记忆
memory = await service.get(memory_id)
print(memory.content)

# 搜索记忆
results = await service.search("咖啡")
for memory in results:
    print(f"- {memory.content}")

# 按类型过滤
facts = await service.search("", memory_type="fact")
```

### Step 5: 更新和删除

```python
# 更新记忆
await service.update(
    memory_id,
    content="用户非常喜欢咖啡，完全不喜欢茶"
)

# 删除记忆
await service.delete(memory_id)
```

---

## 📚 完整示例

### 示例 1: 对话记忆管理

```python
from cozy_memory import MemoryService

async def manage_conversation():
    service = MemoryService()
    
    # 记录对话
    await service.add(
        "用户询问如何安装 CozyMemory",
        memory_type="conversation",
        metadata={"timestamp": "2026-04-09T10:00:00Z"}
    )
    
    # 记录用户偏好
    await service.add(
        "用户偏好简洁的文档",
        memory_type="preference"
    )
    
    # 后续对话中检索
    preferences = await service.search(
        "偏好",
        memory_type="preference"
    )
    
    return preferences
```

### 示例 2: 批量操作

```python
from cozy_memory import MemoryService

async def batch_import():
    service = MemoryService()
    
    memories = [
        ("Python 是最好的语言", "fact"),
        ("2026-04-09 项目启动", "event"),
        ("喜欢异步编程", "preference"),
    ]
    
    # 批量添加
    results = await asyncio.gather(*[
        service.add(content, memory_type=mem_type)
        for content, mem_type in memories
    ])
    
    print(f"成功导入 {len(results)} 条记忆")
```

### 示例 3: 自定义适配器

```python
from cozy_memory import MemoryService, BaseAdapter

class MyCustomAdapter(BaseAdapter):
    """自定义适配器"""
    
    async def add(self, memory):
        # 你的实现
        return memory
    
    # 实现其他方法...

# 使用自定义适配器
service = MemoryService(adapter=MyCustomAdapter())
```

---

## 🔧 配置选项

### 环境变量

```bash
# Memobase 配置 (可选)
export COZY_MEMOBASE_API_KEY="your-api-key"
export COZY_MEMOBASE_PROJECT_ID="your-project-id"

# 日志级别
export COZY_LOG_LEVEL="INFO"  # DEBUG, INFO, WARNING, ERROR
```

### 代码配置

```python
from cozy_memory import MemoryService, MemobaseAdapter, Config

# 方式 1: 直接传递参数
service = MemoryService(
    adapter=MemobaseAdapter(
        api_key="xxx",
        project_id="yyy"
    )
)

# 方式 2: 使用 Config 对象
config = Config(
    memobase_api_key="xxx",
    memobase_project_id="yyy",
    log_level="INFO"
)
service = MemoryService.from_config(config)
```

---

## 🧪 测试

### 单元测试

```python
import pytest
from cozy_memory import MemoryService, MemobaseMockAdapter

@pytest.mark.asyncio
async def test_add_memory():
    service = MemoryService(adapter=MemobaseMockAdapter())
    
    memory = await service.add("测试记忆")
    
    assert memory.content == "测试记忆"
    assert memory.id is not None
```

### 集成测试

```python
@pytest.mark.asyncio
async def test_memobase_integration():
    # 需要真实 API Key
    service = MemoryService(
        adapter=MemobaseAdapter(
            api_key=os.getenv("MEMOBASE_API_KEY"),
            project_id=os.getenv("MEMOBASE_PROJECT_ID")
        )
    )
    
    memory = await service.add("集成测试")
    assert memory.id is not None
```

---

## ❓ 常见问题

### Q: 需要 API Key 吗？

**A**: 不需要。默认使用 Mock 适配器，无需任何配置。

### Q: Mock 和真实环境有什么区别？

**A**: Mock 适配器在内存中存储，重启后数据丢失。真实环境持久化存储。

### Q: 如何切换到真实环境？

**A**: 使用 `MemobaseAdapter` 并传入 API Key：

```python
service = MemoryService(
    adapter=MemobaseAdapter(api_key="xxx", project_id="yyy")
)
```

### Q: 支持并发吗？

**A**: 支持。所有 API 都是异步的，支持高并发。

### Q: 如何备份数据？

**A**: 使用 Memobase 时，数据自动备份。本地存储时，定期导出 JSON。

---

## 📖 下一步

- [配置指南](./configuration.md) - 详细配置选项
- [适配器指南](./adapters.md) - 使用不同适配器
- [API 参考](../api/reference.md) - 完整 API 文档
- [开发指南](../dev/local-dev.md) - 本地开发设置

---

**最后更新**: 2026-04-09  
**维护者**: 蟹小五 🦀

# 测试最佳实践

**版本**: v0.2  
**日期**: 2026-04-09  
**状态**: 已实现

---

## 🎯 测试策略

### 测试金字塔

```
        /\
       /  \
      / E2E \       # 端到端测试 (少量)
     /------\
    /        \
   / Integration \  # 集成测试 (适量)
  /--------------\
 /                \
/    Unit Tests    \ # 单元测试 (大量)
--------------------
```

**CozyMemory 测试分布**:
- 单元测试：70% (核心逻辑)
- 集成测试：20% (适配器)
- E2E 测试：10% (完整流程)

---

## 🧪 测试类型

### 1. 单元测试

**目标**: 测试单个函数/方法

**特点**:
- ✅ 快速 (<10ms)
- ✅ 隔离外部依赖
- ✅ 使用 Mock
- ✅ 覆盖率要求 >95%

**示例**:

```python
# tests/test_service.py
import pytest
from cozy_memory import MemoryService, MemobaseMockAdapter
from cozy_memory.models import Memory, MemoryType

@pytest.mark.asyncio
async def test_add_memory():
    """测试添加记忆"""
    # Arrange
    service = MemoryService(adapter=MemobaseMockAdapter())
    
    # Act
    memory = await service.add(
        "用户喜欢咖啡",
        memory_type="preference"
    )
    
    # Assert
    assert memory.content == "用户喜欢咖啡"
    assert memory.memory_type == MemoryType.PREFERENCE
    assert memory.id is not None
    assert memory.created_at is not None

@pytest.mark.asyncio
async def test_search_memory():
    """测试搜索记忆"""
    # Arrange
    service = MemoryService(adapter=MemobaseMockAdapter())
    await service.add("咖啡相关记忆")
    await service.add("茶相关记忆")
    
    # Act
    results = await service.search("咖啡")
    
    # Assert
    assert len(results) == 1
    assert "咖啡" in results[0].content

@pytest.mark.asyncio
async def test_update_memory():
    """测试更新记忆"""
    # Arrange
    service = MemoryService(adapter=MemobaseMockAdapter())
    memory = await service.add("原始内容")
    
    # Act
    updated = await service.update(
        memory.id,
        content="更新后的内容"
    )
    
    # Assert
    assert updated.content == "更新后的内容"
    assert updated.updated_at > updated.created_at

@pytest.mark.asyncio
async def test_delete_memory():
    """测试删除记忆"""
    # Arrange
    service = MemoryService(adapter=MemobaseMockAdapter())
    memory = await service.add("待删除")
    
    # Act
    success = await service.delete(memory.id)
    
    # Assert
    assert success is True
    
    # 验证已删除
    deleted = await service.get(memory.id)
    assert deleted is None
```

---

### 2. 集成测试

**目标**: 测试组件间交互

**特点**:
- ✅ 测试真实适配器
- ✅ 验证外部服务
- ⚠️ 需要配置
- ⚠️ 较慢 (~100ms)

**示例**:

```python
# tests/test_memobase_adapter.py
import pytest
import os
from cozy_memory import MemoryService, MemobaseAdapter

@pytest.mark.asyncio
@pytest.mark.integration  # 标记为集成测试
async def test_memobase_add():
    """测试 Memobase 适配器添加"""
    # 需要真实 API Key
    if not os.getenv("MEMOBASE_API_KEY"):
        pytest.skip("需要 MEMOBASE_API_KEY")
    
    # Arrange
    adapter = MemobaseAdapter.from_env()
    service = MemoryService(adapter=adapter)
    
    # Act
    memory = await service.add("集成测试记忆")
    
    # Assert
    assert memory.id is not None
    
    # Cleanup
    await service.delete(memory.id)

@pytest.mark.asyncio
@pytest.mark.integration
async def test_memobase_search():
    """测试 Memobase 适配器搜索"""
    if not os.getenv("MEMOBASE_API_KEY"):
        pytest.skip("需要 MEMOBASE_API_KEY")
    
    # Arrange
    service = MemoryService(adapter=MemobaseAdapter.from_env())
    test_content = f"搜索测试_{uuid.uuid4()}"
    await service.add(test_content)
    
    # Act
    results = await service.search("搜索测试")
    
    # Assert
    assert len(results) > 0
    assert any(test_content in m.content for m in results)
    
    # Cleanup
    for m in results:
        if test_content in m.content:
            await service.delete(m.id)
```

---

### 3. 端到端测试

**目标**: 测试完整用户流程

**特点**:
- ✅ 模拟真实使用
- ✅ 验证整体功能
- ⚠️ 最慢 (~1s)
- ⚠️ 需要完整环境

**示例**:

```python
# tests/test_e2e.py
import pytest
from cozy_memory import MemoryService, MemobaseMockAdapter

@pytest.mark.asyncio
async def test_full_workflow():
    """测试完整工作流程"""
    # Arrange
    service = MemoryService(adapter=MemobaseMockAdapter())
    
    # Act: 添加多条记忆
    memories = [
        ("用户喜欢咖啡", "preference"),
        ("2026-04-09 会议", "event"),
        ("Python 是最好的语言", "fact"),
    ]
    
    added = []
    for content, mem_type in memories:
        memory = await service.add(content, memory_type=mem_type)
        added.append(memory)
    
    # Assert: 验证添加成功
    assert len(added) == 3
    
    # Act: 搜索
    results = await service.search("咖啡")
    
    # Assert: 验证搜索结果
    assert len(results) == 1
    assert "咖啡" in results[0].content
    
    # Act: 更新
    updated = await service.update(
        added[0].id,
        content="用户非常喜欢咖啡"
    )
    
    # Assert: 验证更新
    assert updated.content == "用户非常喜欢咖啡"
    
    # Act: 删除
    await service.delete(added[0].id)
    
    # Assert: 验证删除
    deleted = await service.get(added[0].id)
    assert deleted is None
    
    # 验证其他记忆还在
    all_memories = await service.search("")
    assert len(all_memories) == 2
```

---

## 🛠️ 测试工具

### pytest 配置

```python
# tests/conftest.py
import pytest
import asyncio
from cozy_memory import MemoryService, MemobaseMockAdapter

@pytest.fixture
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def service():
    """提供 MemoryService 实例"""
    service = MemoryService(adapter=MemobaseMockAdapter())
    yield service
    # Cleanup
    MemobaseMockAdapter.clear_all()

@pytest.fixture
async def service_with_data(service):
    """提供预填充数据的 Service"""
    await service.add("测试记忆 1")
    await service.add("测试记忆 2")
    await service.add("咖啡相关")
    yield service
```

### pytest.ini

```ini
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
asyncio_mode = auto
markers =
    unit: 单元测试
    integration: 集成测试
    e2e: 端到端测试
    slow: 慢速测试
addopts = 
    -v
    --tb=short
    --strict-markers
    -m "not slow"
```

---

## 📊 测试覆盖率

### 运行覆盖率测试

```bash
# 运行所有测试并生成覆盖率报告
pytest tests/ -v --cov=src --cov-report=html

# 查看 HTML 报告
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux

# 生成文本报告
pytest tests/ -v --cov=src --cov-report=term-missing

# 生成 XML 报告 (用于 CI/CD)
pytest tests/ -v --cov=src --cov-report=xml
```

### 覆盖率要求

```python
# pyproject.toml
[tool.coverage.run]
source = ["src"]
omit = [
    "*/tests/*",
    "*/__init__.py",
]

[tool.coverage.report]
fail_under = 95  # 最低覆盖率要求
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
```

### 覆盖率检查清单

- [ ] 所有公共方法都有测试
- [ ] 边界条件已测试
- [ ] 错误处理已测试
- [ ] 异常路径已测试
- [ ] 覆盖率 >95%

---

## 🏷️ 测试标记

### 使用标记分类

```python
import pytest

@pytest.mark.unit
async def test_unit_example():
    """单元测试"""
    pass

@pytest.mark.integration
async def test_integration_example():
    """集成测试"""
    pass

@pytest.mark.e2e
async def test_e2e_example():
    """端到端测试"""
    pass

@pytest.mark.slow
async def test_slow_example():
    """慢速测试"""
    pass
```

### 运行特定标记的测试

```bash
# 只运行单元测试
pytest -v -m unit

# 只运行集成测试
pytest -v -m integration

# 跳过慢速测试
pytest -v -m "not slow"

# 运行所有测试 (包括慢速)
pytest -v -m "not None"
```

---

## 🔍 测试技巧

### 1. Mock 外部依赖

```python
from unittest.mock import AsyncMock, patch
import pytest
from cozy_memory import MemoryService, MemobaseAdapter

@pytest.mark.asyncio
async def test_with_mock():
    """使用 Mock 测试"""
    # 创建 Mock 适配器
    mock_adapter = AsyncMock()
    mock_adapter.add.return_value = Memory(
        id="test_id",
        content="测试"
    )
    
    service = MemoryService(adapter=mock_adapter)
    
    # 测试
    result = await service.add("测试")
    
    # 验证
    assert result.id == "test_id"
    mock_adapter.add.assert_called_once()
```

### 2. 参数化测试

```python
import pytest

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content,memory_type,expected_type",
    [
        ("用户喜欢咖啡", "preference", MemoryType.PREFERENCE),
        ("今天开会", "event", MemoryType.EVENT),
        ("Python 很好", "fact", MemoryType.FACT),
    ]
)
async def test_add_different_types(
    service, content, memory_type, expected_type
):
    """参数化测试不同类型"""
    memory = await service.add(content, memory_type=memory_type)
    assert memory.memory_type == expected_type
```

### 3. 异步测试

```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_async_operation():
    """测试异步操作"""
    service = MemoryService()
    
    # 并发添加多条记忆
    tasks = [
        service.add(f"记忆{i}")
        for i in range(10)
    ]
    
    results = await asyncio.gather(*tasks)
    
    assert len(results) == 10
    assert all(r.id is not None for r in results)
```

### 4. 异常测试

```python
import pytest

@pytest.mark.asyncio
async def test_invalid_memory_type(service):
    """测试无效类型"""
    with pytest.raises(ValueError) as exc_info:
        await service.add("测试", memory_type="invalid")
    
    assert "invalid" in str(exc_info.value)

@pytest.mark.asyncio
async def test_not_found(service):
    """测试找不到记忆"""
    result = await service.get("nonexistent_id")
    assert result is None
```

### 5. 性能测试

```python
import pytest
import time

@pytest.mark.asyncio
async def test_add_performance(service):
    """测试添加性能"""
    start = time.time()
    
    for i in range(100):
        await service.add(f"记忆{i}")
    
    duration = time.time() - start
    
    # 100 次添加应在 1 秒内完成
    assert duration < 1.0
    print(f"100 次添加耗时：{duration:.3f}秒")
```

---

## 🚀 CI/CD 集成

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt
      
      - name: Run tests
        run: |
          pytest tests/ -v --cov=src --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

### 预提交检查

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest tests/ -v --tb=short
        language: system
        pass_filenames: false
        always_run: true
```

---

## 📝 测试检查清单

### 编写测试前

- [ ] 明确测试目标
- [ ] 确定测试类型 (单元/集成/E2E)
- [ ] 准备测试数据
- [ ] 设置测试环境

### 编写测试时

- [ ] 遵循 AAA 模式 (Arrange-Act-Assert)
- [ ] 测试一个行为
- [ ] 使用描述性名称
- [ ] 添加注释说明意图
- [ ] 测试正常路径和异常路径

### 编写测试后

- [ ] 测试通过
- [ ] 覆盖率达标
- [ ] 代码审查
- [ ] 文档更新

### 维护测试

- [ ] 定期清理过时测试
- [ ] 更新失败的测试
- [ ] 优化慢速测试
- [ ] 补充边界测试

---

## 🦀 维护者注释

**测试原则**:

1. **测试驱动**: 先写测试，再写实现
2. **隔离**: 测试之间互不影响
3. **可重复**: 每次运行结果一致
4. **快速**: 单元测试 <10ms，集成测试 <1s
5. **完整**: 覆盖率 >95%

**测试命名规范**:

```python
# 好名称
test_add_memory_success()
test_search_with_empty_query()
test_update_nonexistent_memory()

# 坏名称
test1()
test_add()
test()
```

**测试组织**:

```
tests/
├── conftest.py          # 共享 fixture
├── test_service.py      # Service 测试
├── test_adapters.py     # 适配器测试
├── test_models.py       # 模型测试
├── test_config.py       # 配置测试
└── integration/         # 集成测试
    ├── test_memobase.py
    └── test_sqlite.py
```

---

## 📚 相关文档

- [本地开发](./local-dev.md)
- [API 参考](../api/reference.md)
- [贡献指南](../CONTRIBUTING.md)

---

**最后更新**: 2026-04-09  
**维护者**: 蟹小五 🦀

# 本地开发指南

**版本**: v0.2  
**日期**: 2026-04-09  
**适用环境**: 本地开发 (macOS/Windows/Linux)

---

## 🚀 快速开始

### 1.1 环境要求

- Python 3.11+
- pip 或 poetry
- Git
- (可选) Node.js - 用于某些工具

### 1.2 安装依赖

```bash
# 克隆仓库
git clone https://github.com/zinohome/CozyMemory.git
cd CozyMemory

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装开发依赖
pip install -r requirements-dev.txt
```

### 1.3 配置环境

```bash
# 复制环境配置示例
cp .env.example .env

# 编辑 .env 文件 (开发环境默认配置即可)
```

### 1.4 验证安装

```bash
# 运行测试
pytest tests/ -v

# 检查代码质量
black --check src/
isort --check-only src/
mypy src/
```

---

## 🧪 运行测试

### 单元测试

```bash
# 运行所有单元测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/test_adapters.py -v

# 运行特定测试函数
pytest tests/test_adapters.py::test_add_memory -v

# 带覆盖率报告
pytest tests/ -v --cov=src --cov-report=html

# 查看 HTML 覆盖率报告
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov\\index.html  # Windows
```

### 测试标记

```bash
# 跳过慢速测试
pytest -v -m "not slow"

# 只运行集成测试
pytest -v -m integration

# 只运行单元测试
pytest -v -m unit
```

### 测试最佳实践

```python
# tests/test_example.py
import pytest
from cozy_memory import MemoryService, MemobaseMockAdapter

@pytest.mark.asyncio
async def test_add_memory():
    """测试添加记忆"""
    service = MemoryService(adapter=MemobaseMockAdapter())
    
    memory = await service.add("测试记忆")
    
    assert memory.content == "测试记忆"
    assert memory.id is not None

@pytest.mark.asyncio
async def test_search_memory():
    """测试搜索记忆"""
    service = MemoryService(adapter=MemobaseMockAdapter())
    
    await service.add("咖啡相关记忆")
    results = await service.search("咖啡")
    
    assert len(results) > 0
```

---

## 🔍 代码质量检查

### 代码格式化

```bash
# 使用 black 格式化代码
black src/ tests/

# 检查导入排序
isort src/ tests/

# 一次性完成
black src/ tests/ && isort src/ tests/
```

### 代码检查

```bash
# flake8 代码检查
flake8 src/ tests/

# mypy 类型检查
mypy src/

# 忽略某些错误
mypy src/ --ignore-missing-imports
```

### 预提交钩子

```bash
# 安装预提交钩子
pre-commit install

# 手动运行所有检查
pre-commit run --all-files

# 查看预提交配置
cat .pre-commit-config.yaml
```

### .pre-commit-config.yaml 示例

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.1.0
    hooks:
      - id: black
        language_version: python3.11
  
  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
        name: isort (python)
  
  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies:
          - types-all
```

---

## 📁 项目结构

```
CozyMemory/
├── src/                      # 源代码
│   ├── cozy_memory/          # 主包
│   │   ├── __init__.py       # 包入口
│   │   ├── service.py        # MemoryService
│   │   ├── adapters/         # 适配器层
│   │   │   ├── __init__.py
│   │   │   ├── base.py       # BaseAdapter
│   │   │   ├── memobase.py   # MemobaseAdapter
│   │   │   └── mock.py       # MemobaseMockAdapter
│   │   ├── models/           # 数据模型
│   │   │   ├── __init__.py
│   │   │   └── memory.py     # Memory, MemoryType, MemorySource
│   │   ├── config.py         # 配置管理
│   │   └── utils/            # 工具函数
│   │       ├── logger.py     # 日志配置
│   │       └── helpers.py    # 辅助函数
│   └── tests/                # 测试代码
│       ├── __init__.py
│       ├── conftest.py       # pytest 配置
│       ├── test_service.py   # Service 测试
│       ├── test_adapters.py  # 适配器测试
│       └── test_models.py    # 模型测试
├── docs/                     # 文档
├── examples/                 # 示例代码
├── requirements.txt          # 生产依赖
├── requirements-dev.txt      # 开发依赖
├── pyproject.toml            # 项目配置
├── setup.py                  # 安装脚本
├── .env.example              # 环境配置示例
├── .pre-commit-config.yaml   # 预提交配置
└── README.md                 # 项目说明
```

---

## 🎭 Mock 服务

### Mock 适配器

本地开发使用 Mock 适配器，无需启动真实服务：

```python
from cozy_memory import MemoryService, MemobaseMockAdapter

# 默认使用 Mock
service = MemoryService()  # 等同于 MemobaseMockAdapter()

# 或显式指定
service = MemoryService(adapter=MemobaseMockAdapter())

# 所有操作都在内存中，适合快速开发和测试
```

### Mock 数据清空

```python
from cozy_memory import MemobaseMockAdapter

# 测试前清空 Mock 数据
MemobaseMockAdapter.clear_all()

# 或在测试中使用 fixture
@pytest.fixture
def clean_mock():
    MemobaseMockAdapter.clear_all()
    yield
    MemobaseMockAdapter.clear_all()
```

### Mock vs 真实环境

| 特性 | Mock 适配器 | 真实适配器 |
|------|-----------|-----------|
| 配置 | 无需 | 需要 API Key |
| 速度 | 极快 (<1ms) | 受网络影响 (~100ms) |
| 持久化 | 否 (内存) | 是 |
| 用途 | 开发/测试 | 生产环境 |

---

## 🐛 调试技巧

### 启用调试模式

```bash
# 在 .env 中设置
DEBUG=True
LOG_LEVEL=DEBUG
LOG_FORMAT=text  # 文本格式更易读
```

### 查看日志

```python
# 代码中配置日志
import logging
import structlog

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s: %(message)s"
)

# 或使用 structlog
structlog.configure(
    processors=[
        structlog.dev.ConsoleRenderer()
    ]
)
```

日志输出示例：

```
DEBUG: Memory added: mem_123
INFO: Search completed: 5 results in 12ms
WARNING: Rate limit approaching: 80%
ERROR: Failed to connect to Memobase
```

### 使用断点

```python
# Python 3.7+
breakpoint()

# 或使用 pdb
import pdb; pdb.set_trace()

# 或使用 ipdb (更强大)
import ipdb; ipdb.set_trace()
```

### 使用 pytest 调试

```python
def test_with_debug():
    result = some_function()
    breakpoint()  # 在测试中暂停
    assert result == expected
```

运行：

```bash
pytest tests/test_example.py -s  # -s 禁用捕获，允许交互
```

---

## 📦 依赖管理

### 查看依赖

```bash
# 列出已安装依赖
pip list

# 查看依赖树
pip install pipdeptree
pipdeptree

# 检查过期依赖
pip install pip-review
pip-review --local
```

### 更新依赖

```bash
# 更新所有依赖
pip-review --auto

# 更新特定依赖
pip install --upgrade pytest

# 更新开发依赖
pip install -r requirements-dev.txt --upgrade
```

### 依赖锁定

```bash
# 生成锁定文件
pip install pip-tools
pip-compile requirements.in
pip-compile requirements-dev.in

# 安装锁定版本
pip-sync requirements.txt requirements-dev.txt
```

---

## 🚀 开发工作流

### 1. 创建功能分支

```bash
git checkout -b feature/your-feature-name
```

### 2. 开发和测试

```bash
# 编写代码
# 编写测试
pytest tests/ -v

# 代码格式化
black src/ tests/
isort src/ tests/

# 类型检查
mypy src/

# 代码检查
flake8 src/ tests/
```

### 3. 提交代码

```bash
git add .
git commit -m "feat: add new feature

- Description of the feature
- Related issues: #123"
```

### 4. 推送和 PR

```bash
git push origin feature/your-feature-name
# 然后在 GitHub 上创建 Pull Request
```

---

## ❓ 常见问题

### Q1: 导入错误 `ModuleNotFoundError: No module named 'cozy_memory'`

**解决**: 确保在正确的目录运行，或安装为可编辑模式：

```bash
pip install -e .
```

### Q2: 测试失败 `pytest-asyncio` 警告

**解决**: 确保 `conftest.py` 中配置了 asyncio 模式：

```python
# tests/conftest.py
import pytest

pytest_plugins = ("pytest_asyncio",)

@pytest.fixture
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

### Q3: 端口被占用

**解决**: CozyMemory v0.2 是库，不需要端口。如果是其他服务占用：

```bash
# 查找占用端口的进程
lsof -i :8000

# 杀死进程
kill -9 <PID>
```

### Q4: Mock 数据不持久化

**解决**: 这是预期行为。Mock 适配器使用内存存储，重启后数据丢失。

需要持久化时：
- 使用真实 Memobase 适配器
- 或等待 SQLite 适配器 (计划中)

### Q5: 类型检查失败

**解决**: 确保安装了类型存根：

```bash
pip install types-all
# 或
pip install types-requests types-aiofiles ...
```

---

## 📋 开发检查清单

### 新功能开发

- [ ] 编写代码
- [ ] 编写单元测试
- [ ] 运行测试 `pytest -v`
- [ ] 代码格式化 `black && isort`
- [ ] 类型检查 `mypy`
- [ ] 代码检查 `flake8`
- [ ] 更新文档
- [ ] 提交代码

### Bug 修复

- [ ] 复现 Bug
- [ ] 编写测试 (暴露 Bug)
- [ ] 修复代码
- [ ] 验证测试通过
- [ ] 运行所有测试
- [ ] 代码格式化
- [ ] 提交代码

### 发布准备

- [ ] 更新版本号
- [ ] 更新 CHANGELOG
- [ ] 运行所有测试
- [ ] 检查覆盖率 (>95%)
- [ ] 更新文档
- [ ] 创建 Git Tag
- [ ] 发布到 PyPI

---

## 🎯 下一步

完成本地开发后：

1. ✅ 确保所有测试通过
2. ✅ 代码格式化检查通过
3. ✅ 覆盖率 >95%
4. ✅ 提交代码到 Git
5. ⏳ 创建 Pull Request
6. ⏳ Code Review
7. ⏳ 合并到主分支
8. ⏳ 发布新版本

---

## 📚 相关文档

- [快速开始](./getting-started.md)
- [配置指南](./configuration.md)
- [测试指南](./testing.md)
- [API 参考](../api/reference.md)

---

**Happy Coding!** 🦀💻

**最后更新**: 2026-04-09  
**维护者**: 蟹小五 🦀

# CozyMemory 本地开发指南

**文档编号**: DEV-LOCAL-001  
**版本**: 1.0  
**创建日期**: 2026-04-06  
**适用环境**: 本地开发 (macOS/Windows/Linux)

---

## 1. 快速开始

### 1.1 环境要求

- Python 3.11+
- pip 或 poetry
- Git

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

### 1.4 运行应用

```bash
# 方式 1: 使用 uvicorn 直接运行
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# 方式 2: 使用 Python 运行
python -m src.api.main
```

访问：
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 2. 运行测试

### 2.1 单元测试

```bash
# 运行所有单元测试
pytest src/tests/unit/ -v

# 运行特定测试文件
pytest src/tests/unit/test_adapters.py -v

# 运行特定测试函数
pytest src/tests/unit/test_adapters.py::test_health_check -v

# 带覆盖率报告
pytest src/tests/unit/ -v --cov=src --cov-report=html

# 查看 HTML 覆盖率报告
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov\\index.html  # Windows
```

### 2.2 API 测试

```bash
# 运行 API 测试
pytest src/tests/unit/test_api.py -v
```

### 2.3 测试标记

```bash
# 跳过慢速测试
pytest -v -m "not slow"

# 只运行集成测试
pytest -v -m integration
```

---

## 3. 代码质量检查

### 3.1 代码格式化

```bash
# 使用 black 格式化代码
black src/ tests/

# 检查导入排序
isort src/ tests/

# 一次性完成
black src/ tests/ && isort src/ tests/
```

### 3.2 代码检查

```bash
# flake8 代码检查
flake8 src/ tests/

# mypy 类型检查
mypy src/
```

### 3.3 预提交钩子

```bash
# 安装预提交钩子
pre-commit install

# 手动运行所有检查
pre-commit run --all-files
```

---

## 4. 项目结构

```
CozyMemory/
├── src/                      # 源代码
│   ├── api/                  # API 层
│   │   ├── v1/               # API v1 版本
│   │   │   ├── routes.py     # 路由定义
│   │   │   └── schemas.py    # Pydantic 模型
│   │   └── main.py           # FastAPI 应用入口
│   ├── adapters/             # 适配器层
│   │   ├── base.py           # 适配器基类
│   │   ├── memobase_adapter.py
│   │   └── memobase_mock_adapter.py
│   ├── services/             # 服务层
│   │   └── memory_service.py
│   ├── models/               # 数据模型
│   │   └── memory.py
│   ├── cache/                # 缓存层
│   ├── utils/                # 工具函数
│   │   ├── config.py         # 配置管理
│   │   └── logger.py         # 日志配置
│   └── tests/                # 测试代码
│       ├── unit/             # 单元测试
│       └── integration/      # 集成测试
├── deploy/                   # 部署配置
├── docs/                     # 文档
├── requirements.txt          # 生产依赖
├── requirements-dev.txt      # 开发依赖
├── pyproject.toml            # 项目配置
└── .env.example              # 环境配置示例
```

---

## 5. Mock 服务

本地开发使用 Mock 适配器，无需启动真实的 Memobase 服务。

### 5.1 Mock 适配器

```python
from src.adapters.memobase_mock_adapter import MemobaseMockAdapter

adapter = MemobaseMockAdapter(
    api_url="http://localhost:8001",  # 不会真正调用
    api_key="test_key",
    timeout=5.0,
)

# 所有操作都在内存中，适合快速开发和测试
```

### 5.2 Mock 数据清空

```python
# 测试前清空 Mock 数据
MemobaseMockAdapter.clear_all()
```

---

## 6. 调试技巧

### 6.1 启用调试模式

在 `.env` 中设置：

```env
DEBUG=True
LOG_LEVEL=DEBUG
LOG_FORMAT=text  # 文本格式更易读
```

### 6.2 查看日志

日志会输出到控制台，格式如下：

```
2026-04-06T10:00:00.000Z [info     ] CozyMemory 启动              version=0.1.0 environment=development
2026-04-06T10:00:00.100Z [info     ] 请求完成                    method=GET path=/api/v1/health status_code=200 duration_ms=15.5
```

### 6.3 使用断点

```python
# 在代码中插入断点
import pdb; pdb.set_trace()

# Python 3.7+
breakpoint()
```

---

## 7. 常见问题

### Q1: 导入错误 `ModuleNotFoundError: No module named 'src'`

**解决**: 确保在正确的目录运行，或将 src 添加到 PYTHONPATH：

```bash
export PYTHONPATH=$(pwd)/src:$PYTHONPATH  # macOS/Linux
set PYTHONPATH=%cd%\src;%PYTHONPATH%  # Windows
```

### Q2: 测试失败 `pytest-asyncio` 警告

**解决**: 确保 `conftest.py` 中配置了 asyncio 模式：

```python
pytest_plugins = ("pytest_asyncio",)
```

### Q3: 端口被占用

**解决**: 修改 `.env` 中的端口：

```env
PORT=8001
```

---

## 8. 下一步

完成本地开发后：

1. ✅ 确保所有测试通过
2. ✅ 代码格式化检查通过
3. ✅ 提交代码到 Git
4. ⏳ 等待服务器环境就绪
5. ⏳ 部署到 Docker 环境
6. ⏳ 运行集成测试

---

## 9. 开发检查清单

开发新功能时：

- [ ] 编写代码
- [ ] 编写单元测试
- [ ] 运行测试 `pytest -v`
- [ ] 代码格式化 `black && isort`
- [ ] 类型检查 `mypy`
- [ ] 代码检查 `flake8`
- [ ] 更新文档
- [ ] 提交代码

---

**Happy Coding!** 🦀💻

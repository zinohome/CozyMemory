# CozyMemory 快速开始

**统一 AI 记忆服务平台** - 整合 Mem0、Memobase、Cognee 三大记忆引擎

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## 🚀 5 分钟快速开始

### 1. 安装依赖

```bash
# 克隆仓库
git clone https://github.com/zinohome/CozyMemory.git
cd CozyMemory

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements-dev.txt
```

### 2. 配置环境

```bash
# 复制环境配置
cp .env.example .env
```

### 3. 运行应用

```bash
# 启动服务
uvicorn src.api.main:app --reload

# 访问 Swagger UI
# http://localhost:8000/docs
```

### 4. 运行测试

```bash
# 运行单元测试
pytest src/tests/unit/ -v

# 查看覆盖率
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

---

## 📚 文档导航

- **[本地开发指南](docs/dev/LOCAL-DEV-GUIDE.md)** - 详细的本地开发教程
- **[API 文档](http://localhost:8000/docs)** - Swagger UI
- **[架构文档](docs/architecture/)** - 系统架构设计
- **[项目管理](docs/pm/)** - 项目计划和进度

---

## 🎯 核心功能

### 统一 API 层

```python
# 创建记忆
POST /api/v1/memories
{
  "user_id": "user_123",
  "content": "用户喜欢喝拿铁咖啡",
  "memory_type": "preference"
}

# 查询记忆
GET /api/v1/memories?user_id=user_123&q=咖啡

# 健康检查
GET /api/v1/health
```

### 智能路由

自动选择最佳记忆引擎：
- **Memobase**: 用户画像记忆
- **Mem0**: 对话记忆
- **Cognee**: 知识图谱

### 结果融合

使用 RRF (Reciprocal Rank Fusion) 算法融合多引擎结果。

---

## 🏗️ 项目结构

```
CozyMemory/
├── src/                      # 源代码
│   ├── api/                  # API 层
│   ├── adapters/             # 记忆引擎适配器
│   ├── services/             # 业务逻辑层
│   ├── models/               # 数据模型
│   ├── cache/                # 缓存层
│   └── utils/                # 工具函数
├── tests/                    # 测试代码
├── docs/                     # 文档
├── deploy/                   # 部署配置
└── requirements*.txt         # 依赖配置
```

---

## 🧪 测试

```bash
# 单元测试
pytest src/tests/unit/ -v

# API 测试
pytest src/tests/unit/test_api.py -v

# 带覆盖率
pytest --cov=src --cov-report=term-missing
```

---

## 📦 部署

### Docker 部署 (待服务器就绪)

```bash
# 构建镜像
docker build -t cozymemory .

# 启动服务
docker-compose -f deploy/docker/docker-compose.yml up -d
```

### 生产环境

详见：[CI/CD 指南](docs/ops/01-cicd-guide.md)

---

## 🔧 开发工具

```bash
# 代码格式化
black src/ tests/
isort src/ tests/

# 代码检查
flake8 src/ tests/
mypy src/

# 预提交钩子
pre-commit install
```

---

## 📊 性能指标

| 指标 | 目标 | 当前 (Mock) |
|------|------|------------|
| 延迟 | <200ms | ~50ms |
| 吞吐量 | 1000 req/s | - |
| 可用性 | 99.9% | - |
| 测试覆盖率 | >80% | - |

---

## 🤝 贡献

1. Fork 仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

详见：[开发规范](docs/DEV-STD-001.md)

---

## 📝 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 📞 联系

- **项目链接**: https://github.com/zinohome/CozyMemory
- **问题反馈**: https://github.com/zinohome/CozyMemory/issues

---

**Built with ❤️ by CozyMemory Team** 🦀

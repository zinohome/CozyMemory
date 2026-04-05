# CozyMemory 开发规范

**文档编号**: DEV-STD-001  
**版本**: 1.0  
**生效日期**: 2026-04-05  
**适用范围**: 所有 CozyMemory 项目开发者

---

## 1. 代码规范

### 1.1 Python 代码风格

遵循 **PEP 8** 规范，使用以下工具自动检查：

```bash
# 代码格式化
black src/ tests/

# 代码检查
flake8 src/ tests/

# 类型检查
mypy src/

# 导入排序
isort src/ tests/
```

**配置**:
- `pyproject.toml` 中统一配置
- 行宽：88 字符 (black 默认)
- 引号：双引号
- 缩进：4 空格

**示例**:
```python
# ✅ 好的代码
from typing import Optional, List
from pydantic import BaseModel, Field


class MemoryRequest(BaseModel):
    """记忆存储请求模型"""
    
    user_id: str = Field(..., description="用户 ID", min_length=1)
    content: str = Field(..., description="记忆内容")
    intent: Optional[str] = Field(None, description="意图类型")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "content": "我喜欢 Python 编程",
                "intent": "fact"
            }
        }


async def store_memory(
    user_id: str,
    content: str,
    intent: Optional[str] = None
) -> dict:
    """存储记忆到引擎"""
    if not user_id:
        raise ValueError("user_id 不能为空")
    
    return {"status": "success"}
```

### 1.2 类型注解

**必须使用类型注解**:
```python
# ✅ 好的代码
def calculate_similarity(
    query: str,
    documents: List[str],
    threshold: float = 0.8
) -> List[dict]:
    ...

# ❌ 不好的代码
def calculate_similarity(query, documents, threshold=0.8):
    ...
```

### 1.3 文档字符串

**所有公共函数/类必须有文档字符串**:
```python
class MemoryAdapter:
    """记忆引擎适配器基类
    
    提供统一的接口来访问不同的记忆引擎 (Mem0, Memobase, Cognee)。
    使用适配器模式屏蔽引擎差异。
    
    Attributes:
        engine_name: 引擎名称
        api_key: API 密钥
        timeout: 请求超时时间 (秒)
    """
    
    async def store(self, user_id: str, content: str) -> dict:
        """存储记忆到引擎
        
        Args:
            user_id: 用户唯一标识
            content: 记忆内容
            
        Returns:
            包含 memory_id 的字典
            
        Raises:
            ConnectionError: 连接引擎失败
            ValueError: 参数验证失败
            
        Example:
            >>> adapter = MemobaseAdapter(api_key="xxx")
            >>> result = await adapter.store("user_123", "我喜欢 Python")
            >>> print(result["memory_id"])
        """
        pass
```

---

## 2. 项目结构

### 2.1 目录结构

```
CozyMemory/
├── src/                          # 源代码
│   ├── api/                      # API 层 (FastAPI)
│   │   ├── v1/                   # API v1
│   │   │   ├── routes/           # 路由
│   │   │   ├── schemas/          # Pydantic 模型
│   │   │   └── deps.py           # 依赖注入
│   │   └── deps.py               # API 依赖
│   ├── adapters/                 # 引擎适配器
│   │   ├── base.py               # 基类
│   │   ├── memobase.py           # Memobase 适配器
│   │   ├── mem0.py               # Mem0 适配器
│   │   └── cognee.py             # Cognee 适配器
│   ├── services/                 # 业务服务
│   │   ├── cache.py              # 缓存服务
│   │   ├── router.py             # 路由服务
│   │   ├── fusion.py             # 融合服务
│   │   └── batch.py              # 批量处理
│   ├── models/                   # 数据模型
│   │   ├── memory.py             # 记忆模型
│   │   └── user.py               # 用户模型
│   ├── utils/                    # 工具函数
│   │   ├── logger.py             # 日志配置
│   │   ├── metrics.py            # 指标收集
│   │   └── helpers.py            # 辅助函数
│   └── config.py                 # 配置管理
├── tests/                        # 测试代码
│   ├── unit/                     # 单元测试
│   ├── integration/              # 集成测试
│   └── performance/              # 性能测试
├── deploy/                       # 部署配置
│   ├── docker/                   # Docker 配置
│   ├── k8s/                      # Kubernetes 配置
│   └── monitoring/               # 监控配置
├── scripts/                      # 脚本工具
├── docs/                         # 文档
├── pyproject.toml                # 项目配置
├── Dockerfile                    # Docker 镜像
└── README.md                     # 项目说明
```

### 2.2 模块导入规则

**导入顺序**:
1. 标准库
2. 第三方库
3. 本地模块

**示例**:
```python
# 标准库
import asyncio
import json
from typing import List, Optional

# 第三方库
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import redis.asyncio as redis

# 本地模块
from src.adapters.base import MemoryAdapter
from src.services.cache import CacheService
from src.config import settings
```

---

## 3. Git 工作流

### 3.1 分支策略

```
main (生产分支，受保护)
  ↑
develop (开发分支)
  ↑
feature/xxx (功能分支)
  ↑
bugfix/xxx (修复分支)
  ↑
hotfix/xxx (紧急修复)
```

**分支命名**:
- `feature/add-memobase-adapter` - 新功能
- `bugfix/fix-cache-ttl` - Bug 修复
- `hotfix/security-patch` - 紧急修复
- `docs/update-readme` - 文档更新

### 3.2 提交信息规范

遵循 **Conventional Commits** 规范：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type 类型**:
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式 (不影响功能)
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具/配置

**示例**:
```bash
# ✅ 好的提交信息
feat(adapter): 添加 Memobase 适配器实现

- 实现 MemoryAdapter 基类
- 添加 store/retrieve/search 方法
- 添加单元测试

Closes #123

# ❌ 不好的提交信息
更新代码
```

### 3.3 Pull Request 流程

```
1. 创建功能分支 (git checkout -b feature/xxx)
2. 开发 + 提交 (git commit -m "feat: ...")
3. 推送分支 (git push origin feature/xxx)
4. 创建 Pull Request (GitHub)
5. CI 自动检查 (单元测试/代码质量)
6. 技术负责人审查 (Code Review)
7. 修改 (如有问题)
8. 合并到 develop 分支
```

**PR 模板**:
```markdown
## 变更描述
简要描述此 PR 的目的

## 关联 Issue
Closes #123

## 测试计划
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 手动测试完成

## 截图 (如适用)
[截图]

## 检查清单
- [ ] 代码符合规范
- [ ] 添加了必要的测试
- [ ] 更新了文档
- [ ] 无安全漏洞
```

---

## 4. 测试规范

### 4.1 测试金字塔

```
        /\
       / E2E \       验收测试 (10%)
      /--------\
     / Integration \  集成测试 (20%)
    /----------------\
   /     Unit Tests   \ 单元测试 (70%)
  /--------------------\
```

### 4.2 单元测试规范

**文件命名**: `test_<module>.py`

**示例**:
```python
# tests/unit/test_memobase_adapter.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.adapters.memobase import MemobaseAdapter


class TestMemobaseAdapter:
    """Memobase 适配器单元测试"""
    
    @pytest.fixture
    def mock_client(self):
        """模拟 Memobase 客户端"""
        client = AsyncMock()
        client.store.return_value = {"id": "mem_123"}
        return client
    
    @pytest.fixture
    def adapter(self, mock_client):
        """创建适配器实例"""
        adapter = MemobaseAdapter(api_key="test_key")
        adapter.client = mock_client
        return adapter
    
    @pytest.mark.asyncio
    async def test_store_success(self, adapter, mock_client):
        """测试存储成功场景"""
        # Arrange
        user_id = "user_123"
        content = "我喜欢 Python"
        
        # Act
        result = await adapter.store(user_id, content)
        
        # Assert
        assert result["id"] == "mem_123"
        mock_client.store.assert_called_once_with(
            user_id=user_id,
            content=content
        )
    
    @pytest.mark.asyncio
    async def test_store_invalid_user_id(self, adapter):
        """测试无效 user_id"""
        # Arrange
        user_id = ""  # 空字符串
        
        # Act & Assert
        with pytest.raises(ValueError, match="user_id 不能为空"):
            await adapter.store(user_id, "content")
```

### 4.3 测试覆盖率要求

| 指标 | 最低要求 | 目标值 |
|------|---------|--------|
| 行覆盖率 | 80% | 90% |
| 分支覆盖率 | 70% | 85% |
| 函数覆盖率 | 90% | 95% |

**检查命令**:
```bash
pytest --cov=src --cov-report=html --cov-fail-under=80
```

---

## 5. API 设计规范

### 5.1 RESTful 规范

**资源命名**:
- 使用复数名词：`/api/v1/memories`
- 小写字母 + 连字符：`/api/v1/user-profiles`

**HTTP 方法**:
- `GET`: 查询
- `POST`: 创建
- `PUT`: 全量更新
- `PATCH`: 部分更新
- `DELETE`: 删除

**状态码**:
- `200 OK`: 成功
- `201 Created`: 创建成功
- `204 No Content`: 删除成功
- `400 Bad Request`: 请求参数错误
- `401 Unauthorized`: 未授权
- `404 Not Found`: 资源不存在
- `429 Too Many Requests`: 请求限流
- `500 Internal Server Error`: 服务器错误

### 5.2 响应格式

**成功响应**:
```json
{
  "status": "success",
  "data": {
    "id": "mem_123",
    "user_id": "user_456",
    "content": "我喜欢 Python",
    "created_at": "2026-04-05T12:00:00Z"
  },
  "meta": {
    "request_id": "req_789",
    "timestamp": "2026-04-05T12:00:00Z"
  }
}
```

**错误响应**:
```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "参数验证失败",
    "details": [
      {
        "field": "user_id",
        "message": "user_id 不能为空"
      }
    ]
  },
  "meta": {
    "request_id": "req_789",
    "timestamp": "2026-04-05T12:00:00Z"
  }
}
```

### 5.3 分页规范

**查询参数**:
- `page`: 页码 (从 1 开始)
- `page_size`: 每页数量 (默认 20，最大 100)

**响应格式**:
```json
{
  "status": "success",
  "data": [...],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "total_pages": 5
  }
}
```

---

## 6. 日志规范

### 6.1 日志级别

| 级别 | 使用场景 |
|------|---------|
| DEBUG | 调试信息 (开发环境) |
| INFO | 正常业务日志 |
| WARNING | 警告 (不影响功能) |
| ERROR | 错误 (需要处理) |
| CRITICAL | 严重错误 (系统崩溃) |

### 6.2 日志格式

```python
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ✅ 好的日志
logger.info("记忆存储成功", extra={
    "user_id": user_id,
    "memory_id": memory_id,
    "engine": "memobase"
})

logger.error("记忆存储失败", extra={
    "user_id": user_id,
    "error": str(e),
    "traceback": traceback.format_exc()
}, exc_info=True)

# ❌ 不好的日志
print("存储成功")
logger.debug("xxx")  # 无上下文
```

### 6.3 日志配置

```python
# src/utils/logger.py
import logging
import sys
from datetime import datetime

def get_logger(name: str) -> logging.Logger:
    """获取日志器"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 控制台处理器
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    
    # 格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    return logger
```

---

## 7. 安全规范

### 7.1 敏感信息处理

**禁止硬编码密钥**:
```python
# ❌ 禁止
API_KEY = "sk-1234567890"

# ✅ 正确
from src.config import settings
API_KEY = settings.openai_api_key
```

**环境变量**:
```bash
# .env 文件 (不提交到 Git)
OPENAI_API_KEY=sk-xxx
DATABASE_URL=postgresql://user:pass@localhost/db
REDIS_URL=redis://localhost:6379
```

### 7.2 输入验证

**使用 Pydantic 验证**:
```python
from pydantic import BaseModel, Field, validator

class MemoryRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1, max_length=10000)
    intent: Optional[str] = Field(None, pattern="^(fact|profile|knowledge)$")
    
    @validator('content')
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError('content 不能为空')
        return v.strip()
```

### 7.3 SQL 注入防护

**使用参数化查询**:
```python
# ❌ 禁止 (SQL 注入风险)
cursor.execute(f"SELECT * FROM memories WHERE user_id = '{user_id}'")

# ✅ 正确
cursor.execute("SELECT * FROM memories WHERE user_id = %s", (user_id,))
```

---

## 8. 性能规范

### 8.1 数据库查询优化

**添加索引**:
```sql
CREATE INDEX idx_memories_user_id ON memories(user_id);
CREATE INDEX idx_memories_created_at ON memories(created_at);
```

**避免 N+1 查询**:
```python
# ❌ 禁止 (N+1 查询)
for user in users:
    memories = await get_memories(user.id)

# ✅ 正确
user_memories = await get_memories_for_users([u.id for u in users])
```

### 8.2 缓存策略

**使用 Redis 缓存**:
```python
from src.services.cache import CacheService

cache = CacheService()

async def get_user_profile(user_id: str):
    # 1. 检查缓存
    cached = await cache.get(f"profile:{user_id}")
    if cached:
        return cached
    
    # 2. 查询数据库
    profile = await db.query(...)
    
    # 3. 写入缓存 (TTL 1 小时)
    await cache.setex(f"profile:{user_id}", 3600, profile)
    
    return profile
```

### 8.3 异步编程

**使用 async/await**:
```python
# ✅ 正确 (异步)
async def store_memories(memories: List[dict]):
    tasks = [store_single(m) for m in memories]
    results = await asyncio.gather(*tasks)
    return results

# ❌ 避免 (同步阻塞)
def store_memories(memories: List[dict]):
    results = []
    for m in memories:
        results.append(store_single(m))  # 阻塞
    return results
```

---

## 9. 文档规范

### 9.1 README 模板

```markdown
# CozyMemory

统一 AI 记忆服务平台

## 快速开始

```bash
# 安装依赖
pip install -e .

# 启动服务
docker-compose up -d

# 运行测试
pytest
```

## API 文档

http://localhost:8000/docs

## 开发指南

参见 [docs/](docs/) 目录
```

### 9.2 API 文档

使用 **FastAPI 自动生成**:
```python
@app.post("/api/v1/memories", response_model=MemoryResponse)
async def create_memory(
    request: MemoryRequest,
    current_user: dict = Depends(get_current_user)
):
    """创建记忆
    
    - **user_id**: 用户 ID
    - **content**: 记忆内容
    - **intent**: 意图类型 (fact/profile/knowledge)
    """
    ...
```

访问：http://localhost:8000/docs

---

## 10. 代码审查清单

### 10.1 审查要点

**代码质量**:
- [ ] 代码符合 PEP 8 规范
- [ ] 有完整的类型注解
- [ ] 有文档字符串
- [ ] 无重复代码 (DRY)
- [ ] 函数职责单一 (SRP)

**测试**:
- [ ] 单元测试覆盖率 >80%
- [ ] 边界条件测试
- [ ] 错误处理测试

**安全**:
- [ ] 无硬编码密钥
- [ ] 输入验证完整
- [ ] 无 SQL 注入风险
- [ ] 无敏感信息泄露

**性能**:
- [ ] 无 N+1 查询
- [ ] 有缓存策略
- [ ] 使用异步编程

**文档**:
- [ ] 更新了 README
- [ ] 更新了 API 文档
- [ ] 添加了变更日志

---

## 11. 工具配置

### 11.1 pyproject.toml

```toml
[tool.black]
line-length = 88
target-version = ['py310']
include = '\.pyi?$'

[tool.isort]
profile = "black"
line_length = 88

[tool.flake8]
max-line-length = 88
extend-ignore = "E203,W503"

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-v --cov=src --cov-report=html"
```

### 11.2 .pre-commit-config.yaml

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
```

---

## 12. 违规处理

| 违规级别 | 处理方式 |
|---------|---------|
| 轻微 (格式问题) | 自动修复 + 提醒 |
| 一般 (缺少测试) | 要求补充 + 重新审查 |
| 严重 (安全漏洞) | 拒绝合并 + 团队通报 |
| 重大 (数据泄露) | 事故处理流程 |

---

**审批**

| 角色 | 姓名 | 签字 | 日期 |
|------|------|------|------|
| 技术负责人 | 蟹小五 | | 2026-04-05 |
| 项目经理 | | | |

---

**版本历史**

| 版本 | 日期 | 作者 | 变更描述 |
|------|------|------|---------|
| 1.0 | 2026-04-05 | 蟹小五 | 初始版本 |

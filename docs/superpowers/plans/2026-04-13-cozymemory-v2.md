# CozyMemory v2.0 实现计划

> **For agentic workers:** REQUIRED: Use the `subagent-driven-development` agent (recommended) or `executing-plans` agent to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从零构建 CozyMemory v2.0 薄服务层，整合 Mem0（会话记忆）、Memobase（用户画像）、Cognee（知识库）三大引擎，提供统一的 REST + gRPC 双协议 API。

**Architecture:** 三引擎按领域独立运作，不做路由/融合/缓存。服务层仅做请求转发和错误转换。每个领域（会话记忆、用户画像、知识库）有独立的 Client → Service → API Router 链路。所有客户端继承 BaseClient，统一 httpx 连接池、重试策略和错误处理。

**Tech Stack:** Python 3.11+, FastAPI 0.110+, httpx[http2] 0.27+, Pydantic v2, pydantic-settings, grpcio 1.60+, structlog 24.0+, pytest 8.0+

---

## 文件结构总览

```
CozyMemory/
├── pyproject.toml                          # [Task 1] 项目配置
├── requirements.txt                        # [Task 1] 生产依赖
├── requirements-dev.txt                    # [Task 1] 开发依赖
├── .env.example                            # [Task 1] 环境变量模板
├── Dockerfile                              # [Task 12] 容器构建
├── docker-compose.yml                      # [Task 12] 本地编排
│
├── proto/                                  # [Task 9] gRPC Proto 定义
│   ├── common.proto
│   ├── conversation.proto
│   ├── profile.proto
│   └── knowledge.proto
│
├── scripts/
│   └── generate_grpc.sh                    # [Task 9] gRPC 代码生成
│
├── src/
│   └── cozymemory/
│       ├── __init__.py                     # [Task 1] 包初始化
│       ├── app.py                          # [Task 10] FastAPI 应用入口
│       ├── config.py                       # [Task 2] 配置管理
│       │
│       ├── models/                          # [Task 3] 统一数据模型
│       │   ├── __init__.py
│       │   ├── common.py                   # 通用模型 (Message, Health, Error)
│       │   ├── conversation.py             # 会话记忆模型
│       │   ├── profile.py                  # 用户画像模型
│       │   └── knowledge.py                # 知识库模型
│       │
│       ├── clients/                         # [Task 4-6] SDK 客户端
│       │   ├── __init__.py
│       │   ├── base.py                     # [Task 4] BaseClient + EngineError
│       │   ├── mem0.py                     # [Task 5] Mem0 客户端
│       │   ├── memobase.py                 # [Task 6] Memobase 客户端
│       │   └── cognee.py                   # [Task 6] Cognee 客户端
│       │
│       ├── services/                        # [Task 7] 业务服务层
│       │   ├── __init__.py
│       │   ├── conversation.py             # 会话记忆服务
│       │   ├── profile.py                  # 用户画像服务
│       │   └── knowledge.py                # 知识库服务
│       │
│       ├── api/                             # [Task 8+10-11] REST API
│       │   ├── __init__.py
│       │   ├── deps.py                     # [Task 8] 依赖注入
│       │   └── v1/
│       │       ├── __init__.py
│       │       ├── router.py               # [Task 10] 汇总路由
│       │       ├── health.py               # [Task 10] 健康检查端点
│       │       ├── conversation.py         # [Task 11] 会话记忆端点
│       │       ├── profile.py              # [Task 11] 用户画像端点
│       │       └── knowledge.py            # [Task 11] 知识库端点
│       │
│       └── grpc_server/                     # [Task 9] gRPC 服务
│           ├── __init__.py
│           └── server.py
│
├── tests/
│   ├── conftest.py                         # [Task 1] 测试配置
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_models_common.py           # [Task 3] 通用模型测试
│   │   ├── test_models_conversation.py     # [Task 3] 会话模型测试
│   │   ├── test_models_profile.py          # [Task 3] 画像模型测试
│   │   ├── test_models_knowledge.py        # [Task 3] 知识库模型测试
│   │   ├── test_base_client.py             # [Task 4] BaseClient 测试
│   │   ├── test_mem0_client.py            # [Task 5] Mem0 客户端测试
│   │   ├── test_memobase_client.py        # [Task 6] Memobase 客户端测试
│   │   ├── test_cognee_client.py          # [Task 6] Cognee 客户端测试
│   │   ├── test_conversation_service.py   # [Task 7] 会话服务测试
│   │   ├── test_profile_service.py        # [Task 7] 画像服务测试
│   │   └── test_knowledge_service.py      # [Task 7] 知识库服务测试
│   └── integration/
│       ├── __init__.py
│       ├── test_health_api.py              # [Task 10] 健康检查集成测试
│       ├── test_conversation_api.py        # [Task 11] 会话 API 集成测试
│       ├── test_profile_api.py             # [Task 11] 画像 API 集成测试
│       └── test_knowledge_api.py           # [Task 11] 知识库 API 集成测试
```

---

### Task 1: 项目脚手架与依赖管理

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `.env.example`
- Create: `src/cozymemory/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/integration/__init__.py`

- [ ] **Step 1: 创建 pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "cozymemory"
version = "2.0.0"
description = "统一 AI 记忆服务平台 - 整合 Mem0, Memobase, Cognee 三大引擎"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.29.0",
    "httpx[http2]>=0.27.0",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "grpcio>=1.60.0",
    "grpcio-tools>=1.60.0",
    "protobuf>=4.25.0",
    "structlog>=24.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "ruff>=0.3",
    "mypy>=1.9",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = [
    "unit: unit tests",
    "integration: integration tests",
]

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.mypy]
python_version = "3.11"
strict = true
```

- [ ] **Step 2: 创建 requirements.txt**

```
# 核心框架
fastapi>=0.110.0
uvicorn[standard]>=0.29.0

# HTTP 客户端
httpx[http2]>=0.27.0

# 数据验证
pydantic>=2.0
pydantic-settings>=2.0

# gRPC
grpcio>=1.60.0
grpcio-tools>=1.60.0
protobuf>=4.25.0

# 日志
structlog>=24.0
```

- [ ] **Step 3: 创建 requirements-dev.txt**

```
-r requirements.txt

# 测试
pytest>=8.0
pytest-asyncio>=0.23
pytest-cov>=5.0
httpx

# 代码质量
ruff>=0.3
mypy>=1.9
```

- [ ] **Step 4: 创建 .env.example**

```bash
# ==================== 应用配置 ====================
APP_NAME=CozyMemory
APP_VERSION=2.0.0
APP_ENV=development
DEBUG=true
HOST=0.0.0.0
PORT=8000
GRPC_PORT=50051

# ==================== 日志配置 ====================
LOG_LEVEL=INFO
LOG_FORMAT=json

# ==================== Mem0 引擎 ====================
MEM0_API_URL=http://localhost:8888
MEM0_API_KEY=
MEM0_TIMEOUT=30.0
MEM0_ENABLED=true

# ==================== Memobase 引擎 ====================
MEMOBASE_API_URL=http://localhost:8019
MEMOBASE_API_KEY=secret
MEMOBASE_TIMEOUT=60.0
MEMOBASE_ENABLED=true

# ==================== Cognee 引擎 ====================
COGNEE_API_URL=http://localhost:8000
COGNEE_API_KEY=
COGNEE_TIMEOUT=300.0
COGNEE_ENABLED=true
```

- [ ] **Step 5: 创建包初始化文件**

`src/cozymemory/__init__.py`:
```python
"""CozyMemory - 统一 AI 记忆服务平台"""

__version__ = "2.0.0"
```

- [ ] **Step 6: 创建测试配置**

`tests/conftest.py`:
```python
"""Pytest 全局配置"""

import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"
```

`tests/unit/__init__.py`:
```python
```

`tests/integration/__init__.py`:
```python
```

- [ ] **Step 7: 安装依赖并验证**

Run: `cd /config/CozyProjects/CozyMemory && pip install -r requirements-dev.txt`
Expected: 所有包安装成功

- [ ] **Step 8: 运行 pytest 确认框架可用**

Run: `cd /config/CozyProjects/CozyMemory && pytest --co -q`
Expected: 无报错（可能 0 tests collected）

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml requirements.txt requirements-dev.txt .env.example src/ tests/
git commit -m "chore: initialize CozyMemory v2.0 project scaffold"
```

---

### Task 2: 配置管理

**Files:**
- Create: `src/cozymemory/config.py`
- Test: `tests/unit/test_config.py`

- [ ] **Step 1: 写失败测试**

`tests/unit/test_config.py`:
```python
"""配置管理测试"""

import os
import pytest
from cozymemory.config import Settings


def test_settings_defaults():
    """默认配置值正确"""
    s = Settings()
    assert s.APP_NAME == "CozyMemory"
    assert s.APP_VERSION == "2.0.0"
    assert s.APP_ENV == "development"
    assert s.DEBUG is True
    assert s.PORT == 8000
    assert s.GRPC_PORT == 50051


def test_settings_mem0_defaults():
    """Mem0 引擎默认配置"""
    s = Settings()
    assert s.MEM0_API_URL == "http://localhost:8888"
    assert s.MEM0_TIMEOUT == 30.0
    assert s.MEM0_ENABLED is True


def test_settings_memobase_defaults():
    """Memobase 引擎默认配置"""
    s = Settings()
    assert s.MEMOBASE_API_URL == "http://localhost:8019"
    assert s.MEMOBASE_API_KEY == "secret"
    assert s.MEMOBASE_TIMEOUT == 60.0
    assert s.MEMOBASE_ENABLED is True


def test_settings_cognee_defaults():
    """Cognee 引擎默认配置"""
    s = Settings()
    assert s.COGNEE_API_URL == "http://localhost:8000"
    assert s.COGNEE_TIMEOUT == 300.0
    assert s.COGNEE_ENABLED is True


def test_settings_from_env(monkeypatch):
    """从环境变量读取配置"""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("MEM0_API_URL", "http://mem0:8000")
    monkeypatch.setenv("MEM0_ENABLED", "false")
    s = Settings()
    assert s.APP_ENV == "production"
    assert s.MEM0_API_URL == "http://mem0:8000"
    assert s.MEM0_ENABLED is False


def test_settings_singleton():
    """全局 settings 实例可用"""
    from cozymemory.config import settings
    assert settings.APP_NAME == "CozyMemory"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /config/CozyProjects/CozyMemory && pytest tests/unit/test_config.py -v`
Expected: FAIL - ModuleNotFoundError: No module named 'cozymemory'

- [ ] **Step 3: 实现配置管理**

`src/cozymemory/config.py`:
```python
"""CozyMemory 配置管理

使用 pydantic-settings 从环境变量和 .env 文件加载配置。
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，支持环境变量和 .env 文件"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 应用配置
    APP_NAME: str = "CozyMemory"
    APP_VERSION: str = "2.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # 服务配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    GRPC_PORT: int = 50051

    # Mem0 引擎
    MEM0_API_URL: str = "http://localhost:8888"
    MEM0_API_KEY: str = ""
    MEM0_TIMEOUT: float = 30.0
    MEM0_ENABLED: bool = True

    # Memobase 引擎
    MEMOBASE_API_URL: str = "http://localhost:8019"
    MEMOBASE_API_KEY: str = "secret"
    MEMOBASE_TIMEOUT: float = 60.0
    MEMOBASE_ENABLED: bool = True

    # Cognee 引擎
    COGNEE_API_URL: str = "http://localhost:8000"
    COGNEE_API_KEY: str = ""
    COGNEE_TIMEOUT: float = 300.0
    COGNEE_ENABLED: bool = True

    # 日志
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"


settings = Settings()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /config/CozyProjects/CozyMemory && pytest tests/unit/test_config.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/cozymemory/config.py tests/unit/test_config.py
git commit -m "feat: add configuration management with pydantic-settings"
```

---

### Task 3: 统一数据模型

**Files:**
- Create: `src/cozymemory/models/__init__.py`
- Create: `src/cozymemory/models/common.py`
- Create: `src/cozymemory/models/conversation.py`
- Create: `src/cozymemory/models/profile.py`
- Create: `src/cozymemory/models/knowledge.py`
- Test: `tests/unit/test_models_common.py`
- Test: `tests/unit/test_models_conversation.py`
- Test: `tests/unit/test_models_profile.py`
- Test: `tests/unit/test_models_knowledge.py`

- [ ] **Step 1: 写通用模型失败测试**

`tests/unit/test_models_common.py`:
```python
"""通用数据模型测试"""

import pytest
from datetime import datetime
from cozymemory.models.common import Message, EngineStatus, HealthResponse, ErrorResponse


def test_message_creation():
    """Message 正确创建"""
    msg = Message(role="user", content="你好")
    assert msg.role == "user"
    assert msg.content == "你好"
    assert msg.created_at is None


def test_message_with_timestamp():
    """Message 带时间戳"""
    msg = Message(role="assistant", content="你好！", created_at="2026-04-13T10:00:00Z")
    assert msg.created_at == "2026-04-13T10:00:00Z"


def test_message_validation_error():
    """Message 缺少必填字段时验证失败"""
    with pytest.raises(Exception):
        Message(role="user")  # 缺少 content


def test_engine_status_healthy():
    """EngineStatus 健康状态"""
    status = EngineStatus(name="Mem0", status="healthy", latency_ms=12.5)
    assert status.name == "Mem0"
    assert status.status == "healthy"
    assert status.error is None


def test_engine_status_unhealthy():
    """EngineStatus 异常状态"""
    status = EngineStatus(name="Cognee", status="unhealthy", error="连接超时")
    assert status.status == "unhealthy"
    assert status.error == "连接超时"


def test_health_response():
    """HealthResponse 正确创建"""
    resp = HealthResponse(
        status="healthy",
        engines={
            "mem0": EngineStatus(name="Mem0", status="healthy", latency_ms=10.0),
        },
    )
    assert resp.status == "healthy"
    assert "mem0" in resp.engines
    assert resp.timestamp is not None


def test_health_response_degraded():
    """HealthResponse 降级状态"""
    resp = HealthResponse(
        status="degraded",
        engines={
            "mem0": EngineStatus(name="Mem0", status="healthy"),
            "cognee": EngineStatus(name="Cognee", status="unhealthy", error="超时"),
        },
    )
    assert resp.status == "degraded"


def test_error_response():
    """ErrorResponse 正确创建"""
    err = ErrorResponse(error="EngineError", detail="Mem0 不可用", engine="mem0")
    assert err.success is False
    assert err.error == "EngineError"
    assert err.engine == "mem0"
```

- [ ] **Step 2: 写会话记忆模型失败测试**

`tests/unit/test_models_conversation.py`:
```python
"""会话记忆模型测试"""

import pytest
from cozymemory.models.conversation import (
    ConversationMemoryCreate,
    ConversationMemorySearch,
    ConversationMemory,
    ConversationMemoryListResponse,
)
from cozymemory.models.common import Message


def test_conversation_memory_create():
    """ConversationMemoryCreate 正确创建"""
    req = ConversationMemoryCreate(
        user_id="user_123",
        messages=[Message(role="user", content="我喜欢咖啡")],
    )
    assert req.user_id == "user_123"
    assert len(req.messages) == 1
    assert req.infer is True
    assert req.metadata is None


def test_conversation_memory_create_with_metadata():
    """ConversationMemoryCreate 带元数据"""
    req = ConversationMemoryCreate(
        user_id="user_123",
        messages=[Message(role="user", content="我喜欢咖啡")],
        metadata={"source": "chat", "session_id": "sess_001"},
        infer=False,
    )
    assert req.metadata["source"] == "chat"
    assert req.infer is False


def test_conversation_memory_create_validation():
    """ConversationMemoryCreate 空消息验证失败"""
    with pytest.raises(Exception):
        ConversationMemoryCreate(user_id="user_123", messages=[])


def test_conversation_memory_search():
    """ConversationMemorySearch 正确创建"""
    req = ConversationMemorySearch(user_id="user_123", query="咖啡")
    assert req.limit == 10
    assert req.threshold is None


def test_conversation_memory_search_limit_range():
    """ConversationMemorySearch limit 范围验证"""
    with pytest.raises(Exception):
        ConversationMemorySearch(user_id="user_123", query="咖啡", limit=0)
    with pytest.raises(Exception):
        ConversationMemorySearch(user_id="user_123", query="咖啡", limit=101)


def test_conversation_memory_response():
    """ConversationMemory 响应模型"""
    mem = ConversationMemory(
        id="mem_123",
        user_id="user_123",
        content="用户喜欢喝拿铁咖啡",
        score=0.92,
    )
    assert mem.id == "mem_123"
    assert mem.score == 0.92


def test_conversation_memory_list_response():
    """ConversationMemoryListResponse 正确创建"""
    resp = ConversationMemoryListResponse(
        data=[
            ConversationMemory(id="mem_1", user_id="u1", content="事实1"),
            ConversationMemory(id="mem_2", user_id="u1", content="事实2"),
        ],
        total=2,
    )
    assert resp.success is True
    assert resp.total == 2
```

- [ ] **Step 3: 写用户画像模型失败测试**

`tests/unit/test_models_profile.py`:
```python
"""用户画像模型测试"""

import pytest
from cozymemory.models.profile import (
    ProfileInsertRequest,
    ProfileFlushRequest,
    ProfileContextRequest,
    ProfileTopic,
    UserProfile,
    ProfileContext,
    ProfileInsertResponse,
)
from cozymemory.models.common import Message


def test_profile_insert_request():
    """ProfileInsertRequest 正确创建"""
    req = ProfileInsertRequest(
        user_id="user_123",
        messages=[Message(role="user", content="我叫小明")],
    )
    assert req.sync is False


def test_profile_flush_request():
    """ProfileFlushRequest 正确创建"""
    req = ProfileFlushRequest(user_id="user_123", sync=True)
    assert req.sync is True


def test_profile_context_request():
    """ProfileContextRequest 正确创建"""
    req = ProfileContextRequest(user_id="user_123", max_token_size=500)
    assert req.max_token_size == 500
    assert req.chats is None


def test_profile_context_request_token_range():
    """ProfileContextRequest token 范围验证"""
    with pytest.raises(Exception):
        ProfileContextRequest(user_id="user_123", max_token_size=50)
    with pytest.raises(Exception):
        ProfileContextRequest(user_id="user_123", max_token_size=5001)


def test_profile_topic():
    """ProfileTopic 正确创建"""
    topic = ProfileTopic(
        id="prof_123",
        topic="basic_info",
        sub_topic="name",
        content="小明",
    )
    assert topic.topic == "basic_info"
    assert topic.sub_topic == "name"


def test_user_profile():
    """UserProfile 正确创建"""
    profile = UserProfile(
        user_id="user_123",
        topics=[
            ProfileTopic(id="p1", topic="basic_info", sub_topic="name", content="小明"),
        ],
    )
    assert len(profile.topics) == 1


def test_profile_context():
    """ProfileContext 正确创建"""
    ctx = ProfileContext(user_id="user_123", context="# Memory\n用户背景...")
    assert "用户背景" in ctx.context


def test_profile_insert_response():
    """ProfileInsertResponse 正确创建"""
    resp = ProfileInsertResponse(user_id="user_123", blob_id="blob_123")
    assert resp.success is True
    assert resp.blob_id == "blob_123"
```

- [ ] **Step 4: 写知识库模型失败测试**

`tests/unit/test_models_knowledge.py`:
```python
"""知识库模型测试"""

import pytest
from cozymemory.models.knowledge import (
    KnowledgeAddRequest,
    KnowledgeCognifyRequest,
    KnowledgeSearchRequest,
    KnowledgeSearchResult,
    KnowledgeDataset,
    KnowledgeAddResponse,
    KnowledgeCognifyResponse,
    KnowledgeSearchResponse,
    KnowledgeDatasetListResponse,
)


def test_knowledge_add_request():
    """KnowledgeAddRequest 正确创建"""
    req = KnowledgeAddRequest(data="文本内容", dataset="my-dataset")
    assert req.node_set is None


def test_knowledge_add_request_validation():
    """KnowledgeAddRequest 空内容验证失败"""
    with pytest.raises(Exception):
        KnowledgeAddRequest(data="", dataset="my-dataset")


def test_knowledge_cognify_request():
    """KnowledgeCognifyRequest 正确创建"""
    req = KnowledgeCognifyRequest()
    assert req.datasets is None
    assert req.run_in_background is True


def test_knowledge_search_request():
    """KnowledgeSearchRequest 正确创建"""
    req = KnowledgeSearchRequest(query="Cognee 是什么？")
    assert req.search_type == "GRAPH_COMPLETION"
    assert req.top_k == 10


def test_knowledge_search_result():
    """KnowledgeSearchResult 允许额外字段"""
    result = KnowledgeSearchResult(id="node_1", text="内容", score=0.95, extra_field="value")
    assert result.id == "node_1"


def test_knowledge_dataset():
    """KnowledgeDataset 正确创建"""
    ds = KnowledgeDataset(id="uuid-123", name="my-dataset")
    assert ds.name == "my-dataset"


def test_knowledge_add_response():
    """KnowledgeAddResponse 正确创建"""
    resp = KnowledgeAddResponse(data_id="data_123", dataset_name="my-dataset")
    assert resp.success is True


def test_knowledge_cognify_response():
    """KnowledgeCognifyResponse 正确创建"""
    resp = KnowledgeCognifyResponse(pipeline_run_id="pipe_123", status="pending")
    assert resp.status == "pending"


def test_knowledge_search_response():
    """KnowledgeSearchResponse 正确创建"""
    resp = KnowledgeSearchResponse(
        data=[KnowledgeSearchResult(id="1", text="结果")],
        total=1,
    )
    assert resp.total == 1


def test_knowledge_dataset_list_response():
    """KnowledgeDatasetListResponse 正确创建"""
    resp = KnowledgeDatasetListResponse(
        data=[KnowledgeDataset(id="1", name="ds1")],
    )
    assert resp.success is True
```

- [ ] **Step 5: 运行测试确认失败**

Run: `cd /config/CozyProjects/CozyMemory && pytest tests/unit/test_models_common.py tests/unit/test_models_conversation.py tests/unit/test_models_profile.py tests/unit/test_models_knowledge.py -v`
Expected: FAIL - ModuleNotFoundError

- [ ] **Step 6: 实现通用模型**

`src/cozymemory/models/__init__.py`:
```python
"""CozyMemory 数据模型"""
```

`src/cozymemory/models/common.py`:
```python
"""通用数据模型

包含 Message、EngineStatus、HealthResponse、ErrorResponse。
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any


class Message(BaseModel):
    """对话消息（Mem0 和 Memobase 共用）"""

    role: str = Field(..., description="角色: user / assistant / system")
    content: str = Field(..., description="消息内容")
    created_at: str | None = Field(None, description="消息时间戳 (ISO 8601)")


class EngineStatus(BaseModel):
    """引擎健康状态"""

    name: str = Field(..., description="引擎名称")
    status: str = Field(..., description="状态: healthy / unhealthy")
    latency_ms: float | None = Field(None, description="响应延迟(ms)")
    error: str | None = Field(None, description="错误信息")


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str = Field(..., description="整体状态: healthy / degraded / unhealthy")
    engines: dict[str, EngineStatus] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseModel):
    """错误响应"""

    success: bool = False
    error: str = Field(..., description="错误类型")
    detail: str | None = Field(None, description="错误详情")
    engine: str | None = Field(None, description="出错的引擎名称")
```

- [ ] **Step 7: 实现会话记忆模型**

`src/cozymemory/models/conversation.py`:
```python
"""会话记忆数据模型

对应引擎：Mem0
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any

from .common import Message


class ConversationMemoryCreate(BaseModel):
    """添加对话请求 → Mem0 自动提取事实"""

    user_id: str = Field(..., description="用户 ID", min_length=1)
    messages: list[Message] = Field(..., description="对话消息列表", min_length=1)
    metadata: dict[str, Any] | None = Field(None, description="元数据 (source, session_id 等)")
    infer: bool = Field(True, description="是否使用 LLM 提取事实。False 则原样存储")


class ConversationMemorySearch(BaseModel):
    """搜索会话记忆"""

    user_id: str = Field(..., description="用户 ID", min_length=1)
    query: str = Field(..., description="搜索查询文本", min_length=1)
    limit: int = Field(10, ge=1, le=100, description="返回数量限制")
    threshold: float | None = Field(None, ge=0, le=1, description="最低相似度阈值")


class ConversationMemory(BaseModel):
    """Mem0 返回的单条记忆（提取出的事实）"""

    id: str = Field(..., description="记忆 ID")
    user_id: str = Field(..., description="用户 ID")
    content: str = Field(..., description="提取的事实内容")
    score: float | None = Field(None, description="搜索相似度分数")
    metadata: dict[str, Any] | None = Field(None, description="元数据")
    created_at: datetime | None = Field(None, description="创建时间")
    updated_at: datetime | None = Field(None, description="更新时间")


class ConversationMemoryListResponse(BaseModel):
    """记忆列表响应"""

    success: bool = True
    data: list[ConversationMemory] = Field(default_factory=list)
    total: int = Field(0, description="总数")
    message: str = ""
```

- [ ] **Step 8: 实现用户画像模型**

`src/cozymemory/models/profile.py`:
```python
"""用户画像数据模型

对应引擎：Memobase
核心范式：插入对话 (insert) → 缓冲区 (buffer) → LLM 处理 (flush) → 生成画像 (profile)
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any

from .common import Message


class ProfileInsertRequest(BaseModel):
    """插入对话到 Memobase 缓冲区"""

    user_id: str = Field(..., description="用户 ID", min_length=1)
    messages: list[Message] = Field(..., description="对话消息列表", min_length=1)
    sync: bool = Field(False, description="是否同步等待处理完成")


class ProfileFlushRequest(BaseModel):
    """触发缓冲区处理"""

    user_id: str = Field(..., description="用户 ID", min_length=1)
    sync: bool = Field(False, description="是否同步等待处理完成")


class ProfileContextRequest(BaseModel):
    """获取上下文提示词请求"""

    user_id: str = Field(..., description="用户 ID", min_length=1)
    max_token_size: int = Field(500, ge=100, le=4000, description="上下文最大 token 数")
    chats: list[Message] | None = Field(None, description="近期对话（用于语义搜索匹配）")


class ProfileTopic(BaseModel):
    """画像中的单个主题条目"""

    id: str = Field(..., description="条目 ID")
    topic: str = Field(..., description="主题 (如 basic_info, interest)")
    sub_topic: str = Field(..., description="子主题 (如 name, hobby)")
    content: str = Field(..., description="内容")
    created_at: datetime | None = Field(None)
    updated_at: datetime | None = Field(None)


class UserProfile(BaseModel):
    """完整用户画像"""

    user_id: str = Field(..., description="用户 ID")
    topics: list[ProfileTopic] = Field(default_factory=list, description="画像主题列表")
    updated_at: datetime | None = Field(None)


class ProfileContext(BaseModel):
    """上下文提示词结果"""

    user_id: str = Field(..., description="用户 ID")
    context: str = Field(..., description="可直接插入 LLM prompt 的文本")


class ProfileInsertResponse(BaseModel):
    """插入响应"""

    success: bool = True
    user_id: str
    blob_id: str | None = Field(None, description="Blob ID")
    message: str = ""
```

- [ ] **Step 9: 实现知识库模型**

`src/cozymemory/models/knowledge.py`:
```python
"""知识库数据模型

对应引擎：Cognee
核心流程：添加文档 (add) → 构建知识图谱 (cognify) → 语义搜索 (search)
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any


class KnowledgeAddRequest(BaseModel):
    """添加文档到知识库"""

    data: str = Field(..., description="文本内容或文件路径", min_length=1)
    dataset: str = Field(..., description="数据集名称", min_length=1)
    node_set: list[str] | None = Field(None, description="节点集标识")


class KnowledgeCognifyRequest(BaseModel):
    """触发知识图谱构建"""

    datasets: list[str] | None = Field(None, description="要处理的数据集列表")
    run_in_background: bool = Field(True, description="是否后台运行")


class KnowledgeSearchRequest(BaseModel):
    """知识库搜索"""

    query: str = Field(..., description="搜索查询", min_length=1)
    dataset: str | None = Field(None, description="限定数据集")
    search_type: str = Field(
        "GRAPH_COMPLETION",
        description="搜索类型: GRAPH_COMPLETION, SUMMARIES, CHUNKS, RAG_COMPLETION",
    )
    top_k: int = Field(10, ge=1, le=100, description="返回数量限制")


class KnowledgeSearchResult(BaseModel):
    """搜索结果"""

    id: str | None = Field(None, description="结果 ID")
    text: str | None = Field(None, description="结果文本内容")
    score: float | None = Field(None, description="相关性分数")
    metadata: dict[str, Any] | None = Field(None, description="附加元数据")

    model_config = {"extra": "allow"}  # Cognee 返回字段不固定


class KnowledgeDataset(BaseModel):
    """数据集信息"""

    id: str = Field(..., description="数据集 ID (UUID)")
    name: str = Field(..., description="数据集名称")
    created_at: datetime | None = Field(None)
    updated_at: datetime | None = Field(None)


class KnowledgeAddResponse(BaseModel):
    """添加文档响应"""

    success: bool = True
    data_id: str | None = Field(None, description="数据项 ID")
    dataset_name: str | None = Field(None)
    message: str = ""


class KnowledgeCognifyResponse(BaseModel):
    """知识图谱构建响应"""

    success: bool = True
    pipeline_run_id: str | None = Field(None, description="管道运行 ID")
    status: str = Field("pending", description="状态: pending/running/completed/failed")
    message: str = ""


class KnowledgeSearchResponse(BaseModel):
    """搜索响应"""

    success: bool = True
    data: list[KnowledgeSearchResult] = Field(default_factory=list)
    total: int = Field(0)
    message: str = ""


class KnowledgeDatasetListResponse(BaseModel):
    """数据集列表响应"""

    success: bool = True
    data: list[KnowledgeDataset] = Field(default_factory=list)
    message: str = ""
```

- [ ] **Step 10: 运行所有模型测试确认通过**

Run: `cd /config/CozyProjects/CozyMemory && pytest tests/unit/test_models_common.py tests/unit/test_models_conversation.py tests/unit/test_models_profile.py tests/unit/test_models_knowledge.py -v`
Expected: ALL PASSED

- [ ] **Step 11: Commit**

```bash
git add src/cozymemory/models/ tests/unit/test_models_*.py
git commit -m "feat: add unified data models for conversation, profile and knowledge"
```

---

### Task 4: BaseClient 基类与 EngineError

**Files:**
- Create: `src/cozymemory/clients/__init__.py`
- Create: `src/cozymemory/clients/base.py`
- Test: `tests/unit/test_base_client.py`

- [ ] **Step 1: 写失败测试**

`tests/unit/test_base_client.py`:
```python
"""BaseClient 基类测试"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch

from cozymemory.clients.base import BaseClient, EngineError


def test_engine_error_creation():
    """EngineError 正确创建"""
    err = EngineError("Mem0", "服务不可用", 503)
    assert err.engine == "Mem0"
    assert err.message == "服务不可用"
    assert err.status_code == 503
    assert "[Mem0]" in str(err)


def test_engine_error_no_status():
    """EngineError 无状态码"""
    err = EngineError("Cognee", "连接超时")
    assert err.status_code is None


def test_base_client_init():
    """BaseClient 正确初始化"""
    client = BaseClient(engine_name="Test", api_url="http://localhost:8000")
    assert client.engine_name == "Test"
    assert client.api_url == "http://localhost:8000"
    assert client.max_retries == 3
    assert client.retry_delay == 1.0


def test_base_client_url_trailing_slash():
    """BaseClient 去除 URL 尾部斜杠"""
    client = BaseClient(engine_name="Test", api_url="http://localhost:8000/")
    assert client.api_url == "http://localhost:8000"


def test_base_client_headers_with_key():
    """BaseClient 带 API Key 的请求头"""
    client = BaseClient(engine_name="Test", api_url="http://localhost:8000", api_key="my-key")
    headers = client._get_headers()
    assert headers["Authorization"] == "Bearer my-key"
    assert headers["Content-Type"] == "application/json"


def test_base_client_headers_without_key():
    """BaseClient 无 API Key 的请求头"""
    client = BaseClient(engine_name="Test", api_url="http://localhost:8000")
    headers = client._get_headers()
    assert "Authorization" not in headers


@pytest.mark.asyncio
async def test_base_client_request_success():
    """BaseClient 成功请求"""
    client = BaseClient(engine_name="Test", api_url="http://localhost:8000")

    mock_response = httpx.Response(200, json={"status": "ok"})

    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=mock_response):
        response = await client._request("GET", "/health")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_base_client_request_4xx_no_retry():
    """BaseClient 4xx 错误不重试"""
    client = BaseClient(engine_name="Test", api_url="http://localhost:8000", max_retries=3)

    mock_response = httpx.Response(400, text="Bad Request")

    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=mock_response):
        with pytest.raises(EngineError) as exc_info:
            await client._request("GET", "/bad")
        assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_base_client_request_5xx_retry():
    """BaseClient 5xx 错误重试后抛异常"""
    client = BaseClient(engine_name="Test", api_url="http://localhost:8000", max_retries=2, retry_delay=0.01)

    mock_response = httpx.Response(500, text="Internal Server Error")

    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=mock_response) as mock_req:
        with pytest.raises(EngineError) as exc_info:
            await client._request("GET", "/error")
        assert exc_info.value.status_code == 500
        assert mock_req.call_count == 2  # 重试 2 次


@pytest.mark.asyncio
async def test_base_client_request_timeout_retry():
    """BaseClient 超时错误重试"""
    client = BaseClient(engine_name="Test", api_url="http://localhost:8000", max_retries=2, retry_delay=0.01)

    with patch.object(
        client._client, "request", new_callable=AsyncMock, side_effect=httpx.TimeoutException("timeout")
    ) as mock_req:
        with pytest.raises(EngineError):
            await client._request("GET", "/slow")
        assert mock_req.call_count == 2


@pytest.mark.asyncio
async def test_base_client_health_check_not_implemented():
    """BaseClient 健康检查未实现"""
    client = BaseClient(engine_name="Test", api_url="http://localhost:8000")
    with pytest.raises(NotImplementedError):
        await client.health_check()


@pytest.mark.asyncio
async def test_base_client_close():
    """BaseClient 关闭连接"""
    client = BaseClient(engine_name="Test", api_url="http://localhost:8000")
    with patch.object(client._client, "aclose", new_callable=AsyncMock):
        await client.close()


@pytest.mark.asyncio
async def test_base_client_context_manager():
    """BaseClient 异步上下文管理器"""
    client = BaseClient(engine_name="Test", api_url="http://localhost:8000")
    with patch.object(client._client, "aclose", new_callable=AsyncMock):
        async with client as c:
            assert c is client
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /config/CozyProjects/CozyMemory && pytest tests/unit/test_base_client.py -v`
Expected: FAIL - ModuleNotFoundError

- [ ] **Step 3: 实现 BaseClient**

`src/cozymemory/clients/__init__.py`:
```python
"""CozyMemory SDK 客户端"""
```

`src/cozymemory/clients/base.py`:
```python
"""BaseClient 基类

提供统一的 httpx AsyncClient 连接池管理、指数退避重试、错误处理和生命周期管理。
"""

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class EngineError(Exception):
    """引擎通信错误"""

    def __init__(self, engine: str, message: str, status_code: int | None = None):
        self.engine = engine
        self.message = message
        self.status_code = status_code
        super().__init__(f"[{engine}] {status_code} - {message}" if status_code else f"[{engine}] {message}")


class BaseClient:
    """
    所有引擎客户端的基类。

    提供统一的：
    - httpx AsyncClient 连接池管理
    - 指数退避重试
    - 错误处理和分类
    - 健康检查
    - 生命周期管理 (async context manager)
    """

    def __init__(
        self,
        engine_name: str,
        api_url: str,
        api_key: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        max_keepalive_connections: int = 50,
        max_connections: int = 100,
        enable_http2: bool = True,
    ):
        self.engine_name = engine_name
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=10.0),
            limits=httpx.Limits(
                max_keepalive_connections=max_keepalive_connections,
                max_connections=max_connections,
            ),
            follow_redirects=True,
            http2=enable_http2,
        )

    def _get_headers(self, content_type: str = "application/json") -> dict[str, str]:
        """获取请求头，子类可覆盖认证方式"""
        headers: dict[str, str] = {"Content-Type": content_type}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: list[tuple] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """
        发送 HTTP 请求，带指数退避重试。

        重试策略：
        - 4xx (除 429): 不重试，立即抛异常
        - 429 (限流): 重试
        - 5xx: 重试
        - 网络错误: 重试
        """
        url = f"{self.api_url}{path}"
        merged_headers = {**self._get_headers(), **(headers or {})}

        # 移除 Content-Type 对 multipart 请求
        if files:
            merged_headers.pop("Content-Type", None)

        last_exception: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = await self._client.request(
                    method=method,
                    url=url,
                    headers=merged_headers,
                    params=params,
                    json=json,
                    data=data,
                    files=files,
                )

                if response.status_code >= 400:
                    # 429 限流 - 重试
                    if response.status_code == 429 and attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (2 ** attempt))
                        continue

                    # 4xx 客户端错误 (除 429) - 不重试
                    if 400 <= response.status_code < 500:
                        raise EngineError(
                            self.engine_name,
                            response.text or f"HTTP {response.status_code}",
                            response.status_code,
                        )

                    # 5xx 服务端错误 - 重试
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (2 ** attempt))
                        continue

                    raise EngineError(
                        self.engine_name,
                        response.text or f"HTTP {response.status_code}",
                        response.status_code,
                    )

                return response

            except EngineError:
                raise

            except httpx.TimeoutException as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    continue

            except httpx.RequestError as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    continue

        if last_exception:
            raise EngineError(
                self.engine_name,
                f"Request failed after {self.max_retries} attempts: {last_exception}",
            )

        raise EngineError(self.engine_name, "Request failed for unknown reason")

    async def health_check(self) -> bool:
        """健康检查，子类必须实现"""
        raise NotImplementedError

    async def close(self) -> None:
        """关闭 HTTP 客户端"""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /config/CozyProjects/CozyMemory && pytest tests/unit/test_base_client.py -v`
Expected: ALL PASSED

- [ ] **Step 5: Commit**

```bash
git add src/cozymemory/clients/ tests/unit/test_base_client.py
git commit -m "feat: add BaseClient with retry logic and EngineError"
```

---

### Task 5: Mem0 客户端

**Files:**
- Create: `src/cozymemory/clients/mem0.py`
- Test: `tests/unit/test_mem0_client.py`

- [ ] **Step 1: 写失败测试**

`tests/unit/test_mem0_client.py`:
```python
"""Mem0 客户端测试"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch

from cozymemory.clients.mem0 import Mem0Client
from cozymemory.clients.base import EngineError
from cozymemory.models.conversation import ConversationMemory


def test_mem0_client_init():
    """Mem0Client 正确初始化"""
    client = Mem0Client(api_url="http://localhost:8888")
    assert client.engine_name == "Mem0"
    assert client.api_url == "http://localhost:8888"


def test_mem0_client_headers():
    """Mem0Client 使用 X-API-Key 认证"""
    client = Mem0Client(api_url="http://localhost:8888", api_key="test-key")
    headers = client._get_headers()
    assert headers.get("X-API-Key") == "test-key"
    assert "Authorization" not in headers


def test_mem0_client_headers_no_key():
    """Mem0Client 无 API Key"""
    client = Mem0Client(api_url="http://localhost:8888")
    headers = client._get_headers()
    assert "X-API-Key" not in headers


@pytest.mark.asyncio
async def test_mem0_health_check_healthy():
    """Mem0Client 健康检查 - 正常"""
    client = Mem0Client(api_url="http://localhost:8888")
    mock_response = httpx.Response(200, json={"status": "ok"})

    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=mock_response):
        result = await client.health_check()
        assert result is True


@pytest.mark.asyncio
async def test_mem0_health_check_unhealthy():
    """Mem0Client 健康检查 - 异常"""
    client = Mem0Client(api_url="http://localhost:8888")
    with patch.object(client._client, "request", new_callable=AsyncMock, side_effect=httpx.ConnectError("refused")):
        result = await client.health_check()
        assert result is False


@pytest.mark.asyncio
async def test_mem0_add():
    """Mem0Client.add 添加对话"""
    client = Mem0Client(api_url="http://localhost:8888")
    mock_response = httpx.Response(
        200,
        json=[{"id": "mem_1", "event": "ADD", "data": {"memory": "用户喜欢咖啡"}}],
    )

    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=mock_response):
        results = await client.add(
            user_id="user_123",
            messages=[{"role": "user", "content": "我喜欢咖啡"}],
        )
        assert len(results) == 1
        assert results[0].content == "用户喜欢咖啡"
        assert results[0].user_id == "user_123"


@pytest.mark.asyncio
async def test_mem0_search():
    """Mem0Client.search 语义搜索"""
    client = Mem0Client(api_url="http://localhost:8888")
    mock_response = httpx.Response(
        200,
        json={"results": [{"id": "mem_1", "user_id": "user_123", "memory": "咖啡", "score": 0.92}]},
    )

    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=mock_response):
        results = await client.search(user_id="user_123", query="咖啡")
        assert len(results) == 1
        assert results[0].score == 0.92


@pytest.mark.asyncio
async def test_mem0_get():
    """Mem0Client.get 获取单条记忆"""
    client = Mem0Client(api_url="http://localhost:8888")
    mock_response = httpx.Response(
        200,
        json={"id": "mem_1", "user_id": "user_123", "memory": "用户喜欢咖啡"},
    )

    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=mock_response):
        result = await client.get("mem_1")
        assert result is not None
        assert result.id == "mem_1"


@pytest.mark.asyncio
async def test_mem0_get_not_found():
    """Mem0Client.get 404 返回 None"""
    client = Mem0Client(api_url="http://localhost:8888")
    mock_response = httpx.Response(404, text="Not Found")

    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=mock_response):
        result = await client.get("nonexistent")
        assert result is None


@pytest.mark.asyncio
async def test_mem0_delete():
    """Mem0Client.delete 删除记忆"""
    client = Mem0Client(api_url="http://localhost:8888")
    mock_response = httpx.Response(200, json={})

    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=mock_response):
        result = await client.delete("mem_1")
        assert result is True


@pytest.mark.asyncio
async def test_mem0_delete_all():
    """Mem0Client.delete_all 删除所有记忆"""
    client = Mem0Client(api_url="http://localhost:8888")
    mock_response = httpx.Response(200, json={})

    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=mock_response):
        result = await client.delete_all("user_123")
        assert result is True
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /config/CozyProjects/CozyMemory && pytest tests/unit/test_mem0_client.py -v`
Expected: FAIL - ModuleNotFoundError

- [ ] **Step 3: 实现 Mem0Client**

`src/cozymemory/clients/mem0.py`:
```python
"""Mem0 引擎客户端

调用自托管 Mem0 REST API。
注意：不使用官方 mem0ai SDK，因为其与自托管服务器不兼容。
"""

from typing import Any

from .base import BaseClient, EngineError
from ..models.conversation import ConversationMemory


class Mem0Client(BaseClient):
    """Mem0 引擎客户端"""

    def __init__(self, api_url: str = "http://localhost:8888", api_key: str | None = None, **kwargs):
        super().__init__(
            engine_name="Mem0",
            api_url=api_url,
            api_key=api_key,
            **kwargs,
        )

    def _get_headers(self, content_type: str = "application/json") -> dict[str, str]:
        """Mem0 自托管使用 X-API-Key 认证"""
        headers: dict[str, str] = {"Content-Type": content_type}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            response = await self._request("GET", "/health")
            return response.status_code == 200
        except Exception:
            return False

    async def add(
        self,
        user_id: str,
        messages: list[dict[str, str]],
        metadata: dict[str, Any] | None = None,
        infer: bool = True,
    ) -> list[ConversationMemory]:
        """添加对话，Mem0 自动提取事实"""
        payload: dict[str, Any] = {
            "messages": messages,
            "user_id": user_id,
            "infer": infer,
        }
        if metadata:
            payload["metadata"] = metadata

        response = await self._request("POST", "/memories", json=payload)
        data = response.json()

        # Mem0 v1.1 返回格式: [{"id": "...", "event": "ADD", "data": {"memory": "..."}}]
        results = []
        for item in data if isinstance(data, list) else [data]:
            memory_text = (
                item.get("data", {}).get("memory", "")
                if isinstance(item.get("data"), dict)
                else item.get("memory", "")
            )
            results.append(
                ConversationMemory(
                    id=item.get("id", ""),
                    user_id=user_id,
                    content=memory_text,
                    metadata=item.get("metadata"),
                )
            )
        return results

    async def search(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        threshold: float | None = None,
    ) -> list[ConversationMemory]:
        """语义搜索会话记忆"""
        payload: dict[str, Any] = {
            "query": query,
            "user_id": user_id,
            "limit": limit,
        }
        if threshold is not None:
            payload["threshold"] = threshold

        response = await self._request("POST", "/search", json=payload)
        data = response.json()

        results = []
        for item in data.get("results", data if isinstance(data, list) else []):
            results.append(
                ConversationMemory(
                    id=item.get("id", ""),
                    user_id=item.get("user_id", user_id),
                    content=item.get("memory", ""),
                    score=item.get("score"),
                    metadata=item.get("metadata"),
                )
            )
        return results

    async def get(self, memory_id: str) -> ConversationMemory | None:
        """获取单条记忆"""
        try:
            response = await self._request("GET", f"/memories/{memory_id}")
            item = response.json()
            return ConversationMemory(
                id=item.get("id", memory_id),
                user_id=item.get("user_id", ""),
                content=item.get("memory", ""),
                metadata=item.get("metadata"),
            )
        except EngineError as e:
            if e.status_code == 404:
                return None
            raise

    async def get_all(self, user_id: str, limit: int = 100) -> list[ConversationMemory]:
        """获取用户所有记忆"""
        response = await self._request(
            "GET",
            "/memories",
            params={"user_id": user_id, "limit": limit},
        )
        data = response.json()

        items = data.get("results", data if isinstance(data, list) else [])
        return [
            ConversationMemory(
                id=item.get("id", ""),
                user_id=item.get("user_id", user_id),
                content=item.get("memory", ""),
                metadata=item.get("metadata"),
            )
            for item in items
        ]

    async def update(self, memory_id: str, content: str) -> ConversationMemory | None:
        """更新记忆内容"""
        response = await self._request(
            "PUT",
            f"/memories/{memory_id}",
            json={"memory": content},
        )
        item = response.json()
        return ConversationMemory(
            id=item.get("id", memory_id),
            user_id=item.get("user_id", ""),
            content=item.get("memory", content),
            metadata=item.get("metadata"),
        )

    async def delete(self, memory_id: str) -> bool:
        """删除单条记忆"""
        try:
            await self._request("DELETE", f"/memories/{memory_id}")
            return True
        except EngineError:
            return False

    async def delete_all(self, user_id: str) -> bool:
        """删除用户所有记忆"""
        try:
            await self._request("DELETE", "/memories", params={"user_id": user_id})
            return True
        except EngineError:
            return False
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /config/CozyProjects/CozyMemory && pytest tests/unit/test_mem0_client.py -v`
Expected: ALL PASSED

- [ ] **Step 5: Commit**

```bash
git add src/cozymemory/clients/mem0.py tests/unit/test_mem0_client.py
git commit -m "feat: add Mem0 client for self-hosted Mem0 REST API"
```

---

### Task 6: Memobase 客户端与 Cognee 客户端

**Files:**
- Create: `src/cozymemory/clients/memobase.py`
- Create: `src/cozymemory/clients/cognee.py`
- Test: `tests/unit/test_memobase_client.py`
- Test: `tests/unit/test_cognee_client.py`

- [ ] **Step 1: 写 Memobase 客户端失败测试**

`tests/unit/test_memobase_client.py`:
```python
"""Memobase 客户端测试"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch

from cozymemory.clients.memobase import MemobaseClient
from cozymemory.clients.base import EngineError


def test_memobase_client_init():
    """MemobaseClient 正确初始化"""
    client = MemobaseClient(api_url="http://localhost:8019")
    assert client.engine_name == "Memobase"
    assert client.api_url == "http://localhost:8019"


def test_memobase_client_headers():
    """MemobaseClient 使用 Bearer Token 认证"""
    client = MemobaseClient(api_url="http://localhost:8019", api_key="my-token")
    headers = client._get_headers()
    assert headers["Authorization"] == "Bearer my-token"


@pytest.mark.asyncio
async def test_memobase_health_check():
    """MemobaseClient 健康检查"""
    client = MemobaseClient(api_url="http://localhost:8019")
    mock_response = httpx.Response(200, json={"status": "ok"})

    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=mock_response):
        result = await client.health_check()
        assert result is True


@pytest.mark.asyncio
async def test_memobase_add_user():
    """MemobaseClient.add_user 创建用户"""
    client = MemobaseClient(api_url="http://localhost:8019")
    mock_response = httpx.Response(200, json={"id": "user_123"})

    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=mock_response):
        user_id = await client.add_user("user_123")
        assert user_id == "user_123"


@pytest.mark.asyncio
async def test_memobase_insert():
    """MemobaseClient.insert 插入对话"""
    client = MemobaseClient(api_url="http://localhost:8019")
    mock_response = httpx.Response(200, json={"blob_id": "blob_123"})

    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=mock_response):
        blob_id = await client.insert(
            user_id="user_123",
            messages=[{"role": "user", "content": "你好"}],
        )
        assert blob_id == "blob_123"


@pytest.mark.asyncio
async def test_memobase_flush():
    """MemobaseClient.flush 触发处理"""
    client = MemobaseClient(api_url="http://localhost:8019")
    mock_response = httpx.Response(200, json={})

    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=mock_response):
        await client.flush("user_123", sync=True)


@pytest.mark.asyncio
async def test_memobase_profile():
    """MemobaseClient.profile 获取画像"""
    client = MemobaseClient(api_url="http://localhost:8019")
    mock_response = httpx.Response(
        200,
        json={
            "basic_info": {
                "name": {"id": "p1", "content": "小明", "created_at": None, "updated_at": None},
            }
        },
    )

    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=mock_response):
        profile = await client.profile("user_123")
        assert profile.user_id == "user_123"
        assert len(profile.topics) == 1
        assert profile.topics[0].topic == "basic_info"
        assert profile.topics[0].sub_topic == "name"
        assert profile.topics[0].content == "小明"


@pytest.mark.asyncio
async def test_memobase_context():
    """MemobaseClient.context 获取上下文"""
    client = MemobaseClient(api_url="http://localhost:8019")
    mock_response = httpx.Response(
        200,
        text="# Memory\n用户背景...",
        headers={"content-type": "text/plain; charset=utf-8"},
    )

    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=mock_response):
        ctx = await client.context("user_123")
        assert ctx.user_id == "user_123"
        assert "用户背景" in ctx.context
```

- [ ] **Step 2: 写 Cognee 客户端失败测试**

`tests/unit/test_cognee_client.py`:
```python
"""Cognee 客户端测试"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch

from cozymemory.clients.cognee import CogneeClient
from cozymemory.clients.base import EngineError


def test_cognee_client_init():
    """CogneeClient 正确初始化"""
    client = CogneeClient(api_url="http://localhost:8000")
    assert client.engine_name == "Cognee"
    assert client.api_url == "http://localhost:8000"


def test_cognee_client_default_timeout():
    """CogneeClient 默认超时为 300s"""
    client = CogneeClient(api_url="http://localhost:8000")
    assert client.timeout == 300.0


@pytest.mark.asyncio
async def test_cognee_health_check():
    """CogneeClient 健康检查"""
    client = CogneeClient(api_url="http://localhost:8000")
    mock_response = httpx.Response(200, json={"status": "ok"})

    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=mock_response):
        result = await client.health_check()
        assert result is True


@pytest.mark.asyncio
async def test_cognee_add():
    """CogneeClient.add 添加数据"""
    client = CogneeClient(api_url="http://localhost:8000")
    mock_response = httpx.Response(200, json={"id": "data_123"})

    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=mock_response):
        result = await client.add(data="文本内容", dataset="my-dataset")
        assert "id" in result


@pytest.mark.asyncio
async def test_cognee_cognify():
    """CogneeClient.cognify 构建知识图谱"""
    client = CogneeClient(api_url="http://localhost:8000")
    mock_response = httpx.Response(200, json={"run_id": "pipe_123", "status": "pending"})

    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=mock_response):
        result = await client.cognify(datasets=["my-dataset"])
        assert result["status"] == "pending"


@pytest.mark.asyncio
async def test_cognee_search():
    """CogneeClient.search 搜索知识库"""
    client = CogneeClient(api_url="http://localhost:8000")
    mock_response = httpx.Response(
        200,
        json=[{"id": "node_1", "text": "Cognee 是知识图谱引擎", "score": 0.95}],
    )

    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=mock_response):
        results = await client.search(query="Cognee 是什么？")
        assert len(results) == 1
        assert results[0].score == 0.95


@pytest.mark.asyncio
async def test_cognee_create_dataset():
    """CogneeClient.create_dataset 创建数据集"""
    client = CogneeClient(api_url="http://localhost:8000")
    mock_response = httpx.Response(
        200,
        json={"id": "550e8400-e29b-41d4-a716-446655440000", "name": "my-dataset"},
    )

    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=mock_response):
        ds = await client.create_dataset("my-dataset")
        assert ds.name == "my-dataset"


@pytest.mark.asyncio
async def test_cognee_list_datasets():
    """CogneeClient.list_datasets 列出数据集"""
    client = CogneeClient(api_url="http://localhost:8000")
    mock_response = httpx.Response(
        200,
        json=[{"id": "uuid-1", "name": "ds1"}, {"id": "uuid-2", "name": "ds2"}],
    )

    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=mock_response):
        datasets = await client.list_datasets()
        assert len(datasets) == 2
```

- [ ] **Step 3: 运行测试确认失败**

Run: `cd /config/CozyProjects/CozyMemory && pytest tests/unit/test_memobase_client.py tests/unit/test_cognee_client.py -v`
Expected: FAIL - ModuleNotFoundError

- [ ] **Step 4: 实现 MemobaseClient**

`src/cozymemory/clients/memobase.py`:
```python
"""Memobase 引擎客户端

调用自托管 Memobase REST API。
核心范式：插入对话 → flush → 获取画像/上下文。
"""

from typing import Any

from .base import BaseClient, EngineError
from ..models.profile import ProfileTopic, UserProfile, ProfileContext


class MemobaseClient(BaseClient):
    """Memobase 引擎客户端"""

    def __init__(
        self, api_url: str = "http://localhost:8019", api_key: str = "secret", **kwargs
    ):
        super().__init__(
            engine_name="Memobase",
            api_url=api_url,
            api_key=api_key,
            **kwargs,
        )

    def _get_headers(self, content_type: str = "application/json") -> dict[str, str]:
        """Memobase 使用 Bearer Token 认证"""
        headers: dict[str, str] = {"Content-Type": content_type}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            response = await self._request("GET", "/healthcheck")
            return response.status_code == 200
        except Exception:
            return False

    # ===== 用户管理 =====

    async def add_user(self, user_id: str | None = None, data: dict | None = None) -> str:
        """创建用户，返回 user_id"""
        payload: dict[str, Any] = {}
        if user_id:
            payload["id"] = user_id
        if data:
            payload["data"] = data

        response = await self._request("POST", "/api/v1/users", json=payload)
        result = response.json()
        return result.get("id", result.get("user_id", ""))

    async def get_user(self, user_id: str) -> dict:
        """获取用户信息"""
        response = await self._request("GET", f"/api/v1/users/{user_id}")
        return response.json()

    async def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        try:
            await self._request("DELETE", f"/api/v1/users/{user_id}")
            return True
        except EngineError:
            return False

    # ===== 数据插入 =====

    async def insert(
        self,
        user_id: str,
        messages: list[dict[str, str]],
        sync: bool = False,
    ) -> str:
        """插入对话数据到 Memobase 缓冲区"""
        payload = {"messages": messages}
        params = {}
        if sync:
            params["wait_process"] = "true"

        response = await self._request(
            "POST",
            f"/api/v1/blobs/insert/{user_id}",
            json=payload,
            params=params,
        )
        result = response.json()
        return result.get("blob_id", result.get("id", ""))

    async def flush(self, user_id: str, sync: bool = False) -> None:
        """触发缓冲区处理"""
        params = {}
        if sync:
            params["wait_process"] = "true"

        await self._request(
            "POST",
            f"/api/v1/users/buffer/{user_id}/chat",
            params=params,
        )

    # ===== 画像 =====

    async def profile(self, user_id: str) -> UserProfile:
        """获取用户结构化画像"""
        response = await self._request(
            "GET",
            f"/api/v1/users/profile/{user_id}",
            params={"need_json": "true"},
        )
        data = response.json()

        topics = []
        if isinstance(data, dict):
            for topic_name, sub_topics in data.items():
                if isinstance(sub_topics, dict):
                    for sub_topic_name, content_data in sub_topics.items():
                        if isinstance(content_data, dict):
                            topics.append(
                                ProfileTopic(
                                    id=content_data.get("id", ""),
                                    topic=topic_name,
                                    sub_topic=sub_topic_name,
                                    content=content_data.get("content", ""),
                                    created_at=content_data.get("created_at"),
                                    updated_at=content_data.get("updated_at"),
                                )
                            )

        return UserProfile(user_id=user_id, topics=topics)

    async def add_profile(
        self, user_id: str, topic: str, sub_topic: str, content: str
    ) -> ProfileTopic:
        """手动添加画像条目"""
        payload = {"topic": topic, "sub_topic": sub_topic, "content": content}
        response = await self._request(
            "POST",
            f"/api/v1/users/profile/{user_id}",
            json=payload,
        )
        result = response.json()
        return ProfileTopic(id=result.get("id", ""), topic=topic, sub_topic=sub_topic, content=content)

    async def delete_profile(self, user_id: str, profile_id: str) -> bool:
        """删除画像条目"""
        try:
            await self._request("DELETE", f"/api/v1/users/profile/{user_id}/{profile_id}")
            return True
        except EngineError:
            return False

    # ===== 上下文 =====

    async def context(
        self,
        user_id: str,
        max_token_size: int = 500,
        chats: list[dict[str, str]] | None = None,
    ) -> ProfileContext:
        """获取上下文提示词（可直接插入 LLM prompt）"""
        params = {"max_token_size": str(max_token_size)}
        json_body = None
        if chats:
            json_body = {"chats": chats}

        response = await self._request(
            "GET",
            f"/api/v1/users/context/{user_id}",
            params=params,
            json=json_body if json_body else None,
        )

        # context 端点返回纯文本或 JSON
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            data = response.json()
            context_text = data.get("context", data.get("result", str(data)))
        else:
            context_text = response.text

        return ProfileContext(user_id=user_id, context=context_text)

    # ===== 事件 =====

    async def events(self, user_id: str, topk: int = 10) -> list[dict]:
        """获取用户事件时间线"""
        response = await self._request(
            "GET",
            f"/api/v1/users/event/{user_id}",
            params={"topk": str(topk)},
        )
        data = response.json()
        return data if isinstance(data, list) else data.get("events", [])
```

- [ ] **Step 5: 实现 CogneeClient**

`src/cozymemory/clients/cognee.py`:
```python
"""Cognee 引擎客户端

从现有 cognee_sdk 迁移简化，保留核心 API。
"""

from typing import Any

from .base import BaseClient, EngineError
from ..models.knowledge import KnowledgeSearchResult, KnowledgeDataset


class CogneeClient(BaseClient):
    """Cognee 引擎客户端"""

    def __init__(
        self, api_url: str = "http://localhost:8000", api_key: str | None = None, **kwargs
    ):
        # cognify 操作需要更长超时
        kwargs.setdefault("timeout", 300.0)
        super().__init__(
            engine_name="Cognee",
            api_url=api_url,
            api_key=api_key,
            **kwargs,
        )

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            response = await self._request("GET", "/health")
            return response.status_code == 200
        except Exception:
            return False

    async def add(self, data: str, dataset: str) -> dict[str, Any]:
        """添加数据到 Cognee"""
        response = await self._request(
            "POST",
            "/api/v1/add",
            data={"datasetName": dataset},
            files=[("data", ("data.txt", data.encode("utf-8"), "text/plain"))],
        )
        return response.json()

    async def cognify(
        self,
        datasets: list[str] | None = None,
        run_in_background: bool = True,
    ) -> dict[str, Any]:
        """触发知识图谱构建"""
        payload: dict[str, Any] = {"run_in_background": run_in_background}
        if datasets:
            payload["datasets"] = datasets

        response = await self._request("POST", "/api/v1/cognify", json=payload)
        return response.json()

    async def search(
        self,
        query: str,
        dataset: str | None = None,
        search_type: str = "GRAPH_COMPLETION",
        top_k: int = 10,
    ) -> list[KnowledgeSearchResult]:
        """搜索知识库"""
        payload: dict[str, Any] = {
            "query": query,
            "search_type": search_type,
            "top_k": top_k,
        }
        if dataset:
            payload["datasets"] = [dataset]

        response = await self._request("POST", "/api/v1/search", json=payload)
        data = response.json()

        results = []
        items = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
        for item in items:
            if isinstance(item, dict):
                results.append(KnowledgeSearchResult(**item))
        return results

    async def list_datasets(self) -> list[KnowledgeDataset]:
        """列出所有数据集"""
        response = await self._request("GET", "/api/v1/datasets")
        data = response.json()
        return [
            KnowledgeDataset(
                id=str(item.get("id", "")),
                name=item.get("name", ""),
                created_at=item.get("createdAt") or item.get("created_at"),
            )
            for item in data
        ]

    async def create_dataset(self, name: str) -> KnowledgeDataset:
        """创建数据集"""
        response = await self._request(
            "POST",
            "/api/v1/datasets",
            json={"name": name},
        )
        data = response.json()
        return KnowledgeDataset(
            id=str(data.get("id", "")),
            name=data.get("name", name),
            created_at=data.get("createdAt") or data.get("created_at"),
        )

    async def delete(self, data_id: str, dataset_id: str) -> bool:
        """删除数据"""
        try:
            await self._request(
                "DELETE",
                "/api/v1/delete",
                params={"data_id": data_id, "dataset_id": dataset_id},
            )
            return True
        except EngineError:
            return False
```

- [ ] **Step 6: 运行测试确认通过**

Run: `cd /config/CozyProjects/CozyMemory && pytest tests/unit/test_memobase_client.py tests/unit/test_cognee_client.py -v`
Expected: ALL PASSED

- [ ] **Step 7: Commit**

```bash
git add src/cozymemory/clients/memobase.py src/cozymemory/clients/cognee.py tests/unit/test_memobase_client.py tests/unit/test_cognee_client.py
git commit -m "feat: add Memobase and Cognee SDK clients"
```

---

### Task 7: 业务服务层

**Files:**
- Create: `src/cozymemory/services/__init__.py`
- Create: `src/cozymemory/services/conversation.py`
- Create: `src/cozymemory/services/profile.py`
- Create: `src/cozymemory/services/knowledge.py`
- Test: `tests/unit/test_conversation_service.py`
- Test: `tests/unit/test_profile_service.py`
- Test: `tests/unit/test_knowledge_service.py`

- [ ] **Step 1: 写会话记忆服务失败测试**

`tests/unit/test_conversation_service.py`:
```python
"""会话记忆服务测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from cozymemory.services.conversation import ConversationService
from cozymemory.models.conversation import ConversationMemory, ConversationMemoryListResponse
from cozymemory.clients.base import EngineError


@pytest.fixture
def mock_mem0_client():
    client = MagicMock()
    client.add = AsyncMock(return_value=[
        ConversationMemory(id="mem_1", user_id="u1", content="事实1"),
    ])
    client.search = AsyncMock(return_value=[
        ConversationMemory(id="mem_1", user_id="u1", content="事实1", score=0.9),
    ])
    client.get = AsyncMock(return_value=ConversationMemory(id="mem_1", user_id="u1", content="事实1"))
    client.get_all = AsyncMock(return_value=[
        ConversationMemory(id="mem_1", user_id="u1", content="事实1"),
    ])
    client.delete = AsyncMock(return_value=True)
    client.delete_all = AsyncMock(return_value=True)
    return client


@pytest.mark.asyncio
async def test_conversation_service_add(mock_mem0_client):
    """ConversationService.add 调用 Mem0 客户端"""
    service = ConversationService(client=mock_mem0_client)
    result = await service.add(
        user_id="u1",
        messages=[{"role": "user", "content": "你好"}],
    )
    assert result.success is True
    assert len(result.data) == 1
    mock_mem0_client.add.assert_called_once()


@pytest.mark.asyncio
async def test_conversation_service_search(mock_mem0_client):
    """ConversationService.search 搜索记忆"""
    service = ConversationService(client=mock_mem0_client)
    result = await service.search(user_id="u1", query="你好")
    assert result.success is True
    assert result.total == 1
    mock_mem0_client.search.assert_called_once()


@pytest.mark.asyncio
async def test_conversation_service_get(mock_mem0_client):
    """ConversationService.get 获取单条记忆"""
    service = ConversationService(client=mock_mem0_client)
    result = await service.get("mem_1")
    assert result is not None
    assert result.id == "mem_1"


@pytest.mark.asyncio
async def test_conversation_service_delete(mock_mem0_client):
    """ConversationService.delete 删除记忆"""
    service = ConversationService(client=mock_mem0_client)
    result = await service.delete("mem_1")
    assert result.success is True
    mock_mem0_client.delete.assert_called_once_with("mem_1")


@pytest.mark.asyncio
async def test_conversation_service_delete_all(mock_mem0_client):
    """ConversationService.delete_all 删除所有记忆"""
    service = ConversationService(client=mock_mem0_client)
    result = await service.delete_all("u1")
    assert result.success is True
    mock_mem0_client.delete_all.assert_called_once_with("u1")


@pytest.mark.asyncio
async def test_conversation_service_add_engine_error(mock_mem0_client):
    """ConversationService.add 引擎错误时抛出 EngineError"""
    mock_mem0_client.add = AsyncMock(side_effect=EngineError("Mem0", "不可用", 503))
    service = ConversationService(client=mock_mem0_client)
    with pytest.raises(EngineError):
        await service.add(user_id="u1", messages=[{"role": "user", "content": "你好"}])
```

- [ ] **Step 2: 写用户画像服务失败测试**

`tests/unit/test_profile_service.py`:
```python
"""用户画像服务测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from cozymemory.services.profile import ProfileService
from cozymemory.models.profile import UserProfile, ProfileTopic, ProfileContext, ProfileInsertResponse
from cozymemory.clients.base import EngineError


@pytest.fixture
def mock_memobase_client():
    client = MagicMock()
    client.insert = AsyncMock(return_value="blob_123")
    client.flush = AsyncMock(return_value=None)
    client.profile = AsyncMock(return_value=UserProfile(
        user_id="u1",
        topics=[ProfileTopic(id="p1", topic="basic_info", sub_topic="name", content="小明")],
    ))
    client.context = AsyncMock(return_value=ProfileContext(user_id="u1", context="# Memory\n..."))
    client.add_profile = AsyncMock(return_value=ProfileTopic(id="p2", topic="interest", sub_topic="hobby", content="游泳"))
    client.delete_profile = AsyncMock(return_value=True)
    return client


@pytest.mark.asyncio
async def test_profile_service_insert(mock_memobase_client):
    """ProfileService.insert 插入对话"""
    service = ProfileService(client=mock_memobase_client)
    result = await service.insert(user_id="u1", messages=[{"role": "user", "content": "你好"}])
    assert result.success is True
    assert result.blob_id == "blob_123"


@pytest.mark.asyncio
async def test_profile_service_flush(mock_memobase_client):
    """ProfileService.flush 触发处理"""
    service = ProfileService(client=mock_memobase_client)
    result = await service.flush("u1")
    assert result.success is True
    mock_memobase_client.flush.assert_called_once()


@pytest.mark.asyncio
async def test_profile_service_get_profile(mock_memobase_client):
    """ProfileService.get_profile 获取画像"""
    service = ProfileService(client=mock_memobase_client)
    result = await service.get_profile("u1")
    assert result.success is True
    assert result.data.user_id == "u1"
    assert len(result.data.topics) == 1


@pytest.mark.asyncio
async def test_profile_service_get_context(mock_memobase_client):
    """ProfileService.get_context 获取上下文"""
    service = ProfileService(client=mock_memobase_client)
    result = await service.get_context("u1")
    assert result.success is True
    assert result.data.user_id == "u1"
```

- [ ] **Step 3: 写知识库服务失败测试**

`tests/unit/test_knowledge_service.py`:
```python
"""知识库服务测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from cozymemory.services.knowledge import KnowledgeService
from cozymemory.models.knowledge import (
    KnowledgeDataset, KnowledgeAddResponse, KnowledgeCognifyResponse,
    KnowledgeSearchResponse, KnowledgeSearchResult, KnowledgeDatasetListResponse,
)
from cozymemory.clients.base import EngineError


@pytest.fixture
def mock_cognee_client():
    client = MagicMock()
    client.add = AsyncMock(return_value={"id": "data_123"})
    client.cognify = AsyncMock(return_value={"run_id": "pipe_123", "status": "pending"})
    client.search = AsyncMock(return_value=[
        KnowledgeSearchResult(id="n1", text="结果1", score=0.9),
    ])
    client.create_dataset = AsyncMock(return_value=KnowledgeDataset(id="uuid-1", name="my-ds"))
    client.list_datasets = AsyncMock(return_value=[
        KnowledgeDataset(id="uuid-1", name="ds1"),
    ])
    return client


@pytest.mark.asyncio
async def test_knowledge_service_add(mock_cognee_client):
    """KnowledgeService.add 添加文档"""
    service = KnowledgeService(client=mock_cognee_client)
    result = await service.add(data="文本", dataset="my-ds")
    assert result.success is True
    mock_cognee_client.add.assert_called_once_with(data="文本", dataset="my-ds")


@pytest.mark.asyncio
async def test_knowledge_service_cognify(mock_cognee_client):
    """KnowledgeService.cognify 构建知识图谱"""
    service = KnowledgeService(client=mock_cognee_client)
    result = await service.cognify(datasets=["my-ds"])
    assert result.success is True
    mock_cognee_client.cognify.assert_called_once()


@pytest.mark.asyncio
async def test_knowledge_service_search(mock_cognee_client):
    """KnowledgeService.search 搜索知识库"""
    service = KnowledgeService(client=mock_cognee_client)
    result = await service.search(query="Cognee 是什么？")
    assert result.success is True
    assert result.total == 1


@pytest.mark.asyncio
async def test_knowledge_service_create_dataset(mock_cognee_client):
    """KnowledgeService.create_dataset 创建数据集"""
    service = KnowledgeService(client=mock_cognee_client)
    result = await service.create_dataset(name="my-ds")
    assert result.success is True
    assert result.data.name == "my-ds"


@pytest.mark.asyncio
async def test_knowledge_service_list_datasets(mock_cognee_client):
    """KnowledgeService.list_datasets 列出数据集"""
    service = KnowledgeService(client=mock_cognee_client)
    result = await service.list_datasets()
    assert result.success is True
    assert len(result.data) == 1
```

- [ ] **Step 4: 运行测试确认失败**

Run: `cd /config/CozyProjects/CozyMemory && pytest tests/unit/test_conversation_service.py tests/unit/test_profile_service.py tests/unit/test_knowledge_service.py -v`
Expected: FAIL - ModuleNotFoundError

- [ ] **Step 5: 实现三个服务**

`src/cozymemory/services/__init__.py`:
```python
"""CozyMemory 业务服务层"""
```

`src/cozymemory/services/conversation.py`:
```python
"""会话记忆服务

薄层封装 Mem0 客户端，负责请求转发和错误转换。
"""

import logging
from typing import Any

from ..clients.mem0 import Mem0Client
from ..clients.base import EngineError
from ..models.conversation import (
    ConversationMemory,
    ConversationMemoryListResponse,
)

logger = logging.getLogger(__name__)


class ConversationService:
    """会话记忆服务"""

    def __init__(self, client: Mem0Client):
        self.client = client

    async def add(
        self,
        user_id: str,
        messages: list[dict[str, str]],
        metadata: dict[str, Any] | None = None,
        infer: bool = True,
    ) -> ConversationMemoryListResponse:
        """添加对话，Mem0 自动提取事实"""
        memories = await self.client.add(
            user_id=user_id,
            messages=messages,
            metadata=metadata,
            infer=infer,
        )
        return ConversationMemoryListResponse(
            success=True,
            data=memories,
            total=len(memories),
            message=f"对话已添加，提取出 {len(memories)} 条记忆",
        )

    async def search(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        threshold: float | None = None,
    ) -> ConversationMemoryListResponse:
        """搜索会话记忆"""
        memories = await self.client.search(
            user_id=user_id,
            query=query,
            limit=limit,
            threshold=threshold,
        )
        return ConversationMemoryListResponse(
            success=True,
            data=memories,
            total=len(memories),
        )

    async def get(self, memory_id: str) -> ConversationMemory | None:
        """获取单条记忆"""
        return await self.client.get(memory_id)

    async def get_all(self, user_id: str, limit: int = 100) -> ConversationMemoryListResponse:
        """获取用户所有记忆"""
        memories = await self.client.get_all(user_id=user_id, limit=limit)
        return ConversationMemoryListResponse(
            success=True,
            data=memories,
            total=len(memories),
        )

    async def delete(self, memory_id: str) -> ConversationMemoryListResponse:
        """删除单条记忆"""
        success = await self.client.delete(memory_id)
        return ConversationMemoryListResponse(
            success=success,
            message="记忆已删除" if success else "删除失败",
        )

    async def delete_all(self, user_id: str) -> ConversationMemoryListResponse:
        """删除用户所有记忆"""
        success = await self.client.delete_all(user_id)
        return ConversationMemoryListResponse(
            success=success,
            message="用户所有记忆已删除" if success else "删除失败",
        )
```

`src/cozymemory/services/profile.py`:
```python
"""用户画像服务

薄层封装 Memobase 客户端，负责请求转发和错误转换。
"""

import logging
from typing import Any

from ..clients.memobase import MemobaseClient
from ..clients.base import EngineError
from ..models.profile import (
    ProfileInsertResponse,
    ProfileTopic,
    UserProfile,
    ProfileContext,
)
from ..models.common import Message

logger = logging.getLogger(__name__)


class _ServiceResponse:
    """通用服务响应包装"""

    @staticmethod
    def success(data: Any = None, message: str = ""):
        return {"success": True, "data": data, "message": message}


class ProfileService:
    """用户画像服务"""

    def __init__(self, client: MemobaseClient):
        self.client = client

    async def insert(
        self,
        user_id: str,
        messages: list[dict[str, str] | Message],
        sync: bool = False,
    ) -> ProfileInsertResponse:
        """插入对话到 Memobase 缓冲区"""
        msg_dicts = [
            {"role": m.role, "content": m.content} if isinstance(m, Message) else m
            for m in messages
        ]
        blob_id = await self.client.insert(user_id=user_id, messages=msg_dicts, sync=sync)
        return ProfileInsertResponse(
            success=True,
            user_id=user_id,
            blob_id=blob_id,
            message="对话已插入缓冲区",
        )

    async def flush(self, user_id: str, sync: bool = False) -> dict:
        """触发缓冲区处理"""
        await self.client.flush(user_id=user_id, sync=sync)
        return {"success": True, "message": "处理完成"}

    async def get_profile(self, user_id: str) -> dict:
        """获取用户结构化画像"""
        profile = await self.client.profile(user_id=user_id)
        return {"success": True, "data": profile, "message": ""}

    async def get_context(
        self,
        user_id: str,
        max_token_size: int = 500,
        chats: list[dict[str, str]] | None = None,
    ) -> dict:
        """获取上下文提示词"""
        ctx = await self.client.context(
            user_id=user_id,
            max_token_size=max_token_size,
            chats=chats,
        )
        return {"success": True, "data": ctx, "message": ""}

    async def add_profile_item(
        self, user_id: str, topic: str, sub_topic: str, content: str
    ) -> dict:
        """手动添加画像条目"""
        result = await self.client.add_profile(
            user_id=user_id, topic=topic, sub_topic=sub_topic, content=content
        )
        return {"success": True, "data": result, "message": ""}

    async def delete_profile_item(self, user_id: str, profile_id: str) -> dict:
        """删除画像条目"""
        success = await self.client.delete_profile(user_id=user_id, profile_id=profile_id)
        return {"success": success, "message": "已删除" if success else "删除失败"}
```

`src/cozymemory/services/knowledge.py`:
```python
"""知识库服务

薄层封装 Cognee 客户端，负责请求转发和错误转换。
"""

import logging
from typing import Any

from ..clients.cognee import CogneeClient
from ..clients.base import EngineError
from ..models.knowledge import (
    KnowledgeAddResponse,
    KnowledgeCognifyResponse,
    KnowledgeSearchResponse,
    KnowledgeDataset,
    KnowledgeDatasetListResponse,
)

logger = logging.getLogger(__name__)


class KnowledgeService:
    """知识库服务"""

    def __init__(self, client: CogneeClient):
        self.client = client

    async def add(self, data: str, dataset: str) -> KnowledgeAddResponse:
        """添加文档到知识库"""
        result = await self.client.add(data=data, dataset=dataset)
        return KnowledgeAddResponse(
            success=True,
            data_id=result.get("id"),
            dataset_name=dataset,
            message="数据已添加",
        )

    async def cognify(
        self,
        datasets: list[str] | None = None,
        run_in_background: bool = True,
    ) -> KnowledgeCognifyResponse:
        """触发知识图谱构建"""
        result = await self.client.cognify(datasets=datasets, run_in_background=run_in_background)
        return KnowledgeCognifyResponse(
            success=True,
            pipeline_run_id=result.get("run_id"),
            status=result.get("status", "pending"),
            message="知识图谱构建已启动",
        )

    async def search(
        self,
        query: str,
        dataset: str | None = None,
        search_type: str = "GRAPH_COMPLETION",
        top_k: int = 10,
    ) -> KnowledgeSearchResponse:
        """搜索知识库"""
        results = await self.client.search(
            query=query, dataset=dataset, search_type=search_type, top_k=top_k
        )
        return KnowledgeSearchResponse(
            success=True,
            data=results,
            total=len(results),
        )

    async def create_dataset(self, name: str) -> KnowledgeDatasetListResponse:
        """创建数据集"""
        ds = await self.client.create_dataset(name=name)
        return KnowledgeDatasetListResponse(
            success=True,
            data=[ds],
            message="数据集已创建",
        )

    async def list_datasets(self) -> KnowledgeDatasetListResponse:
        """列出所有数据集"""
        datasets = await self.client.list_datasets()
        return KnowledgeDatasetListResponse(
            success=True,
            data=datasets,
        )
```

- [ ] **Step 6: 运行测试确认通过**

Run: `cd /config/CozyProjects/CozyMemory && pytest tests/unit/test_conversation_service.py tests/unit/test_profile_service.py tests/unit/test_knowledge_service.py -v`
Expected: ALL PASSED

- [ ] **Step 7: Commit**

```bash
git add src/cozymemory/services/ tests/unit/test_conversation_service.py tests/unit/test_profile_service.py tests/unit/test_knowledge_service.py
git commit -m "feat: add service layer for conversation, profile and knowledge"
```

---

### Task 8: 依赖注入

**Files:**
- Create: `src/cozymemory/api/__init__.py`
- Create: `src/cozymemory/api/deps.py`

- [ ] **Step 1: 实现依赖注入**

`src/cozymemory/api/__init__.py`:
```python
"""CozyMemory REST API"""
```

`src/cozymemory/api/deps.py`:
```python
"""API 依赖注入

提供客户端和服务单例的 FastAPI 依赖注入函数。
"""

from ..config import settings
from ..clients.mem0 import Mem0Client
from ..clients.memobase import MemobaseClient
from ..clients.cognee import CogneeClient
from ..services.conversation import ConversationService
from ..services.profile import ProfileService
from ..services.knowledge import KnowledgeService

# 客户端单例（延迟初始化）
_mem0_client: Mem0Client | None = None
_memobase_client: MemobaseClient | None = None
_cognee_client: CogneeClient | None = None


def get_mem0_client() -> Mem0Client:
    """获取 Mem0 客户端单例"""
    global _mem0_client
    if _mem0_client is None:
        _mem0_client = Mem0Client(
            api_url=settings.MEM0_API_URL,
            api_key=settings.MEM0_API_KEY or None,
            timeout=settings.MEM0_TIMEOUT,
        )
    return _mem0_client


def get_memobase_client() -> MemobaseClient:
    """获取 Memobase 客户端单例"""
    global _memobase_client
    if _memobase_client is None:
        _memobase_client = MemobaseClient(
            api_url=settings.MEMOBASE_API_URL,
            api_key=settings.MEMOBASE_API_KEY,
            timeout=settings.MEMOBASE_TIMEOUT,
        )
    return _memobase_client


def get_cognee_client() -> CogneeClient:
    """获取 Cognee 客户端单例"""
    global _cognee_client
    if _cognee_client is None:
        _cognee_client = CogneeClient(
            api_url=settings.COGNEE_API_URL,
            api_key=settings.COGNEE_API_KEY or None,
            timeout=settings.COGNEE_TIMEOUT,
        )
    return _cognee_client


def get_conversation_service() -> ConversationService:
    """获取会话记忆服务"""
    return ConversationService(client=get_mem0_client())


def get_profile_service() -> ProfileService:
    """获取用户画像服务"""
    return ProfileService(client=get_memobase_client())


def get_knowledge_service() -> KnowledgeService:
    """获取知识库服务"""
    return KnowledgeService(client=get_cognee_client())
```

- [ ] **Step 2: Commit**

```bash
git add src/cozymemory/api/
git commit -m "feat: add API dependency injection for clients and services"
```

---

### Task 9: gRPC Proto 定义与代码生成

**Files:**
- Create: `proto/common.proto`
- Create: `proto/conversation.proto`
- Create: `proto/profile.proto`
- Create: `proto/knowledge.proto`
- Create: `scripts/generate_grpc.sh`
- Create: `src/cozymemory/grpc_server/__init__.py`
- Create: `src/cozymemory/grpc_server/server.py`

- [ ] **Step 1: 创建 Proto 文件**

`proto/common.proto`:
```protobuf
syntax = "proto3";
package cozymemory;

message Empty {}

message HealthRequest {}

message HealthResponse {
  string status = 1;
  map<string, EngineStatus> engines = 2;
  int64 timestamp = 3;
}

message EngineStatus {
  string name = 1;
  string status = 2;
  double latency_ms = 3;
  string error = 4;
}
```

`proto/conversation.proto`:
```protobuf
syntax = "proto3";
package cozymemory;

import "common.proto";

message Message {
  string role = 1;
  string content = 2;
  string created_at = 3;
}

message AddConversationRequest {
  string user_id = 1;
  repeated Message messages = 2;
  map<string, string> metadata = 3;
  bool infer = 4;
}

message ConversationMemory {
  string id = 1;
  string user_id = 2;
  string content = 3;
  optional double score = 4;
  map<string, string> metadata = 5;
  string created_at = 6;
  string updated_at = 7;
}

message AddConversationResponse {
  bool success = 1;
  repeated ConversationMemory data = 2;
  string message = 3;
}

message SearchConversationsRequest {
  string user_id = 1;
  string query = 2;
  int32 limit = 3;
  optional double threshold = 4;
}

message SearchConversationsResponse {
  bool success = 1;
  repeated ConversationMemory data = 2;
  int32 total = 3;
  string message = 4;
}

message GetConversationRequest {
  string memory_id = 1;
}

message DeleteConversationRequest {
  string memory_id = 1;
}

message DeleteAllConversationsRequest {
  string user_id = 1;
}

message DeleteResponse {
  bool success = 1;
  string message = 2;
}

service ConversationService {
  rpc AddConversation(AddConversationRequest) returns (AddConversationResponse);
  rpc SearchConversations(SearchConversationsRequest) returns (SearchConversationsResponse);
  rpc GetConversation(GetConversationRequest) returns (ConversationMemory);
  rpc DeleteConversation(DeleteConversationRequest) returns (DeleteResponse);
  rpc DeleteAllConversations(DeleteAllConversationsRequest) returns (DeleteResponse);
}
```

`proto/profile.proto`:
```protobuf
syntax = "proto3";
package cozymemory;

import "common.proto";

message InsertProfileRequest {
  string user_id = 1;
  repeated Message messages = 2;
  bool sync = 3;
}

message InsertProfileResponse {
  bool success = 1;
  string user_id = 2;
  string blob_id = 3;
  string message = 4;
}

message FlushProfileRequest {
  string user_id = 1;
  bool sync = 2;
}

message FlushProfileResponse {
  bool success = 1;
  string message = 2;
}

message ProfileTopic {
  string id = 1;
  string topic = 2;
  string sub_topic = 3;
  string content = 4;
  string created_at = 5;
  string updated_at = 6;
}

message UserProfile {
  string user_id = 1;
  repeated ProfileTopic topics = 2;
  string updated_at = 3;
}

message GetProfileRequest {
  string user_id = 1;
}

message GetContextRequest {
  string user_id = 1;
  int32 max_token_size = 2;
  repeated Message chats = 3;
}

message GetContextResponse {
  bool success = 1;
  string user_id = 2;
  string context = 3;
}

service ProfileService {
  rpc InsertProfile(InsertProfileRequest) returns (InsertProfileResponse);
  rpc FlushProfile(FlushProfileRequest) returns (FlushProfileResponse);
  rpc GetProfile(GetProfileRequest) returns (UserProfile);
  rpc GetContext(GetContextRequest) returns (GetContextResponse);
}
```

`proto/knowledge.proto`:
```protobuf
syntax = "proto3";
package cozymemory;

import "common.proto";

message AddKnowledgeRequest {
  string data = 1;
  string dataset = 2;
  repeated string node_set = 3;
}

message AddKnowledgeResponse {
  bool success = 1;
  string data_id = 2;
  string dataset_name = 3;
  string message = 4;
}

message CognifyRequest {
  repeated string datasets = 1;
  bool run_in_background = 2;
}

message CognifyResponse {
  bool success = 1;
  string pipeline_run_id = 2;
  string status = 3;
  string message = 4;
}

message SearchKnowledgeRequest {
  string query = 1;
  string dataset = 2;
  string search_type = 3;
  int32 top_k = 4;
}

message KnowledgeSearchResult {
  string id = 1;
  string text = 2;
  optional double score = 3;
  map<string, string> metadata = 4;
}

message SearchKnowledgeResponse {
  bool success = 1;
  repeated KnowledgeSearchResult data = 2;
  int32 total = 3;
  string message = 4;
}

message DatasetInfo {
  string id = 1;
  string name = 2;
  string created_at = 3;
}

message CreateDatasetRequest {
  string name = 1;
}

message ListDatasetsRequest {}

message ListDatasetsResponse {
  bool success = 1;
  repeated DatasetInfo data = 2;
  string message = 3;
}

service KnowledgeService {
  rpc CreateDataset(CreateDatasetRequest) returns (DatasetInfo);
  rpc ListDatasets(ListDatasetsRequest) returns (ListDatasetsResponse);
  rpc AddKnowledge(AddKnowledgeRequest) returns (AddKnowledgeResponse);
  rpc Cognify(CognifyRequest) returns (CognifyResponse);
  rpc SearchKnowledge(SearchKnowledgeRequest) returns (SearchKnowledgeResponse);
}
```

- [ ] **Step 2: 创建 gRPC 代码生成脚本**

`scripts/generate_grpc.sh`:
```bash
#!/bin/bash
# 生成 gRPC Python 代码

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

PROTO_DIR="$PROJECT_ROOT/proto"
OUT_DIR="$PROJECT_ROOT/src/cozymemory/grpc_server"

mkdir -p "$OUT_DIR"

python -m grpc_tools.protoc \
  -I"$PROTO_DIR" \
  --python_out="$OUT_DIR" \
  --grpc_python_out="$OUT_DIR" \
  "$PROTO_DIR/common.proto" \
  "$PROTO_DIR/conversation.proto" \
  "$PROTO_DIR/profile.proto" \
  "$PROTO_DIR/knowledge.proto"

echo "gRPC code generated in $OUT_DIR"
```

- [ ] **Step 3: 创建 gRPC 服务占位**

`src/cozymemory/grpc_server/__init__.py`:
```python
"""CozyMemory gRPC 服务"""
```

`src/cozymemory/grpc_server/server.py`:
```python
"""gRPC 服务器

启动 gRPC 服务，复用 Service 层逻辑。
gRPC 功能在 REST API 完成后再实现。
"""

import asyncio
import logging
from concurrent import futures

import grpc

from ..config import settings

logger = logging.getLogger(__name__)


async def serve_grpc():
    """启动 gRPC 服务器（占位实现）"""
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    # TODO: 注册 gRPC 服务实现
    server.add_insecure_port(f"[::]:{settings.GRPC_PORT}")
    await server.start()
    logger.info(f"gRPC server started on port {settings.GRPC_PORT}")
    await server.wait_for_termination()
```

- [ ] **Step 4: Commit**

```bash
git add proto/ scripts/generate_grpc.sh src/cozymemory/grpc_server/
git commit -m "feat: add gRPC proto definitions and server placeholder"
```

---

### Task 10: FastAPI 应用入口与健康检查

**Files:**
- Create: `src/cozymemory/app.py`
- Create: `src/cozymemory/api/v1/__init__.py`
- Create: `src/cozymemory/api/v1/router.py`
- Create: `src/cozymemory/api/v1/health.py`
- Test: `tests/integration/test_health_api.py`

- [ ] **Step 1: 写健康检查集成测试**

`tests/integration/test_health_api.py`:
```python
"""健康检查集成测试"""

import pytest
from httpx import AsyncClient, ASGITransport

from cozymemory.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """GET /api/v1/health 返回 200"""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "engines" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_openapi_docs(client):
    """GET /docs 返回 200（Swagger UI）"""
    response = await client.get("/docs")
    assert response.status_code == 200
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /config/CozyProjects/CozyMemory && pytest tests/integration/test_health_api.py -v`
Expected: FAIL - ModuleNotFoundError

- [ ] **Step 3: 实现健康检查端点**

`src/cozymemory/api/v1/__init__.py`:
```python
"""CozyMemory API v1"""
```

`src/cozymemory/api/v1/health.py`:
```python
"""健康检查端点"""

import time
import logging

from fastapi import APIRouter

from ...config import settings
from ...models.common import EngineStatus, HealthResponse
from ...api.deps import get_mem0_client, get_memobase_client, get_cognee_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """检查服务及所有引擎的健康状态"""
    engines: dict[str, EngineStatus] = {}

    # 检查 Mem0
    if settings.MEM0_ENABLED:
        try:
            client = get_mem0_client()
            start = time.time()
            healthy = await client.health_check()
            latency = (time.time() - start) * 1000
            engines["mem0"] = EngineStatus(
                name="Mem0",
                status="healthy" if healthy else "unhealthy",
                latency_ms=round(latency, 1),
            )
        except Exception as e:
            engines["mem0"] = EngineStatus(name="Mem0", status="unhealthy", error=str(e))
    else:
        engines["mem0"] = EngineStatus(name="Mem0", status="unhealthy", error="disabled")

    # 检查 Memobase
    if settings.MEMOBASE_ENABLED:
        try:
            client = get_memobase_client()
            start = time.time()
            healthy = await client.health_check()
            latency = (time.time() - start) * 1000
            engines["memobase"] = EngineStatus(
                name="Memobase",
                status="healthy" if healthy else "unhealthy",
                latency_ms=round(latency, 1),
            )
        except Exception as e:
            engines["memobase"] = EngineStatus(name="Memobase", status="unhealthy", error=str(e))
    else:
        engines["memobase"] = EngineStatus(name="Memobase", status="unhealthy", error="disabled")

    # 检查 Cognee
    if settings.COGNEE_ENABLED:
        try:
            client = get_cognee_client()
            start = time.time()
            healthy = await client.health_check()
            latency = (time.time() - start) * 1000
            engines["cognee"] = EngineStatus(
                name="Cognee",
                status="healthy" if healthy else "unhealthy",
                latency_ms=round(latency, 1),
            )
        except Exception as e:
            engines["cognee"] = EngineStatus(name="Cognee", status="unhealthy", error=str(e))
    else:
        engines["cognee"] = EngineStatus(name="Cognee", status="unhealthy", error="disabled")

    # 计算整体状态
    healthy_count = sum(1 for e in engines.values() if e.status == "healthy")
    total_count = len(engines)

    if healthy_count == total_count:
        overall = "healthy"
    elif healthy_count > 0:
        overall = "degraded"
    else:
        overall = "unhealthy"

    return HealthResponse(status=overall, engines=engines)
```

- [ ] **Step 4: 实现路由汇总**

`src/cozymemory/api/v1/router.py`:
```python
"""API v1 路由汇总"""

from fastapi import APIRouter

from .health import router as health_router

router = APIRouter(prefix="/api/v1")
router.include_router(health_router)
```

- [ ] **Step 5: 实现 FastAPI 应用入口**

`src/cozymemory/app.py`:
```python
"""CozyMemory FastAPI 应用入口"""

import time
import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from .config import settings
from .api.v1.router import router as v1_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info(f"CozyMemory starting v{settings.APP_VERSION} env={settings.APP_ENV}")
    yield
    logger.info("CozyMemory shutting down")


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title=settings.APP_NAME,
        description="统一 AI 记忆服务平台 - 整合 Mem0、Memobase、Cognee 三大引擎",
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 请求日志中间件
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = (time.time() - start_time) * 1000
        logger.info(
            f"{request.method} {request.url.path} {response.status_code} {duration:.1f}ms"
        )
        return response

    # 全局异常处理
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": "InternalServerError",
                "detail": str(exc) if settings.DEBUG else "服务器内部错误",
            },
        )

    # 注册路由
    app.include_router(v1_router)

    return app
```

- [ ] **Step 6: 运行测试确认通过**

Run: `cd /config/CozyProjects/CozyMemory && pytest tests/integration/test_health_api.py -v`
Expected: ALL PASSED

- [ ] **Step 7: Commit**

```bash
git add src/cozymemory/app.py src/cozymemory/api/ tests/integration/test_health_api.py
git commit -m "feat: add FastAPI app entry point and health check endpoint"
```

---

### Task 11: REST API 端点实现

**Files:**
- Create: `src/cozymemory/api/v1/conversation.py`
- Create: `src/cozymemory/api/v1/profile.py`
- Create: `src/cozymemory/api/v1/knowledge.py`
- Modify: `src/cozymemory/api/v1/router.py` (添加新路由)
- Test: `tests/integration/test_conversation_api.py`
- Test: `tests/integration/test_profile_api.py`
- Test: `tests/integration/test_knowledge_api.py`

- [ ] **Step 1: 写会话记忆 API 集成测试**

`tests/integration/test_conversation_api.py`:
```python
"""会话记忆 API 集成测试"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from cozymemory.app import create_app
from cozymemory.models.conversation import ConversationMemory, ConversationMemoryListResponse


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_add_conversation(client):
    """POST /api/v1/conversations 添加对话"""
    mock_service = AsyncMock()
    mock_service.add = AsyncMock(return_value=ConversationMemoryListResponse(
        success=True,
        data=[ConversationMemory(id="mem_1", user_id="u1", content="事实1")],
        total=1,
        message="对话已添加，提取出 1 条记忆",
    ))

    with patch("cozymemory.api.v1.conversation.get_conversation_service", return_value=mock_service):
        response = await client.post(
            "/api/v1/conversations",
            json={
                "user_id": "u1",
                "messages": [{"role": "user", "content": "我喜欢咖啡"}],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1


@pytest.mark.asyncio
async def test_search_conversations(client):
    """POST /api/v1/conversations/search 搜索记忆"""
    mock_service = AsyncMock()
    mock_service.search = AsyncMock(return_value=ConversationMemoryListResponse(
        success=True,
        data=[ConversationMemory(id="mem_1", user_id="u1", content="咖啡", score=0.92)],
        total=1,
    ))

    with patch("cozymemory.api.v1.conversation.get_conversation_service", return_value=mock_service):
        response = await client.post(
            "/api/v1/conversations/search",
            json={"user_id": "u1", "query": "咖啡"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1


@pytest.mark.asyncio
async def test_delete_conversation(client):
    """DELETE /api/v1/conversations/{memory_id} 删除记忆"""
    mock_service = AsyncMock()
    mock_service.delete = AsyncMock(return_value=ConversationMemoryListResponse(
        success=True, message="记忆已删除"
    ))

    with patch("cozymemory.api.v1.conversation.get_conversation_service", return_value=mock_service):
        response = await client.delete("/api/v1/conversations/mem_1")
        assert response.status_code == 200
```

- [ ] **Step 2: 写用户画像 API 集成测试**

`tests/integration/test_profile_api.py`:
```python
"""用户画像 API 集成测试"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from cozymemory.app import create_app
from cozymemory.models.profile import UserProfile, ProfileTopic, ProfileContext, ProfileInsertResponse


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_insert_profile(client):
    """POST /api/v1/profiles/insert 插入对话"""
    mock_service = AsyncMock()
    mock_service.insert = AsyncMock(return_value=ProfileInsertResponse(
        success=True, user_id="u1", blob_id="blob_1", message="对话已插入缓冲区"
    ))

    with patch("cozymemory.api.v1.profile.get_profile_service", return_value=mock_service):
        response = await client.post(
            "/api/v1/profiles/insert",
            json={
                "user_id": "u1",
                "messages": [{"role": "user", "content": "我叫小明"}],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


@pytest.mark.asyncio
async def test_get_profile(client):
    """GET /api/v1/profiles/{user_id} 获取画像"""
    mock_service = AsyncMock()
    mock_service.get_profile = AsyncMock(return_value={
        "success": True,
        "data": UserProfile(
            user_id="u1",
            topics=[ProfileTopic(id="p1", topic="basic_info", sub_topic="name", content="小明")],
        ),
    })

    with patch("cozymemory.api.v1.profile.get_profile_service", return_value=mock_service):
        response = await client.get("/api/v1/profiles/u1")
        assert response.status_code == 200
```

- [ ] **Step 3: 写知识库 API 集成测试**

`tests/integration/test_knowledge_api.py`:
```python
"""知识库 API 集成测试"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from cozymemory.app import create_app
from cozymemory.models.knowledge import (
    KnowledgeAddResponse, KnowledgeCognifyResponse,
    KnowledgeSearchResponse, KnowledgeSearchResult,
    KnowledgeDataset, KnowledgeDatasetListResponse,
)


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_add_knowledge(client):
    """POST /api/v1/knowledge/add 添加文档"""
    mock_service = AsyncMock()
    mock_service.add = AsyncMock(return_value=KnowledgeAddResponse(
        success=True, data_id="data_1", dataset_name="my-ds", message="数据已添加"
    ))

    with patch("cozymemory.api.v1.knowledge.get_knowledge_service", return_value=mock_service):
        response = await client.post(
            "/api/v1/knowledge/add",
            json={"data": "文本内容", "dataset": "my-ds"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


@pytest.mark.asyncio
async def test_cognify_knowledge(client):
    """POST /api/v1/knowledge/cognify 构建知识图谱"""
    mock_service = AsyncMock()
    mock_service.cognify = AsyncMock(return_value=KnowledgeCognifyResponse(
        success=True, pipeline_run_id="pipe_1", status="pending", message="知识图谱构建已启动"
    ))

    with patch("cozymemory.api.v1.knowledge.get_knowledge_service", return_value=mock_service):
        response = await client.post(
            "/api/v1/knowledge/cognify",
            json={"datasets": ["my-ds"], "run_in_background": True},
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_search_knowledge(client):
    """POST /api/v1/knowledge/search 搜索知识库"""
    mock_service = AsyncMock()
    mock_service.search = AsyncMock(return_value=KnowledgeSearchResponse(
        success=True,
        data=[KnowledgeSearchResult(id="n1", text="结果", score=0.9)],
        total=1,
    ))

    with patch("cozymemory.api.v1.knowledge.get_knowledge_service", return_value=mock_service):
        response = await client.post(
            "/api/v1/knowledge/search",
            json={"query": "Cognee 是什么？"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
```

- [ ] **Step 4: 运行测试确认失败**

Run: `cd /config/CozyProjects/CozyMemory && pytest tests/integration/test_conversation_api.py tests/integration/test_profile_api.py tests/integration/test_knowledge_api.py -v`
Expected: FAIL - 模块未找到

- [ ] **Step 5: 实现会话记忆 API 端点**

`src/cozymemory/api/v1/conversation.py`:
```python
"""会话记忆 REST API 端点

对应引擎：Mem0
"""

from fastapi import APIRouter, HTTPException, Depends

from ...models.conversation import (
    ConversationMemoryCreate,
    ConversationMemorySearch,
    ConversationMemory,
    ConversationMemoryListResponse,
)
from ...models.common import ErrorResponse
from ...clients.base import EngineError
from ...api.deps import get_conversation_service
from ...services.conversation import ConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post(
    "",
    response_model=ConversationMemoryListResponse,
    responses={502: {"model": ErrorResponse}},
)
async def add_conversation(
    request: ConversationMemoryCreate,
    service: ConversationService = Depends(get_conversation_service),
):
    """添加对话，Mem0 自动提取事实性记忆"""
    try:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        return await service.add(
            user_id=request.user_id,
            messages=messages,
            metadata=request.metadata,
            infer=request.infer,
        )
    except EngineError as e:
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Mem0 引擎错误: {e.message}",
        )


@router.post(
    "/search",
    response_model=ConversationMemoryListResponse,
    responses={502: {"model": ErrorResponse}},
)
async def search_conversations(
    request: ConversationMemorySearch,
    service: ConversationService = Depends(get_conversation_service),
):
    """搜索会话记忆"""
    try:
        return await service.search(
            user_id=request.user_id,
            query=request.query,
            limit=request.limit,
            threshold=request.threshold,
        )
    except EngineError as e:
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Mem0 引擎错误: {e.message}",
        )


@router.get(
    "/{memory_id}",
    response_model=ConversationMemory,
    responses={404: {"model": ErrorResponse}},
)
async def get_conversation(
    memory_id: str,
    service: ConversationService = Depends(get_conversation_service),
):
    """获取单条记忆"""
    try:
        result = await service.get(memory_id)
        if result is None:
            raise HTTPException(status_code=404, detail="记忆不存在")
        return result
    except EngineError as e:
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Mem0 引擎错误: {e.message}",
        )


@router.delete(
    "/{memory_id}",
    response_model=ConversationMemoryListResponse,
)
async def delete_conversation(
    memory_id: str,
    service: ConversationService = Depends(get_conversation_service),
):
    """删除单条记忆"""
    try:
        return await service.delete(memory_id)
    except EngineError as e:
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Mem0 引擎错误: {e.message}",
        )


@router.delete(
    "",
    response_model=ConversationMemoryListResponse,
)
async def delete_all_conversations(
    user_id: str,
    service: ConversationService = Depends(get_conversation_service),
):
    """删除用户所有记忆"""
    try:
        return await service.delete_all(user_id)
    except EngineError as e:
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Mem0 引擎错误: {e.message}",
        )
```

- [ ] **Step 6: 实现用户画像 API 端点**

`src/cozymemory/api/v1/profile.py`:
```python
"""用户画像 REST API 端点

对应引擎：Memobase
"""

from fastapi import APIRouter, HTTPException, Depends

from ...models.profile import (
    ProfileInsertRequest,
    ProfileFlushRequest,
    ProfileContextRequest,
    ProfileInsertResponse,
    UserProfile,
    ProfileContext,
)
from ...models.common import ErrorResponse, Message
from ...clients.base import EngineError
from ...api.deps import get_profile_service
from ...services.profile import ProfileService

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.post(
    "/insert",
    response_model=ProfileInsertResponse,
    responses={502: {"model": ErrorResponse}},
)
async def insert_profile(
    request: ProfileInsertRequest,
    service: ProfileService = Depends(get_profile_service),
):
    """插入对话到 Memobase 缓冲区，自动提取画像"""
    try:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        return await service.insert(
            user_id=request.user_id,
            messages=messages,
            sync=request.sync,
        )
    except EngineError as e:
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Memobase 引擎错误: {e.message}",
        )


@router.post(
    "/flush",
    responses={502: {"model": ErrorResponse}},
)
async def flush_profile(
    request: ProfileFlushRequest,
    service: ProfileService = Depends(get_profile_service),
):
    """触发缓冲区处理"""
    try:
        return await service.flush(user_id=request.user_id, sync=request.sync)
    except EngineError as e:
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Memobase 引擎错误: {e.message}",
        )


@router.get(
    "/{user_id}",
    responses={502: {"model": ErrorResponse}},
)
async def get_profile(
    user_id: str,
    service: ProfileService = Depends(get_profile_service),
):
    """获取用户结构化画像"""
    try:
        return await service.get_profile(user_id)
    except EngineError as e:
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Memobase 引擎错误: {e.message}",
        )


@router.post(
    "/{user_id}/context",
    responses={502: {"model": ErrorResponse}},
)
async def get_context(
    user_id: str,
    request: ProfileContextRequest,
    service: ProfileService = Depends(get_profile_service),
):
    """获取上下文提示词"""
    try:
        chats = None
        if request.chats:
            chats = [{"role": m.role, "content": m.content} for m in request.chats]
        return await service.get_context(
            user_id=user_id,
            max_token_size=request.max_token_size,
            chats=chats,
        )
    except EngineError as e:
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Memobase 引擎错误: {e.message}",
        )
```

- [ ] **Step 7: 实现知识库 API 端点**

`src/cozymemory/api/v1/knowledge.py`:
```python
"""知识库 REST API 端点

对应引擎：Cognee
"""

from fastapi import APIRouter, HTTPException, Depends

from ...models.knowledge import (
    KnowledgeAddRequest,
    KnowledgeCognifyRequest,
    KnowledgeSearchRequest,
    KnowledgeAddResponse,
    KnowledgeCognifyResponse,
    KnowledgeSearchResponse,
    KnowledgeDatasetListResponse,
)
from ...models.common import ErrorResponse
from ...clients.base import EngineError
from ...api.deps import get_knowledge_service
from ...services.knowledge import KnowledgeService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post(
    "/datasets",
    response_model=KnowledgeDatasetListResponse,
    responses={502: {"model": ErrorResponse}},
)
async def create_dataset(
    name: str,
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """创建数据集"""
    try:
        return await service.create_dataset(name=name)
    except EngineError as e:
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Cognee 引擎错误: {e.message}",
        )


@router.get(
    "/datasets",
    response_model=KnowledgeDatasetListResponse,
    responses={502: {"model": ErrorResponse}},
)
async def list_datasets(
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """列出所有数据集"""
    try:
        return await service.list_datasets()
    except EngineError as e:
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Cognee 引擎错误: {e.message}",
        )


@router.post(
    "/add",
    response_model=KnowledgeAddResponse,
    responses={502: {"model": ErrorResponse}},
)
async def add_knowledge(
    request: KnowledgeAddRequest,
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """添加文档到知识库"""
    try:
        return await service.add(data=request.data, dataset=request.dataset)
    except EngineError as e:
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Cognee 引擎错误: {e.message}",
        )


@router.post(
    "/cognify",
    response_model=KnowledgeCognifyResponse,
    responses={502: {"model": ErrorResponse}},
)
async def cognify(
    request: KnowledgeCognifyRequest,
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """触发知识图谱构建"""
    try:
        return await service.cognify(
            datasets=request.datasets,
            run_in_background=request.run_in_background,
        )
    except EngineError as e:
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Cognee 引擎错误: {e.message}",
        )


@router.post(
    "/search",
    response_model=KnowledgeSearchResponse,
    responses={502: {"model": ErrorResponse}},
)
async def search_knowledge(
    request: KnowledgeSearchRequest,
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """搜索知识库"""
    try:
        return await service.search(
            query=request.query,
            dataset=request.dataset,
            search_type=request.search_type,
            top_k=request.top_k,
        )
    except EngineError as e:
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Cognee 引擎错误: {e.message}",
        )
```

- [ ] **Step 8: 更新路由汇总**

修改 `src/cozymemory/api/v1/router.py`，添加三个领域路由：

```python
"""API v1 路由汇总"""

from fastapi import APIRouter

from .health import router as health_router
from .conversation import router as conversation_router
from .profile import router as profile_router
from .knowledge import router as knowledge_router

router = APIRouter(prefix="/api/v1")
router.include_router(health_router)
router.include_router(conversation_router)
router.include_router(profile_router)
router.include_router(knowledge_router)
```

- [ ] **Step 9: 运行所有集成测试确认通过**

Run: `cd /config/CozyProjects/CozyMemory && pytest tests/integration/ -v`
Expected: ALL PASSED

- [ ] **Step 10: Commit**

```bash
git add src/cozymemory/api/v1/ tests/integration/test_conversation_api.py tests/integration/test_profile_api.py tests/integration/test_knowledge_api.py
git commit -m "feat: add REST API endpoints for conversation, profile and knowledge"
```

---

### Task 12: Docker 部署配置

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`

- [ ] **Step 1: 创建 Dockerfile**

`Dockerfile`:
```dockerfile
FROM python:3.11-slim AS base

WORKDIR /app

# 安装系统依赖（gRPC 需要）
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc curl && \
    rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY src/ src/
COPY proto/ proto/

# 生成 gRPC 代码
RUN python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./src/cozymemory/grpc_server \
    --grpc_python_out=./src/cozymemory/grpc_server \
    ./proto/common.proto \
    ./proto/conversation.proto \
    ./proto/profile.proto \
    ./proto/knowledge.proto

EXPOSE 8000 50051

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1

# 默认启动 REST API
CMD ["uvicorn", "cozymemory.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: 创建 docker-compose.yml**

`docker-compose.yml`:
```yaml
version: "3.8"

services:
  cozymemory:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: cozy_memory
    restart: unless-stopped
    ports:
      - "8010:8000"    # REST API
      - "50051:50051"  # gRPC
    environment:
      - APP_ENV=production
      - LOG_LEVEL=INFO
      - MEM0_API_URL=http://mem0-api:8000
      - MEM0_ENABLED=true
      - MEMOBASE_API_URL=http://memobase-server-api:8000
      - MEMOBASE_API_KEY=secret
      - MEMOBASE_ENABLED=true
      - COGNEE_API_URL=http://cognee:8000
      - COGNEE_ENABLED=true
    depends_on:
      - mem0-api
      - memobase-server-api
      - cognee
    networks:
      - 1panel-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # 以下服务假设已在 unified_deployment 中定义
  # 这里仅声明依赖关系
  mem0-api:
    image: mem0/mem0-api:latest
    container_name: mem0_api
    ports:
      - "8888:8000"
    networks:
      - 1panel-network

  memobase-server-api:
    image: memobase/memobase-server-api:latest
    container_name: memobase_server_api
    ports:
      - "8019:8000"
    networks:
      - 1panel-network

  cognee:
    image: cognee/cognee:latest
    container_name: cognee
    ports:
      - "8000:8000"
    networks:
      - 1panel-network

networks:
  1panel-network:
    external: true
```

- [ ] **Step 3: 验证 Dockerfile 可构建**

Run: `cd /config/CozyProjects/CozyMemory && docker build -t cozymemory:2.0 .`
Expected: 构建成功

- [ ] **Step 4: Commit**

```bash
git add Dockerfile docker-compose.yml
git commit -m "feat: add Dockerfile and docker-compose.yml for deployment"
```

---

### Task 13: 全量测试与代码质量

**Files:**
- 无新文件

- [ ] **Step 1: 运行全部单元测试**

Run: `cd /config/CozyProjects/CozyMemory && pytest tests/unit/ -v --tb=short`
Expected: ALL PASSED

- [ ] **Step 2: 运行全部集成测试**

Run: `cd /config/CozyProjects/CozyMemory && pytest tests/integration/ -v --tb=short`
Expected: ALL PASSED

- [ ] **Step 3: 运行测试覆盖率检查**

Run: `cd /config/CozyProjects/CozyMemory && pytest --cov=cozymemory --cov-report=term-missing tests/`
Expected: 覆盖率 > 70%

- [ ] **Step 4: 运行 ruff 代码检查**

Run: `cd /config/CozyProjects/CozyMemory && ruff check src/ tests/`
Expected: 无错误

- [ ] **Step 5: 运行 ruff 格式化检查**

Run: `cd /config/CozyProjects/CozyMemory && ruff format --check src/ tests/`
Expected: 无格式问题

- [ ] **Step 6: Commit（如有修复）**

```bash
git add -A
git commit -m "chore: fix lint and formatting issues"
```

---

## 自检清单

### 1. Spec 覆盖度

| 设计文档要求 | 对应 Task |
|---|---|
| 三引擎独立建模 (common/conversation/profile/knowledge) | Task 3 |
| BaseClient 统一重试/错误/连接池 | Task 4 |
| Mem0Client 自托管 API (X-API-Key 认证) | Task 5 |
| MemobaseClient (insert → flush → profile) | Task 6 |
| CogneeClient (add → cognify → search) | Task 6 |
| 三个 Service 薄层封装 | Task 7 |
| 依赖注入 (deps.py) | Task 8 |
| gRPC Proto 定义 | Task 9 |
| REST API 健康检查 | Task 10 |
| REST API 会话记忆端点 | Task 11 |
| REST API 用户画像端点 | Task 11 |
| REST API 知识库端点 | Task 11 |
| FastAPI 应用入口 + CORS + 日志 + 异常处理 | Task 10 |
| Dockerfile + docker-compose | Task 12 |
| .env.example 环境变量 | Task 1 |
| pyproject.toml + requirements | Task 1 |
| 全量测试 | Task 13 |

### 2. 占位符扫描

✅ 无 TBD/TODO（gRPC server.py 有一个 TODO 标记，这是故意的——gRPC 实现层在 REST 完成后再做）
✅ 所有步骤包含完整代码
✅ 所有测试包含具体断言
✅ 无 "类似 Task N" 的引用

### 3. 类型一致性

✅ `ConversationMemory` — Task 3 定义，Task 5/7/11 使用，字段一致
✅ `EngineError` — Task 4 定义，Task 5/6/7/11 使用
✅ `BaseClient._get_headers()` — Task 4 定义，Task 5 覆盖为 X-API-Key，Task 6 覆盖为 Bearer
✅ `get_conversation_service()` / `get_profile_service()` / `get_knowledge_service()` — Task 8 定义，Task 10/11 使用
✅ Service 方法签名 — Task 7 定义，Task 11 API 端点调用一致
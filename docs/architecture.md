# CozyMemory 架构设计文档

**版本**: 2.0  
**日期**: 2026-04-13  
**状态**: 已批准  
**作者**: 张老师 & AI 架构师

---

## 1. 项目定位

CozyMemory 是一个**薄服务层**，整合 Mem0、Memobase、Cognee 三个记忆引擎，通过统一的数据模型和双协议 API（REST + gRPC）对外提供服务。

**核心原则：简单、直接、不过度设计。**

三引擎职责明确，各司其职：

| 引擎 | 领域 | 核心能力 |
|------|------|---------|
| **Mem0** | 会话记忆 | 添加对话 → 自动提取事实 |
| **Memobase** | 用户画像 | 插入对话 → 自动构建结构化画像 |
| **Cognee** | 知识库 | 添加文档 → 构建知识图谱 → 语义搜索 |

---

## 2. 架构图

```
┌─────────────────────────────────────────────────────────┐
│                   CozyMemory Service                     │
│                                                         │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │   REST API        │  │   gRPC API        │            │
│  │   (FastAPI)       │  │   (grpcio)        │            │
│  │   :8000           │  │   :50051          │            │
│  └────────┬─────────┘  └────────┬──────────┘            │
│           └──────────┬───────────┘                       │
│                      ▼                                   │
│  ┌───────────────────────────────────────────────────┐   │
│  │              Service Layer (薄层)                  │   │
│  │  ConversationService | ProfileService |           │   │
│  │  KnowledgeService                                  │   │
│  └───┬──────────────────┬────────────────────────┘   │   │
│      │                  │                        │      │
│  ┌───▼──────┐  ┌───────▼──────┐  ┌───────────▼──┐  │
│  │Mem0Client│  │MemobaseClient│  │ CogneeClient │  │
│  │(自建SDK) │  │ (自建SDK)    │  │ (自建SDK)    │  │
│  └───┬──────┘  └───────┬──────┘  └───────┬──────┘  │
└──────┼──────────────────┼─────────────────┼──────────┘
       │ HTTP             │ HTTP            │ HTTP
       ▼                  ▼                 ▼
  ┌─────────┐      ┌──────────┐      ┌──────────┐
  │  Mem0   │      │ Memobase  │      │  Cognee  │
  │  :8888  │      │  :8019    │      │  :8000   │
  └─────────┘      └──────────┘      └──────────┘
```

**关键设计决策：**

- **不做路由**：三引擎职责明确，按领域分发，不需要"智能路由"
- **不做融合**：三引擎数据不交叉，不存在"多引擎结果融合"场景
- **不做缓存**：服务层是薄层，缓存由引擎自身负责
- **不做认证**：后期可加中间件层，不影响端点设计

---

## 3. 项目结构

```
CozyMemory/
├── archive/                        # 归档的旧代码（不参与构建）
├── projects/                       # 子项目（CozyCognee SDK 等）
│
├── proto/                          # gRPC proto 定义
│   ├── common.proto
│   ├── conversation.proto
│   ├── profile.proto
│   └── knowledge.proto
│
├── src/
│   └── cozymemory/
│       ├── __init__.py
│       ├── app.py                  # FastAPI 应用入口
│       ├── config.py               # 配置管理 (pydantic-settings)
│       │
│       ├── models/                  # 统一数据模型
│       │   ├── __init__.py
│       │   ├── common.py           # 通用模型 (HealthStatus, ErrorResponse)
│       │   ├── conversation.py     # 会话记忆模型
│       │   ├── profile.py          # 用户画像模型
│       │   └── knowledge.py        # 知识库模型
│       │
│       ├── clients/                 # SDK 客户端
│       │   ├── __init__.py
│       │   ├── base.py             # BaseClient (httpx, 重试, 错误处理)
│       │   ├── mem0.py             # Mem0 客户端
│       │   ├── memobase.py         # Memobase 客户端
│       │   └── cognee.py           # Cognee 客户端 (从现有 SDK 迁移简化)
│       │
│       ├── services/                # 业务服务层
│       │   ├── __init__.py
│       │   ├── conversation.py     # 会话记忆服务
│       │   ├── profile.py           # 用户画像服务
│       │   └── knowledge.py         # 知识库服务
│       │
│       ├── api/                     # REST API
│       │   ├── __init__.py
│       │   ├── deps.py              # 依赖注入
│       │   └── v1/
│       │       ├── __init__.py
│       │       ├── router.py        # 汇总路由
│       │       ├── conversation.py  # /api/v1/conversations/*
│       │       ├── profile.py       # /api/v1/profiles/*
│       │       ├── knowledge.py    # /api/v1/knowledge/*
│       │       └── health.py        # /api/v1/health
│       │
│       └── grpc_server/             # gRPC 服务
│           ├── __init__.py
│           └── server.py
│
├── tests/
│   ├── unit/
│   │   ├── test_clients/
│   │   ├── test_services/
│   │   └── test_models/
│   └── integration/
│       └── test_api/
│
├── docs/                            # 设计文档
│   ├── architecture.md              # 本文档
│   ├── data-models.md               # 数据模型设计
│   ├── sdk-clients.md               # SDK 客户端设计
│   ├── api-reference.md             # API 参考
│   └── deployment.md               # 部署设计
│
├── scripts/
│   └── generate_grpc.sh             # gRPC 代码生成脚本
│
├── pyproject.toml
├── requirements.txt
├── Dockerfile
├── docker-compose.yml               # CozyMemory 自身容器
├── .env.example
└── README.md
```

---

## 4. 技术栈

| 层级 | 技术 | 版本 | 说明 |
|------|------|------|------|
| REST API | FastAPI | 0.110+ | 高性能异步框架 |
| gRPC | grpcio + grpcio-tools | 1.60+ | 高性能 RPC 协议 |
| HTTP 客户端 | httpx[http2] | 0.27+ | 异步 HTTP，支持 HTTP/2 |
| 数据验证 | Pydantic | 2.0+ | 模型验证 |
| 配置管理 | pydantic-settings | 2.0+ | 环境变量配置 |
| 日志 | structlog | 24.0+ | 结构化日志 |
| 测试 | pytest + pytest-asyncio | 8.0+ | 异步测试支持 |
| 代码质量 | ruff + mypy | 最新 | 格式化 + 类型检查 |

---

## 5. 数据流

### 5.1 会话记忆流（Mem0）

```
用户请求 POST /api/v1/conversations
    │
    ▼
ConversationService.add()
    │
    ▼
Mem0Client.add(user_id, messages, infer=True)
    │ HTTP POST /memories
    ▼
Mem0 服务 → LLM 提取事实 → 存储
    │
    ▼
返回 list[ConversationMemory]
```

### 5.2 用户画像流（Memobase）

```
用户请求 POST /api/v1/profiles/insert
    │
    ▼
ProfileService.insert()
    │
    ▼
MemobaseClient.insert(user_id, messages)
    │ HTTP POST /blobs/insert/{user_id}
    ▼
Memobase 服务 → 缓冲区 → LLM 提取画像
    │
    ▼
用户请求 GET /api/v1/profiles/{user_id}
    │
    ▼
ProfileService.get_profile()
    │
    ▼
MemobaseClient.profile(user_id)
    │ HTTP GET /users/profile/{user_id}
    ▼
返回 UserProfile (结构化画像)
```

### 5.3 知识库流（Cognee）

```
用户请求 POST /api/v1/knowledge/add
    │
    ▼
KnowledgeService.add()
    │
    ▼
CogneeClient.add(data, dataset)
    │ HTTP POST /api/v1/add
    ▼
Cognee 服务 → 存储

用户请求 POST /api/v1/knowledge/cognify
    │
    ▼
KnowledgeService.cognify()
    │
    ▼
CogneeClient.cognify(datasets)
    │ HTTP POST /api/v1/cognify
    ▼
Cognee 服务 → 构建知识图谱

用户请求 POST /api/v1/knowledge/search
    │
    ▼
KnowledgeService.search()
    │
    ▼
CogneeClient.search(query, dataset)
    │ HTTP POST /api/v1/search
    ▼
返回 list[KnowledgeSearchResult]
```

---

## 6. 与之前版本的区别

| 方面 | v1（归档） | v2（当前） |
|------|-----------|-----------|
| 架构 | 5 层架构 | 3 层：API → Service → Client |
| 路由 | 智能路由（意图识别 + LLM） | 无路由，按领域直接分发 |
| 融合 | RRF + 加权融合 | 无融合，三引擎数据不交叉 |
| 缓存 | Redis + LRU + 穿透保护 | 无缓存，引擎自身负责 |
| 数据模型 | 单一 Memory 模型 | 三个领域独立模型 |
| 适配器 | 通用 BaseAdapter | 三个专用 Client |
| gRPC | 无 | 有，功能与 REST 对等 |
| 认证 | OAuth2 + API Key | 暂无，后期可加 |
| 依赖 | Redis, PostgreSQL, ChromaDB | 仅 httpx + grpcio |
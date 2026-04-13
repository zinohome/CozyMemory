# CozyMemory 数据模型设计文档

**版本**: 2.0  
**日期**: 2026-04-13  
**状态**: 已批准

---

## 1. 设计原则

- **三个领域独立建模**，不做强行统一
- **每个模型只包含对应引擎实际能提供的字段**
- **请求模型和响应模型分离**
- **使用 Pydantic v2 BaseModel**，支持 OpenAPI 自动生成

---

## 2. 通用模型 (`models/common.py`)

```python
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

---

## 3. 会话记忆模型 (`models/conversation.py`)

> 对应引擎：**Mem0**

### 3.1 请求模型

```python
class ConversationMemoryCreate(BaseModel):
    """添加对话 → Mem0 自动提取事实
    
    Mem0 的核心流程：
    1. 传入对话消息列表
    2. Mem0 使用 LLM 自动提取事实性记忆
    3. 返回提取出的记忆列表
    """
    user_id: str = Field(..., description="用户 ID", min_length=1)
    messages: list[Message] = Field(
        ..., description="对话消息列表", min_length=1
    )
    metadata: dict[str, Any] | None = Field(
        None, description="元数据 (source, session_id 等)"
    )
    infer: bool = Field(
        True, description="是否使用 LLM 提取事实。False 则原样存储"
    )

class ConversationMemorySearch(BaseModel):
    """搜索会话记忆"""
    user_id: str = Field(..., description="用户 ID", min_length=1)
    query: str = Field(..., description="搜索查询文本", min_length=1)
    limit: int = Field(10, ge=1, le=100, description="返回数量限制")
    threshold: float | None = Field(
        None, ge=0, le=1, description="最低相似度阈值"
    )
```

### 3.2 响应模型

```python
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

### 3.3 Mem0 API 映射

| 统一模型字段 | Mem0 API 响应字段 | 说明 |
|-------------|-----------------|------|
| `id` | `id` | 记忆唯一标识 |
| `user_id` | `user_id` | 用户标识 |
| `content` | `memory` (v1.1) 或 `data.memory` | 提取出的事实 |
| `score` | `score` | 搜索相似度 |
| `metadata` | `metadata` | 附加信息 |
| `created_at` | `created_at` | 创建时间 |
| `updated_at` | `updated_at` | 更新时间 |

---

## 4. 用户画像模型 (`models/profile.py`)

> 对应引擎：**Memobase**

### 4.1 核心认知

Memobase 不是 CRUD 记忆系统，它的核心范式是：

```
插入对话 (insert) → 缓冲区 (buffer) → LLM 处理 (flush) → 生成画像 (profile)
```

画像由系统自动从对话中提取，不能直接 CRUD。但可以手动增删改画像条目。

### 4.2 请求模型

```python
class ProfileInsertRequest(BaseModel):
    """插入对话 → Memobase 自动提取画像
    
    流程：
    1. 调用 insert 传入对话消息
    2. 消息进入缓冲区
    3. 调用 flush 触发处理（或等待自动处理）
    4. 调用 profile 获取结构化画像
    """
    user_id: str = Field(..., description="用户 ID", min_length=1)
    messages: list[Message] = Field(
        ..., description="对话消息列表", min_length=1
    )
    sync: bool = Field(
        False, description="是否同步等待处理完成"
    )

class ProfileFlushRequest(BaseModel):
    """触发缓冲区处理"""
    user_id: str = Field(..., description="用户 ID", min_length=1)
    sync: bool = Field(
        False, description="是否同步等待处理完成"
    )

class ProfileContextRequest(BaseModel):
    """获取上下文提示词
    
    返回可直接插入 LLM prompt 的文本，包含用户画像和近期事件。
    """
    user_id: str = Field(..., description="用户 ID", min_length=1)
    max_token_size: int = Field(
        500, ge=100, le=4000, description="上下文最大 token 数"
    )
    chats: list[Message] | None = Field(
        None, description="近期对话（用于语义搜索匹配）"
    )
```

### 4.3 响应模型

```python
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
    topics: list[ProfileTopic] = Field(
        default_factory=list, description="画像主题列表"
    )
    updated_at: datetime | None = Field(None)

class ProfileContext(BaseModel):
    """上下文提示词结果"""
    user_id: str = Field(..., description="用户 ID")
    context: str = Field(
        ..., description="可直接插入 LLM prompt 的文本"
    )

class ProfileInsertResponse(BaseModel):
    """插入响应"""
    success: bool = True
    user_id: str
    blob_id: str | None = Field(None, description="Blob ID")
    message: str = ""
```

### 4.4 Memobase API 映射

| 统一操作 | Memobase API | 说明 |
|---------|-------------|------|
| 创建用户 | `POST /users` | 首次使用需创建用户 |
| 插入对话 | `POST /blobs/insert/{user_id}` | ChatBlob 格式 |
| 触发处理 | `POST /users/buffer/{user_id}/chat` | flush 操作 |
| 获取画像 | `GET /users/profile/{user_id}` | 结构化画像 |
| 获取上下文 | `GET /users/context/{user_id}` | 上下文提示词 |
| 添加画像条目 | `POST /users/profile/{user_id}` | 手动添加 |
| 删除画像条目 | `DELETE /users/profile/{user_id}/{id}` | 手动删除 |
| 获取事件 | `GET /users/event/{user_id}` | 时间线事件 |

---

## 5. 知识库模型 (`models/knowledge.py`)

> 对应引擎：**Cognee**

### 5.1 核心认知

Cognee 的核心流程是：

```
添加文档 (add) → 构建知识图谱 (cognify) → 语义搜索 (search)
```

这是一个异步管道：添加文档后需要显式触发 cognify 才能搜索。

### 5.2 请求模型

```python
class KnowledgeAddRequest(BaseModel):
    """添加文档到知识库"""
    data: str = Field(
        ..., description="文本内容或文件路径", min_length=1
    )
    dataset: str = Field(
        ..., description="数据集名称", min_length=1
    )
    node_set: list[str] | None = Field(
        None, description="节点集标识"
    )

class KnowledgeCognifyRequest(BaseModel):
    """触发知识图谱构建
    
    Cognee 是异步管道，add 之后需要 cognify 才能搜索。
    """
    datasets: list[str] | None = Field(
        None, description="要处理的数据集列表"
    )
    run_in_background: bool = Field(
        True, description="是否后台运行"
    )

class KnowledgeSearchRequest(BaseModel):
    """知识库搜索"""
    query: str = Field(..., description="搜索查询", min_length=1)
    dataset: str | None = Field(None, description="限定数据集")
    search_type: str = Field(
        "GRAPH_COMPLETION",
        description="搜索类型: GRAPH_COMPLETION, SUMMARIES, CHUNKS, RAG_COMPLETION"
    )
    top_k: int = Field(10, ge=1, le=100, description="返回数量限制")
```

### 5.3 响应模型

```python
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

### 5.4 Cognee API 映射

| 统一操作 | Cognee API | 说明 |
|---------|-----------|------|
| 添加文档 | `POST /api/v1/add` | multipart/form-data |
| 构建图谱 | `POST /api/v1/cognify` | 异步管道 |
| 搜索 | `POST /api/v1/search` | 多种搜索类型 |
| 创建数据集 | `POST /api/v1/datasets` | — |
| 列出数据集 | `GET /api/v1/datasets` | — |
| 删除数据 | `DELETE /api/v1/delete` | — |
| 健康检查 | `GET /health` | — |

---

## 6. 模型之间的关系

```
┌─────────────────────────────────────────────────────────────┐
│                    CozyMemory 统一模型层                      │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────┐ │
│  │ ConversationMemory│  │ UserProfile       │  │ Knowledge │ │
│  │                  │  │                   │  │           │ │
│  │ - id             │  │ - user_id         │  │ - dataset │ │
│  │ - user_id        │  │ - topics[]        │  │ - add()   │ │
│  │ - content (事实) │  │   - topic         │  │ - cognify │ │
│  │ - score          │  │   - sub_topic     │  │ - search  │ │
│  │                  │  │   - content        │  │           │ │
│  └───────┬──────────┘  └────────┬──────────┘  └─────┬─────┘ │
│          │                      │                    │       │
│          ▼                      ▼                    ▼       │
│  ┌───────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │  Mem0Client   │  │ MemobaseClient    │  │ CogneeClient │ │
│  └───────────────┘  └──────────────────┘  └───────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

三个领域通过 `user_id` 关联，但数据完全独立，不存在跨引擎的合并或融合。
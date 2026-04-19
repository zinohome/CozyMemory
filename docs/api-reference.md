# CozyMemory API Reference

**版本**：v1  
**协议**：REST (HTTP/JSON) + gRPC  
**REST 基础地址**：`http://<host>:8000/api/v1`  
**gRPC 地址**：`<host>:50051`（明文 TCP，无 TLS）  
**交互式文档**：`http://<host>:8000/docs`（Swagger UI）、`http://<host>:8000/redoc`

---

## 概述

CozyMemory 是统一 AI 记忆服务平台，整合三个专用引擎：

| 引擎 | 域 | 用途 |
|------|-----|------|
| **Mem0** | `conversations` | 对话事实提取与语义搜索 |
| **Memobase** | `profiles` | 用户结构化画像（须 UUID v4 user_id） |
| **Cognee** | `knowledge` | 知识图谱构建与推理检索 |

三引擎可独立调用，也可通过**统一上下文接口**（`/context` / `ContextService`）一次并发获取全部结果。

---

## 通用约定

### 认证

当前版本无需调用方传认证头（内网部署场景）。引擎密钥由服务端环境变量配置，调用方无需关心。

### 响应结构

所有成功响应遵循统一格式：

```json
{
  "success": true,
  "data": { ... },
  "message": ""
}
```

### 错误响应

```json
{
  "success": false,
  "error": "Mem0Error",
  "detail": "upstream timeout after 3 retries",
  "engine": "Mem0"
}
```

| HTTP 状态码 | 含义 |
|------------|------|
| `400` | 请求参数业务层错误（如非 UUID user_id 传给 Memobase） |
| `404` | 资源不存在 |
| `422` | 请求体校验失败（缺少必填字段、类型错误等） |
| `502` | 后端引擎服务不可达或返回 5xx |

### 消息对象（Message）

对话消息在 REST 和 gRPC 中均使用相同结构：

```json
{
  "role": "user",         // user / assistant / system
  "content": "消息内容",
  "created_at": null      // ISO 8601，可选
}
```

---

## REST API

### 健康检查

#### `GET /health`

检查 CozyMemory 本身及三个后端引擎的存活状态。

**响应示例**

```json
{
  "status": "healthy",
  "engines": {
    "mem0":     {"name": "Mem0",     "status": "healthy", "latency_ms": 42.5,   "error": null},
    "memobase": {"name": "Memobase", "status": "healthy", "latency_ms": 18.2,   "error": null},
    "cognee":   {"name": "Cognee",   "status": "healthy", "latency_ms": 1240.0, "error": null}
  },
  "timestamp": "2026-04-19T10:00:00Z"
}
```

`status` 三档：`healthy`（全部正常）/ `degraded`（部分异常）/ `unhealthy`（全部异常）。  
Cognee 健康检查调用图数据库，延迟 1~4s 属正常现象。

```bash
curl http://localhost:8000/api/v1/health
```

---

### 对话记忆（Conversations）

底层引擎：**Mem0**。存储经 LLM 提取的事实性记忆，而非原始对话内容。

#### `POST /conversations` — 添加对话并提取记忆

**请求体**

```json
{
  "user_id": "user_01",
  "messages": [
    {"role": "user",      "content": "我最近开始学打篮球，感觉很有趣"},
    {"role": "assistant", "content": "太棒了！篮球是很好的运动"}
  ],
  "metadata": {"source": "web"},
  "infer": true,
  "agent_id": "sales-bot",
  "session_id": "sess_abc123"
}
```

| 字段 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `user_id` | string | 是 | — | 用户 ID，任意字符串 |
| `messages` | Message[] | 是 | — | 至少 1 条 |
| `metadata` | object | 否 | null | 随记忆存储的自定义元数据 |
| `infer` | bool | 否 | `true` | `true`：LLM 提取事实；`false`：原样存储 |
| `agent_id` | string | 否 | null | 智能体 ID，按 agent 隔离记忆视角（不同 agent 只看自己的记忆） |
| `session_id` | string | 否 | null | 会话 ID，映射为 Mem0 `run_id`，实现短期记忆隔离 |

**响应**

```json
{
  "success": true,
  "data": [
    {
      "id": "mem_abc123",
      "user_id": "user_01",
      "content": "用户喜欢篮球运动",
      "score": null,
      "metadata": {"source": "web"},
      "created_at": "2026-04-19T10:00:00Z",
      "updated_at": "2026-04-19T10:00:00Z"
    }
  ],
  "total": 1,
  "message": ""
}
```

```bash
curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user_01","messages":[{"role":"user","content":"我喜欢打篮球"}],"infer":true}'
```

---

#### `GET /conversations` — 列出用户所有记忆

**查询参数**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `user_id` | string | 是 | — | |
| `limit` | int | 否 | 100 | 最大返回数量 |

```bash
curl "http://localhost:8000/api/v1/conversations?user_id=user_01&limit=20"
```

---

#### `POST /conversations/search` — 语义搜索记忆

**请求体**

```json
{
  "user_id": "user_01",
  "query": "用户喜欢什么运动",
  "limit": 5,
  "threshold": 0.7,
  "agent_id": "sales-bot",
  "session_id": "sess_abc123",
  "memory_scope": "long"
}
```

| 字段 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `user_id` | string | 是 | — | |
| `query` | string | 是 | — | 自然语言查询文本 |
| `limit` | int | 否 | 10 | 返回数量，1~100 |
| `threshold` | float | 否 | null | 最低相似度，0~1，null 不过滤 |
| `agent_id` | string | 否 | null | 限定 agent 视角 |
| `session_id` | string | 否 | null | 限定 session（`memory_scope=short/both` 时生效） |
| `memory_scope` | enum | 否 | `long` | `short`：会话级记忆；`long`：跨会话长期记忆；`both`：两者都搜索 |

每条结果的 `score` 字段反映语义相关度（越高越相关）。

```bash
curl -X POST http://localhost:8000/api/v1/conversations/search \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user_01","query":"用户喜欢什么运动","limit":5}'
```

---

#### `GET /conversations/{memory_id}` — 获取单条记忆

记忆不存在返回 `404`。

```bash
curl http://localhost:8000/api/v1/conversations/mem_abc123
```

---

#### `DELETE /conversations/{memory_id}` — 删除单条记忆

```bash
curl -X DELETE http://localhost:8000/api/v1/conversations/mem_abc123
```

---

#### `DELETE /conversations` — 删除用户所有记忆

**查询参数**：`user_id`（必填）

```bash
curl -X DELETE "http://localhost:8000/api/v1/conversations?user_id=user_01"
```

---

### 用户画像（Profiles）

底层引擎：**Memobase**。

> **user_id 透明映射**：CozyMemory 通过 Redis 自动将任意字符串 `user_id` 映射为 Memobase 所需的 UUID v4，调用方无需自己生成 UUID。  
> 若需查看或管理映射关系，参见下方的 [用户 ID 映射（Users）](#用户-id-映射users) 章节。

**工作流程**

```
insert（写入缓冲区）→ 自动/手动 flush（LLM 提取）→ GET /{user_id}（读取画像）
```

#### `POST /profiles/insert` — 插入对话到缓冲区

**请求体**

```json
{
  "user_id": "user_01",
  "messages": [
    {"role": "user",      "content": "我叫小明，今年 28 岁，住在北京"},
    {"role": "assistant", "content": "好的，我已记录您的基本信息"}
  ],
  "sync": false
}
```

| 字段 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `user_id` | string | 是 | — | 任意字符串，内部自动映射为 UUID v4；用户不存在时自动创建 |
| `messages` | Message[] | 是 | — | |
| `sync` | bool | 否 | `false` | `true`：同步等待 LLM 处理完成后返回 |

**响应**

```json
{
  "success": true,
  "user_id": "user_01",
  "blob_id": "blob_xyz789",
  "message": "对话已插入缓冲区"
}
```

```bash
curl -X POST http://localhost:8000/api/v1/profiles/insert \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user_01","messages":[{"role":"user","content":"我叫小明，喜欢游泳"}],"sync":true}'
```

---

#### `POST /profiles/flush` — 触发缓冲区处理

手动触发 LLM 处理缓冲区对话（配合 `sync=false` 的批量插入使用）。

**请求体**

```json
{"user_id": "user_01", "sync": true}
```

---

#### `GET /profiles/{user_id}` — 获取用户结构化画像

**响应示例**

```json
{
  "success": true,
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "topics": [
      {
        "id": "profile_001",
        "topic": "basic_info",
        "sub_topic": "name",
        "content": "用户名叫小明",
        "created_at": "2026-04-19T10:00:00Z",
        "updated_at": "2026-04-19T10:00:00Z"
      },
      {
        "id": "profile_002",
        "topic": "interest",
        "sub_topic": "sport",
        "content": "喜欢游泳",
        "created_at": "2026-04-19T10:00:00Z",
        "updated_at": "2026-04-19T10:00:00Z"
      }
    ],
    "updated_at": null
  },
  "message": ""
}
```

```bash
curl http://localhost:8000/api/v1/profiles/user_01
```

---

#### `POST /profiles/{user_id}/context` — 获取 LLM 上下文提示词

将用户画像格式化为可直接插入 system prompt 的文本。

**请求体**

```json
{"max_token_size": 500, "chats": null}
```

| 字段 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `max_token_size` | int | 否 | 500 | 上下文最大 token 数，100~4000 |
| `chats` | Message[] | 否 | null | 当前对话（预留字段，待 Memobase 后续版本支持） |

**响应**

```json
{
  "success": true,
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "context": "## User Profile\n- Name: 小明\n- Interests: Swimming\n..."
  },
  "message": ""
}
```

```bash
curl -X POST \
  http://localhost:8000/api/v1/profiles/user_01/context \
  -H "Content-Type: application/json" \
  -d '{"max_token_size":500}'
```

---

#### `POST /profiles/{user_id}/items` — 手动添加画像条目

绕过对话提取，直接写入一条结构化画像数据。

> 用户必须已通过 `POST /profiles/insert` 在 Memobase 中创建，否则返回 502（外键约束）。

**请求体**

```json
{
  "topic": "interest",
  "sub_topic": "sport",
  "content": "喜欢游泳和跑步，每周运动 3 次"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `topic` | string | 是 | 主题（如 `basic_info`、`interest`、`preference`） |
| `sub_topic` | string | 是 | 子主题（如 `name`、`sport`、`food`） |
| `content` | string | 是 | 内容描述 |

**响应**

```json
{
  "success": true,
  "data": {
    "id": "profile_003",
    "topic": "interest",
    "sub_topic": "sport",
    "content": "喜欢游泳和跑步，每周运动 3 次",
    "created_at": "2026-04-19T10:00:00Z",
    "updated_at": "2026-04-19T10:00:00Z"
  },
  "message": ""
}
```

```bash
curl -X POST \
  http://localhost:8000/api/v1/profiles/user_01/items \
  -H "Content-Type: application/json" \
  -d '{"topic":"interest","sub_topic":"sport","content":"喜欢游泳"}'
```

---

#### `DELETE /profiles/{user_id}/items/{profile_id}` — 删除画像条目

```bash
curl -X DELETE \
  http://localhost:8000/api/v1/profiles/user_01/items/profile_003
```

**响应**：`{"success": true, "message": ""}`

---

### 用户 ID 映射（Users）

管理 `user_id` ↔ UUID v4 的双向映射关系（由 Redis 维护）。  
通常无需手动调用——所有画像接口自动完成映射。以下接口供调试、跨系统 ID 对齐或清理使用。

#### `GET /users/{user_id}/uuid` — 获取或创建映射

返回该 `user_id` 对应的 UUID；若不存在则自动创建。

```bash
curl http://localhost:8000/api/v1/users/user_01/uuid
```

**响应**

```json
{"success": true, "user_id": "user_01", "uuid": "550e8400-e29b-41d4-a716-446655440000"}
```

---

#### `GET /users/{user_id}/uuid/lookup` — 仅查询映射（不自动创建）

映射不存在时返回 `404`，而非自动生成新 UUID。

```bash
curl http://localhost:8000/api/v1/users/user_01/uuid/lookup
```

---

#### `DELETE /users/{user_id}/uuid` — 删除映射记录

删除 Redis 中的映射记录（不影响 Memobase 实际数据）。  
> 删除后下次调用画像接口将生成新 UUID，相当于切换到新的 Memobase 用户。  
> 若需彻底清除数据，请先调用 `DELETE /profiles/{user_id}/items/*` 清空画像。

```bash
curl -X DELETE http://localhost:8000/api/v1/users/user_01/uuid
```

**响应**：`{"success": true, "message": "映射已删除"}`

---

### 知识库（Knowledge）

底层引擎：**Cognee**。

**工作流程**

```
add（写入文档）→ cognify（构建知识图谱，异步）→ search（推理检索）
```

#### `POST /knowledge/add` — 添加文档到知识库

**请求体**

```json
{
  "data": "CozyMemory 是统一 AI 记忆平台，整合了 Mem0、Memobase 和 Cognee 三大引擎",
  "dataset": "default"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `data` | string | 是 | 文本内容 |
| `dataset` | string | 是 | 目标数据集名称，不存在时自动创建 |
| `node_set` | string[] | 否 | 节点集标识（高级用法） |

**响应**

```json
{
  "success": true,
  "data_id": "data_abc123",
  "dataset_name": "default",
  "message": ""
}
```

**保存 `data_id`**，删除文档时需要用到。

```bash
curl -X POST http://localhost:8000/api/v1/knowledge/add \
  -H "Content-Type: application/json" \
  -d '{"data":"CozyMemory 整合三大 AI 记忆引擎","dataset":"my-dataset"}'
```

---

#### `POST /knowledge/cognify` — 构建知识图谱

对已添加的文档执行实体提取、关系建模，生成图谱结构。**耗时 30~120s，强烈建议后台运行**。

**请求体**

```json
{"datasets": ["default"], "run_in_background": true}
```

| 字段 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `datasets` | string[] | 否 | null | 指定数据集，null 处理全部 |
| `run_in_background` | bool | 否 | `true` | 推荐 `true` |

**响应**

```json
{
  "success": true,
  "pipeline_run_id": "run_xyz456",
  "status": "pending",
  "message": ""
}
```

> cognify 完成前调用 search 返回空结果，这是正常现象，轮询等待即可。

---

#### `POST /knowledge/search` — 搜索知识库

**请求体**

```json
{
  "query": "AI 记忆服务有哪些核心能力",
  "dataset": "default",
  "search_type": "GRAPH_COMPLETION",
  "top_k": 5
}
```

| 字段 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `query` | string | 是 | — | 查询文本（非空） |
| `dataset` | string | 否 | null | 限定数据集，null 搜索全部 |
| `search_type` | enum | 否 | `GRAPH_COMPLETION` | 见下表 |
| `top_k` | int | 否 | 10 | 返回数量，1~100 |

**search_type 选项**

| 值 | 说明 | 适用场景 |
|----|------|----------|
| `CHUNKS` | 原文片段，速度最快 | 快速检索、调试 |
| `SUMMARIES` | 摘要段落 | 长文概览 |
| `RAG_COMPLETION` | RAG 生成，融合原文 | 问答 |
| `GRAPH_COMPLETION` | 图谱推理，关联性最强 | **推荐**，深度推理 |

**响应**

```json
{
  "success": true,
  "data": [
    {
      "id": "chunk_001",
      "text": "CozyMemory 整合了 Mem0、Memobase 和 Cognee 三大引擎...",
      "score": 0.92,
      "metadata": {}
    }
  ],
  "total": 1,
  "message": ""
}
```

---

#### `GET /knowledge/datasets` — 列出所有数据集

```bash
curl http://localhost:8000/api/v1/knowledge/datasets
```

**响应**

```json
{
  "success": true,
  "data": [
    {"id": "ds_uuid_001", "name": "default", "created_at": "2026-04-19T10:00:00Z"}
  ],
  "message": ""
}
```

---

#### `POST /knowledge/datasets?name=` — 创建数据集

```bash
curl -X POST "http://localhost:8000/api/v1/knowledge/datasets?name=my-new-dataset"
```

---

#### `DELETE /knowledge` — 删除知识数据

先通过 `GET /knowledge/datasets` 获取 `dataset_id`，再结合 add 时返回的 `data_id` 执行删除。

**请求体**

```json
{"data_id": "data_abc123", "dataset_id": "ds_uuid_001"}
```

```bash
curl -X DELETE http://localhost:8000/api/v1/knowledge \
  -H "Content-Type: application/json" \
  -d '{"data_id":"data_abc123","dataset_id":"ds_uuid_001"}'
```

---

### 统一上下文（Context）

一次请求并发调用三引擎。**总延迟 = 最慢引擎延迟**，而非三者之和。某引擎失败不影响其他引擎结果。

#### `POST /context` — 并发获取三类记忆

**请求体**

```json
{
  "user_id": "user_01",
  "query": "用户最近关心什么话题",
  "include_conversations": true,
  "include_profile": true,
  "include_knowledge": true,
  "conversation_limit": 5,
  "max_token_size": 500,
  "knowledge_top_k": 3,
  "knowledge_search_type": "GRAPH_COMPLETION",
  "engine_timeout": 5.0,
  "chats": null,
  "agent_id": "sales-bot",
  "session_id": "sess_abc123",
  "memory_scope": "both",
  "knowledge_datasets": ["product-docs", "faq"]
}
```

| 字段 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `user_id` | string | 是 | — | 任意字符串，画像透明映射 UUID |
| `query` | string | 否 | null | 有值→语义搜索；null→Mem0 全量，Cognee 跳过 |
| `include_conversations` | bool | 否 | `true` | 是否调用 Mem0 |
| `include_profile` | bool | 否 | `true` | 是否调用 Memobase |
| `include_knowledge` | bool | 否 | `true` | 是否调用 Cognee（需提供 query） |
| `conversation_limit` | int | 否 | 5 | Mem0 返回条数，1~100 |
| `max_token_size` | int | 否 | 500 | Memobase 上下文 token 上限，100~4000 |
| `knowledge_top_k` | int | 否 | 3 | Cognee 返回结果数，1~50 |
| `knowledge_search_type` | enum | 否 | `GRAPH_COMPLETION` | 同 knowledge search_type |
| `engine_timeout` | float | 否 | null | 每引擎超时秒数；超时记入 errors，不中断整体 |
| `chats` | Message[] | 否 | null | 当前对话轮次（传给 Memobase） |
| `agent_id` | string | 否 | null | 限定 agent 视角（Mem0） |
| `session_id` | string | 否 | null | 限定 session（`memory_scope=short/both` 时生效） |
| `memory_scope` | enum | 否 | `long` | `short`/`long`/`both`；`both` 时并发两路 Mem0 查询，响应中分别填充 `short_term_memories` 和 `long_term_memories` |
| `knowledge_datasets` | string[] | 否 | null | 限定检索数据集列表；null 搜索全部；多个数据集并发搜索后合并 |

**响应**

```json
{
  "success": true,
  "user_id": "user_01",
  "conversations": [
    {
      "id": "mem_abc123",
      "user_id": "user_01",
      "content": "用户喜欢篮球运动",
      "score": 0.88,
      "metadata": {},
      "created_at": "2026-04-19T10:00:00Z",
      "updated_at": "2026-04-19T10:00:00Z"
    }
  ],
  "short_term_memories": [],
  "long_term_memories": [
    {"id": "mem_abc123", "user_id": "user_01", "content": "用户喜欢篮球运动", "score": 0.88}
  ],
  "profile_context": "## User Profile\n- Interests: Basketball, Swimming\n...",
  "knowledge": [
    {"id": "chunk_001", "text": "CozyMemory 整合三大引擎...", "score": 0.91, "metadata": {}}
  ],
  "errors": {},
  "latency_ms": 423.5
}
```

| 响应字段 | 说明 |
|---------|------|
| `conversations` | Mem0 记忆列表（向后兼容字段，等同于 `long_term_memories`）；未启用或失败时为 `[]` |
| `short_term_memories` | 会话级短期记忆，`memory_scope=short/both` 时填充 |
| `long_term_memories` | 跨会话长期记忆，`memory_scope=long/both` 时填充 |
| `profile_context` | Memobase 生成文本，可直接插入 system prompt；未启用或无画像时为 `null` |
| `knowledge` | Cognee 搜索结果；未启用、无 query 或失败时为 `[]` |
| `errors` | 各引擎错误，键为 `conversations`/`profile`/`knowledge`；无错误时为 `{}` |
| `latency_ms` | 本次请求实际耗时（毫秒） |

**超时触发示例**（`engine_timeout=0.001`）

```json
{
  "success": true,
  "conversations": [],
  "profile_context": null,
  "knowledge": [],
  "errors": {
    "conversations": "engine timeout after 0.001s",
    "profile":       "engine timeout after 0.001s",
    "knowledge":     "engine timeout after 0.001s"
  },
  "latency_ms": 12.1
}
```

```bash
curl -X POST http://localhost:8000/api/v1/context \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_01",
    "query": "用户喜欢什么运动",
    "include_conversations": true,
    "include_profile": true,
    "include_knowledge": false,
    "memory_scope": "both",
    "agent_id": "sales-bot"
  }'
```

---

## gRPC API

**服务地址**：`<host>:50051`（明文 TCP，无 TLS）  
**包名**：`cozymemory`  
**Proto 文件**：项目 `proto/` 目录（`conversation.proto`、`profile.proto`、`knowledge.proto`、`context.proto`）

### 客户端依赖

```bash
pip install grpcio grpcio-tools   # grpcio >= 1.80.0
```

```python
import grpc
from cozymemory.grpc_server import (
    conversation_pb2, conversation_pb2_grpc,
    profile_pb2,      profile_pb2_grpc,
    knowledge_pb2,    knowledge_pb2_grpc,
    context_pb2,      context_pb2_grpc,
)

# 异步客户端（推荐）
channel = grpc.aio.insecure_channel("localhost:50051")

# 同步客户端
# channel = grpc.insecure_channel("localhost:50051")
```

> **注意**：异步调用须使用 `grpc.aio.insecure_channel`；同步客户端的 stub 不支持 `await`。

---

### ConversationService

对应 `proto/conversation.proto`，底层引擎：Mem0。

```protobuf
service ConversationService {
  rpc AddConversation          (AddConversationRequest)        returns (AddConversationResponse);
  rpc ListConversations        (ListConversationsRequest)      returns (SearchConversationsResponse);
  rpc SearchConversations      (SearchConversationsRequest)    returns (SearchConversationsResponse);
  rpc GetConversation          (GetConversationRequest)        returns (ConversationMemory);
  rpc DeleteConversation       (DeleteConversationRequest)     returns (DeleteResponse);
  rpc DeleteAllConversations   (DeleteAllConversationsRequest) returns (DeleteResponse);
}
```

#### `AddConversation`

```protobuf
message AddConversationRequest {
  string user_id = 1;
  repeated Message messages = 2;
  map<string, string> metadata = 3;
  bool infer = 4;           // true = LLM 提取；false = 原样存储
  string agent_id = 5;      // 按 agent 隔离记忆视角，空字符串表示不限制
  string session_id = 6;    // 会话 ID，映射到 Mem0 run_id（短期记忆）
}
message AddConversationResponse {
  bool success = 1;
  repeated ConversationMemory data = 2;
  string message = 3;
}
```

```python
stub = conversation_pb2_grpc.ConversationServiceStub(channel)
resp = await stub.AddConversation(
    conversation_pb2.AddConversationRequest(
        user_id="user_01",
        messages=[conversation_pb2.Message(role="user", content="我喜欢打篮球")],
        infer=True,
        agent_id="sales-bot",
        session_id="sess_abc123",
    ),
    timeout=30,
)
assert resp.success
memory_id = resp.data[0].id
```

#### `ListConversations`

```protobuf
message ListConversationsRequest {
  string user_id = 1;
  int32 limit = 2;
  string agent_id = 3;      // 限定 agent 视角
  string session_id = 4;    // 限定 session
  string memory_scope = 5;  // short / long / both（默认 long）
}
// 返回 SearchConversationsResponse
```

#### `SearchConversations`

```protobuf
message SearchConversationsRequest {
  string user_id = 1;
  string query = 2;
  int32 limit = 3;
  optional double threshold = 4;
  string agent_id = 5;      // 限定 agent 视角
  string session_id = 6;    // 限定 session（memory_scope=short/both 时生效）
  string memory_scope = 7;  // short / long / both（默认 long）
}
message SearchConversationsResponse {
  bool success = 1;
  repeated ConversationMemory data = 2;
  int32 total = 3;
  string message = 4;
}
```

#### `GetConversation`

```protobuf
message GetConversationRequest { string memory_id = 1; }
// 返回 ConversationMemory
message ConversationMemory {
  string id = 1; string user_id = 2; string content = 3;
  optional double score = 4; map<string, string> metadata = 5;
  string created_at = 6; string updated_at = 7;
}
```

#### `DeleteConversation` / `DeleteAllConversations`

```protobuf
message DeleteConversationRequest     { string memory_id = 1; }
message DeleteAllConversationsRequest { string user_id = 1; }
message DeleteResponse                { bool success = 1; string message = 2; }
```

---

### ProfileService

对应 `proto/profile.proto`，底层引擎：Memobase。

```protobuf
service ProfileService {
  rpc InsertProfile    (InsertProfileRequest)     returns (InsertProfileResponse);
  rpc FlushProfile     (FlushProfileRequest)      returns (FlushProfileResponse);
  rpc GetProfile       (GetProfileRequest)        returns (UserProfile);
  rpc GetContext       (GetContextRequest)        returns (GetContextResponse);
  rpc AddProfileItem   (AddProfileItemRequest)    returns (AddProfileItemResponse);
  rpc DeleteProfileItem(DeleteProfileItemRequest) returns (DeleteResponse);
}
```

#### `InsertProfile`

```protobuf
message InsertProfileRequest {
  string user_id = 1;          // 任意字符串，内部自动映射为 UUID v4
  repeated Message messages = 2;
  bool sync = 3;               // true = 等待 LLM 处理完成
}
message InsertProfileResponse {
  bool success = 1; string user_id = 2; string blob_id = 3; string message = 4;
}
```

```python
stub = profile_pb2_grpc.ProfileServiceStub(channel)
resp = await stub.InsertProfile(
    profile_pb2.InsertProfileRequest(
        user_id="user_01",   # 任意 ID，无需 UUID v4
        messages=[conversation_pb2.Message(role="user", content="我叫小明，喜欢游泳")],
        sync=True,
    ),
    timeout=60,
)
assert resp.success
```

#### `GetProfile`

```protobuf
message GetProfileRequest { string user_id = 1; }
message UserProfile {
  string user_id = 1; repeated ProfileTopic topics = 2; string updated_at = 3;
}
message ProfileTopic {
  string id = 1; string topic = 2; string sub_topic = 3;
  string content = 4; string created_at = 5; string updated_at = 6;
}
```

#### `GetContext`

```protobuf
message GetContextRequest {
  string user_id = 1; int32 max_token_size = 2; repeated Message chats = 3;
}
message GetContextResponse {
  bool success = 1; string user_id = 2; string context = 3;
}
```

#### `AddProfileItem` / `DeleteProfileItem`

```protobuf
message AddProfileItemRequest {
  string user_id = 1; string topic = 2; string sub_topic = 3; string content = 4;
}
message AddProfileItemResponse {
  bool success = 1; ProfileTopic data = 2; string message = 3;
}
message DeleteProfileItemRequest {
  string user_id = 1; string profile_id = 2;
}
```

> `AddProfileItem` 要求用户已在 Memobase 创建（先调用 `InsertProfile`），否则返回 `FAILED_PRECONDITION`。

---

### KnowledgeService

对应 `proto/knowledge.proto`，底层引擎：Cognee。

```protobuf
service KnowledgeService {
  rpc CreateDataset  (CreateDatasetRequest)   returns (DatasetInfo);
  rpc ListDatasets   (ListDatasetsRequest)    returns (ListDatasetsResponse);
  rpc AddKnowledge   (AddKnowledgeRequest)    returns (AddKnowledgeResponse);
  rpc Cognify        (CognifyRequest)         returns (CognifyResponse);
  rpc SearchKnowledge(SearchKnowledgeRequest) returns (SearchKnowledgeResponse);
  rpc DeleteKnowledge(DeleteKnowledgeRequest) returns (DeleteResponse);
}
```

#### `AddKnowledge`

```protobuf
message AddKnowledgeRequest {
  string data = 1; string dataset = 2; repeated string node_set = 3;
}
message AddKnowledgeResponse {
  bool success = 1; string data_id = 2; string dataset_name = 3; string message = 4;
}
```

#### `Cognify`

```protobuf
message CognifyRequest {
  repeated string datasets = 1;    // 空列表 = 处理全部
  bool run_in_background = 2;
}
message CognifyResponse {
  bool success = 1; string pipeline_run_id = 2; string status = 3; string message = 4;
}
```

#### `SearchKnowledge`

```protobuf
message SearchKnowledgeRequest {
  string query = 1;
  string dataset = 2;        // 空字符串 = 搜索全部
  string search_type = 3;    // CHUNKS / SUMMARIES / RAG_COMPLETION / GRAPH_COMPLETION
  int32 top_k = 4;
}
message SearchKnowledgeResponse {
  bool success = 1; repeated KnowledgeSearchResult data = 2; int32 total = 3; string message = 4;
}
message KnowledgeSearchResult {
  string id = 1; string text = 2; optional double score = 3; map<string, string> metadata = 4;
}
```

**Python 完整流程示例**

```python
import asyncio

stub = knowledge_pb2_grpc.KnowledgeServiceStub(channel)

# 1. 添加文档
add_resp = await stub.AddKnowledge(
    knowledge_pb2.AddKnowledgeRequest(data="CozyMemory 整合三大引擎", dataset="my-ds"),
    timeout=30,
)

# 2. 触发图谱构建（后台，30~120s）
await stub.Cognify(
    knowledge_pb2.CognifyRequest(datasets=["my-ds"], run_in_background=True),
    timeout=60,
)

# 3. 轮询搜索
for _ in range(12):   # 最多等 120s
    await asyncio.sleep(10)
    result = await stub.SearchKnowledge(
        knowledge_pb2.SearchKnowledgeRequest(
            query="AI 记忆引擎", dataset="my-ds", search_type="CHUNKS", top_k=5
        ),
        timeout=30,
    )
    if list(result.data):
        break
```

---

### ContextService

对应 `proto/context.proto`。一次 RPC 并发调用三引擎。

```protobuf
service ContextService {
  rpc GetUnifiedContext(GetUnifiedContextRequest) returns (GetUnifiedContextResponse);
}

message GetUnifiedContextRequest {
  string user_id = 1;
  optional string query = 2;
  bool include_conversations = 3;
  bool include_profile = 4;
  bool include_knowledge = 5;
  int32 conversation_limit = 6;
  int32 max_token_size = 7;
  int32 knowledge_top_k = 8;
  string knowledge_search_type = 9;
  optional double engine_timeout = 10;
  repeated Message chats = 11;
  string agent_id = 12;              // 智能体 ID，按 agent 隔离记忆视角
  string session_id = 13;            // 会话 ID，短期记忆隔离
  string memory_scope = 14;          // short / long / both（默认 long）
  repeated string knowledge_datasets = 15; // 指定数据集，空 = 搜索全部
}

message GetUnifiedContextResponse {
  bool success = 1;
  string user_id = 2;
  repeated ConversationMemory conversations = 3;       // 向后兼容
  string profile_context = 4;
  repeated KnowledgeSearchResult knowledge = 5;
  map<string, string> errors = 6;      // 各引擎错误，无错误时为空 map
  double latency_ms = 7;
  repeated ConversationMemory short_term_memories = 8; // memory_scope=short/both 时填充
  repeated ConversationMemory long_term_memories = 9;  // memory_scope=long/both 时填充
}
```

```python
stub = context_pb2_grpc.ContextServiceStub(channel)
resp = await stub.GetUnifiedContext(
    context_pb2.GetUnifiedContextRequest(
        user_id="user_01",
        query="用户喜欢什么运动",
        include_conversations=True,
        include_profile=True,
        include_knowledge=False,
        conversation_limit=5,
        max_token_size=300,
        engine_timeout=5.0,
        agent_id="sales-bot",
        memory_scope="both",         # 同时获取短期和长期记忆
    ),
    timeout=30,
)
assert resp.success
print(resp.profile_context)                  # 可直接插入 system prompt
print(list(resp.short_term_memories))        # 本次会话记忆
print(list(resp.long_term_memories))         # 跨会话长期记忆
print(dict(resp.errors))                     # {} 表示全部引擎正常
print(resp.latency_ms)
```

---

## 端口与访问地址汇总

| 服务 | 协议 | 端口 | 说明 |
|------|------|------|------|
| CozyMemory REST | HTTP | `:8000` | 通过 Caddy 反向代理 |
| CozyMemory gRPC | TCP | `:50051` | 直连容器，无代理 |
| Cognee API | HTTP | `:8080` | 通过 Caddy |
| Mem0 API | HTTP | `:8081` | 通过 Caddy |
| Memobase API | HTTP | `:8019` | 通过 Caddy |
| Swagger UI | HTTP | `:8000/docs` | CozyMemory 交互式文档 |
| ReDoc | HTTP | `:8000/redoc` | 另一种风格的 REST 文档 |
| OpenAPI JSON | HTTP | `:8000/openapi.json` | 机器可读的接口定义 |

---

## 常见问题

### Q: 调用画像接口时要自己处理 UUID v4 吗？

不需要。CozyMemory 内置 Redis 透明映射层，任意字符串 `user_id` 均自动映射为 Memobase 所需的 UUID v4。  
直接传 `"user_01"` 即可，CozyMemory 内部完成转换。

如需查看某个 `user_id` 对应的 UUID，调用：

```bash
curl http://localhost:8000/api/v1/users/user_01/uuid
```

### Q: 添加文档后搜索没有结果？

必须先调用 `cognify`，等待图谱构建完成（30~120s）后搜索才有结果。建议轮询等待：

```python
# cognify 完成信号：search 返回非空 data
```

### Q: 统一上下文接口报 errors 怎么办？

`errors` 字段记录各引擎的局部失败，不影响整体 `success=true`。先检查 `errors` 再处理对应字段：

```python
resp = ...
if "profile" in resp["errors"]:
    print("画像获取失败:", resp["errors"]["profile"])
    # profile_context 此时为 null
```

### Q: gRPC 调用报 `TypeError: object can't be used in 'await'`？

使用了同步 channel。改为异步：

```python
# 错误
channel = grpc.insecure_channel("localhost:50051")

# 正确
channel = grpc.aio.insecure_channel("localhost:50051")
```

### Q: AddProfileItem 返回 FAILED_PRECONDITION？

用户未在 Memobase 中创建。必须先调用 `InsertProfile` / `POST /profiles/insert` 初始化用户，再调用 `AddProfileItem`。

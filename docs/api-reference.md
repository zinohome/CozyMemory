# CozyMemory API Reference

**版本**: 0.3.0  
**Base URL**: `/api/v1`  
**协议**: REST (HTTP/1.1) + gRPC (HTTP/2)  
**许可**: AGPL-3.0-or-later

所有 REST 响应统一格式 `{success: bool, data: ..., message: str}`，除非另有说明。

---

## 鉴权

CozyMemory 采用双角色鉴权模型：

| 角色 | Header | 值 | 权限范围 |
|------|--------|----|----------|
| **App Key** | `X-Cozy-API-Key` | App Key（PG 动态 key） | 业务路由，数据按 App 隔离 |
| **Bootstrap Key** | `X-Cozy-API-Key` | Bootstrap key（env `COZY_API_KEYS`） | 全部路由，数据不隔离 |
| **Developer JWT** | `Authorization: Bearer <JWT>` | JWT token | `/auth/*` + `/dashboard/*` + 业务路由（需同时带 `X-Cozy-App-Id`） |

### 免鉴权端点

`/health`、`/docs`、`/redoc`、`/openapi.json`

### 用户 ID 隔离

- **App Key**：`user_id` 通过 `uuid5(App.namespace_id, external_user_id)` 映射为内部 UUID，数据按 App 隔离
- **Bootstrap Key**：`user_id` 直接透传，无隔离

---

## 健康检查

### GET /health

检查三引擎连通性。免鉴权。

**响应**

```json
{
  "status": "healthy",
  "engines": {
    "mem0": {"name": "Mem0", "status": "healthy", "latency_ms": 26.0, "error": null},
    "memobase": {"name": "Memobase", "status": "healthy", "latency_ms": 15.3, "error": null},
    "cognee": {"name": "Cognee", "status": "healthy", "latency_ms": 33.0, "error": null}
  },
  "timestamp": "2026-04-24T15:44:05Z"
}
```

`status` 取值：`healthy`（全部正常）、`degraded`（部分不可用）、`unhealthy`（全部不可用）。

---

## Auth — 开发者账号

### POST /auth/register

注册开发者账号，自动创建 Organization。

**请求**

```json
{
  "email": "dev@example.com",
  "password": "securepass123",
  "org_name": "My Company",
  "org_slug": "my-company",
  "name": "Zhang Jun"
}
```

**响应**

```json
{
  "access_token": "eyJhbGci...",
  "expires_in": 86400,
  "developer": {
    "id": "uuid",
    "email": "dev@example.com",
    "name": "Zhang Jun",
    "role": "owner",
    "org_id": "uuid",
    "org_name": "My Company",
    "org_slug": "my-company",
    "is_active": true,
    "last_login_at": null
  }
}
```

### POST /auth/login

JWT 登录。

**请求**

```json
{
  "email": "dev@example.com",
  "password": "securepass123"
}
```

**响应**：同 `/auth/register`。

### GET /auth/me

获取当前开发者信息。需 Bearer JWT。

**响应**：`DeveloperInfo` 对象。

### PATCH /auth/password

修改密码。需 Bearer JWT。

**请求**

```json
{
  "old_password": "oldpass",
  "new_password": "newpass"
}
```

**响应**：204 No Content。

---

## Dashboard — 应用管理

所有 `/dashboard/*` 端点需 Bearer JWT。

### GET /dashboard/apps

列出当前 org 下的 App。

**查询参数**：`limit`（默认 50）、`offset`（默认 0）

**响应**

```json
{
  "data": [
    {
      "id": "uuid",
      "org_id": "uuid",
      "name": "My Chatbot",
      "slug": "my-chatbot",
      "namespace_id": "uuid",
      "description": "",
      "created_at": "2026-04-24T10:00:00Z"
    }
  ],
  "total": 1
}
```

### POST /dashboard/apps

创建 App。需 owner/admin 角色。

**请求**

```json
{
  "name": "My Chatbot",
  "slug": "my-chatbot",
  "description": "Production chatbot"
}
```

### GET /dashboard/apps/{app_id}

获取单个 App 详情。

### PATCH /dashboard/apps/{app_id}

更新 App。需 owner/admin。

**请求**

```json
{
  "name": "New Name",
  "description": "Updated description"
}
```

### DELETE /dashboard/apps/{app_id}

删除 App 及其所有数据。需 owner 角色。204 No Content。

### GET /dashboard/organization

获取当前 org 信息。

**响应**

```json
{
  "id": "uuid",
  "name": "My Company",
  "slug": "my-company",
  "created_at": "2026-04-24T10:00:00Z",
  "developer_count": 3,
  "app_count": 2
}
```

### PATCH /dashboard/organization

更新 org 信息。需 owner。

### GET /dashboard/organization/developers

列出 org 下所有开发者。

### GET /dashboard/apps/{app_id}/usage

获取 App API 使用统计。

**查询参数**：`days`（1-90，默认 7）

**响应**

```json
{
  "total": 1250,
  "success": 1200,
  "errors": 50,
  "avg_latency_ms": 45.3,
  "per_route": [{"route": "conversations.add", "count": 500, "avg_ms": 38.2}],
  "daily": [{"date": "2026-04-24", "count": 200}],
  "since": "2026-04-17T00:00:00Z",
  "days": 7
}
```

---

## API Keys

所有端点前缀 `/dashboard/apps/{app_id}/keys`，需 Bearer JWT。

### GET /dashboard/apps/{app_id}/keys

列出 App 的所有 Key。

**响应**

```json
{
  "data": [
    {
      "id": "uuid",
      "app_id": "uuid",
      "name": "Production Key",
      "prefix": "cozy_live_abc12",
      "environment": "live",
      "disabled": false,
      "created_at": "2026-04-24T10:00:00Z",
      "last_used_at": null,
      "expires_at": null
    }
  ],
  "total": 1
}
```

### POST /dashboard/apps/{app_id}/keys

创建 Key。需 owner/admin。

**请求**

```json
{
  "name": "Production Key",
  "environment": "live"
}
```

**响应**

```json
{
  "record": {"id": "uuid", "name": "Production Key", "prefix": "cozy_live_abc12", "...": "..."},
  "key": "cozy_live_abc12def456..."
}
```

> **重要**：`key` 字段仅在创建时返回一次，之后无法再获取。

### POST /dashboard/apps/{app_id}/keys/{key_id}/rotate

轮转 Key（旧 Key 立即失效）。需 owner/admin。

### PATCH /dashboard/apps/{app_id}/keys/{key_id}

更新 Key 属性（name、disabled）。需 owner/admin。

### DELETE /dashboard/apps/{app_id}/keys/{key_id}

删除 Key。需 owner。204 No Content。

---

## External Users

前缀 `/dashboard/apps/{app_id}/users`，需 Bearer JWT。

### GET /dashboard/apps/{app_id}/users

分页列出 App 下的外部用户。

**查询参数**：`limit`（默认 50）、`offset`（默认 0）

**响应**

```json
{
  "data": [
    {
      "external_user_id": "alice",
      "internal_uuid": "uuid",
      "created_at": "2026-04-24T10:00:00Z"
    }
  ],
  "total": 1
}
```

### DELETE /dashboard/apps/{app_id}/users/{external_user_id}

GDPR 删除：移除用户及其在三引擎的所有数据。

---

## Conversations — 对话记忆（Mem0）

需 App Key 或 Bootstrap Key。

### GET /conversations

列出用户的所有记忆。

**查询参数**：`user_id`（必填）、`limit`（默认 100）

**响应**

```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "memory": "用户喜欢科幻小说",
      "created_at": "2026-04-24T10:00:00Z",
      "updated_at": null,
      "metadata": {}
    }
  ],
  "message": "ok"
}
```

### POST /conversations

添加对话，自动提取事实记忆。

**请求**

```json
{
  "user_id": "alice",
  "messages": [
    {"role": "user", "content": "I love hiking in the mountains"},
    {"role": "assistant", "content": "That sounds wonderful!"}
  ],
  "metadata": {},
  "infer": true
}
```

- `infer=true`（默认）：LLM 提取事实
- `infer=false`：存储原始消息

可选字段：`agent_id`、`session_id`

### POST /conversations/search

语义搜索记忆。

**请求**

```json
{
  "user_id": "alice",
  "query": "outdoor activities",
  "limit": 10,
  "threshold": 0.5
}
```

可选字段：`agent_id`、`session_id`、`memory_scope`

### GET /conversations/{memory_id}

获取单条记忆。不存在返回 `data: null`（Mem0 返回 null 而非 404）。

### DELETE /conversations/{memory_id}

删除单条记忆。

### DELETE /conversations?user_id=xxx

删除用户的全部记忆。

---

## Profiles — 用户画像（Memobase）

需 App Key 或 Bootstrap Key。

### POST /profiles/insert

插入对话到 Memobase buffer。

**请求**

```json
{
  "user_id": "alice",
  "messages": [
    {"role": "user", "content": "I'm a software engineer who loves hiking"}
  ],
  "sync": true
}
```

- `sync=true`：同步处理（等待 LLM 提取完成）
- `sync=false`：异步入 buffer

> 用户不存在时自动创建。

### POST /profiles/flush

触发 buffer 处理，立即生成画像。

**请求**

```json
{
  "user_id": "alice",
  "sync": true
}
```

### GET /profiles/{user_id}

获取结构化画像。

**响应**

```json
{
  "success": true,
  "data": {
    "profiles": [
      {
        "id": "uuid",
        "content": "reads sci-fi novels",
        "attributes": {
          "topic": "interest",
          "sub_topic": "hobby"
        }
      }
    ]
  }
}
```

### POST /profiles/{user_id}/context

生成 LLM-ready 上下文 prompt。

**请求**

```json
{
  "max_token_size": 2000,
  "chats": []
}
```

**响应**

```json
{
  "success": true,
  "data": {
    "context": "User is a software engineer who enjoys hiking and reading sci-fi novels..."
  }
}
```

### POST /profiles/{user_id}/items

手动添加画像条目。

**请求**

```json
{
  "user_id": "alice",
  "topic": "interest",
  "sub_topic": "hobby",
  "content": "reading"
}
```

### DELETE /profiles/{user_id}/items/{profile_id}

删除单条画像。

---

## Knowledge — 知识图谱（Cognee）

需 App Key 或 Bootstrap Key。

### GET /knowledge/datasets

列出数据集（App Key 只看自己的，Bootstrap Key 看全部）。

### POST /knowledge/datasets?name=xxx

创建数据集。

### DELETE /knowledge/datasets/{dataset_id}

删除数据集。

### POST /knowledge/add

添加文本文档到数据集。

**请求**

```json
{
  "data": "这是一段长文本，将被处理为知识图谱...",
  "dataset": "my-dataset"
}
```

### POST /knowledge/add-files

上传文件到数据集。`multipart/form-data`。

**表单字段**：`dataset`（字符串）、`files`（文件数组）

### GET /knowledge/datasets/{dataset_id}/data

列出数据集内的文档。

### GET /knowledge/datasets/{dataset_id}/data/{data_id}/raw

获取文档原始内容（`application/octet-stream`）。

### DELETE /knowledge/datasets/{dataset_id}/data/{data_id}

删除单个文档。

### POST /knowledge/cognify

触发知识图谱构建。

**请求**

```json
{
  "datasets": ["dataset-id-1"],
  "run_in_background": true
}
```

**响应**

```json
{
  "success": true,
  "pipeline_run_id": "uuid",
  "status": "DATASET_PROCESSING_STARTED"
}
```

### GET /knowledge/cognify/status/{job_id}

查询 cognify 任务状态。

### POST /knowledge/search

搜索知识图谱。

**请求**

```json
{
  "query": "什么是机器学习？",
  "dataset": "my-dataset",
  "search_type": "GRAPH_COMPLETION",
  "top_k": 5
}
```

`search_type` 取值：
- `CHUNKS`：原始文本块
- `SUMMARIES`：段落摘要
- `RAG_COMPLETION`：LLM 基于检索生成
- `GRAPH_COMPLETION`：沿图谱推理（最强）

### GET /knowledge/datasets/{dataset_id}/graph

获取知识图谱结构（节点 + 边），用于可视化。

### DELETE /knowledge

删除文档（兼容旧接口）。

**请求**

```json
{
  "dataset_id": "uuid",
  "data_id": "uuid"
}
```

---

## Context — 统一上下文

需 App Key 或 Bootstrap Key。

### POST /context

并发查询三引擎，返回融合上下文。

**请求**

```json
{
  "user_id": "alice",
  "query": "outdoor activities",
  "max_token_size": 4000
}
```

**响应**

```json
{
  "success": true,
  "data": {
    "conversations": [...],
    "profiles": "User likes hiking...",
    "knowledge": [...],
    "errors": {}
  }
}
```

- 总延迟 = max(各引擎延迟)，而非相加
- `query=null`：Mem0 返回全量，Cognee 跳过
- 单引擎故障不阻塞其他引擎，失败信息记入 `errors`

---

## Operator — 平台运维

所有 `/operator/*` 端点仅接受 Bootstrap Key，JWT 会被拒绝。

### GET /operator/orgs

跨组织总览。

**响应**

```json
{
  "data": [
    {
      "id": "uuid",
      "name": "My Company",
      "slug": "my-company",
      "created_at": "2026-04-24T10:00:00Z",
      "dev_count": 3,
      "app_count": 2
    }
  ],
  "total": 1
}
```

### GET /operator/users-mapping

列出所有用户 ID 映射。

### GET /operator/users-mapping/{user_id}/uuid

查询用户映射。

**查询参数**：`create`（默认 false）

- `create=false`：只读，不存在返回 404
- `create=true`：幂等创建

### DELETE /operator/users-mapping/{user_id}/uuid

删除用户映射（不删除引擎数据）。

### GET /operator/backup/export/{user_id}

导出用户全部数据为 JSON。

**查询参数**：`datasets`（逗号分隔的 Cognee dataset ID）

### POST /operator/backup/import

导入备份 JSON。

**请求**

```json
{
  "bundle": {"...": "导出的 JSON 内容"},
  "target_user_id": "alice"
}
```

---

## 错误响应

### 格式

```json
{
  "success": false,
  "error": "EngineError",
  "detail": "Mem0 returned HTTP 500",
  "engine": "mem0"
}
```

> `APP_ENV=production` 时 `detail` 被隐藏。

### HTTP 状态码

| 状态码 | 含义 |
|--------|------|
| 400 | 请求参数错误 |
| 401 | 未鉴权或鉴权失败 |
| 403 | 权限不足（如 member 角色尝试删除 App） |
| 404 | 资源不存在 |
| 422 | 请求体校验失败 |
| 502 | 后端引擎错误（EngineError） |

---

## gRPC API

19 个 gRPC 方法，功能与 REST 完全一致。Proto 定义位于 `proto/` 目录。

### 连接方式

| 场景 | 地址 | 协议 |
|------|------|------|
| 容器内网 / 本机调试 | `localhost:50151` | insecure (h2c) |
| 外部客户端（生产） | `<server-ip>:50051` | TLS (Caddy 自签证书) |

### 鉴权

通过 gRPC metadata 传递，等同 REST 的 Header：

```python
metadata = [('x-cozy-api-key', '<your-app-key>')]
# 或 bootstrap key:
metadata = [('x-cozy-api-key', '<bootstrap-key>')]
```

### 服务定义

```protobuf
// proto/conversation.proto
service ConversationService {
  rpc AddConversation(AddConversationRequest) returns (AddConversationResponse);
  rpc SearchConversations(SearchConversationsRequest) returns (SearchConversationsResponse);
  rpc ListConversations(ListConversationsRequest) returns (SearchConversationsResponse);
  rpc GetConversation(GetConversationRequest) returns (ConversationMemory);
  rpc DeleteConversation(DeleteConversationRequest) returns (DeleteResponse);
  rpc DeleteAllConversations(DeleteAllConversationsRequest) returns (DeleteResponse);
}

// proto/profile.proto
service ProfileService {
  rpc InsertProfile(InsertProfileRequest) returns (InsertProfileResponse);
  rpc FlushProfile(FlushProfileRequest) returns (FlushProfileResponse);
  rpc GetProfile(GetProfileRequest) returns (UserProfile);
  rpc GetContext(GetContextRequest) returns (GetContextResponse);
  rpc AddProfileItem(AddProfileItemRequest) returns (AddProfileItemResponse);
  rpc DeleteProfileItem(DeleteProfileItemRequest) returns (DeleteProfileItemResponse);
}

// proto/knowledge.proto
service KnowledgeService {
  rpc CreateDataset(CreateDatasetRequest) returns (CreateDatasetResponse);
  rpc ListDatasets(ListDatasetsRequest) returns (ListDatasetsResponse);
  rpc AddKnowledge(AddKnowledgeRequest) returns (AddKnowledgeResponse);
  rpc Cognify(CognifyRequest) returns (CognifyResponse);
  rpc SearchKnowledge(SearchKnowledgeRequest) returns (SearchKnowledgeResponse);
  rpc DeleteKnowledge(DeleteKnowledgeRequest) returns (DeleteKnowledgeResponse);
}

// proto/context.proto
service ContextService {
  rpc GetUnifiedContext(GetUnifiedContextRequest) returns (GetUnifiedContextResponse);
}
```

### Python 调用示例

```python
import grpc
from cozymemory.grpc_server import (
    conversation_pb2, conversation_pb2_grpc,
    profile_pb2, profile_pb2_grpc,
    knowledge_pb2, knowledge_pb2_grpc,
    context_pb2, context_pb2_grpc,
)

# 连接
channel = grpc.insecure_channel('localhost:50151')
metadata = [('x-cozy-api-key', 'your-app-key')]

# ── 记忆 ──
conv = conversation_pb2_grpc.ConversationServiceStub(channel)

# 添加记忆（同步，等 LLM 提取完成）
resp = conv.AddConversation(conversation_pb2.AddConversationRequest(
    user_id="user_001",
    messages=[conversation_pb2.Message(role="user", content="我在做AI产品开发")],
), metadata=metadata, timeout=60)
print(resp.success, resp.data)  # True, [ConversationMemory(...)]

# 添加记忆（异步，立即返回）
resp = conv.AddConversation(conversation_pb2.AddConversationRequest(
    user_id="user_001",
    messages=[conversation_pb2.Message(role="user", content="最近在学Rust")],
    async_mode=True,
), metadata=metadata, timeout=10)
print(resp.message)  # "对话已接收，记忆正在后台提取中"

# 搜索记忆
resp = conv.SearchConversations(conversation_pb2.SearchConversationsRequest(
    user_id="user_001", query="技术栈"
), metadata=metadata, timeout=10)
for m in resp.data:
    print(m.content, m.score)

# 列出所有记忆
resp = conv.ListConversations(conversation_pb2.ListConversationsRequest(
    user_id="user_001"
), metadata=metadata, timeout=10)

# ── 用户画像 ──
prof = profile_pb2_grpc.ProfileServiceStub(channel)

# 插入对话（异步提取画像）
prof.InsertProfile(profile_pb2.InsertProfileRequest(
    user_id="<uuid-v4>",
    messages=[conversation_pb2.Message(role="user", content="我叫张三，30岁")],
    sync=False,
), metadata=metadata)

# 获取画像
resp = prof.GetProfile(profile_pb2.GetProfileRequest(
    user_id="<uuid-v4>"
), metadata=metadata)
for topic in resp.topics:
    print(topic.topic, topic.sub_topic, topic.content)

# 获取 LLM 上下文 prompt
resp = prof.GetContext(profile_pb2.GetContextRequest(
    user_id="<uuid-v4>"
), metadata=metadata)
print(resp.context)  # "---\n# 记忆\n..."

# ── 知识图谱 ──
know = knowledge_pb2_grpc.KnowledgeServiceStub(channel)

know.CreateDataset(knowledge_pb2.CreateDatasetRequest(name="my_kb"), metadata=metadata)
know.AddKnowledge(knowledge_pb2.AddKnowledgeRequest(
    data="PostgreSQL是关系数据库...", dataset="my_kb"
), metadata=metadata)
know.Cognify(knowledge_pb2.CognifyRequest(datasets=["my_kb"]), metadata=metadata, timeout=300)

resp = know.SearchKnowledge(knowledge_pb2.SearchKnowledgeRequest(
    query="数据库", dataset="my_kb", search_type="CHUNKS"
), metadata=metadata)
# search_type 可选: CHUNKS, SUMMARIES, GRAPH_COMPLETION 等
# 不传则默认 CHUNKS

# ── 统一上下文 ──
ctx = context_pb2_grpc.ContextServiceStub(channel)
resp = ctx.GetUnifiedContext(context_pb2.GetUnifiedContextRequest(
    user_id="user_001",
    query="技术背景",
    profile_user_id="<uuid-v4>",  # 画像用户 ID
), metadata=metadata, timeout=10)
print(resp.conversations, resp.profile_context, resp.knowledge)
```

### 性能对比（gRPC vs REST）

| 接口 | gRPC | REST | 提速 |
|------|------|------|------|
| Search | 1.0ms | 1.8ms | 1.8x |
| Add(async) | 0.7ms | 3.5ms | 5.0x |
| Profile.Get | 3.9ms | 5.4ms | 1.4x |
| 10并发 QPS | ~1M | ~750K | 1.4x |

**建议**：高频业务调用（搜索、写入）走 gRPC，管理操作走 REST。

---

## Swagger UI

启动后访问 `http://你的IP:8000/docs` 查看交互式 API 文档。

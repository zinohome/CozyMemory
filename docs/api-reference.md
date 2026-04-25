# CozyMemory API Reference

**版本**: 0.2.0  
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

18 个 gRPC 方法镜像 REST 端点（健康检查为 REST 专属）。Proto 定义位于 `proto/` 目录。

```protobuf
service ConversationService {
  rpc ListMemories(ListMemoriesRequest) returns (MemoryListResponse);
  rpc AddConversation(AddConversationRequest) returns (MemoryListResponse);
  rpc SearchMemories(SearchMemoriesRequest) returns (MemoryListResponse);
  rpc GetMemory(GetMemoryRequest) returns (MemoryResponse);
  rpc DeleteMemory(DeleteMemoryRequest) returns (MemoryListResponse);
  rpc DeleteAllMemories(DeleteAllMemoriesRequest) returns (MemoryListResponse);
}

service ProfileService {
  rpc InsertProfile(InsertProfileRequest) returns (InsertProfileResponse);
  rpc FlushProfile(FlushProfileRequest) returns (FlushProfileResponse);
  rpc GetProfile(GetProfileRequest) returns (GetProfileResponse);
  rpc GetProfileContext(GetProfileContextRequest) returns (GetProfileContextResponse);
  rpc AddProfileItem(AddProfileItemRequest) returns (AddProfileItemResponse);
  rpc DeleteProfileItem(DeleteProfileItemRequest) returns (DeleteProfileItemResponse);
}

service KnowledgeService {
  rpc ListDatasets(ListDatasetsRequest) returns (DatasetListResponse);
  rpc AddKnowledge(AddKnowledgeRequest) returns (AddKnowledgeResponse);
  rpc CognifyKnowledge(CognifyRequest) returns (CognifyResponse);
  rpc SearchKnowledge(SearchKnowledgeRequest) returns (SearchKnowledgeResponse);
  rpc DeleteKnowledge(DeleteKnowledgeRequest) returns (DeleteKnowledgeResponse);
}

service ContextService {
  rpc GetUnifiedContext(ContextRequest) returns (ContextResponse);
}
```

gRPC 端口：50051（Caddy TLS 终止，内部 h2c）。

---

## Swagger UI

启动后访问 `http://你的IP:8000/docs` 查看交互式 API 文档。

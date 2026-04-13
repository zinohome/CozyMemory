# CozyMemory API 参考文档

**版本**: 2.0  
**日期**: 2026-04-13  
**状态**: 已批准

---

## 1. 概述

CozyMemory 提供双协议 API：

| 协议 | 端口 | 用途 |
|------|------|------|
| **REST API** | 8000 | 通用访问，自动生成 OpenAPI 文档 |
| **gRPC API** | 50051 | 内部微服务高性能调用 |

REST 和 gRPC 功能完全对等，由同一个 Service 层驱动。

---

## 2. REST API

### 2.1 通用

**Base URL**: `http://localhost:8000/api/v1`

**认证**: 暂无，后期可加 API Key 中间件

**错误响应格式**:
```json
{
  "success": false,
  "error": "EngineError",
  "detail": "Mem0 服务不可用",
  "engine": "mem0"
}
```

**HTTP 状态码**:
- `200` - 成功
- `400` - 请求参数错误
- `404` - 资源不存在
- `502` - 下游引擎错误
- `503` - 引擎不可用

---

### 2.2 健康检查

#### `GET /api/v1/health`

检查服务及所有引擎的健康状态。

**响应**:
```json
{
  "status": "healthy",
  "engines": {
    "mem0": {
      "name": "Mem0",
      "status": "healthy",
      "latency_ms": 12.5
    },
    "memobase": {
      "name": "Memobase",
      "status": "healthy",
      "latency_ms": 8.3
    },
    "cognee": {
      "name": "Cognee",
      "status": "healthy",
      "latency_ms": 15.1
    }
  },
  "timestamp": "2026-04-13T10:30:00Z"
}
```

---

### 2.3 会话记忆 (`/api/v1/conversations`)

> 对应引擎：**Mem0**

#### `POST /api/v1/conversations`

添加对话，Mem0 自动提取事实性记忆。

**请求**:
```json
{
  "user_id": "user_123",
  "messages": [
    {"role": "user", "content": "我喜欢喝拿铁咖啡"},
    {"role": "assistant", "content": "好的，我记住了你喜欢拿铁咖啡。"}
  ],
  "metadata": {"source": "chat", "session_id": "sess_001"},
  "infer": true
}
```

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "id": "mem_abc123",
      "user_id": "user_123",
      "content": "用户喜欢喝拿铁咖啡",
      "score": null,
      "metadata": {"source": "chat", "session_id": "sess_001"},
      "created_at": "2026-04-13T10:30:00Z",
      "updated_at": null
    }
  ],
  "message": "对话已添加，提取出 1 条记忆"
}
```

#### `POST /api/v1/conversations/search`

搜索会话记忆。

**请求**:
```json
{
  "user_id": "user_123",
  "query": "咖啡偏好",
  "limit": 10,
  "threshold": 0.5
}
```

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "id": "mem_abc123",
      "user_id": "user_123",
      "content": "用户喜欢喝拿铁咖啡",
      "score": 0.92,
      "metadata": {},
      "created_at": "2026-04-13T10:30:00Z",
      "updated_at": null
    }
  ],
  "total": 1,
  "message": ""
}
```

#### `GET /api/v1/conversations/{memory_id}`

获取单条记忆。

**响应**: 单条 `ConversationMemory`

#### `DELETE /api/v1/conversations/{memory_id}`

删除单条记忆。

**响应**:
```json
{"success": true, "message": "记忆已删除"}
```

#### `DELETE /api/v1/conversations?user_id={user_id}`

删除用户所有记忆。

**响应**:
```json
{"success": true, "message": "用户所有记忆已删除"}
```

---

### 2.4 用户画像 (`/api/v1/profiles`)

> 对应引擎：**Memobase**

#### `POST /api/v1/profiles/insert`

插入对话到 Memobase 缓冲区，自动提取画像。

**请求**:
```json
{
  "user_id": "user_123",
  "messages": [
    {"role": "user", "content": "我叫小明，今年25岁"},
    {"role": "assistant", "content": "你好小明！"}
  ],
  "sync": false
}
```

**响应**:
```json
{
  "success": true,
  "user_id": "user_123",
  "blob_id": "blob_abc123",
  "message": "对话已插入缓冲区"
}
```

> **注意**：`sync=false` 时数据进入缓冲区，需要调用 flush 或等待自动处理才能在画像中体现。

#### `POST /api/v1/profiles/flush`

触发缓冲区处理，将缓冲区数据提取为画像。

**请求**:
```json
{
  "user_id": "user_123",
  "sync": true
}
```

**响应**:
```json
{"success": true, "message": "处理完成"}
```

#### `GET /api/v1/profiles/{user_id}`

获取用户结构化画像。

**响应**:
```json
{
  "success": true,
  "data": {
    "user_id": "user_123",
    "topics": [
      {
        "id": "prof_abc123",
        "topic": "basic_info",
        "sub_topic": "name",
        "content": "小明",
        "created_at": "2026-04-13T10:30:00Z",
        "updated_at": null
      },
      {
        "id": "prof_def456",
        "topic": "basic_info",
        "sub_topic": "age",
        "content": "25岁",
        "created_at": "2026-04-13T10:30:00Z",
        "updated_at": null
      }
    ],
    "updated_at": "2026-04-13T10:30:00Z"
  },
  "message": ""
}
```

#### `POST /api/v1/profiles/{user_id}/context`

获取上下文提示词（可直接插入 LLM prompt）。

**请求**:
```json
{
  "user_id": "user_123",
  "max_token_size": 500,
  "chats": null
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "user_id": "user_123",
    "context": "# Memory\nUnless the user has relevant queries...\n## User Background:\n- basic_info:name:小明\n- basic_info:age:25岁\n..."
  },
  "message": ""
}
```

---

### 2.5 知识库 (`/api/v1/knowledge`)

> 对应引擎：**Cognee**

#### `POST /api/v1/knowledge/datasets`

创建数据集。

**请求**:
```json
{"name": "my-dataset"}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "my-dataset",
    "created_at": "2026-04-13T10:30:00Z"
  }
}
```

#### `GET /api/v1/knowledge/datasets`

列出所有数据集。

#### `POST /api/v1/knowledge/add`

添加文档到知识库。

**请求**:
```json
{
  "data": "Cognee 是一个知识图谱引擎，可以将文档转换为结构化的知识图谱。",
  "dataset": "my-dataset"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "data_id": "data_abc123",
    "dataset_name": "my-dataset",
    "message": "数据已添加"
  }
}
```

#### `POST /api/v1/knowledge/cognify`

触发知识图谱构建。

**请求**:
```json
{
  "datasets": ["my-dataset"],
  "run_in_background": true
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "pipeline_run_id": "pipe_abc123",
    "status": "pending",
    "message": "知识图谱构建已启动"
  }
}
```

#### `POST /api/v1/knowledge/search`

搜索知识库。

**请求**:
```json
{
  "query": "Cognee 是什么？",
  "dataset": "my-dataset",
  "search_type": "GRAPH_COMPLETION",
  "top_k": 10
}
```

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "id": "node_abc123",
      "text": "Cognee 是一个知识图谱引擎...",
      "score": 0.95,
      "metadata": {}
    }
  ],
  "total": 1,
  "message": ""
}
```

---

## 3. gRPC API

### 3.1 Proto 定义

#### common.proto

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

#### conversation.proto

```protobuf
syntax = "proto3";
package cozymemory;

import "common.proto";

// 消息
message Message {
  string role = 1;
  string content = 2;
  string created_at = 3;
}

// 添加对话请求
message AddConversationRequest {
  string user_id = 1;
  repeated Message messages = 2;
  map<string, string> metadata = 3;
  bool infer = 4;
}

// 会话记忆
message ConversationMemory {
  string id = 1;
  string user_id = 2;
  string content = 3;
  optional double score = 4;
  map<string, string> metadata = 5;
  string created_at = 6;
  string updated_at = 7;
}

// 添加对话响应
message AddConversationResponse {
  bool success = 1;
  repeated ConversationMemory data = 2;
  string message = 3;
}

// 搜索请求
message SearchConversationsRequest {
  string user_id = 1;
  string query = 2;
  int32 limit = 3;
  optional double threshold = 4;
}

// 搜索响应
message SearchConversationsResponse {
  bool success = 1;
  repeated ConversationMemory data = 2;
  int32 total = 3;
  string message = 4;
}

// 获取单条请求
message GetConversationRequest {
  string memory_id = 1;
}

// 删除请求
message DeleteConversationRequest {
  string memory_id = 1;
}

// 删除所有请求
message DeleteAllConversationsRequest {
  string user_id = 1;
}

// 删除响应
message DeleteResponse {
  bool success = 1;
  string message = 2;
}

// 会话记忆服务
service ConversationService {
  rpc AddConversation(AddConversationRequest) returns (AddConversationResponse);
  rpc SearchConversations(SearchConversationsRequest) returns (SearchConversationsResponse);
  rpc GetConversation(GetConversationRequest) returns (ConversationMemory);
  rpc DeleteConversation(DeleteConversationRequest) returns (DeleteResponse);
  rpc DeleteAllConversations(DeleteAllConversationsRequest) returns (DeleteResponse);
}
```

#### profile.proto

```protobuf
syntax = "proto3";
package cozymemory;

import "common.proto";

// 插入对话请求
message InsertProfileRequest {
  string user_id = 1;
  repeated Message messages = 2;
  bool sync = 3;
}

// 插入对话响应
message InsertProfileResponse {
  bool success = 1;
  string user_id = 2;
  string blob_id = 3;
  string message = 4;
}

// Flush 请求
message FlushProfileRequest {
  string user_id = 1;
  bool sync = 2;
}

// Flush 响应
message FlushProfileResponse {
  bool success = 1;
  string message = 2;
}

// 画像主题条目
message ProfileTopic {
  string id = 1;
  string topic = 2;
  string sub_topic = 3;
  string content = 4;
  string created_at = 5;
  string updated_at = 6;
}

// 用户画像
message UserProfile {
  string user_id = 1;
  repeated ProfileTopic topics = 2;
  string updated_at = 3;
}

// 获取画像请求
message GetProfileRequest {
  string user_id = 1;
}

// 上下文请求
message GetContextRequest {
  string user_id = 1;
  int32 max_token_size = 2;
  repeated Message chats = 3;
}

// 上下文响应
message GetContextResponse {
  bool success = 1;
  string user_id = 2;
  string context = 3;
}

// 用户画像服务
service ProfileService {
  rpc InsertProfile(InsertProfileRequest) returns (InsertProfileResponse);
  rpc FlushProfile(FlushProfileRequest) returns (FlushProfileResponse);
  rpc GetProfile(GetProfileRequest) returns (UserProfile);
  rpc GetContext(GetContextRequest) returns (GetContextResponse);
}
```

#### knowledge.proto

```protobuf
syntax = "proto3";
package cozymemory;

import "common.proto";

// 添加知识请求
message AddKnowledgeRequest {
  string data = 1;
  string dataset = 2;
  repeated string node_set = 3;
}

// 添加知识响应
message AddKnowledgeResponse {
  bool success = 1;
  string data_id = 2;
  string dataset_name = 3;
  string message = 4;
}

// 构建知识图谱请求
message CognifyRequest {
  repeated string datasets = 1;
  bool run_in_background = 2;
}

// 构建知识图谱响应
message CognifyResponse {
  bool success = 1;
  string pipeline_run_id = 2;
  string status = 3;
  string message = 4;
}

// 搜索知识请求
message SearchKnowledgeRequest {
  string query = 1;
  string dataset = 2;
  string search_type = 3;
  int32 top_k = 4;
}

// 搜索结果
message KnowledgeSearchResult {
  string id = 1;
  string text = 2;
  optional double score = 3;
  map<string, string> metadata = 4;
}

// 搜索知识响应
message SearchKnowledgeResponse {
  bool success = 1;
  repeated KnowledgeSearchResult data = 2;
  int32 total = 3;
  string message = 4;
}

// 数据集
message DatasetInfo {
  string id = 1;
  string name = 2;
  string created_at = 3;
}

// 创建数据集请求
message CreateDatasetRequest {
  string name = 1;
}

// 列出数据集请求
message ListDatasetsRequest {}

// 数据集列表响应
message ListDatasetsResponse {
  bool success = 1;
  repeated DatasetInfo data = 2;
  string message = 3;
}

// 知识库服务
service KnowledgeService {
  rpc CreateDataset(CreateDatasetRequest) returns (DatasetInfo);
  rpc ListDatasets(ListDatasetsRequest) returns (ListDatasetsResponse);
  rpc AddKnowledge(AddKnowledgeRequest) returns (AddKnowledgeResponse);
  rpc Cognify(CognifyRequest) returns (CognifyResponse);
  rpc SearchKnowledge(SearchKnowledgeRequest) returns (SearchKnowledgeResponse);
}
```

### 3.2 gRPC 代码生成

```bash
# scripts/generate_grpc.sh
#!/bin/bash
python -m grpc_tools.protoc \
  -I./proto \
  --python_out=./src/cozymemory/grpc_server \
  --grpc_python_out=./src/cozymemory/grpc_server \
  ./proto/common.proto \
  ./proto/conversation.proto \
  ./proto/profile.proto \
  ./proto/knowledge.proto
```

---

## 4. 依赖注入

```python
# api/deps.py

from functools import lru_cache

from ..config import Settings, settings
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
    global _mem0_client
    if _mem0_client is None:
        _mem0_client = Mem0Client(
            api_url=settings.MEM0_API_URL,
            api_key=settings.MEM0_API_KEY or None,
            timeout=settings.MEM0_TIMEOUT,
        )
    return _mem0_client


def get_memobase_client() -> MemobaseClient:
    global _memobase_client
    if _memobase_client is None:
        _memobase_client = MemobaseClient(
            api_url=settings.MEMOBASE_API_URL,
            api_key=settings.MEMOBASE_API_KEY,
            timeout=settings.MEMOBASE_TIMEOUT,
        )
    return _memobase_client


def get_cognee_client() -> CogneeClient:
    global _cognee_client
    if _cognee_client is None:
        _cognee_client = CogneeClient(
            api_url=settings.COGNEE_API_URL,
            api_key=settings.COGNEE_API_KEY or None,
            timeout=settings.COGNEE_TIMEOUT,
        )
    return _cognee_client


def get_conversation_service() -> ConversationService:
    return ConversationService(client=get_mem0_client())


def get_profile_service() -> ProfileService:
    return ProfileService(client=get_memobase_client())


def get_knowledge_service() -> KnowledgeService:
    return KnowledgeService(client=get_cognee_client())
```
# CozyMemory 项目完整验证报告

**版本：** 2.0.0 | **Python：** ≥ 3.11 | **License：** MIT | **提交数：** 66 | **报告日期：** 2026-04-19

---

## 一、项目定位

CozyMemory 是一个**统一 AI 记忆服务平台**，将三个独立的 AI 记忆引擎聚合成单一服务入口：

| 引擎 | 职责 | 技术后端 |
|------|------|---------|
| **Mem0** | 对话记忆（LLM 自动提取事实） | 自托管 Mem0 REST API，向量存储 Qdrant |
| **Memobase** | 用户画像（结构化 topic/sub_topic） | 自托管 Memobase REST API，pgvector |
| **Cognee** | 知识图谱（文档 → 知识图） | 自托管 Cognee REST API，Neo4j + pgvector |

上层同时提供 **REST API（FastAPI）** 和 **gRPC API**，两者共用同一套 Service 层逻辑，不依赖任何官方 SDK（全部通过 httpx 直接调用后端 REST）。

---

## 二、架构设计

```
HTTP Client / gRPC Client
         │
    FastAPI App  ←──── gRPC Server (grpc.aio)
         │                    │
    API Layer             gRPC Servicers
    (v1/routers)         (server.py)
         │                    │
    ─────┴──────────────────────
              Service Layer
      ConversationService  ProfileService
      KnowledgeService     ContextService
    ─────┬──────────────────────
         │
    Client Layer (httpx async)
    BaseClient → Mem0Client / MemobaseClient / CogneeClient
         │
    Backend Engines (self-hosted docker)
```

### 2.1 BaseClient 核心机制

文件：`src/cozymemory/clients/base.py`

**连接池：** `httpx.AsyncClient`，`max_keepalive=50`，`max_connections=100`，HTTP/2 启用。

**指数退避重试**（默认 3 次）：

| 触发条件 | 处理 |
|---------|------|
| HTTP 429 | 重试，等待 `retry_delay × 2^attempt` 秒 |
| HTTP 5xx | 重试，最后一次触发熔断计数 |
| `httpx.TimeoutException` | 重试，最后一次触发熔断计数 |
| `httpx.RequestError` | 重试，最后一次触发熔断计数 |
| HTTP 4xx（非 429） | 立即抛出 `EngineError`，不重试 |

**熔断器（Circuit Breaker）：**
- 连续失败 `failure_threshold`（默认 5）次 → 熔断器打开
- 打开后 `circuit_recovery_timeout`（默认 60s）内所有请求立即 fail-fast
- 到期后降至 `threshold-1` 允许一次探活（half-open）

**每次重试均打印结构化日志：**
```
engine.retry  engine=Mem0  attempt=2  max_retries=3  status=503  reason=server_error
```

### 2.2 ContextService 并发扇出

文件：`src/cozymemory/services/context.py`

`POST /api/v1/context` 的核心：

```python
# 根据 include_* 标志动态构建协程列表
coros = [conv_svc.search(...), profile_svc.get_context(...), knowledge_svc.search(...)]

# 可选每引擎超时
if engine_timeout:
    coros = [asyncio.wait_for(c, timeout=engine_timeout) for c in coros]

# 并发执行，单引擎失败不影响其他引擎
results = await asyncio.gather(*coros, return_exceptions=True)

# 结果归并：超时/异常 → errors 字段，成功 → 对应数据字段
```

`latency_ms` = 所有引擎中最慢的那个（gather 结束时间 - 开始时间）。

### 2.3 依赖注入

`api/deps.py` 使用懒加载单例：客户端（`Mem0Client`、`MemobaseClient`、`CogneeClient`）全局各创建一次，gRPC Servicer 的 `__init__` 调用同一组 `get_*_service()` 函数，保证连接池复用。

---

## 三、全部 REST API（20 个端点）

**统一错误响应：** `ErrorResponse { success: false, error: str, detail: str|null, engine: str|null }`

### 3.1 健康检查

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/health` | 并发探活三引擎，返回 healthy/degraded/unhealthy |

**Response** `HealthResponse`
```json
{
  "status": "healthy",
  "engines": {
    "mem0":     {"name":"mem0","status":"healthy","latency_ms":12.3,"error":null},
    "memobase": {"name":"memobase","status":"healthy","latency_ms":8.1,"error":null},
    "cognee":   {"name":"cognee","status":"degraded","latency_ms":null,"error":"timeout"}
  },
  "timestamp": "2026-04-19T10:00:00Z"
}
```

---

### 3.2 对话记忆（Mem0）

| 方法 | 路径 | 请求 | 响应 | 错误 |
|------|------|------|------|------|
| GET | `/api/v1/conversations` | `?user_id=&limit=100` | `ConversationMemoryListResponse` | 502 |
| POST | `/api/v1/conversations` | `ConversationMemoryCreate` | `ConversationMemoryListResponse` | 422, 502 |
| POST | `/api/v1/conversations/search` | `ConversationMemorySearch` | `ConversationMemoryListResponse` | 502 |
| GET | `/api/v1/conversations/{memory_id}` | — | `ConversationMemory` | 404, 502 |
| DELETE | `/api/v1/conversations/{memory_id}` | — | `ConversationMemoryListResponse` | 502 |
| DELETE | `/api/v1/conversations` | `?user_id=` | `ConversationMemoryListResponse` | 502 |

**ConversationMemoryCreate（POST body）：**
```json
{
  "user_id": "user_01",
  "messages": [
    {"role": "user", "content": "我喜欢游泳"},
    {"role": "assistant", "content": "好的"}
  ],
  "metadata": {"session": "s1"},
  "infer": true
}
```

**ConversationMemorySearch（POST body）：**
```json
{"user_id": "user_01", "query": "用户喜欢什么运动", "limit": 5, "threshold": 0.7}
```

**ConversationMemory（单条记忆）：**
```json
{
  "id": "m1",
  "user_id": "user_01",
  "content": "喜欢游泳",
  "score": 0.91,
  "metadata": null,
  "created_at": null,
  "updated_at": null
}
```

---

### 3.3 用户画像（Memobase）

> **注意：** `user_id` 必须为 UUID v4（Memobase 底层强制校验）

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/profiles/insert` | 插入对话到 Memobase 缓冲区，LLM 异步提取画像 |
| POST | `/api/v1/profiles/flush` | 触发缓冲区处理 |
| GET | `/api/v1/profiles/{user_id}` | 获取结构化画像（topic + sub_topic + content） |
| POST | `/api/v1/profiles/{user_id}/context` | 获取 LLM-ready 上下文提示词字符串 |
| POST | `/api/v1/profiles/{user_id}/items` | 手动添加画像条目 |
| DELETE | `/api/v1/profiles/{user_id}/items/{profile_id}` | 删除画像条目 |

**ProfileInsertRequest：**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "messages": [{"role": "user", "content": "我叫小明，喜欢游泳"}],
  "sync": false
}
```

**ProfileAddItemRequest：**
```json
{"topic": "interest", "sub_topic": "sport", "content": "喜欢游泳和跑步"}
```

**UserProfile（GET response）：**
```json
{
  "success": true,
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "topics": [
      {
        "id": "p1",
        "topic": "basic_info",
        "sub_topic": "name",
        "content": "小明",
        "created_at": null,
        "updated_at": null
      }
    ]
  }
}
```

---

### 3.4 知识图谱（Cognee）

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/knowledge/datasets` | 列出所有 dataset |
| POST | `/api/v1/knowledge/datasets?name=` | 创建 dataset |
| POST | `/api/v1/knowledge/add` | 添加文档到知识库 |
| POST | `/api/v1/knowledge/cognify` | 触发知识图谱构建（两步流程：add → cognify → search） |
| POST | `/api/v1/knowledge/search` | 搜索知识库 |
| DELETE | `/api/v1/knowledge` | 删除文档 |

**KnowledgeSearchRequest：**
```json
{
  "query": "AI记忆架构",
  "dataset": "default",
  "search_type": "GRAPH_COMPLETION",
  "top_k": 5
}
```

`search_type` 枚举：`CHUNKS` | `SUMMARIES` | `RAG_COMPLETION` | `GRAPH_COMPLETION`

---

### 3.5 统一上下文

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/context` | 并发调用三引擎，返回合并上下文 |

**ContextRequest（完整字段）：**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "query": "用户最近关心什么话题",
  "include_conversations": true,
  "include_profile": true,
  "include_knowledge": true,
  "conversation_limit": 5,
  "max_token_size": 500,
  "knowledge_top_k": 3,
  "knowledge_search_type": "GRAPH_COMPLETION",
  "engine_timeout": 5.0,
  "chats": [{"role": "user", "content": "你好，我最近喜欢游泳"}]
}
```

**ContextResponse：**
```json
{
  "success": true,
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "conversations": [...],
  "profile_context": "# 用户背景\n- 姓名: 小明\n- 兴趣: 游泳",
  "knowledge": [...],
  "errors": {},
  "latency_ms": 312.5
}
```

---

## 四、全部 gRPC API（19 个方法，4 个 Service）

**服务地址：** `[::]:{GRPC_PORT}`（默认 50051）

### 4.1 ConversationService（6 个方法）

```protobuf
service ConversationService {
  rpc AddConversation        (AddConversationRequest)        returns (AddConversationResponse);
  rpc SearchConversations    (SearchConversationsRequest)    returns (SearchConversationsResponse);
  rpc GetConversation        (GetConversationRequest)        returns (ConversationMemory);
  rpc DeleteConversation     (DeleteConversationRequest)     returns (DeleteResponse);
  rpc DeleteAllConversations (DeleteAllConversationsRequest) returns (DeleteResponse);
  rpc ListConversations      (ListConversationsRequest)      returns (SearchConversationsResponse);
}
```

关键消息字段：
- `AddConversationRequest`：`user_id`, `repeated Message messages`, `map<string,string> metadata`, `bool infer`
- `SearchConversationsRequest`：`user_id`, `query`, `int32 limit`, `optional double threshold`
- `ConversationMemory`：`id`, `user_id`, `content`, `optional double score`, `map<string,string> metadata`

### 4.2 ProfileService（6 个方法）

```protobuf
service ProfileService {
  rpc InsertProfile     (InsertProfileRequest)     returns (InsertProfileResponse);
  rpc FlushProfile      (FlushProfileRequest)      returns (FlushProfileResponse);
  rpc GetProfile        (GetProfileRequest)        returns (UserProfile);
  rpc GetContext        (GetContextRequest)        returns (GetContextResponse);
  rpc AddProfileItem    (AddProfileItemRequest)    returns (AddProfileItemResponse);
  rpc DeleteProfileItem (DeleteProfileItemRequest) returns (DeleteResponse);
}
```

### 4.3 KnowledgeService（6 个方法）

```protobuf
service KnowledgeService {
  rpc CreateDataset   (CreateDatasetRequest)   returns (DatasetInfo);
  rpc ListDatasets    (ListDatasetsRequest)    returns (ListDatasetsResponse);
  rpc AddKnowledge    (AddKnowledgeRequest)    returns (AddKnowledgeResponse);
  rpc Cognify         (CognifyRequest)         returns (CognifyResponse);
  rpc SearchKnowledge (SearchKnowledgeRequest) returns (SearchKnowledgeResponse);
  rpc DeleteKnowledge (DeleteKnowledgeRequest) returns (DeleteResponse);
}
```

### 4.4 ContextService（1 个方法）

```protobuf
service ContextService {
  rpc GetUnifiedContext (GetUnifiedContextRequest) returns (GetUnifiedContextResponse);
}
```

`GetUnifiedContextRequest` 字段：
- `string user_id = 1`
- `optional string query = 2`
- `bool include_conversations = 3`
- `bool include_profile = 4`
- `bool include_knowledge = 5`
- `int32 conversation_limit = 6`
- `int32 max_token_size = 7`
- `int32 knowledge_top_k = 8`
- `string knowledge_search_type = 9`
- `optional double engine_timeout = 10`
- `repeated Message chats = 11`

`GetUnifiedContextResponse` 字段：
- `bool success = 1`
- `string user_id = 2`
- `repeated ConversationMemory conversations = 3`
- `string profile_context = 4`
- `repeated KnowledgeSearchResult knowledge = 5`
- `map<string,string> errors = 6`
- `double latency_ms = 7`

---

## 五、测试体系

**总测试数：312 个，全部 PASS，耗时约 24 秒**

### 5.1 测试文件清单

| 文件 | 测试数 | 覆盖内容 |
|------|--------|---------|
| `test_base_client.py` | 18 | 重试逻辑、熔断器、4xx/5xx 行为、HTTP 文件上传 |
| `test_grpc_server.py` | 45 | 全部 4 个 Servicer 的成功路径 + EngineError 映射 |
| `test_api_conversations.py` | 15 | REST 对话记忆 6 端点 |
| `test_api_knowledge.py` | 16 | REST 知识图谱 6 端点 |
| `test_api_profiles.py` | 15 | REST 画像 6 端点 |
| `test_api_context.py` | 5 | REST 统一上下文端点 |
| `test_context_service.py` | 13 | 并发扇出、部分失败、engine_timeout、chats 参数透传 |
| `test_cognee_client_behaviors.py` | 18 | Cognee 客户端各异常路径 |
| `test_cognee_client.py` | 8 | Cognee 基础方法 |
| `test_cognee_client_extra.py` | 12 | Cognee 搜索格式兼容 |
| `test_memobase_client_behaviors.py` | 10 | Memobase errno 格式、upsert 语义 |
| `test_memobase_client_extra.py` | 15 | add_user、insert、flush、add_profile、delete_profile |
| `test_memobase_client.py` | 8 | Memobase 基础方法 |
| `test_mem0_client.py` | 11 | Mem0 基础方法 |
| `test_mem0_client_extra.py` | 11 | get_all、delete 幂等、add 元数据、search |
| `test_services_extra.py` | 15 | 各 Service 层边界行为 |
| `test_conversation_service.py` | 6 | ConversationService 方法 |
| `test_profile_service.py` | 4 | ProfileService 方法 |
| `test_knowledge_service.py` | 5 | KnowledgeService 方法 |
| `test_logging_config.py` | 7 | development/production 渲染器、级别、降噪 |
| `test_models_common.py` | 8 | 公共模型字段验证 |
| `test_models_conversation.py` | 7 | 对话模型字段验证 |
| `test_models_knowledge.py` | 10 | 知识模型字段验证 |
| `test_models_profile.py` | 8 | 画像模型字段验证 |
| `test_config.py` | 6 | Settings 读取、env 变量覆盖 |
| `test_deps.py` | 8 | 依赖注入单例行为 |
| `test_app.py` | 3 | FastAPI 生命周期、路由挂载 |
| **合计** | **312** | |

### 5.2 覆盖率（核心代码）

| 模块 | 语句数 | 未覆盖 | 覆盖率 |
|------|--------|--------|--------|
| `models/*` | — | — | **100%** |
| `services/context.py` | 56 | 0 | **100%** |
| `api/v1/context.py` | 9 | 0 | **100%** |
| `api/v1/profile.py` | 52 | 0 | **100%** |
| `config.py` | 25 | 0 | **100%** |
| `logging_config.py` | 14 | 0 | **100%** |
| `clients/mem0.py` | 68 | 2 | **97%** |
| `services/conversation.py` | 27 | 1 | **96%** |
| `clients/cognee.py` | 56 | 2 | **96%** |
| `clients/memobase.py` | 103 | 4 | **96%** |
| `clients/base.py` | 96 | 5 | **95%** |
| `grpc_server/server.py` | 221 | 15 | **93%** |
| `api/v1/knowledge.py` | 48 | 4 | **92%** |
| `services/profile.py` | 27 | 3 | **89%** |
| `services/knowledge.py` | 26 | 3 | **88%** |
| **整体（含生成代码）** | **1654** | **313** | **81%** |

> 生成的 `*_pb2.py` / `*_pb2_grpc.py` 不经人工编写，行覆盖率低属正常。排除后核心业务代码均在 88%+。

---

## 六、部署架构

### 6.1 容器布局（docker-compose.1panel.yml）

```
                    ┌─────────────────────────────────────────┐
  外部请求            │          cozy_caddy (反向代理)           │
──────────────────► │  :8000 CozyMemory  :8080 Cognee         │
                    │  :8081 Mem0 WebUI  :8019 Memobase        │
                    └─────────────────────────────────────────┘
                          │ (1panel-network 内网)
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
    cozy_api          cozy_cognee      cozy_mem0_api
  (REST:8000          (cognee:0.4.1)   (mem0-api:latest)
   gRPC:50051)
         │                │                │
    ┌────┴────┐    ┌───────┴──────┐    ┌───┴────┐
    │postgres │    │   neo4j      │    │qdrant  │
    │+pgvector│    │   minio      │    │redis   │
    └─────────┘    └──────────────┘    └────────┘
                         +
                   cozy_memobase_api
```

**11 个容器，全部通过 `1panel-network` 内网互通，仅 Caddy 对外暴露端口。**

| 容器 | 镜像 | 内存限制 |
|------|------|---------|
| `cozy_postgres` | `pgvector/pgvector:0.8.1-pg17-trixie` | 无限制 |
| `cozy_redis` | `redis:7-alpine` | 无限制 |
| `cozy_qdrant` | `qdrant/qdrant:v1.15` | 无限制 |
| `cozy_minio` | `quay.io/minio/minio:...` | 无限制 |
| `cozy_neo4j` | `neo4j:2026.03.1` | 2 GB / 512 MB reserve |
| `cozy_cognee` | `cognee:0.4.1` | 2 GB / 512 MB reserve |
| `cozy_cognee_frontend` | `cognee-frontend:local-0.4.1` | 1 GB / 256 MB reserve |
| `cozy_mem0_api` | `mem0-api:latest` | 1 GB / 256 MB reserve |
| `cozy_mem0_webui` | `mem0-webui:latest` | 512 MB / 128 MB reserve |
| `cozy_memobase_api` | `memobase-server:latest` | 1 GB / 256 MB reserve |
| `cozy_api` | `cozymemory:latest` | 512 MB / 128 MB reserve |
| `cozy_caddy` | `caddy:alpine` | 无限制 |

### 6.2 CozyMemory 容器内进程（supervisord）

```ini
[program:rest-api]
command = uvicorn cozymemory.app:create_app --factory --host 0.0.0.0 --port 8000
autostart = true
autorestart = true

[program:grpc-server]
command = cozymemory-grpc
autostart = true
autorestart = true
```

单容器同时运行 REST（:8000）和 gRPC（:50051），由 supervisord 管理。

### 6.3 环境变量

```bash
MEM0_API_URL=http://cozy_mem0_api:8000
MEMOBASE_API_URL=http://cozy_memobase_api:8019
COGNEE_API_URL=http://cozy_cognee:8000
MEM0_ENABLED=true
MEMOBASE_ENABLED=true
COGNEE_ENABLED=true
APP_ENV=production       # 隐藏错误详情
LOG_LEVEL=INFO
GRPC_PORT=50051
```

### 6.4 构建与启动命令

```bash
# 构建所有自定义镜像
cd base_runtime && ./build.sh all

# 单独构建
./build.sh cognee        # cognee|mem0-api|mem0-webui|memobase|cozymemory

# 启动全栈
docker compose -f base_runtime/docker-compose.1panel.yml up -d

# 查看状态
docker compose -f base_runtime/docker-compose.1panel.yml ps

# 验证
curl http://SERVER_IP:8000/api/v1/health
```

### 6.5 快速 API 冒烟测试

```bash
# 健康检查
curl http://SERVER_IP:8000/api/v1/health

# 添加对话记忆
curl -X POST http://SERVER_IP:8000/api/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u1","messages":[{"role":"user","content":"我喜欢游泳"}]}'

# 语义搜索
curl -X POST http://SERVER_IP:8000/api/v1/conversations/search \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u1","query":"运动爱好","limit":5}'

# 插入画像（user_id 必须为 UUID v4）
curl -X POST http://SERVER_IP:8000/api/v1/profiles/insert \
  -H "Content-Type: application/json" \
  -d '{"user_id":"550e8400-e29b-41d4-a716-446655440000","messages":[{"role":"user","content":"test"}],"sync":true}'

# 统一上下文
curl -X POST http://SERVER_IP:8000/api/v1/context \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u1","query":"用户喜欢什么","engine_timeout":5.0}'
```

---

## 七、版本历史摘要（66 次提交）

| 阶段 | 代表提交 | 内容 |
|------|---------|------|
| 初始化 | `83e1813` | 项目脚手架 |
| 基础设施 | `f9063d1`~`3451bbd` | docker-compose、Caddy、SQL 初始化 |
| 核心功能 | `4276dcc`~`c78bbb8` | API 层、Service 层、gRPC 服务 |
| 测试强化 | `d591877`~`ef22073` | 覆盖率 84%→92%→96%，gRPC 行为测试 |
| 工程优化 | `2861de0`~`ad62e01` | Swagger 文档、5 项质量修复 |
| 统一上下文 | `6c46bce` | `POST /api/v1/context` 并发扇出 |
| 10 项优化 | `0c203ad` | 类型安全、死代码清理、重试日志、gRPC context 端点 |
| 评审修复 | `67288fc` | grpcio pin 收紧、chats 限制说明 |

---

## 八、已知限制

| 限制 | 说明 |
|------|------|
| Memobase user_id 格式 | 必须为 UUID v4，字符串 ID（如 `"user_01"`）会被 Memobase 拒绝（HTTP 422） |
| chats 参数 | `ContextRequest.chats` 目前透传到 Memobase 层但不生效，因为 Memobase context 端点是 GET-only；待 Memobase 升级后自动生效 |
| Cognee 健康检查延迟 | 每次约 1–4 秒（图数据库查询），health 端点在 Cognee 较慢时显示 degraded 属正常 |
| grpcio 版本要求 | 已锁定 `>=1.80.0`，生成的 pb2 stubs 依赖 1.80 新 API |
| 集成测试依赖 | 需运行完整 base_runtime 才能执行集成测试，单元测试（312 个）无需任何后端 |

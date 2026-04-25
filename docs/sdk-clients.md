# CozyMemory SDK 与客户端

**版本**: 0.2.0  
**更新**: 2026-04-25

---

## 概览

CozyMemory 有两层客户端：

1. **公开 SDK**（面向外部开发者）：Python / JS/TS 包，通过 REST API 集成 CozyMemory
2. **内部 Client**（服务层内部）：httpx 异步客户端，CozyMemory API 服务端与三引擎后端的通信层

---

## 公开 SDK

### Python SDK

**安装**

```bash
pip install cozymemory
```

**基本用法**

```python
from cozymemory import CozyMemoryClient

with CozyMemoryClient(api_key="cozy_live_xxx", base_url="http://localhost:8000") as c:
    # 对话记忆
    c.conversations.add("alice", [{"role": "user", "content": "I love hiking"}])
    memories = c.conversations.list("alice")
    results = c.conversations.search("alice", "outdoor activity")
    c.conversations.delete("memory-id")
    c.conversations.delete_all("alice")

    # 用户画像
    c.profiles.insert("alice", [{"role": "user", "content": "I'm an engineer"}])
    c.profiles.flush("alice")
    profile = c.profiles.get("alice")
    context = c.profiles.context("alice")
    c.profiles.add_item("alice", topic="interest", sub_topic="hobby", content="reading")
    c.profiles.delete_item("alice", "profile-id")

    # 知识图谱
    datasets = c.knowledge.datasets()
    c.knowledge.add("long document text...", dataset="my-dataset")
    c.knowledge.cognify(datasets=["my-dataset"])
    results = c.knowledge.search("query", dataset="my-dataset", search_type="GRAPH_COMPLETION")

    # 统一上下文
    ctx = c.context.get_unified("alice", query="outdoor activity")
```

**异步用法**

```python
from cozymemory import AsyncCozyMemoryClient

async with AsyncCozyMemoryClient(api_key="cozy_live_xxx") as c:
    await c.conversations.add("alice", [{"role": "user", "content": "hello"}])
```

**错误处理**

| 异常类 | 场景 |
|--------|------|
| `CozyMemoryError` | 所有错误的基类 |
| `APIError` | HTTP 4xx/5xx 响应 |
| `AuthError` | 401 未授权 |

**源码位置**：`sdks/python/`

详细文档见 [sdks/python/README.md](../sdks/python/README.md)

---

### JS/TS SDK

**安装**

```bash
npm install @cozymemory/sdk
```

**基本用法**

```typescript
import { CozyMemory } from '@cozymemory/sdk';

const client = new CozyMemory({
  apiKey: 'cozy_live_xxx',
  baseUrl: 'http://localhost:8000',
});

// 对话记忆
await client.conversations.add('alice', [{ role: 'user', content: 'I love hiking' }]);
const memories = await client.conversations.list('alice');
const results = await client.conversations.search('alice', 'outdoor activity');

// 用户画像
await client.profiles.insert('alice', [{ role: 'user', content: "I'm an engineer" }]);
const profile = await client.profiles.get('alice');
const context = await client.profiles.context('alice');

// 知识图谱
const datasets = await client.knowledge.datasets();
await client.knowledge.add('document text', 'my-dataset');
await client.knowledge.cognify(['my-dataset']);
const searchResults = await client.knowledge.search('query', {
  dataset: 'my-dataset',
  searchType: 'GRAPH_COMPLETION',
});

// 统一上下文
const ctx = await client.context.getUnified('alice', { query: 'outdoor activity' });
```

**错误处理**

```typescript
import { CozyMemoryError, APIError, AuthError } from '@cozymemory/sdk';

try {
  await client.conversations.list('alice');
} catch (e) {
  if (e instanceof AuthError) {
    // API key 无效或过期
  } else if (e instanceof APIError) {
    console.log(e.status, e.message);
  }
}
```

**导出类型**

`HealthResponse`, `Memory`, `MemoryListResponse`, `SearchOptions`, `ProfileItem`, `ProfileResponse`, `ContextResponse`, `Dataset`, `SearchResult`, `CognifyResponse`

**源码位置**：`sdks/js/`

详细文档见 [sdks/js/README.md](../sdks/js/README.md)

---

## 内部 Client 层

CozyMemory 服务层通过 httpx 异步客户端与三引擎后端通信。

### 架构

```
Service (业务逻辑)
  → Client (BaseClient 子类)
    → httpx.AsyncClient
      → 引擎后端 HTTP API
```

### BaseClient

所有引擎客户端的基类，提供：

| 能力 | 说明 |
|------|------|
| **连接池** | httpx async connection pool，lifespan 关闭时释放 |
| **指数退避重试** | 5xx 和网络错误自动重试 |
| **断路器** | 连续失败超过 `failure_threshold` 后断开；4xx 不计入 |
| **超时** | 可配置的请求超时 |
| **错误标准化** | 引擎错误统一抛出 `EngineError(engine, status_code, detail)` |

### 引擎客户端

| Client | 引擎 | Auth Header | 关键特性 |
|--------|------|-------------|---------|
| `Mem0Client` | Mem0 | `X-API-Key` | `get()` 返回 None 而非 404；`add()` 解析 `results` 字段 |
| `MemobaseClient` | Memobase | `Authorization: Bearer` | 自动创建用户（upsert）；HTTP 200 + `errno` 错误模式 |
| `CogneeClient` | Cognee | `Authorization: Bearer` | 登录获取 token；两步 add→cognify 流程 |

### 依赖注入

`api/deps.py` 懒加载创建单例客户端，通过 FastAPI `Depends()` 注入：

```python
def get_conversation_service() -> ConversationService:
    return ConversationService(get_mem0_client())

def get_profile_service() -> ProfileService:
    return ProfileService(get_memobase_client())

def get_knowledge_service() -> KnowledgeService:
    return KnowledgeService(get_cognee_client())
```

gRPC servicer 也使用相同的依赖函数。`close_all_clients()` 在 lifespan shutdown 时释放连接池。

### 引擎 API 注意事项

详见 [CLAUDE.md](../CLAUDE.md) 的 "Engine API Quirks" 章节，包含每个引擎的非显而易见行为和陷阱。

---

## 对比

| 维度 | 公开 SDK | 内部 Client |
|------|---------|------------|
| **用户** | 外部开发者 | CozyMemory 服务层 |
| **通信** | REST API（经 Caddy） | 直连引擎后端（Docker 内网） |
| **鉴权** | App Key / Bootstrap Key | 引擎原生 API Key / Token |
| **数据隔离** | uuid5 App 级隔离 | 无隔离（直接操作引擎） |
| **安装** | `pip install` / `npm install` | 内置于 `src/cozymemory/clients/` |
| **错误处理** | `CozyMemoryError` 层次 | `EngineError` + 断路器 |

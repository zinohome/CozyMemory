# CozyMemory 数据模型

**版本**: 0.2.0  
**更新**: 2026-04-25

---

## 概览

CozyMemory 的数据分为两大类：

1. **平台模型**（PostgreSQL `cozymemory` 库）：多租户管理、鉴权、审计
2. **业务数据**（各引擎自有存储）：对话记忆、用户画像、知识图谱

```
Organization ──┬── Developer (JWT 登录)
               └── App ──┬── ApiKey (API 鉴权)
                         ├── ExternalUser (uuid5 映射)
                         ├── AppDataset (Cognee 数据集归属)
                         └── APIUsage (调用统计)
                              └── AuditLog (操作审计)
```

---

## 平台模型（SQLAlchemy 2.0）

### Organization

多租户顶层实体。Developer 注册时自动创建。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | UUID | PK, default=uuid4 | |
| `name` | String(200) | NOT NULL | 组织名称 |
| `slug` | String(64) | UNIQUE, NOT NULL | URL 安全标识（如 `my-company`） |
| `created_at` | DateTime(tz) | server_default=now() | |
| `updated_at` | DateTime(tz) | auto-update | |

**关系**：`developers` (cascade delete), `apps` (cascade delete)

### Developer

开发者账号，通过 JWT 登录管理 UI。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | UUID | PK, default=uuid4 | |
| `org_id` | UUID | FK→organizations, NOT NULL | 所属组织 |
| `email` | String(320) | UNIQUE, NOT NULL | 登录邮箱 |
| `password_hash` | String(255) | NOT NULL | bcrypt 哈希 |
| `name` | String(100) | default="" | 显示名 |
| `role` | String(20) | default="member" | `owner` / `admin` / `member` |
| `is_active` | Boolean | default=True | 账号状态 |
| `created_at` | DateTime(tz) | server_default=now() | |
| `last_login_at` | DateTime(tz) | nullable | 最近登录时间 |

**角色权限**：

| 操作 | owner | admin | member |
|------|-------|-------|--------|
| 查看 App / Key | ✅ | ✅ | ✅ |
| 创建 App / Key | ✅ | ✅ | ❌ |
| 更新 App / Key | ✅ | ✅ | ❌ |
| 删除 App / Key | ✅ | ❌ | ❌ |
| 管理 Organization | ✅ | ❌ | ❌ |

### App

应用实体，数据隔离的基本单位。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | UUID | PK, default=uuid4 | |
| `org_id` | UUID | FK→organizations, NOT NULL | 所属组织 |
| `name` | String(200) | NOT NULL | 应用名称 |
| `slug` | String(64) | NOT NULL | URL 安全标识，org 内唯一 |
| `namespace_id` | UUID | default=uuid4, NOT NULL | uuid5 计算命名空间（不可变） |
| `description` | Text | default="" | |
| `created_at` | DateTime(tz) | server_default=now() | |

**唯一约束**：`(org_id, slug)`

**关系**：`api_keys` (cascade delete), `external_users` (cascade delete)

### ApiKey

App 级 API 密钥，用于 SDK / 第三方集成。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | UUID | PK, default=uuid4 | |
| `app_id` | UUID | FK→apps, NOT NULL | 所属 App |
| `name` | String(100) | NOT NULL | 描述名 |
| `key_hash` | String(64) | UNIQUE, NOT NULL | SHA-256 hex |
| `prefix` | String(20) | NOT NULL | 显示前缀（如 `cozy_live_abc12`） |
| `environment` | String(20) | default="live" | `live`（生产）/ `test`（沙箱） |
| `disabled` | Boolean | default=False | 是否禁用 |
| `created_at` | DateTime(tz) | server_default=now() | |
| `last_used_at` | DateTime(tz) | nullable | 最近使用时间 |
| `expires_at` | DateTime(tz) | nullable | 过期时间 |

**索引**：`ix_api_keys_hash`（快速查找）, `ix_api_keys_app`

**安全**：明文 Key 仅在创建 / 轮转时返回一次，数据库只存 SHA-256 哈希。

### ExternalUser

App 外部用户到引擎内部 UUID 的确定性映射。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `internal_uuid` | UUID | PK | `uuid5(App.namespace_id, external_user_id)` |
| `app_id` | UUID | FK→apps, NOT NULL | 所属 App |
| `external_user_id` | String(255) | NOT NULL | 业务侧用户 ID（如 `alice`） |
| `created_at` | DateTime(tz) | server_default=now() | |

**唯一约束**：`(app_id, external_user_id)`

**设计原理**：Memobase 要求 UUID v4 格式的 user_id。通过 `uuid5(namespace_id, external_user_id)` 实现确定性映射，同一个 `alice` 在不同 App 下映射为不同 UUID，实现数据隔离。

### AuditLog

操作审计日志。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | UUID | PK, default=uuid4 | |
| `actor_type` | String(20) | NOT NULL | `developer` / `api_key` / `system` |
| `actor_id` | String(64) | NOT NULL | 操作者 ID |
| `action` | String(100) | NOT NULL | 如 `app.created`、`api_key.rotated` |
| `target_type` | String(30) | nullable | 目标类型（`app`、`api_key`） |
| `target_id` | String(64) | nullable | 目标 ID |
| `app_id` | UUID | FK→apps, SET NULL | 关联 App |
| `meta` | JSONB | nullable | 操作元数据 |
| `ip_address` | String(45) | nullable | IPv4/v6 |
| `user_agent` | String(500) | nullable | |
| `created_at` | DateTime(tz) | server_default=now() | |

**索引**：`ix_audit_logs_app_time` (app_id, created_at), `ix_audit_logs_actor` (actor_type, actor_id)

**保留策略**：90 天（cron 定时清理）

### AppDataset

Cognee 数据集到 App 的归属映射。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `dataset_id` | UUID | PK | Cognee 数据集 ID |
| `app_id` | UUID | FK→apps, NOT NULL | 所属 App |
| `created_at` | DateTime(tz) | server_default=now() | |

**用途**：App Key 用户只能看到和操作自己 App 下的数据集。

### APIUsage

每请求 API 使用统计。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | UUID | PK, default=uuid4 | |
| `app_id` | UUID | FK→apps, NOT NULL | |
| `route` | String(100) | NOT NULL | 标准化路由键（如 `conversations.item`） |
| `method` | String(10) | NOT NULL | HTTP 方法 |
| `status_code` | Integer | NOT NULL | 响应状态码 |
| `duration_ms` | Float | NOT NULL | 请求耗时 |
| `created_at` | DateTime(tz) | server_default=now() | |

**索引**：`ix_api_usage_app_time`, `ix_api_usage_route`

---

## 业务数据模型（Pydantic v2）

业务数据通过三引擎存储，CozyMemory 使用 Pydantic 模型做请求/响应序列化。

### 通用类型

```python
class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str

class EngineStatus(BaseModel):
    name: str
    status: Literal["healthy", "unhealthy"]
    latency_ms: float
    error: str | None
```

### 对话记忆（Mem0）

```python
class ConversationMemory(BaseModel):
    id: str
    memory: str
    created_at: str | None
    updated_at: str | None
    metadata: dict | None

class ConversationMemoryCreate(BaseModel):
    user_id: str
    messages: list[Message]
    metadata: dict | None = None
    infer: bool = True
    agent_id: str | None = None
    session_id: str | None = None

class ConversationMemorySearch(BaseModel):
    user_id: str
    query: str
    limit: int = 10
    threshold: float | None = None
```

### 用户画像（Memobase）

```python
class ProfileItem(BaseModel):
    id: str
    content: str
    attributes: dict  # {"topic": "...", "sub_topic": "..."}

class ProfileInsertRequest(BaseModel):
    user_id: str
    messages: list[Message]
    sync: bool = False

class ProfileAddItemRequest(BaseModel):
    user_id: str
    topic: str
    sub_topic: str
    content: str
```

### 知识图谱（Cognee）

```python
class KnowledgeAddRequest(BaseModel):
    data: str
    dataset: str

class KnowledgeSearchRequest(BaseModel):
    query: str
    dataset: str
    search_type: SearchType  # "CHUNKS" | "SUMMARIES" | "RAG_COMPLETION" | "GRAPH_COMPLETION"
    top_k: int = 5

class KnowledgeCognifyRequest(BaseModel):
    datasets: list[str] | None = None
    run_in_background: bool = True
```

### 统一上下文

```python
class ContextRequest(BaseModel):
    user_id: str
    query: str | None = None
    max_token_size: int | None = None

class ContextResponse(BaseModel):
    conversations: list[dict]
    profiles: str | None
    knowledge: list[dict]
    errors: dict[str, str]
```

---

## 存储分布

| 数据 | 存储位置 | 说明 |
|------|---------|------|
| 平台模型 | PostgreSQL `cozymemory` 库 | Alembic 迁移管理 |
| Mem0 对话记忆 | Qdrant 向量 + SQLite 历史 | |
| Memobase 用户画像 | PostgreSQL `memobase` 库 | |
| Cognee 知识图谱 | Neo4j 图 + PostgreSQL + MinIO | |
| 用户 ID 映射 | Redis DB 2 | Operator 用的旧映射 |
| 外部用户映射 | PostgreSQL `external_users` 表 | App 级确定性 uuid5 |
| API 指标 | Prometheus TSDB | 30 天保留 |

---

## 数据库迁移

使用 Alembic 管理 `cozymemory` 库的 schema 变更。详见 [migration-guide.md](migration-guide.md)。

```bash
alembic upgrade head      # 升级到最新
alembic downgrade -1      # 回退一步
alembic history           # 查看迁移历史
```

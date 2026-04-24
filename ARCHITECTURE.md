# CozyMemory Architecture

> 现状总结，截至 Step 8.18（2026-04-24）。用于新人 / 新会话快速理解整体结构。
> 历史版本见 `docs/architecture.md`（2026-04-13，单租户早期设计）。

## 1. 产品定位

CozyMemory 是一个 **多租户 AI 记忆平台 SaaS**：把三个专业记忆引擎（Mem0 对话记忆 / Memobase 用户画像 / Cognee 知识图谱）聚合成一套统一 API，面向需要给 LLM 应用加"长期记忆 + 个性化"的客户 app。

**两类使用者**：

- **Developer**（SaaS 客户的工程师）：在我们的 Dashboard 注册 → 建 Organization → 建 App → 发 API Key → 嵌到自家客户端 app 里
- **Operator**（平台 ops / 我们自己）：跨 org 运维、排障、全局数据审计

**一个 App 的数据在平台内完全隔离**：`internal_uuid = uuid5(app.namespace_id, external_user_id)`。同样的 `alice` 在 App A 和 App B 是两个完全独立的内部用户。

## 2. 系统拓扑

```
客户端 app (toC 终端用户)
   │
   │ X-Cozy-API-Key: cozy_live_...
   ▼
┌──────────────────────────────────────────────────────┐
│ Caddy (:80 :8000 :8080 :8081 :8019 :8088 :3001)     │
└──────────────────────────────────────────────────────┘
   ▼                                                 ▼
┌─────────────────────┐              ┌────────────────────┐
│ cozymemory-api      │              │ cozymemory-ui      │
│ - REST :8000        │              │ Next.js 16 admin   │
│ - gRPC :50051       │              │ Developer + Operator│
│ (supervisord 单容器)│              └────────────────────┘
└─────────────────────┘
   ▼
┌──────────────────────────────────────────────────────┐
│ Service layer (Conversation/Profile/Knowledge/Context)│
│   ↓                                                  │
│ Client layer (Mem0Client / MemobaseClient / CogneeClient)│
└──────────────────────────────────────────────────────┘
   ▼
┌──────────────────────────────────────────────────────┐
│ 底层引擎 (都是 HTTP 服务)                              │
│   mem0-api :8888    memobase :8019    cognee :8000   │
└──────────────────────────────────────────────────────┘
   ▼
┌──────────────────────────────────────────────────────┐
│ 数据存储                                              │
│   postgres (cozymemory + pgvector + cognee)          │
│   redis (缓存)                                        │
│   qdrant (向量)                                       │
│   neo4j (图)                                          │
│   minio (对象存储)                                    │
└──────────────────────────────────────────────────────┘
```

## 3. 代码布局

```
src/cozymemory/
├── app.py                     # FastAPI 组装 + 中间件链
├── api/
│   ├── deps.py                # 服务层 DI
│   └── v1/                    # REST 路由
│       ├── auth.py            # register / login / me / change-password
│       ├── dashboard.py       # apps CRUD + org + developers + usage
│       ├── api_keys.py        # apps/{id}/keys CRUD
│       ├── dashboard_users.py # apps/{id}/users (external_user 映射)
│       ├── conversation.py    # 业务：对话记忆
│       ├── profile.py         # 业务：画像
│       ├── context.py         # 业务：统一上下文
│       ├── knowledge.py       # 业务：知识库
│       └── operator/          # bootstrap-only 运维路由
│           ├── orgs.py        # 所有 org 总览
│           ├── users_mapping.py  # 老 Mem0 Redis uid 映射
│           └── backup.py      # 全局备份
├── auth/
│   ├── jwt.py                 # pyjwt HS256
│   ├── password.py            # bcrypt 直连（弃 passlib）
│   ├── app_context.py         # get_app_context + scope_user_id
│   └── deps.py                # get_current_developer / require_role
├── clients/                   # BaseClient + Mem0/Memobase/Cognee 子类
├── services/
│   ├── conversation.py        # 业务封装
│   ├── profile.py
│   ├── context.py             # asyncio.gather 并发三引擎
│   ├── knowledge.py
│   ├── api_key_store.py       # PG 动态 key 存取（sha256 hash）
│   ├── user_resolver.py       # uuid5(ns, ext_id) + PG 索引 + Redis 缓存
│   └── dataset_registry.py    # Knowledge 的 App↔Dataset 归属
├── db/
│   ├── engine.py              # async SQLAlchemy 2.0
│   └── models.py              # 8 个表
├── grpc_server/
│   ├── server.py              # 19 个 servicer 方法
│   ├── auth_interceptor.py    # 鉴权 + usage 拦截器
│   ├── app_ctx.py             # ContextVar + scope_user_id_grpc
│   └── *_pb2*.py              # 生成的 proto 代码
└── config.py                  # pydantic-settings

ui/                            # Next.js 16 + React 19 Dashboard
sdks/
├── python/                    # cozymemory (PyPI 命名)
└── js/                        # @cozymemory/sdk (npm 命名)
base_runtime/
├── docker-compose.1panel.yml  # 11 服务全家桶
├── Caddyfile
└── build.sh                   # 镜像构建脚本
alembic/                       # 迁移
proto/                         # gRPC 定义
```

## 4. 多租户数据模型

PostgreSQL 8 张平台表（业务数据归三引擎各自后端）：

```
organizations ─┬─ developers (用户/owner)
               │
               └─ apps ──┬── api_keys    (sha256 hash 存，明文只在创建时返回一次)
                        │
                        ├── external_users  (app_id × ext_id → internal_uuid)
                        │
                        ├── app_datasets   (Knowledge dataset 归属)
                        │
                        └── api_usage      (业务调用日志，7 天窗口 aggregate)

audit_logs (独立表，记 developer 的管理动作)
```

**关键约束**：
- `apps (org_id, slug) UNIQUE` —— 一个 org 内 app slug 唯一
- `external_users (app_id, external_user_id) UNIQUE` —— 上游 UPSERT 幂等
- `ExternalUser.internal_uuid = uuid5(app.namespace_id, external_user_id)` —— 确定性，Redis 丢了也能重算

## 5. 鉴权模型（三条路并行）

```python
# src/cozymemory/app.py 的 require_api_key 中间件
if X-Cozy-API-Key in settings.api_keys_set:      # bootstrap (env)
    → 全放行，admin 视角，scope_user_id 透传
elif X-Cozy-API-Key = 动态 App Key:              # 客户 app
    → verify_and_touch(sha256) → inject app_id → scope_user_id 走 uuid5
elif Authorization: Bearer <JWT>:                # Developer UI
    → decode → 查 Developer → 检查 X-Cozy-App-Id 归属该 org
    → inject app_id → 业务路由 scope_user_id 走 uuid5
    → 调 /operator/* → 拒（401）
else:
    → 401
```

业务路由（`/conversations` `/profiles` `/context` `/knowledge`）规则：
- Bearer **必须**带 `X-Cozy-App-Id`，否则 401
- 防止"Dashboard 无 AppId 轮询污染 external_users"的坑

gRPC（`auth_interceptor.py`）对齐同样语义，metadata 里读 `x-cozy-api-key`，鉴权失败 → `UNAUTHENTICATED`。

## 6. 请求流（典型）

**客户 app 写一条对话并拉 LLM 上下文**：

```
客户 app
  │
  ├── POST /api/v1/conversations            (X-Cozy-API-Key: cozy_live_xxx)
  │   ↓ middleware: verify_and_touch → request.state.app_id = X
  │   ↓ route: scope_user_id(X, "alice") → uuid5(ns_X, "alice") = U_alice
  │   ↓ service.add(user_id=U_alice, messages=[...])
  │   ↓ Mem0Client.add(U_alice, ...)
  │   ├── api_usage 写一行 (tap middleware)
  │   └── 200 {success: true, data: []}
  │
  └── POST /api/v1/context                  (同 key)
      ↓ scope_user_id → U_alice
      ↓ ContextService asyncio.gather(
           mem0.search(U_alice, "..."),
           memobase.context(U_alice),
           cognee.search("...", dataset in app_datasets[X]),
        )
      └── 合并后返回统一 prompt 素材
```

三引擎并发 → 总延迟 ≈ max(三者)，不是 sum。

## 7. 前端

Next.js 16 App Router，两套独立 layout：

```
ui/src/app/
├── (app)/                     # Developer JWT 登录后
│   ├── layout.tsx             # AuthGuard + 统一 AppSidebar（context-aware）
│   ├── home/                  # 跨 App 统计卡
│   ├── apps/                  # App 列表
│   │   └── [id]/              # App 工作台（sidebar 自动展开 8 子项）
│   │       ├── page.tsx       # 概览 + IntegrationQuickstart + UsageCard
│   │       ├── keys/          # API Key CRUD + 一次性明文显示
│   │       ├── users/         # External users 列表 + GDPR 删除
│   │       ├── memory/        # 对话记忆浏览
│   │       ├── profiles/      # 用户画像
│   │       ├── knowledge/     # 知识库（per-App dataset）
│   │       ├── context/       # 上下文调试
│   │       └── playground/    # 沙盒
│   └── settings/              # 账号 + 组织 + 成员
├── (auth)/                    # 公开：登录/注册
└── operator/                  # Operator 独立入口
    ├── page.tsx               # landing（key gate）+ dashboard
    ├── orgs/                  # 跨 org 总览
    ├── users-mapping/         # 老 Mem0 Redis uid
    ├── memory-raw/            # 全局记忆浏览
    ├── profiles-raw/
    ├── knowledge-raw/
    ├── backup/
    ├── health/                # 引擎延迟图（MetricsPoller 仅在 operator 下运行）
    └── settings/              # legacy bootstrap keys 面板
```

状态管理：
- Zustand（persist）：`jwt` / `currentAppId` / `sidebarWidth` / `locale` → localStorage
- Zustand（session）：`operatorKey` → **sessionStorage**（关浏览器即丢，避免高权限 key 长留）
- TanStack Query：服务端状态（apps / users / usage / members / orgs）
- Fetch helpers：
  - `apiFetch({ scoped })` —— Developer 业务调用（Bearer + 可选 AppId）
  - `dashboardFetch` —— Developer 管理调用（Bearer, 无 AppId）
  - `operatorFetch` —— Operator 调用（X-Cozy-API-Key = operatorKey）

## 8. SDK

- `sdks/python/` —— `cozymemory`（PyPI 名），httpx 同步+异步，4 资源类
- `sdks/js/` —— `@cozymemory/sdk`（npm 名），TypeScript + 原生 fetch
- 都封 `X-Cozy-API-Key` header，暴露 `conversations / profiles / knowledge / context` 资源
- `AuthError` / `APIError` / `CozyMemoryError` 三级错误
- 示例代码内嵌在 Dashboard 的 App 概览页（IntegrationQuickstart 组件）

## 9. 部署

`base_runtime/docker-compose.1panel.yml` 一套启动 11 个服务：

| 容器 | 角色 | 镜像来源 |
|---|---|---|
| cozymemory | REST :8000 + gRPC :50051 | 本仓 `Dockerfile` |
| cozymemory-ui | Next.js dashboard | 本仓 `ui/Dockerfile` |
| caddy | 反向代理 | `caddy:alpine` |
| cozy_postgres | 主库 + pgvector | `pgvector/pgvector:0.8.1-pg17` |
| cozy_redis | 缓存 | `redis:7-alpine` |
| cozy_qdrant | Mem0 向量 | `qdrant/qdrant:v1.15` |
| cozy_minio | 对象存储 | `minio` |
| cozy_neo4j | Cognee 图 | `neo4j:2026.03.1` |
| cognee / cognee-frontend | 知识图谱引擎 | 本仓 sibling 项目 |
| mem0-api / mem0-webui | 对话记忆引擎 | sibling 项目 |
| memobase-server-api | 用户画像引擎 | sibling 项目 |
| prometheus + grafana | 观测 | 官方镜像 |

数据库迁移走 Alembic（`alembic/versions/`）。本地开发有独立 `cozymemory_test` 库避免 pytest 清数据（Step 8.13）。

## 10. 观测

- **Prometheus**（`:9090`）scrape `cozymemory` 的 `/metrics`
- **Grafana**（`:3001`）dashboards
- **Structlog** 结构化日志，每条带 `request_id / method / path`（via `contextvars`）
- **api_usage 表**：per-App 请求级日志，7 天窗口聚合，Dashboard 概览页 `UsageCard` 消费

## 11. 当前不做 / 留坑

- **RBAC**：org 内只有 `owner` vs 未来的 `admin / member`，当前所有 dev 等权
- **邀请**：没有成员邀请流程；多人协作靠各自注册同 slug 的 org（会冲突）
- **邮箱验证**：register 不发 email
- **配额 / 速率限制**：api_usage 有数据但没执行限制
- **SDK 发布**：两个 SDK 在仓内未发布到 PyPI / npm
- **老全局数据**：pre-Phase-2 的 Mem0 user_id 池不属于任何 App，只对 Operator 可见，不自动迁移

---

## 12. 关键抽象 cheat sheet

- **`scope_user_id(app_ctx, external_user_id)`**（`auth/app_context.py`）: Phase 2 多租户的关卡，App Key → uuid5 / bootstrap → 原样。业务路由统一走它。
- **`UserResolver.resolve(app, ext_id)`**：uuid5 计算 + PG upsert + Redis TTL 缓存。
- **`AppDatasetRegistry`**：Knowledge 的 (app_id, dataset_id) 一对一归属，`filter_datasets_for_app` / `ensure_owned` / `register_dataset_for_app` 是 router 三板斧。
- **`AuthUsageInterceptor`**（gRPC）：单拦截器同时处理鉴权 + usage 落盘。
- **`buildAuthHeaders(scoped)`**（`ui/src/lib/api.ts`）：所有手写 fetch 必须走它，不然会在 JWT-only 模式下漏 header。

## 13. 版本历史脚注

- Phase 1（Step 0-5）：单租户引擎聚合
- Phase 2（Step 1-18）：多租户 / Dashboard / SDK
- 当前进度：**Phase 2 完成**，进入功能增强（邀请、配额、计费）待启动

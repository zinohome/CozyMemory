# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-04-24

多租户 SaaS 化 + 安全审计 + 发布就绪。

### Added — 多租户 SaaS 架构（Phase 2）
- **账号体系**：Organization → Developer → App → ApiKey 四级模型（PostgreSQL + Alembic）
- **双角色模型**：Developer（JWT 登录，管理自己 org 下的 App/Key）+ Operator（bootstrap key，跨 org 运维）
- **JWT 鉴权**：开发者注册/登录 API，Bearer token + `X-Cozy-App-Id` 联合鉴权
- **App Key 动态管理**：从 Redis 迁移到 PostgreSQL，关联到 App，支持 CRUD + 审计日志
- **数据隔离**：`uuid5(app_namespace, external_user_id)` 透明映射，业务路由强制 per-App scope
- **Knowledge per-App 归属**：`app_datasets` 关联表 + Alembic 迁移
- **per-App API 用量统计**：`api_usage` 表 + 滑动窗口聚合
- **External Users 管理**：分页列表 + GDPR 删除（级联清理 Mem0/Memobase/Redis 映射）
- **gRPC 多租户**：鉴权拦截器 + App 隔离 + 用量计数

### Added — Developer Dashboard UI（Next.js 16）
- **(auth) 路由**：`/login` → `/register` → `/apps` 登录注册流程，AuthGuard 守卫
- **Apps 管理**：列表 + 创建 + 详情 + AppSwitcher + UserMenu
- **App 工作台**：`/apps/[id]/*` 含 memory / profiles / knowledge / context / playground 子页
- **Keys 管理**：App 详情页内 Key CRUD + `ApiKeyCreatedDialog` 一次性展示
- **External Users 页**：分页 + GDPR 删除
- **UX 重构**：统一 sidebar + 角色专属 home 页 + 可拖拽宽度

### Added — Operator 管理 UI
- **独立入口**：`/operator`（手动输 key，`sessionStorage` 保存）
- **Operator 子页**：orgs / users-mapping / memory-raw / profiles-raw / knowledge-raw / backup / health / settings
- **operatorFetch**：`sessionStorage` 中的 key 自动附加到请求

### Added — UI 增强（batch 1–7）
- `ConfirmDialog` 替换浏览器原生 `confirm()`
- 全站 toast 通知（sonner），约 20 处错误/成功路径
- 乐观删除（Memory Lab / User Profiles / Knowledge Base）
- Playground 会话持久化（Zustand persist，最多 20 会话）
- Sparkline hover tooltip（值 + 相对时间 + 虚线导引）
- 键盘快捷键（Gmail 风格 `g x` 序列导航 + `?` 帮助 Dialog）
- `EmptyState` 复用组件，帮新用户发现下一步动作
- i18n 基建 + 全站中文翻译（~200 keys）+ `<LanguageToggle />`
- `docs/usage-cn.md` 338 行中文使用说明
- Knowledge 文件上传 + Documents tab（preview/download/delete）

### Added — 可观测性
- Prometheus + Grafana 可观测性基础（batch 16）
- 自定义指标：`cozy_engine_up` / `cozy_engine_latency_ms` / `cozy_engine_request_duration_seconds` / `cozy_engine_request_errors_total` / `cozy_app_requests_total`
- Prometheus 告警规则：EngineDown / HighLatency / HighErrorRate / APIDown
- OpenTelemetry 可选接入（`pip install .[otel]`，`OTEL_ENABLED=true` 启用）

### Added — SDK
- **Python SDK** (`cozymemory` on PyPI)：sync + async client，4 resource classes，完整 API 参考文档
- **JS/TS SDK** (`@cozymemory/sdk` on npm)：native fetch，全类型导出，ESM-only
- SDK 发布 CI/CD（`publish-sdks.yml`，`sdk-v*` tag 触发）

### Added — CI/CD
- GitHub Actions：lint + unit tests + coverage（`--cov-fail-under=70`）
- `pip-audit` 安全扫描
- Self-hosted deploy job：build → tag → force-recreate → health check → rollback on failure
- 部署后自动集成测试（REST + gRPC）
- SHA-tagged image 保留（最近 5 个）

### Added — 部署 & 运维
- K8s 部署示例（`deploy/k8s/`：Deployment + Service + Secret）
- Docker 日志配置（`json-file` 50m×5，全 15 服务统一）
- Database migration 操作指南（`docs/migration-guide.md`）

### Fixed — 安全审计（15 项）
- **Critical**：`memory_id` GET/DELETE 加 App 归属校验（REST + gRPC），防跨租户读取
- **Critical**：gRPC TLS 终止（Caddy `localhost:50051` + `tls internal`）
- **High**：gRPC health service（`grpc.health.v1.Health`）
- **High**：Prometheus 指标按引擎/App 维度拆分
- **Medium**：JWT_SECRET 生产启动校验（默认值 → RuntimeError）
- **Medium**：Redis 滑动窗口速率限制（per-App，`RATE_LIMIT_PER_MINUTE`）
- **Medium**：`/metrics` 端点对外返回 404（Caddy 内网直抓）
- **Medium**：UI cookie 加 `Secure` 标志
- **Medium**：UI 加 CSP / X-Content-Type-Options / X-Frame-Options 响应头
- **Low**：JS SDK 全类型化（消除 `<unknown>`）
- **Low**：SDK CHANGELOG + `.env.example` 同步

### Fixed — UI 修复
- A11y：axe-core 扫描 9 页，修复全部 critical/serious 问题
- 性能：`MemoryRow` / `ProfileItemRow` 包 `React.memo` + `useCallback`
- 响应式：375px 视口溢出修复，Dashboard stats cards 标准三段布局
- AuthGuard Zustand persist hydration 竞态修复

### Changed — 发布就绪
- 版本号统一为 `importlib.metadata` 单一来源（消除 4 处不一致）
- Docker-compose 硬编码密码全部模板化到 `.env`（`init.sql` → `init.sh`）
- License 从 MIT 改为 AGPL-3.0-or-later
- CORS `CORS_ALLOWED_ORIGINS` 变量化（默认 `*`，生产可限制）
- 依赖版本加上限（20 个 Python 依赖）

### Infrastructure
- Python 3.11+，FastAPI，httpx，pydantic v2，structlog，SQLAlchemy 2.0，Alembic
- Next.js 16，React 19，TanStack Query v5，Zustand，@base-ui/react + shadcn + Tailwind v4
- PostgreSQL + pgvector / Redis / Qdrant / Neo4j + APOC + GDS / MinIO / Caddy
- 524 单元测试 + 69 集成测试（50 REST + 19 gRPC），全通过

## [0.1.0] - 2026-04-21

首个公开预发布。统一 AI 记忆服务平台的最小可用版本。

### Added — 三引擎整合
- REST API（FastAPI）+ gRPC 双接口，涵盖 Mem0 对话记忆、Memobase 画像、Cognee 知识图谱
- `/context` 并发编排三引擎，单引擎失败不阻塞整体响应
- 透明 user_id → UUID v4 映射（Redis 持久化），屏蔽 Memobase 的 UUID 强约束

### Added — 管理 UI（Next.js 16 / React 19）
- **Dashboard**：三引擎健康 + 用户/数据集计数 + 10m/1h/6h 可切换的延迟/增长 sparkline
- **Memory Lab**：Mem0 记忆浏览/搜索/删除
- **User Profiles**：Memobase 画像读取 + LLM context prompt + topic 增删
- **Knowledge Base**：Cognee 数据集 CRUD + add + cognify + 图检索 + 交互式力导向图可视化
- **Context Studio**：跨引擎并发上下文查看 + 错误降级
- **Playground**：SSE 流式聊天，自动调 /context 增强 system prompt
- **Users**：Redis user_id ↔ UUID 映射 CRUD
- **Backup**：每用户 JSON 备份/恢复
- **Settings**：API key 管理 + 审计日志

### Added — 鉴权 / 安全
- 两层 API Key 模型：bootstrap key + dynamic key
- `X-Cozy-API-Key` header 鉴权

### Added — 运维
- `base_runtime/build.sh all` 一键构建 7 个自定义镜像
- `docker-compose.1panel.yml` 部署 14 个容器
- 329 单元测试 + 50 REST 集成测试

### Fixed — 首轮部署契约错位
- UI `engines` 从 array 改 dict
- Memobase `add_profile` 自动创建不存在的 user
- Cognee frontend Caddy `header_up Host localhost:3000` 解决 Next.js 16 跨源警告

[0.2.0]: https://github.com/zinohome/CozyMemory/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/zinohome/CozyMemory/releases/tag/v0.1.0

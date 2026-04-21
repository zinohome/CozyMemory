# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added — UX polish batch 5
- 新增复用组件 `components/empty-state.tsx`（icon + title + description
  + 可选 CTA link/onClick）替换 Memory Lab / User Profiles / Playground
  三页的灰色单行空态提示，帮新用户发现下一步动作
- Dark mode 审核：Dashboard / Knowledge / Playground 三页实测无 bug，
  CSS 变量（`bg-background` / `text-foreground`）已完整覆盖 — 无需改动

### Fixed — Responsive breakpoint sweep (batch 4)
- 375px 视口下 /knowledge 水平溢出 20px：长 dataset 名 `truncate` +
  多处 flex 容器加 `min-w-0`，消除溢出
- Dashboard stats cards 特殊的 `col-span-2` 布局改为标准三段响应式
  （mobile 堆叠 / tablet 2 列 / desktop 3 列）
- Engine Health card title 加 `truncate` + badge 加 `shrink-0` 防挤压
- AppLayout `flex-1 p-6` → `flex-1 p-4 sm:p-6 min-w-0`，mobile 减少
  padding + 允许 grid 正确收缩

### Added — UI enhancement batch 3
- Playground 会话持久化（`lib/playground-sessions-store.ts`）：
  Zustand persist 存最多 20 会话到 localStorage，页面顶部加会话下拉、
  New chat、Delete session；title 从首条 user message 自动截取
- Sparkline hover tooltip：`components/sparkline.tsx` 接受
  `timestamps[]` + `formatValue` prop，鼠标悬停显示值和相对时间
  （如 "22ms · 30s ago"）+ 虚线导引 + 点高亮。Dashboard 5 条 sparkline
  启用
- 键盘快捷键（`lib/use-hotkeys.ts`、`components/hotkeys-provider.tsx`）：
  Gmail 风格 `g x` 序列导航 9 条路由，`?` 打开帮助 Dialog；聚焦
  input/textarea 时自动禁用

### Added — UI enhancement batch 2
- Next.js App Router 错误边界：`app/error.tsx`（路由段兜底）+
  `app/global-error.tsx`（根级兜底），开发环境显示错误细节
- Server API Keys 面板抽出为独立组件 `components/server-api-keys-panel.tsx`，
  Settings 页从 577 行瘦到 136 行
- Context inspector 抽出为独立组件 `components/context-inspector.tsx`，
  Playground 页从 547 行瘦到 467 行
- Backup 的 export/import 迁移到 TanStack Query `useMutation`，
  自动 isPending/onError 钩子
- icon-only 按钮补齐 aria-label（Knowledge 的 delete/refresh/create、
  Memory/Profile/Users 的 trash、user-selector pick），满足屏幕阅读器
  和 a11y 审计

### Added — UI enhancement batch 1
- `ConfirmDialog` component（Radix Dialog）替换浏览器原生 `confirm()`；
  Settings 里的 rotate/delete key 以及 Knowledge Base 的删除 dataset
  现在弹自定义对话框
- 全站 toast 通知（sonner）：Settings、Backup、Memory Lab、User Profiles、
  Knowledge Base、Playground 约 20 处错误/成功路径替换为顶部右侧 toast
- 乐观删除：Memory Lab 记忆、User Profiles topic、Knowledge Base
  dataset 的删除在 UI 上立即生效，失败回滚 + toast 提示
- Knowledge Base 数据集名称过滤框，按输入实时缩减列表

## [0.1.0] - 2026-04-21

首个公开预发布。统一 AI 记忆服务平台的最小可用版本。

### Added — 三引擎整合
- REST API（FastAPI）+ gRPC 双接口，涵盖 Mem0 对话记忆、Memobase 画像、Cognee 知识图谱
- `/context` 并发编排三引擎，单引擎失败不阻塞整体响应
- 透明 user_id → UUID v4 映射（Redis 持久化），屏蔽 Memobase 的 UUID 强约束

### Added — 管理 UI（Next.js 16 / React 19）
- **Dashboard**：三引擎健康 + 用户/数据集计数 + 10m/1h/6h 可切换的延迟/增长 sparkline（客户端环形缓冲 + localStorage 持久化）
- **Memory Lab**：Mem0 记忆浏览/搜索/删除
- **User Profiles**：Memobase 画像读取 + LLM context prompt + topic 增删
- **Knowledge Base**：Cognee 数据集 CRUD + add + cognify + 图检索 + 交互式力导向图可视化（按类型过滤 + 节点点击详情）
- **Context Studio**：跨引擎并发上下文查看 + 错误降级
- **Playground**：SSE 流式聊天，自动调 /context 增强 system prompt，对话写回 Mem0；可自定义 system prompt / model / temperature / max_tokens
- **Users**：Redis user_id ↔ UUID 映射 CRUD
- **Backup**：每用户 JSON 备份/恢复（Mem0 + Memobase + 可选 Cognee 数据集）
- **Settings**：Client API key 持久化 + 服务端动态 key CRUD + 审计日志查看

### Added — 鉴权 / 安全
- 两层 API Key 模型：bootstrap key（env，管理员）+ dynamic key（Redis，可 CRUD）
- `X-Cozy-API-Key` header 鉴权，`/health`、`/docs`、`/openapi.json` 免鉴权
- API key 使用审计日志（Redis LPUSH + LTRIM，保留最近 200 条 per key）
- 所有敏感配置模板化到 `.env`，`.env.example` 提供填充指引

### Added — 可观测性
- 客户端轮询器 `MetricsPoller` 10s 采集，跨导航持续累积
- SVG 零依赖 sparkline（null 值断开避免与零延迟混淆）
- 窗口过滤器 10m/1h/6h 切换

### Added — 运维
- `base_runtime/build.sh all` 一键构建 7 个自定义镜像
- `docker-compose.1panel.yml` 部署 14 个容器（4 基础设施 + 3 引擎 + 3 引擎 UI + CozyMemory API + UI + Caddy）
- 集成测试 session 级 teardown，自动清理 grpc-/test- 前缀的 dataset 和 user 映射
- UI 层 `ui/src/lib/api-types.ts` 由 `npm run gen:api` 自动从后端 `/openapi.json` 生成，防契约漂移

### Fixed — 首轮部署发现的契约错位
- UI `engines` 从 array 改 dict，`EngineStatus.name` 代替 `engine`
- `ConversationMemory.content` 代替 `memory`
- `ProfileResponse` / `ProfileContextResponse` 添加 `data` 包装层
- `memory_scope` 从 `short_term/long_term/both` 改 `short/long/both`
- `ContextRequest` 字段 `enable_*` 改 `include_*`、`top_k` 改 `knowledge_top_k`、`timeout_ms` 改 `engine_timeout`
- Memobase `add_profile` 自动创建不存在的 user（复用 insert 里的 FK-retry 模式）
- Cognee frontend：Dockerfile 修 Linux 大小写敏感导致的 `Logo/` → `logo/` 目录引用失败
- Cognee frontend：Caddy `header_up Host localhost:3000` 解决 Next.js 16 跨源警告阻塞 HMR
- Cognee frontend：注入 `NEXT_PUBLIC_LOCAL_API_URL` 让浏览器 fetch 指向真实 server IP
- Mem0 server：`filters={}` 包裹 entity identifiers，适配 mem0ai 库 API

### Known issues
- 知识图谱备份恢复依赖 Cognee 重新 cognify，生成的实体/边与源可能略有差异（DocumentChunk 文本保真，图结构非）
- gRPC 集成测试（`test_grpc_integration.py`）未纳入 CI 流程
- 无 CI workflow，测试需手动运行
- `projects/Cozy*` 非真正 git submodule，patch 应用通过 `build.sh` 构建上下文完成

### Infrastructure
- Python 3.11+，FastAPI，httpx，pydantic v2，structlog
- Next.js 16，React 19，TanStack Query v5，Zustand，@base-ui/react + shadcn + Tailwind v4
- PostgreSQL + pgvector / Redis / Qdrant / Neo4j + APOC + GDS / MinIO / Caddy
- 329 单元测试 + 50 REST 集成测试，全通过

[0.1.0]: https://github.com/zinohome/CozyMemory/releases/tag/v0.1.0

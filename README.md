# CozyMemory

[![CI](https://github.com/zinohome/CozyMemory/actions/workflows/ci.yml/badge.svg)](https://github.com/zinohome/CozyMemory/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**统一 AI 记忆服务平台** — 单一 API 整合三大记忆引擎，开箱即用的管理 UI 和 Playground。

**中文使用说明**：[docs/usage-cn.md](docs/usage-cn.md)

| 引擎 | 域 | 能力 |
|------|----|------|
| [**Mem0**](https://github.com/mem0ai/mem0) | 对话记忆 | 从对话自动提取事实，语义搜索 |
| [**Memobase**](https://github.com/memodb-io/memobase) | 用户画像 | 结构化存储偏好/背景，生成 LLM context prompt |
| [**Cognee**](https://github.com/topoteretes/cognee) | 知识图谱 | 文档 → 实体/关系图 → 图检索 |

CozyMemory 把这三者整合为一个 REST + gRPC API，前置 Next.js 管理 UI，并自带鉴权、审计、备份、观测。

---

## 快速开始

### 一键部署（Docker Compose）

```bash
git clone --recurse-submodules https://github.com/zinohome/CozyMemory.git
cd CozyMemory

# 替换 docker-compose 里的 YOUR_SERVER_IP 和 LLM_API_KEY
vi base_runtime/docker-compose.1panel.yml

# 构建 7 个自定义镜像（约 25-30 分钟）
sudo ./base_runtime/build.sh all

# 启动全部 14 个容器
sudo docker compose -f base_runtime/docker-compose.1panel.yml up -d

# 等待 ~60 秒，验证
curl http://localhost:8000/api/v1/health
```

访问：
- **管理 UI**：http://localhost:8088
- **API Swagger**：http://localhost:8000/docs
- **单独子 UI**：8080 (Cognee) / 8081 (Mem0) / 8019 (Memobase)

### 环境要求

- Linux (x86_64 / arm64) + Docker 24+
- 内存 8GB+，磁盘 20GB+
- 外部 LLM（OpenAI 兼容 API，默认走 `caddy:9090` 代理到 `oneapi.naivehero.top`）

---

## 架构

```
┌───────────────────────────────────────────────────────────────────┐
│  Caddy :80/:8000/:8080/:8081/:8019/:8088  统一反向代理 + LLM 代理 :9090 │
└───────────────────────────────────────────────────────────────────┘
         ↓                     ↓                    ↓
┌────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│ CozyMemory UI  │ ← │  CozyMemory API  │ → │ Mem0 / Memobase  │
│ :8088 (Next16) │   │  :8000 REST      │   │ / Cognee 后端    │
│                │   │  :50051 gRPC     │   │                  │
└────────────────┘   └──────────────────┘   └──────────────────┘
                              ↓
             ┌────────────────┴────────────────┐
             ↓                                 ↓
        ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐
        │Postgres│   │ Redis  │   │ Qdrant │   │ Neo4j  │
        │pgvector│   │ 用户id │   │ mem0   │   │ cognee │
        └────────┘   │ 映射   │   │ 向量   │   │ 图谱   │
                     └────────┘   └────────┘   └────────┘
                                        ↓
                                   ┌────────┐
                                   │ MinIO  │
                                   │ S3 兼容 │
                                   └────────┘
```

所有 14 个容器通过 `1panel-network` 连通；对外只暴露 6 个端口（80/8000/8080/8081/8019/8088）。

---

## REST API 速览

全部 `/api/v1/*` 端点，统一响应 `{success, data, message}`。完整 schema 见 `/openapi.json` 或 `/docs`。

### 健康 / 上下文
```bash
GET  /health                          # 三引擎健康检查
POST /context                         # 并发融合三引擎返回 LLM 上下文
```

### Mem0 对话记忆
```bash
GET    /conversations?user_id=        # 列出用户记忆
POST   /conversations                 # 添加对话，自动提取事实
POST   /conversations/search          # 语义搜索
DELETE /conversations/{id}
```

### Memobase 画像
```bash
POST /profiles/insert                 # 插入对话到 buffer
POST /profiles/flush                  # 触发 LLM 处理
GET  /profiles/{user_id}              # 读结构化画像
POST /profiles/{user_id}/context      # 生成 LLM prompt
POST /profiles/{user_id}/items        # 手动添加 topic
```

### Cognee 知识图谱
```bash
GET    /knowledge/datasets            # 数据集列表
POST   /knowledge/add                 # 添加文档
POST   /knowledge/cognify             # 构建图谱（异步）
POST   /knowledge/search              # 图检索
GET    /knowledge/datasets/{id}/graph # 图数据（nodes+edges）
```

### 备份 / 管理
```bash
GET    /backup/export/{user_id}?datasets=...  # 导出 JSON bundle
POST   /backup/import                         # 恢复
GET    /admin/api-keys                        # 列 key（需 bootstrap key）
POST   /admin/api-keys                        # 创建
POST   /admin/api-keys/{id}/rotate            # 轮换
GET    /admin/api-keys/{id}/logs              # 审计日志
```

---

## SDKs

客户端 SDK，REST API 的薄封装。拿到 `cozy_live_...` key 即可上手。

- **Python**：`sdks/python/`（包名 `cozymemory`）— 同时提供 `CozyMemoryClient`（同步）和 `CozyMemoryAsyncClient`（异步 httpx）。
- **TypeScript / JS**：`sdks/js/`（包名 `@cozymemory/sdk`）— 基于原生 `fetch`，Node 18+ / 浏览器通用，ESM。

每个 SDK 有 `README.md` + `examples/quickstart.*` 可直接参考。

---

## UI 功能一览

访问 http://localhost:8088，首次要在 **Settings** 里填 bootstrap API key。

| 页面 | 功能 |
|------|------|
| **Dashboard** | 三引擎健康 + 用户/数据集计数 + 10m/1h/6h 可切换的延迟/增长 sparkline 趋势图 |
| **Memory Lab** | 浏览/搜索/删除单用户 Mem0 记忆 |
| **User Profiles** | 读画像、看 LLM context prompt、手动增删 topic |
| **Knowledge Base** | 数据集 CRUD + add + cognify + 图检索 + 交互式力导向图可视化（按节点类型过滤 + 点击查看属性） |
| **Context Studio** | 跨三引擎并发拉 context，带错误降级 |
| **Playground** | 聊天 UI，自动调 /context 增强 system prompt，SSE 流式 LLM 回复，自定义 system prompt/model/temperature/max_tokens，对话写回 Mem0 |
| **Users** | Redis user_id ↔ UUID 映射管理 |
| **Backup** | 每用户 JSON 备份/恢复（Mem0 记忆 + Memobase topics + 可选 Cognee 数据集） |
| **Settings** | Client API key + 服务端动态 key CRUD（创建/重命名/轮换/禁用/删除） + 审计日志查看 |

---

## 配置

### 必改（`base_runtime/docker-compose.1panel.yml`）
- `YOUR_SERVER_IP` → 服务器实际 IP（影响浏览器端和跨容器通信）
- `LLM_API_KEY` → OpenAI 兼容 key（cognee 和 mem0-api、cozymemory 各有一份）
- `COZY_API_KEYS` → 逗号分隔的 bootstrap key（留空 = 关闭鉴权）

### 可选
- `MEMOBASE_LLM_BASE_URL` / `MEMOBASE_EMBEDDING_BASE_URL` — Memobase 自己的 LLM
- PostgreSQL / Redis / MinIO / Neo4j 密码和 volume 路径

### 鉴权（两层模型）
1. **Bootstrap key**（env `COZY_API_KEYS`）— 管理员凭证，唯一能访问 `/api/v1/admin/*`
2. **Dynamic key**（Redis 存储）— 用户在 Settings 页创建的日常凭证，仅调业务接口

所有请求 header：`X-Cozy-API-Key: <key>`。`/api/v1/health` 和 `/docs` 豁免鉴权。

---

## 开发

### 后端
```bash
pip install -e ".[dev]"
uvicorn cozymemory.app:create_app --factory --host 0.0.0.0 --port 8000

# 单元测试
pytest tests/unit/ -v                     # 329 tests，无后端依赖

# 集成测试（需运行中的 base_runtime）
COZY_TEST_URL=http://localhost:8000 COZY_TEST_API_KEY=cozy-dev-key-001 \
  pytest tests/integration/ -v            # 50 tests

# Lint / 类型
ruff check src/ tests/
mypy src/cozymemory --ignore-missing-imports

# 生成 gRPC stub
./scripts/generate_grpc.sh
```

### 前端（`ui/`）
```bash
cd ui
npm install
npm run dev                # port 3000

# 从后端 openapi 自动生成 TS 类型（改后端 Pydantic 后跑）
npm run gen:api            # 读 http://localhost:8000/openapi.json

# 类型检查
npx tsc --noEmit
```

### 重建单个镜像
```bash
sudo ./base_runtime/build.sh cozymemory-ui    # 只重建 UI
sudo ./base_runtime/build.sh cognee           # 只重建 Cognee
sudo docker compose -f base_runtime/docker-compose.1panel.yml \
  up -d --force-recreate cozymemory-ui
```

---

## 项目结构

```
CozyMemory/
├── src/cozymemory/          # 后端 Python 包
│   ├── api/v1/              # REST 路由
│   ├── clients/             # Mem0/Memobase/Cognee HTTP 客户端
│   ├── services/            # 业务逻辑层
│   ├── grpc_server/         # gRPC 实现
│   └── models/              # Pydantic 模型
├── ui/                      # Next.js 16 管理界面
│   └── src/
│       ├── app/(app)/       # 9 个页面
│       ├── components/      # shadcn + 自定义组件
│       └── lib/
│           ├── api.ts       # 手写 API 客户端包装
│           └── api-types.ts # 自动生成，勿手改
├── base_runtime/            # Docker 部署
│   ├── docker-compose.1panel.yml
│   ├── build.sh             # 一键构建 7 镜像
│   └── Caddyfile
├── projects/                # 上游项目 submodules + patch
│   ├── CozyCognee/          # Cognee + 前端 patch
│   ├── CozyMem0/            # Mem0 + 前端 patch
│   └── CozyMemobase/        # Memobase patch
├── tests/
│   ├── unit/                # 329 个单元测试
│   └── integration/         # 50 个集成测试
├── proto/                   # gRPC 定义
└── CLAUDE.md                # 给 AI 协作的深度笔记
```

---

## 子项目

三个 `Cozy*` 子项目是对应上游的 fork，应用了必要的 patch：
- **CozyCognee** — Cognee 主体 + frontend Linux 大小写兼容性、Next.js 16 cross-origin 修复
- **CozyMem0** — 修 mem0ai 的 `filters={}` entity 参数传递
- **CozyMemobase** — 部署源码，给 Memobase 加 `wait_process` 支持

它们独立维护，修了会同步 push 到自己的 repo。

---

## 故障排查

| 症状 | 原因 | 解决 |
|------|------|------|
| Cognee `/search` 返回 `NoDataError` | 数据集没 cognify | 先 `POST /knowledge/cognify` 等 30-120s |
| Memobase `/profiles/{user_id}` 返回 422 | user_id 不是 UUID v4 | CozyMemory 服务层自动做字符串→UUID 映射，直接传任意字符串即可 |
| UI 页面全 401 | 浏览器没配 client key | Settings → Client API Key 里填 bootstrap key |
| Cognee health 慢（1-4s） | 要扫全库 datasets | 正常现象，非故障 |
| Dashboard Engine Health 空白 | `engines` dict key 是小写 `mem0` 非 `Mem0` | UI 已处理，升级最新版 |

---

## 测试 / 交付验证

从零部署的完整验证流程：

```bash
# 1. 停止 + 删镜像 + 清缓存
sudo docker compose -f base_runtime/docker-compose.1panel.yml down
sudo docker rmi cozymemory cozymemory-ui cognee:0.4.1 cognee-frontend:local-0.4.1 \
                mem0-api mem0-webui memobase-server
sudo docker builder prune -af

# 2. 重建 + 启动
sudo ./base_runtime/build.sh all
sudo docker compose -f base_runtime/docker-compose.1panel.yml up -d

# 3. 验证
curl http://localhost:8000/api/v1/health           # 三引擎 healthy
pytest tests/unit/ -q                               # 329 passed
COZY_TEST_URL=http://localhost:8000 pytest tests/integration/ -q \
  --ignore=tests/integration/test_grpc_integration.py   # 50 passed
```

---

## 文档

- **[CLAUDE.md](CLAUDE.md)** — 架构、约定、API 怪癖、给 AI 协作的深度笔记
- **[docs/](docs/)** — api-reference、architecture、data-models、deployment、sdk-clients
- **[base_runtime/](base_runtime/)** — 部署配置与 build 脚本
- **Swagger UI**：http://localhost:8000/docs
- **子项目仓库**：[CozyCognee](https://github.com/zinohome/CozyCognee)、[CozyMem0](https://github.com/zinohome/CozyMem0)、[CozyMemobase](https://github.com/zinohome/CozyMemobase)

---

## 许可

MIT

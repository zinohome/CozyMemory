# CozyMemory

[![CI](https://github.com/zinohome/CozyMemory/actions/workflows/ci.yml/badge.svg)](https://github.com/zinohome/CozyMemory/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)
[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

**统一 AI 记忆服务平台** — 单一 API 整合三大记忆引擎，开箱即用的管理 UI 和 Playground。

**中文使用说明**：[docs/usage-cn.md](docs/usage-cn.md)

| 引擎 | 域 | 能力 |
|------|----|------|
| [**Mem0**](https://github.com/mem0ai/mem0) | 对话记忆 | 从对话自动提取事实，语义搜索 |
| [**Memobase**](https://github.com/memodb-io/memobase) | 用户画像 | 结构化存储偏好/背景，生成 LLM context prompt |
| [**Cognee**](https://github.com/topoteretes/cognee) | 知识图谱 | 文档 → 实体/关系图 → 图检索 |

CozyMemory 把这三者整合为一个 REST + gRPC API，前置 Next.js 管理 UI，并自带多租户鉴权、审计、备份、观测。

---

## 快速开始

### 一键部署（Docker Compose）

```bash
git clone https://github.com/zinohome/CozyMemory.git
cd CozyMemory

# 配置环境变量
cp CozyMemory/.env.example CozyMemory/.env
vi CozyMemory/.env    # 必填：LLM_API_KEY, 各数据库密码, JWT_SECRET

# 替换 docker-compose 中的服务器 IP（5 处）
sed -i 's/192.168.32.40/你的服务器IP/g' CozyMemory/docker-compose.1panel.yml

# 构建 7 个自定义镜像（约 25-30 分钟）
sudo ./CozyMemory/build.sh all

# 启动全部 15 个容器
sudo docker compose -f CozyMemory/docker-compose.1panel.yml up -d

# 等待 ~60 秒，验证
curl http://localhost:8000/api/v1/health
```

访问：
- **管理 UI**：http://localhost:8088（Developer 登录 → `/login`；Operator → `/operator`）
- **API Swagger**：http://localhost:8000/docs
- **Grafana 监控**：http://localhost:3001
- **子引擎 UI**：8080 (Cognee) / 8081 (Mem0)

### 环境要求

- Linux (x86_64 / arm64) + Docker 24+
- 内存 8GB+，磁盘 20GB+
- 外部 LLM（OpenAI 兼容 API）

---

## 架构

```
┌──────────────────────────────────────────────────────────────────────┐
│  Caddy :80/:8000/:8080/:8081/:8019/:8088/:50051  反向代理 + LLM :9090 │
└──────────────────────────────────────────────────────────────────────┘
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
        │pgvector│   │ 映射+  │   │ mem0   │   │ cognee │
        └────────┘   │ 限流   │   │ 向量   │   │ 图谱   │
                     └────────┘   └────────┘   └────────┘
```

---

## 鉴权（双角色模型）

| 角色 | 入口 | 凭证 | 权限 |
|------|------|------|------|
| **Developer** | `/login` → `/apps` | JWT（注册/登录）| 管理自己 org 下的 App / Key / External Users；业务数据按 App 隔离 |
| **Operator** | `/operator` | Bootstrap key（env `COZY_API_KEYS`）| 跨 org 只读维护、全局设置 |

中间件按 header 分流：
- `X-Cozy-API-Key` = bootstrap key → 全放行
- `X-Cozy-API-Key` = App Key → 仅业务路由，自动注入 `app_id`
- `Authorization: Bearer <JWT>` → Developer Dashboard + 业务路由（需同时带 `X-Cozy-App-Id`）

`/health`、`/docs`、`/openapi.json` 免鉴权。

---

## REST API 速览

全部 `/api/v1/*` 端点，统一响应 `{success, data, message}`。完整 schema 见 `/docs`。

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
```

### Developer Dashboard
```bash
POST /auth/register                   # 开发者注册
POST /auth/login                      # JWT 登录
GET  /dashboard/apps                  # App 列表
POST /dashboard/apps                  # 创建 App
POST /dashboard/apps/{id}/keys        # 创建 App Key
```

### Operator 管理
```bash
GET /operator/orgs                    # 跨 org 总览
GET /operator/users-mapping           # Mem0 UUID 映射
GET /operator/backup/export/{user_id} # 备份导出
```

---

## SDKs

| SDK | 安装 | 文档 |
|-----|------|------|
| **Python** | `pip install cozymemory` | [sdks/python/README.md](sdks/python/README.md) |
| **JS/TS** | `npm install @cozymemory/sdk` | [sdks/js/README.md](sdks/js/README.md) |

```python
from cozymemory import CozyMemoryClient

with CozyMemoryClient(api_key="cozy_live_xxx", base_url="http://localhost:8000") as c:
    c.conversations.add("alice", [{"role": "user", "content": "I love hiking"}])
    ctx = c.context.get_unified("alice", query="outdoor activity")
```

---

## UI 功能一览

### Developer 视角（JWT 登录）

| 页面 | 功能 |
|------|------|
| **Apps** | App 列表 + 创建 |
| **App 工作台** | Memory / Profiles / Knowledge / Context / Playground 子页 |
| **Keys** | App Key CRUD + 一次性展示 |
| **External Users** | 分页列表 + GDPR 删除 |

### Operator 视角（Bootstrap key）

| 页面 | 功能 |
|------|------|
| **Dashboard** | 三引擎健康 + 延迟/增长 sparkline |
| **Orgs** | 跨 org 总览 |
| **Memory / Profiles / Knowledge** | 全局裸数据浏览 |
| **Backup** | 每用户 JSON 备份/恢复 |
| **Health** | 引擎详细状态 |
| **Settings** | Bootstrap key 管理 + 审计日志 |

### 通用能力
- i18n 中英切换 + 键盘快捷键（`?` 查看）
- 乐观删除 + toast 通知 + 暗色模式
- Knowledge 交互式力导向图可视化
- Playground SSE 流式聊天 + 会话持久化

---

## 可观测性

- **Prometheus**：`/metrics` 端点暴露引擎延迟/错误/用量指标
- **Grafana**：http://localhost:3001 预置 dashboard
- **告警规则**：EngineDown / HighLatency / HighErrorRate / APIDown
- **OpenTelemetry**：`pip install cozymemory[otel]` + `OTEL_ENABLED=true`

---

## 开发

### 后端
```bash
pip install -e ".[dev]"
uvicorn cozymemory.app:create_app --factory --host 0.0.0.0 --port 8000

# 测试
pytest tests/unit/ -v                                    # 524 单元测试
COZY_TEST_URL=http://localhost:8000 pytest tests/integration/ -v  # 69 集成测试

# Lint / 类型
ruff check src/ tests/
mypy src/cozymemory --ignore-missing-imports
```

### 前端（`ui/`）
```bash
cd ui && npm install && npm run dev    # port 3000
npm run gen:api                        # 从后端 openapi.json 生成 TS 类型
npx tsc --noEmit                       # 类型检查
```

### 重建镜像
```bash
sudo ./CozyMemory/build.sh cozymemory      # 只重建 API
sudo ./CozyMemory/build.sh cozymemory-ui   # 只重建 UI
sudo docker compose -f CozyMemory/docker-compose.1panel.yml \
  up -d --force-recreate cozymemory-api cozymemory-ui
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
│   ├── models/              # Pydantic 模型
│   ├── auth.py              # JWT + 角色鉴权
│   ├── db.py                # SQLAlchemy 模型（Org/Developer/App/Key）
│   ├── metrics.py           # Prometheus 自定义指标
│   └── telemetry.py         # OpenTelemetry 可选接入
├── ui/                      # Next.js 16 管理界面
├── sdks/
│   ├── python/              # Python SDK (cozymemory)
│   └── js/                  # JS/TS SDK (@cozymemory/sdk)
├── CozyMemory/            # Docker 部署
│   ├── docker-compose.1panel.yml
│   ├── build.sh
│   ├── Caddyfile
│   └── prometheus/          # Prometheus 配置 + 告警规则
├── deploy/k8s/              # Kubernetes 部署示例
├── alembic/                 # 数据库迁移
├── proto/                   # gRPC protobuf 定义
├── tests/
│   ├── unit/                # 524 单元测试
│   └── integration/         # 69 集成测试（50 REST + 19 gRPC）
├── docs/                    # 参考文档
└── CLAUDE.md                # AI 协作深度笔记
```

---

## 文档

- **[CLAUDE.md](CLAUDE.md)** — 架构、约定、API 怪癖
- **[CHANGELOG.md](CHANGELOG.md)** — 版本历史
- **[docs/usage-cn.md](docs/usage-cn.md)** — 中文使用说明
- **[docs/migration-guide.md](docs/migration-guide.md)** — 数据库迁移操作指南
- **[docs/](docs/)** — API 参考、架构、数据模型、部署、SDK 文档
- **Swagger UI**：http://localhost:8000/docs

---

## 许可

[AGPL-3.0-or-later](LICENSE)

# CozyMemory Base Runtime 设计文档

**日期：** 2026-04-17  
**状态：** 待实施  
**目标：** 为 CozyMemory 后续开发搭建统一的基础运行环境，支持一键部署

---

## 背景

CozyMemory 集成三个 AI 记忆引擎：Cognee（知识图谱）、Mem0（对话记忆）、Memobase（用户画像）。
三个引擎各自在 `projects/POCRunning/` 下有独立可运行的部署配置，但基础设施（postgres、redis 等）各自独立，资源浪费且管理分散。

`base_runtime/` 是将三个引擎统一整合的基础运行环境，作为 CozyMemory 后续开发阶段的集成底座。
未来 CozyMemory 应用服务开发完成后，直接加入此 compose 文件即可形成完整后端。

---

## 目录结构

```
base_runtime/
├── docker-compose.1panel.yml   # 主编排文件（1Panel 专用）
├── Caddyfile                   # Caddy 多端口路由配置
├── build.sh                    # 统一镜像构建脚本（构建所有自定义镜像）
└── sql/
    └── init.sql                # PostgreSQL 多租户数据库初始化脚本
```

---

## 服务架构

### 流量入口（Caddy 多端口）

```
外部访问
  :8080  ──► /api/*  → cognee:8000              (Cognee API，透传全路径)
         ──► /*       → cognee-frontend:3000      (Cognee 前端)

  :8081  ──► /api/*  → mem0-api:8000             (Mem0 API，透传全路径，不 strip 前缀)
         ──► /*       → mem0-webui:3000           (Mem0 前端)

  :8019  ──► /*       → memobase-server-api:8000  (Memobase API)

  :8000  ← 预留给未来 CozyMemory Admin 服务（当前不使用）
```

> **Mem0 路由说明：** mem0-api 路由本身就在 `/api/v1/*`，mem0-webui 调用的是
> `${NEXT_PUBLIC_API_URL}/api/v1/...`。Caddy 直接透传整个路径，**不做前缀裁剪**。
> 如果 strip `/api`，mem0-api 会收到 `/v1/...` 导致 404。

### 服务清单（10个）

| 服务 | 镜像 | 对外端口 | 说明 |
|---|---|---|---|
| caddy | caddy:alpine | 8080, 8081, 8019 | 统一反向代理 |
| cognee | cognee:0.4.1 | — | Cognee 核心服务 |
| cognee-frontend | cognee-frontend:local-0.4.1 | — | Cognee 前端 |
| mem0-api | mem0-api:latest | — | Mem0 API 服务 |
| mem0-webui | mem0-webui:latest | — | Mem0 前端 |
| memobase-server-api | memobase-server:latest | — | Memobase API 服务 |
| postgres | pgvector/pgvector:0.8.1-pg17-trixie | — | 共享关系型+向量数据库 |
| redis | redis:7-alpine | — | 共享缓存（db0=cognee, db1=memobase） |
| qdrant | qdrant/qdrant:v1.15 | — | Mem0 专用向量数据库 |
| minio | quay.io/minio/minio:RELEASE.2023-11-01T01-57-10Z-cpuv1 | — | Cognee 专用对象存储 |
| neo4j | neo4j:latest | — | Cognee 专用图数据库 |

> **已移除：** cognee-mcp-api（当前阶段不需要）  
> **预留：** :8000 端口留给未来 CozyMemory Admin

### 基础设施共享策略

| 资源 | 使用方 | 隔离方式 |
|---|---|---|
| postgres | Cognee + Memobase | 独立数据库（cognee_db / memobase） |
| redis | Cognee + Memobase | 不同 DB 编号（db0 / db1） |
| qdrant | Mem0 | 独占（Mem0 无 postgres 依赖） |
| minio | Cognee | 独占 |
| neo4j | Cognee | 独占 |

---

## 自定义镜像构建

所有自定义镜像的 Dockerfile 已存在于对应的 Cozy* 目录中，build.sh 统一调用：

| 镜像 | Dockerfile 位置 | 构建特点 |
|---|---|---|
| `mem0-api:latest` | `CozyMem0/deployment/mem0/Dockerfile` | 应用 CORS + 中文支持 patch |
| `mem0-webui:latest` | `CozyMem0/projects/mem0/openmemory/ui/Dockerfile` | Next.js 多阶段构建 |
| `memobase-server:latest` | `CozyMemobase/deployment/memobase/Dockerfile` | 需先同步源码到 deployment 目录 |
| `cognee:0.4.1` | `CozyCognee/deployment/docker/cognee/Dockerfile` | 以项目根目录为构建上下文，含 CORS patch |
| `cognee-frontend:local-0.4.1` | `CozyCognee/deployment/docker/cognee-frontend/Dockerfile` | 含多处 UI patch（去除 cloud 功能） |

### 构建前代码同步检查

**memobase** 的 deployment 目录包含源码副本（`memobase_server/`、`api.py` 等），需验证：
- `CozyMemobase/deployment/memobase/memobase_server/` 与最新源码 `projects/memobase/src/server/api/` 是否一致
- 如不一致，重新运行 `CozyMemobase/deployment/memobase/build.sh` 会自动同步

**CozyCognee / CozyMem0** 的 patch 以 Python 脚本方式应用，需验证 patch 目标文件的路径和内容在最新上游代码中是否发生变化。

---

## 数据存储

所有数据统一存放在 `/data/CozyMemory/` 下：

```
/data/CozyMemory/
├── postgres/           # PostgreSQL 数据
├── redis/              # Redis 持久化
├── qdrant/             # Qdrant 向量存储
├── minio/              # MinIO 对象存储
├── neo4j/
│   ├── data/
│   ├── logs/
│   └── plugins/
├── cognee/
│   ├── data/
│   └── logs/
├── mem0/
│   ├── history/        # SQLite 历史数据库
│   └── logs/
├── memobase/           # Memobase 数据
└── tiktoken/           # Tiktoken 编码缓存（需预先复制）
```

### Tiktoken 缓存说明

Cognee 和 Memobase 都依赖 `tiktoken` 做 token 计数。首次运行会从 Azure Blob 下载编码文件，
受限网络环境下会失败。**部署前需将缓存文件复制到位：**

```bash
mkdir -p /data/CozyMemory/tiktoken
cp /home/ubuntu/.tiktoken/* /data/CozyMemory/tiktoken/
```

---

## 网络配置

- 网络名：`1panel-network`（external，由 1Panel 预先创建）
- 所有服务加入同一网络，容器间通过服务名互访
- 基础设施服务（postgres、redis 等）不暴露任何宿主机端口

---

## 配置方式

- LLM API Key 直接写入 `docker-compose.1panel.yml`，部署前手动修改
- 服务器 IP 使用占位符 `YOUR_SERVER_IP`，部署前全局替换为实际 IP
- 无 `.env` 文件依赖，降低 1Panel 操作复杂度

---

## Caddyfile 路由设计

```caddyfile
# Cognee 生态 (8080)
:8080 {
    handle /api/* {
        reverse_proxy cognee:8000
    }
    handle {
        reverse_proxy cognee-frontend:3000
    }
}

# Mem0 生态 (8081)
# 注意：不做前缀裁剪，mem0-api 路由本身在 /api/v1/*
:8081 {
    handle /api/* {
        reverse_proxy mem0-api:8000
    }
    handle {
        reverse_proxy mem0-webui:3000
    }
}

# Memobase (8019)
:8019 {
    reverse_proxy memobase-server-api:8000
}
```

---

## 未来扩展点

- **CozyMemory Admin**（端口 8000）：统一管理三个引擎的管理界面，加入后修改 Caddy 配置即可
- **CozyMemory 应用服务**：REST API + gRPC，作为新 service 加入此 compose 文件
- **认证层**：未来可在 Caddy 层加 JWT/API Key 校验，无需改动各引擎服务

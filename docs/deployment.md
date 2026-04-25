# CozyMemory 部署指南

**版本**: 0.2.0  
**更新**: 2026-04-25

---

## 1. 部署架构

CozyMemory 由 15 个容器组成，运行在 `1panel-network` Docker 网络中，Caddy 作为反向代理统一暴露端口。

```
┌────────────────────────────────────────────────────────────────────────┐
│  Caddy :80/:8000/:8080/:8081/:8019/:8088/:3001/:50051  反向代理       │
└────────────────────────────────────────────────────────────────────────┘
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

## 2. 系统要求

- Linux x86_64 / arm64
- Docker 24+ 和 Docker Compose v2
- 内存 8GB+（推荐 16GB）
- 磁盘 20GB+
- 外部 LLM（OpenAI 兼容 API）

---

## 3. 快速部署

```bash
git clone https://github.com/zinohome/CozyMemory.git
cd CozyMemory

# 配置环境变量
cp base_runtime/.env.example base_runtime/.env
vi base_runtime/.env    # 必填：LLM_API_KEY, 各数据库密码, JWT_SECRET

# 构建 7 个自定义镜像（约 25-30 分钟）
sudo ./base_runtime/build.sh all

# 启动全部 15 个容器
sudo docker compose -f base_runtime/docker-compose.1panel.yml up -d

# 等待 ~60 秒，验证
curl http://localhost:8000/api/v1/health
```

---

## 4. 环境变量

所有环境变量通过 `base_runtime/.env` 配置，docker compose 自动加载。

### 必填项

| 变量 | 说明 |
|------|------|
| `LLM_API_KEY` | OpenAI 兼容 API Key，所有引擎共用 |
| `POSTGRES_PASSWORD` | PostgreSQL root 密码 |
| `REDIS_PASSWORD` | Redis 密码 |
| `NEO4J_PASSWORD` | Neo4j 密码 |
| `MINIO_ROOT_PASSWORD` | MinIO root 密码 |
| `COGNEE_DB_PASSWORD` | Cognee 数据库用户密码 |
| `MEMOBASE_DB_PASSWORD` | Memobase 数据库用户密码 |
| `COZYMEMORY_DB_PASSWORD` | CozyMemory 数据库用户密码 |
| `MEMOBASE_ACCESS_TOKEN` | Memobase 服务端 token |
| `JWT_SECRET` | Developer JWT 签名密钥（`openssl rand -hex 32`） |

### 可选项

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `COZY_API_KEYS` | 空（关闭鉴权） | 逗号分隔的 bootstrap key |
| `CORS_ALLOWED_ORIGINS` | `*` | 生产环境应限制为具体域名 |
| `COGNEE_ADMIN_PASSWORD` | `passw0rd` | Cognee 管理员密码 |

> **注意**：数据库密码在 `init.sh` 首次建库时写入。已初始化后修改 `.env` 不会自动更新密码，需手动 `ALTER USER`。

---

## 5. 服务清单（15 个容器）

### 基础设施层

| 服务 | 镜像 | 容器名 | 内部端口 | 说明 |
|------|------|--------|----------|------|
| PostgreSQL | `pgvector/pgvector:0.8.1-pg17` | `cozy_postgres` | 5432 | 主数据库 + 向量扩展 |
| Redis | `redis:7-alpine` | `cozy_redis` | 6379 | 用户映射 + 缓存 |
| Qdrant | `qdrant/qdrant:v1.15` | `cozy_qdrant` | 6333 | Mem0 向量存储 |
| MinIO | `minio:RELEASE.2023-11-01` | `cozy_minio` | 9000/9001 | Cognee 对象存储 |
| Neo4j | `neo4j:2026.03.1` | `cozy_neo4j` | 7687 | Cognee 图数据库 |

### 引擎层

| 服务 | 镜像 | 容器名 | 内部端口 | 说明 |
|------|------|--------|----------|------|
| Cognee API | `cognee:0.4.1` | `cozy_cognee` | 8000 | 知识图谱引擎 |
| Cognee Frontend | `cognee-frontend:local-0.4.1` | `cozy_cognee_frontend` | 3000 | Cognee 管理 UI |
| Mem0 API | `mem0-api:latest` | `cozy_mem0_api` | 8000 | 对话记忆引擎 |
| Mem0 WebUI | `mem0-webui:latest` | `cozy_mem0_webui` | 3000 | Mem0 管理 UI |
| Memobase API | `memobase-server:latest` | `cozy_memobase_api` | 8000 | 用户画像引擎 |

### 应用层

| 服务 | 镜像 | 容器名 | 内部端口 | 说明 |
|------|------|--------|----------|------|
| CozyMemory API | `cozymemory:latest` | `cozymemory` | 8000/50051 | REST + gRPC（supervisord） |
| CozyMemory UI | `cozymemory-ui:latest` | `cozy_ui` | 3000 | Next.js 16 管理界面 |

### 可观测性层

| 服务 | 镜像 | 容器名 | 内部端口 | 说明 |
|------|------|--------|----------|------|
| Prometheus | `prom/prometheus:v2.55.0` | `cozy_prometheus` | 9090 | 指标采集（30 天保留） |
| Grafana | `grafana/grafana:11.4.0` | `cozy_grafana` | 3000 | 监控 Dashboard |

### 反向代理

| 服务 | 镜像 | 容器名 | 说明 |
|------|------|--------|------|
| Caddy | `caddy:alpine` | `cozy_caddy` | 统一入口 + LLM 代理 |

---

## 6. 端口映射（Caddy）

| 外部端口 | 目标服务 | 说明 |
|----------|---------|------|
| 80 | 导航页 | 服务发现静态页 |
| 8000 | CozyMemory API | REST API（`/metrics` 被屏蔽） |
| 8080 | Cognee | `/api/*` → API，`/*` → Frontend |
| 8081 | Mem0 | `/api/*` → API，`/*` → WebUI |
| 8019 | Memobase | 直连 API |
| 8088 | CozyMemory UI | Developer + Operator 管理界面 |
| 3001 | Grafana | 监控 Dashboard |
| 50051 | gRPC (TLS) | 自签名 TLS，内部 h2c |

---

## 7. 构建自定义镜像

7 个自定义镜像由 `build.sh` 从源码构建：

```bash
sudo ./base_runtime/build.sh all            # 构建全部（~25 分钟）
sudo ./base_runtime/build.sh cozymemory     # 只构建 API
sudo ./base_runtime/build.sh cozymemory-ui  # 只构建 UI
sudo ./base_runtime/build.sh cognee         # 只构建 Cognee
sudo ./base_runtime/build.sh mem0-api       # 只构建 Mem0
sudo ./base_runtime/build.sh memobase       # 只构建 Memobase
```

构建完成后重启对应容器：

```bash
sudo docker compose -f base_runtime/docker-compose.1panel.yml \
  up -d --force-recreate cozymemory-api cozymemory-ui
```

---

## 8. Dockerfile（CozyMemory API）

多阶段构建，使用 supervisord 同时运行 REST 和 gRPC：

- **Builder 阶段**：`python:3.11-slim`，安装依赖到 `/opt/venv`
- **Runtime 阶段**：非 root 用户 `cozymemory`（UID 1000），supervisord 管理两个进程
- **健康检查**：每 30 秒检查 `/api/v1/health`，15 秒启动延迟，3 次重试
- **暴露端口**：8000（REST）+ 50051（gRPC）

---

## 9. 数据持久化

所有有状态数据存储在 `/data/CozyMemory/` 下：

```
/data/CozyMemory/
├── postgres/       # PostgreSQL 数据
├── redis/          # Redis AOF 持久化
├── qdrant/         # Qdrant 向量数据
├── neo4j/          # Neo4j 图数据
├── minio/          # MinIO 对象存储
├── cognee/         # Cognee 数据 + 日志
├── mem0/           # Mem0 历史 + 日志
├── memobase/       # Memobase 数据
├── prometheus/     # 指标数据（30 天）
├── grafana/        # Dashboard 配置
└── tiktoken/       # 共享 tokenizer 缓存
```

---

## 10. 日志管理

所有 15 个容器统一配置 Docker 日志轮转：

```yaml
logging:
  driver: json-file
  options:
    max-size: "50m"
    max-file: "5"
```

查看日志：

```bash
sudo docker logs -f cozymemory --tail 100      # CozyMemory API
sudo docker logs -f cozy_cognee --tail 100      # Cognee
sudo docker compose -f base_runtime/docker-compose.1panel.yml logs -f  # 全部
```

---

## 11. 可观测性

### Prometheus

- 采集 CozyMemory `/metrics` 端点
- 告警规则（`base_runtime/prometheus/alerts.yml`）：
  - `EngineDown`：引擎连续 2 分钟不可达
  - `HighEngineLatency`：P95 延迟 > 5 秒
  - `HighEngineErrorRate`：错误率 > 10%
  - `HighRequestLatencyP99`：API P99 > 10 秒
  - `APIDown`：CozyMemory 主进程不可达

### Grafana

- 访问 `http://你的IP:3001`，默认密码 `cozyadmin`
- 预置 Dashboard 展示引擎健康、延迟、错误率

### OpenTelemetry（可选）

```bash
pip install cozymemory[otel]
```

设置 `OTEL_ENABLED=true` 启用链路追踪，支持 OTLP 导出。

---

## 12. 健康检查

```bash
# 快速检查
curl http://localhost:8000/api/v1/health

# 预期响应
{
  "status": "healthy",
  "engines": {
    "mem0": {"name": "Mem0", "status": "healthy", "latency_ms": 26.0},
    "memobase": {"name": "Memobase", "status": "healthy", "latency_ms": 15.3},
    "cognee": {"name": "Cognee", "status": "healthy", "latency_ms": 33.0}
  }
}
```

状态值：`healthy`（全部正常）、`degraded`（部分引擎不可用）、`unhealthy`（全部不可用）。

---

## 13. 常见操作

### 重启单个服务

```bash
sudo docker compose -f base_runtime/docker-compose.1panel.yml restart cozymemory-api
```

### 重建并重启

```bash
sudo ./base_runtime/build.sh cozymemory
sudo docker compose -f base_runtime/docker-compose.1panel.yml \
  up -d --force-recreate cozymemory-api
```

### 数据库迁移

```bash
cd /home/ubuntu/CozyProjects/CozyMemory
source .venv/bin/activate
alembic upgrade head
```

详见 [migration-guide.md](migration-guide.md)。

### 备份

```bash
# 单用户备份
curl http://localhost:8000/api/v1/operator/backup/export/{user_id} \
  -H "X-Cozy-API-Key: 你的bootstrap-key" > backup.json

# PostgreSQL 全量备份
sudo docker exec cozy_postgres pg_dumpall -U postgres > pg_backup.sql
```

---

## 14. Kubernetes 部署

参考 `deploy/k8s/` 目录：

- `secret.yaml`：API key + 数据库凭证
- `deployment.yaml`：2 副本，liveness/readiness 探针
- `service.yaml`：ClusterIP，端口 8000 + 50051

> K8s 部署仅覆盖 CozyMemory API 本身，三引擎后端需另行部署。

---

## 15. 生产检查清单

- [ ] 所有密码已改为强密码（非默认值）
- [ ] `JWT_SECRET` 已用 `openssl rand -hex 32` 生成
- [ ] `COZY_API_KEYS` 已设置（启用鉴权）
- [ ] `CORS_ALLOWED_ORIGINS` 已限制为具体域名
- [ ] Grafana 默认密码已修改
- [ ] 磁盘空间 > 20GB
- [ ] 日志轮转已配置（默认 50m × 5）
- [ ] 备份策略已制定

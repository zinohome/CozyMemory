# Cognee 知识图谱多租户隔离 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Cognee 的图/向量数据库从 Neo4j+PGVector 切换为 Kuzu+LanceDB，开启多租户隔离。

**Architecture:** 纯配置变更，无应用代码改动。修改 docker-compose 环境变量切换数据库 provider，注释保留 Neo4j 服务供单用户回退，修改 Dockerfile 移除 neo4j 构建依赖。Kuzu 和 LanceDB 都是嵌入式数据库，数据存储在 Cognee 容器的 `/app/data` 目录（已挂载到宿主机）。

**Tech Stack:** Docker Compose, Cognee 0.4.1, Kuzu 0.11.3 (embedded graph DB), LanceDB (embedded vector DB)

**Spec:** `docs/superpowers/specs/2026-04-27-cognee-knowledge-isolation-design.md`

---

### File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `base_runtime/docker-compose.1panel.yml:86-109` | 注释 Neo4j 服务段 |
| Modify | `base_runtime/docker-compose.1panel.yml:115-176` | Cognee 环境变量 + depends_on |
| Modify | `projects/CozyCognee/deployment/docker/cognee/Dockerfile:37,57` | 移除 `--extra neo4j` |

> **注意：** Spec 第 4 节提到 "build.sh 调整" 实际不需要。`build_cognee()` 没有 EXTRAS 参数，neo4j 依赖是在 Dockerfile 的 `uv sync` 命令中硬编码的。docker-compose 中的 `EXTRAS` 环境变量在我们的自定义 Dockerfile/entrypoint 中未被使用（仅 MCP 模式用到），但仍按 spec 更新以保持一致性。

---

### Task 1: 注释 Neo4j 服务，添加回退说明

**Files:**
- Modify: `base_runtime/docker-compose.1panel.yml:86-109`

- [ ] **Step 1: 注释 Neo4j 服务段**

将 `neo4j:` 服务块（第 86-109 行）整段注释，并在顶部添加回退说明：

```yaml
  # ──────── Neo4j（已禁用 — 多租户模式使用 Kuzu 替代）────────
  # 如需切回 Neo4j（单用户/开发模式），取消注释本段并修改 cognee 环境变量：
  #   GRAPH_DATABASE_PROVIDER=neo4j
  #   GRAPH_DATABASE_URL=bolt://neo4j:7687
  #   GRAPH_DATABASE_USERNAME=neo4j
  #   GRAPH_DATABASE_PASSWORD=${NEO4J_PASSWORD}
  #   VECTOR_DB_PROVIDER=pgvector
  #   VECTOR_DB_URL=postgresql://${COGNEE_DB_USER:-cognee_user}:${COGNEE_DB_PASSWORD}@postgres:5432/cognee_db
  #   ENABLE_BACKEND_ACCESS_CONTROL=false
  # 同时需将 cognee 的 depends_on 中添加 neo4j
  #
  # neo4j:
  #   image: neo4j:2026.03.1
  #   container_name: cozy_neo4j
  #   restart: unless-stopped
  #   environment:
  #     NEO4J_AUTH: neo4j/${NEO4J_PASSWORD:?NEO4J_PASSWORD required}
  #     NEO4J_PLUGINS: '["apoc", "graph-data-science"]'
  #     NEO4J_dbms_memory_heap_initial__size: 512m
  #     NEO4J_dbms_memory_heap_max__size: 1G
  #   volumes:
  #     - /data/CozyMemory/neo4j/data:/data
  #     - /data/CozyMemory/neo4j/logs:/logs
  #     - /data/CozyMemory/neo4j/plugins:/plugins
  #   networks:
  #     - 1panel-network
  #   logging: *default-logging
  #   labels:
  #     createdBy: "Apps"
  #   deploy:
  #     resources:
  #       limits:
  #         memory: 2g
  #       reservations:
  #         memory: 512m
```

- [ ] **Step 2: 验证 YAML 语法**

Run: `docker compose -f base_runtime/docker-compose.1panel.yml config --quiet`
Expected: 无输出（静默退出 0）

- [ ] **Step 3: Commit**

```bash
git add base_runtime/docker-compose.1panel.yml
git commit -m "chore(cognee): comment out Neo4j service for multi-tenant mode

Neo4j does not support Cognee's per-dataset isolation. Commented out with
instructions for re-enabling in single-user/dev mode."
```

---

### Task 2: 切换 Cognee 环境变量 — 图/向量数据库 + 多租户

**Files:**
- Modify: `base_runtime/docker-compose.1panel.yml:115-176` (cognee service)

- [ ] **Step 1: 替换图数据库配置**

将 cognee 服务的环境变量块中：

```yaml
      - VECTOR_DB_PROVIDER=pgvector
      - VECTOR_DB_URL=postgresql://${COGNEE_DB_USER:-cognee_user}:${COGNEE_DB_PASSWORD}@postgres:5432/cognee_db
      - GRAPH_DATABASE_PROVIDER=neo4j
      - GRAPH_DATABASE_NAME=neo4j
      - GRAPH_DATABASE_URL=bolt://neo4j:7687
      - GRAPH_DATABASE_USERNAME=neo4j
      - GRAPH_DATABASE_PASSWORD=${NEO4J_PASSWORD}
```

替换为：

```yaml
      - VECTOR_DB_PROVIDER=lancedb
      - GRAPH_DATABASE_PROVIDER=kuzu
```

- [ ] **Step 2: 开启多租户隔离**

将：

```yaml
      - ENABLE_BACKEND_ACCESS_CONTROL=false
```

替换为：

```yaml
      - ENABLE_BACKEND_ACCESS_CONTROL=true
```

- [ ] **Step 3: 更新 EXTRAS 环境变量**

将：

```yaml
      - EXTRAS=api,postgres,neo4j
```

替换为：

```yaml
      - EXTRAS=api,postgres
```

- [ ] **Step 4: 移除 neo4j depends_on**

将 cognee 的 `depends_on` 从：

```yaml
    depends_on:
      - postgres
      - redis
      - neo4j
      - minio
```

改为：

```yaml
    depends_on:
      - postgres
      - redis
      - minio
```

- [ ] **Step 5: 验证 YAML 语法**

Run: `docker compose -f base_runtime/docker-compose.1panel.yml config --quiet`
Expected: 无输出（静默退出 0）

- [ ] **Step 6: Commit**

```bash
git add base_runtime/docker-compose.1panel.yml
git commit -m "feat(cognee): switch to Kuzu+LanceDB and enable multi-tenant isolation

- GRAPH_DATABASE_PROVIDER: neo4j → kuzu
- VECTOR_DB_PROVIDER: pgvector → lancedb
- ENABLE_BACKEND_ACCESS_CONTROL: false → true
- Remove neo4j-specific env vars and depends_on"
```

---

### Task 3: 修改 Cognee Dockerfile — 移除 neo4j 构建依赖

**Files:**
- Modify: `projects/CozyCognee/deployment/docker/cognee/Dockerfile:37,57`

> **背景:** Dockerfile 中两个 `uv sync` 命令都硬编码了 `--extra neo4j`。Kuzu 和 LanceDB 已是 Cognee 的核心依赖（在 `pyproject.toml` 的 `dependencies` 而非 `optional-dependencies` 中），无需额外 extra。

- [ ] **Step 1: 移除第一个 uv sync 中的 neo4j extra**

在 `Dockerfile` 第 37 行，将：

```dockerfile
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --extra debug --extra api --extra postgres --extra neo4j --extra llama-index --extra ollama --extra mistral --extra groq --extra anthropic --extra scraping --frozen --no-install-project --no-dev --no-editable
```

改为：

```dockerfile
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --extra debug --extra api --extra postgres --extra llama-index --extra ollama --extra mistral --extra groq --extra anthropic --extra scraping --frozen --no-install-project --no-dev --no-editable
```

- [ ] **Step 2: 移除第二个 uv sync 中的 neo4j extra**

在 `Dockerfile` 第 57 行，将：

```dockerfile
RUN --mount=type=cache,target=/root/.cache/uv \
uv sync --extra debug --extra api --extra postgres --extra neo4j --extra llama-index --extra ollama --extra mistral --extra groq --extra anthropic --extra scraping --frozen --no-dev --no-editable
```

改为：

```dockerfile
RUN --mount=type=cache,target=/root/.cache/uv \
uv sync --extra debug --extra api --extra postgres --extra llama-index --extra ollama --extra mistral --extra groq --extra anthropic --extra scraping --frozen --no-dev --no-editable
```

- [ ] **Step 3: 移除 pgvector 注释（不再适用）**

删除第 39-40 行：

```dockerfile
# Note: pgvector is included in the postgres extra dependencies
# No additional adapter installation needed for pgvector
```

和第 65 行：

```dockerfile
# Note: pgvector support is included via postgres extra dependencies
```

- [ ] **Step 4: Commit**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory
git add projects/CozyCognee/deployment/docker/cognee/Dockerfile
git commit -m "chore(cognee): remove neo4j extra from Dockerfile

Kuzu and LanceDB are core dependencies, no extra flag needed.
Also remove stale pgvector comments."
```

---

### Task 4: 重建镜像并部署

- [ ] **Step 1: 重建 Cognee 后端镜像**

Run: `cd /home/ubuntu/CozyProjects/CozyMemory && base_runtime/build.sh cognee`
Expected: 构建成功，最后输出 `cognee:0.4.1 built.`

> 注意：首次构建可能较慢（需要重新下载移除 neo4j 后的依赖缓存），预计 3-8 分钟。

- [ ] **Step 2: 停止旧服务**

Run: `docker compose -f base_runtime/docker-compose.1panel.yml stop cognee neo4j`
Expected: 两个服务停止

- [ ] **Step 3: 启动更新后的服务栈**

Run: `docker compose -f base_runtime/docker-compose.1panel.yml up -d`
Expected: 所有服务启动（neo4j 不会启动因为已注释）

- [ ] **Step 4: 检查 Cognee 容器日志**

Run: `docker logs cozy_cognee --tail 50 2>&1`
Expected:
- 无 Neo4j 连接错误
- 出现 "Starting server..." 且 gunicorn worker 启动成功
- 可能看到 Kuzu/LanceDB 初始化日志

- [ ] **Step 5: 健康检查**

Run: `curl -s http://localhost:8000/api/v1/health | python3 -m json.tool`
Expected: Cognee 引擎状态 healthy（`engines.cognee.status` 为 `"healthy"`）

- [ ] **Step 6: Commit（如有额外调整）**

如果 Task 4 过程中需要微调配置，统一提交。

---

### Task 5: 验证多租户隔离

> 此任务无代码变更，仅为端到端验证。使用 CozyMemory REST API（不直连 Cognee）。

- [ ] **Step 1: 确认 Cognee 直连 API 正常**

Run:
```bash
curl -s http://localhost:8080/api/v1/datasets | python3 -m json.tool
```
Expected: 返回 JSON 数组（可能为空 `[]`）

- [ ] **Step 2: 基本功能 — 通过 CozyMemory API 创建 dataset 并添加数据**

使用 App A 的 API Key 操作：

```bash
APP_A_KEY="<App A 的 API Key>"

# 创建 dataset
curl -s -X POST "http://localhost:8000/api/v1/knowledge/datasets?name=test-isolation" \
  -H "X-Cozy-API-Key: $APP_A_KEY" | python3 -m json.tool

# 添加数据
curl -s -X POST http://localhost:8000/api/v1/knowledge/add \
  -H "Content-Type: application/json" \
  -H "X-Cozy-API-Key: $APP_A_KEY" \
  -d '{"dataset_id":"<dataset_id>","data":"CozyMemory is a unified AI memory platform."}' | python3 -m json.tool

# 触发知识图谱构建
curl -s -X POST http://localhost:8000/api/v1/knowledge/cognify \
  -H "Content-Type: application/json" \
  -H "X-Cozy-API-Key: $APP_A_KEY" \
  -d '{"dataset_id":"<dataset_id>"}' | python3 -m json.tool
```

Expected: 所有请求返回 `success: true`

- [ ] **Step 3: 搜索 — 验证 App A 能找到自己的数据**

```bash
curl -s -X POST http://localhost:8000/api/v1/knowledge/search \
  -H "Content-Type: application/json" \
  -H "X-Cozy-API-Key: $APP_A_KEY" \
  -d '{"query":"memory platform","dataset_id":"<dataset_id>"}' | python3 -m json.tool
```

Expected: 返回包含 "CozyMemory" 相关的搜索结果

- [ ] **Step 4: 跨 App 隔离 — App B 无法访问 App A 的 dataset**

```bash
APP_B_KEY="<App B 的 API Key>"

# App B 搜索 App A 的 dataset_id → 应返回 404
curl -s -X POST http://localhost:8000/api/v1/knowledge/search \
  -H "Content-Type: application/json" \
  -H "X-Cozy-API-Key: $APP_B_KEY" \
  -d '{"query":"memory platform","dataset_id":"<App A 的 dataset_id>"}' | python3 -m json.tool
```

Expected: HTTP 404（dataset 不属于 App B）

- [ ] **Step 5: 验证 Kuzu 数据目录结构**

```bash
docker exec cozy_cognee find /app/data -name "*.kuzu" -o -name "lancedb" -type d 2>/dev/null | head -20
```

Expected: 看到按用户/dataset 隔离的目录结构

- [ ] **Step 6: 清理测试数据**

```bash
curl -s -X DELETE http://localhost:8000/api/v1/knowledge \
  -H "Content-Type: application/json" \
  -H "X-Cozy-API-Key: $APP_A_KEY" \
  -d '{"data_id":"<data_id>","dataset_id":"<dataset_id>"}' | python3 -m json.tool
```

---

## Spec Coverage Check

| Spec Section | Task |
|---|---|
| §1 docker-compose 环境变量变更 | Task 2 |
| §2 Neo4j 服务注释保留 | Task 1 |
| §3 Cognee depends_on 调整 | Task 2 Step 4 |
| §4 Cognee build.sh 调整 | **N/A** — spec 不准确，实际改 Dockerfile (Task 3) |
| §5 数据存储路径 | 无需改动（已配置 volume），Task 5 Step 5 验证 |
| §6 已有数据处理 | Task 5 说明（通过 API 重新 add+cognify） |
| §7 CozyMemory 代码层影响 | 无改动（确认） |
| §8 验证计划 | Task 5 |

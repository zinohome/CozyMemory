# Base Runtime 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `base_runtime/` 目录下创建可一键部署的 CozyMemory 基础运行环境，整合 Cognee、Mem0、Memobase 三个引擎及其所有前端，使用 Caddy 多端口反代。

**Architecture:** 10 个 Docker 服务共享基础设施（postgres/pgvector、redis、qdrant、minio、neo4j），Caddy 在三个端口（8080/8081/8019）分别代理各引擎的前端和 API。自定义镜像由 `build.sh` 统一构建，来源于 Cozy* 项目目录中的 Dockerfile。

**Tech Stack:** Docker Compose v3.8、Caddy、pgvector/pgvector:0.8.1-pg17-trixie、Redis 7、Qdrant v1.15、MinIO、Neo4j、FastAPI、Next.js

---

## 文件清单

| 文件 | 操作 | 说明 |
|---|---|---|
| `base_runtime/docker-compose.1panel.yml` | 创建 | 主编排文件，10 个服务 |
| `base_runtime/Caddyfile` | 创建 | 多端口路由配置 |
| `base_runtime/sql/init.sql` | 创建 | PG 多租户初始化（复用 unified_deployment） |
| `base_runtime/build.sh` | 创建 | 统一镜像构建脚本 |

---

## Task 1：创建目录结构 + init.sql

**Files:**
- Create: `base_runtime/sql/init.sql`
- Create: `base_runtime/` 目录骨架

- [ ] **Step 1: 创建目录**

```bash
mkdir -p /home/ubuntu/CozyProjects/CozyMemory/base_runtime/sql
```

Expected: 无报错

- [ ] **Step 2: 验证 unified_deployment 的 init.sql 内容正确**

```bash
cat /home/ubuntu/CozyProjects/CozyMemory/unified_deployment/sql/init.sql
```

Expected: 看到创建 `cognee_user`、`cognee_db`、`memobase` 用户和库、启用 pgvector 扩展的 SQL。

- [ ] **Step 3: 创建 init.sql**

写入 `base_runtime/sql/init.sql`：

```sql
-- CozyMemory 统一数据库初始化脚本
-- PostgreSQL + pgvector 首次启动时自动执行

-- ===========================
-- Cognee 数据库初始化
-- ===========================
CREATE USER cognee_user WITH PASSWORD 'cognee_password';
CREATE DATABASE cognee_db OWNER cognee_user;
ALTER DATABASE cognee_db SET default_transaction_isolation TO 'read committed';
ALTER DATABASE cognee_db SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE cognee_db TO cognee_user;

\c cognee_db
CREATE EXTENSION IF NOT EXISTS vector;

-- ===========================
-- Memobase 数据库初始化
-- ===========================
CREATE USER memobase WITH PASSWORD 'memobase123';
CREATE DATABASE memobase OWNER memobase;
ALTER DATABASE memobase SET default_transaction_isolation TO 'read committed';
ALTER DATABASE memobase SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE memobase TO memobase;

\c memobase
CREATE EXTENSION IF NOT EXISTS vector;
```

- [ ] **Step 4: Commit**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory
git add base_runtime/sql/init.sql
git commit -m "feat(base_runtime): add sql init script"
```

---

## Task 2：创建 Caddyfile

**Files:**
- Create: `base_runtime/Caddyfile`

- [ ] **Step 1: 验证 Caddy 可用于配置校验**

```bash
docker run --rm -v /home/ubuntu/CozyProjects/CozyMemory/base_runtime:/etc/caddy caddy:alpine caddy validate --config /etc/caddy/Caddyfile 2>&1 || echo "file not exist yet, ok"
```

Expected: "file not exist yet, ok"（文件还没创建，预期失败）

- [ ] **Step 2: 创建 Caddyfile**

写入 `base_runtime/Caddyfile`：

```caddyfile
# CozyMemory 统一反向代理配置
# 端口说明：
#   :8080 → Cognee（前端 + API）
#   :8081 → Mem0（前端 + API）
#   :8019 → Memobase API

# Cognee 生态 (:8080)
:8080 {
    # Cognee API（/api/* 路径优先匹配）
    handle /api/* {
        reverse_proxy cognee:8000
    }
    # Cognee 前端（其余所有路径）
    handle {
        reverse_proxy cognee-frontend:3000
    }
}

# Mem0 生态 (:8081)
# 注意：mem0-api 路由本身在 /api/v1/*，不裁剪前缀，直接透传
:8081 {
    # Mem0 API
    handle /api/* {
        reverse_proxy mem0-api:8000
    }
    # Mem0 前端
    handle {
        reverse_proxy mem0-webui:3000
    }
}

# Memobase API (:8019)
:8019 {
    reverse_proxy memobase-server-api:8000
}
```

- [ ] **Step 3: 校验 Caddyfile 语法**

```bash
docker run --rm \
  -v /home/ubuntu/CozyProjects/CozyMemory/base_runtime/Caddyfile:/etc/caddy/Caddyfile:ro \
  caddy:alpine caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
```

Expected: `Valid configuration`

- [ ] **Step 4: Commit**

```bash
git add base_runtime/Caddyfile
git commit -m "feat(base_runtime): add Caddyfile multi-port routing"
```

---

## Task 3：创建 docker-compose.1panel.yml（基础设施层）

**Files:**
- Create: `base_runtime/docker-compose.1panel.yml`（基础设施部分）

- [ ] **Step 1: 确认 1panel-network 存在**

```bash
docker network ls | grep 1panel-network
```

Expected: 看到 `1panel-network` 的 external 网络。若不存在：`docker network create 1panel-network`

- [ ] **Step 2: 创建 docker-compose.1panel.yml（基础设施服务）**

写入 `base_runtime/docker-compose.1panel.yml`（此步骤只写基础设施部分，后续 Task 4 追加应用层）：

```yaml
# CozyMemory Base Runtime
# 1Panel 专用 Docker Compose 编排文件
# 部署前替换：YOUR_SERVER_IP → 实际服务器 IP
# 数据存储：/data/CozyMemory/
# 网络：1panel-network（1Panel 预建外部网络）

services:

  # ==========================================
  # 基础设施层（无对外端口，仅内网访问）
  # ==========================================

  postgres:
    image: pgvector/pgvector:0.8.1-pg17-trixie
    container_name: cozy_postgres
    restart: unless-stopped
    environment:
      POSTGRES_PASSWORD: cozy_pg_root_pass
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - /data/CozyMemory/postgres:/var/lib/postgresql/data
      - ./sql/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    networks:
      - 1panel-network
    labels:
      createdBy: "Apps"

  redis:
    image: redis:7-alpine
    container_name: cozy_redis
    restart: unless-stopped
    command: redis-server --appendonly yes --requirepass cozy_redis_pass
    volumes:
      - /data/CozyMemory/redis:/data
    networks:
      - 1panel-network
    labels:
      createdBy: "Apps"

  qdrant:
    image: qdrant/qdrant:v1.15
    container_name: cozy_qdrant
    restart: unless-stopped
    volumes:
      - /data/CozyMemory/qdrant:/qdrant/storage
    networks:
      - 1panel-network
    labels:
      createdBy: "Apps"

  minio:
    image: quay.io/minio/minio:RELEASE.2023-11-01T01-57-10Z-cpuv1
    container_name: cozy_minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - /data/CozyMemory/minio:/data
    networks:
      - 1panel-network
    labels:
      createdBy: "Apps"

  neo4j:
    image: neo4j:latest
    container_name: cozy_neo4j
    restart: unless-stopped
    environment:
      NEO4J_AUTH: neo4j/pleaseletmein
      NEO4J_PLUGINS: '["apoc", "graph-data-science"]'
      NEO4J_dbms_memory_heap_initial__size: 512m
      NEO4J_dbms_memory_heap_max__size: 1G
    volumes:
      - /data/CozyMemory/neo4j/data:/data
      - /data/CozyMemory/neo4j/logs:/logs
      - /data/CozyMemory/neo4j/plugins:/plugins
    networks:
      - 1panel-network
    labels:
      createdBy: "Apps"
    deploy:
      resources:
        limits:
          memory: 2g
        reservations:
          memory: 512m

networks:
  1panel-network:
    external: true
```

- [ ] **Step 3: 验证 compose 配置语法**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory/base_runtime
docker compose -f docker-compose.1panel.yml config --quiet
```

Expected: 无报错退出（exit code 0）

- [ ] **Step 4: 启动基础设施层冒烟测试**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory/base_runtime
docker compose -f docker-compose.1panel.yml up -d postgres redis qdrant minio neo4j
sleep 10
docker compose -f docker-compose.1panel.yml ps
```

Expected: 5 个容器均为 `Up` 状态（neo4j 可能需要较长时间）

- [ ] **Step 5: 验证 postgres 初始化成功**

```bash
docker exec cozy_postgres psql -U postgres -c "\l" | grep -E "cognee_db|memobase"
```

Expected: 看到 `cognee_db` 和 `memobase` 两个数据库

- [ ] **Step 6: 停止测试容器**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory/base_runtime
docker compose -f docker-compose.1panel.yml down
```

- [ ] **Step 7: Commit**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory
git add base_runtime/docker-compose.1panel.yml
git commit -m "feat(base_runtime): add infrastructure services to compose"
```

---

## Task 4：docker-compose.1panel.yml 追加应用层服务

**Files:**
- Modify: `base_runtime/docker-compose.1panel.yml`（追加应用服务 + Caddy）

- [ ] **Step 1: 在 `networks:` 声明前追加全部应用服务**

在 `docker-compose.1panel.yml` 的 `networks:` 节之前追加以下内容：

```yaml
  # ==========================================
  # Cognee 服务群
  # ==========================================

  cognee:
    image: cognee:0.4.1
    container_name: cozy_cognee
    restart: unless-stopped
    environment:
      - DEBUG=false
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
      - HOST=0.0.0.0
      - HTTP_PORT=8000
      - PYTHONUNBUFFERED=1
      - LLM_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
      - LLM_PROVIDER=openai
      - LLM_MODEL=gpt-4o-mini
      - LLM_ENDPOINT=https://oneapi.naivehero.top/v1
      - LLM_MAX_TOKENS=16384
      - EMBEDDING_PROVIDER=openai
      - EMBEDDING_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
      - EMBEDDING_ENDPOINT=https://oneapi.naivehero.top/v1
      - EMBEDDING_MODEL=openai/text-embedding-3-large
      - EMBEDDING_DIMENSIONS=3072
      - DATABASE_URL=postgresql://cognee_user:cognee_password@postgres:5432/cognee_db
      - DB_PROVIDER=postgres
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=cognee_db
      - DB_USERNAME=cognee_user
      - DB_PASSWORD=cognee_password
      - VECTOR_DB_PROVIDER=pgvector
      - VECTOR_DB_URL=postgresql://cognee_user:cognee_password@postgres:5432/cognee_db
      - GRAPH_DATABASE_PROVIDER=neo4j
      - GRAPH_DATABASE_NAME=neo4j
      - GRAPH_DATABASE_URL=bolt://neo4j:7687
      - GRAPH_DATABASE_USERNAME=neo4j
      - GRAPH_DATABASE_PASSWORD=pleaseletmein
      - REDIS_URL=redis://:cozy_redis_pass@redis:6379/0
      - S3_ENDPOINT=http://minio:9000
      - S3_ACCESS_KEY=minioadmin
      - S3_SECRET_KEY=minioadmin
      - S3_BUCKET_NAME=cognee-storage
      - S3_USE_SSL=false
      - CORS_ALLOWED_ORIGINS=*
      - EXTRAS=api,postgres,neo4j
      - TELEMETRY_DISABLED=1
      - DEFAULT_USER_EMAIL=admin@cognee.com
      - DEFAULT_USER_PASSWORD=passw0rd
      - TIKTOKEN_CACHE_DIR=/root/.tiktoken
    depends_on:
      - postgres
      - redis
      - neo4j
      - minio
    volumes:
      - /data/CozyMemory/cognee/data:/app/data
      - /data/CozyMemory/cognee/logs:/app/logs
      - /data/CozyMemory/tiktoken:/root/.tiktoken
    networks:
      - 1panel-network
    labels:
      createdBy: "Apps"
    deploy:
      resources:
        limits:
          memory: 2g
        reservations:
          memory: 512m

  cognee-frontend:
    image: cognee-frontend:local-0.4.1
    container_name: cozy_cognee_frontend
    restart: unless-stopped
    # cognee-frontend 跑 Next.js dev 模式，NEXT_PUBLIC_* 可在运行时注入
    environment:
      - NEXT_PUBLIC_BACKEND_API_URL=http://YOUR_SERVER_IP:8080
      - NEXT_PUBLIC_IS_CLOUD_ENVIRONMENT=false
      - NEXT_DISABLE_DEV_INDICATORS=true
      - NEXT_TELEMETRY_DISABLED=1
    depends_on:
      - cognee
    networks:
      - 1panel-network
    labels:
      createdBy: "Apps"

  # ==========================================
  # Mem0 服务群
  # ==========================================

  mem0-api:
    image: mem0-api:latest
    container_name: cozy_mem0_api
    restart: unless-stopped
    environment:
      OPENAI_API_KEY: sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
      OPENAI_BASE_URL: https://oneapi.naivehero.top/v1
      OPENAI_MODEL: gpt-4.1-nano-2025-04-14
      QDRANT_HOST: qdrant
      QDRANT_PORT: 6333
      QDRANT_URL: http://qdrant:6333
      QDRANT_COLLECTION_NAME: memories
      HISTORY_DB_PATH: /app/history/history.db
      CORS_ORIGINS: "*"
    depends_on:
      - qdrant
    volumes:
      - /data/CozyMemory/mem0/history:/app/history
      - /data/CozyMemory/mem0/logs:/app/logs
    networks:
      - 1panel-network
    labels:
      createdBy: "Apps"
    deploy:
      resources:
        limits:
          memory: 1g
        reservations:
          memory: 256m

  mem0-webui:
    image: mem0-webui:latest
    container_name: cozy_mem0_webui
    restart: unless-stopped
    # entrypoint.sh 在启动时将 NEXT_PUBLIC_* 替换进 .next/ 编译产物
    environment:
      NEXT_PUBLIC_API_URL: http://YOUR_SERVER_IP:8081
      NEXT_PUBLIC_USER_ID: user
    depends_on:
      - mem0-api
    networks:
      - 1panel-network
    labels:
      createdBy: "Apps"

  # ==========================================
  # Memobase 服务群
  # ==========================================

  memobase-server-api:
    image: memobase-server:latest
    container_name: cozy_memobase_api
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql://memobase:memobase123@postgres:5432/memobase
      REDIS_URL: redis://:cozy_redis_pass@redis:6379/1
      ACCESS_TOKEN: secret
      PROJECT_ID: default
      API_HOSTS: "http://YOUR_SERVER_IP:8019,http://memobase-server-api:8000"
      USE_CORS: "true"
      MEMOBASE_LANGUAGE: zh
      MEMOBASE_LLM_STYLE: openai
      MEMOBASE_LLM_API_KEY: "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
      MEMOBASE_LLM_BASE_URL: "https://oneapi.naivehero.top/v1"
      MEMOBASE_EMBEDDING_API_KEY: "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
      MEMOBASE_EMBEDDING_BASE_URL: "https://oneapi.naivehero.top/v1"
      MEMOBASE_EMBEDDING_PROVIDER: openai
      TIKTOKEN_CACHE_DIR: /root/.tiktoken
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      - postgres
      - redis
    volumes:
      - /data/CozyMemory/tiktoken:/root/.tiktoken
      - /data/CozyMemory/memobase:/app/data
    networks:
      - 1panel-network
    labels:
      createdBy: "Apps"
    deploy:
      resources:
        limits:
          memory: 1g
        reservations:
          memory: 256m

  # ==========================================
  # Caddy 反向代理
  # ==========================================

  caddy:
    image: caddy:alpine
    container_name: cozy_caddy
    restart: unless-stopped
    ports:
      - "8080:8080"
      - "8081:8081"
      - "8019:8019"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - /data/CozyMemory/caddy/data:/data
      - /data/CozyMemory/caddy/config:/config
    depends_on:
      - cognee
      - cognee-frontend
      - mem0-api
      - mem0-webui
      - memobase-server-api
    networks:
      - 1panel-network
    labels:
      createdBy: "Apps"
```

- [ ] **Step 2: 验证完整 compose 配置**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory/base_runtime
docker compose -f docker-compose.1panel.yml config --quiet
```

Expected: 无报错退出

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory
git add base_runtime/docker-compose.1panel.yml
git commit -m "feat(base_runtime): add application services and caddy to compose"
```

---

## Task 5：创建 build.sh

**Files:**
- Create: `base_runtime/build.sh`

- [ ] **Step 1: 创建 build.sh**

写入 `base_runtime/build.sh`：

```bash
#!/bin/bash
# CozyMemory Base Runtime 镜像构建脚本
# 构建所有自定义 Docker 镜像（公共镜像无需构建）
#
# 用法：
#   ./build.sh          # 构建全部镜像
#   ./build.sh cognee   # 仅构建指定镜像（可选值：cognee, cognee-frontend, mem0-api, mem0-webui, memobase）

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECTS_DIR="$(cd "$SCRIPT_DIR/../projects" && pwd)"
TARGET="${1:-all}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[BUILD]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ---- mem0-api ----
build_mem0_api() {
    log "Building mem0-api:latest ..."
    [ -d "$PROJECTS_DIR/CozyMem0" ] || err "CozyMem0 directory not found: $PROJECTS_DIR/CozyMem0"
    docker build \
        -f "$PROJECTS_DIR/CozyMem0/deployment/mem0/Dockerfile" \
        -t mem0-api:latest \
        "$PROJECTS_DIR/CozyMem0"
    log "mem0-api:latest built."
}

# ---- mem0-webui ----
build_mem0_webui() {
    log "Building mem0-webui:latest ..."
    UI_DIR="$PROJECTS_DIR/CozyMem0/projects/mem0/openmemory/ui"
    [ -d "$UI_DIR" ] || err "mem0 UI directory not found: $UI_DIR"
    docker build -t mem0-webui:latest "$UI_DIR"
    log "mem0-webui:latest built."
}

# ---- memobase-server ----
build_memobase() {
    log "Syncing memobase source files ..."
    DEPLOY_DIR="$PROJECTS_DIR/CozyMemobase/deployment/memobase"
    SRC_DIR="$PROJECTS_DIR/CozyMemobase/projects/memobase/src/server/api"
    [ -d "$SRC_DIR" ] || err "Memobase source not found: $SRC_DIR"

    cp "$SRC_DIR/pyproject.toml" "$DEPLOY_DIR/"
    cp "$SRC_DIR/uv.lock"        "$DEPLOY_DIR/"
    cp "$SRC_DIR/api.py"         "$DEPLOY_DIR/"
    cp -r "$SRC_DIR/memobase_server" "$DEPLOY_DIR/"
    log "Memobase source synced. Building memobase-server:latest ..."

    docker build -f "$DEPLOY_DIR/Dockerfile" -t memobase-server:latest "$DEPLOY_DIR"
    log "memobase-server:latest built."
}

# ---- cognee ----
build_cognee() {
    log "Building cognee:0.4.1 ..."
    [ -d "$PROJECTS_DIR/CozyCognee" ] || err "CozyCognee directory not found: $PROJECTS_DIR/CozyCognee"
    docker build \
        -f "$PROJECTS_DIR/CozyCognee/deployment/docker/cognee/Dockerfile" \
        -t cognee:0.4.1 \
        "$PROJECTS_DIR/CozyCognee"
    log "cognee:0.4.1 built."
}

# ---- cognee-frontend ----
build_cognee_frontend() {
    log "Building cognee-frontend:local-0.4.1 ..."
    [ -d "$PROJECTS_DIR/CozyCognee" ] || err "CozyCognee directory not found: $PROJECTS_DIR/CozyCognee"
    docker build \
        -f "$PROJECTS_DIR/CozyCognee/deployment/docker/cognee-frontend/Dockerfile" \
        -t cognee-frontend:local-0.4.1 \
        "$PROJECTS_DIR/CozyCognee"
    log "cognee-frontend:local-0.4.1 built."
}

# ---- 入口 ----
case "$TARGET" in
    all)
        build_mem0_api
        build_mem0_webui
        build_memobase
        build_cognee
        build_cognee_frontend
        ;;
    mem0-api)       build_mem0_api ;;
    mem0-webui)     build_mem0_webui ;;
    memobase)       build_memobase ;;
    cognee)         build_cognee ;;
    cognee-frontend) build_cognee_frontend ;;
    *)
        echo "Usage: $0 [all|mem0-api|mem0-webui|memobase|cognee|cognee-frontend]"
        exit 1
        ;;
esac

echo ""
log "Done! Custom images:"
docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" \
    | grep -E "mem0-api|mem0-webui|memobase-server|cognee"
```

- [ ] **Step 2: 赋予执行权限**

```bash
chmod +x /home/ubuntu/CozyProjects/CozyMemory/base_runtime/build.sh
```

- [ ] **Step 3: 验证脚本语法**

```bash
bash -n /home/ubuntu/CozyProjects/CozyMemory/base_runtime/build.sh
```

Expected: 无报错输出（exit 0）

- [ ] **Step 4: Commit**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory
git add base_runtime/build.sh
git commit -m "feat(base_runtime): add unified image build script"
```

---

## Task 6：构建所有自定义镜像

- [ ] **Step 1: 准备 tiktoken 缓存目录**

```bash
mkdir -p /data/CozyMemory/tiktoken
cp /home/ubuntu/.tiktoken/* /data/CozyMemory/tiktoken/
ls /data/CozyMemory/tiktoken/
```

Expected: 看到 `.tiktoken` 文件（如 `o200k_base.tiktoken` 等）

- [ ] **Step 2: 构建所有镜像（时间较长，约 10-30 分钟）**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory/base_runtime
./build.sh all 2>&1 | tee /tmp/build.log
```

Expected: 最终看到 `Done! Custom images:` 和 5 个镜像列表

- [ ] **Step 3: 验证镜像存在**

```bash
for img in "mem0-api:latest" "mem0-webui:latest" "memobase-server:latest" "cognee:0.4.1" "cognee-frontend:local-0.4.1"; do
    docker image inspect "$img" > /dev/null 2>&1 && echo "✓ $img" || echo "✗ $img MISSING"
done
```

Expected: 5 行全为 `✓`

---

## Task 7：替换占位符并全栈启动验证

- [ ] **Step 1: 替换 YOUR_SERVER_IP**

```bash
# 查询本机 IP
ip route get 1 | awk '{print $7; exit}'
```

Expected: 看到服务器 IP（如 192.168.66.11）

```bash
# 替换 compose 文件中的占位符（将 192.168.66.11 替换为实际 IP）
sed -i 's/YOUR_SERVER_IP/192.168.66.11/g' \
    /home/ubuntu/CozyProjects/CozyMemory/base_runtime/docker-compose.1panel.yml
```

- [ ] **Step 2: 启动全部服务**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory/base_runtime
docker compose -f docker-compose.1panel.yml up -d
```

Expected: 无报错，所有容器启动

- [ ] **Step 3: 等待服务就绪**

```bash
sleep 30
docker compose -f docker-compose.1panel.yml ps
```

Expected: 所有服务均为 `running`（neo4j 和 cognee 启动较慢，可等待 60 秒）

- [ ] **Step 4: 验证 Cognee API**

```bash
curl -s http://localhost:8080/api/v1/users | head -c 200
```

Expected: 返回 JSON（可能是 401 未授权或用户列表，不应 404/Connection refused）

- [ ] **Step 5: 验证 Mem0 API**

```bash
curl -s http://localhost:8081/api/v1/memories?user_id=test | head -c 200
```

Expected: 返回 JSON（memories 列表或空数组）

- [ ] **Step 6: 验证 Memobase API**

```bash
curl -s -H "Authorization: Bearer secret" \
    http://localhost:8019/api/v1/users | head -c 200
```

Expected: 返回 JSON（不应 Connection refused）

- [ ] **Step 7: 验证 Cognee 前端**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/
```

Expected: `200` 或 `308`（重定向）

- [ ] **Step 8: 验证 Mem0 前端**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8081/
```

Expected: `200` 或 `308`

- [ ] **Step 9: 最终 Commit**

```bash
cd /home/ubuntu/CozyProjects/CozyMemory
# 将替换后的 IP 写回占位符（便于 git 版本管理，部署时再替换）
sed -i 's/192.168.66.11/YOUR_SERVER_IP/g' \
    base_runtime/docker-compose.1panel.yml
git add base_runtime/
git commit -m "feat: add base_runtime one-click deployment

包含：
- docker-compose.1panel.yml（10个服务，Caddy多端口）
- Caddyfile（8080 cognee / 8081 mem0 / 8019 memobase）
- sql/init.sql（postgres多租户初始化）
- build.sh（5个自定义镜像统一构建）

Generated with [Claude Code](https://claude.ai/code)
via [Happy](https://happy.engineering)

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: Happy <yesreply@happy.engineering>"
```

---

## 部署快速参考

```bash
# 1. 构建镜像（首次或代码更新后）
cd base_runtime && ./build.sh all

# 2. 准备 tiktoken 缓存（首次）
mkdir -p /data/CozyMemory/tiktoken
cp /home/ubuntu/.tiktoken/* /data/CozyMemory/tiktoken/

# 3. 替换服务器 IP
sed -i 's/YOUR_SERVER_IP/<实际IP>/g' docker-compose.1panel.yml

# 4. 启动
docker compose -f docker-compose.1panel.yml up -d

# 5. 查看状态
docker compose -f docker-compose.1panel.yml ps
```

**访问地址（替换 SERVER_IP）：**
- Cognee 前端：`http://SERVER_IP:8080`
- Cognee API：`http://SERVER_IP:8080/api/v1/`
- Mem0 前端：`http://SERVER_IP:8081`
- Mem0 API：`http://SERVER_IP:8081/api/v1/`
- Memobase API：`http://SERVER_IP:8019`

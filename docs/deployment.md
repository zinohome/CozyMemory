# CozyMemory 部署设计文档

**版本**: 2.0  
**日期**: 2026-04-13  
**状态**: 已批准

---

## 1. 部署架构

CozyMemory 作为独立容器加入现有的 `1panel-network` 网络，与 Mem0、Memobase、Cognee 互通。

```
┌─────────────────────────────────────────────────────────────────┐
│                    1panel-network (Docker)                       │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Mem0 API    │  │  Memobase    │  │  Cognee      │          │
│  │  :8888       │  │  :8019       │  │  :8000       │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                  │                  │                  │
│         │    ┌─────────────────────────┐      │                 │
│         └────│  CozyMemory Service     │──────┘                 │
│              │  REST :8010             │                        │
│              │  gRPC :50051            │                        │
│              └─────────────────────────┘                        │
│                          │                                       │
│              ┌───────────┴───────────┐                           │
│              │  外部服务 / 其他微服务  │                           │
│              └───────────────────────┘                           │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Postgres │  │  Redis   │  │  Qdrant  │  │  Neo4j   │       │
│  │ :5432    │  │  :6379   │  │  :6333   │  │  :7687   │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Dockerfile

```dockerfile
FROM python:3.11-slim AS base

WORKDIR /app

# 安装系统依赖（gRPC 需要）
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY src/ src/
COPY proto/ proto/

# 生成 gRPC 代码
RUN python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./src/cozymemory/grpc_server \
    --grpc_python_out=./src/cozymemory/grpc_server \
    ./proto/common.proto \
    ./proto/conversation.proto \
    ./proto/profile.proto \
    ./proto/knowledge.proto

EXPOSE 8000 50051

# 默认启动 REST + gRPC
CMD ["python", "-m", "cozymemory.app"]
```

---

## 3. docker-compose.yml

将 CozyMemory 容器加入 `unified_deployment/docker-compose.1panel.yml`：

```yaml
# 在现有 docker-compose.1panel.yml 中添加：

  # ==========================================
  # CozyMemory 统一记忆服务
  # ==========================================
  cozymemory:
    build:
      context: /path/to/CozyMemory
      dockerfile: Dockerfile
    container_name: cozy_memory
    restart: unless-stopped
    ports:
      - "8010:8000"    # REST API
      - "50051:50051"  # gRPC
    environment:
      # 应用配置
      - APP_ENV=production
      - LOG_LEVEL=INFO
      # Mem0 引擎
      - MEM0_API_URL=http://mem0-api:8000
      - MEM0_API_KEY=${MEM0_API_KEY:-}
      - MEM0_ENABLED=true
      # Memobase 引擎
      - MEMOBASE_API_URL=http://memobase-server-api:8000
      - MEMOBASE_API_KEY=secret
      - MEMOBASE_ENABLED=true
      # Cognee 引擎
      - COGNEE_API_URL=http://cognee:8000
      - COGNEE_API_KEY=${COGNEE_API_KEY:-}
      - COGNEE_ENABLED=true
    depends_on:
      - mem0-api
      - memobase-server-api
      - cognee
    networks:
      - 1panel-network
    labels:
      createdBy: "Apps"
```

---

## 4. 依赖清单

### requirements.txt

```
# 核心框架
fastapi>=0.110.0
uvicorn[standard]>=0.29.0

# HTTP 客户端（SDK 通信）
httpx[http2]>=0.27.0

# 数据验证
pydantic>=2.0
pydantic-settings>=2.0

# gRPC
grpcio>=1.60.0
grpcio-tools>=1.60.0
protobuf>=4.25.0

# 日志
structlog>=24.0
```

### requirements-dev.txt

```
-r requirements.txt

# 测试
pytest>=8.0
pytest-asyncio>=0.23
pytest-cov>=5.0
httpx  # 测试客户端

# 代码质量
ruff>=0.3
mypy>=1.9
black>=24.0
```

---

## 5. 环境变量

### .env.example

```bash
# ==================== 应用配置 ====================
APP_NAME=CozyMemory
APP_VERSION=2.0.0
APP_ENV=development
DEBUG=true
HOST=0.0.0.0
PORT=8000
GRPC_PORT=50051

# ==================== 日志配置 ====================
LOG_LEVEL=INFO
LOG_FORMAT=json

# ==================== Mem0 引擎 ====================
MEM0_API_URL=http://localhost:8888
MEM0_API_KEY=                    # 自托管默认不需要
MEM0_TIMEOUT=30.0
MEM0_ENABLED=true

# ==================== Memobase 引擎 ====================
MEMOBASE_API_URL=http://localhost:8019
MEMOBASE_API_KEY=secret           # 自托管默认 token
MEMOBASE_TIMEOUT=60.0
MEMOBASE_ENABLED=true

# ==================== Cognee 引擎 ====================
COGNEE_API_URL=http://localhost:8000
COGNEE_API_KEY=                   # 可选
COGNEE_TIMEOUT=300.0              # cognify 操作需要更长超时
COGNEE_ENABLED=true
```

---

## 6. 服务启动

### 开发环境

```bash
# 安装依赖
pip install -r requirements-dev.txt

# 启动 REST API（开发模式）
uvicorn cozymemory.app:create_app --factory --reload --port 8000

# 启动 gRPC（开发模式）
python -m cozymemory.grpc_server.server
```

### 生产环境

```bash
# 构建并启动
docker-compose -f unified_deployment/docker-compose.1panel.yml up -d cozymemory

# 查看日志
docker-compose logs -f cozymemory

# 健康检查
curl http://localhost:8010/api/v1/health
```

---

## 7. 端口分配

| 服务 | 内部端口 | 外部端口 | 说明 |
|------|---------|---------|------|
| CozyMemory REST | 8000 | 8010 | REST API |
| CozyMemory gRPC | 50051 | 50051 | gRPC 服务 |
| Mem0 API | 8000 | 8888 | 会话记忆引擎 |
| Memobase | 8000 | 8019 | 用户画像引擎 |
| Cognee | 8000 | 8000 | 知识库引擎 |

> 注意：CozyMemory REST 外部端口为 8010，避免与 Cognee 的 8000 冲突。内部通信使用 Docker 网络的服务名（如 `mem0-api:8000`），无需端口映射。

---

## 8. 健康检查与监控

### 健康检查端点

```
GET /api/v1/health
```

返回各引擎状态：

```json
{
  "status": "healthy",
  "engines": {
    "mem0": {"name": "Mem0", "status": "healthy", "latency_ms": 12.5},
    "memobase": {"name": "Memobase", "status": "healthy", "latency_ms": 8.3},
    "cognee": {"name": "Cognee", "status": "healthy", "latency_ms": 15.1}
  },
  "timestamp": "2026-04-13T10:30:00Z"
}
```

- `healthy`: 所有引擎正常
- `degraded`: 部分引擎不可用
- `unhealthy`: 全部引擎不可用

### Docker 健康检查

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

---

## 9. 后期扩展点

以下功能暂不实现，但架构预留了扩展空间：

### 9.1 认证

在 `api/deps.py` 中添加认证中间件：

```python
# 后期添加：API Key 认证
from fastapi import Security
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
```

### 9.2 速率限制

使用 `slowapi` 中间件：

```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)
```

### 9.3 指标监控

使用 `prometheus-fastapi-instrumentator`：

```python
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)
```

### 9.4 日志聚合

使用 `structlog` + JSON 格式，可接入 ELK/Loki。
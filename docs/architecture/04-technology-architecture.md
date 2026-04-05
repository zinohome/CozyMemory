# 统一 AI 记忆服务平台 - 技术架构设计

**文档编号**: ARCH-TECH-004  
**版本**: 1.0  
**状态**: 草案  
**创建日期**: 2026-04-05  
**作者**: 蟹小五 (AI 架构师)

---

## 1. 技术栈总览

### 1.1 核心技术栈

| 层级 | 技术 | 版本 | 理由 |
|------|------|------|------|
| **API Gateway** | FastAPI | 0.109+ | 高性能、异步、OpenAPI 自动生成 |
| **GraphQL** | Strawberry | 0.200+ | FastAPI 原生集成、类型安全 |
| **gRPC** | grpcio | 1.60+ | 官方库、性能最优 |
| **数据库** | PostgreSQL | 15+ | 成熟稳定、JSON 支持 |
| **缓存** | Redis | 7+ | 高性能、数据结构丰富 |
| **对象存储** | MinIO | 2024+ | S3 兼容、自托管 |
| **LLM 推理** | Ollama | 0.1+ | 本地部署、模型丰富 |

### 1.2 开发工具链

| 用途 | 工具 | 版本 |
|------|------|------|
| 包管理 | uv/pip | 最新 |
| 代码质量 | ruff + mypy | 最新 |
| 测试 | pytest + httpx | 8.0+ |
| 文档 | MkDocs | 最新 |
| 容器化 | Docker + Compose | 24+ |
| CI/CD | GitHub Actions | - |

---

## 2. 部署架构

### 2.1 Docker Compose 架构

```yaml
# docker-compose.yml
version: '3.9'

services:
  # ==================== 统一 API 层 ====================
  api-gateway:
    build:
      context: ./apps/api-gateway
      dockerfile: Dockerfile
    container_name: uamp-api-gateway
    ports:
      - "8000:8000"  # REST/GraphQL
      - "50051:50051"  # gRPC
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/uamp
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - ROUTING_MODE=hybrid
      - LLM_URL=http://intent-llm:11434
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs
    networks:
      - uamp-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # ==================== 数据库层 ====================
  postgres:
    image: postgres:15-alpine
    container_name: uamp-postgres
    environment:
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=uamp
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./initdb:/docker-entrypoint-initdb.d
    networks:
      - uamp-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: uamp-redis
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - uamp-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ==================== 对象存储 ====================
  minio:
    image: minio/minio:latest
    container_name: uamp-minio
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=${MINIO_ROOT_USER}
      - MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD}
    ports:
      - "9000:9000"  # API
      - "9001:9001"  # Console
    volumes:
      - minio_data:/data
    networks:
      - uamp-network
    restart: unless-stopped

  # ==================== LLM 意图识别 ====================
  intent-llm:
    image: ollama/ollama:latest
    container_name: uamp-intent-llm
    volumes:
      - ollama_models:/root/.ollama
    networks:
      - uamp-network
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    # 启动后执行：docker exec -it uamp-intent-llm ollama pull qwen2.5:1.5b

  # ==================== 记忆引擎（外部服务） ====================
  # Cognee
  cognee:
    image: cognee/cognee:latest
    container_name: uamp-cognee
    environment:
      - COGNEE_DB_URL=postgresql://user:pass@postgres:5432/cognee
    networks:
      - uamp-network
    restart: unless-stopped
    # 可选，如果 Cognee 独立部署则不需要

  # Mem0
  mem0:
    image: mem0ai/mem0:latest
    container_name: uamp-mem0
    environment:
      - MEM0_DB_URL=postgresql://user:pass@postgres:5432/mem0
    networks:
      - uamp-network
    restart: unless-stopped
    # 可选，如果 Mem0 独立部署则不需要

  # Memobase
  memobase:
    image: memobase/memobase:latest
    container_name: uamp-memobase
    environment:
      - MEMOBASE_DB_URL=postgresql://user:pass@postgres:5432/memobase
    networks:
      - uamp-network
    restart: unless-stopped
    # 可选，如果 Memobase 独立部署则不需要

  # ==================== 监控 ====================
  prometheus:
    image: prom/prometheus:latest
    container_name: uamp-prometheus
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    ports:
      - "9090:9090"
    networks:
      - uamp-network
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: uamp-grafana
    environment:
      - GF_SECURITY_ADMIN_USER=${GRAFANA_ADMIN_USER}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
    ports:
      - "3000:3000"
    networks:
      - uamp-network
    restart: unless-stopped
    depends_on:
      - prometheus

networks:
  uamp-network:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
  minio_data:
  ollama_models:
  prometheus_data:
  grafana_data:
```

### 2.2 网络拓扑

```
┌─────────────────────────────────────────────────────────────┐
│                      Public Network                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  Reverse Proxy (可选)                 │   │
│  │                   Nginx / Traefik                     │   │
│  │                   Port: 443 (HTTPS)                   │   │
│  └────────────────────┬─────────────────────────────────┘   │
│                       │                                      │
│                       ▼                                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              API Gateway                              │   │
│  │              Port: 8000 (HTTP)                        │   │
│  │              Port: 50051 (gRPC)                       │   │
│  └────────────────────┬─────────────────────────────────┘   │
│                       │                                      │
│         ┌─────────────┼─────────────┐                       │
│         │             │             │                       │
│         ▼             ▼             ▼                       │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐                 │
│  │ Postgres  │ │   Redis   │ │   MinIO   │                 │
│  │  :5432    │ │  :6379    │ │ :9000/9001│                 │
│  └───────────┘ └───────────┘ └───────────┘                 │
│                                                              │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐                 │
│  │ Intent    │ │  Cognee   │ │   Mem0    │                 │
│  │ LLM       │ │  (外部)   │ │  (外部)   │                 │
│  │ :11434    │ │           │ │           │                 │
│  └───────────┘ └───────────┘ └───────────┘                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 项目结构

### 3.1 目录结构

```
uamp/
├── apps/
│   └── api-gateway/
│       ├── src/
│       │   ├── __init__.py
│       │   ├── main.py              # FastAPI 应用入口
│       │   ├── config.py            # 配置管理
│       │   ├── dependencies.py      # 依赖注入
│       │   │
│       │   ├── api/
│       │   │   ├── __init__.py
│       │   │   ├── rest/            # RESTful API
│       │   │   │   ├── __init__.py
│       │   │   │   ├── memories.py
│       │   │   │   ├── conversations.py
│       │   │   │   └── users.py
│       │   │   │
│       │   │   ├── graphql/         # GraphQL API
│       │   │   │   ├── __init__.py
│       │   │   │   ├── schema.py
│       │   │   │   ├── queries.py
│       │   │   │   ├── mutations.py
│       │   │   │   └── subscriptions.py
│       │   │   │
│       │   │   └── grpc/            # gRPC Server
│       │   │       ├── __init__.py
│       │   │       ├── server.py
│       │   │       └── servicers.py
│       │   │
│       │   ├── services/
│       │   │   ├── __init__.py
│       │   │   ├── memory_service.py
│       │   │   ├── router_service.py
│       │   │   ├── fusion_service.py
│       │   │   └── cache_service.py
│       │   │
│       │   ├── adapters/
│       │   │   ├── __init__.py
│       │   │   ├── base.py
│       │   │   ├── cognee_adapter.py
│       │   │   ├── mem0_adapter.py
│       │   │   └── memobase_adapter.py
│       │   │
│       │   ├── routers/
│       │   │   ├── __init__.py
│       │   │   ├── rule_router.py
│       │   │   ├── llm_router.py
│       │   │   └── hybrid_router.py
│       │   │
│       │   ├── models/
│       │   │   ├── __init__.py
│       │   │   ├── user.py
│       │   │   ├── api_key.py
│       │   │   └── memory.py
│       │   │
│       │   ├── schemas/
│       │   │   ├── __init__.py
│       │   │   ├── memory.py
│       │   │   ├── user.py
│       │   │   └── api_key.py
│       │   │
│       │   ├── auth/
│       │   │   ├── __init__.py
│       │   │   ├── jwt_auth.py
│       │   │   ├── api_key_auth.py
│       │   │   └── deps.py
│       │   │
│       │   ├── middleware/
│       │   │   ├── __init__.py
│       │   │   ├── authentication.py
│       │   │   ├── rate_limiting.py
│       │   │   ├── logging.py
│       │   │   └── exception_handler.py
│       │   │
│       │   └── utils/
│       │       ├── __init__.py
│       │       ├── logger.py
│       │       └── metrics.py
│       │
│       ├── tests/
│       │   ├── __init__.py
│       │   ├── conftest.py
│       │   ├── test_rest_api.py
│       │   ├── test_graphql.py
│       │   └── test_grpc.py
│       │
│       ├── Dockerfile
│       ├── requirements.txt
│       └── pyproject.toml
│
├── proto/
│   └── memory_service.proto
│
├── monitoring/
│   ├── prometheus.yml
│   └── grafana/
│       └── dashboards/
│           └── api-gateway.json
│
├── initdb/
│   └── 001_init_schema.sql
│
├── docs/
│   └── architecture/
│       ├── 00-architecture-vision.md
│       ├── 01-business-architecture.md
│       ├── 02-data-architecture.md
│       ├── 03-application-architecture.md
│       ├── 04-technology-architecture.md
│       ├── 05-implementation-plan.md
│       ├── 06-quality-assurance-plan.md
│       └── adr/
│           ├── ADR-001-api-gateway.md
│           ├── ADR-002-graphql.md
│           ├── ADR-003-grpc.md
│           ├── ADR-004-routing.md
│           └── ADR-005-auth.md
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## 4. 配置管理

### 4.1 环境变量

```bash
# .env.example

# ==================== 应用配置 ====================
APP_NAME=Unified AI Memory Platform
APP_ENV=development  # development | staging | production
DEBUG=true
SECRET_KEY=your-secret-key-change-in-production

# ==================== 数据库配置 ====================
DATABASE_URL=postgresql://uamp:password@localhost:5432/uamp
DB_USER=uamp
DB_PASSWORD=password

# ==================== Redis 配置 ====================
REDIS_URL=redis://localhost:6379/0

# ==================== MinIO 配置 ====================
MINIO_ENDPOINT=localhost:9000
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_BUCKET=memories

# ==================== LLM 配置 ====================
LLM_URL=http://localhost:11434
LLM_MODEL=qwen2.5:1.5b
LLM_TIMEOUT=5.0
ROUTING_MODE=hybrid  # hybrid | rules_only | llm_only

# ==================== 认证配置 ====================
JWT_SECRET_KEY=${SECRET_KEY}
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# ==================== 监控配置 ====================
PROMETHEUS_URL=http://localhost:9090
GRAFANA_URL=http://localhost:3000

# ==================== 记忆引擎配置 ====================
COGNEE_API_URL=http://localhost:8001
MEM0_API_URL=http://localhost:8888
MEMOBASE_API_URL=http://localhost:8002
```

### 4.2 配置类

```python
# src/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Literal

class Settings(BaseSettings):
    """应用配置"""
    
    # 应用配置
    app_name: str = "Unified AI Memory Platform"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    secret_key: str
    
    # 数据库
    database_url: str
    db_user: str
    db_password: str
    
    # Redis
    redis_url: str
    
    # MinIO
    minio_endpoint: str
    minio_root_user: str
    minio_root_password: str
    minio_bucket: str = "memories"
    
    # LLM
    llm_url: str = "http://localhost:11434"
    llm_model: str = "qwen2.5:1.5b"
    llm_timeout: float = 5.0
    routing_mode: Literal["hybrid", "rules_only", "llm_only"] = "hybrid"
    
    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
    
    # 记忆引擎
    cognee_api_url: str = "http://localhost:8001"
    mem0_api_url: str = "http://localhost:8888"
    memobase_api_url: str = "http://localhost:8002"
    
    # 监控
    prometheus_url: str = "http://localhost:9090"
    grafana_url: str = "http://localhost:3000"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
```

---

## 5. 监控与日志

### 5.1 日志配置

```python
# src/utils/logger.py
import logging
import sys
from datetime import datetime

def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """配置结构化日志"""
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # 格式化器
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger
```

### 5.2 监控指标

```python
# src/utils/metrics.py
from prometheus_client import Counter, Histogram, Gauge
from functools import wraps
import time

# 指标定义
REQUEST_COUNT = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'api_request_latency_seconds',
    'API request latency',
    ['method', 'endpoint'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

ACTIVE_CONNECTIONS = Gauge(
    'api_active_connections',
    'Number of active connections'
)

ROUTING_DECISIONS = Counter(
    'routing_decisions_total',
    'Total routing decisions',
    ['source', 'engines']
)

CACHE_HIT_RATE = Gauge(
    'cache_hit_rate',
    'Cache hit rate'
)

# 装饰器
def track_metrics(endpoint: str):
    """追踪 API 指标装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                status = 'success'
                return result
            except Exception as e:
                status = 'error'
                raise
            finally:
                duration = time.time() - start_time
                REQUEST_COUNT.labels(
                    method='POST',
                    endpoint=endpoint,
                    status=status
                ).inc()
                REQUEST_LATENCY.labels(
                    method='POST',
                    endpoint=endpoint
                ).observe(duration)
        
        return wrapper
    return decorator
```

### 5.3 Prometheus 配置

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'api-gateway'
    static_configs:
      - targets: ['api-gateway:8000']
    metrics_path: '/metrics'
    
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
  
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

---

## 6. 安全配置

### 6.1 CORS 配置

```python
# src/middleware/cors.py
from fastapi.middleware.cors import CORSMiddleware

def setup_cors(app, settings: Settings):
    """配置 CORS"""
    
    if settings.app_env == "production":
        origins = [
            "https://yourdomain.com",
            "https://app.yourdomain.com",
        ]
    else:
        origins = ["*"]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
```

### 6.2 限流配置

```python
# src/middleware/rate_limiting.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# 限流规则
# - 普通用户：100 请求/分钟
# - API Key 用户：1000 请求/分钟
# - 超级用户：不限流
```

---

## 7. 性能优化

### 7.1 数据库连接池

```python
# src/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(
    settings.database_url,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600,
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
```

### 7.2 Redis 缓存策略

```python
# src/services/cache_service.py
import redis.asyncio as redis
from typing import Optional, Any
import json

class CacheService:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.default_ttl = 3600  # 1 小时
    
    async def get(self, key: str) -> Optional[Any]:
        value = await self.redis.get(key)
        if value:
            return json.loads(value)
        return None
    
    async def set(self, key: str, value: Any, ttl: int = None):
        await self.redis.setex(
            key,
            ttl or self.default_ttl,
            json.dumps(value)
        )
    
    async def delete(self, key: str):
        await self.redis.delete(key)
    
    # 路由结果缓存
    async def cache_routing_result(self, query_hash: str, result: dict):
        await self.set(f"routing:{query_hash}", result, ttl=3600)
    
    async def get_routing_result(self, query_hash: str) -> Optional[dict]:
        return await self.get(f"routing:{query_hash}")
```

---

**END OF DOCUMENT**
